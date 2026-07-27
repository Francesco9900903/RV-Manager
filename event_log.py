from typing import Optional, Any

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
        "details": details or {},
        "severity": severity,
    }
    try:
        sb.table("audit_events").insert(payload).execute()
    except Exception:
        # Il registro eventi non deve mai bloccare l'operazione principale.
        pass

def recent_events(sb, limit: int = 100):
    return (
        sb.table("audit_events")
        .select(
            "id,event_type,title,severity,employee_id,entity_type,"
            "entity_id,details,created_at,employees(name)"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute().data or []
    )
