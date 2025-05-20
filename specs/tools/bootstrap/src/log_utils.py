import pathlib
import json
from datetime import datetime

LOGS_DIR = pathlib.Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def get_logfile(prefix="audit"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOGS_DIR / f"{prefix}_{ts}.jsonl"

class AuditLogger:
    def __init__(self, logfile=None):
        self.logfile = logfile or get_logfile()
        self._file = open(self.logfile, "a", encoding="utf-8")
    def log(self, event: dict):
        event["timestamp"] = datetime.now().isoformat()
        self._file.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._file.flush()
    def close(self):
        self._file.close()
