"""Password hashing with stdlib PBKDF2-HMAC-SHA256 and constant-time compare."""
import base64
import hashlib
import hmac
import os

_ITERATIONS = 600_000

def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 1024:
        raise ValueError("Password must be between 12 and 1024 characters")
    salt = os.urandom(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (_ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt, digest = stored.split("$")
        if scheme != "pbkdf2_sha256" or int(rounds) < 200_000:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(candidate, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False
