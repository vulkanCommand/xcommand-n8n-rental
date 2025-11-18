from fastapi.middleware.cors import CORSMiddleware
import stripe
import json, os, secrets
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from db import fetch_all, execute
from provisioner import start_n8n_local, stop_container, remove_volume

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # later we can restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def provision_core(email: str, plan: str):
    # validate plan
    if plan not in ("1d", "5d"):
        raise ValueError("plan must be '1d' or '5d'")

    # duration
    days = 1 if plan == "1d" else 5

    # random workspace subdomain like u-3d83d4
    sub = f"u-{secrets.token_hex(3)}"

    # root domain for dev vs prod
    root = os.getenv("N8N_ROOT_DOMAIN", "localhost")
    fqdn = f"{sub}.{root}" if root != "localhost" else f"{sub}.localhost"

    # timezone-aware UTC expiry
    expires_dt = datetime.now(timezone.utc) + timedelta(days=days)
    expires_iso = expires_dt.isoformat()

    # container + volume names
    container_name = f"n8n_{sub}"
    volume_name = f"n8n_{sub}_data"

    # ensure app_users row exists (idempotent)
    execute(
        """
        insert into app_users (email)
        values (%s)
        on conflict (email) do nothing
        """,
        (email,),
    )

    # record a fake payment (dev only)
    amount_cents = 99 if days == 1 else 300
    execute(
        """
        insert into payments (stripe_session_id, email, plan, amount_cents)
        values (%s, %s, %s, %s)
        on conflict (stripe_session_id) do nothing
        """,
        (f"test_{secrets.token_hex(6)}", email, plan, amount_cents),
    )

    # create workspace row
    # create workspace row
    # create workspace row
    execute(
        """
        insert into workspaces (email, plan, subdomain, fqdn, container_name, volume_name, status, expires_at)
        values (%s, %s, %s, %s, %s, %s, 'provisioning', %s)
        """,
        (email, plan, sub, fqdn, container_name, volume_name, expires_dt),
    )



    # boot local n8n with explicit expires_at for janitor label
    host_port = start_n8n_local(
        container_name=container_name,
        volume_name=volume_name,
        encryption_key=os.getenv("ENCRYPTION_KEY", "devkey"),
        expires_at=expires_iso,
    )

    public_host = os.getenv("PUBLIC_WORKSPACE_HOST", "xcommand.cloud")
    url = f"http://{public_host}:{host_port}"


    # mark active and store url
    execute(
        "update workspaces set status='active', fqdn=%s where subdomain=%s",
        (url, sub),
    )

    # return the workspace row
    rows = fetch_all(
        "select id, email, subdomain, fqdn, status, expires_at, created_at from workspaces where subdomain=%s",
        (sub,),
    )
    if not rows:
        raise RuntimeError("workspace row not found after insert")
    return rows[0]





@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "api",
        "domain": os.getenv("N8N_ROOT_DOMAIN", "unset"),
    }


class ProvisionRequest(BaseModel):
    email: EmailStr
    plan: str  # '1d' or '5d'


@app.post("/provision/test")
def provision_test(req: ProvisionRequest):
    try:
        row = provision_core(req.email, req.plan)
        return JSONResponse(jsonable_encoder(row))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/workspaces/{sub}/stop")
def stop_workspace(sub: str = Path(..., pattern=r"^u-[0-9a-f]{6}$")):
    rows = fetch_all(
        "select container_name from workspaces where subdomain=%s", (sub,)
    )
    if not rows:
        raise HTTPException(404, "workspace not found")
    container_name = rows[0]["container_name"]
    stopped = stop_container(container_name)
    execute("update workspaces set status='stopping' where subdomain=%s", (sub,))
    return {"ok": True, "stopped": stopped}


@app.post("/workspaces/{sub}/wipe")
def wipe_workspace(sub: str = Path(..., pattern=r"^u-[0-9a-f]{6}$")):
    rows = fetch_all(
        "select volume_name from workspaces where subdomain=%s", (sub,)
    )
    if not rows:
        raise HTTPException(404, "workspace not found")
    volume_name = rows[0]["volume_name"]
    wiped = remove_volume(volume_name)
    execute("update workspaces set status='deleted' where subdomain=%s", (sub,))
    return {"ok": True, "wiped": wiped}


@app.post("/provision/simulate")
def provision_simulate(req: ProvisionRequest):
    try:
        row = provision_core(req.email, req.plan)
        return JSONResponse(jsonable_encoder(row))
    except Exception as e:
        raise HTTPException(400, str(e))

class CheckoutRequest(BaseModel):
    email: EmailStr
    plan: str                  # "1d" or "5d"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@app.post("/stripe/create-checkout-session")
async def create_checkout_session(req: CheckoutRequest):
    stripe.api_key = os.getenv("STRIPE_SECRET")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe secret not configured")

    # basic plan validation
    if req.plan not in ("1d", "5d"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    # amounts in cents
    amount_map = {
        "1d": 100,   # $1
        "5d": 300,   # $3
    }
    label_map = {
        "1d": "xCommand 24h n8n workspace",
        "5d": "xCommand 5-day n8n workspace",
    }

    amount = amount_map[req.plan]

    # Always use HTTPS URLs that Stripe accepts (ignore file:// from frontend)
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
