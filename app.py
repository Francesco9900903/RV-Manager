
import re
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader
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
def supabase():
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

sb = supabase()

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

def find_amount(block, label):
    m = re.search(rf"{re.escape(label)}\s+([\d\.,-]+)", block, re.I)
    return parse_it_number(m.group(1)) if m else 0.0

def parse_cost_report(text):
    pm = re.search(r"periodo da\s+(\d{2})/(\d{4})\s+a\s+\d{2}/\d{4}", text, re.I)
    if not pm:
        raise ValueError("Periodo non riconosciuto.")
    year, month = int(pm.group(2)), int(pm.group(1))

    sections = re.split(r"(?=Dipendente\s*:\s*\d+)", text, flags=re.I)
    parsed = []
    for block in sections:
        h = re.search(r"Dipendente\s*:\s*(\d+)\s+([^\n]+)", block, re.I)
        totals = re.findall(r"Totale dipendente:\s*([\d\.,]+)", block, re.I)
        if not h or not totals:
            continue
        parsed.append({
            "code": h.group(1).strip(),
            "name": re.sub(r"\s{2,}.*$", "", h.group(2).strip()),
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
        raise ValueError("Nessun dipendente riconosciuto nel PDF.")
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

st.sidebar.title("RV Manager")
section = st.sidebar.radio(
    "Personale",
    ["Cruscotto", "Importa costi", "Dipendenti", "Scheda dipendente",
     "Fringe benefit", "Extra da regolarizzare", "Dati del mese"]
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
