"""DEV-04.3.2: isolated outbound request contract, no live network."""
import unittest
from unittest.mock import patch

from app.worker.egress import EgressDenied, probe_https


class APIWorkerV2Tests(unittest.TestCase):
    def setUp(self):
        self.hosts=["api.example.test"]
        self.cidrs=["203.0.113.0/24"]
        self.config={"url":"https://api.example.test/health","method":"HEAD",
                     "headers":{"x-opscontrol-check":"ready"},"expected_status":204}

    def test_head_uses_pinned_tls_and_only_approved_header(self):
        with patch("app.worker.egress.resolve_target",return_value="203.0.113.10"), patch(
            "app.worker.egress._pinned_https",return_value=(204,0)
        ) as transport:
            result=probe_https(self.config,self.hosts,self.cidrs)
        self.assertEqual(result["outcome"],"SUCCESS")
        self.assertEqual(transport.call_args.args[5],"HEAD")
        self.assertEqual(transport.call_args.args[6],{"x-opscontrol-check":"ready"})

    def test_legacy_get_preserves_transport_signature(self):
        with patch("app.worker.egress.resolve_target",return_value="203.0.113.10"), patch(
            "app.worker.egress._pinned_https",return_value=(200,2)
        ) as transport:
            result=probe_https({"url":self.config["url"]},self.hosts,self.cidrs)
        self.assertEqual(result["outcome"],"SUCCESS")
        self.assertEqual(len(transport.call_args.args),4)

    def test_untrusted_header_is_denied_before_dns(self):
        cfg=dict(self.config,headers={"authorization":"Bearer secret"})
        with patch("app.worker.egress.resolve_target") as resolver:
            with self.assertRaises(EgressDenied):
                probe_https(cfg,self.hosts,self.cidrs)
            resolver.assert_not_called()

    def test_crlf_injection_is_denied(self):
        cfg=dict(self.config,headers={"x-opscontrol-check":"yes\r\nHost:evil"})
        with self.assertRaises(EgressDenied):
            probe_https(cfg,self.hosts,self.cidrs)

    def test_post_is_denied(self):
        with self.assertRaises(EgressDenied):
            probe_https(dict(self.config,method="POST"),self.hosts,self.cidrs)


if __name__=="__main__":
    unittest.main()
