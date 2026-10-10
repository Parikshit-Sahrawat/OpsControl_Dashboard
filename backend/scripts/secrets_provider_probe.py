"""Offline scoped secret-provider acceptance; validates no credential leakage."""
import os
from app.worker.credentials import resolve_basic_auth,CredentialProviderError
def denied(fn):
    try:fn()
    except CredentialProviderError:return
    raise AssertionError("Credential policy unexpectedly permitted the request")
class FakeSecrets:
    def __init__(self,region):assert region=="ap-south-1"
    def get_secret_value(self,SecretId):
        assert SecretId=="arn:aws:secretsmanager:ap-south-1:123456789012:secret:opscontrol/read-only-demo"
        return {"SecretString":'{"username":"read-only-monitor","password":"synthetic-private-value"}'}
def main():
    reference="aws-secretsmanager://ap-south-1/arn:aws:secretsmanager:ap-south-1:123456789012:secret:opscontrol/read-only-demo"
    assert resolve_basic_auth(reference,FakeSecrets)==("read-only-monitor","synthetic-private-value")
    denied(lambda:resolve_basic_auth(reference.replace("ap-south-1/arn","us-east-1/arn"),FakeSecrets))
    denied(lambda:resolve_basic_auth("aws-secretsmanager://ap-south-1/http://169.254.169.254",FakeSecrets))
    old=os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"]="production"
    try:
        os.environ["OPSCONTROL_CREDENTIAL_SYNTHETIC_USERNAME"]="read-only-monitor"
        os.environ["OPSCONTROL_CREDENTIAL_SYNTHETIC_PASSWORD"]="synthetic-private-value"
        denied(lambda:resolve_basic_auth("synthetic"))
    finally:
        if old is None:os.environ.pop("ENVIRONMENT",None)
        else:os.environ["ENVIRONMENT"]=old
        os.environ.pop("OPSCONTROL_CREDENTIAL_SYNTHETIC_USERNAME",None)
        os.environ.pop("OPSCONTROL_CREDENTIAL_SYNTHETIC_PASSWORD",None)
    print("SECRETS MANAGER SCOPED REFERENCE AND PRODUCTION ENV DENY TESTS PASS")
if __name__=="__main__":main()
