from test_local_auto_deploy import m
import unittest
from unittest.mock import patch


class ReadinessTests(unittest.TestCase):
    def test_worker_exec_is_independent(self):
        with patch.object(m, "run") as run:
            m.check_worker(("docker", "compose"), {}, 123.0)
        args = run.call_args.args
        self.assertEqual(args[2:7], ("exec", "-T", "worker", "python", "-c"))
        self.assertIn("123.0 <= t", args[-1])
        self.assertIn("time.time()-t < 60", args[-1])

    def test_worker_failure_propagates(self):
        with patch.object(m, "run", side_effect=RuntimeError("worker stopped")):
            with self.assertRaisesRegex(RuntimeError, "worker stopped"):
                m.check_worker(("docker", "compose"), {}, 123.0)
