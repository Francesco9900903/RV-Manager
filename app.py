
import re
from datetime import date, datetime, timedelta, time
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader, PdfWriter
from supabase import create_client

st.set_page_config(page_title="RV Manager", page_icon="👥", layout="wide")

MONTHS = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

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

        sb.storage.from_("payslips").upload(
            storage_path,
            output.getvalue(),
            {
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

    st.sidebar.title("RV Manager")
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

    tabs = st.tabs(["Timbratura", "Inserimento manuale", "Storico", "Buste paga"])

    with tabs[0]:
        st.title("Timbratura")
        st.caption(f"{employee.get('name')} · {today.strftime('%d/%m/%Y')}")

        open_shift = current_open_shift(employee_id, public_sb)
        if open_shift:
            started = datetime.fromisoformat(open_shift["clock_in"].replace("Z", "+00:00"))
            st.success(f"Entrata registrata alle {started.astimezone().strftime('%H:%M')}")
            break_minutes = st.number_input(
                "Pausa totale da sottrarre (minuti)",
                min_value=0,
                max_value=480,
                value=int(open_shift.get("break_minutes") or 0),
                step=5,
            )
            if st.button("Registra uscita", type="primary", use_container_width=True):
                now = datetime.now().astimezone()
                public_sb.table("clock_entries").update({
                    "clock_out": now.isoformat(),
                    "break_minutes": break_minutes,
                    "status": "submitted",
                }).eq("id", open_shift["id"]).execute()
                refresh_timesheet_from_clock(employee_id, today, public_sb)
                st.success("Uscita registrata. Le ore sono state inviate al responsabile.")
                st.rerun()
        else:
            shift_type = st.selectbox("Turno", ["Pranzo", "Cena", "Spezzato", "Altro"])
            if st.button("Registra entrata", type="primary", use_container_width=True):
                now = datetime.now().astimezone()
                public_sb.table("clock_entries").insert({
                    "employee_id": employee_id,
                    "work_date": today.isoformat(),
                    "clock_in": now.isoformat(),
                    "shift_type": shift_type,
                    "status": "open",
                }).execute()
                st.success("Entrata registrata.")
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
            st.dataframe(pd.DataFrame(day_entries), use_container_width=True, hide_index=True)

    with tabs[1]:
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
                st.success("Ore inviate al responsabile.")

    with tabs[2]:
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

    with tabs[3]:
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

        sb.storage.from_("payslips").upload(
            storage_path,
            output.getvalue(),
            {
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


st.sidebar.title("RV Manager")
st.sidebar.caption("Versione 3.6 stabile")
section = st.sidebar.radio(
    "Personale",
    ["Cruscotto", "Importa costi", "Dipendenti", "Scheda dipendente",
     "Ore e approvazioni", "Accessi dipendenti", "Buste paga", "Fringe benefit",
     "Extra da regolarizzare", "Dati del mese"]
)

today = date.today()
years = list(range(2025, today.year + 2))
year = st.sidebar.selectbox("Anno", years, index=years.index(today.year))
month = st.sidebar.selectbox("Mese", list(MONTHS), format_func=lambda x: MONTHS[x], index=today.month - 1)

if section == "Cruscotto":
    st.title("Cruscotto gestione personale")
    st.caption(f"{MONTHS[month]} {year}")

    df, revenue, covers = month_data(year, month)
    if df.empty:
        st.info("Non risultano ancora costi importati per questo mese.")
    else:
        official = df["company_cost"].sum()
        extra = df["extra_cash"].sum()
        fringe = df["fringe"].sum()
        total = df["management_cost"].sum()
        hours = df["hours"].sum()
        incidence = total / revenue * 100 if revenue else 0

        a, b, c, d = st.columns(4)
        a.metric("Costo aziendale", euro(official))
        b.metric("Extra registrati", euro(extra))
        c.metric("Fringe benefit", euro(fringe))
        d.metric("Costo gestionale", euro(total))

        e, f, g, h = st.columns(4)
        e.metric("Fatturato", euro(revenue))
        f.metric("Incidenza personale", f"{incidence:.1f}%")
        g.metric("Costo medio/ora", euro(total / hours) if hours else "Ore mancanti")
        h.metric("Costo/coperto", euro(total / covers) if covers else "Coperti mancanti")

        st.subheader("Costo per reparto")
        st.bar_chart(df.groupby("department")["management_cost"].sum())

        view = df[["name", "department", "hours", "net_pay", "gross_pay",
                   "company_cost", "fringe", "extra_cash", "management_cost"]].copy()
        view.columns = ["Dipendente", "Reparto", "Ore", "Netto", "Lordo",
                        "Costo azienda", "Fringe", "Extra", "Costo gestionale"]
        for col in ["Netto", "Lordo", "Costo azienda", "Fringe", "Extra", "Costo gestionale"]:
            view[col] = view[col].map(euro)
        st.dataframe(view, use_container_width=True, hide_index=True)

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
                    "approved_at": datetime.now().astimezone().isoformat(),
                }, on_conflict="employee_id,work_date").execute()

                total = sync_monthly_hours(employee_id, work_date.year, work_date.month)
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
                            "approved_at": datetime.now().astimezone().isoformat(),
                        }).eq("id", options[selected]).execute()
                        total = sync_monthly_hours(employee_id, year, month)
                        st.success(f"Approvata. Totale mensile: {total:.2f} ore.")
                        st.rerun()
                    if c2.button("Rifiuta"):
                        sb.table("timesheets").update({
                            "status": "rejected",
                        }).eq("id", options[selected]).execute()
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
            detected_year, detected_month, saved, unresolved = split_and_store_payslips(
                uploaded, fallback_year, fallback_month
            )
            employee_names = {
                int(row["id"]): row["name"]
                for row in sb.table("employees").select("id,name").execute().data or []
            }
            st.success(
                f"Pubblicate {len(saved)} buste paga per "
                f"{MONTHS[detected_month]} {detected_year}."
            )
            result_rows = []
            for item in saved:
                result_rows.append({
                    "Dipendente": employee_names.get(item["employee_id"], item["employee_id"]),
                    "Pagine": ", ".join(map(str, item["pages"])),
                    "Stato": "Pubblicata",
                })
            st.dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)

            if unresolved:
                st.warning(
                    "Pagine non riconosciute e non pubblicate: "
                    + ", ".join(map(str, unresolved))
                )
        except Exception as exc:
            st.error(f"Elaborazione non riuscita: {exc}")

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
        st.success("Dati aggiornati.")
