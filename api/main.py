import json
import os
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
    Return all non-deleted workspaces for this email, newest first.
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


@app.post("/support/chat")
async def support_chat(payload: ChatRequest):
    """
    AI support endpoint.

    - Only answers questions about xCommand Cloud:
      plans, payments, workspaces, n8n usage inside the platform,
      expiry rules, and troubleshooting.
    - Politely declines anything outside this scope.
    """
    system_prompt = {
        "role": "system",
        "content": (
            "You are the xCommand Cloud AI support assistant.\n\n"
            "Product:\n"
            "- xCommand Cloud rents short-lived n8n automation workspaces ('containers' or 'workspaces')\n"
            "  on plans such as 24-hour and 5-Day.\n"
            "- Users pay via Stripe checkout and then receive an email with their workspace URL.\n"
            "- Workspaces are ephemeral: after expiry the container is stopped and wiped, so users must\n"
            "  export their flows as JSON if they want to keep them.\n\n"
            "Scope:\n"
            "- Answer ONLY questions about xCommand Cloud, its plans, workspaces, Stripe payments for\n"
            "  xCommand Cloud, and basic n8n workflow questions that are covered by the knowledge base.\n"
            "- If the user asks about topics unrelated to xCommand Cloud (health, generic coding, other\n"
            "  products), politely say you only handle xCommand Cloud support and redirect them.\n\n"
            "Personality and style (Option 4 hybrid):\n"
            "- Friendly but professional.\n"
            "- Use clear, simple language.\n"
            "- Prefer 2–5 short sentences or a short bulleted list, not a giant wall of text.\n"
            "- Be structured and actionable: always give concrete next steps.\n"
            "- Do not write marketing fluff; sound like a helpful support engineer.\n\n"
            "Issue types and behaviour:\n"
            "First, internally decide which category the current problem fits:\n"
            "- 'workspace_access': cannot open workspace, link not working, 4xx/5xx errors, login issues.\n"
            "- 'expiry': when the plan ends, container deletion, extending time, buying a new plan.\n"
            "- 'workflow_export': exporting/importing JSON, backing up flows before deletion,\n"
            "   moving flows to the user's own n8n instance.\n"
            "- 'billing': payment failed, duplicate charge, refund, invoice/receipt, card issues.\n"
            "- 'general': anything else about how xCommand Cloud works.\n\n"
            "Then respond according to the category:\n"
            "- For workspace_access:\n"
            "  * Ask for: email used at checkout, plan type (24-hour vs 5-Day), and approximate purchase time.\n"
            "  * Suggest 1–3 precise checks (correct link, email spam/junk, waiting a few minutes after payment, etc.).\n"
            "  * If it clearly needs a human, provide the support email and list exactly what details they should send.\n"
            "- For expiry:\n"
            "  * Explain simply how expiry is calculated based on the plan.\n"
            "  * Explain what the user should assume about remaining time if there is no exact timer available.\n"
            "  * Remind them to export workflows before expiry and, if needed, give brief export steps.\n"
            "- For workflow_export:\n"
            "  * Give step-by-step instructions for exporting an n8n workflow as JSON.\n"
            "  * Briefly explain how to import that JSON into another n8n instance later.\n"
            "  * Emphasise that flows are deleted after the container is cleaned up.\n"
            "- For billing:\n"
            "  * Be conservative: never guess about money or promise refunds.\n"
            "  * Explain what the AI can and cannot do for billing.\n"
            "  * Direct them to the billing/support email with a short checklist of what to include\n"
            "    (email used for payment, plan type, date/time of payment, and any Stripe receipt/ID).\n"
            "- For general:\n"
            "  * Answer from the xCommand Cloud knowledge base.\n"
            "  * Keep the answer focused and avoid going off-topic.\n\n"
            "Always:\n"
            "- If you ask the user to email support, keep it to one short paragraph and a bullet list\n"
            "  of details they should include.\n"
            "- Never invent policies, features, or promises that are not supported by the knowledge base.\n"
        ),
    }


    knowledge_prompt = {
        "role": "system",
        "content": (
            "Here is your product knowledge base for xCommand Cloud. "
            "Use it as the source of truth when possible:\n\n"
            f"{XCOMMAND_KNOWLEDGE or '[knowledge file not loaded]'}"
        ),
    }

    messages = [system_prompt, knowledge_prompt]

    for msg in payload.messages:
        messages.append({"role": msg.role, "content": msg.content})

    try:
        reply = chat_with_openai(messages)
        return {"reply": reply}
    except Exception as e:
        print("OpenAI error:", str(e))
        return {"error": "openai_failure"}
