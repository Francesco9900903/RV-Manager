from datetime import date
from typing import Iterable

def approved_hours_summary(timesheets: Iterable[dict]) -> dict:
    approved = [row for row in timesheets if row.get("status") == "approved"]
    ordinary = sum(float(row.get("ordinary_hours") or 0) for row in approved)
    overtime = sum(float(row.get("overtime_hours") or 0) for row in approved)
    return {
        "ordinary": round(ordinary, 2),
        "overtime": round(overtime, 2),
        "total": round(ordinary + overtime, 2),
        "days": len({row.get("work_date") for row in approved if row.get("work_date")}),
    }

def current_period(today: date) -> tuple[int, int]:
    return today.year, today.month
