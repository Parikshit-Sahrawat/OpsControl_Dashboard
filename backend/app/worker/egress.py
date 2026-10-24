"""Strict outbound HTTPS probes with DNS/IP validation and connection pinning.

Cannot replace network-layer egress firewall. Private IPs are allowed only
when explicitly listed in the worker's organization-scoped CIDR policy.
"""
import http.client
import ipaddress
import socket
import ssl
import time
import base64
import os
from urllib.parse import urlsplit

class EgressDenied(ValueError): pass

def policy_hosts(hosts):
    if not isinstance(hosts,list) or not hosts or len(hosts)>64: raise EgressDenied("Approved hostname list required (max 64)")
    result=[]
    for host in hosts:
        if not isinstance(host,str) or len(host)>253 or not host or host.lower()!=host or any(x in host for x in "/:@*%?# "):
            raise EgressDenied("Invalid exact hostname")
        if host=="localhost" or host.endswith(".localhost") or not all(label and len(label)<=63 and label[0].isalnum() and label[-1].isalnum() and all(ch.isalnum() or ch=="-" for ch in label) for label in host.split(".")):
            raise EgressDenied("Invalid approved hostname")
        result.append(host)
    return result

def policy_cidrs(cidrs):
    if not isinstance(cidrs,list) or not cidrs or len(cidrs)>32: raise EgressDenied("Approved CIDR list required (max 32)")
    result=[]
    for cidr in cidrs:
        try:
            if not isinstance(cidr,str) or "/" not in cidr: raise ValueError()
            net=ipaddress.ip_network(cidr,strict=True)
        except ValueError as exc: raise EgressDenied("Invalid network CIDR") from exc
        # Explicit private LAN CIDRs are valid, but metadata/link-local/
        # loopback are NEVER reachable even with a permissive customer policy.
        if net.prefixlen < (8 if net.version==4 else 32):
            raise EgressDenied("Network allowlist range is excessively broad")
        if net.is_loopback or net.is_link_local or net.is_multicast or net.is_unspecified:
            raise EgressDenied("Forbidden network range")
        result.append(net)
    return result

def validate_ip(value, cidrs):
    try: ip=ipaddress.ip_address(value.split("%")[0])
    except ValueError as exc: raise EgressDenied("Invalid DNS answer") from exc
    if isinstance(ip,ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip=ip.ipv4_mapped
    # Deny metadata and link-local regardless of configured ranges.
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        raise EgressDenied("DNS answer has forbidden address class")
    if str(ip) in {"169.254.169.254","169.254.170.2","100.100.100.200"}:
        raise EgressDenied("Cloud metadata endpoint denied")
    if not any(ip in net for net in cidrs):
        raise EgressDenied("DNS answer outside approved network policy")
    return ip

def check_target(url, hosts, cidrs):
    if not isinstance(url,str) or not url.isascii() or any(ord(ch)<33 or ord(ch)>126 for ch in url):
        raise EgressDenied("URL contains unsafe characters")
    try: parts=urlsplit(url)
    except ValueError as exc: raise EgressDenied("Invalid target URL") from exc
    if parts.scheme!="https" or parts.username is not None or parts.password is not None:
        raise EgressDenied("Only HTTPS without URL credentials is supported")
    if parts.fragment or parts.query: raise EgressDenied("Query parameters and fragments are not allowed in probe targets")
    try: port=parts.port
    except ValueError as exc: raise EgressDenied("Invalid port") from exc
    if port not in (None,443): raise EgressDenied("Only TLS port 443 is allowed")
    host=parts.hostname
    if host not in policy_hosts(hosts): raise EgressDenied("Target hostname is not approved")
    networks=policy_cidrs(cidrs)
    if host is None: raise EgressDenied("Missing hostname")
    if len(url)>2048: raise EgressDenied("URL exceeds limit")
    path=parts.path or "/"
    if not path.isascii() or any(ord(ch)<33 or ord(ch)>126 for ch in path):
        raise EgressDenied("Target path contains unsafe characters")
    return parts, networks

def resolve_target(host, networks, resolver=socket.getaddrinfo):
    answers=resolver(host,443,type=socket.SOCK_STREAM)
    if not answers: raise EgressDenied("Empty DNS response")
    # Fail closed if any answer is outside the policy, blocking mixed DNS
    # and DNS rebinding. Pin the selected validated IP for the connection.
    ips=[validate_ip(item[4][0],networks) for item in answers]
    return str(ips[0])

def _pinned_https(host,ip,path,timeout,authorization=None,method='GET',headers=None):
    context=ssl.create_default_context()
    sock=socket.create_connection((ip,443),timeout=timeout)
    sock.settimeout(timeout)
    try:
        secure=context.wrap_socket(sock,server_hostname=host)
        try:
            auth_header = f"Authorization: {authorization}\r\n" if authorization else ""
            if authorization and (len(authorization)>8192 or any(ord(c)<32 or ord(c)>126 for c in authorization)):
                raise EgressDenied("Invalid authentication header encoding")
            extra="".join(f"{name}: {value}\r\n" for name,value in (headers or {}).items())
            request=(f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: OpsControl-RemoteProbe/1\r\nAccept: application/json\r\n{auth_header}{extra}Connection: close\r\n\r\n").encode("ascii")
            secure.sendall(request)
            response=http.client.HTTPResponse(secure)
            response.begin()
            # Bound read even if server lies about Content-Length.
            body=response.read(65537)
            if len(body)>65536: raise EgressDenied("Response body exceeds 64 KiB")
            return response.status,len(body)
        finally: secure.close()
    except Exception:
        sock.close()
        raise

def probe_https(config, hosts, cidrs):
    parts,networks=check_target(config["url"],hosts,cidrs)
    expected=config.get("expected_status",200)
    if type(expected) is not int or not 100<=expected<=599:
        raise EgressDenied("Invalid expected response status")
    method=config.get("method","GET")
    if type(method) is not str or method not in ("GET","HEAD"):
        raise EgressDenied("Unsupported API method")
    headers=config.get("headers",{})
    if not isinstance(headers,dict) or len(headers)>8:
        raise EgressDenied("Invalid API headers")
    for name,value in headers.items():
        if (not isinstance(name,str) or name not in {"accept","user-agent","x-opscontrol-check"}
                or not isinstance(value,str) or not value or len(value)>256
                or any(ord(ch)<32 or ord(ch)>126 for ch in value)):
            raise EgressDenied("Unsafe API request header")
    ip=resolve_target(parts.hostname,networks)
    authorization = None
    reference = config.get("credential_ref")
    if reference is not None:
        # The control plane cannot select secrets outside operator-installed
        # worker policy. Resolve only after destination/DNS policy succeeds.
        approved = {item.strip() for item in os.getenv("OPSCONTROL_ALLOWED_CREDENTIAL_REFS", "").split(",") if item.strip()}
        if not isinstance(reference, str) or reference not in approved:
            raise EgressDenied("Credential reference is not approved for this worker")
        from app.worker.credentials import resolve_basic_auth, CredentialProviderError
        try:
            username, password = resolve_basic_auth(reference)
        except CredentialProviderError:
            raise EgressDenied("Approved credential is unavailable") from None
        if ':' in username:
            raise EgressDenied("Invalid Basic authentication account encoding")
        authorization = "Basic " + base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    path=parts.path or "/"
    if not path.isascii() or any(ord(ch)<33 or ord(ch)>126 for ch in path):
        raise EgressDenied("Target path contains unsafe characters")
    # No redirects are followed. 3xx is an observed result, not a new hop.
    timeout= min(max(int(config.get("timeout_seconds",8)),1),10)
    started=time.monotonic()
    if method=="GET" and not headers:
        status,size=(_pinned_https(parts.hostname,ip,path,timeout,authorization) if authorization
                     else _pinned_https(parts.hostname,ip,path,timeout))
    else:
        status,size=_pinned_https(parts.hostname,ip,path,timeout,authorization,method,headers)
    elapsed=min(int((time.monotonic()-started)*1000),600000)
    result = {"outcome":"SUCCESS" if status==expected else "ASSERTION_FAILED",
              "http_status":status,"response_time_ms":elapsed,"response_size_bytes":size}
    if authorization:
        result["auth_mode"] = "BASIC"
    return result
