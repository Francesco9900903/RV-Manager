
import re
import json
import hashlib
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
try:
    from rv_manager.employee_portal_utils import approved_hours_summary, current_period
except ModuleNotFoundError:
    from employee_portal_utils import approved_hours_summary, current_period

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


    .rv-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.85rem;
        margin: 0.8rem 0 1.2rem 0;
    }

    .rv-kpi-card {
        background: #fff;
        border: 1px solid var(--rv-border);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: var(--rv-shadow);
    }

    .rv-kpi-card.good {
        border-left: 5px solid #0f9f6e;
    }

    .rv-kpi-card.warn {
        border-left: 5px solid #d97706;
    }

    .rv-kpi-card.danger {
        border-left: 5px solid #c83b4d;
    }

    .rv-kpi-card.info {
        border-left: 5px solid #3b82f6;
    }

    .rv-kpi-label {
        color: var(--rv-muted);
        font-size: 0.78rem;
        font-weight: 700;
    }

    .rv-kpi-value {
        color: var(--rv-navy);
        font-size: 1.65rem;
        font-weight: 800;
        margin-top: 0.25rem;
    }

    .rv-kpi-note {
        color: var(--rv-muted);
        font-size: 0.74rem;
        margin-top: 0.25rem;
    }

    .rv-section-card {
        background: #fff;
        border: 1px solid var(--rv-border);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: var(--rv-shadow);
        margin-bottom: 1rem;
    }

    @media (max-width: 1000px) {
        .rv-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 600px) {
        .rv-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
        }

        .rv-kpi-card {
            padding: 0.75rem;
        }

        .rv-kpi-value {
            font-size: 1.3rem;
        }
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

    button[kind="primary"],
    .stFormSubmitButton button[kind="primary"],
    .stButton button[kind="primary"] {
        background: var(--rv-accent) !important;
        border-color: var(--rv-accent) !important;
        color: #ffffff !important;
    }

    button[kind="primary"] *,
    .stFormSubmitButton button[kind="primary"] *,
    .stButton button[kind="primary"] * {
        color: #ffffff !important;
        fill: #ffffff !important;
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


    /* Mobile employee experience */
    .rv-mobile-hero {
        background: linear-gradient(135deg, #172033 0%, #24304a 100%);
        color: white;
        border-radius: 18px;
        padding: 1rem 1rem 1.1rem 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 26px rgba(23,32,51,0.14);
    }

    .rv-mobile-hero h2 {
        color: white;
        margin: 0;
        font-size: 1.25rem;
    }

    .rv-mobile-hero p {
        color: #d7deea;
        margin: 0.35rem 0 0 0;
        font-size: 0.9rem;
    }

    .rv-quick-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.7rem;
        margin-bottom: 1rem;
    }

    .rv-quick-card {
        background: #fff;
        border: 1px solid var(--rv-border);
        border-radius: 14px;
        padding: 0.9rem;
        box-shadow: var(--rv-shadow);
    }

    .rv-quick-label {
        color: var(--rv-muted);
        font-size: 0.76rem;
        font-weight: 650;
    }

    .rv-quick-value {
        color: var(--rv-navy);
        font-size: 1.15rem;
        font-weight: 760;
        margin-top: 0.15rem;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            min-width: 230px !important;
            max-width: 230px !important;
            width: 230px !important;
        }

        section[data-testid="stSidebar"] > div {
            width: 230px !important;
        }

        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 5rem;
        }

        h1 {
            font-size: 1.8rem;
        }

        h2 {
            font-size: 1.35rem;
        }

        div[data-testid="column"] {
            min-width: 100% !important;
        }

        [data-testid="stHorizontalBlock"] {
            gap: 0.55rem;
        }

        div[data-testid="stMetric"] {
            min-height: 92px;
        }

        div[data-testid="stDataFrame"] {
            overflow-x: auto;
        }

        button[data-baseweb="tab"] {
            font-size: 0.78rem;
            padding-left: 0.55rem;
            padding-right: 0.55rem;
        }

        .stButton > button,
        .stDownloadButton > button,
        a[data-testid="stLinkButton"] {
            width: 100%;
            min-height: 54px;
            font-size: 1rem;
        }
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

ITALIAN_TRANSLATIONS = {
    # Stati
    "approved": "Approvato",
    "submitted": "Da approvare",
    "rejected": "Rifiutato",
    "published": "Pubblicato",
    "archived": "Archiviato",
    "draft": "Bozza",
    "open": "Aperto",
    "closed": "Chiuso",
    "active": "Attivo",
    "inactive": "Non attivo",
    "manager": "Responsabile",
    "employee": "Dipendente",
    "admin": "Amministratore",
    "owner": "Titolare",
    "general": "Generale",
    "payslip": "Busta paga",
    "document": "Documento",
    # Gravità
    "info": "Informazione",
    "warning": "Avviso",
    "critical": "Critico",
    "success": "Completato",
    # Tipi evento
    "monthly_data_updated": "Dati mensili aggiornati",
    "employee_created": "Dipendente creato",
    "employee_account_created": "Account dipendente creato",
    "employee_account_linked": "Account dipendente associato",
    "clock_in": "Entrata registrata",
    "clock_out": "Uscita registrata",
    "timesheet_submitted": "Ore inviate",
    "timesheet_admin_saved": "Ore inserite dal responsabile",
    "timesheet_approved": "Ore approvate",
    "timesheet_rejected": "Ore rifiutate",
    "payroll_costs_imported": "Costi paghe importati",
    "payslip_published": "Busta paga pubblicata",
    "employee_document_published": "Documento pubblicato",
    "employee_document_archived": "Documento archiviato",
    "fringe_benefit_created": "Fringe benefit registrato",
    "extra_payment_created": "Altro costo registrato",
    "backup_exported": "Backup esportato",
    "qa_completed": "Collaudo completato",
    # Entità
    "employee": "Dipendente",
    "employee_account": "Account dipendente",
    "clock_entry": "Timbratura",
    "timesheet": "Registrazione ore",
    "monthly_costs": "Costi mensili",
    "monthly_revenue": "Dati del mese",
    "payslip": "Busta paga",
    "employee_document": "Documento dipendente",
    "fringe_benefit": "Fringe benefit",
    "extra_payment": "Altro costo",
    "system_backup": "Backup del sistema",
    "quality_assurance": "Collaudo",
}

def translate_it(value):
    if value is None:
        return ""
    text = str(value)
    return ITALIAN_TRANSLATIONS.get(text, ITALIAN_TRANSLATIONS.get(text.lower(), text))

def format_date_it(value):
    """Restituisce sempre le date come giorno/mese/anno."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.astimezone(ROME_TZ).strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(ROME_TZ)
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return text

def format_datetime_it(value):
    """Data italiana e ora locale: giorno/mese/anno ore:minuti."""
    if value is None or value == "":
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC_TZ)
        return parsed.astimezone(ROME_TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return format_date_it(value)

def localize_dataframe_it(dataframe):
    if not isinstance(dataframe, pd.DataFrame):
        return dataframe

    result = dataframe.copy()
    date_words = (
        "data", "giorno", "scadenza", "creata", "creato",
        "aggiornata", "aggiornato", "timestamp"
    )
    datetime_words = ("creata", "creato", "aggiornata", "aggiornato", "ora")

    for column in result.columns:
        column_text = str(column).lower()
        if any(word in column_text for word in date_words):
            formatter = (
                format_datetime_it
                if any(word in column_text for word in datetime_words)
                else format_date_it
            )
            result[column] = result[column].map(formatter)

        if result[column].dtype == object:
            result[column] = result[column].map(translate_it)

    return result

# Tutte le tabelle dell'app ereditano automaticamente formato e termini italiani.
_original_dataframe = st.dataframe

def dataframe_italiano(data=None, *args, **kwargs):
    return _original_dataframe(localize_dataframe_it(data), *args, **kwargs)

st.dataframe = dataframe_italiano

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
    df["other_cost"] = df["employee_id"].map(x_map).fillna(0)
    # Compatibilità con analisi precedenti.
    df["extra_cash"] = df["other_cost"]
    # Gli extra del mese vengono sommati al costo importato del dipendente.
    df["management_cost"] = df["company_cost"] + df["other_cost"]

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

    tabs = st.tabs(["⌂ Home", "◷ Timbratura", "✎ Manuale", "≡ Storico", "▤ Buste paga", "□ Documenti"])

    with st.expander("Installa sul telefono"):
        st.markdown(
            """
            **iPhone/iPad:** apri il menu Condividi di Safari e scegli
            **Aggiungi alla schermata Home**.

            **Android:** apri il menu di Chrome e scegli
            **Aggiungi a schermata Home** oppure **Installa app**.

            L'app resta una web app: per timbrare e consultare documenti serve
            una connessione internet.
            """
        )


    with tabs[0]:
        st.markdown(
            f"""
            <div class="rv-mobile-hero">
                <h2>Ciao, {employee.get('name', '').title()}</h2>
                <p>{employee.get('department') or 'Area dipendente'} · {now_rome().strftime('%d/%m/%Y')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        open_shift_home = current_open_shift(employee_id, public_sb)
        month_start_home, month_end_home = month_bounds(year, month)
        home_timesheets = (
            public_sb.table("timesheets")
            .select("ordinary_hours,overtime_hours,status,work_date")
            .eq("employee_id", employee_id)
            .gte("work_date", month_start_home.isoformat())
            .lt("work_date", month_end_home.isoformat())
            .execute().data or []
        )
        approved_summary = approved_hours_summary(home_timesheets)
        home_hours = approved_summary["total"]
        home_overtime = approved_summary["overtime"]

        if open_shift_home:
            started_home = parse_db_datetime(open_shift_home.get("clock_in"))
            shift_status = (
                f"In servizio dalle {started_home.strftime('%H:%M')}"
                if started_home else "In servizio"
            )
        else:
            shift_status = "Fuori servizio"

        st.markdown(
            f"""
            <div class="rv-quick-grid">
                <div class="rv-quick-card">
                    <div class="rv-quick-label">Stato di oggi</div>
                    <div class="rv-quick-value">{shift_status}</div>
                </div>
                <div class="rv-quick-card">
                    <div class="rv-quick-label">Ore approvate mese</div>
                    <div class="rv-quick-value">{home_hours:.2f}</div>
                </div>
                <div class="rv-quick-card">
                    <div class="rv-quick-label">Straordinari mese</div>
                    <div class="rv-quick-value">{home_overtime:.2f}</div>
                </div>
                <div class="rv-quick-card">
                    <div class="rv-quick-label">Periodo</div>
                    <div class="rv-quick-value">{MONTHS[month]} {year}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
            "Priorità": (
                "🔴 Alta" if row.get("priority") == "Alta"
                else "🟠 Media" if row.get("priority") == "Media"
                else "🟢 Bassa"
            ),
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


def security_health_snapshot():
    checks = []

    # Secrets principali.
    try:
        supabase_cfg = st.secrets.get("supabase", {})
    except Exception:
        supabase_cfg = {}

    has_url = bool(supabase_cfg.get("url"))
    has_secret = bool(
        supabase_cfg.get("secret_key")
        or supabase_cfg.get("service_role_key")
    )
    has_public = bool(
        supabase_cfg.get("publishable_key")
        or supabase_cfg.get("anon_key")
    )

    checks.append({
        "Controllo": "URL Supabase configurato",
        "Esito": "OK" if has_url else "MANCANTE",
        "Priorità": "Alta",
    })
    checks.append({
        "Controllo": "Chiave server configurata nei Secrets",
        "Esito": "OK" if has_secret else "MANCANTE",
        "Priorità": "Alta",
    })
    checks.append({
        "Controllo": "Chiave pubblica configurata",
        "Esito": "OK" if has_public else "MANCANTE",
        "Priorità": "Media",
    })

    # Tabelle principali.
    table_names = [
        "employees",
        "employee_accounts",
        "timesheets",
        "clock_entries",
        "payslips",
        "employee_documents",
        "audit_events",
    ]
    for table_name in table_names:
        try:
            sb.table(table_name).select("*").limit(1).execute()
            result = "OK"
        except Exception:
            result = "ERRORE"
        checks.append({
            "Controllo": f"Tabella {table_name}",
            "Esito": result,
            "Priorità": "Alta" if table_name in {
                "employees", "employee_accounts", "employee_documents", "payslips"
            } else "Media",
        })

    # Bucket privati.
    for bucket_name in ["payslips", "employee-documents"]:
        try:
            sb.storage.from_(bucket_name).list()
            result = "OK"
        except Exception:
            result = "ERRORE"
        checks.append({
            "Controllo": f"Bucket privato {bucket_name}",
            "Esito": result,
            "Priorità": "Alta",
        })

    return checks

def export_backup_manifest():
    manifest = {
        "generated_at": now_rome().isoformat(),
        "application": "RV Manager Enterprise",
        "version": "4.4.0",
        "tables": {},
    }

    for table_name in [
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
    ]:
        try:
            rows = (
                sb.table(table_name)
                .select("*")
                .limit(10000)
                .execute().data or []
            )
            manifest["tables"][table_name] = rows
        except Exception as exc:
            manifest["tables"][table_name] = {
                "_error": f"{type(exc).__name__}: {exc}"
            }

    return manifest


BACKUP_BUCKET = "system-backups"

def backup_bytes_and_metadata(backup_type="manuale"):
    manifest = export_backup_manifest()
    manifest["backup_type"] = backup_type
    manifest["version"] = "4.1.0"

    payload = json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode("utf-8")

    checksum = hashlib.sha256(payload).hexdigest()
    generated = now_rome()
    filename = (
        f"rv_manager_{backup_type}_"
        f"{generated.strftime('%Y%m%d_%H%M%S')}.json"
    )

    return {
        "manifest": manifest,
        "bytes": payload,
        "checksum": checksum,
        "filename": filename,
        "size_bytes": len(payload),
        "generated_at": generated,
    }

def register_backup_record(metadata, status="completato", error_message=""):
    row = {
        "backup_type": metadata.get("backup_type", "manuale"),
        "file_name": metadata.get("filename", ""),
        "storage_path": metadata.get("storage_path", ""),
        "size_bytes": int(metadata.get("size_bytes") or 0),
        "checksum_sha256": metadata.get("checksum", ""),
        "status": status,
        "error_message": error_message,
        "created_at": metadata.get("created_at") or now_rome().isoformat(),
    }
    return sb.table("backup_registry").insert(row).execute()

def create_cloud_backup(backup_type="manuale"):
    package = backup_bytes_and_metadata(backup_type)
    storage_path = (
        f"{package['generated_at'].strftime('%Y/%m/%d')}/"
        f"{package['filename']}"
    )

    sb.storage.from_(BACKUP_BUCKET).upload(
        storage_path,
        package["bytes"],
        {
            "content-type": "application/json",
            "upsert": "false",
        },
    )

    metadata = {
        "backup_type": backup_type,
        "filename": package["filename"],
        "storage_path": storage_path,
        "size_bytes": package["size_bytes"],
        "checksum": package["checksum"],
        "created_at": package["generated_at"].isoformat(),
    }
    register_backup_record(metadata)

    audit(
        "backup_exported",
        f"Backup {backup_type} completato",
        entity_type="system_backup",
        details={
            "file_name": package["filename"],
            "storage_path": storage_path,
            "size_bytes": package["size_bytes"],
            "checksum_sha256": package["checksum"],
        },
    )

    package["storage_path"] = storage_path
    return package

def list_backup_records(limit=30):
    try:
        return (
            sb.table("backup_registry")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute().data or []
        )
    except Exception:
        return []

def get_backup_settings():
    defaults = {
        "enabled": False,
        "frequency": "giornaliero",
        "run_hour": 2,
        "retention_count": 30,
        "last_run_at": None,
        "next_run_at": None,
    }
    try:
        rows = (
            sb.table("backup_settings")
            .select("*")
            .eq("id", 1)
            .limit(1)
            .execute().data or []
        )
        if rows:
            defaults.update(rows[0])
    except Exception:
        pass
    return defaults

def save_backup_settings(enabled, frequency, run_hour, retention_count):
    payload = {
        "id": 1,
        "enabled": bool(enabled),
        "frequency": frequency,
        "run_hour": int(run_hour),
        "retention_count": int(retention_count),
        "updated_at": now_rome().isoformat(),
    }
    return (
        sb.table("backup_settings")
        .upsert(payload, on_conflict="id")
        .execute()
    )

def verify_backup_integrity(record):
    storage_path = record.get("storage_path")
    expected_checksum = record.get("checksum_sha256")
    if not storage_path or not expected_checksum:
        return False, "Dati di verifica incompleti."

    payload = sb.storage.from_(BACKUP_BUCKET).download(storage_path)
    actual_checksum = hashlib.sha256(payload).hexdigest()
    if actual_checksum == expected_checksum:
        return True, "Integrità verificata: il file non risulta alterato."
    return False, "La firma del file non corrisponde: backup da controllare."

def backup_size_label(size_bytes):
    size = float(size_bytes or 0)
    if size < 1024:
        return f"{int(size)} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"



# Tabelle minime in vigore da maggio 2026 per il CCNL Turismo
# Confcommercio - aziende alberghiere.
CCNL_TURISMO_2026 = {
    "Albergo": {
        "Quadro A": 2491.82, "Quadro B": 2307.53, "1": 2084.71,
        "2": 1905.40, "3": 1797.04, "4": 1695.69, "5": 1590.27,
        "6S": 1529.13, "6": 1507.45, "7": 1412.60,
    },
    "Alberghi minori": {
        "Quadro A": 2480.46, "Quadro B": 2297.20, "1": 2074.38,
        "2": 1896.62, "3": 1789.29, "4": 1688.98, "5": 1584.07,
        "6S": 1523.45, "6": 1501.77, "7": 1407.44,
    },
}

MANSIONI_TURISMO = [
    "Addetto/a ricevimento", "Cameriere/a di sala", "Barista", "Cuoco/a",
    "Aiuto cuoco/a", "Cameriere/a ai piani", "Addetto/a pulizie",
    "Manutentore/trice", "Responsabile di reparto", "Direttore/trice", "Altro",
]

def euro_it(value):
    value = float(value or 0)
    formatted = f"{value:,.2f}"
    return "€ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")

def progressive_irpef_annual(taxable):
    taxable = max(float(taxable or 0), 0.0)
    first = min(taxable, 28000.0) * 0.23
    second = min(max(taxable - 28000.0, 0.0), 22000.0) * 0.35
    third = max(taxable - 50000.0, 0.0) * 0.43
    return first + second + third

def employee_tax_credit_annual(income):
    income = max(float(income or 0), 0.0)
    if income <= 15000:
        return max(1955.0, 1910.0 + 1190.0 * (15000.0 - income) / 15000.0)
    if income <= 50000:
        return 1910.0 * (50000.0 - income) / 35000.0
    return 0.0

def simulate_payroll(inputs):
    monthly_divisor = float(inputs.get("monthly_divisor") or 172.0)
    contractual_monthly = float(inputs.get("contractual_monthly") or 0.0)
    ordinary_hours = float(inputs.get("ordinary_hours") or 0.0)
    hourly_rate = contractual_monthly / monthly_divisor

    ordinary_pay = hourly_rate * ordinary_hours
    overtime_pay = hourly_rate * float(inputs.get("overtime_hours") or 0.0) * (
        1 + float(inputs.get("overtime_markup") or 0.0) / 100
    )
    night_pay = hourly_rate * float(inputs.get("night_hours") or 0.0) * (
        float(inputs.get("night_markup") or 0.0) / 100
    )
    holiday_pay = hourly_rate * float(inputs.get("holiday_hours") or 0.0) * (
        float(inputs.get("holiday_markup") or 0.0) / 100
    )
    sunday_pay = hourly_rate * float(inputs.get("sunday_hours") or 0.0) * (
        float(inputs.get("sunday_markup") or 0.0) / 100
    )

    gross_month = (
        ordinary_pay + overtime_pay + night_pay + holiday_pay + sunday_pay
        + float(inputs.get("superminimo") or 0.0)
        + float(inputs.get("bonuses") or 0.0)
        + float(inputs.get("allowances") or 0.0)
    )

    employee_rate = float(inputs.get("employee_contribution_rate") or 0.0) / 100
    employee_contributions = gross_month * employee_rate
    annual_taxable = max(gross_month - employee_contributions, 0.0) * 14
    gross_irpef_annual = progressive_irpef_annual(annual_taxable)
    tax_credit_annual = employee_tax_credit_annual(annual_taxable)
    irpef_month = max(gross_irpef_annual - tax_credit_annual, 0.0) / 14
    additions_month = annual_taxable * (
        float(inputs.get("additional_tax_rate") or 0.0) / 100
    ) / 14
    net_month = gross_month - employee_contributions - irpef_month - additions_month

    employer_contributions = gross_month * (
        float(inputs.get("employer_contribution_rate") or 0.0) / 100
    )
    inail = gross_month * (float(inputs.get("inail_rate") or 0.0) / 100)
    thirteenth = gross_month / 12
    fourteenth = gross_month / 12
    tfr = gross_month / 13.5
    leave_accrual = gross_month * (
        float(inputs.get("leave_accrual_rate") or 0.0) / 100
    )
    company_cost = (
        gross_month + employer_contributions + inail + thirteenth
        + fourteenth + tfr + leave_accrual
    )

    return {
        "hourly_rate": hourly_rate,
        "ordinary_pay": ordinary_pay,
        "overtime_pay": overtime_pay,
        "night_pay": night_pay,
        "holiday_pay": holiday_pay,
        "sunday_pay": sunday_pay,
        "gross_month": gross_month,
        "employee_contributions": employee_contributions,
        "annual_taxable": annual_taxable,
        "gross_irpef_annual": gross_irpef_annual,
        "tax_credit_annual": tax_credit_annual,
        "irpef_month": irpef_month,
        "additions_month": additions_month,
        "net_month": max(net_month, 0.0),
        "employer_contributions": employer_contributions,
        "inail": inail,
        "thirteenth": thirteenth,
        "fourteenth": fourteenth,
        "tfr": tfr,
        "leave_accrual": leave_accrual,
        "company_cost": company_cost,
        "annual_company_cost": company_cost * 12,
    }

def payroll_report_html(inputs, result):
    rows = [
        ("Mansione", inputs.get("job_title", "")),
        ("Livello", inputs.get("level", "")),
        ("CCNL", inputs.get("ccnl_name", "Turismo Confcommercio")),
        ("Settore", inputs.get("sector", "")),
        ("Ore ordinarie", f"{inputs.get('ordinary_hours', 0):.2f}"),
        ("Minimo mensile utilizzato", euro_it(inputs.get("contractual_monthly", 0))),
        ("Lordo mensile stimato", euro_it(result["gross_month"])),
        ("Netto mensile stimato", euro_it(result["net_month"])),
        ("Costo mensile azienda", euro_it(result["company_cost"])),
        ("Costo annuo azienda", euro_it(result["annual_company_cost"])),
    ]
    body = "".join(
        f"<tr><th>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Simulazione busta paga</title>
<style>
body{{font-family:Arial,sans-serif;margin:40px;color:#172033}}
h1{{margin-bottom:4px}} small{{color:#667085}}
table{{border-collapse:collapse;width:100%;margin-top:24px}}
th,td{{border:1px solid #dfe5ed;padding:12px;text-align:left}}
th{{width:45%;background:#f4f6f9}}
.notice{{margin-top:24px;padding:14px;background:#fff7e6;border:1px solid #f0d49a}}
</style></head><body><h1>RV Manager Enterprise</h1>
<small>Simulazione economica CCNL Turismo Confcommercio</small>
<table>{body}</table>
<div class="notice"><strong>Avvertenza:</strong> elaborazione indicativa.
Non sostituisce il cedolino o il conteggio del consulente del lavoro.</div>
</body></html>"""

def save_payroll_simulation(inputs, result):
    payload = {
        "job_title": inputs.get("job_title"),
        "ccnl": inputs.get("ccnl_name", "Turismo Confcommercio"),
        "sector": inputs.get("sector"),
        "level": inputs.get("level"),
        "monthly_hours": float(inputs.get("ordinary_hours") or 0),
        "gross_monthly": round(result.get("gross_month", 0), 2),
        "net_monthly": round(result.get("net_month", 0), 2),
        "company_cost_monthly": round(result.get("company_cost", 0), 2),
        "parameters": inputs,
        "result": result,
        "created_at": now_rome().isoformat(),
    }
    return sb.table("payroll_simulations").insert(payload).execute()

def runtime_environment_snapshot():
    try:
        cfg = st.secrets.get("app", {})
    except Exception:
        cfg = {}

    environment = str(cfg.get("environment", "production")).strip().lower()
    project_label = str(cfg.get("project_label", "RV Manager")).strip()
    allow_real_data = bool(cfg.get("allow_real_data", environment == "production"))

    return {
        "environment": environment,
        "project_label": project_label,
        "allow_real_data": allow_real_data,
        "is_production": environment == "production",
        "is_staging": environment == "staging",
    }

def rls_diagnostic_snapshot():
    results = []

    table_names = [
        "employee_accounts",
        "timesheets",
        "clock_entries",
        "payslips",
        "employee_documents",
        "employee_notifications",
    ]

    for table_name in table_names:
        try:
            response = (
                sb.table("rls_diagnostic")
                .select("table_name,rls_enabled,policy_count")
                .eq("table_name", table_name)
                .limit(1)
                .execute()
            )
            row = (response.data or [{}])[0]
            results.append({
                "Tabella": table_name,
                "RLS": "ATTIVA" if row.get("rls_enabled") else "NON VERIFICATA",
                "Policy": int(row.get("policy_count") or 0),
            })
        except Exception:
            results.append({
                "Tabella": table_name,
                "RLS": "DIAGNOSTICA NON INSTALLATA",
                "Policy": 0,
            })

    return results



def safe_system_message(error):
    text = str(error or "").strip()
    if not text:
        return "Dettaglio tecnico non disponibile."
    lowered = text.lower()

    if "does not exist" in lowered or "42703" in lowered:
        return "Il controllo usa una struttura dati non compatibile con questa installazione."
    if "permission" in lowered or "unauthorized" in lowered or "401" in lowered:
        return "Permessi insufficienti per completare il controllo."
    if "timeout" in lowered:
        return "Il servizio ha impiegato troppo tempo a rispondere."
    if "connection" in lowered or "network" in lowered:
        return "Connessione temporaneamente non disponibile."
    return "Il controllo non è stato completato. Apri i dettagli tecnici per maggiori informazioni."

def technical_error_text(error):
    text = str(error or "").strip()
    return text[:500] if text else "Nessun dettaglio disponibile."

def system_health_snapshot():
    checks = []

    def add_check(name, ok, detail, category, technical_detail=""):
        checks.append({
            "Controllo": name,
            "Stato": "OPERATIVO" if ok else "DA VERIFICARE",
            "Dettaglio": detail,
            "Categoria": category,
            "Dettaglio tecnico": technical_detail,
        })

    # 1. Connessione database.
    try:
        import time
        started_at = time.perf_counter()
        sb.table("employee_accounts").select("*", count="exact").limit(1).execute()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        performance_ok = elapsed_ms < 3000

        add_check(
            "Connessione al database",
            True,
            "Supabase risponde correttamente.",
            "Database",
            f"Tempo di risposta: {elapsed_ms} ms.",
        )
        add_check(
            "Prestazioni database",
            performance_ok,
            (
                "Tempo di risposta regolare."
                if performance_ok
                else "Il database risponde, ma con tempi superiori alla soglia consigliata."
            ),
            "Prestazioni",
            f"Tempo di risposta misurato: {elapsed_ms} ms. Soglia: 3000 ms.",
        )
    except Exception as exc:
        add_check(
            "Connessione al database",
            False,
            safe_system_message(exc),
            "Database",
            technical_error_text(exc),
        )
        add_check(
            "Prestazioni database",
            False,
            "Prestazioni non misurabili perché la connessione non è stata completata.",
            "Prestazioni",
            technical_error_text(exc),
        )

    # 2. Tabelle fondamentali.
    required_tables = [
        "employee_accounts",
        "timesheets",
        "clock_entries",
        "payslips",
        "employee_documents",
        "employee_notifications",
    ]
    missing_tables = []
    for table_name in required_tables:
        try:
            sb.table(table_name).select("*").limit(1).execute()
        except Exception:
            missing_tables.append(table_name)

    add_check(
        "Struttura dati principale",
        len(missing_tables) == 0,
        (
            "Tutte le tabelle fondamentali sono raggiungibili."
            if not missing_tables
            else "Non raggiungibili: " + ", ".join(missing_tables)
        ),
        "Database",
    )

    # 3. RLS e policy.
    rls_rows = rls_diagnostic_snapshot()
    rls_ok = bool(rls_rows) and all(
        row.get("RLS") == "ATTIVA" and int(row.get("Policy") or 0) > 0
        for row in rls_rows
    )
    add_check(
        "Protezione dei dati utenti",
        rls_ok,
        (
            "RLS attiva e almeno una policy presente su tutte le tabelle controllate."
            if rls_ok
            else "Una o più tabelle non risultano completamente protette."
        ),
        "Sicurezza",
    )

    # 4. Storage.
    try:
        bucket_response = sb.storage.list_buckets()
        bucket_names = {
            getattr(bucket, "name", None)
            if not isinstance(bucket, dict)
            else bucket.get("name")
            for bucket in (bucket_response or [])
        }
        bucket_names.discard(None)
        expected = {"payslips", "employee-documents"}
        missing_buckets = sorted(expected - bucket_names)
        add_check(
            "Archivio documenti",
            not missing_buckets,
            (
                "Bucket documenti e buste paga disponibili."
                if not missing_buckets
                else "Bucket mancanti: " + ", ".join(missing_buckets)
            ),
            "Archiviazione",
        )
    except Exception as exc:
        add_check(
            "Archivio documenti",
            False,
            safe_system_message(exc),
            "Archiviazione",
            technical_error_text(exc),
        )

    # 5. Ambiente.
    env_info = runtime_environment_snapshot()
    env_ok = env_info["environment"] in {"production", "staging"}
    add_check(
        "Configurazione ambiente",
        env_ok,
        (
            f"Ambiente configurato come {env_info['environment'].upper()}."
            if env_ok
            else "Valore ambiente non riconosciuto."
        ),
        "Configurazione",
    )

    # 6. Ultimo backup registrato.
    try:
        backup_rows = list_backup_records(limit=1)
        if backup_rows:
            latest = backup_rows[0]
            backup_date = format_datetime_it(latest.get("created_at"))
            backup_ok = latest.get("status") == "completato"
            add_check(
                "Backup applicativo",
                backup_ok,
                (
                    f"Ultimo backup completato: {backup_date}."
                    if backup_ok
                    else "L'ultimo backup richiede verifica."
                ),
                "Continuità operativa",
                latest.get("error_message", ""),
            )
        else:
            add_check(
                "Backup applicativo",
                False,
                "Nessun backup ancora presente. Esegui il primo backup manuale.",
                "Continuità operativa",
            )
    except Exception as exc:
        add_check(
            "Backup applicativo",
            False,
            "Il centro backup richiede la migrazione Enterprise 4.1.",
            "Continuità operativa",
            technical_error_text(exc),
        )

    # 7. Versione.
    try:
        from rv_manager import __version__
        version_text = __version__
    except Exception:
        version_text = "4.4.0"

    add_check(
        "Versione software",
        True,
        f"RV Manager Enterprise {version_text}.",
        "Applicazione",
    )

    return checks


def enterprise_audit_snapshot():
    checks = []

    def add(area, name, ok, detail, weight=1):
        checks.append({
            "Area": area,
            "Controllo": name,
            "Stato": "SUPERATO" if ok else "DA RISOLVERE",
            "Dettaglio": detail,
            "Peso": int(weight),
        })

    # Applicazione e configurazione
    env = runtime_environment_snapshot()
    add(
        "Configurazione",
        "Ambiente dichiarato",
        env["environment"] in {"production", "staging"},
        f"Ambiente: {env['environment'].upper()}",
        2,
    )

    try:
        from rv_manager import __version__
        app_version = __version__
    except Exception:
        app_version = "4.4.0"

    add(
        "Applicazione",
        "Versione identificabile",
        bool(app_version),
        f"Versione installata: {app_version}",
        1,
    )

    # Database e sicurezza
    health = system_health_snapshot()
    for row in health:
        area_map = {
            "Database": "Database",
            "Sicurezza": "Sicurezza",
            "Archiviazione": "Storage",
            "Configurazione": "Configurazione",
            "Continuità operativa": "Backup",
            "Prestazioni": "Prestazioni",
            "Applicazione": "Applicazione",
        }
        area = area_map.get(row.get("Categoria"), row.get("Categoria", "Sistema"))
        add(
            area,
            row.get("Controllo", "Controllo sistema"),
            row.get("Stato") == "OPERATIVO",
            row.get("Dettaglio", ""),
            3 if area in {"Sicurezza", "Database", "Backup"} else 2,
        )

    # Qualità dei dati
    try:
        employees = (
            sb.table("employees")
            .select("id,name,department,active")
            .limit(10000)
            .execute().data or []
        )
        active = [row for row in employees if row.get("active")]
        incomplete = [
            row for row in active
            if not str(row.get("name") or "").strip()
            or not str(row.get("department") or "").strip()
        ]
        add(
            "Qualità dati",
            "Anagrafiche dipendenti",
            len(incomplete) == 0,
            (
                f"{len(active)} dipendenti attivi, nessuna anagrafica incompleta."
                if not incomplete
                else f"{len(incomplete)} anagrafiche attive richiedono completamento."
            ),
            2,
        )
    except Exception as exc:
        add(
            "Qualità dati",
            "Anagrafiche dipendenti",
            False,
            safe_system_message(exc),
            2,
        )

    try:
        orphan_documents = (
            sb.table("employee_documents")
            .select("id,employee_id,title")
            .is_("employee_id", "null")
            .limit(100)
            .execute().data or []
        )
        add(
            "Qualità dati",
            "Documenti associati",
            len(orphan_documents) == 0,
            (
                "Tutti i documenti controllati risultano associati."
                if not orphan_documents
                else f"{len(orphan_documents)} documenti senza dipendente."
            ),
            3,
        )
    except Exception:
        add(
            "Qualità dati",
            "Documenti associati",
            False,
            "Controllo non completato.",
            2,
        )

    try:
        orphan_payslips = (
            sb.table("payslips")
            .select("id,employee_id")
            .is_("employee_id", "null")
            .limit(100)
            .execute().data or []
        )
        add(
            "Qualità dati",
            "Buste paga associate",
            len(orphan_payslips) == 0,
            (
                "Tutte le buste paga controllate risultano associate."
                if not orphan_payslips
                else f"{len(orphan_payslips)} buste paga senza dipendente."
            ),
            3,
        )
    except Exception:
        add(
            "Qualità dati",
            "Buste paga associate",
            False,
            "Controllo non completato.",
            2,
        )

    # Funzioni fondamentali
    required_features = [
        ("Dipendenti", "Gestione dipendenti"),
        ("Ore e approvazioni", "Gestione ore"),
        ("Buste paga", "Buste paga"),
        ("Centro documenti", "Documenti"),
        ("Registro eventi", "Audit"),
        ("Simulazione busta paga", "Simulazioni"),
        ("Stato del sistema", "Diagnostica"),
    ]
    for menu_name, label in required_features:
        add(
            "Funzionalità",
            label,
            menu_name in MENU_ITEMS,
            "Voce disponibile nel menu." if menu_name in MENU_ITEMS else "Voce non disponibile.",
            1,
        )

    return checks


def enterprise_scores(checks):
    areas = {}
    for row in checks:
        area = row["Area"]
        areas.setdefault(area, {"earned": 0, "possible": 0})
        weight = int(row.get("Peso") or 1)
        areas[area]["possible"] += weight
        if row["Stato"] == "SUPERATO":
            areas[area]["earned"] += weight

    scores = {
        area: round(values["earned"] / values["possible"] * 100)
        if values["possible"] else 0
        for area, values in areas.items()
    }

    earned = sum(values["earned"] for values in areas.values())
    possible = sum(values["possible"] for values in areas.values())
    overall = round(earned / possible * 100) if possible else 0
    return scores, overall


def readiness_label(score):
    if score >= 95:
        return "Pronto per il collaudo commerciale"
    if score >= 85:
        return "Quasi pronto"
    if score >= 70:
        return "In consolidamento"
    return "Non pronto per la distribuzione"

def health_status_icon(status):
    return "🟢" if status == "OPERATIVO" else "🟡"

st.sidebar.markdown(
    """
    <div class="rv-brand">
        <div class="rv-brand-mark">RV</div>
        <div>
            <div class="rv-brand-title">RV Manager</div>
            <div class="rv-brand-subtitle">Enterprise 4.4 · Centro Controllo</div>
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
    "Simulazione busta paga": "€",
    "Centro documenti": "□",
    "Centro notifiche": "●",
    "Sicurezza e collaudo": "⚿",
    "Stato del sistema": "◈",
    "Centro Controllo Enterprise": "▦",
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
    "Simulazione busta paga",
    "Centro documenti",
    "Centro notifiche",
    "Sicurezza e collaudo",
    "Stato del sistema",
    "Centro Controllo Enterprise",
    "Fringe benefit",
    "Extra da regolarizzare",
    "Dati del mese",
]

def vai_a_sezione(nome_sezione):
    st.session_state["navigazione_principale"] = nome_sezione

section = st.sidebar.radio(
    "Navigazione",
    MENU_ITEMS,
    format_func=lambda item: f"{MENU_ICONS[item]}  {item}",
    label_visibility="collapsed",
    key="navigazione_principale",
)

env_info = runtime_environment_snapshot()
if env_info["is_staging"]:
    st.sidebar.warning("AMBIENTE STAGING · usare solo dati fittizi")
elif env_info["is_production"]:
    st.sidebar.success("AMBIENTE PRODUZIONE")
else:
    st.sidebar.info(f"AMBIENTE: {env_info['environment'].upper()}")

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

    present_class = "good" if snapshot["present_now"] > 0 else "warn"
    pending_class = "warn" if snapshot["pending_count"] > 0 else "good"
    expiry_class = "danger" if len(document_expiry_snapshot(30)) > 0 else "good"
    incidence_class = (
        "danger" if snapshot["incidence"] >= 35
        else "warn" if snapshot["incidence"] >= 32
        else "good"
    )

    st.markdown(
        f"""
        <div class="rv-kpi-grid">
            <div class="rv-kpi-card {present_class}">
                <div class="rv-kpi-label">Presenti adesso</div>
                <div class="rv-kpi-value">{snapshot['present_now']} / {snapshot['active_employees']}</div>
                <div class="rv-kpi-note">Personale attualmente in servizio</div>
            </div>
            <div class="rv-kpi-card info">
                <div class="rv-kpi-label">Ore lavorate oggi</div>
                <div class="rv-kpi-value">{snapshot['today_hours']:.2f}</div>
                <div class="rv-kpi-note">Incluse le timbrature aperte</div>
            </div>
            <div class="rv-kpi-card {pending_class}">
                <div class="rv-kpi-label">Ore da approvare</div>
                <div class="rv-kpi-value">{snapshot['pending_count']}</div>
                <div class="rv-kpi-note">Registrazioni in attesa</div>
            </div>
            <div class="rv-kpi-card {expiry_class}">
                <div class="rv-kpi-label">Documenti in scadenza</div>
                <div class="rv-kpi-value">{len(document_expiry_snapshot(30))}</div>
                <div class="rv-kpi-note">Entro i prossimi 30 giorni</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.markdown(
        """
        <div class="rv-section-card">
            <h3 style="margin-top:0">Centro operativo</h3>
            <p style="margin-bottom:0">Priorità, controlli e attività del periodo selezionato.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
            s2.metric("Altro costo", euro(extra))
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
                "company_cost", "fringe", "other_cost", "management_cost"
            ]].copy()
            view.columns = [
                "Dipendente", "Reparto", "Ore", "Netto", "Lordo",
                "Costo azienda", "Fringe", "Altro costo", "Costo gestionale"
            ]
            for column in [
                "Netto", "Lordo", "Costo azienda",
                "Fringe", "Altro costo", "Costo gestionale"
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
    q1.button(
        "👥 Dipendenti",
        use_container_width=True,
        on_click=vai_a_sezione,
        args=("Dipendenti",),
    )
    q2.button(
        "⏰ Ore e approvazioni",
        use_container_width=True,
        on_click=vai_a_sezione,
        args=("Ore e approvazioni",),
    )
    q3.button(
        "📄 Centro documenti",
        use_container_width=True,
        on_click=vai_a_sezione,
        args=("Centro documenti",),
    )
    q4.button(
        "🔔 Notifiche e scadenze",
        use_container_width=True,
        on_click=vai_a_sezione,
        args=("Centro notifiche",),
    )

    q5, q6 = st.columns(2)
    q5.button(
        "▤ Buste paga",
        use_container_width=True,
        on_click=vai_a_sezione,
        args=("Buste paga",),
    )
    q6.button(
        "✦ AI Manager",
        use_container_width=True,
        on_click=vai_a_sezione,
        args=("AI Manager",),
    )


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
                "other_cost",
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
                "Altro costo",
                "Costo gestionale",
                "Costo/ora",
                "Peso sul totale %",
            ]

            for column in [
                "Lordo",
                "Costo azienda",
                "Altro costo",
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
    st.title("AI Manager Pro")
    st.caption(
        "Analisi automatica del personale, priorità operative e suggerimenti "
        "basati sui dati reali del gestionale."
    )

    current = personnel_bi_period(year, month)
    previous_year, previous_month = previous_period(year, month)
    previous = personnel_bi_period(previous_year, previous_month)
    snapshot = manager_daily_snapshot(year, month)
    expiry_items = document_expiry_snapshot(30)
    unread_alerts = [
        row for row in manager_notification_snapshot(50)
        if not row["Letta"]
    ]

    if current["df"].empty:
        st.info(
            "Non ci sono ancora dati economici sufficienti per il periodo "
            "selezionato. Le analisi operative restano comunque disponibili."
        )

    # Executive risk score.
    risk_score = 0
    risk_reasons = []

    if current["incidence"] >= 35:
        risk_score += 30
        risk_reasons.append("Incidenza del personale elevata")
    elif current["incidence"] >= 32:
        risk_score += 18
        risk_reasons.append("Incidenza del personale da monitorare")

    if current["overtime"] >= 30:
        risk_score += 22
        risk_reasons.append("Straordinari molto elevati")
    elif current["overtime"] >= 15:
        risk_score += 12
        risk_reasons.append("Straordinari in crescita")

    if snapshot["pending_count"] >= 10:
        risk_score += 15
        risk_reasons.append("Molte registrazioni da approvare")
    elif snapshot["pending_count"] > 0:
        risk_score += 7
        risk_reasons.append("Registrazioni in attesa")

    if expiry_items:
        high_expiry = sum(
            1 for row in expiry_items
            if row.get("Priorità") == "Alta"
        )
        risk_score += min(20, high_expiry * 5)
        if high_expiry:
            risk_reasons.append(
                f"{high_expiry} documenti scaduti o in scadenza ravvicinata"
            )

    if snapshot["anomalies"]:
        risk_score += min(20, len(snapshot["anomalies"]) * 4)
        risk_reasons.append(
            f"{len(snapshot['anomalies'])} anomalie operative"
        )

    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        risk_label = "Critico"
        risk_message = "Intervento consigliato oggi"
    elif risk_score >= 40:
        risk_label = "Attenzione"
        risk_message = "Situazione da monitorare"
    else:
        risk_label = "Regolare"
        risk_message = "Nessuna criticità rilevante"

    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Indice di attenzione", f"{risk_score}/100")
    h2.metric("Stato", risk_label)
    h3.metric("Presenti ora", snapshot["present_now"])
    h4.metric("Azioni aperte", len(unread_alerts) + snapshot["pending_count"])

    if risk_score >= 70:
        st.error(f"**{risk_message}**")
    elif risk_score >= 40:
        st.warning(f"**{risk_message}**")
    else:
        st.success(f"**{risk_message}**")

    tab_briefing, tab_actions, tab_analysis, tab_questions = st.tabs(
        [
            "Briefing del giorno",
            "Azioni consigliate",
            "Analisi del mese",
            "Domande guidate",
        ]
    )

    with tab_briefing:
        st.subheader("Riepilogo operativo")

        briefing_rows = [
            {
                "Indicatore": "Dipendenti presenti",
                "Valore": (
                    f"{snapshot['present_now']} su "
                    f"{snapshot['active_employees']}"
                ),
                "Valutazione": (
                    "Regolare" if snapshot["present_now"] > 0
                    else "Nessun presente"
                ),
            },
            {
                "Indicatore": "Ore da approvare",
                "Valore": snapshot["pending_count"],
                "Valutazione": (
                    "Da gestire" if snapshot["pending_count"] > 0
                    else "Aggiornato"
                ),
            },
            {
                "Indicatore": "Anomalie operative",
                "Valore": len(snapshot["anomalies"]),
                "Valutazione": (
                    "Da verificare" if snapshot["anomalies"]
                    else "Nessuna"
                ),
            },
            {
                "Indicatore": "Documenti in scadenza",
                "Valore": len(expiry_items),
                "Valutazione": (
                    "Da verificare" if expiry_items else "Nessuno"
                ),
            },
            {
                "Indicatore": "Straordinari del mese",
                "Valore": f"{current['overtime']:.2f} ore",
                "Valutazione": (
                    "Elevati" if current["overtime"] >= 20
                    else "Sotto controllo"
                ),
            },
            {
                "Indicatore": "Incidenza del personale",
                "Valore": f"{current['incidence']:.1f}%",
                "Valutazione": (
                    "Elevata" if current["incidence"] >= 35
                    else "Regolare"
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(briefing_rows),
            use_container_width=True,
            hide_index=True,
        )

        if risk_reasons:
            st.subheader("Motivi dell'indice di attenzione")
            for reason in risk_reasons:
                st.write(f"• {reason}")

    with tab_actions:
        st.subheader("Priorità operative")

        actions = []

        if snapshot["pending_count"] > 0:
            actions.append({
                "Priorità": "Alta",
                "Azione": (
                    f"Approva {snapshot['pending_count']} registrazioni ore."
                ),
                "Area": "Ore",
            })

        for anomaly in snapshot["anomalies"][:10]:
            actions.append({
                "Priorità": anomaly.get("Priorità", "Media"),
                "Azione": (
                    f"Controlla {anomaly.get('Dipendente', '')}: "
                    f"{anomaly.get('Anomalia', '')}."
                ),
                "Area": "Presenze",
            })

        for item in expiry_items[:10]:
            actions.append({
                "Priorità": item.get("Priorità", "Media"),
                "Azione": (
                    f"Gestisci {item.get('Documento', '')} di "
                    f"{item.get('Dipendente', '')}, scadenza "
                    f"{item.get('Scadenza', '')}."
                ),
                "Area": "Documenti",
            })

        if current["overtime"] >= 20:
            actions.append({
                "Priorità": "Media",
                "Azione": (
                    f"Analizza le {current['overtime']:.2f} ore di "
                    "straordinario del mese."
                ),
                "Area": "Costi",
            })

        if current["incidence"] >= 35:
            actions.append({
                "Priorità": "Alta",
                "Azione": (
                    f"Verifica l'incidenza del personale, attualmente "
                    f"pari al {current['incidence']:.1f}%."
                ),
                "Area": "Business Intelligence",
            })

        if not actions:
            actions.append({
                "Priorità": "Bassa",
                "Azione": "Nessuna azione urgente.",
                "Area": "Generale",
            })

        st.dataframe(
            pd.DataFrame(actions),
            use_container_width=True,
            hide_index=True,
        )

    with tab_analysis:
        if current["df"].empty:
            st.info("Dati economici del mese non ancora disponibili.")
        else:
            insights = build_personnel_insights(current, previous)

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Costo gestionale", euro(current["management_cost"]))
            a2.metric("Incidenza", f"{current['incidence']:.1f}%")
            a3.metric("Straordinari", f"{current['overtime']:.2f}")
            a4.metric("Costo/coperto", euro(current["cost_per_cover"]))

            st.subheader("Interpretazione automatica")
            for insight in insights:
                render_insight(insight)

            if current["department_costs"]:
                st.subheader("Peso dei reparti")
                department_series = pd.Series(
                    current["department_costs"],
                    name="Costo gestionale",
                ).sort_values(ascending=False)
                st.bar_chart(department_series)

    with tab_questions:
        st.subheader("Assistente guidato")

        question = st.selectbox(
            "Scegli una domanda",
            [
                "Quali sono le priorità di oggi?",
                "Perché è cambiato il costo del personale?",
                "Quale reparto pesa di più?",
                "Gli straordinari sono sotto controllo?",
                "L'incidenza del personale è sostenibile?",
                "Quali documenti richiedono attenzione?",
            ],
        )

        if question == "Quali sono le priorità di oggi?":
            if actions:
                for item in actions[:6]:
                    st.write(
                        f"• **{item['Priorità']}** · {item['Azione']}"
                    )
            else:
                st.success("Non risultano attività urgenti.")

        elif question == "Perché è cambiato il costo del personale?":
            current_cost = current["management_cost"]
            previous_cost = previous["management_cost"]
            difference = current_cost - previous_cost

            if previous_cost:
                delta = difference / previous_cost * 100
                st.write(
                    f"Il costo è variato di **{euro(difference)}**, "
                    f"pari al **{delta:+.1f}%** rispetto al mese precedente."
                )
            else:
                st.write(
                    f"Il costo del mese è **{euro(current_cost)}**. "
                    "Manca un periodo precedente confrontabile."
                )

            st.info(
                "Controlla in Business Intelligence ore, extra, fringe, "
                "straordinari e costo per reparto."
            )

        elif question == "Quale reparto pesa di più?":
            if current["department_costs"]:
                department = max(
                    current["department_costs"],
                    key=current["department_costs"].get,
                )
                value = current["department_costs"][department]
                share = (
                    value / current["management_cost"] * 100
                    if current["management_cost"] else 0
                )
                st.write(
                    f"Il reparto con il costo maggiore è **{department}**, "
                    f"con **{euro(value)}**, pari al **{share:.1f}%** "
                    "del totale."
                )
            else:
                st.info("Non sono disponibili costi per reparto.")

        elif question == "Gli straordinari sono sotto controllo?":
            if current["overtime"] >= 30:
                st.error(
                    f"Risultano **{current['overtime']:.2f} ore** di "
                    "straordinario: livello elevato."
                )
            elif current["overtime"] >= 15:
                st.warning(
                    f"Risultano **{current['overtime']:.2f} ore** di "
                    "straordinario: situazione da monitorare."
                )
            else:
                st.success(
                    f"Gli straordinari risultano pari a "
                    f"**{current['overtime']:.2f} ore**."
                )

        elif question == "L'incidenza del personale è sostenibile?":
            incidence = current["incidence"]
            if incidence >= 35:
                st.error(
                    f"L'incidenza è **{incidence:.1f}%**: livello elevato."
                )
            elif incidence >= 32:
                st.warning(
                    f"L'incidenza è **{incidence:.1f}%**: richiede attenzione."
                )
            elif incidence > 0:
                st.success(
                    f"L'incidenza è **{incidence:.1f}%**."
                )
            else:
                st.info("Manca il fatturato del mese.")

        else:
            if not expiry_items:
                st.success(
                    "Non risultano documenti in scadenza nei prossimi 30 giorni."
                )
            else:
                st.dataframe(
                    pd.DataFrame(expiry_items),
                    use_container_width=True,
                    hide_index=True,
                )

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
                "Data": format_datetime_it(event.get("created_at")),
                "Operazione": translate_it(event.get("event_type")),
                "Descrizione": translate_it(event.get("title")),
                "Livello": translate_it(event.get("severity")),
                "Dipendente": employee.get("name", ""),
                "Elemento": translate_it(event.get("entity_type")),
                "Identificativo": event.get("entity_id", ""),
            })

        event_df = pd.DataFrame(rows)
        filter_type = st.selectbox(
            "Filtra per tipo",
            ["Tutte"] + sorted(event_df["Operazione"].dropna().unique().tolist()),
        )
        if filter_type != "Tutte":
            event_df = event_df[event_df["Operazione"] == filter_type]

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
        if st.button("Salva ore e netto", type="primary"):
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
        if st.button("Salva modifiche", type="primary"):
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
                format="DD/MM/YYYY",
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



elif section == "Sicurezza e collaudo":
    st.title("Sicurezza, backup e collaudo")
    st.caption(
        "Controlli tecnici prima dell'utilizzo con dati reali e sensibili."
    )

    tab_health, tab_backup, tab_tests, tab_access = st.tabs(
        [
            "Stato sicurezza",
            "Backup dati",
            "Checklist collaudo",
            "Verifica accessi",
        ]
    )

    with tab_health:
        checks = security_health_snapshot()
        check_df = pd.DataFrame(checks)

        ok_count = int((check_df["Esito"] == "OK").sum())
        total_count = len(check_df)
        critical_errors = int(
            (
                (check_df["Esito"] != "OK")
                & (check_df["Priorità"] == "Alta")
            ).sum()
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Controlli superati", f"{ok_count}/{total_count}")
        c2.metric("Errori prioritari", critical_errors)
        c3.metric(
            "Stato generale",
            "Pronto" if critical_errors == 0 else "Da correggere",
        )

        st.dataframe(
            check_df,
            use_container_width=True,
            hide_index=True,
        )

        if critical_errors:
            st.error(
                "Sono presenti controlli prioritari non superati. "
                "Non caricare nuovi dati sensibili prima della correzione."
            )
        else:
            st.success(
                "I controlli tecnici principali risultano superati."
            )

        st.warning(
            "Le chiavi Supabase apparse in screenshot o conversazioni devono "
            "essere rigenerate prima dell'utilizzo definitivo."
        )

    with tab_backup:
        st.subheader("Esportazione tecnica dei dati")
        st.caption(
            "Il file JSON contiene le righe delle principali tabelle. "
            "I file PDF presenti nello Storage non sono inclusi."
        )

        if st.button("Prepara backup JSON", type="primary"):
            with st.spinner("Preparazione backup..."):
                manifest = export_backup_manifest()
                backup_bytes = json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ).encode("utf-8")

            st.download_button(
                "Scarica backup JSON",
                data=backup_bytes,
                file_name=(
                    f"rv_manager_backup_"
                    f"{now_rome().strftime('%Y%m%d_%H%M%S')}.json"
                ),
                mime="application/json",
                use_container_width=True,
            )

            audit(
                "backup_exported",
                "Backup JSON preparato",
                entity_type="system_backup",
                details={
                    "generated_at": manifest["generated_at"],
                    "tables": list(manifest["tables"]),
                },
            )

        st.info(
            "Per un backup completo dello Storage, scarica separatamente i "
            "bucket privati da Supabase oppure usa uno script amministrativo."
        )

    with tab_tests:
        st.subheader("Checklist collaudo")
        checklist = [
            "Accesso manager",
            "Accesso dipendente",
            "Dipendente vede solo il proprio profilo",
            "Timbratura entrata",
            "Timbratura uscita",
            "Inserimento manuale ore",
            "Approvazione ore",
            "Rifiuto ore",
            "Caricamento documento dipendente",
            "Documento visibile solo al dipendente corretto",
            "Pubblicazione busta paga",
            "Busta paga visibile solo al dipendente corretto",
            "Registro eventi aggiornato",
            "Dashboard desktop",
            "Dashboard smartphone",
            "Sidebar mobile",
            "Backup JSON scaricabile",
        ]

        results = []
        for item in checklist:
            passed = st.checkbox(item, key=f"qa_{item}")
            results.append({"Test": item, "Superato": passed})

        passed_count = sum(1 for row in results if row["Superato"])
        st.progress(passed_count / len(results))
        st.caption(
            f"Test completati: {passed_count} su {len(results)}"
        )

        if passed_count == len(results):
            st.success("Collaudo completo.")
            if st.button("Registra collaudo completato", type="primary"):
                audit(
                    "qa_completed",
                    "Checklist di collaudo completata",
                    entity_type="quality_assurance",
                    details={"tests": len(results)},
                    severity="success",
                )
                st.success("Collaudo registrato nel Registro eventi.")

    with tab_access:
        st.subheader("Controllo associazioni account")
        accounts = (
            sb.table("employee_accounts")
            .select(
                "auth_user_id,employee_id,role,"
                "employees(name,department,active)"
            )
            .execute().data or []
        )

        rows = []
        for account in accounts:
            employee = account.get("employees") or {}
            rows.append({
                "Utente Auth": account.get("auth_user_id", ""),
                "Dipendente": employee.get("name", ""),
                "Reparto": employee.get("department", ""),
                "Ruolo": account.get("role", ""),
                "Dipendente attivo": bool(employee.get("active")),
            })

        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nessun account dipendente associato.")

        st.warning(
            "La verifica definitiva va eseguita effettuando login con almeno "
            "due account dipendente differenti e controllando documenti, "
            "buste paga e ore."
        )





elif section == "Simulazione busta paga":
    st.title("Simulazione busta paga – CCNL Turismo")
    st.caption(
        "Stima del netto mensile e del costo aziendale per il CCNL Turismo "
        "Confcommercio. Seleziona il settore applicato all’azienda."
    )
    st.warning(
        "Il risultato è indicativo e non sostituisce l'elaborazione del "
        "consulente del lavoro. Aliquote, agevolazioni, addizionali e "
        "inquadramento devono essere verificati prima dell'assunzione."
    )

    with st.form("simulatore_busta_paga"):
        st.subheader("Rapporto di lavoro")
        r1, r2, r3, r4 = st.columns(4)
        ccnl_name = r1.text_input(
            "CCNL",
            value="Turismo Confcommercio",
            disabled=True,
        )
        sector = r2.selectbox(
            "Settore",
            list(CCNL_TURISMO_2026.keys()),
            help=(
                "Il CCNL resta Turismo Confcommercio. "
                "Qui si seleziona il settore retributivo applicabile."
            ),
        )
        level = r3.selectbox(
            "Livello",
            list(CCNL_TURISMO_2026[sector].keys()),
        )
        contract_type = r4.selectbox(
            "Tipo di contratto",
            ["Tempo indeterminato", "Tempo determinato", "Apprendistato"],
        )

        m1, m2, m3 = st.columns(3)
        job_title_choice = m1.selectbox("Mansione", MANSIONI_TURISMO)
        custom_job = m2.text_input(
            "Mansione personalizzata",
            disabled=job_title_choice != "Altro",
        )
        weekly_hours = m3.number_input(
            "Ore settimanali contrattuali", 1.0, 40.0, 40.0, 1.0
        )
        job_title = (
            custom_job.strip()
            if job_title_choice == "Altro"
            else job_title_choice
        )

        st.subheader("Lavoro svolto nel mese")
        h1, h2, h3 = st.columns(3)
        ordinary_hours = h1.number_input(
            "Ore ordinarie", 0.0, 300.0, 172.0, 1.0
        )
        overtime_hours = h2.number_input(
            "Ore straordinarie", 0.0, 150.0, 0.0, 0.5
        )
        night_hours = h3.number_input(
            "Ore notturne", 0.0, 200.0, 0.0, 0.5
        )
        h4, h5, h6 = st.columns(3)
        holiday_hours = h4.number_input(
            "Ore festive", 0.0, 150.0, 0.0, 0.5
        )
        sunday_hours = h5.number_input(
            "Ore domenicali", 0.0, 150.0, 0.0, 0.5
        )
        monthly_divisor = h6.number_input(
            "Divisore orario", 1.0, 300.0, 172.0, 1.0
        )

        st.subheader("Elementi economici")
        default_minimum = CCNL_TURISMO_2026[sector][level]
        e1, e2, e3, e4 = st.columns(4)
        contractual_monthly = e1.number_input(
            "Minimo mensile CCNL",
            0.0, 10000.0, float(default_minimum), 1.0,
            help="Valore precaricato della tabella maggio 2026, modificabile.",
        )
        superminimo = e2.number_input(
            "Superminimo mensile", 0.0, 10000.0, 0.0, 10.0
        )
        bonuses = e3.number_input(
            "Premi nel mese", 0.0, 20000.0, 0.0, 10.0
        )
        allowances = e4.number_input(
            "Indennità nel mese", 0.0, 20000.0, 0.0, 10.0
        )

        with st.expander("Maggiorazioni e parametri di stima"):
            p1, p2, p3, p4 = st.columns(4)
            overtime_markup = p1.number_input(
                "Straordinario %", 0.0, 200.0, 15.0, 1.0
            )
            night_markup = p2.number_input(
                "Notturno %", 0.0, 200.0, 25.0, 1.0
            )
            holiday_markup = p3.number_input(
                "Festivo %", 0.0, 200.0, 30.0, 1.0
            )
            sunday_markup = p4.number_input(
                "Domenicale %", 0.0, 200.0, 10.0, 1.0
            )

            c1, c2, c3, c4 = st.columns(4)
            employee_contribution_rate = c1.number_input(
                "Contributi dipendente %", 0.0, 30.0, 9.19, 0.01
            )
            employer_contribution_rate = c2.number_input(
                "Contributi azienda %", 0.0, 60.0, 30.00, 0.10
            )
            inail_rate = c3.number_input(
                "INAIL stimata %", 0.0, 20.0, 1.00, 0.10
            )
            additional_tax_rate = c4.number_input(
                "Addizionali stimate %", 0.0, 10.0, 2.00, 0.10
            )
            leave_accrual_rate = st.number_input(
                "Ferie e permessi – accantonamento %",
                0.0, 30.0, 8.00, 0.10,
            )

        calculate = st.form_submit_button(
            "Calcola simulazione",
            type="primary",
            use_container_width=True,
        )

    if calculate:
        inputs = {
            "ccnl_name": ccnl_name,
            "sector": sector,
            "level": level,
            "contract_type": contract_type,
            "job_title": job_title,
            "weekly_hours": weekly_hours,
            "ordinary_hours": ordinary_hours,
            "overtime_hours": overtime_hours,
            "night_hours": night_hours,
            "holiday_hours": holiday_hours,
            "sunday_hours": sunday_hours,
            "monthly_divisor": monthly_divisor,
            "contractual_monthly": contractual_monthly,
            "superminimo": superminimo,
            "bonuses": bonuses,
            "allowances": allowances,
            "overtime_markup": overtime_markup,
            "night_markup": night_markup,
            "holiday_markup": holiday_markup,
            "sunday_markup": sunday_markup,
            "employee_contribution_rate": employee_contribution_rate,
            "employer_contribution_rate": employer_contribution_rate,
            "inail_rate": inail_rate,
            "additional_tax_rate": additional_tax_rate,
            "leave_accrual_rate": leave_accrual_rate,
        }
        result = simulate_payroll(inputs)
        st.session_state["ultima_simulazione_busta"] = {
            "inputs": inputs,
            "result": result,
        }

    simulation = st.session_state.get("ultima_simulazione_busta")
    if simulation:
        inputs = simulation["inputs"]
        result = simulation["result"]

        st.divider()
        st.subheader("Risultato della simulazione")
        n1, n2, n3, n4 = st.columns(4)
        n1.metric("Lordo mensile", euro_it(result["gross_month"]))
        n2.metric("Netto stimato", euro_it(result["net_month"]))
        n3.metric("Costo azienda", euro_it(result["company_cost"]))
        n4.metric("Costo annuo stimato", euro_it(result["annual_company_cost"]))

        tab_employee, tab_company, tab_details = st.tabs(
            ["Dipendente", "Azienda", "Dettaglio calcolo"]
        )
        with tab_employee:
            employee_rows = [
                {"Voce": "Retribuzione lorda", "Importo": euro_it(result["gross_month"])},
                {"Voce": "Contributi dipendente", "Importo": euro_it(result["employee_contributions"])},
                {"Voce": "IRPEF mensile stimata", "Importo": euro_it(result["irpef_month"])},
                {"Voce": "Addizionali stimate", "Importo": euro_it(result["additions_month"])},
                {"Voce": "Netto mensile stimato", "Importo": euro_it(result["net_month"])},
            ]
            st.dataframe(
                pd.DataFrame(employee_rows),
                use_container_width=True,
                hide_index=True,
            )

        with tab_company:
            company_rows = [
                {"Voce": "Retribuzione lorda", "Importo": euro_it(result["gross_month"])},
                {"Voce": "Contributi azienda", "Importo": euro_it(result["employer_contributions"])},
                {"Voce": "INAIL stimata", "Importo": euro_it(result["inail"])},
                {"Voce": "Rateo tredicesima", "Importo": euro_it(result["thirteenth"])},
                {"Voce": "Rateo quattordicesima", "Importo": euro_it(result["fourteenth"])},
                {"Voce": "TFR maturato", "Importo": euro_it(result["tfr"])},
                {"Voce": "Ferie e permessi", "Importo": euro_it(result["leave_accrual"])},
                {"Voce": "Costo complessivo mensile", "Importo": euro_it(result["company_cost"])},
            ]
            st.dataframe(
                pd.DataFrame(company_rows),
                use_container_width=True,
                hide_index=True,
            )

        with tab_details:
            detail_rows = [
                {"Voce": "Paga oraria", "Importo": euro_it(result["hourly_rate"])},
                {"Voce": "Ore ordinarie", "Importo": euro_it(result["ordinary_pay"])},
                {"Voce": "Straordinari", "Importo": euro_it(result["overtime_pay"])},
                {"Voce": "Maggiorazione notturna", "Importo": euro_it(result["night_pay"])},
                {"Voce": "Maggiorazione festiva", "Importo": euro_it(result["holiday_pay"])},
                {"Voce": "Maggiorazione domenicale", "Importo": euro_it(result["sunday_pay"])},
                {"Voce": "Imponibile fiscale annuo stimato", "Importo": euro_it(result["annual_taxable"])},
                {"Voce": "Detrazione lavoro annua stimata", "Importo": euro_it(result["tax_credit_annual"])},
            ]
            st.dataframe(
                pd.DataFrame(detail_rows),
                use_container_width=True,
                hide_index=True,
            )

        report_html = payroll_report_html(inputs, result)
        a1, a2 = st.columns(2)
        a1.download_button(
            "Scarica preventivo stampabile",
            data=report_html.encode("utf-8"),
            file_name=(
                "simulazione_"
                + inputs.get("job_title", "dipendente").replace(" ", "_")
                + ".html"
            ),
            mime="text/html",
            use_container_width=True,
        )
        if a2.button("Salva simulazione", use_container_width=True):
            try:
                save_payroll_simulation(inputs, result)
                audit(
                    "payroll_simulation_saved",
                    "Simulazione busta paga salvata",
                    entity_type="payroll_simulation",
                    details={
                        "job_title": inputs.get("job_title"),
                        "level": inputs.get("level"),
                        "gross": result.get("gross_month"),
                        "net": result.get("net_month"),
                        "company_cost": result.get("company_cost"),
                    },
                )
                st.success("Simulazione salvata.")
            except Exception as exc:
                st.error(
                    "Simulazione non salvata. "
                    "Esegui la migrazione Enterprise 4.2."
                )
                with st.expander("Dettaglio tecnico"):
                    st.code(technical_error_text(exc))




elif section == "Centro Controllo Enterprise":
    st.title("Centro Controllo Enterprise")
    st.caption(
        "Audit tecnico e valutazione della preparazione di RV Manager "
        "alla distribuzione commerciale."
    )

    if st.button(
        "Esegui audit completo",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Controllo del sistema in corso..."):
            checks = enterprise_audit_snapshot()
            scores, overall = enterprise_scores(checks)
            st.session_state["enterprise_audit"] = {
                "created_at": now_rome().isoformat(),
                "checks": checks,
                "scores": scores,
                "overall": overall,
            }

    if "enterprise_audit" not in st.session_state:
        checks = enterprise_audit_snapshot()
        scores, overall = enterprise_scores(checks)
        st.session_state["enterprise_audit"] = {
            "created_at": now_rome().isoformat(),
            "checks": checks,
            "scores": scores,
            "overall": overall,
        }

    audit_data = st.session_state["enterprise_audit"]
    checks = audit_data["checks"]
    scores = audit_data["scores"]
    overall = audit_data["overall"]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Enterprise Readiness", f"{overall}%")
    k2.metric(
        "Controlli superati",
        sum(1 for row in checks if row["Stato"] == "SUPERATO"),
    )
    k3.metric(
        "Da risolvere",
        sum(1 for row in checks if row["Stato"] != "SUPERATO"),
    )
    k4.metric(
        "Ultimo audit",
        format_datetime_it(audit_data["created_at"]),
    )

    if overall >= 95:
        st.success(f"**{readiness_label(overall)}**")
    elif overall >= 85:
        st.warning(f"**{readiness_label(overall)}**")
    else:
        st.error(f"**{readiness_label(overall)}**")

    st.subheader("Punteggi per area")
    score_rows = [
        {"Area": area, "Punteggio": score}
        for area, score in sorted(scores.items())
    ]
    score_df = pd.DataFrame(score_rows)
    st.dataframe(
        score_df,
        use_container_width=True,
        hide_index=True,
    )

    if not score_df.empty:
        chart_df = score_df.set_index("Area")
        st.bar_chart(chart_df)

    tab_summary, tab_issues, tab_all, tab_release = st.tabs(
        [
            "Riepilogo",
            "Interventi richiesti",
            "Tutti i controlli",
            "Percorso LTS",
        ]
    )

    with tab_summary:
        area_groups = {}
        for row in checks:
            area_groups.setdefault(row["Area"], []).append(row)

        for area, rows in sorted(area_groups.items()):
            passed = sum(1 for row in rows if row["Stato"] == "SUPERATO")
            with st.container(border=True):
                st.markdown(f"**{area}**")
                st.caption(f"{passed} controlli superati su {len(rows)}")

    with tab_issues:
        issues = [
            row for row in checks
            if row["Stato"] != "SUPERATO"
        ]
        if not issues:
            st.success("Non risultano interventi tecnici aperti.")
        else:
            issue_df = pd.DataFrame(issues)[
                ["Area", "Controllo", "Stato", "Dettaglio"]
            ]
            st.dataframe(
                issue_df,
                use_container_width=True,
                hide_index=True,
            )

    with tab_all:
        all_df = pd.DataFrame(checks)[
            ["Area", "Controllo", "Stato", "Dettaglio"]
        ]
        st.dataframe(
            all_df,
            use_container_width=True,
            hide_index=True,
        )

        audit_json = json.dumps(
            {
                "versione": "4.4.0",
                "data": audit_data["created_at"],
                "enterprise_readiness": overall,
                "punteggi": scores,
                "controlli": checks,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ).encode("utf-8")

        st.download_button(
            "Scarica report audit",
            data=audit_json,
            file_name=(
                "enterprise_readiness_"
                + now_rome().strftime("%Y%m%d_%H%M%S")
                + ".json"
            ),
            mime="application/json",
            use_container_width=True,
        )

    with tab_release:
        st.markdown(
            """
            **Percorso per RV Manager Enterprise 2026 LTS**

            1. Risolvere tutti i controlli ad alta priorità.
            2. Eseguire il test con due account dipendente differenti.
            3. Eseguire e verificare un backup.
            4. Collaudare ogni pagina da desktop e smartphone.
            5. Congelare il codice della versione candidata.
            6. Creare il tag `2026-LTS-RC1`.
            7. Eseguire un periodo pilota con dati controllati.
            8. Pubblicare la versione LTS soltanto dopo il collaudo finale.
            """
        )

        st.info(
            "Il punteggio automatico è uno strumento interno. "
            "Non costituisce una certificazione legale o di sicurezza."
        )


elif section == "Stato del sistema":
    st.title("Stato del sistema")
    st.caption(
        "Controllo automatico dell'affidabilità, della sicurezza e dei servizi "
        "principali di RV Manager."
    )

    env_info = runtime_environment_snapshot()

    if env_info["is_staging"]:
        st.warning("Ambiente STAGING: utilizzare solo dati fittizi o anonimizzati.")
    elif env_info["is_production"]:
        st.error(
            "Ambiente PRODUZIONE: evitare prove distruttive e installare "
            "solo aggiornamenti già collaudati."
        )
    else:
        st.info(f"Ambiente rilevato: {env_info['environment'].upper()}")

    if st.button(
        "Esegui controllo completo del sistema",
        type="primary",
        use_container_width=True,
    ):
        st.session_state["ultimo_controllo_sistema"] = {
            "data": format_datetime_it(datetime.now(UTC_TZ).isoformat()),
            "risultati": system_health_snapshot(),
        }

    if "ultimo_controllo_sistema" not in st.session_state:
        st.session_state["ultimo_controllo_sistema"] = {
            "data": format_datetime_it(datetime.now(UTC_TZ).isoformat()),
            "risultati": system_health_snapshot(),
        }

    health_data = st.session_state["ultimo_controllo_sistema"]
    health_rows = health_data["risultati"]

    operational = sum(
        1 for row in health_rows if row["Stato"] == "OPERATIVO"
    )
    total_checks = len(health_rows)
    pending = total_checks - operational

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Controlli superati", f"{operational}/{total_checks}")
    c2.metric("Da verificare", pending)
    c3.metric("Ambiente", env_info["environment"].upper())
    c4.metric("Ultimo controllo", health_data["data"])

    if pending == 0:
        st.success(
            "Il sistema risulta operativo nei controlli automatici eseguiti."
        )
    else:
        st.warning(
            f"{pending} controllo/i richiedono attenzione. "
            "Apri i dettagli qui sotto."
        )

    st.subheader("Riepilogo")
    for row in health_rows:
        with st.container(border=True):
            left, right = st.columns([1, 5])
            left.markdown(f"### {health_status_icon(row['Stato'])}")
            right.markdown(f"**{row['Controllo']}**")
            right.caption(row["Dettaglio"])


    st.divider()
    st.subheader("Centro backup")
    st.caption(
        "Backup manuali e automatici sono gestiti qui, senza aggiungere "
        "nuove voci al menu."
    )

    backup_records = list_backup_records(limit=30)
    latest_backup = backup_records[0] if backup_records else None

    b1, b2, b3, b4 = st.columns(4)
    b1.metric(
        "Ultimo backup",
        format_datetime_it(latest_backup.get("created_at"))
        if latest_backup else "Mai eseguito",
    )
    b2.metric(
        "Tipo",
        translate_it(latest_backup.get("backup_type")).capitalize()
        if latest_backup else "—",
    )
    b3.metric(
        "Dimensione",
        backup_size_label(latest_backup.get("size_bytes"))
        if latest_backup else "—",
    )
    b4.metric(
        "Integrità",
        "Da verificare" if latest_backup else "—",
    )

    st.markdown("#### Backup manuale")
    manual_col1, manual_col2 = st.columns(2)

    if manual_col1.button(
        "Esegui backup adesso",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Creazione e archiviazione del backup..."):
                package = create_cloud_backup("manuale")
            st.session_state["ultimo_backup_generato"] = package
            st.success(
                f"Backup completato: {package['filename']} "
                f"({backup_size_label(package['size_bytes'])})."
            )
            st.rerun()
        except Exception as exc:
            st.error(
                "Backup non completato. Verifica di aver eseguito la "
                "migrazione Enterprise 4.1 e che il bucket sia disponibile."
            )
            with st.expander("Dettaglio tecnico"):
                st.code(technical_error_text(exc))

    generated_backup = st.session_state.get("ultimo_backup_generato")
    if generated_backup:
        manual_col2.download_button(
            "Scarica ultimo backup creato",
            data=generated_backup["bytes"],
            file_name=generated_backup["filename"],
            mime="application/json",
            use_container_width=True,
        )
    else:
        manual_col2.button(
            "Scarica ultimo backup creato",
            disabled=True,
            use_container_width=True,
        )

    st.markdown("#### Backup automatici")
    settings = get_backup_settings()

    with st.form("configurazione_backup_automatici"):
        auto_enabled = st.toggle(
            "Backup automatici attivi",
            value=bool(settings.get("enabled")),
        )
        s1, s2, s3 = st.columns(3)
        frequency_options = ["giornaliero", "settimanale", "mensile"]
        current_frequency = settings.get("frequency", "giornaliero")
        frequency_index = (
            frequency_options.index(current_frequency)
            if current_frequency in frequency_options else 0
        )
        auto_frequency = s1.selectbox(
            "Frequenza",
            frequency_options,
            index=frequency_index,
        )
        auto_hour = s2.number_input(
            "Ora di esecuzione",
            min_value=0,
            max_value=23,
            value=int(settings.get("run_hour") or 2),
            step=1,
        )
        retention_count = s3.number_input(
            "Backup da conservare",
            min_value=3,
            max_value=365,
            value=int(settings.get("retention_count") or 30),
            step=1,
        )

        save_auto = st.form_submit_button(
            "Salva configurazione backup",
            type="primary",
            use_container_width=True,
        )

    if save_auto:
        try:
            save_backup_settings(
                auto_enabled,
                auto_frequency,
                auto_hour,
                retention_count,
            )
            st.success("Configurazione dei backup automatici salvata.")
        except Exception as exc:
            st.error(
                "Configurazione non salvata. Esegui la migrazione "
                "Enterprise 4.1."
            )
            with st.expander("Dettaglio tecnico"):
                st.code(technical_error_text(exc))

    st.info(
        "L'esecuzione automatica affidabile viene effettuata dal processo "
        "programmato incluso nel pacchetto. Dopo l'installazione occorre "
        "configurare i due Secrets GitHub SUPABASE_URL e "
        "SUPABASE_SECRET_KEY."
    )

    st.markdown("#### Storico backup")
    if backup_records:
        history_rows = []
        for row in backup_records:
            history_rows.append({
                "Data": format_datetime_it(row.get("created_at")),
                "Tipo": translate_it(row.get("backup_type")).capitalize(),
                "Dimensione": backup_size_label(row.get("size_bytes")),
                "Stato": translate_it(row.get("status")).capitalize(),
                "Nome file": row.get("file_name", ""),
                "Percorso": row.get("storage_path", ""),
            })
        st.dataframe(
            pd.DataFrame(history_rows),
            use_container_width=True,
            hide_index=True,
        )

        selected_backup = st.selectbox(
            "Backup da verificare o scaricare",
            options=backup_records,
            format_func=lambda row: (
                f"{format_datetime_it(row.get('created_at'))} · "
                f"{row.get('backup_type', '').capitalize()} · "
                f"{row.get('file_name', '')}"
            ),
        )

        action1, action2 = st.columns(2)
        if action1.button(
            "Verifica integrità",
            use_container_width=True,
        ):
            try:
                ok, message = verify_backup_integrity(selected_backup)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as exc:
                st.error("Verifica non completata.")
                with st.expander("Dettaglio tecnico"):
                    st.code(technical_error_text(exc))

        try:
            selected_payload = sb.storage.from_(BACKUP_BUCKET).download(
                selected_backup.get("storage_path")
            )
            action2.download_button(
                "Scarica backup selezionato",
                data=selected_payload,
                file_name=selected_backup.get("file_name", "backup.json"),
                mime="application/json",
                use_container_width=True,
            )
        except Exception:
            action2.button(
                "Scarica backup selezionato",
                disabled=True,
                use_container_width=True,
            )
    else:
        st.info("Nessun backup presente nello storico.")


    with st.expander("Dettagli tecnici per amministratori"):
        technical_df = pd.DataFrame(health_rows)[
            ["Categoria", "Controllo", "Stato", "Dettaglio tecnico"]
        ]
        st.dataframe(
            technical_df,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Questa sezione è destinata all'amministratore tecnico e può "
            "contenere informazioni utili per l'assistenza."
        )

    with st.expander("Protezione delle tabelle"):
        rls_rows = rls_diagnostic_snapshot()
        st.dataframe(
            pd.DataFrame(rls_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "RLS impedisce agli utenti non autorizzati di accedere ai dati "
            "di altri dipendenti. Le policy stabiliscono quali operazioni "
            "sono consentite."
        )

    with st.expander("Verifica manuale tra utenti"):
        st.markdown(
            """
            1. Accedi con il dipendente A e annota documenti, ore e buste paga.
            2. Esci e accedi con il dipendente B.
            3. Verifica che B non possa vedere i dati di A.
            4. Ripeti il controllo invertendo i due account.
            5. Esegui questo test in staging prima di ogni rilascio.
            """
        )
        st.warning(
            "Il controllo automatico verifica configurazione e servizi, "
            "ma non sostituisce il test reale con due account distinti."
        )


elif section == "Fringe benefit":
    st.title("Fringe benefit")
    employees = employees_df()
    if not employees.empty:
        with st.form("fringe"):
            name = st.selectbox("Dipendente", employees["name"].tolist())
            employee_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
            d = st.date_input("Data", value=date(year, month, 1), format="DD/MM/YYYY")
            amount = st.number_input("Importo", min_value=0.0, step=10.0)
            category = st.selectbox("Categoria", ["Buoni", "Alloggio", "Auto", "Telefono", "Pasto", "Altro"])
            note = st.text_input("Nota")
            save = st.form_submit_button("Registra altro costo", type="primary")
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
    st.title("Altri costi da regolarizzare")
    st.warning(
        "Registro interno. Gli importi devono essere comunicati e "
        "regolarizzati con il consulente. Ogni importo viene sommato, "
        "come «Altro costo», al costo aziendale importato del dipendente "
        "nel mese della data selezionata."
    )
    employees = employees_df()
    if not employees.empty:
        with st.form("extra"):
            name = st.selectbox("Dipendente", employees["name"].tolist())
            employee_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
            d = st.date_input("Data", value=date(year, month, 1), format="DD/MM/YYYY")
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
            selected_year = d.year
            selected_month = d.month
            start_extra, end_extra = month_bounds(selected_year, selected_month)
            monthly_extras = (
                sb.table("extra_payments")
                .select("amount")
                .eq("employee_id", employee_id)
                .gte("payment_date", start_extra.isoformat())
                .lt("payment_date", end_extra.isoformat())
                .execute().data or []
            )
            total_other_cost = sum(
                float(row.get("amount") or 0)
                for row in monthly_extras
            )
            imported_cost_rows = (
                sb.table("monthly_costs")
                .select("company_cost")
                .eq("employee_id", employee_id)
                .eq("year", selected_year)
                .eq("month", selected_month)
                .limit(1)
                .execute().data or []
            )
            imported_cost = (
                float(imported_cost_rows[0].get("company_cost") or 0)
                if imported_cost_rows else 0
            )
            st.success(
                f"Altro costo registrato. Totale altri costi di "
                f"{MONTHS[selected_month]} {selected_year}: "
                f"{euro(total_other_cost)}. Costo complessivo del "
                f"dipendente: {euro(imported_cost + total_other_cost)}."
            )

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
