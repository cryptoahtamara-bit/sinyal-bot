
import os
import requests
from flask import Flask, request, jsonify

# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

# =========================================================
# PROXY SETTINGS
# =========================================================

PROXY_ENABLED = os.getenv("PROXY_ENABLED", "true").lower() == "true"

PROXY_URL = os.getenv(
    "PROXY_URL",
    "http://username:password@gateway.webshare.io:80"
)

# =========================================================
# REQUEST SESSION
# =========================================================

session = requests.Session()

if PROXY_ENABLED:

    proxies = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }

    session.proxies.update(proxies)

    print("[PROXY] Enabled")

else:

    print("[PROXY] Disabled")

# =========================================================
# HEALTHCHECK
# =========================================================

@app.route("/")
def home():
    return "Bot running", 200

# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    print(f"[WEBHOOK] {data}")

    return jsonify({
        "success": True
    })

# =========================================================
# MEXC REQUEST
# =========================================================

def mexc_post(url, headers=None, body=None):

    try:

        response = session.post(
            url,
            headers=headers,
            data=body,
            timeout=20
        )

        print(f"[MEXC] STATUS => {response.status_code}")
        print(f"[MEXC] RAW RESPONSE => {response.text}")

        return response

    except Exception as e:

        print(f"[ERROR] {e}")

        return None

# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    port = int(os.getenv("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
