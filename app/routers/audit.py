import os
import json
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/audit", tags=["Audit"])

LOG_DIR = "logs"


def _read_log_files() -> List[Dict[str, Any]]:
    if not os.path.isdir(LOG_DIR):
        return []

    entries: List[Dict[str, Any]] = []
    try:
        for name in sorted(os.listdir(LOG_DIR)):
            if not name.startswith("audit_") or not name.endswith(".log"):
                continue
            path = os.path.join(LOG_DIR, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            # Basic normalization for frontend expectations
                            if isinstance(obj, dict):
                                obj.setdefault("event_type", obj.get("action"))
                                entries.append(obj)
                        except json.JSONDecodeError:
                            # skip malformed lines
                            continue
            except Exception:
                # skip unreadable files
                continue
    except Exception:
        return []

    # Sort by timestamp desc if available
    def sort_key(e: Dict[str, Any]):
        return e.get("timestamp") or ""

    entries.sort(key=sort_key, reverse=True)
    return entries


@router.get("/logs")
def get_audit_logs() -> List[Dict[str, Any]]:
    try:
        return _read_log_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read audit logs: {e}")
