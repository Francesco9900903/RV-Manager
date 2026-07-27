from typing import Optional, Any
from datetime import date, datetime
from decimal import Decimal

def _json_safe(value: Any):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

def log_event(
    sb,
    event_type: str,
    title: str,
    *,
    employee_id: Optional[int] = None,
    actor_user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    severity: str = "info",
) -> None:
    payload = {
        "event_type": event_type,
        "title": title,
        "employee_id": employee_id,
        "actor_user_id": actor_user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": _json_safe(details or {}),
        "severity": severity,
    }
    try:
        sb.table("audit_events").insert(payload).execute()
    except Exception:
        # L'audit non deve bloccare mai l'operazione principale.
        pass

def recent_events(sb, limit: int = 100):
    return (
        sb.table("audit_events")
        .select(
            "id,event_type,title,severity,employee_id,actor_user_id,"
            "entity_type,entity_id,details,created_at,employees(name)"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute().data or []
    )
