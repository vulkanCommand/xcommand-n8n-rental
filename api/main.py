import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import stripe
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from db import fetch_all, execute
from openai_client import chat_with_openai
from provisioner import start_n8n_local, stop_container, remove_volume


app = FastAPI()

# --- CORS ---------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: tighten this when you lock in frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Knowledge base for the support bot --------------------------------------

KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "support_knowledge.md")

try:
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        XCOMMAND_KNOWLEDGE = f.read()
    print("[support] Loaded support_knowledge.md")
except Exception as e:
    print("[support] Failed to load support_knowledge.md:", e)
    XCOMMAND_KNOWLEDGE = ""


# --- Models -------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ProvisionRequest(BaseModel):
    email: EmailStr
    plan: str  # '1d' or '5d'


class CheckoutRequest(BaseModel):
    email: EmailStr
    plan: str  # "1d" or "5d"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

class BackupRequest(BaseModel):
    workspace_id: int
    email: EmailStr
    container_name: str
    volume_name: str
    expires_at: datetime  # ISO string from n8n will be parsed automatically

def extract_email_from_messages(messages):
    for item in reversed(messages):  # check newest first
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", item.content)
        if match:
            return match.group(0)
    return None


# --- Workspace provisioning core ---------------------------------------------


def provision_core(email: str, plan: str):
    """
    Provision a new n8n workspace for the given email and plan.

    - Valid plans: '1d' (24 hours) or '5d' (5 days)
    - Creates app_users row if needed
    - Inserts a payment record (dev/test)
    - Inserts a workspace row
    - Starts the n8n container with an expiry label
    - Marks workspace active and stores its public URL
    """
    if plan not in ("1d", "5d"):
        raise ValueError("plan must be '1d' or '5d'")

    # Duration based on plan
    days = 1 if plan == "1d" else 5

    # Random workspace subdomain like "u-3d83d4"
    sub = f"u-{secrets.token_hex(3)}"

    # Root domain for dev vs prod (used for internal naming)
    root = os.getenv("N8N_ROOT_DOMAIN", "localhost")
    fqdn = f"{sub}.{root}" if root != "localhost" else f"{sub}.localhost"

    # Timezone-aware UTC expiry
    expires_dt = datetime.now(timezone.utc) + timedelta(days=days)
    expires_iso = expires_dt.isoformat()

    # Container + volume names
    container_name = f"n8n_{sub}"
    volume_name = f"n8n_{sub}_data"

    # Ensure app_users row exists (idempotent)
    execute(
        """
        insert into app_users (email)
        values (%s)
        on conflict (email) do nothing
        """,
        (email,),
    )

    # Record a fake payment (dev only)
    amount_cents = 99 if days == 1 else 300
    execute(
        """
        insert into payments (stripe_session_id, email, plan, amount_cents)
        values (%s, %s, %s, %s)
        on conflict (stripe_session_id) do nothing
        """,
        (f"test_{secrets.token_hex(6)}", email, plan, amount_cents),
    )

    # Create workspace row in "provisioning" state
    execute(
        """
        insert into workspaces (email, plan, subdomain, fqdn, container_name, volume_name, status, expires_at)
        values (%s, %s, %s, %s, %s, %s, 'provisioning', %s)
        """,
        (email, plan, sub, fqdn, container_name, volume_name, expires_dt),
    )

    # Boot local n8n with explicit expires_at for janitor label
    host_port = start_n8n_local(
        container_name=container_name,
        volume_name=volume_name,
        encryption_key=os.getenv("ENCRYPTION_KEY", "devkey"),
        expires_at=expires_iso,
    )

    # Always use the HTTPS workspace subdomain as the public URL.
    # Example: https://u-3d83d4.xcommand.cloud
    workspace_root = os.getenv("WORKSPACE_BASE_DOMAIN", "xcommand.cloud")
    public_url = f"https://{sub}.{workspace_root}"

    # Mark active and store URL (overwrite fqdn with public URL)
    execute(
        "update workspaces set status='active', fqdn=%s where subdomain=%s",
        (public_url, sub),
    )

    # Return the workspace row
    rows = fetch_all(
        """
        select id, email, subdomain, fqdn, status, expires_at, created_at
        from workspaces
        where subdomain=%s
        """,
        (sub,),
    )
    if not rows:
        raise RuntimeError("workspace row not found after insert")

    return rows[0]


# --- Health -------------------------------------------------------------------


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "api",
        "domain": os.getenv("N8N_ROOT_DOMAIN", "unset"),
    }


# --- Workspace lookup APIs ----------------------------------------------------


@app.get("/workspaces/by-email/{email}")
def get_workspace_by_email(email: EmailStr):
    """
    Return the most recent non-deleted workspace for this email.
    """
    rows = fetch_all(
        """
        select *
        from workspaces
        where email = %s
          and status <> 'deleted'
        order by created_at desc
        limit 1
        """,
        (email,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="No active workspace for this email")

    workspace = rows[0]
    return JSONResponse(jsonable_encoder({"ok": True, "workspace": workspace}))


@app.get("/workspaces/all-by-email/{email}")
def get_workspaces_by_email(email: EmailStr):
    """
    Return all non-deleted, non-expired workspaces for this email, newest first.
    """
    rows = fetch_all(
        """
        select
          id,
          email,
          plan,
          subdomain,
          fqdn,
          container_name,
          volume_name,
          status,
          expires_at,
          created_at
        from workspaces
        where email = %s
          and status <> 'deleted'
          and expires_at > now() at time zone 'utc'

        order by created_at desc
        """,
        (email,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="No active workspaces for this email")

    return JSONResponse(jsonable_encoder({"ok": True, "workspaces": rows}))


# --- Workspace lifecycle management ------------------------------------------


@app.post("/provision/test")
def provision_test(req: ProvisionRequest):
    """
    Manually provision a workspace (test-only helper).
    """
    try:
        row = provision_core(req.email, req.plan)
        return JSONResponse(jsonable_encoder(row))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/provision/simulate")
def provision_simulate(req: ProvisionRequest):
    """
    Another manual provision endpoint (kept for compatibility).
    """
    try:
        row = provision_core(req.email, req.plan)
        return JSONResponse(jsonable_encoder(row))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/workspaces/{sub}/stop")
def stop_workspace(sub: str = Path(..., pattern=r"^u-[0-9a-f]{6}$")):
    """
    Stop the container for a given workspace subdomain.
    """
    rows = fetch_all(
        "select container_name from workspaces where subdomain=%s",
        (sub,),
    )
    if not rows:
        raise HTTPException(404, "workspace not found")

    container_name = rows[0]["container_name"]
    stopped = stop_container(container_name)
    execute("update workspaces set status='stopping' where subdomain=%s", (sub,))
    return {"ok": True, "stopped": stopped}


@app.post("/workspaces/{sub}/wipe")
def wipe_workspace(sub: str = Path(..., pattern=r"^u-[0-9a-f]{6}$")):
    """
    Wipe the Docker volume for a given workspace and mark it deleted.
    """
    rows = fetch_all(
        "select volume_name from workspaces where subdomain=%s",
        (sub,),
    )
    if not rows:
        raise HTTPException(404, "workspace not found")

    volume_name = rows[0]["volume_name"]
    wiped = remove_volume(volume_name)
    execute("update workspaces set status='deleted' where subdomain=%s", (sub,))
    return {"ok": True, "wiped": wiped}

# --- Backup endpoint for n8n --------------------------------------------------

@app.post("/workspaces/backup")
def backup_workspace(req: BackupRequest):
    """
    Endpoint for n8n to trigger a 'backup-before-expiry' action.
    """
    # 1) Check that the workspace exists
    rows = fetch_all(
        """
        select
          id,
          email,
          container_name,
          volume_name,
          status,
          export_notice_sent
        from workspaces
        where id = %s
        """,
        (req.workspace_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="workspace not found")

    ws = rows[0]

    if ws["email"] != req.email:
        raise HTTPException(status_code=400, detail="email does not match workspace record")

    # 2) TODO: put your real backup logic here
    # For now we just log so you can see it in container logs.
    print(
        f"[backup] Request received for workspace_id={req.workspace_id}, "
        f"email={req.email}, container={req.container_name}, volume={req.volume_name}, "
        f"expires_at={req.expires_at}"
    )

    # Do NOT update export_notice_sent here.
    # Your n8n step 6 already sets export_notice_sent = true.

    return {"ok": True, "workspace_id": req.workspace_id}


# --- Stripe checkout + webhook -----------------------------------------------


@app.post("/stripe/create-checkout-session")
async def create_checkout_session(req: CheckoutRequest):
    """
    Create a Stripe Checkout session for a given email and plan.
    """
    stripe.api_key = os.getenv("STRIPE_SECRET")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe secret not configured")

    # Basic plan validation
    if req.plan not in ("1d", "5d"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Amounts in cents
    amount_map = {
        "1d": 100,  # $1
        "5d": 300,  # $3
    }
    label_map = {
        "1d": "xCommand 24h n8n workspace",
        "5d": "xCommand 5-day n8n workspace",
    }

    amount = amount_map[req.plan]

    # Always use HTTPS URLs that Stripe accepts (ignore frontend file:// urls)
    success_url = "https://app.xcommand.cloud/ready.html"
    cancel_url = "https://app.xcommand.cloud/pay.html"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": label_map[req.plan]},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "email": str(req.email),
                "plan": req.plan,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e}")

    return {"checkout_url": session.url, "id": session.id}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook endpoint for Stripe checkout.session.completed.

    Expected payload shape (simplified):

    {
      "type": "checkout.session.completed",
      "data": {
        "object": {
          "customer_details": { "email": "user@example.com" },
          "metadata": { "email": "...", "plan": "1d" }
        }
      }
    }
    """
    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Ignore other Stripe event types
    if event.get("type") != "checkout.session.completed":
        return JSONResponse({"ok": True, "ignored": True})

    session = (event.get("data") or {}).get("object") or {}
    metadata = session.get("metadata") or {}

    email = (
        (session.get("customer_details") or {}).get("email")
        or metadata.get("email")
    )
    plan = metadata.get("plan") or "1d"

    if not email:
        raise HTTPException(status_code=400, detail="Missing email in event")

    # Basic plan validation
    if plan not in ("1d", "5d"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    try:
        workspace = provision_core(email=email, plan=plan)
    except Exception as e:
        # Surface provisioning errors as 400 for now
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(jsonable_encoder({"ok": True, "workspace": workspace}))


# --- AI Support Chat ----------------------------------------------------------


@app.get("/metrics/active-workspaces")
def metric_active_workspaces():
    """
    Return the number of non-expired, non-deleted workspaces.
    Used by Grafana for accurate active workspace counts.
    """
    row = fetch_one("""
        SELECT COUNT(*) AS count
        FROM workspaces
        WHERE status <> 'deleted'
          AND expires_at > NOW() AT TIME ZONE 'utc'
    """)
    return {"active_workspaces": row["count"]}



@app.post("/support/chat")
async def support_chat(payload: ChatRequest):
    """
    AI support endpoint.

    - Answers only questions about xCommand Cloud: plans, payments, workspaces, expiry, provisioning,
      troubleshooting, and n8n workflow basics.
    """

    # ------------------- 1) SYSTEM PROMPT -------------------------------------
    system_prompt = {
        "role": "system",
        "content": (
            "You are the xCommand Cloud AI support assistant.\n\n"
            "Product:\n"
            "- xCommand Cloud rents short-lived n8n automation workspaces ('containers' or 'workspaces')\n"
            "  on plans such as 24-hour and 5-Day.\n"
            "- Users pay via Stripe checkout and then receive an email with their workspace URL.\n"
            "- Workspaces are ephemeral: after expiry the container is stopped and wiped.\n\n"
            "Personality and style (Hybrid):\n"
            "- Friendly but professional.\n"
            "- Clear, simple, and structured.\n"
            "- Prefer short lists or 2–5 sentences.\n"
            "- Never use marketing tone or long paragraphs.\n\n"
            "Issue type behavior:\n"
            "- workspace_access: troubleshooting 4xx/5xx errors, wrong links, not loading.\n"
            "- expiry: remaining time, deletion rules, how expiry works.\n"
            "- workflow_export: exporting/importing JSON.\n"
            "- billing: duplicate charges, payment issues.\n"
            "- general: anything else about xCommand Cloud.\n\n"
            "Rules:\n"
            "- Always stay inside the xCommand Cloud domain.\n"
            "- If asked something unrelated (health, generic coding, etc.) decline politely.\n"
            "- When giving steps, be short and actionable.\n"
            "- Never invent policies or features not in the knowledge base.\n"
        ),
    }

    # ------------------- 2) KNOWLEDGE BASE PROMPT -----------------------------
    knowledge_prompt = {
        "role": "system",
        "content": (
            "Here is the xCommand Cloud product knowledge base. "
            "Use it as the source of truth:\n\n"
            f"{XCOMMAND_KNOWLEDGE or '[knowledge file not loaded]'}"
        ),
    }

    # ------------------- 3) EMAIL EXTRACTION ----------------------------------
    user_email = extract_email_from_messages(payload.messages)

    if user_email:
        email_context = {
            "role": "system",
            "content": (
                f"The user's email appears to be: {user_email}. "
                "Use this email when answering. Do NOT ask them to repeat it unless truly needed."
            )
        }
    else:
        email_context = {
            "role": "system",
            "content": (
                "No email detected yet. If the question involves payments or workspace access, "
                "ask for the checkout email."
            )
        }

    # ------------------- 4) WORKSPACE LOOKUP ----------------------------------
    # Helper function to query DB
    def lookup_latest_workspace(email: str):
        try:
            rows = fetch_all(
                """
                select
                  plan,
                  status,
                  fqdn,
                  expires_at,
                  created_at
                from workspaces
                where email = %s
                  and status <> 'deleted'
                order by created_at desc
                limit 1
                """,
                (email,),
            )
        except Exception:
            return None

        if not rows:
            return None
        return rows[0]

    # Build workspace context
    if user_email:
        ws = lookup_latest_workspace(user_email)
        if ws:
            plan = ws.get("plan")
            status = ws.get("status")
            fqdn = ws.get("fqdn")
            expires_at = ws.get("expires_at")
            created_at = ws.get("created_at")

            # Convert datetimes safely
            def dt(x):
                if isinstance(x, datetime):
                    return x.astimezone(timezone.utc).isoformat()
                return str(x)

            workspace_context = {
                "role": "system",
                "content": (
                    "Workspace lookup result:\n"
                    f"- plan: {plan}\n"
                    f"- status: {status}\n"
                    f"- url: {fqdn}\n"
                    f"- created_at: {dt(created_at)} (UTC)\n"
                    f"- expires_at: {dt(expires_at)} (UTC)\n\n"
                    "Use this information when answering. "
                    "If status='active' and user reports 502/504, explain likely causes. "
                    "If expired or near expiry, explain expiry rules. "
                    "If no workspace should exist yet, explain provisioning delay."
                )
            }
        else:
            workspace_context = {
                "role": "system",
                "content": (
                    f"No active workspace found for {user_email}. "
                    "If the user claims they paid, ask for plan type and payment time, "
                    "and instruct them what to send to human support."
                )
            }
    else:
        workspace_context = {
            "role": "system",
            "content": (
                "Workspace lookup skipped because no email has been identified yet."
            )
        }

    # ------------------- 5) FINAL MESSAGE LIST --------------------------------
    messages = [
        system_prompt,
        knowledge_prompt,
        email_context,
        workspace_context,
    ]

    # Append user + assistant history
    for msg in payload.messages:
        messages.append({"role": msg.role, "content": msg.content})

    # ------------------- 6) CALL OPENAI ---------------------------------------
    try:
        reply = chat_with_openai(messages)
        return {"reply": reply}
    except Exception as e:
        print("OpenAI error:", str(e))
        return {"error": "openai_failure"}