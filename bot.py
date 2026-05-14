import os
import requests

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
# MEXC REQUEST EXAMPLE
# =========================================================

def mexc_post(url, headers, body):

    response = session.post(
        url,
        headers=headers,
        data=body,
        timeout=20
    )

    print(f"[MEXC] STATUS => {response.status_code}")
    print(f"[MEXC] RAW RESPONSE => {response.text}")

    return response

# =========================================================
# ENV VARIABLES
# =========================================================
#
# PROXY_ENABLED=true
# PROXY_URL=http://username:password@gateway.webshare.io:80
#
# =========================================================
