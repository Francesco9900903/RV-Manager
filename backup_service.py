import hashlib
import json
from datetime import datetime, timezone
from typing import Any

BACKUP_BUCKET = "system-backups"
TABLES = [
    "employees",
    "employee_accounts",
    "timesheets",
    "clock_entries",
    "monthly_costs",
    "monthly_revenue",
    "fringe_benefits",
    "extra_payments",
    "payslips",
    "employee_documents",
    "employee_notifications",
    "manager_notifications",
    "audit_events",
]

def build_manifest(client: Any, backup_type: str = "automatico") -> dict:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "application": "RV Manager Enterprise",
        "version": "4.1.0",
        "backup_type": backup_type,
        "tables": {},
    }
    for table in TABLES:
        try:
            rows = client.table(table).select("*").limit(10000).execute().data or []
            manifest["tables"][table] = rows
        except Exception as exc:
            manifest["tables"][table] = {
                "_error": f"{type(exc).__name__}: {exc}"
            }
    return manifest

def create_backup(client: Any, backup_type: str = "automatico") -> dict:
    manifest = build_manifest(client, backup_type)
    payload = json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode("utf-8")
    checksum = hashlib.sha256(payload).hexdigest()
    now = datetime.now(timezone.utc)
    filename = f"rv_manager_{backup_type}_{now.strftime('%Y%m%d_%H%M%S')}.json"
    path = f"{now.strftime('%Y/%m/%d')}/{filename}"

    client.storage.from_(BACKUP_BUCKET).upload(
        path,
        payload,
        {"content-type": "application/json", "upsert": "false"},
    )
    client.table("backup_registry").insert({
        "backup_type": backup_type,
        "file_name": filename,
        "storage_path": path,
        "size_bytes": len(payload),
        "checksum_sha256": checksum,
        "status": "completato",
        "created_at": now.isoformat(),
    }).execute()

    return {
        "filename": filename,
        "storage_path": path,
        "size_bytes": len(payload),
        "checksum_sha256": checksum,
    }
