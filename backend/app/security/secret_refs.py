"""Reject embedded credentials in user-configurable collector/template JSON.

Only opaque references to an operator-managed secret provider may be configured.
Existing stored values are recursively redacted on serialization, but must still
be rotated and migrated before production. This is not a secret-store implementation.
"""
from urllib.parse import urlsplit

_SECRET_KEYS = {
    "password", "passwd", "pwd", "secret", "token", "access_token",
    "refresh_token", "api_key", "apikey", "private_key", "client_secret",
    "authorization", "proxy_authorization", "cookie", "set_cookie",
    "bearer_token", "credential", "credentials", "aws_secret_access_key",
}
_ALLOWED_REFERENCES = {"credential_ref", "secret_ref", "token_ref", "key_ref", "password_ref"}

def is_secret_field(name):
    normalized = str(name).lower().replace("-", "_").replace(" ", "_")
    if normalized in _ALLOWED_REFERENCES or normalized.endswith("_ref"):
        return False
    if normalized in _SECRET_KEYS:
        return True
    return normalized.endswith(("_password", "_secret", "_token", "_api_key", "_private_key"))

def _unsafe_url(text):
    if not isinstance(text, str):
        return False
    if not text.startswith(("http://", "https://")):
        return False
    parts = urlsplit(text)
    return parts.username is not None or parts.password is not None

def require_safe_config(value):
    if value is None:
        return value
    if not isinstance(value, dict):
        raise ValueError("Configuration must be a JSON object")
    def check(item, depth=0):
        if depth > 20:
            raise ValueError("Configuration nesting exceeds security limit")
        if isinstance(item, dict):
            for k,v in item.items():
                if is_secret_field(k):
                    raise ValueError("Embedded credentials are forbidden. Use a secret reference")
                check(v, depth+1)
        elif isinstance(item, list):
            if len(item) > 1000:
                raise ValueError("Configuration list exceeds size limit")
            for sub in item: check(sub,depth+1)
        elif _unsafe_url(item):
            raise ValueError("Credentials must not appear in URLs")
    check(value)
    return value

def redact_config(value):
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if is_secret_field(key) else redact_config(sub))
                for key,sub in value.items()}
    if isinstance(value, list):
        return [redact_config(item) for item in value]
    if _unsafe_url(value):
        return "[REDACTED_URL_WITH_CREDENTIALS]"
    return value

def require_safe_url(value):
    if value is not None and _unsafe_url(value):
        raise ValueError("URL must not contain embedded credentials")
    return value

def redact_url(value):
    return "[REDACTED_URL_WITH_CREDENTIALS]" if _unsafe_url(value) else value
