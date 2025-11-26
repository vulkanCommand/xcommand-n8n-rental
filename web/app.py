from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import json
import urllib.request
import urllib.parse
import os

app = FastAPI()

API_BASE = "http://api:8001"
WORKSPACE_BASE_DOMAIN = os.getenv("WORKSPACE_BASE_DOMAIN", "xcommand.cloud")


@app.get("/", response_class=HTMLResponse)
def landing():
    # Static landing page
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


@app.get("/workspace", response_class=HTMLResponse)
def workspace(email: str):
    """
    Look up ALL active workspaces for this email.
    This is what the 'Find my workspace' button should use.
    """
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

        # Build canonical https URL from subdomain + base domain
        if subdomain:
            ws_url = f"https://{subdomain}.{WORKSPACE_BASE_DOMAIN}"
        else:
            ws_url = ws.get("fqdn", "#")

        cards_html += f"""
        <section style="border-radius: 16px; padding: 18px 20px; margin-bottom: 18px;
                        background: #020617; border: 1px solid #1f2937;">
          <p><strong>Workspace ID:</strong> {subdomain}</p>
          <p><strong>Plan:</strong> {plan}</p>
          <p><strong>Status:</strong> {status}</p>
          <p><strong>Expires at (UTC):</strong> {expires}</p>

          <p style="margin-top: 10px;">
            <a href="{ws_url}" target="_blank" rel="noopener"
               style="padding: 9px 18px; background: #22c55e; color: white;
                      text-decoration: none; border-radius: 999px; font-size: 14px;">
              Open this workspace
            </a>
          </p>
          <p style="margin-top: 4px; font-size: 12px; color: #9ca3af;">
            URL: <code style="font-size: 12px;">{ws_url}</code>
          </p>
        </section>
        """

    count = len(workspaces)
    if count == 1:
        count_text = "You currently have 1 active workspace."
    else:
        count_text = f"You currently have {count} active workspaces."

    html = f"""
    <html>
      <head>
        <title>Your n8n workspaces</title>
      </head>
      <body style="font-family: system-ui; max-width: 720px; margin: 40px auto; line-height: 1.5; color: #e5e7eb; background:#020617;">
        <h1 style="margin-bottom: 4px;">Your n8n workspaces</h1>
        <p><strong>Email:</strong> {email}</p>
        <p>{count_text}</p>

        <hr style="margin: 24px 0; border-color:#1f2937;" />

        {cards_html}

        <h3 style="margin-top: 32px;">What to expect</h3>
        <ul>
          <li><strong>First time:</strong> n8n may show a “Set up owner account” screen. Create your account once.</li>
          <li><strong>Later:</strong> opening from <em>Find my workspace</em> jumps into that workspace.</li>
          <li><strong>When it expires:</strong> the workspace container is stopped, data is wiped, and it disappears from this list.</li>
        </ul>

        <p style="margin-top: 32px;">
          <a href="/" style="color:#60a5fa;">Back to landing</a>
        </p>
      </body>
    </html>
    """

    return HTMLResponse(html)
