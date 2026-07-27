
import re
from datetime import date, datetime, timedelta, time
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader, PdfWriter
from supabase import create_client
try:
    from rv_manager.ai_manager import build_personnel_insights
    from rv_manager.event_log import log_event, recent_events
    from rv_manager.ui import render_insight
except ModuleNotFoundError:
    from ai_manager import build_personnel_insights
    from event_log import log_event, recent_events
    from ui import render_insight
from zoneinfo import ZoneInfo

st.set_page_config(page_title="RV Manager Enterprise", page_icon="◈", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --rv-navy: #172033;
        --rv-navy-soft: #24304a;
        --rv-surface: #ffffff;
        --rv-background: #f4f6f9;
        --rv-border: #e3e8ef;
        --rv-text: #1f2937;
        --rv-muted: #667085;
        --rv-accent: #c83b4d;
        --rv-success: #087a55;
        --rv-warning: #b5680b;
        --rv-danger: #b42318;
        --rv-radius: 14px;
        --rv-shadow: 0 8px 26px rgba(23, 32, 51, 0.07);
    }

    html, body, [class*="css"] {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI",
                     Roboto, Helvetica, Arial, sans-serif;
        color: var(--rv-text);
    }

    .stApp {
        background: var(--rv-background);
    }

    /* Area principale */
    .block-container {
        max-width: 1480px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--rv-navy);
        letter-spacing: -0.025em;
    }

    h1 {
        font-weight: 760;
        margin-bottom: 0.15rem;
    }

    h2, h3 {
        font-weight: 700;
    }

    p, label, .stCaption {
        color: var(--rv-muted);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #172033 0%, #202b42 100%);
        border-right: 0;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc;
    }

    section[data-testid="stSidebar"] label {
        color: #d7deea !important;
        font-weight: 600;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.15);
        border-radius: 10px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 0.22rem;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        border-radius: 10px;
        padding: 0.52rem 0.65rem;
        transition: background 0.15s ease, transform 0.15s ease;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.08);
        transform: translateX(2px);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: rgba(255,255,255,0.14);
        box-shadow: inset 3px 0 0 var(--rv-accent);
    }

    .rv-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0.25rem 0 1.2rem 0;
        padding: 0.25rem 0.25rem 0.9rem 0.25rem;
        border-bottom: 1px solid rgba(255,255,255,0.12);
    }

    .rv-brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        background: linear-gradient(135deg, #d84b5d, #a9273a);
        color: white;
        font-weight: 800;
        box-shadow: 0 8px 18px rgba(0,0,0,0.18);
    }

    .rv-brand-title {
        color: white;
        font-size: 1.03rem;
        font-weight: 760;
        line-height: 1.15;
    }

    .rv-brand-subtitle {
        color: #aeb9ca;
        font-size: 0.72rem;
        margin-top: 0.16rem;
    }

    /* Metriche come card */
    div[data-testid="stMetric"] {
        background: var(--rv-surface);
        border: 1px solid var(--rv-border);
        border-radius: var(--rv-radius);
        padding: 1rem 1.05rem;
        min-height: 112px;
        box-shadow: var(--rv-shadow);
    }

    div[data-testid="stMetricLabel"] {
        color: var(--rv-muted);
        font-size: 0.82rem;
        font-weight: 650;
    }

    div[data-testid="stMetricValue"] {
        color: var(--rv-navy);
        font-weight: 760;
        letter-spacing: -0.025em;
    }

    /* Tabelle e grafici */
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"],
    div[data-testid="stVegaLiteChart"],
    div[data-testid="stArrowVegaLiteChart"] {
        background: var(--rv-surface);
        border: 1px solid var(--rv-border);
        border-radius: var(--rv-radius);
        padding: 0.45rem;
        box-shadow: var(--rv-shadow);
        overflow: hidden;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        color: var(--rv-muted);
        font-weight: 650;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--rv-accent);
    }

    div[data-baseweb="tab-highlight"] {
        background-color: var(--rv-accent);
    }

    /* Input */
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div,
    .stDateInput > div > div {
        border-radius: 10px;
        border-color: var(--rv-border);
        background: #fff;
    }

    /* Pulsanti */
    .stButton > button,
    .stDownloadButton > button,
    a[data-testid="stLinkButton"] {
        min-height: 44px;
        border-radius: 10px;
        font-weight: 700;
        border: 1px solid var(--rv-border);
        transition: transform 0.14s ease, box-shadow 0.14s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    a[data-testid="stLinkButton"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(23,32,51,0.11);
    }

    button[kind="primary"] {
        background: var(--rv-accent);
        border-color: var(--rv-accent);
        color: white;
    }

    /* Alert */
    div[data-testid="stAlert"] {
        border-radius: 12px;
        border-width: 1px;
        box-shadow: 0 4px 16px rgba(23,32,51,0.04);
    }

    /* File uploader */
    section[data-testid="stFileUploaderDropzone"] {
        background: #fff;
        border: 1px dashed #bac4d2;
        border-radius: 12px;
    }

    /* Header Streamlit più discreto */
    header[data-testid="stHeader"] {
        background: transparent;
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    /* Responsive */
    @media (max-width: 900px) {
        .block-container {
            padding-top: 1.15rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }

        div[data-testid="stMetric"] {
            min-height: 100px;
            padding: 0.8rem;
        }

        .stButton > button {
            min-height: 52px;
            font-size: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

MONTHS = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

ROME_TZ = ZoneInfo("Europe/Rome")
UTC_TZ = ZoneInfo("UTC")

def now_rome():
    return datetime.now(ROME_TZ)

def parse_db_datetime(value):
    """Converte un timestamp Supabase/UTC nel fuso Europe/Rome."""
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC_TZ)
    return parsed.astimezone(ROME_TZ)


def euro(v):
    v = float(v or 0)
    return f"€ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_it_number(value):
    if not value:
        return 0.0
    value = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0

@st.cache_resource
def supabase_admin():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["secret_key"]
    except Exception:
        st.error(
            "Supabase non è configurato. Apri Manage app → Settings → Secrets "
            "e inserisci url e secret_key."
        )
        st.stop()
    return create_client(url, key)

@st.cache_resource
def supabase_public():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["publishable_key"]
    except Exception:
        return None
    return create_client(url, key)


sb = supabase_admin()
public_sb = supabase_public()

def current_actor_user_id():
    try:
        user = public_sb.auth.get_user()
        return str(user.user.id) if user and user.user else None
    except Exception:
        return None

def audit(
    event_type,
    title,
    *,
    employee_id=None,
    entity_type=None,
    entity_id=None,
    details=None,
    severity="info",
):
    log_event(
        sb,
        event_type,
        title,
        employee_id=employee_id,
        actor_user_id=current_actor_user_id(),
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or {},
        severity=severity,
    )

def init_session():
    defaults = {
        "logged_in": False,
        "user_role": "admin",
        "employee_id": None,
        "user_email": None,
        "access_token": None,
        "refresh_token": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

def employee_login():
    st.title("RV Manager")
    st.subheader("Accesso dipendente")
    st.caption("Inserisci email e password fornite dall'azienda.")
    if public_sb is None:
        st.error("Manca publishable_key nei Secrets di Streamlit.")
        st.stop()

    with st.form("employee_login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Accedi", type="primary")

    if submit:
        try:
            result = public_sb.auth.sign_in_with_password({
                "email": email.strip(),
                "password": password,
            })
            session = result.session
            user = result.user
            if not session or not user:
                st.error("Accesso non riuscito.")
                return

            # Use the signed-in user's JWT for RLS-protected queries.
            public_sb.auth.set_session(session.access_token, session.refresh_token)
            account = (
                public_sb.table("employee_accounts")
                .select("employee_id,role")
                .eq("auth_user_id", user.id)
                .single()
                .execute()
                .data
            )
            st.session_state.logged_in = True
            st.session_state.user_role = account.get("role", "employee")
            st.session_state.employee_id = account.get("employee_id")
            st.session_state.user_email = email.strip()
            st.session_state.access_token = session.access_token
            st.session_state.refresh_token = session.refresh_token
            st.rerun()
        except Exception:
            st.error("Email, password o associazione dipendente non valide.")

def restore_user_session():
    if (
        public_sb is not None
        and st.session_state.get("logged_in")
        and st.session_state.get("access_token")
        and st.session_state.get("refresh_token")
    ):
        try:
            public_sb.auth.set_session(
                st.session_state.access_token,
                st.session_state.refresh_token,
            )
        except Exception:
            st.session_state.logged_in = False

restore_user_session()

def employees_df():
    data = (
        sb.table("employees")
        .select("id,code,name,department,role,level,active")
        .order("name")
        .execute()
        .data or []
    )
    return pd.DataFrame(data)

def pdf_text(uploaded):
    reader = PdfReader(BytesIO(uploaded.getvalue()))
    return "\n".join((p.extract_text() or "") for p in reader.pages)

def normalize_pdf_text(text):
    """Normalizza spazi e caratteri tipici dei PDF del consulente."""
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

def find_amount(block, label):
    # Cerca la voce all'inizio di una riga, evitando di confondere
    # "Oneri sociali" con "Oneri sociali collaboratori".
    pattern = rf"(?im)^\s*{re.escape(label)}\s+(-?[\d\.]+,\d{{2}})\s*$"
    matches = re.findall(pattern, block)
    return parse_it_number(matches[-1]) if matches else 0.0

def parse_cost_report(text):
    text = normalize_pdf_text(text)

    pm = re.search(
        r"periodo\s+da\s+(\d{2})/(\d{4})\s+a\s+\d{2}/\d{4}",
        text,
        re.I,
    )
    if not pm:
        raise ValueError("Periodo non riconosciuto nel PDF.")
    year, month = int(pm.group(2)), int(pm.group(1))

    # Il prospetto può spezzare lo stesso dipendente su due pagine e
    # ripetere l'intestazione. Accorpiamo quindi tutti i blocchi con lo
    # stesso codice dipendente prima di estrarre i valori.
    headers = list(re.finditer(
        r"(?im)^\s*Dipendente\s*:\s*(\d+)\s+([^\n]+?)\s*$",
        text,
    ))

    grouped = {}
    for index, header in enumerate(headers):
        start = header.start()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        code = header.group(1).strip()
        name = re.sub(r"\s{2,}", " ", header.group(2).strip())
        block = text[start:end]

        if code not in grouped:
            grouped[code] = {"name": name, "blocks": []}
        grouped[code]["blocks"].append(block)

    parsed = []
    for code, item in grouped.items():
        block = "\n".join(item["blocks"])
        totals = re.findall(
            r"(?im)^\s*Totale dipendente\s*:\s*([\d\.]+,\d{2})\s*$",
            block,
        )
        if not totals:
            continue

        parsed.append({
            "code": code,
            "name": item["name"],
            "gross_pay": find_amount(block, "Retribuzioni lorde"),
            "social_charges": find_amount(block, "Oneri sociali"),
            "other_charges": find_amount(block, "Altri oneri"),
            "tfr": (
                find_amount(block, "TFR esercizio")
                + find_amount(block, "TFR erogato")
                + find_amount(block, "TFR previdenza complementare")
            ),
            "inail": find_amount(block, "INAIL"),
            "company_cost": parse_it_number(totals[-1]),
        })

    if not parsed:
        raise ValueError(
            "Nessun dipendente riconosciuto. Verifica che il PDF sia il "
            "prospetto 'Costo del personale - singoli dipendenti'."
        )
    return year, month, parsed

def import_cost_pdf(uploaded):
    year, month, parsed = parse_cost_report(pdf_text(uploaded))
    for item in parsed:
        existing = (
            sb.table("employees")
            .select("id")
            .eq("code", item["code"])
            .execute()
            .data or []
        )
        if existing:
            employee_id = existing[0]["id"]
            sb.table("employees").update({"name": item["name"]}).eq("id", employee_id).execute()
        else:
            inserted = sb.table("employees").insert({
                "code": item["code"],
                "name": item["name"],
                "department": "Da assegnare",
                "active": True
            }).execute().data
            employee_id = inserted[0]["id"]

        sb.table("monthly_costs").upsert({
            "employee_id": employee_id,
            "year": year,
            "month": month,
            "gross_pay": item["gross_pay"],
            "social_charges": item["social_charges"],
            "other_charges": item["other_charges"],
            "tfr": item["tfr"],
            "inail": item["inail"],
            "company_cost": item["company_cost"],
            "source_file": uploaded.name
        }, on_conflict="employee_id,year,month").execute()

    return year, month, len(parsed), sum(x["company_cost"] for x in parsed)

def month_data(year, month):
    costs = (
        sb.table("monthly_costs")
        .select("*,employees(id,name,department,role,level)")
        .eq("year", year)
        .eq("month", month)
        .execute().data or []
    )
    if not costs:
        return pd.DataFrame(), 0.0, 0

    data = []
    for c in costs:
        e = c.get("employees") or {}
        data.append({
            "employee_id": c["employee_id"],
            "name": e.get("name", ""),
            "department": e.get("department", "Da assegnare"),
            "role": e.get("role", ""),
            "level": e.get("level", ""),
            "hours": float(c.get("hours") or 0),
            "net_pay": float(c.get("net_pay") or 0),
            "gross_pay": float(c.get("gross_pay") or 0),
            "company_cost": float(c.get("company_cost") or 0),
        })

    df = pd.DataFrame(data)
    start = f"{year:04d}-{month:02d}-01"
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    end = f"{ny:04d}-{nm:02d}-01"

    fringe = (
        sb.table("fringe_benefits").select("employee_id,amount")
        .gte("benefit_date", start).lt("benefit_date", end).execute().data or []
    )
    extras = (
        sb.table("extra_payments").select("employee_id,amount")
        .gte("payment_date", start).lt("payment_date", end).execute().data or []
    )

    f_map, x_map = {}, {}
    for x in fringe:
        f_map[x["employee_id"]] = f_map.get(x["employee_id"], 0) + float(x["amount"] or 0)
    for x in extras:
        x_map[x["employee_id"]] = x_map.get(x["employee_id"], 0) + float(x["amount"] or 0)

    df["fringe"] = df["employee_id"].map(f_map).fillna(0)
    df["extra_cash"] = df["employee_id"].map(x_map).fillna(0)
    df["management_cost"] = df["company_cost"] + df["extra_cash"]

    rev = (
        sb.table("monthly_revenue").select("revenue,covers")
        .eq("year", year).eq("month", month).execute().data or []
    )
    revenue = float(rev[0]["revenue"] or 0) if rev else 0.0
    covers = int(rev[0]["covers"] or 0) if rev else 0
    return df, revenue, covers


def month_bounds(year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end

def get_month_timesheets(employee_id, year, month, client=sb):
    start, end = month_bounds(year, month)
    return (
        client.table("timesheets")
        .select("id,work_date,ordinary_hours,overtime_hours,break_hours,shift_type,status,note")
        .eq("employee_id", employee_id)
        .gte("work_date", start.isoformat())
        .lt("work_date", end.isoformat())
        .order("work_date")
        .execute()
        .data or []
    )

def sync_monthly_hours(employee_id, year, month):
    rows = get_month_timesheets(employee_id, year, month, sb)
    total = sum(
        float(r.get("ordinary_hours") or 0) + float(r.get("overtime_hours") or 0)
        for r in rows
        if r.get("status") == "approved"
    )
    sb.table("monthly_costs").upsert({
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "hours": total,
    }, on_conflict="employee_id,year,month").execute()
    return total


def minutes_between(start_time, end_time):
    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    return int((end_dt - start_dt).total_seconds() // 60)

def decimal_hours(total_minutes):
    return round(total_minutes / 60, 2)

def current_open_shift(employee_id, client):
    data = (
        client.table("clock_entries")
        .select("*")
        .eq("employee_id", employee_id)
        .is_("clock_out", "null")
        .order("clock_in", desc=True)
        .limit(1)
        .execute()
        .data or []
    )
    return data[0] if data else None

def refresh_timesheet_from_clock(employee_id, work_date, client):
    entries = (
        client.table("clock_entries")
        .select("clock_in,clock_out,break_minutes")
        .eq("employee_id", employee_id)
        .eq("work_date", work_date.isoformat())
        .execute()
        .data or []
    )
    total_minutes = 0
    for entry in entries:
        if not entry.get("clock_out"):
            continue
        start_dt = datetime.fromisoformat(entry["clock_in"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(entry["clock_out"].replace("Z", "+00:00"))
        worked = int((end_dt - start_dt).total_seconds() // 60)
        worked -= int(entry.get("break_minutes") or 0)
        total_minutes += max(worked, 0)

    if total_minutes <= 0:
        return

    hours = decimal_hours(total_minutes)
    client.table("timesheets").upsert({
        "employee_id": employee_id,
        "work_date": work_date.isoformat(),
        "ordinary_hours": min(hours, 8),
        "overtime_hours": max(hours - 8, 0),
        "break_hours": 0,
        "shift_type": "Timbratura",
        "status": "submitted",
        "note": "Calcolato automaticamente dalle timbrature",
    }, on_conflict="employee_id,work_date").execute()


def employee_portal():
    employee_id = st.session_state.employee_id
    employee = (
        public_sb.table("employees")
        .select("name,department")
        .eq("id", employee_id)
        .single()
        .execute()
        .data
    )

    

def normalize_person_name(value):
    value = (value or "").upper().strip()
    value = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9 ]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value

def parse_payslip_header(page_text):
    """
    Legge l'intestazione del cedolino reale:
    COD.DIPENDENTE | DIPENDENTE | DATA NASCITA | CODICE FISCALE
    Esempio: 0038 CANTINI MASSIMILIANO 13/12/1964 CNTMSM64T13D612D
    """
    text = page_text or ""

    employee_match = re.search(
        r"(?m)^\s*(\d{4})\s+"
        r"([A-ZÀ-ÖØ-Ý' ]{5,}?)\s+"
        r"(\d{2}/\d{2}/\d{4})\s+"
        r"([A-Z0-9]{16})\s*$",
        text,
    )

    if not employee_match:
        # Fallback più permissivo per estrazioni PDF con spazi irregolari.
        employee_match = re.search(
            r"\b(\d{4})\s+"
            r"([A-ZÀ-ÖØ-Ý' ]{5,}?)\s+"
            r"(\d{2}/\d{2}/\d{4})\s+"
            r"([A-Z0-9]{16})\b",
            text,
        )

    period_match = re.search(
        r"\b("
        r"GENNAIO|FEBBRAIO|MARZO|APRILE|MAGGIO|GIUGNO|"
        r"LUGLIO|AGOSTO|SETTEMBRE|OTTOBRE|NOVEMBRE|DICEMBRE"
        r")\s+(\d{4})\b",
        normalize_person_name(text),
    )

    if not employee_match:
        return None

    month_lookup = {
        "GENNAIO": 1, "FEBBRAIO": 2, "MARZO": 3, "APRILE": 4,
        "MAGGIO": 5, "GIUGNO": 6, "LUGLIO": 7, "AGOSTO": 8,
        "SETTEMBRE": 9, "OTTOBRE": 10, "NOVEMBRE": 11, "DICEMBRE": 12,
    }

    return {
        "employee_code": employee_match.group(1).strip(),
        "employee_name": normalize_person_name(employee_match.group(2)),
        "birth_date": employee_match.group(3).strip(),
        "tax_code": normalize_person_name(employee_match.group(4)),
        "year": int(period_match.group(2)) if period_match else None,
        "month": month_lookup.get(period_match.group(1)) if period_match else None,
    }

def employee_match_catalog():
    employees = (
        sb.table("employees")
        .select("id,code,name")
        .order("name")
        .execute().data or []
    )
    profiles = (
        sb.table("employee_profiles")
        .select("employee_id,tax_code")
        .execute().data or []
    )
    tax_map = {
        int(p["employee_id"]): normalize_person_name(p.get("tax_code"))
        for p in profiles if p.get("tax_code")
    }

    catalog = []
    for employee in employees:
        catalog.append({
            "id": int(employee["id"]),
            "code": str(employee.get("code") or "").strip().zfill(4),
            "name": normalize_person_name(employee.get("name")),
            "tax_code": tax_map.get(int(employee["id"]), ""),
        })
    return catalog

def match_employee_from_header(header, catalog):
    if not header:
        return None

    scored = []
    for employee in catalog:
        score = 0

        if employee["tax_code"] and header["tax_code"] == employee["tax_code"]:
            score += 100

        if employee["code"] and header["employee_code"] == employee["code"]:
            score += 60

        if employee["name"] and header["employee_name"] == employee["name"]:
            score += 80
        elif employee["name"] and employee["name"] in header["employee_name"]:
            score += 50

        if score:
            scored.append((score, employee["id"]))

    if not scored:
        return None

    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None

    return scored[0][1]

def split_and_store_payslips(uploaded_file, fallback_year, fallback_month):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    catalog = employee_match_catalog()
    if not catalog:
        raise ValueError("Non risultano dipendenti nel gestionale.")

    grouped_pages = {}
    unresolved_pages = []
    recognized_preview = []

    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        header = parse_payslip_header(page_text)
        employee_id = match_employee_from_header(header, catalog)

        if not header or employee_id is None:
            unresolved_pages.append(page_index + 1)
            continue

        page_year = header.get("year") or fallback_year
        page_month = header.get("month") or fallback_month
        group_key = (employee_id, page_year, page_month)

        grouped_pages.setdefault(group_key, []).append(page_index)
        recognized_preview.append({
            "Pagina": page_index + 1,
            "Codice": header["employee_code"],
            "Dipendente": header["employee_name"],
            "Codice fiscale": header["tax_code"],
            "Periodo": f"{MONTHS[page_month]} {page_year}",
        })

    if not grouped_pages:
        raise ValueError(
            "Nessuna busta paga riconosciuta. Verifica che il PDF sia quello "
            "dei cedolini mensili e che i dipendenti siano presenti nel gestionale."
        )

    saved = []

    for (employee_id, detected_year, detected_month), page_indexes in grouped_pages.items():
        writer = PdfWriter()
        for page_index in page_indexes:
            writer.add_page(reader.pages[page_index])

        output = BytesIO()
        writer.write(output)
        output.seek(0)

        storage_path = (
            f"{employee_id}/{detected_year:04d}/"
            f"{detected_month:02d}/busta_paga.pdf"
        )

        try:
            sb.storage.from_("payslips").remove([storage_path])
        except Exception:
            pass

        # Supabase Storage richiede un oggetto file binario.
        # Passare direttamente i bytes può causare errori nel multipart encoder.
        pdf_file = BytesIO(output.getvalue())
        pdf_file.name = "busta_paga.pdf"

        sb.storage.from_("payslips").upload(
            path=storage_path,
            file=pdf_file,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true",
            },
        )

        sb.table("payslips").upsert({
            "employee_id": employee_id,
            "year": detected_year,
            "month": detected_month,
            "storage_path": storage_path,
            "original_file_name": uploaded_file.name,
            "page_count": len(page_indexes),
            "status": "published",
        }, on_conflict="employee_id,year,month").execute()

        sb.table("employee_notifications").insert({
            "employee_id": employee_id,
            "title": "Nuova busta paga disponibile",
            "message": f"È disponibile la busta paga di {MONTHS[detected_month]} {detected_year}.",
            "notification_type": "payslip",
            "is_read": False,
        }).execute()

        audit(
            "payslip_published",
            "Busta paga pubblicata",
            employee_id=employee_id,
            entity_type="payslip",
            entity_id=f"{detected_year}-{detected_month:02d}",
            details={
                "storage_path": storage_path,
                "page_count": len(page_indexes),
                "original_file_name": uploaded_file.name,
            },
        )

        saved.append({
            "employee_id": employee_id,
            "year": detected_year,
            "month": detected_month,
            "pages": [x + 1 for x in page_indexes],
        })

    return saved, unresolved_pages, recognized_preview

def payslip_download_url(storage_path, client):
    result = client.storage.from_("payslips").create_signed_url(storage_path, 300)
    if isinstance(result, dict):
        return (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )
    return getattr(result, "signed_url", None)

def safe_storage_filename(filename):
    filename = (filename or "documento").strip()
    stem, dot, extension = filename.rpartition(".")
    if not dot:
        stem, extension = filename, ""
    stem = normalize_person_name(stem).lower().replace(" ", "_")
    stem = re.sub(r"[^a-z0-9_-]", "", stem) or "documento"
    extension = re.sub(r"[^a-z0-9]", "", extension.lower())
    return f"{stem}.{extension}" if extension else stem

def employee_document_url(storage_path, client):
    result = client.storage.from_("employee-documents").create_signed_url(
        storage_path,
        300,
    )
    if isinstance(result, dict):
        return (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )
    return getattr(result, "signed_url", None)




def employee_portal():
    employee_id = st.session_state.employee_id
    employee = (
        public_sb.table("employees")
        .select("name,department")
        .eq("id", employee_id)
        .single()
        .execute()
        .data
    )

    st.sidebar.markdown(
        """
        <div class="rv-brand">
            <div class="rv-brand-mark">RV</div>
            <div>
                <div class="rv-brand-title">Area dipendente</div>
                <div class="rv-brand-subtitle">RV Manager Enterprise</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.write(employee.get("name", "Dipendente"))
    st.sidebar.caption(employee.get("department") or "")
    if st.sidebar.button("Esci"):
        try:
            public_sb.auth.sign_out()
        except Exception:
            pass
        for key in ["logged_in", "employee_id", "access_token", "refresh_token", "user_email"]:
            st.session_state[key] = None if key != "logged_in" else False
        st.rerun()

    today = date.today()
    years = list(range(2025, today.year + 2))
    selected_year = st.sidebar.selectbox("Anno", years, index=years.index(today.year))
    selected_month = st.sidebar.selectbox(
        "Mese", list(MONTHS),
        format_func=lambda x: MONTHS[x],
        index=today.month - 1,
    )

    tabs = st.tabs(["Home", "Timbratura", "Inserimento manuale", "Storico", "Buste paga", "Documenti"])

    with tabs[0]:
        st.title(f"Benvenuto, {employee.get('name', 'Dipendente').title()}")
        st.caption(employee.get("department") or "Area personale")

        start_date, end_date = month_bounds(selected_year, selected_month)

        month_entries = (
            public_sb.table("timesheets")
            .select("ordinary_hours,overtime_hours,status,work_date")
            .eq("employee_id", employee_id)
            .gte("work_date", start_date.isoformat())
            .lt("work_date", end_date.isoformat())
            .execute().data or []
        )

        approved_entries = [
            row for row in month_entries if row.get("status") == "approved"
        ]
        ordinary_total = sum(float(row.get("ordinary_hours") or 0) for row in approved_entries)
        overtime_total = sum(float(row.get("overtime_hours") or 0) for row in approved_entries)
        days_worked = len({row.get("work_date") for row in approved_entries if row.get("work_date")})

        latest_payslip = (
            public_sb.table("payslips")
            .select("year,month,storage_path")
            .eq("employee_id", employee_id)
            .eq("status", "published")
            .order("year", desc=True)
            .order("month", desc=True)
            .limit(1)
            .execute().data or []
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Ore approvate", f"{ordinary_total + overtime_total:.2f}")
        c2.metric("Straordinari", f"{overtime_total:.2f}")
        c3.metric("Giorni registrati", days_worked)

        st.subheader("Azioni rapide")
        q1, q2 = st.columns(2)
        q1.info("Usa la scheda **Timbratura** per registrare entrata e uscita.")
        if latest_payslip:
            document = latest_payslip[0]
            period = f"{MONTHS[int(document['month'])]} {int(document['year'])}"
            url = payslip_download_url(document["storage_path"], public_sb)
            if url:
                q2.link_button(
                    f"Apri ultima busta paga · {period}",
                    url,
                    use_container_width=True,
                )
        else:
            q2.info("Nessuna busta paga ancora disponibile.")

        st.subheader("Calendario presenze")
        calendar_rows = []
        for row in sorted(month_entries, key=lambda x: x.get("work_date") or ""):
            total = float(row.get("ordinary_hours") or 0) + float(row.get("overtime_hours") or 0)
            calendar_rows.append({
                "Giorno": row.get("work_date"),
                "Ore": round(total, 2),
                "Straordinario": round(float(row.get("overtime_hours") or 0), 2),
                "Stato": row.get("status"),
            })

        if calendar_rows:
            st.dataframe(
                pd.DataFrame(calendar_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nessuna presenza registrata per il mese selezionato.")

        notifications = (
            public_sb.table("employee_notifications")
            .select("id,title,message,created_at,is_read")
            .eq("employee_id", employee_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute().data or []
        )
        st.subheader("Notifiche")
        if notifications:
            for notice in notifications:
                icon = "●" if not notice.get("is_read") else "○"
                st.write(f"{icon} **{notice.get('title', 'Notifica')}**")
                st.caption(notice.get("message") or "")
        else:
            st.info("Nessuna notifica.")

    with tabs[1]:
        st.title("Timbratura smart")
        st.caption(f"{employee.get('name')} · {today.strftime('%d/%m/%Y')}")

        open_shift = current_open_shift(employee_id, public_sb)

        if open_shift:
            started = parse_db_datetime(open_shift["clock_in"])
            local_started = started.astimezone()

            st.success(
                f"Sei in servizio dalle {local_started.strftime('%H:%M')}."
            )

            @st.fragment(run_every="30s")
            def live_employee_elapsed():
                elapsed = now_rome() - local_started
                elapsed_seconds = max(elapsed.total_seconds(), 0)
                hours = int(elapsed_seconds // 3600)
                minutes = int((elapsed_seconds % 3600) // 60)

                c_elapsed, c_clock = st.columns(2)
                c_elapsed.metric("Tempo trascorso", f"{hours}h {minutes:02d}m")
                c_clock.metric("Ora attuale", now_rome().strftime("%H:%M"))

            live_employee_elapsed()

            st.info(
                "Quando hai terminato il turno, premi il pulsante rosso. "
                "Potrai indicare la pausa prima della conferma."
            )

            break_minutes = st.number_input(
                "Pausa totale da sottrarre",
                min_value=0,
                max_value=480,
                value=int(open_shift.get("break_minutes") or 0),
                step=5,
                format="%d",
                help="Inserisci i minuti complessivi di pausa del turno.",
            )

            note = st.text_input(
                "Nota facoltativa",
                placeholder="Esempio: servizio prolungato, sostituzione collega…",
            )

            if st.button(
                "🔴 REGISTRA USCITA",
                type="primary",
                use_container_width=True,
            ):
                now = now_rome()
                public_sb.table("clock_entries").update({
                    "clock_out": now.isoformat(),
                    "break_minutes": break_minutes,
                    "status": "submitted",
                }).eq("id", open_shift["id"]).execute()

                refresh_timesheet_from_clock(employee_id, today, public_sb)

                if note.strip():
                    public_sb.table("timesheets").update({
                        "note": note.strip()
                    }).eq("employee_id", employee_id).eq(
                        "work_date", today.isoformat()
                    ).execute()

                audit(
                    "clock_out",
                    "Uscita registrata",
                    employee_id=employee_id,
                    entity_type="clock_entry",
                    entity_id=open_shift["id"],
                    details={
                        "clock_out": now.isoformat(),
                        "break_minutes": int(break_minutes),
                    },
                )
                st.success(
                    "Uscita registrata. Le ore sono state inviate al responsabile."
                )
                st.rerun()

        else:
            st.info(
                "Premi il pulsante verde quando inizi il turno. "
                "Non devi compilare altri campi."
            )

            shift_type = st.selectbox(
                "Tipo turno",
                ["Pranzo", "Cena", "Spezzato", "Altro"],
            )

            if st.button(
                "🟢 REGISTRA ENTRATA",
                type="primary",
                use_container_width=True,
            ):
                now = now_rome()
                public_sb.table("clock_entries").insert({
                    "employee_id": employee_id,
                    "work_date": today.isoformat(),
                    "clock_in": now.isoformat(),
                    "shift_type": shift_type,
                    "status": "open",
                }).execute()

                audit(
                    "clock_in",
                    "Entrata registrata",
                    employee_id=employee_id,
                    entity_type="clock_entry",
                    entity_id=today.isoformat(),
                    details={"clock_in": now.isoformat(), "shift_type": shift_type},
                )
                st.success(
                    f"Entrata registrata alle {now.strftime('%H:%M')}."
                )
                st.rerun()

        day_entries = (
            public_sb.table("clock_entries")
            .select("clock_in,clock_out,break_minutes,shift_type,status")
            .eq("employee_id", employee_id)
            .eq("work_date", today.isoformat())
            .order("clock_in")
            .execute()
            .data or []
        )

        if day_entries:
            st.subheader("Timbrature di oggi")
            display_rows = []
            for entry in day_entries:
                clock_in = parse_db_datetime(entry["clock_in"])
                clock_out = None
                worked_hours = None

                if entry.get("clock_out"):
                    clock_out = parse_db_datetime(entry["clock_out"])
                    minutes = int(
                        (clock_out - clock_in).total_seconds() // 60
                    ) - int(entry.get("break_minutes") or 0)
                    worked_hours = round(max(minutes, 0) / 60, 2)

                display_rows.append({
                    "Entrata": clock_in.strftime("%H:%M"),
                    "Uscita": (
                        clock_out.strftime("%H:%M")
                        if clock_out else "In servizio"
                    ),
                    "Pausa (min)": int(entry.get("break_minutes") or 0),
                    "Ore": worked_hours if worked_hours is not None else "",
                    "Turno": entry.get("shift_type"),
                    "Stato": entry.get("status"),
                })

            st.dataframe(
                pd.DataFrame(display_rows),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[2]:
        st.title("Inserimento manuale")
        st.caption("Usalo per recuperare una giornata non timbrata o correggere un'assenza di timbratura.")

        with st.form("my_hours_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            work_date = c1.date_input("Giorno", value=today)
            shift_type = c2.selectbox("Turno", ["Pranzo", "Cena", "Spezzato", "Altro"], key="manual_shift")
            c3, c4, c5 = st.columns(3)
            ordinary = c3.number_input("Ore ordinarie", min_value=0.0, max_value=24.0, step=0.25)
            overtime = c4.number_input("Straordinario", min_value=0.0, max_value=12.0, step=0.25)
            break_hours = c5.number_input("Pausa", min_value=0.0, max_value=8.0, step=0.25)
            note = st.text_input("Motivo o nota")
            submit = st.form_submit_button("Invia ore", type="primary")

        if submit:
            if work_date.year != selected_year or work_date.month != selected_month:
                st.error("La data deve appartenere al mese selezionato.")
            elif ordinary + overtime <= 0:
                st.error("Inserisci almeno un'ora.")
            else:
                public_sb.table("timesheets").upsert({
                    "employee_id": employee_id,
                    "work_date": work_date.isoformat(),
                    "ordinary_hours": ordinary,
                    "overtime_hours": overtime,
                    "break_hours": break_hours,
                    "shift_type": shift_type,
                    "status": "submitted",
                    "note": note,
                }, on_conflict="employee_id,work_date").execute()
                audit(
                    "timesheet_submitted",
                    "Ore manuali inviate dal dipendente",
                    employee_id=employee_id,
                    entity_type="timesheet",
                    entity_id=work_date.isoformat(),
                    details={
                        "ordinary_hours": ordinary,
                        "overtime_hours": overtime,
                        "break_hours": break_hours,
                        "shift_type": shift_type,
                    },
                )
                st.success("Ore inviate al responsabile.")

    with tabs[3]:
        st.title("Storico ore")
        st.caption(f"{MONTHS[selected_month]} {selected_year}")
        records = get_month_timesheets(
            employee_id, selected_year, selected_month, public_sb
        )
        df = pd.DataFrame(records)
        if df.empty:
            st.info("Non hai ancora inserito ore per questo mese.")
        else:
            total_submitted = (
                df["ordinary_hours"].fillna(0).astype(float)
                + df["overtime_hours"].fillna(0).astype(float)
            ).sum()
            approved = df.loc[df["status"] == "approved"]
            total_approved = (
                approved["ordinary_hours"].fillna(0).astype(float)
                + approved["overtime_hours"].fillna(0).astype(float)
            ).sum() if not approved.empty else 0
            a, b = st.columns(2)
            a.metric("Ore inserite", f"{total_submitted:.2f}")
            b.metric("Ore approvate", f"{total_approved:.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[4]:
        st.title("Le mie buste paga")
        documents = (
            public_sb.table("payslips")
            .select("year,month,storage_path,page_count,created_at")
            .eq("employee_id", employee_id)
            .eq("status", "published")
            .order("year", desc=True)
            .order("month", desc=True)
            .execute().data or []
        )
        if not documents:
            st.info("Non sono ancora disponibili buste paga.")
        else:
            for document in documents:
                period = f"{MONTHS[int(document['month'])]} {int(document['year'])}"
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{period}**")
                c1.caption(f"{int(document.get('page_count') or 1)} pagina/e")
                url = payslip_download_url(document["storage_path"], public_sb)
                if url:
                    c2.link_button("Apri PDF", url, use_container_width=True)
                else:
                    c2.warning("Link non disponibile")


    with tabs[5]:
        st.title("I miei documenti")
        st.caption(
            "Contratti, attestati, CU e altri documenti personali "
            "pubblicati dal responsabile."
        )

        # Lettura server-side filtrata sull'employee_id autenticato.
        # Evita che una policy RLS incompleta nasconda documenti validi,
        # senza esporre file di altri dipendenti.
        documents = (
            sb.table("employee_documents")
            .select(
                "id,title,document_type,document_date,expiry_date,"
                "storage_path,original_file_name,status,created_at"
            )
            .eq("employee_id", employee_id)
            .eq("status", "published")
            .order("document_date", desc=True)
            .order("created_at", desc=True)
            .execute().data or []
        )

        if not documents:
            st.info("Non sono ancora disponibili documenti personali.")
        else:
            document_rows = []
            for document in documents:
                expiry = document.get("expiry_date") or ""
                document_rows.append({
                    "Documento": document.get("title"),
                    "Categoria": document.get("document_type"),
                    "Data": document.get("document_date") or "",
                    "Scadenza": expiry,
                    "File": document.get("original_file_name") or "",
                })

            st.dataframe(
                pd.DataFrame(document_rows),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Apri documento")
            selected_document_id = st.selectbox(
                "Seleziona",
                [int(d["id"]) for d in documents],
                format_func=lambda document_id: next(
                    (
                        f"{d['title']} · {d.get('document_type', '')}"
                        for d in documents
                        if int(d["id"]) == document_id
                    ),
                    str(document_id),
                ),
            )
            selected_document = next(
                d for d in documents if int(d["id"]) == selected_document_id
            )
            url = employee_document_url(
                selected_document["storage_path"],
                sb,
            )
            if url:
                st.link_button(
                    "Apri documento",
                    url,
                    use_container_width=True,
                )
            else:
                st.warning("Documento trovato, ma il collegamento temporaneo non è disponibile.")


# Employee login gate. The current Streamlit app can remain private during tests.
if st.query_params.get("area") == "dipendente":
    if not st.session_state.logged_in:
        employee_login()
        st.stop()
    employee_portal()
    st.stop()



def normalize_person_name(value):
    value = (value or "").upper().strip()
    value = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9 ]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value

def detect_payslip_period(text, fallback_year, fallback_month):
    patterns = [
        r"(?:mese|periodo|competenza)\s*[:\-]?\s*([A-ZÀ-ÖØ-Ý]+)\s+(\d{4})",
        r"(?:mese|periodo|competenza)\s*[:\-]?\s*(\d{1,2})[\/\-](\d{4})",
        r"(\d{1,2})[\/\-](\d{4})",
    ]
    month_names = {normalize_person_name(v): k for k, v in MONTHS.items()}
    upper = normalize_person_name(text)

    m = re.search(patterns[0], upper, re.I)
    if m:
        month_value = month_names.get(normalize_person_name(m.group(1)))
        if month_value:
            return int(m.group(2)), month_value

    for pattern in patterns[1:]:
        m = re.search(pattern, text, re.I)
        if m:
            month_value = int(m.group(1))
            year_value = int(m.group(2))
            if 1 <= month_value <= 12 and 2020 <= year_value <= 2100:
                return year_value, month_value

    return fallback_year, fallback_month

def employee_match_catalog():
    employees = (
        sb.table("employees")
        .select("id,code,name")
        .order("name")
        .execute().data or []
    )
    profiles = (
        sb.table("employee_profiles")
        .select("employee_id,tax_code")
        .execute().data or []
    )
    tax_map = {
        int(p["employee_id"]): normalize_person_name(p.get("tax_code"))
        for p in profiles if p.get("tax_code")
    }

    catalog = []
    for employee in employees:
        catalog.append({
            "id": int(employee["id"]),
            "code": normalize_person_name(employee.get("code")),
            "name": normalize_person_name(employee.get("name")),
            "tax_code": tax_map.get(int(employee["id"]), ""),
        })
    return catalog

def match_employee_from_page(page_text, catalog):
    normalized = normalize_person_name(page_text)
    scored = []
    for employee in catalog:
        score = 0
        if employee["tax_code"] and employee["tax_code"] in normalized:
            score += 100
        if employee["code"] and re.search(rf"\b{re.escape(employee['code'])}\b", normalized):
            score += 35
        if employee["name"] and employee["name"] in normalized:
            score += 70
        else:
            name_parts = [p for p in employee["name"].split() if len(p) > 2]
            matched_parts = sum(1 for p in name_parts if re.search(rf"\b{re.escape(p)}\b", normalized))
            if name_parts and matched_parts == len(name_parts):
                score += 50
        if score:
            scored.append((score, employee["id"]))

    if not scored:
        return None
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]

def split_and_store_payslips(uploaded_file, fallback_year, fallback_month):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    catalog = employee_match_catalog()
    if not catalog:
        raise ValueError("Non risultano dipendenti nel gestionale.")

    grouped_pages = {}
    unresolved_pages = []
    current_employee_id = None

    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        matched_employee_id = match_employee_from_page(page_text, catalog)

        # Le pagine successive della stessa busta possono non ripetere il nome.
        if matched_employee_id is not None:
            current_employee_id = matched_employee_id

        if current_employee_id is None:
            unresolved_pages.append(page_index + 1)
            continue

        grouped_pages.setdefault(current_employee_id, []).append(page_index)

    if not grouped_pages:
        raise ValueError(
            "Nessuna busta paga riconosciuta. Il PDF potrebbe essere una scansione "
            "oppure avere un formato non ancora supportato."
        )

    full_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    detected_year, detected_month = detect_payslip_period(
        full_text, fallback_year, fallback_month
    )

    saved = []
    for employee_id, page_indexes in grouped_pages.items():
        writer = PdfWriter()
        for page_index in page_indexes:
            writer.add_page(reader.pages[page_index])

        output = BytesIO()
        writer.write(output)
        output.seek(0)

        storage_path = (
            f"{employee_id}/{detected_year:04d}/"
            f"{detected_month:02d}/busta_paga.pdf"
        )

        # Remove previous version, if present, then upload the replacement.
        try:
            sb.storage.from_("payslips").remove([storage_path])
        except Exception:
            pass

        # Supabase Storage richiede un oggetto file binario.
        # Passare direttamente i bytes può causare errori nel multipart encoder.
        pdf_file = BytesIO(output.getvalue())
        pdf_file.name = "busta_paga.pdf"

        sb.storage.from_("payslips").upload(
            path=storage_path,
            file=pdf_file,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true",
            },
        )

        sb.table("payslips").upsert({
            "employee_id": employee_id,
            "year": detected_year,
            "month": detected_month,
            "storage_path": storage_path,
            "original_file_name": uploaded_file.name,
            "page_count": len(page_indexes),
            "status": "published",
        }, on_conflict="employee_id,year,month").execute()

        saved.append({
            "employee_id": employee_id,
            "pages": [x + 1 for x in page_indexes],
        })

    return detected_year, detected_month, saved, unresolved_pages

def payslip_download_url(storage_path, client):
    result = client.storage.from_("payslips").create_signed_url(storage_path, 300)
    if isinstance(result, dict):
        return (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
        )
    return getattr(result, "signed_url", None)



def manager_daily_snapshot(selected_year, selected_month):
    today = date.today()
    month_start, month_end = month_bounds(selected_year, selected_month)

    employees = (
        sb.table("employees")
        .select("id,name,department,active")
        .eq("active", True)
        .execute().data or []
    )
    employee_map = {int(e["id"]): e for e in employees}

    today_clock = (
        sb.table("clock_entries")
        .select("employee_id,clock_in,clock_out,status,work_date")
        .eq("work_date", today.isoformat())
        .execute().data or []
    )
    present_ids = {
        int(row["employee_id"])
        for row in today_clock
        if row.get("clock_in") and not row.get("clock_out")
    }
    open_entries = [
        row for row in today_clock
        if row.get("clock_in") and not row.get("clock_out")
    ]

    timesheets = (
        sb.table("timesheets")
        .select("employee_id,work_date,ordinary_hours,overtime_hours,status")
        .gte("work_date", month_start.isoformat())
        .lt("work_date", month_end.isoformat())
        .execute().data or []
    )
    approved = [r for r in timesheets if r.get("status") == "approved"]
    pending = [r for r in timesheets if r.get("status") == "submitted"]

    total_hours = sum(
        float(r.get("ordinary_hours") or 0) + float(r.get("overtime_hours") or 0)
        for r in approved
    )
    overtime_total = sum(float(r.get("overtime_hours") or 0) for r in approved)

    today_rows = [r for r in approved if r.get("work_date") == today.isoformat()]
    today_hours = sum(
        float(r.get("ordinary_hours") or 0) + float(r.get("overtime_hours") or 0)
        for r in today_rows
    )

    live_open_hours = 0.0
    for row in open_entries:
        started = parse_db_datetime(row.get("clock_in"))
        if started:
            live_open_hours += max(
                (now_rome() - started).total_seconds() / 3600,
                0,
            )
    today_hours += live_open_hours

    costs = (
        sb.table("monthly_costs")
        .select("company_cost")
        .eq("year", selected_year)
        .eq("month", selected_month)
        .execute().data or []
    )
    monthly_cost = sum(float(r.get("company_cost") or 0) for r in costs)
    avg_hour_cost = monthly_cost / total_hours if total_hours else 0
    today_cost = today_hours * avg_hour_cost if avg_hour_cost else 0

    revenue_rows = (
        sb.table("monthly_revenue")
        .select("revenue,covers")
        .eq("year", selected_year)
        .eq("month", selected_month)
        .execute().data or []
    )
    revenue = float(revenue_rows[0].get("revenue") or 0) if revenue_rows else 0
    covers = int(revenue_rows[0].get("covers") or 0) if revenue_rows else 0
    incidence = monthly_cost / revenue * 100 if revenue else 0

    payslip_result = (
        sb.table("payslips")
        .select("id", count="exact")
        .eq("year", selected_year)
        .eq("month", selected_month)
        .eq("status", "published")
        .execute()
    )
    payslip_count = payslip_result.count or 0

    overtime_by_employee = {}
    for row in approved:
        employee_id = int(row["employee_id"])
        overtime_by_employee[employee_id] = (
            overtime_by_employee.get(employee_id, 0)
            + float(row.get("overtime_hours") or 0)
        )

    anomalies = []
    for row in open_entries:
        employee = employee_map.get(int(row["employee_id"]), {})
        anomalies.append({
            "Priorità": "Alta",
            "Dipendente": employee.get("name", "Dipendente"),
            "Anomalia": "Uscita non registrata",
        })

    for employee_id, overtime in overtime_by_employee.items():
        if overtime >= 10:
            employee = employee_map.get(employee_id, {})
            anomalies.append({
                "Priorità": "Media",
                "Dipendente": employee.get("name", "Dipendente"),
                "Anomalia": f"Straordinari elevati: {overtime:.2f} ore",
            })

    agenda = []
    if pending:
        agenda.append(f"Approva {len(pending)} registrazioni ore.")
    if open_entries:
        agenda.append(f"Controlla {len(open_entries)} timbrature senza uscita.")
    if payslip_count == 0:
        agenda.append("Pubblica le buste paga del mese.")
    if overtime_total >= 20:
        agenda.append(f"Verifica {overtime_total:.2f} ore di straordinario.")
    if not agenda:
        agenda.append("Nessuna attività urgente.")

    daily_status = {}
    for row in timesheets:
        work_date = row.get("work_date")
        if not work_date:
            continue
        status = row.get("status")
        if status == "rejected":
            daily_status[work_date] = "Anomalia"
        elif status == "submitted" and daily_status.get(work_date) != "Anomalia":
            daily_status[work_date] = "Da approvare"
        elif work_date not in daily_status:
            daily_status[work_date] = "Regolare"

    calendar_rows = []
    cursor = month_start
    while cursor < month_end:
        calendar_rows.append({
            "Data": cursor.isoformat(),
            "Stato": daily_status.get(cursor.isoformat(), "Nessun dato"),
        })
        cursor += timedelta(days=1)

    dept_hours = {}
    for row in approved:
        employee = employee_map.get(int(row["employee_id"]), {})
        department = employee.get("department") or "Da assegnare"
        worked = float(row.get("ordinary_hours") or 0) + float(row.get("overtime_hours") or 0)
        dept_hours[department] = dept_hours.get(department, 0) + worked

    return {
        "active_employees": len(employees),
        "present_now": len(present_ids),
        "pending_count": len(pending),
        "today_hours": today_hours,
        "today_cost": today_cost,
        "incidence": incidence,
        "covers": covers,
        "payslip_count": payslip_count,
        "overtime_total": overtime_total,
        "agenda": agenda,
        "anomalies": anomalies,
        "calendar_rows": calendar_rows,
        "dept_hours": dept_hours,
    }


def document_expiry_snapshot(days_ahead=60):
    today = date.today()
    limit_date = today + timedelta(days=days_ahead)

    rows = (
        sb.table("employee_documents")
        .select(
            "id,employee_id,title,document_type,expiry_date,status,"
            "employees(name,department)"
        )
        .eq("status", "published")
        .not_.is_("expiry_date", "null")
        .lte("expiry_date", limit_date.isoformat())
        .order("expiry_date")
        .execute().data or []
    )

    result = []
    for row in rows:
        expiry = date.fromisoformat(row["expiry_date"])
        days_left = (expiry - today).days
        employee_data = row.get("employees") or {}

        if days_left < 0:
            status = "Scaduto"
            priority = "Alta"
        elif days_left <= 15:
            status = "In scadenza"
            priority = "Alta"
        elif days_left <= 30:
            status = "Da controllare"
            priority = "Media"
        else:
            status = "Prossima scadenza"
            priority = "Bassa"

        result.append({
            "ID": int(row["id"]),
            "Dipendente": employee_data.get("name", ""),
            "Reparto": employee_data.get("department", ""),
            "Documento": row.get("title", ""),
            "Categoria": row.get("document_type", ""),
            "Scadenza": row.get("expiry_date", ""),
            "Giorni residui": days_left,
            "Stato": status,
            "Priorità": priority,
        })

    return result

def manager_notification_snapshot(limit=30):
    rows = (
        sb.table("manager_notifications")
        .select(
            "id,title,message,notification_type,priority,is_read,"
            "created_at,employee_id,employees(name)"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute().data or []
    )

    result = []
    for row in rows:
        employee_data = row.get("employees") or {}
        result.append({
            "ID": int(row["id"]),
            "Priorità": row.get("priority", "Media"),
            "Titolo": row.get("title", ""),
            "Messaggio": row.get("message", ""),
            "Dipendente": employee_data.get("name", ""),
            "Letta": bool(row.get("is_read")),
            "Creata": row.get("created_at", ""),
        })
    return result

def ensure_automatic_manager_alerts():
    """
    Crea alert solo quando non esiste già un alert aperto equivalente.
    """
    today = date.today()
    alerts_created = 0

    # Documenti scaduti o in scadenza.
    for item in document_expiry_snapshot(30):
        alert_key = f"document:{item['ID']}:{item['Scadenza']}"
        existing = (
            sb.table("manager_notifications")
            .select("id")
            .eq("alert_key", alert_key)
            .eq("is_read", False)
            .limit(1)
            .execute().data or []
        )
        if not existing:
            sb.table("manager_notifications").insert({
                "employee_id": None,
                "title": f"Documento {item['Stato'].lower()}",
                "message": (
                    f"{item['Documento']} · {item['Dipendente']} · "
                    f"scadenza {item['Scadenza']}."
                ),
                "notification_type": "document_expiry",
                "priority": item["Priorità"],
                "alert_key": alert_key,
                "is_read": False,
            }).execute()
            alerts_created += 1

    # Timbrature aperte da oltre 10 ore.
    open_rows = (
        sb.table("clock_entries")
        .select("id,employee_id,clock_in,employees(name)")
        .is_("clock_out", "null")
        .execute().data or []
    )
    for row in open_rows:
        started = parse_db_datetime(row.get("clock_in"))
        if not started:
            continue
        hours_open = (now_rome() - started).total_seconds() / 3600
        if hours_open < 10:
            continue

        alert_key = f"clock:{row['id']}:over10h"
        existing = (
            sb.table("manager_notifications")
            .select("id")
            .eq("alert_key", alert_key)
            .eq("is_read", False)
            .limit(1)
            .execute().data or []
        )
        if not existing:
            employee_data = row.get("employees") or {}
            sb.table("manager_notifications").insert({
                "employee_id": row.get("employee_id"),
                "title": "Turno aperto da oltre 10 ore",
                "message": (
                    f"{employee_data.get('name', 'Dipendente')} risulta "
                    f"in servizio da {hours_open:.1f} ore."
                ),
                "notification_type": "clock_anomaly",
                "priority": "Alta",
                "alert_key": alert_key,
                "is_read": False,
            }).execute()
            alerts_created += 1

    return alerts_created


def executive_monthly_trend(selected_year, selected_month, months_back=12):
    points = []
    cursor_year = selected_year
    cursor_month = selected_month

    for _ in range(months_back):
        revenue_rows = (
            sb.table("monthly_revenue")
            .select("revenue,covers")
            .eq("year", cursor_year)
            .eq("month", cursor_month)
            .execute().data or []
        )
        costs_rows = (
            sb.table("monthly_costs")
            .select("company_cost")
            .eq("year", cursor_year)
            .eq("month", cursor_month)
            .execute().data or []
        )
        timesheet_rows = (
            sb.table("timesheets")
            .select("ordinary_hours,overtime_hours,status,work_date")
            .eq("status", "approved")
            .gte(
                "work_date",
                date(cursor_year, cursor_month, 1).isoformat(),
            )
            .lt(
                "work_date",
                month_bounds(cursor_year, cursor_month)[1].isoformat(),
            )
            .execute().data or []
        )

        revenue = float(revenue_rows[0].get("revenue") or 0) if revenue_rows else 0
        covers = int(revenue_rows[0].get("covers") or 0) if revenue_rows else 0
        cost = sum(float(row.get("company_cost") or 0) for row in costs_rows)
        ordinary = sum(float(row.get("ordinary_hours") or 0) for row in timesheet_rows)
        overtime = sum(float(row.get("overtime_hours") or 0) for row in timesheet_rows)

        points.append({
            "Periodo": f"{cursor_year:04d}-{cursor_month:02d}",
            "Costo personale": round(cost, 2),
            "Fatturato": round(revenue, 2),
            "Incidenza %": round(cost / revenue * 100, 2) if revenue else 0,
            "Ore": round(ordinary + overtime, 2),
            "Straordinari": round(overtime, 2),
            "Coperti": covers,
            "Costo/coperto": round(cost / covers, 2) if covers else 0,
        })

        cursor_month -= 1
        if cursor_month == 0:
            cursor_month = 12
            cursor_year -= 1

    points.reverse()
    return points

def executive_absence_snapshot(selected_year, selected_month):
    start_date, end_date = month_bounds(selected_year, selected_month)
    rows = (
        sb.table("timesheets")
        .select("employee_id,work_date,status,ordinary_hours,overtime_hours")
        .gte("work_date", start_date.isoformat())
        .lt("work_date", end_date.isoformat())
        .execute().data or []
    )

    rejected = sum(1 for row in rows if row.get("status") == "rejected")
    pending = sum(1 for row in rows if row.get("status") == "submitted")
    approved_days = len({
        (row.get("employee_id"), row.get("work_date"))
        for row in rows
        if row.get("status") == "approved"
    })

    return {
        "rejected": rejected,
        "pending": pending,
        "approved_days": approved_days,
    }


def previous_period(selected_year, selected_month):
    if selected_month == 1:
        return selected_year - 1, 12
    return selected_year, selected_month - 1

def personnel_bi_period(selected_year, selected_month):
    df, revenue, covers = month_data(selected_year, selected_month)

    if df.empty:
        return {
            "df": df,
            "revenue": revenue,
            "covers": covers,
            "official_cost": 0.0,
            "management_cost": 0.0,
            "hours": 0.0,
            "overtime": 0.0,
            "incidence": 0.0,
            "cost_per_hour": 0.0,
            "cost_per_cover": 0.0,
            "employee_count": 0,
            "department_costs": {},
            "department_hours": {},
        }

    start_date, end_date = month_bounds(selected_year, selected_month)
    timesheets = (
        sb.table("timesheets")
        .select(
            "employee_id,ordinary_hours,overtime_hours,status,"
            "employees(name,department)"
        )
        .eq("status", "approved")
        .gte("work_date", start_date.isoformat())
        .lt("work_date", end_date.isoformat())
        .execute().data or []
    )

    department_hours = {}
    overtime = 0.0
    for row in timesheets:
        employee = row.get("employees") or {}
        department = employee.get("department") or "Da assegnare"
        ordinary_hours = float(row.get("ordinary_hours") or 0)
        overtime_hours = float(row.get("overtime_hours") or 0)
        department_hours[department] = (
            department_hours.get(department, 0)
            + ordinary_hours
            + overtime_hours
        )
        overtime += overtime_hours

    official_cost = float(df["company_cost"].sum())
    management_cost = float(df["management_cost"].sum())
    hours = float(df["hours"].sum())
    incidence = management_cost / revenue * 100 if revenue else 0
    cost_per_hour = management_cost / hours if hours else 0
    cost_per_cover = management_cost / covers if covers else 0

    department_costs = (
        df.groupby("department")["management_cost"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    return {
        "df": df,
        "revenue": float(revenue or 0),
        "covers": int(covers or 0),
        "official_cost": official_cost,
        "management_cost": management_cost,
        "hours": hours,
        "overtime": overtime,
        "incidence": incidence,
        "cost_per_hour": cost_per_hour,
        "cost_per_cover": cost_per_cover,
        "employee_count": int(df["employee_id"].nunique()),
        "department_costs": department_costs,
        "department_hours": department_hours,
    }

def variation_percent(current_value, previous_value):
    if previous_value == 0:
        return None
    return (current_value - previous_value) / previous_value * 100

def format_variation(value):
    if value is None:
        return "N/D"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"

def personnel_bi_history(selected_year, selected_month, months_back=12):
    rows = []
    cursor_year = selected_year
    cursor_month = selected_month

    for _ in range(months_back):
        period = personnel_bi_period(cursor_year, cursor_month)
        rows.append({
            "Periodo": f"{cursor_year:04d}-{cursor_month:02d}",
            "Costo aziendale": round(period["official_cost"], 2),
            "Costo gestionale": round(period["management_cost"], 2),
            "Fatturato": round(period["revenue"], 2),
            "Incidenza %": round(period["incidence"], 2),
            "Ore": round(period["hours"], 2),
            "Straordinari": round(period["overtime"], 2),
            "Costo/ora": round(period["cost_per_hour"], 2),
            "Costo/coperto": round(period["cost_per_cover"], 2),
            "Dipendenti": period["employee_count"],
        })

        cursor_year, cursor_month = previous_period(cursor_year, cursor_month)

    rows.reverse()
    return rows

def personnel_bi_insights(current_period, previous_period_data):
    insights = []

    cost_change = variation_percent(
        current_period["management_cost"],
        previous_period_data["management_cost"],
    )
    incidence_change = (
        current_period["incidence"] - previous_period_data["incidence"]
        if previous_period_data["incidence"] or current_period["incidence"]
        else None
    )
    overtime_change = variation_percent(
        current_period["overtime"],
        previous_period_data["overtime"],
    )
    hours_change = variation_percent(
        current_period["hours"],
        previous_period_data["hours"],
    )

    if cost_change is not None:
        if cost_change > 5:
            insights.append(
                f"Il costo gestionale del personale è aumentato del "
                f"{cost_change:.1f}% rispetto al mese precedente."
            )
        elif cost_change < -5:
            insights.append(
                f"Il costo gestionale del personale è diminuito del "
                f"{abs(cost_change):.1f}% rispetto al mese precedente."
            )

    if incidence_change is not None:
        if incidence_change > 2:
            insights.append(
                f"L'incidenza del personale è peggiorata di "
                f"{incidence_change:.1f} punti percentuali."
            )
        elif incidence_change < -2:
            insights.append(
                f"L'incidenza del personale è migliorata di "
                f"{abs(incidence_change):.1f} punti percentuali."
            )

    if overtime_change is not None and overtime_change > 20:
        insights.append(
            f"Gli straordinari sono aumentati del {overtime_change:.1f}%."
        )

    if hours_change is not None and current_period["management_cost"] > 0:
        if hours_change < -10 and (cost_change or 0) > 0:
            insights.append(
                "Le ore sono diminuite, ma il costo è aumentato: "
                "verifica premi, extra, livelli contrattuali o componenti una tantum."
            )

    if current_period["incidence"] > 35:
        insights.append(
            f"Incidenza personale elevata: {current_period['incidence']:.1f}%."
        )
    elif 0 < current_period["incidence"] <= 30:
        insights.append(
            f"Incidenza personale sotto il 30%: "
            f"{current_period['incidence']:.1f}%."
        )

    if current_period["department_costs"]:
        top_department = max(
            current_period["department_costs"],
            key=current_period["department_costs"].get,
        )
        top_value = current_period["department_costs"][top_department]
        total = current_period["management_cost"]
        share = top_value / total * 100 if total else 0
        insights.append(
            f"Il reparto con il costo più alto è {top_department}: "
            f"{euro(top_value)}, pari al {share:.1f}% del totale."
        )

    if not insights:
        insights.append(
            "Non emergono variazioni rilevanti rispetto al mese precedente."
        )

    return insights

st.sidebar.markdown(
    """
    <div class="rv-brand">
        <div class="rv-brand-mark">RV</div>
        <div>
            <div class="rv-brand-title">RV Manager</div>
            <div class="rv-brand-subtitle">Enterprise 3.0</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

MENU_ICONS = {
    "Cruscotto": "⌂",
    "Business Intelligence": "▥",
    "AI Manager": "✦",
    "Registro eventi": "≡",
    "Importa costi": "⇧",
    "Dipendenti": "◉",
    "Scheda dipendente": "◎",
    "Ore e approvazioni": "◷",
    "Accessi dipendenti": "◇",
    "Buste paga": "▤",
    "Centro documenti": "□",
    "Centro notifiche": "●",
    "Fringe benefit": "◆",
    "Extra da regolarizzare": "△",
    "Dati del mese": "▦",
}

MENU_ITEMS = [
    "Cruscotto",
    "Business Intelligence",
    "AI Manager",
    "Registro eventi",
    "Importa costi",
    "Dipendenti",
    "Scheda dipendente",
    "Ore e approvazioni",
    "Accessi dipendenti",
    "Buste paga",
    "Centro documenti",
    "Centro notifiche",
    "Fringe benefit",
    "Extra da regolarizzare",
    "Dati del mese",
]

section = st.sidebar.radio(
    "Navigazione",
    MENU_ITEMS,
    format_func=lambda item: f"{MENU_ICONS[item]}  {item}",
    label_visibility="collapsed",
)

today = date.today()
years = list(range(2025, today.year + 2))
year = st.sidebar.selectbox("Anno", years, index=years.index(today.year))
month = st.sidebar.selectbox("Mese", list(MONTHS), format_func=lambda x: MONTHS[x], index=today.month - 1)

if section == "Cruscotto":
    st.title("Dashboard direzionale")
    st.caption(
        f"Panoramica operativa e indicatori del personale · "
        f"{MONTHS[month]} {year}"
    )

    snapshot = manager_daily_snapshot(year, month)
    absence_snapshot = executive_absence_snapshot(year, month)
    trend_rows = executive_monthly_trend(year, month, 12)

    df, revenue, covers = month_data(year, month)
    monthly_cost = float(df["management_cost"].sum()) if not df.empty else 0
    monthly_hours = float(df["hours"].sum()) if not df.empty else 0
    monthly_overtime = float(snapshot["overtime_total"])
    cost_per_cover = monthly_cost / covers if covers else 0
    average_hour_cost = monthly_cost / monthly_hours if monthly_hours else 0

    # Riepilogo direzionale
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Costo personale oggi", euro(snapshot["today_cost"]))
    r2.metric("Costo personale mese", euro(monthly_cost))
    r3.metric("Ore lavorate oggi", f"{snapshot['today_hours']:.2f}")
    r4.metric("Ore mese", f"{monthly_hours:.2f}")

    r5, r6, r7, r8 = st.columns(4)
    r5.metric("Straordinari mese", f"{monthly_overtime:.2f}")
    r6.metric("Incidenza personale", f"{snapshot['incidence']:.1f}%")
    r7.metric("Costo/coperto", euro(cost_per_cover) if covers else "N/D")
    r8.metric("Costo medio/ora", euro(average_hour_cost) if monthly_hours else "N/D")

    r9, r10, r11, r12 = st.columns(4)
    r9.metric(
        "Presenti adesso",
        f"{snapshot['present_now']} / {snapshot['active_employees']}",
    )
    r10.metric("Ore da approvare", snapshot["pending_count"])
    r11.metric("Registrazioni rifiutate", absence_snapshot["rejected"])
    r12.metric("Documenti in scadenza", len(document_expiry_snapshot(30)))

    ensure_automatic_manager_alerts()

    st.subheader("Centro operativo")
    for task in snapshot["agenda"]:
        st.write(f"• {task}")

    expiry_items = document_expiry_snapshot(30)
    manager_alerts = [
        row for row in manager_notification_snapshot(20)
        if not row["Letta"]
    ]

    if snapshot["anomalies"] or expiry_items or manager_alerts:
        st.subheader("Avvisi prioritari")

        combined_alerts = []
        for row in snapshot["anomalies"]:
            combined_alerts.append({
                "Priorità": row.get("Priorità", "Media"),
                "Area": "Presenze",
                "Dettaglio": (
                    f"{row.get('Dipendente', '')} · "
                    f"{row.get('Anomalia', '')}"
                ),
            })
        for row in expiry_items[:10]:
            combined_alerts.append({
                "Priorità": row.get("Priorità", "Media"),
                "Area": "Documenti",
                "Dettaglio": (
                    f"{row.get('Dipendente', '')} · "
                    f"{row.get('Documento', '')} · "
                    f"{row.get('Scadenza', '')}"
                ),
            })
        for row in manager_alerts[:10]:
            combined_alerts.append({
                "Priorità": row.get("Priorità", "Media"),
                "Area": "Notifiche",
                "Dettaglio": row.get("Messaggio", ""),
            })

        st.dataframe(
            pd.DataFrame(combined_alerts),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("Nessuna anomalia o scadenza urgente.")

    tab_summary, tab_trend, tab_people, tab_calendar = st.tabs(
        [
            "Sintesi economica",
            "Andamento 12 mesi",
            "Personale e reparti",
            "Calendario presenze",
        ]
    )

    with tab_summary:
        if df.empty:
            st.info("Non risultano ancora costi importati per questo mese.")
        else:
            official = df["company_cost"].sum()
            extra = df["extra_cash"].sum()
            fringe = df["fringe"].sum()
            total = df["management_cost"].sum()
            incidence = total / revenue * 100 if revenue else 0

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Costo aziendale", euro(official))
            s2.metric("Extra registrati", euro(extra))
            s3.metric("Fringe benefit", euro(fringe))
            s4.metric("Costo gestionale", euro(total))

            s5, s6, s7 = st.columns(3)
            s5.metric("Fatturato", euro(revenue))
            s6.metric("Coperti", covers)
            s7.metric("Incidenza", f"{incidence:.1f}%")

            st.subheader("Costo per reparto")
            st.bar_chart(df.groupby("department")["management_cost"].sum())

            view = df[[
                "name", "department", "hours", "net_pay", "gross_pay",
                "company_cost", "fringe", "extra_cash", "management_cost"
            ]].copy()
            view.columns = [
                "Dipendente", "Reparto", "Ore", "Netto", "Lordo",
                "Costo azienda", "Fringe", "Extra", "Costo gestionale"
            ]
            for column in [
                "Netto", "Lordo", "Costo azienda",
                "Fringe", "Extra", "Costo gestionale"
            ]:
                view[column] = view[column].map(euro)

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
            )

    with tab_trend:
        trend_df = pd.DataFrame(trend_rows)

        if trend_df.empty:
            st.info("Non sono disponibili dati storici.")
        else:
            st.subheader("Costo personale e fatturato")
            st.line_chart(
                trend_df.set_index("Periodo")[
                    ["Costo personale", "Fatturato"]
                ]
            )

            st.subheader("Incidenza del personale")
            st.line_chart(
                trend_df.set_index("Periodo")[["Incidenza %"]]
            )

            t1, t2 = st.columns(2)
            with t1:
                st.subheader("Ore e straordinari")
                st.bar_chart(
                    trend_df.set_index("Periodo")[["Ore", "Straordinari"]]
                )
            with t2:
                st.subheader("Costo per coperto")
                st.line_chart(
                    trend_df.set_index("Periodo")[["Costo/coperto"]]
                )

            st.dataframe(
                trend_df,
                use_container_width=True,
                hide_index=True,
            )

    with tab_people:
        if snapshot["present_now"] > 0:
            st.subheader("Personale attualmente in servizio")
            current_rows = (
                sb.table("clock_entries")
                .select(
                    "employee_id,clock_in,shift_type,"
                    "employees(name,department)"
                )
                .eq("work_date", date.today().isoformat())
                .is_("clock_out", "null")
                .order("clock_in")
                .execute().data or []
            )

            current_view = []
            for row in current_rows:
                employee_data = row.get("employees") or {}
                started = parse_db_datetime(row["clock_in"])
                elapsed_hours = (
                    (now_rome() - started).total_seconds() / 3600
                    if started else 0
                )
                current_view.append({
                    "Dipendente": employee_data.get("name", ""),
                    "Reparto": employee_data.get("department", ""),
                    "Entrata": started.strftime("%H:%M") if started else "",
                    "Ore aperte": round(max(elapsed_hours, 0), 2),
                    "Turno": row.get("shift_type", ""),
                })

            st.dataframe(
                pd.DataFrame(current_view),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nessun dipendente attualmente in servizio.")

        if snapshot["dept_hours"]:
            st.subheader("Ore approvate per reparto")
            st.bar_chart(
                pd.Series(snapshot["dept_hours"]).sort_values(
                    ascending=False
                )
            )
        else:
            st.info("Non risultano ancora ore approvate per reparto.")

        p1, p2, p3 = st.columns(3)
        p1.metric(
            "Giornate approvate",
            absence_snapshot["approved_days"],
        )
        p2.metric(
            "In attesa di approvazione",
            absence_snapshot["pending"],
        )
        p3.metric(
            "Registrazioni rifiutate",
            absence_snapshot["rejected"],
        )

    with tab_calendar:
        st.dataframe(
            pd.DataFrame(snapshot["calendar_rows"]),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Accesso rapido")
    q1, q2, q3, q4 = st.columns(4)
    q1.info("👥 Dipendenti")
    q2.info("⏰ Ore e approvazioni")
    q3.info("📄 Documenti e buste paga")
    q4.info("🔔 Notifiche e scadenze")


elif section == "Business Intelligence":
    st.title("Business Intelligence del personale")
    st.caption(
        f"Analisi comparativa · {MONTHS[month]} {year}"
    )

    current = personnel_bi_period(year, month)
    prev_year, prev_month = previous_period(year, month)
    previous = personnel_bi_period(prev_year, prev_month)

    if current["df"].empty:
        st.info(
            "Non risultano dati del personale per il periodo selezionato."
        )
    else:
        cost_change = variation_percent(
            current["management_cost"],
            previous["management_cost"],
        )
        hours_change = variation_percent(
            current["hours"],
            previous["hours"],
        )
        overtime_change = variation_percent(
            current["overtime"],
            previous["overtime"],
        )
        incidence_delta = (
            current["incidence"] - previous["incidence"]
            if previous["incidence"] or current["incidence"]
            else None
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric(
            "Costo gestionale",
            euro(current["management_cost"]),
            format_variation(cost_change),
        )
        k2.metric(
            "Incidenza personale",
            f"{current['incidence']:.1f}%",
            (
                f"{incidence_delta:+.1f} pt"
                if incidence_delta is not None else "N/D"
            ),
            delta_color="inverse",
        )
        k3.metric(
            "Ore lavorate",
            f"{current['hours']:.2f}",
            format_variation(hours_change),
        )
        k4.metric(
            "Straordinari",
            f"{current['overtime']:.2f}",
            format_variation(overtime_change),
            delta_color="inverse",
        )

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("Costo medio/ora", euro(current["cost_per_hour"]))
        k6.metric("Costo/coperto", euro(current["cost_per_cover"]))
        k7.metric("Dipendenti nel mese", current["employee_count"])
        k8.metric("Fatturato", euro(current["revenue"]))

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "Confronto mensile",
                "Reparti",
                "Dipendenti",
                "Indicatori e suggerimenti",
            ]
        )

        with tab1:
            history = pd.DataFrame(
                personnel_bi_history(year, month, 12)
            )

            st.subheader("Costo e fatturato")
            st.line_chart(
                history.set_index("Periodo")[
                    ["Costo gestionale", "Fatturato"]
                ]
            )

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Incidenza personale")
                st.line_chart(
                    history.set_index("Periodo")[["Incidenza %"]]
                )
            with c2:
                st.subheader("Costo medio per ora")
                st.line_chart(
                    history.set_index("Periodo")[["Costo/ora"]]
                )

            c3, c4 = st.columns(2)
            with c3:
                st.subheader("Ore e straordinari")
                st.bar_chart(
                    history.set_index("Periodo")[["Ore", "Straordinari"]]
                )
            with c4:
                st.subheader("Costo per coperto")
                st.line_chart(
                    history.set_index("Periodo")[["Costo/coperto"]]
                )

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
            )

        with tab2:
            department_costs = pd.Series(
                current["department_costs"],
                name="Costo gestionale",
            ).sort_values(ascending=False)

            department_hours = pd.Series(
                current["department_hours"],
                name="Ore approvate",
            ).sort_values(ascending=False)

            d1, d2 = st.columns(2)
            with d1:
                st.subheader("Costo per reparto")
                if department_costs.empty:
                    st.info("Nessun costo disponibile.")
                else:
                    st.bar_chart(department_costs)

            with d2:
                st.subheader("Ore per reparto")
                if department_hours.empty:
                    st.info("Nessuna ora approvata disponibile.")
                else:
                    st.bar_chart(department_hours)

            department_rows = []
            departments = sorted(
                set(current["department_costs"])
                | set(current["department_hours"])
            )
            for department in departments:
                department_cost = float(
                    current["department_costs"].get(department, 0)
                )
                department_hours_value = float(
                    current["department_hours"].get(department, 0)
                )
                department_rows.append({
                    "Reparto": department,
                    "Costo": department_cost,
                    "Ore": department_hours_value,
                    "Costo/ora": (
                        department_cost / department_hours_value
                        if department_hours_value else 0
                    ),
                    "Peso sul costo %": (
                        department_cost / current["management_cost"] * 100
                        if current["management_cost"] else 0
                    ),
                })

            department_df = pd.DataFrame(department_rows)
            if not department_df.empty:
                department_df["Costo"] = department_df["Costo"].map(euro)
                department_df["Costo/ora"] = (
                    department_df["Costo/ora"].map(euro)
                )
                department_df["Peso sul costo %"] = (
                    department_df["Peso sul costo %"]
                    .map(lambda value: f"{value:.1f}%")
                )

            st.dataframe(
                department_df,
                use_container_width=True,
                hide_index=True,
            )

        with tab3:
            employee_df = current["df"].copy()
            employee_df["Costo/ora"] = employee_df.apply(
                lambda row: (
                    row["management_cost"] / row["hours"]
                    if row["hours"] else 0
                ),
                axis=1,
            )
            employee_df["Peso sul totale %"] = employee_df[
                "management_cost"
            ].apply(
                lambda value: (
                    value / current["management_cost"] * 100
                    if current["management_cost"] else 0
                )
            )

            employee_view = employee_df[[
                "name",
                "department",
                "hours",
                "gross_pay",
                "company_cost",
                "extra_cash",
                "management_cost",
                "Costo/ora",
                "Peso sul totale %",
            ]].copy()
            employee_view.columns = [
                "Dipendente",
                "Reparto",
                "Ore",
                "Lordo",
                "Costo azienda",
                "Extra",
                "Costo gestionale",
                "Costo/ora",
                "Peso sul totale %",
            ]

            for column in [
                "Lordo",
                "Costo azienda",
                "Extra",
                "Costo gestionale",
                "Costo/ora",
            ]:
                employee_view[column] = employee_view[column].map(euro)

            employee_view["Peso sul totale %"] = (
                employee_view["Peso sul totale %"]
                .map(lambda value: f"{value:.1f}%")
            )

            st.dataframe(
                employee_view.sort_values(
                    "Costo gestionale",
                    ascending=False,
                ),
                use_container_width=True,
                hide_index=True,
            )

        with tab4:
            st.subheader("Lettura automatica dei dati")
            for insight in personnel_bi_insights(current, previous):
                st.write(f"• {insight}")

            st.subheader("Confronto con il mese precedente")
            comparison_rows = [
                {
                    "Indicatore": "Costo gestionale",
                    "Mese corrente": euro(current["management_cost"]),
                    "Mese precedente": euro(previous["management_cost"]),
                    "Variazione": format_variation(cost_change),
                },
                {
                    "Indicatore": "Incidenza personale",
                    "Mese corrente": f"{current['incidence']:.1f}%",
                    "Mese precedente": f"{previous['incidence']:.1f}%",
                    "Variazione": (
                        f"{incidence_delta:+.1f} pt"
                        if incidence_delta is not None else "N/D"
                    ),
                },
                {
                    "Indicatore": "Ore lavorate",
                    "Mese corrente": f"{current['hours']:.2f}",
                    "Mese precedente": f"{previous['hours']:.2f}",
                    "Variazione": format_variation(hours_change),
                },
                {
                    "Indicatore": "Straordinari",
                    "Mese corrente": f"{current['overtime']:.2f}",
                    "Mese precedente": f"{previous['overtime']:.2f}",
                    "Variazione": format_variation(overtime_change),
                },
                {
                    "Indicatore": "Costo/coperto",
                    "Mese corrente": euro(current["cost_per_cover"]),
                    "Mese precedente": euro(previous["cost_per_cover"]),
                    "Variazione": format_variation(
                        variation_percent(
                            current["cost_per_cover"],
                            previous["cost_per_cover"],
                        )
                    ),
                },
            ]

            st.dataframe(
                pd.DataFrame(comparison_rows),
                use_container_width=True,
                hide_index=True,
            )



elif section == "AI Manager":
    st.title("AI Manager del personale")
    st.caption(
        "Analisi automatica basata sui dati reali del gestionale. "
        "Non invia dati a servizi esterni."
    )

    current = personnel_bi_period(year, month)
    previous_year, previous_month = previous_period(year, month)
    previous = personnel_bi_period(previous_year, previous_month)

    if current["df"].empty:
        st.info("Non ci sono dati sufficienti per il periodo selezionato.")
    else:
        insights = build_personnel_insights(current, previous)

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Costo gestionale", euro(current["management_cost"]))
        a2.metric("Incidenza", f"{current['incidence']:.1f}%")
        a3.metric("Straordinari", f"{current['overtime']:.2f}")
        a4.metric("Costo/coperto", euro(current["cost_per_cover"]))

        st.subheader("Analisi e azioni suggerite")
        for insight in insights:
            render_insight(insight)

        st.subheader("Domande guidate")
        question = st.selectbox(
            "Cosa vuoi analizzare?",
            [
                "Perché è cambiato il costo del personale?",
                "Quale reparto pesa di più?",
                "Gli straordinari sono sotto controllo?",
                "L'incidenza del personale è sostenibile?",
            ],
        )

        if question == "Perché è cambiato il costo del personale?":
            current_cost = current["management_cost"]
            previous_cost = previous["management_cost"]
            difference = current_cost - previous_cost
            st.write(
                f"Il costo è variato di **{euro(difference)}** rispetto al "
                f"mese precedente. Verifica ore, extra, fringe e componenti "
                f"una tantum nel dettaglio dipendenti."
            )
        elif question == "Quale reparto pesa di più?":
            if current["department_costs"]:
                department = max(
                    current["department_costs"],
                    key=current["department_costs"].get,
                )
                value = current["department_costs"][department]
                st.write(
                    f"Il reparto con il costo maggiore è **{department}**, "
                    f"con **{euro(value)}**."
                )
            else:
                st.info("Non sono disponibili costi per reparto.")
        elif question == "Gli straordinari sono sotto controllo?":
            if current["overtime"] >= 20:
                st.warning(
                    f"Risultano {current['overtime']:.2f} ore di straordinario. "
                    "È consigliabile verificare il dettaglio per dipendente."
                )
            else:
                st.success(
                    f"Gli straordinari risultano pari a "
                    f"{current['overtime']:.2f} ore."
                )
        else:
            if current["incidence"] >= 35:
                st.error(
                    f"L'incidenza è {current['incidence']:.1f}%, "
                    "quindi richiede attenzione."
                )
            elif current["incidence"] > 0:
                st.success(
                    f"L'incidenza è {current['incidence']:.1f}%."
                )
            else:
                st.info("Manca il fatturato del mese.")

elif section == "Registro eventi":
    st.title("Registro eventi aziendali")
    st.caption(
        "Cronologia delle operazioni importanti del gestionale."
    )

    events = recent_events(sb, 200)
    if not events:
        st.info(
            "Il registro è vuoto. I nuovi eventi verranno salvati "
            "dopo l'installazione della migrazione Enterprise 2.0."
        )
    else:
        rows = []
        for event in events:
            employee = event.get("employees") or {}
            rows.append({
                "Data": event.get("created_at", ""),
                "Tipo": event.get("event_type", ""),
                "Titolo": event.get("title", ""),
                "Gravità": event.get("severity", ""),
                "Dipendente": employee.get("name", ""),
                "Entità": event.get("entity_type", ""),
                "ID entità": event.get("entity_id", ""),
            })

        event_df = pd.DataFrame(rows)
        filter_type = st.selectbox(
            "Filtra per tipo",
            ["Tutti"] + sorted(event_df["Tipo"].dropna().unique().tolist()),
        )
        if filter_type != "Tutti":
            event_df = event_df[event_df["Tipo"] == filter_type]

        st.dataframe(
            event_df,
            use_container_width=True,
            hide_index=True,
        )


elif section == "Importa costi":
    st.title("Importa prospetto costi paghe")
    st.caption("Il mese e l’anno vengono letti automaticamente dal PDF, indipendentemente dai filtri laterali.")
    uploaded = st.file_uploader("PDF del consulente", type=["pdf"])
    if uploaded and st.button("Importa", type="primary"):
        try:
            y, m, count, total = import_cost_pdf(uploaded)
            st.success(f"Importati {count} dipendenti per {MONTHS[m]} {y}. Totale: {euro(total)}")
        except Exception as exc:
            st.error(str(exc))

    employees = employees_df()
    if not employees.empty:
        st.divider()
        st.subheader("Ore e netto")
        name = st.selectbox("Dipendente", employees["name"].tolist())
        employee_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
        c1, c2 = st.columns(2)
        hours = c1.number_input("Ore del mese", min_value=0.0, step=0.5)
        net = c2.number_input("Netto in busta", min_value=0.0, step=10.0)
        if st.button("Salva ore e netto"):
            sb.table("monthly_costs").upsert({
                "employee_id": employee_id, "year": year, "month": month,
                "hours": hours, "net_pay": net
            }, on_conflict="employee_id,year,month").execute()
            st.success("Aggiornato.")

elif section == "Dipendenti":
    st.title("Dipendenti")
    employees = employees_df()

    with st.expander("Nuovo dipendente", expanded=employees.empty):
        with st.form("new_emp"):
            code = st.text_input("Codice dipendente")
            name = st.text_input("Nome e cognome")
            c1, c2, c3 = st.columns(3)
            department = c1.selectbox("Reparto", ["Sala", "Bar", "Cucina", "Amministrazione", "Da assegnare"])
            role = c2.text_input("Ruolo")
            level = c3.text_input("Livello")
            save = st.form_submit_button("Crea", type="primary")
        if save:
            sb.table("employees").insert({
                "code": code or None, "name": name, "department": department,
                "role": role or None, "level": level or None, "active": True
            }).execute()
            log_event(
                sb,
                "employee_created",
                f"Dipendente creato: {name}",
                entity_type="employee",
                details={"name": name, "department": department},
            )
            st.success("Dipendente creato.")
            st.rerun()

    if not employees.empty:
        edited = st.data_editor(
            employees, use_container_width=True, hide_index=True,
            disabled=["id", "code", "name"],
            column_config={
                "department": st.column_config.SelectboxColumn(
                    "Reparto", options=["Sala", "Bar", "Cucina", "Amministrazione", "Da assegnare"]
                ),
                "active": st.column_config.CheckboxColumn("Attivo")
            }
        )
        if st.button("Salva modifiche"):
            for _, r in edited.iterrows():
                sb.table("employees").update({
                    "department": r["department"],
                    "role": None if pd.isna(r["role"]) else r["role"],
                    "level": None if pd.isna(r["level"]) else r["level"],
                    "active": bool(r["active"])
                }).eq("id", int(r["id"])).execute()
            st.success("Salvato.")

elif section == "Scheda dipendente":
    st.title("Scheda dipendente")
    employees = employees_df()
    if employees.empty:
        st.info("Nessun dipendente.")
    else:
        name = st.selectbox("Dipendente", employees["name"].tolist())
        emp = employees.loc[employees["name"] == name].iloc[0]
        employee_id = int(emp["id"])

        a, b, c = st.columns(3)
        a.metric("Reparto", emp["department"] or "Da assegnare")
        b.metric("Ruolo", emp["role"] or "Da definire")
        c.metric("Livello", emp["level"] or "Da definire")

        profile_data = sb.table("employee_profiles").select("*").eq("employee_id", employee_id).execute().data or []
        profile = profile_data[0] if profile_data else {}

        with st.form("profile"):
            c1, c2 = st.columns(2)
            phone = c1.text_input("Telefono", value=profile.get("phone") or "")
            email = c2.text_input("Email", value=profile.get("email") or "")
            tax_code = c1.text_input("Codice fiscale", value=profile.get("tax_code") or "")
            iban = c2.text_input("IBAN", value=profile.get("iban") or "")
            address = st.text_input("Indirizzo", value=profile.get("address") or "")
            contract_type = c1.text_input("Tipo contratto", value=profile.get("contract_type") or "")
            contract_end = c2.text_input("Scadenza contratto AAAA-MM-GG", value=str(profile.get("contract_end") or ""))
            weekly_hours = c1.number_input("Ore settimanali", min_value=0.0, value=float(profile.get("weekly_hours") or 0))
            emergency = c2.text_input("Contatto emergenza", value=profile.get("emergency_contact") or "")
            notes = st.text_area("Note", value=profile.get("notes") or "")
            save = st.form_submit_button("Salva scheda", type="primary")
        if save:
            sb.table("employee_profiles").upsert({
                "employee_id": employee_id, "phone": phone, "email": email,
                "tax_code": tax_code, "iban": iban, "address": address,
                "contract_type": contract_type or None,
                "contract_end": contract_end or None,
                "weekly_hours": weekly_hours,
                "emergency_contact": emergency, "notes": notes
            }, on_conflict="employee_id").execute()
            st.success("Scheda salvata.")

        history = (
            sb.table("monthly_costs")
            .select("year,month,hours,net_pay,gross_pay,company_cost")
            .eq("employee_id", employee_id)
            .order("year", desc=True).order("month", desc=True)
            .execute().data or []
        )
        st.subheader("Storico costi")
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)


elif section == "Ore e approvazioni":
    st.title("Gestione ore dipendenti")
    st.caption("Inserisci entrata, uscita e pausa: il totale viene calcolato automaticamente.")

    employees = employees_df()
    if employees.empty:
        st.info("Nessun dipendente presente.")
    else:
        selected_name = st.selectbox("Dipendente", employees["name"].tolist())
        employee_id = int(employees.loc[employees["name"] == selected_name, "id"].iloc[0])

        tab1, tab2 = st.tabs(["Inserimento rapido", "Approvazione ore"])

        with tab1:
            with st.form("admin_hours_simple", clear_on_submit=False):
                c1, c2 = st.columns(2)
                work_date = c1.date_input("Giorno", value=date(year, month, 1))
                shift_type = c2.selectbox("Turno", ["Pranzo", "Cena", "Spezzato", "Altro"])

                c3, c4, c5 = st.columns(3)
                start_time = c3.time_input("Entrata", value=time(9, 0))
                end_time = c4.time_input("Uscita", value=time(17, 0))
                break_minutes = c5.number_input(
                    "Pausa (minuti)", min_value=0, max_value=480, value=0, step=5
                )

                note = st.text_input("Nota")
                save = st.form_submit_button("Calcola, salva e approva", type="primary")

            if save:
                gross_minutes = minutes_between(start_time, end_time)
                worked_minutes = max(gross_minutes - int(break_minutes), 0)
                total_hours = decimal_hours(worked_minutes)
                ordinary_hours = min(total_hours, 8)
                overtime_hours = max(round(total_hours - 8, 2), 0)

                sb.table("timesheets").upsert({
                    "employee_id": employee_id,
                    "work_date": work_date.isoformat(),
                    "ordinary_hours": ordinary_hours,
                    "overtime_hours": overtime_hours,
                    "break_hours": round(break_minutes / 60, 2),
                    "shift_type": shift_type,
                    "status": "approved",
                    "note": note or "Inserimento rapido del responsabile",
                    "approved_at": now_rome().isoformat(),
                }, on_conflict="employee_id,work_date").execute()

                total = sync_monthly_hours(employee_id, work_date.year, work_date.month)
                audit(
                    "timesheet_admin_saved",
                    "Ore inserite e approvate dal responsabile",
                    employee_id=employee_id,
                    entity_type="timesheet",
                    entity_id=work_date.isoformat(),
                    details={
                        "ordinary_hours": ordinary_hours,
                        "overtime_hours": overtime_hours,
                        "break_minutes": int(break_minutes),
                        "shift_type": shift_type,
                    },
                )
                st.success(
                    f"Giornata salvata: {total_hours:.2f} ore "
                    f"({ordinary_hours:.2f} ordinarie + {overtime_hours:.2f} straordinarie). "
                    f"Totale approvato del mese: {total:.2f} ore."
                )

        with tab2:
            st.subheader("Timbrature registrate")
            start_date, end_date = month_bounds(year, month)
            clock_rows = (
                sb.table("clock_entries")
                .select("id,work_date,clock_in,clock_out,break_minutes,shift_type,status")
                .eq("employee_id", employee_id)
                .gte("work_date", start_date.isoformat())
                .lt("work_date", end_date.isoformat())
                .order("work_date")
                .execute().data or []
            )
            if clock_rows:
                st.dataframe(pd.DataFrame(clock_rows), use_container_width=True, hide_index=True)
            else:
                st.info("Nessuna timbratura registrata per il mese selezionato.")

            records = get_month_timesheets(employee_id, year, month, sb)
            df = pd.DataFrame(records)
            if df.empty:
                st.info("Nessuna ora presente per il mese selezionato.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                pending = [r for r in records if r.get("status") == "submitted"]
                if pending:
                    options = {
                        f"{r['work_date']} · "
                        f"{float(r.get('ordinary_hours') or 0)+float(r.get('overtime_hours') or 0):.2f} ore":
                        r["id"]
                        for r in pending
                    }
                    selected = st.selectbox("Voce da approvare", list(options.keys()))
                    c1, c2 = st.columns(2)
                    if c1.button("Approva", type="primary"):
                        sb.table("timesheets").update({
                            "status": "approved",
                            "approved_at": now_rome().isoformat(),
                        }).eq("id", options[selected]).execute()
                        total = sync_monthly_hours(employee_id, year, month)
                        audit(
                            "timesheet_approved",
                            "Registrazione ore approvata",
                            employee_id=employee_id,
                            entity_type="timesheet",
                            entity_id=options[selected],
                            details={"year": year, "month": month, "monthly_total": total},
                        )
                        st.success(f"Approvata. Totale mensile: {total:.2f} ore.")
                        st.rerun()
                    if c2.button("Rifiuta"):
                        sb.table("timesheets").update({
                            "status": "rejected",
                        }).eq("id", options[selected]).execute()
                        audit(
                            "timesheet_rejected",
                            "Registrazione ore rifiutata",
                            employee_id=employee_id,
                            entity_type="timesheet",
                            entity_id=options[selected],
                            severity="warning",
                        )
                        st.warning("Voce rifiutata.")
                        st.rerun()
                else:
                    st.success("Non ci sono ore in attesa di approvazione.")

elif section == "Accessi dipendenti":
    st.title("Account dipendenti")
    st.caption(
        "Crea direttamente qui email e password temporanea. "
        "Non è più necessario entrare in Supabase Authentication."
    )

    employees = employees_df()
    if employees.empty:
        st.info("Nessun dipendente presente.")
    else:
        with st.form("create_employee_account"):
            selected_name = st.selectbox("Dipendente", employees["name"].tolist())
            employee_id = int(employees.loc[employees["name"] == selected_name, "id"].iloc[0])
            email = st.text_input("Email di accesso")
            password = st.text_input(
                "Password temporanea",
                type="password",
                help="Almeno 8 caratteri. Comunicala direttamente al dipendente.",
            )
            role = st.selectbox("Ruolo", ["employee", "manager"])
            create = st.form_submit_button("Crea account", type="primary")

        if create:
            if not email.strip() or len(password) < 8:
                st.error("Inserisci un'email valida e una password di almeno 8 caratteri.")
            else:
                try:
                    created = sb.auth.admin.create_user({
                        "email": email.strip(),
                        "password": password,
                        "email_confirm": True,
                    })
                    user_id = created.user.id
                    sb.table("employee_accounts").upsert({
                        "auth_user_id": user_id,
                        "employee_id": employee_id,
                        "role": role,
                    }, on_conflict="auth_user_id").execute()
                    audit(
                        "employee_account_created",
                        "Account dipendente creato",
                        employee_id=employee_id,
                        entity_type="employee_account",
                        entity_id=user_id,
                        details={"email": email.strip(), "role": role},
                    )
                    st.success(
                        "Account creato. Il dipendente può accedere dall'indirizzo "
                        "dell'app aggiungendo ?area=dipendente"
                    )
                except Exception as exc:
                    st.error(f"Creazione non riuscita: {exc}")

        st.subheader("Indirizzo area dipendente")
        st.code("https://rv-manager.streamlit.app/?area=dipendente")

        accounts = (
            sb.table("employee_accounts")
            .select("auth_user_id,role,employees(name,department)")
            .execute().data or []
        )
        if accounts:
            st.dataframe(pd.DataFrame(accounts), use_container_width=True, hide_index=True)
        else:
            st.info("Non sono ancora stati creati account.")


elif section == "Buste paga":
    st.title("Buste paga")
    st.caption(
        "Carica il PDF cumulativo del commercialista. Il programma divide le pagine "
        "e pubblica ogni documento nell'area privata del dipendente."
    )
    st.warning(
        "Prima di caricare documenti reali, rigenera le chiavi Supabase già apparse "
        "negli screenshot e aggiorna i Secrets di Streamlit."
    )

    uploaded = st.file_uploader("PDF cumulativo delle buste paga", type=["pdf"])
    c1, c2 = st.columns(2)
    fallback_year = c1.selectbox(
        "Anno di riferimento",
        list(range(2025, date.today().year + 2)),
        index=list(range(2025, date.today().year + 2)).index(year),
    )
    fallback_month = c2.selectbox(
        "Mese di riferimento",
        list(MONTHS),
        format_func=lambda x: MONTHS[x],
        index=month - 1,
    )
    st.caption(
        "Mese e anno vengono cercati nel PDF. Questi campi sono usati solo "
        "se il periodo non è leggibile nel documento."
    )

    if uploaded and st.button("Dividi e pubblica", type="primary"):
        try:
            saved, unresolved, recognized_preview = split_and_store_payslips(
                uploaded, fallback_year, fallback_month
            )
            employee_names = {
                int(row["id"]): row["name"]
                for row in sb.table("employees").select("id,name").execute().data or []
            }
            st.success(f"Pubblicate {len(saved)} buste paga.")
            if recognized_preview:
                st.subheader("Pagine riconosciute")
                st.dataframe(
                    pd.DataFrame(recognized_preview),
                    use_container_width=True,
                    hide_index=True,
                )

            result_rows = []
            for item in saved:
                result_rows.append({
                    "Dipendente": employee_names.get(item["employee_id"], item["employee_id"]),
                    "Periodo": f"{MONTHS[item['month']]} {item['year']}",
                    "Pagine": ", ".join(map(str, item["pages"])),
                    "Stato": "Pubblicata",
                })
            st.subheader("Documenti pubblicati")
            st.dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)

            if unresolved:
                st.warning(
                    "Pagine non riconosciute e non pubblicate: "
                    + ", ".join(map(str, unresolved))
                )
        except Exception as exc:
            st.error(f"Elaborazione non riuscita: {type(exc).__name__}: {exc}")
            st.caption(
                "Il PDF non viene pubblicato se l'elaborazione non termina correttamente."
            )

    st.divider()
    st.subheader("Archivio pubblicato")
    archive = (
        sb.table("payslips")
        .select("id,year,month,storage_path,page_count,status,employees(name)")
        .order("year", desc=True)
        .order("month", desc=True)
        .execute().data or []
    )
    if archive:
        archive_rows = []
        for document in archive:
            employee = document.get("employees") or {}
            archive_rows.append({
                "Dipendente": employee.get("name", ""),
                "Periodo": f"{MONTHS[int(document['month'])]} {int(document['year'])}",
                "Pagine": int(document.get("page_count") or 1),
                "Stato": document.get("status"),
                "Percorso": document.get("storage_path"),
            })
        st.dataframe(pd.DataFrame(archive_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna busta paga pubblicata.")



elif section == "Centro documenti":
    st.title("Centro documenti")
    st.caption(
        "Carica contratti, CU, attestati e altri documenti. "
        "Ogni file sarà visibile esclusivamente al dipendente selezionato."
    )

    employees = (
        sb.table("employees")
        .select("id,name,department")
        .eq("active", True)
        .order("name")
        .execute().data or []
    )

    if not employees:
        st.warning("Non risultano dipendenti attivi.")
    else:
        employee_by_id = {int(row["id"]): row for row in employees}
        employee_id = st.selectbox(
            "Dipendente",
            list(employee_by_id),
            format_func=lambda value: employee_by_id[value]["name"],
        )

        c1, c2 = st.columns(2)
        document_type = c1.selectbox(
            "Categoria",
            [
                "Contratto",
                "CU",
                "Attestato HACCP",
                "Formazione",
                "Visita medica",
                "Certificato",
                "Comunicazione",
                "Altro",
            ],
        )
        document_date = c2.date_input("Data documento", value=date.today())

        c3, c4 = st.columns(2)
        title = c3.text_input(
            "Titolo",
            placeholder="Esempio: Contratto di assunzione",
        )
        has_expiry = c4.checkbox("Documento con scadenza")

        expiry_date = None
        if has_expiry:
            expiry_date = st.date_input(
                "Data di scadenza",
                value=date.today() + timedelta(days=365),
            )

        uploaded_document = st.file_uploader(
            "Documento",
            type=["pdf", "png", "jpg", "jpeg", "doc", "docx"],
            key="employee_document_upload",
        )

        notes = st.text_area(
            "Note interne facoltative",
            placeholder="Queste note restano nel gestionale.",
        )

        if st.button(
            "Pubblica nell'area dipendente",
            type="primary",
            disabled=not uploaded_document or not title.strip(),
        ):
            try:
                safe_name = safe_storage_filename(uploaded_document.name)
                storage_path = (
                    f"{employee_id}/{document_date.year:04d}/"
                    f"{document_date.month:02d}/"
                    f"{now_rome().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
                )

                # Il client Storage installato su Streamlit accetta i bytes
                # del file; BytesIO genera TypeError in questa versione.
                file_bytes = uploaded_document.getvalue()

                sb.storage.from_("employee-documents").upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={
                        "content-type": uploaded_document.type
                        or "application/octet-stream",
                        "upsert": "false",
                    },
                )

                sb.table("employee_documents").insert({
                    "employee_id": employee_id,
                    "title": title.strip(),
                    "document_type": document_type,
                    "document_date": document_date.isoformat(),
                    "expiry_date": (
                        expiry_date.isoformat() if expiry_date else None
                    ),
                    "storage_path": storage_path,
                    "original_file_name": uploaded_document.name,
                    "mime_type": uploaded_document.type,
                    "notes": notes.strip() or None,
                    "status": "published",
                }).execute()

                sb.table("employee_notifications").insert({
                    "employee_id": employee_id,
                    "title": "Nuovo documento disponibile",
                    "message": (
                        f"È stato pubblicato il documento: {title.strip()}."
                    ),
                    "notification_type": "document",
                    "is_read": False,
                }).execute()

                sb.table("manager_notifications").insert({
                    "employee_id": employee_id,
                    "title": "Documento pubblicato",
                    "message": (
                        f"{title.strip()} è stato pubblicato nell'area privata "
                        f"di {employee_by_id[employee_id]['name']}."
                    ),
                    "notification_type": "document_published",
                    "priority": "Bassa",
                    "alert_key": (
                        f"document-published:{employee_id}:"
                        f"{storage_path}"
                    ),
                    "is_read": False,
                }).execute()

                audit(
                    "employee_document_published",
                    "Documento pubblicato nell'area dipendente",
                    employee_id=employee_id,
                    entity_type="employee_document",
                    entity_id=storage_path,
                    details={
                        "title": title.strip(),
                        "document_type": document_type,
                        "document_date": document_date.isoformat(),
                        "expiry_date": expiry_date.isoformat() if expiry_date else None,
                        "original_file_name": uploaded_document.name,
                    },
                )
                st.success(
                    "Documento pubblicato nell'area privata del dipendente."
                )
            except Exception as exc:
                st.error(
                    f"Pubblicazione non riuscita: "
                    f"{type(exc).__name__}: {exc}"
                )

    st.divider()
    st.subheader("Archivio documenti")

    archive = (
        sb.table("employee_documents")
        .select(
            "id,title,document_type,document_date,expiry_date,status,"
            "original_file_name,storage_path,employees(name)"
        )
        .order("document_date", desc=True)
        .execute().data or []
    )

    if not archive:
        st.info("Nessun documento pubblicato.")
    else:
        archive_rows = []
        for document in archive:
            employee_data = document.get("employees") or {}
            archive_rows.append({
                "ID": int(document["id"]),
                "Dipendente": employee_data.get("name", ""),
                "Documento": document.get("title", ""),
                "Categoria": document.get("document_type", ""),
                "Data": document.get("document_date", ""),
                "Scadenza": document.get("expiry_date") or "",
                "Stato": document.get("status", ""),
                "File": document.get("original_file_name", ""),
            })

        st.dataframe(
            pd.DataFrame(archive_rows),
            use_container_width=True,
            hide_index=True,
        )

        selected_archive_id = st.selectbox(
            "Documento da gestire",
            [int(row["id"]) for row in archive],
            format_func=lambda value: next(
                (
                    f"{row.get('title')} · "
                    f"{(row.get('employees') or {}).get('name', '')}"
                    for row in archive
                    if int(row["id"]) == value
                ),
                str(value),
            ),
        )

        selected_archive = next(
            row for row in archive
            if int(row["id"]) == selected_archive_id
        )

        a1, a2 = st.columns(2)
        url = employee_document_url(
            selected_archive["storage_path"],
            sb,
        )
        if url:
            a1.link_button(
                "Apri documento",
                url,
                use_container_width=True,
            )

        if a2.button(
            "Archivia documento",
            use_container_width=True,
        ):
            sb.table("employee_documents").update({
                "status": "archived"
            }).eq("id", selected_archive_id).execute()
            audit(
                "employee_document_archived",
                "Documento dipendente archiviato",
                entity_type="employee_document",
                entity_id=selected_archive_id,
                severity="warning",
            )
            st.success("Documento archiviato.")
            st.rerun()



elif section == "Centro notifiche":
    st.title("Centro notifiche")
    st.caption(
        "Avvisi operativi, anomalie e scadenze da controllare."
    )

    if st.button("Aggiorna controlli automatici", type="primary"):
        created = ensure_automatic_manager_alerts()
        st.success(f"Controllo completato. Nuovi avvisi creati: {created}.")
        st.rerun()

    notifications = manager_notification_snapshot()

    if not notifications:
        st.success("Non ci sono notifiche.")
    else:
        unread = [row for row in notifications if not row["Letta"]]
        a, b, c = st.columns(3)
        a.metric("Totali", len(notifications))
        b.metric("Da leggere", len(unread))
        c.metric(
            "Priorità alta",
            sum(1 for row in unread if row["Priorità"] == "Alta"),
        )

        st.dataframe(
            pd.DataFrame(notifications),
            use_container_width=True,
            hide_index=True,
        )

        selected_id = st.selectbox(
            "Notifica da gestire",
            [row["ID"] for row in notifications],
            format_func=lambda value: next(
                (
                    f"{row['Priorità']} · {row['Titolo']}"
                    for row in notifications
                    if row["ID"] == value
                ),
                str(value),
            ),
        )

        n1, n2 = st.columns(2)
        if n1.button("Segna come letta", use_container_width=True):
            sb.table("manager_notifications").update({
                "is_read": True,
                "read_at": now_rome().isoformat(),
            }).eq("id", selected_id).execute()
            st.success("Notifica aggiornata.")
            st.rerun()

        if n2.button("Segna come da leggere", use_container_width=True):
            sb.table("manager_notifications").update({
                "is_read": False,
                "read_at": None,
            }).eq("id", selected_id).execute()
            st.success("Notifica aggiornata.")
            st.rerun()

    st.divider()
    st.subheader("Scadenze entro 60 giorni")
    expiry_rows = document_expiry_snapshot(60)
    if expiry_rows:
        st.dataframe(
            pd.DataFrame(expiry_rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nessun documento in scadenza nei prossimi 60 giorni.")


elif section == "Fringe benefit":
    st.title("Fringe benefit")
    employees = employees_df()
    if not employees.empty:
        with st.form("fringe"):
            name = st.selectbox("Dipendente", employees["name"].tolist())
            employee_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
            d = st.date_input("Data", value=date(year, month, 1))
            amount = st.number_input("Importo", min_value=0.0, step=10.0)
            category = st.selectbox("Categoria", ["Buoni", "Alloggio", "Auto", "Telefono", "Pasto", "Altro"])
            note = st.text_input("Nota")
            save = st.form_submit_button("Registra", type="primary")
        if save:
            sb.table("fringe_benefits").insert({
                "employee_id": employee_id, "benefit_date": d.isoformat(),
                "amount": amount, "category": category, "note": note
            }).execute()
            log_event(
                sb,
                "fringe_benefit_created",
                "Fringe benefit registrato",
                employee_id=employee_id,
                entity_type="fringe_benefit",
                details={"amount": amount, "category": category},
            )
            audit(
                "fringe_benefit_created",
                "Fringe benefit registrato",
                employee_id=employee_id,
                entity_type="fringe_benefit",
                details={"amount": amount, "category": category},
            )
            st.success("Fringe registrato.")

elif section == "Extra da regolarizzare":
    st.title("Extra da regolarizzare")
    st.warning("Registro interno. Gli importi devono essere comunicati e regolarizzati con il consulente.")
    employees = employees_df()
    if not employees.empty:
        with st.form("extra"):
            name = st.selectbox("Dipendente", employees["name"].tolist())
            employee_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
            d = st.date_input("Data", value=date(year, month, 1))
            amount = st.number_input("Importo", min_value=0.0, step=10.0)
            reason = st.text_input("Motivo")
            note = st.text_area("Nota")
            save = st.form_submit_button("Registra", type="primary")
        if save and reason:
            sb.table("extra_payments").insert({
                "employee_id": employee_id, "payment_date": d.isoformat(),
                "amount": amount, "reason": reason,
                "payment_method": "Da regolarizzare",
                "regularized": False, "note": note
            }).execute()
            log_event(
                sb,
                "extra_payment_created",
                "Extra registrato",
                employee_id=employee_id,
                entity_type="extra_payment",
                details={"amount": amount, "reason": reason},
                severity="warning",
            )
            audit(
                "extra_payment_created",
                "Extra registrato",
                employee_id=employee_id,
                entity_type="extra_payment",
                details={"amount": amount, "reason": reason},
                severity="warning",
            )
            st.success("Extra registrato.")

elif section == "Dati del mese":
    st.title("Dati del mese")
    existing = (
        sb.table("monthly_revenue").select("revenue,covers")
        .eq("year", year).eq("month", month).execute().data or []
    )
    revenue = float(existing[0]["revenue"] or 0) if existing else 0.0
    covers = int(existing[0]["covers"] or 0) if existing else 0

    with st.form("month"):
        new_revenue = st.number_input("Fatturato", min_value=0.0, value=revenue, step=1000.0)
        new_covers = st.number_input("Coperti", min_value=0, value=covers, step=10)
        save = st.form_submit_button("Salva", type="primary")
    if save:
        sb.table("monthly_revenue").upsert({
            "year": year, "month": month,
            "revenue": new_revenue, "covers": new_covers
        }, on_conflict="year,month").execute()
        log_event(
            sb,
            "monthly_data_updated",
            f"Dati mensili aggiornati: {MONTHS[month]} {year}",
            entity_type="monthly_revenue",
            entity_id=f"{year}-{month:02d}",
            details={"revenue": new_revenue, "covers": new_covers},
        )
        audit(
            "monthly_data_updated",
            f"Dati mensili aggiornati: {MONTHS[month]} {year}",
            entity_type="monthly_revenue",
            entity_id=f"{year}-{month:02d}",
            details={"revenue": new_revenue, "covers": new_covers},
        )
        st.success("Dati aggiornati.")
