import os
import sys
from datetime import datetime, timedelta, timezone

from supabase import create_client
from rv_manager.backup_service import create_backup

def is_due(settings: dict) -> bool:
    if not settings.get("enabled"):
        return False

    last_run = settings.get("last_run_at")
    frequency = settings.get("frequency", "giornaliero")
    if not last_run:
        return True

    parsed = datetime.fromisoformat(str(last_run).replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = {
        "giornaliero": timedelta(days=1),
        "settimanale": timedelta(days=7),
        "mensile": timedelta(days=30),
    }.get(frequency, timedelta(days=1))
    return now - parsed >= delta

def main() -> int:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        print("Secrets SUPABASE_URL e SUPABASE_SECRET_KEY mancanti.")
        return 1

    client = create_client(url, key)
    rows = (
        client.table("backup_settings")
        .select("*")
        .eq("id", 1)
        .limit(1)
        .execute().data or []
    )
    settings = rows[0] if rows else {"enabled": False}

    if not is_due(settings):
        print("Nessun backup automatico dovuto.")
        return 0

    result = create_backup(client, "automatico")
    client.table("backup_settings").update({
        "last_run_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", 1).execute()

    print(f"Backup completato: {result['filename']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
