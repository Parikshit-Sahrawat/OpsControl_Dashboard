"""Collector credential resolution.

Production accepts only AWS Secrets Manager exact ARN references through
workload identity. Development may opt into environment-backed references.
Never log secret values or expose provider errors to the API.
"""
import json
import os
import re

class CredentialProviderError(RuntimeError):
    pass

_REGION=re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
_SECRET_ARN=re.compile(
    r"^arn:aws(?:-us-gov)?:secretsmanager:(?P<region>[a-z0-9-]+):"
    r"(?P<account>\d{12}):secret:[A-Za-z0-9/_+=.@-]{1,250}$"
)

def resolve_basic_auth(credential_ref: str,client_factory=None) -> tuple[str,str]:
    if not isinstance(credential_ref,str) or not credential_ref or len(credential_ref)>350:
        raise CredentialProviderError("Valid credential reference required")
    if credential_ref.startswith("aws-secretsmanager://"):
        rest=credential_ref.removeprefix("aws-secretsmanager://")
        try:region,arn=rest.split("/",1)
        except ValueError:raise CredentialProviderError("Invalid Secrets Manager reference") from None
        match=_SECRET_ARN.fullmatch(arn)
        if not match or not _REGION.fullmatch(region) or match["region"]!=region:
            raise CredentialProviderError("Secrets Manager ARN/region mismatch")
        if client_factory is None:
            try:
                import boto3
            except ImportError as exc:
                raise CredentialProviderError("Optional AWS provider dependencies required") from exc
            client_factory=lambda requested_region:boto3.client("secretsmanager",region_name=requested_region)
        try:
            result=client_factory(region).get_secret_value(SecretId=arn)
            secret=result.get("SecretString")
            payload=json.loads(secret) if isinstance(secret,str) else None
        except Exception as exc:
            raise CredentialProviderError("Secrets Manager credential retrieval failed") from exc
        if not isinstance(payload,dict):
            raise CredentialProviderError("Secret must be a JSON credential object")
        username,password=payload.get("username"),payload.get("password")
    else:
        if os.getenv("ENVIRONMENT","development").lower()=="production":
            raise CredentialProviderError("Production forbids environment-backed collector credentials")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",credential_ref):
            raise CredentialProviderError("Invalid development credential reference")
        normalized=re.sub(r"[^A-Za-z0-9]","_",credential_ref).upper()
        prefix=f"OPSCONTROL_CREDENTIAL_{normalized}"
        username=os.getenv(f"{prefix}_USERNAME")
        password=os.getenv(f"{prefix}_PASSWORD")
    if not isinstance(username,str) or not username or not isinstance(password,str) or not password:
        raise CredentialProviderError("Credential reference has incomplete account/password fields")
    if len(username)>256 or len(password)>2048 or any(ord(ch)<32 for ch in username):
        raise CredentialProviderError("Invalid credential encoding")
    return username,password
