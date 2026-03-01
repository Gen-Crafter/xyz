FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /proxy

RUN pip install mitmproxy==11.1.0 httpx==0.28.1

COPY mitm_addon.py .

EXPOSE 8080

# Run mitmdump (headless mitmproxy) with the governance addon
# TLSFilter addon in mitm_addon.py handles selective interception:
#   - AI domains (chatgpt.com, api.openai.com, etc.) → MITM intercepted + scanned
#   - All other domains → tunneled through as-is (no cert issues)
CMD ["mitmdump", "-s", "mitm_addon.py", "--listen-port", "8080", "--set", "api_url=http://api:8000"]
