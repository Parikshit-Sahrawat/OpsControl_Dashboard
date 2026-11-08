"""Owned fixture preflight. Never adopt a service already listening on a port."""
import socket


def claim_port(address, port, *, socket_factory=socket.socket):
    try:
        with socket_factory() as claim:
            claim.bind((address, port))
            return claim.getsockname()[1]
    except OSError as exc:
        raise RuntimeError(
            f"Owned fixture bind failed address={address} port={port} "
            f"errno={exc.errno}; refusing existing service or privileged fallback"
        ) from exc


def https_port(address, requested=0):
    # Docker maps this unprivileged host port to the isolated fixture's TLS443.
    if requested and not 1024 <= requested <= 65535:
        raise ValueError("Fixture HTTPS host port must be 1024..65535 (or 0 for allocation)")
    return claim_port(address, requested)
