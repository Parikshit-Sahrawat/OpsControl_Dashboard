"""Real occupied TCP listener plus deterministic OS permission failure injection."""
import errno
import socket
import unittest
from scripts.fixture_ports import claim_port, https_port


class FixturePorts(unittest.TestCase):
    def test_unprivileged_dynamic_https(self):
        self.assertGreaterEqual(https_port('127.0.0.1'), 1024)

    def test_occupied_port_is_never_adopted(self):
        with socket.socket() as owner:
            owner.bind(('127.0.0.1', 0))
            owner.listen()
            port = owner.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError, f'address=127.0.0.1 port={port} errno={errno.EADDRINUSE}'):
                claim_port('127.0.0.1', port)
            self.assertEqual(owner.getsockname()[1], port)

    def test_permission_denied_retains_endpoint_and_errno(self):
        def denied():
            raise PermissionError(errno.EACCES, 'Injected OS bind denial')
        with self.assertRaisesRegex(RuntimeError, 'address=192.0.2.1 port=443 errno=13') as caught:
            claim_port('192.0.2.1', 443, socket_factory=denied)
        self.assertIsInstance(caught.exception.__cause__, PermissionError)

    def test_no_privileged_fallback(self):
        for port in (443, -1, 65536):
            with self.assertRaises(ValueError):
                https_port('127.0.0.1', port)
