"""Supported API entrypoint: explicit proxy trust, no wildcard forwarded headers."""
import uvicorn
from app.core.config import settings
from app.security.deployment import trusted_proxies

def main():
    allowed = trusted_proxies(settings.trusted_proxy_ips) if settings.environment == "production" else (
        trusted_proxies(settings.trusted_proxy_ips) if settings.trusted_proxy_ips else "127.0.0.1")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000,
                proxy_headers=True, forwarded_allow_ips=allowed, access_log=False)

if __name__ == "__main__":
    main()
