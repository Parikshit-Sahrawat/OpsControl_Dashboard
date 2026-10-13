"""Native Windows Service wrapper; pywin32 is a Windows-only runtime dependency."""

import json, threading
from pathlib import Path
import win32event, win32service, win32serviceutil
from opscontrol_agent import Agent


class OpsControlService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OpsControlAgent"
    _svc_display_name_ = "OpsControl Agent"

    def __init__(self, args):
        super().__init__(args)
        self.stop = threading.Event()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop.set()

    def SvcDoRun(self):
        root = Path(r"C:\ProgramData\OpsControlAgent")
        config = json.loads((root / "service.json").read_text())
        Agent(
            root / "state",
            config["backend"],
            root / "bin" / "otelcol-contrib.exe",
            self.stop,
        ).run(root / "state" / "enrollment")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(OpsControlService)
