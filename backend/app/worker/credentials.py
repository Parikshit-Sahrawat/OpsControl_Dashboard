"""Local credential resolver for collector development.

Production deployments should replace this with a managed secret provider.
Collector configuration stores only a credential_ref, never the password.
"""

import os
import re


class CredentialProviderError(RuntimeError):
    pass


def resolve_basic_auth(credential_ref: str) -> tuple[str, str]:
    if not credential_ref:
        raise CredentialProviderError("credential_ref is required")

    normalized = re.sub(r"[^A-Za-z0-9]", "_", credential_ref).upper()
    prefix = f"OPSCONTROL_CREDENTIAL_{normalized}"
    username = os.getenv(f"{prefix}_USERNAME")
    password = os.getenv(f"{prefix}_PASSWORD")

    if username is None or password is None:
        raise CredentialProviderError(
            f"Managed credential '{credential_ref}' is not available to the collector worker"
        )
    return username, password
