from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
import json
import urllib.request
import urllib.parse
import os  # NEW

app = FastAPI()

API_BASE = "http://api:8001"

# NEW: use the same base domain everywhere
WORKSPACE_BASE_DOMAIN = os.getenv("WORKSPACE_BASE_DOMAIN", "xcommand.cloud")


@app.get("/", response_class=HTMLResponse)
def landing():
    # Serve your futuristic landing page from index.html
    return FileResponse("index.html")


@app.get("/pay.html", response_class=HTMLResponse)
def pay_page():
    return FileResponse("pay.html")


@app.get("/ready.html", response_class=HTMLResponse)
def ready_page():
    return FileResponse("ready.html")


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/support", response_class=HTMLResponse)
def support_page():
    return FileResponse("support.html")


from fastapi.responses import JSONResponse


@app.post("/support/chat")
async def support_chat_proxy(request: Request):
    """
    Proxy endpoint for the support chat.

    Browser -> app.xcommand.cloud/support/chat
            -> web container
            -> forwards JSON to api:8001/support/chat inside Docker network
    """
    body = await request.body()

    url = f"{API_BASE}/support/chat"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read()
            status = resp.getcode()
    except Exception as e:
        print("support_chat_proxy error:", e)
        return JSONResponse({"error": "proxy_failure"}, status_code=502)

    try:
        data = json.loads(resp_body.decode("utf-8"))
    except Exception:
        # If API returned non-JSON for some reason
        return JSONResponse({"error": "invalid_response_from_api"}, status_code=502)

    return JSONResponse(data, status_code=status)


@app.get("/workspace", response_class=HTMLResponse)
def workspace(email: str):
    # call API: /workspaces/all-by-email/{email}
    encoded_email = urllib.parse.quote(email, safe="")
    url = f"{API_BASE}/workspaces/all-by-email/{encoded_email}"

    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
    except Exception as e:
        return HTMLResponse(
            f"""
            <html>
              <body style="font-family: system-ui; max-width: 720px; margin: 40px auto;">
                <h1>Workspace lookup failed</h1>
                <p>Could not contact API: {e}</p>
                <p><a href="/">Go back</a></p>
              </body>
            </html>
            """,
            status_code=500,
        )

    workspaces = data.get("workspaces") or []

    if not data.get("ok") or not workspaces:
        return HTMLResponse(
            """
            <html>
              <body style="font-family: system-ui; max-width: 720px; margin: 40px auto;">
                <h1>No workspace found</h1>
                <p>We couldn't find any active workspaces for that email.</p>
                <p>Make sure you completed checkout using this email.</p>
                <p><a href="/">Go back</a></p>
              </body>
            </html>
            """,
            status_code=404,
        )

    cards_html = ""
    for ws in workspaces:
        status = ws.get("status", "unknown")
        expires = ws.get("expires_at", "unknown")
        subdomain = ws.get("subdomain", "")
        plan = ws.get("plan", "?")

        # Always build HTTPS URL from subdomain + base domain
        if subdomain:
            ws_url = f"https://{subdomain}.{WORKSPACE_BASE_DOMAIN}"
        else:
            ws_url = ws.get("fqdn", "#")

        cards_html += f"""
        <div style="border-radius: 14px; padding: 16px 20px; margin-bottom: 16px;
                    background: #020617; border: 1px solid #1f2937;">
          <p><strong>Workspace ID:</strong> {subdomain}</p>
          <p><strong>Plan:</strong> {plan}</p>
          <p><strong>Status:</strong> {status}</p>
          <p><strong>Expires at (UTC):</strong> {expires}</p>

          <p style="margin-top: 10px;">
            <a href="{ws_url}" target="_blank" rel="noopener"
               style="padding: 8px 16px; background: #22c55e; color: white;
                      text-decoration: none; border-radius: 999px; font-size: 14px;">
              Open this workspace
            </a>
          </p>
          <p style="margin-top: 4px; font-size: 12px; color: #9ca3af;">
            URL: <code style="font-size: 12px;">{ws_url}</code>
          </p>
        </div>
        """

    count = len(workspaces)
    count_text = (
        "You currently have 1 active workspace."
        if count == 1
        else f"You currently have {count} active workspaces."
    )

    html = f"""
    <html>
      <head><title>Your n8n workspaces</title></head>
      <body style="font-family: system-ui; max-width: 720px; margin: 40px auto; line-height: 1.5; color: #e5e7eb; background:#020617;">
        <h1>Your n8n workspaces</h1>

        <p><strong>Email:</strong> {email}</p>
        <p>{count_text}</p>

        <hr style="margin: 24px 0; border-color:#1f2937;" />

        {cards_html}

        <h3 style="margin-top: 32px;">What to expect</h3>
        <ul>
          <li><strong>First time:</strong> n8n may show a “Set up owner account” screen. Create your account once.</li>
          <li><strong>After that:</strong> opening from <em>Find my workspace</em> will jump straight into that workspace.</li>
          <li><strong>When it expires:</strong> the workspace container is stopped, data is wiped, and it disappears from this list.</li>
        </ul>

        <p style="margin-top: 32px;">
          <a href="/" style="color:#60a5fa;">Back to landing</a>
        </p>
      </body>
    </html>
    """

    return HTMLResponse(html)


    ws = data["workspace"]
    status = ws.get("status", "unknown")
    expires = ws.get("expires_at", "unknown")
    subdomain = ws.get("subdomain", "")

    # 🔑 KEY CHANGE:
    # Always build a secure HTTPS URL from subdomain + base domain.
    # Ignore any IP:port fqdn in the DB.
    if subdomain:
        ws_url = f"https://{subdomain}.{WORKSPACE_BASE_DOMAIN}"
    else:
        # fallback to whatever API sent, just in case
        ws_url = ws.get("fqdn", "#")

    return f"""
    <html>
      <head><title>Your n8n Workspace</title></head>
      <body style="font-family: system-ui; max-width: 720px; margin: 40px auto; line-height: 1.5;">
        <h1>Your n8n Workspace</h1>

        <p><strong>Email:</strong> {email}</p>
        <p><strong>Workspace ID:</strong> {subdomain}</p>
        <p><strong>Status:</strong> {status}</p>
        <p><strong>Expires at (UTC):</strong> {expires}</p>

        <hr style="margin: 24px 0;" />

        <h2>Open your workspace</h2>
        <p>
          <a href="{ws_url}" target="_blank" rel="noopener"
             style="padding: 10px 20px; background: #2563eb; color: white; text-decoration: none; border-radius: 4px;">
            Launch n8n workspace
          </a>
        </p>
        <p style="margin-top: 8px;">
          If the button doesn't work, you can copy and paste this URL into a new tab:<br>
          <code>{ws_url}</code>
        </p>

        <h3 style="margin-top: 32px;">What to expect</h3>
        <ul>
          <li><strong>First time:</strong> n8n may show a “Set up owner account” screen. Create your account once.</li>
          <li><strong>After that:</strong> opening this page and clicking <em>Launch n8n workspace</em> should jump straight into your workflows.</li>
          <li><strong>When it expires:</strong> the workspace container is stopped and all data is wiped automatically.</li>
        </ul>

        <p style="margin-top: 32px;">
          <a href="/">Back to landing</a>
        </p>
      </body>
    </html>
    """
