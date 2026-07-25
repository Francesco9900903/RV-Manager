
import io
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf import PdfReader

DB_PATH = Path(__file__).with_name("personale.db")

st.set_page_config(
    page_title="La Cambusa - Gestione Personale",
    page_icon="👥",
    layout="wide",
)

# -------------------- DATABASE --------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            role TEXT,
            level TEXT,
            department TEXT DEFAULT 'Da assegnare',
            hire_date TEXT,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS monthly_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            gross_pay REAL DEFAULT 0,
            social_charges REAL DEFAULT 0,
            other_charges REAL DEFAULT 0,
            tfr REAL DEFAULT 0,
            inail REAL DEFAULT 0,
            company_cost REAL DEFAULT 0,
            net_pay REAL DEFAULT 0,
            hours REAL DEFAULT 0,
            source_file TEXT,
            UNIQUE(employee_id, year, month),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS fringe_benefits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            benefit_date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            note TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS extra_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            payment_method TEXT DEFAULT 'Da regolarizzare',
            regularized INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS monthly_revenue (
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            revenue REAL DEFAULT 0,
            covers INTEGER DEFAULT 0,
            PRIMARY KEY(year, month)
        );

        CREATE TABLE IF NOT EXISTS employee_profiles (
            employee_id INTEGER PRIMARY KEY,
            phone TEXT,
            email TEXT,
            tax_code TEXT,
            iban TEXT,
            address TEXT,
            contract_type TEXT,
            contract_end TEXT,
            weekly_hours REAL DEFAULT 0,
            emergency_contact TEXT,
            notes TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS employee_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            details TEXT,
            amount REAL DEFAULT 0,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS employee_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT,
            issue_date TEXT,
            expiry_date TEXT,
            status TEXT DEFAULT 'Valido',
            note TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS employee_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            rating_date TEXT NOT NULL,
            punctuality INTEGER DEFAULT 0,
            professionalism INTEGER DEFAULT 0,
            sales INTEGER DEFAULT 0,
            flexibility INTEGER DEFAULT 0,
            teamwork INTEGER DEFAULT 0,
            leadership INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        """
    )
    conn.commit()
    conn.close()

init_db()

# -------------------- HELPERS --------------------

MONTHS = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

def euro(v):
    return f"€ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_it_number(s):
    if s is None:
        return 0.0
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def pdf_to_text(uploaded):
    reader = PdfReader(uploaded)
    return "\n".join((page.extract_text() or "") for page in reader.pages)

def parse_period(text):
    m = re.search(r"periodo da\s+(\d{2})/(\d{4})\s+a\s+\d{2}/\d{4}", text, re.I)
    if not m:
        return None, None
    return int(m.group(2)), int(m.group(1))

def parse_total_company(text):
    m = re.search(r"Totale ditta:\s*([\d\.,]+)", text, re.I)
    return parse_it_number(m.group(1)) if m else 0.0

def extract_value(block, label):
    m = re.search(rf"{re.escape(label)}\s+([\d\.,-]+)", block, re.I)
    return parse_it_number(m.group(1)) if m else 0.0

def parse_employee_costs(text):
    # Split on each employee section.
    pieces = re.split(r"(?=Dipendente\s*:\s*\d+)", text, flags=re.I)
    rows = []
    for block in pieces:
        head = re.search(r"Dipendente\s*:\s*(\d+)\s+([^\n]+)", block, re.I)
        if not head:
            continue
        code = head.group(1).strip()
        name = head.group(2).strip()
        # Stop accidental carry-over at next headings.
        name = re.sub(r"\s{2,}.*$", "", name)
        total_matches = re.findall(r"Totale dipendente:\s*([\d\.,]+)", block, re.I)
        if not total_matches:
            continue
        total = parse_it_number(total_matches[-1])
        gross = extract_value(block, "Retribuzioni lorde")
        social = extract_value(block, "Oneri sociali")
        other = extract_value(block, "Altri oneri")
        inail = extract_value(block, "INAIL")
        tfr = (
            extract_value(block, "TFR esercizio")
            + extract_value(block, "TFR erogato")
            + extract_value(block, "TFR previdenza complementare")
        )
        rows.append({
            "code": code,
            "name": name,
            "gross_pay": gross,
            "social_charges": social,
            "other_charges": other,
            "tfr": tfr,
            "inail": inail,
            "company_cost": total,
        })
    return rows

def upsert_employee(conn, code, name):
    conn.execute(
        """
        INSERT INTO employees(code, name)
        VALUES(?, ?)
        ON CONFLICT(code) DO UPDATE SET name=excluded.name
        """,
        (code, name),
    )
    return conn.execute("SELECT id FROM employees WHERE code=?", (code,)).fetchone()[0]

def import_cost_pdf(uploaded):
    text = pdf_to_text(uploaded)
    year, month = parse_period(text)
    if not year or not month:
        raise ValueError("Periodo mensile non riconosciuto nel PDF.")
    rows = parse_employee_costs(text)
    if not rows:
        raise ValueError("Nessun costo dipendente riconosciuto nel PDF.")

    conn = get_conn()
    for r in rows:
        emp_id = upsert_employee(conn, r["code"], r["name"])
        conn.execute(
            """
            INSERT INTO monthly_costs(
                employee_id, year, month, gross_pay, social_charges,
                other_charges, tfr, inail, company_cost, source_file
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(employee_id, year, month) DO UPDATE SET
                gross_pay=excluded.gross_pay,
                social_charges=excluded.social_charges,
                other_charges=excluded.other_charges,
                tfr=excluded.tfr,
                inail=excluded.inail,
                company_cost=excluded.company_cost,
                source_file=excluded.source_file
            """,
            (
                emp_id, year, month, r["gross_pay"], r["social_charges"],
                r["other_charges"], r["tfr"], r["inail"], r["company_cost"],
                uploaded.name,
            ),
        )
    conn.commit()
    conn.close()
    return year, month, len(rows), parse_total_company(text)

def month_totals(year, month):
    conn = get_conn()
    costs = pd.read_sql_query(
        """
        SELECT e.id, e.code, e.name, e.department, e.role, e.level,
               c.gross_pay, c.social_charges, c.other_charges, c.tfr,
               c.inail, c.company_cost, c.net_pay, c.hours
        FROM monthly_costs c
        JOIN employees e ON e.id=c.employee_id
        WHERE c.year=? AND c.month=?
        ORDER BY e.name
        """,
        conn,
        params=(year, month),
    )
    fringe = pd.read_sql_query(
        """
        SELECT employee_id, COALESCE(SUM(amount),0) amount
        FROM fringe_benefits
        WHERE substr(benefit_date,1,7)=?
        GROUP BY employee_id
        """,
        conn,
        params=(f"{year:04d}-{month:02d}",),
    )
    extra = pd.read_sql_query(
        """
        SELECT employee_id, COALESCE(SUM(amount),0) amount
        FROM extra_payments
        WHERE substr(payment_date,1,7)=?
        GROUP BY employee_id
        """,
        conn,
        params=(f"{year:04d}-{month:02d}",),
    )
    rev = conn.execute(
        "SELECT revenue, covers FROM monthly_revenue WHERE year=? AND month=?",
        (year, month),
    ).fetchone()
    conn.close()

    if costs.empty:
        return costs, 0.0, 0, 0.0, 0.0

    costs = costs.merge(fringe, how="left", left_on="id", right_on="employee_id")
    costs = costs.rename(columns={"amount": "fringe"})
    costs = costs.drop(columns=["employee_id"], errors="ignore")
    costs = costs.merge(extra, how="left", left_on="id", right_on="employee_id")
    costs = costs.rename(columns={"amount": "extra_cash"})
    costs = costs.drop(columns=["employee_id"], errors="ignore")
    costs["fringe"] = costs["fringe"].fillna(0)
    costs["extra_cash"] = costs["extra_cash"].fillna(0)
    costs["gestional_cost"] = costs["company_cost"] + costs["extra_cash"]
    revenue, covers = rev if rev else (0.0, 0)
    return costs, float(revenue), int(covers), costs["fringe"].sum(), costs["extra_cash"].sum()

# -------------------- SIDEBAR --------------------

st.sidebar.title("La Cambusa")
section = st.sidebar.radio(
    "Modulo personale",
    ["Cruscotto", "Importa costi", "Dipendenti", "Scheda dipendente", "Fringe benefit", "Extra da regolarizzare", "Impostazioni mese"]
)

today = date.today()
years = list(range(2025, today.year + 2))
selected_year = st.sidebar.selectbox("Anno", years, index=years.index(today.year))
selected_month = st.sidebar.selectbox(
    "Mese", list(MONTHS.keys()),
    format_func=lambda x: MONTHS[x],
    index=today.month - 1
)

# -------------------- DASHBOARD --------------------

if section == "Cruscotto":
    st.title("Cruscotto gestione personale")
    st.caption(f"{MONTHS[selected_month]} {selected_year}")

    df, revenue, covers, fringe_total, extra_total = month_totals(selected_year, selected_month)

    if df.empty:
        st.info("Non risultano ancora costi del personale importati per questo mese.")
    else:
        official_cost = df["company_cost"].sum()
        gestional_cost = df["gestional_cost"].sum()
        hours = df["hours"].sum()
        incidence = (gestional_cost / revenue * 100) if revenue else 0
        cost_per_hour = (gestional_cost / hours) if hours else 0
        cost_per_cover = (gestional_cost / covers) if covers else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Costo aziendale ufficiale", euro(official_cost))
        c2.metric("Extra registrati", euro(extra_total))
        c3.metric("Fringe benefit", euro(fringe_total))
        c4.metric("Costo gestionale", euro(gestional_cost))

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Fatturato", euro(revenue))
        c6.metric("Incidenza personale", f"{incidence:.1f}%")
        c7.metric("Costo medio/ora", euro(cost_per_hour) if hours else "Ore mancanti")
        c8.metric("Costo per coperto", euro(cost_per_cover) if covers else "Coperti mancanti")

        if revenue:
            if incidence <= 30:
                st.success(f"Incidenza personale {incidence:.1f}%: entro l'obiettivo del 30%.")
            elif incidence <= 35:
                st.warning(f"Incidenza personale {incidence:.1f}%: fascia di attenzione.")
            else:
                st.error(f"Incidenza personale {incidence:.1f}%: superiore al 35%.")

        chart = df.groupby("department", dropna=False)["gestional_cost"].sum().sort_values(ascending=False)
        st.subheader("Costo per reparto")
        st.bar_chart(chart)

        st.subheader("Costo per dipendente")
        view = df[[
            "name", "department", "hours", "gross_pay", "social_charges",
            "tfr", "inail", "company_cost", "fringe", "extra_cash", "gestional_cost"
        ]].copy()
        view.columns = [
            "Dipendente", "Reparto", "Ore", "Lordo", "Oneri sociali",
            "TFR", "INAIL", "Costo azienda", "Fringe", "Extra", "Costo gestionale"
        ]
        for col in ["Lordo", "Oneri sociali", "TFR", "INAIL", "Costo azienda", "Fringe", "Extra", "Costo gestionale"]:
            view[col] = view[col].map(euro)
        st.dataframe(view, use_container_width=True, hide_index=True)

# -------------------- IMPORT --------------------

elif section == "Importa costi":
    st.title("Importazione prospetto costi paghe")
    st.write(
        "Carica il PDF **Costo del personale - singoli dipendenti/complessivo per ditta**. "
        "Il sistema riconosce periodo, dipendenti e costo aziendale."
    )
    uploaded = st.file_uploader("PDF costi paghe", type=["pdf"])
    if uploaded and st.button("Importa PDF", type="primary"):
        try:
            y, m, count, total = import_cost_pdf(uploaded)
            st.success(
                f"Importati {count} dipendenti per {MONTHS[m]} {y}. "
                f"Totale ditta rilevato: {euro(total)}."
            )
        except Exception as exc:
            st.error(f"Importazione non riuscita: {exc}")

    st.divider()
    st.subheader("Inserimento ore e netto")
    st.caption("Questi valori possono essere importati in una fase successiva dai cedolini oppure inseriti manualmente.")
    conn = get_conn()
    employees = pd.read_sql_query("SELECT id, name FROM employees ORDER BY name", conn)
    conn.close()
    if not employees.empty:
        emp_name = st.selectbox("Dipendente", employees["name"].tolist())
        emp_id = int(employees.loc[employees["name"] == emp_name, "id"].iloc[0])
        col1, col2 = st.columns(2)
        hours = col1.number_input("Ore del mese", min_value=0.0, step=0.5)
        net = col2.number_input("Netto in busta", min_value=0.0, step=10.0)
        if st.button("Salva ore e netto"):
            conn = get_conn()
            conn.execute(
                """
                INSERT INTO monthly_costs(employee_id, year, month, hours, net_pay)
                VALUES(?,?,?,?,?)
                ON CONFLICT(employee_id, year, month) DO UPDATE SET
                    hours=excluded.hours, net_pay=excluded.net_pay
                """,
                (emp_id, selected_year, selected_month, hours, net),
            )
            conn.commit()
            conn.close()
            st.success("Ore e netto aggiornati.")

# -------------------- EMPLOYEES --------------------

elif section == "Dipendenti":
    st.title("Anagrafica dipendenti")
    conn = get_conn()
    employees = pd.read_sql_query("SELECT * FROM employees ORDER BY name", conn)
    conn.close()
    if employees.empty:
        st.info("Importa almeno un prospetto paghe.")
    else:
        edited = st.data_editor(
            employees[["id", "code", "name", "role", "level", "department", "hire_date", "active"]],
            use_container_width=True,
            hide_index=True,
            disabled=["id", "code", "name"],
            column_config={
                "department": st.column_config.SelectboxColumn(
                    "Reparto",
                    options=["Sala", "Bar", "Cucina", "Amministrazione", "Da assegnare"]
                ),
                "active": st.column_config.CheckboxColumn("Attivo"),
            },
        )
        if st.button("Salva anagrafica", type="primary"):
            conn = get_conn()
            for _, r in edited.iterrows():
                conn.execute(
                    """
                    UPDATE employees
                    SET role=?, level=?, department=?, hire_date=?, active=?
                    WHERE id=?
                    """,
                    (r["role"], r["level"], r["department"], r["hire_date"], int(bool(r["active"])), int(r["id"])),
                )
            conn.commit()
            conn.close()
            st.success("Anagrafica aggiornata.")


# -------------------- EMPLOYEE DETAIL --------------------

elif section == "Scheda dipendente":
    st.title("Scheda dipendente definitiva")
    conn = get_conn()
    employees = pd.read_sql_query(
        "SELECT id, code, name, role, level, department, hire_date FROM employees ORDER BY name",
        conn
    )
    conn.close()

    if employees.empty:
        st.info("Importa prima un prospetto paghe per creare l'anagrafica.")
    else:
        selected_name = st.selectbox("Seleziona dipendente", employees["name"].tolist())
        emp = employees.loc[employees["name"] == selected_name].iloc[0]
        emp_id = int(emp["id"])

        conn = get_conn()
        profile = conn.execute(
            """
            SELECT phone, email, tax_code, iban, address, contract_type,
                   contract_end, weekly_hours, emergency_contact, notes
            FROM employee_profiles WHERE employee_id=?
            """,
            (emp_id,),
        ).fetchone()
        conn.close()

        profile = profile or ("", "", "", "", "", "", "", 0, "", "")

        st.subheader(selected_name)
        a, b, c, d = st.columns(4)
        a.metric("Reparto", emp["department"] or "Da assegnare")
        b.metric("Ruolo", emp["role"] or "Da definire")
        c.metric("Livello", emp["level"] or "Da definire")
        d.metric("Codice", emp["code"])

        tabs = st.tabs([
            "Dati e contratto", "Costi e paghe", "Timeline",
            "Documenti e scadenze", "Valutazione", "Note"
        ])

        with tabs[0]:
            with st.form("profile_form"):
                c1, c2 = st.columns(2)
                phone = c1.text_input("Telefono", value=profile[0] or "")
                email = c2.text_input("Email", value=profile[1] or "")
                tax_code = c1.text_input("Codice fiscale", value=profile[2] or "")
                iban = c2.text_input("IBAN", value=profile[3] or "")
                address = st.text_input("Indirizzo", value=profile[4] or "")
                contract_type = c1.selectbox(
                    "Tipo contratto",
                    ["", "Tempo indeterminato", "Tempo determinato", "Apprendistato", "A chiamata", "Collaborazione", "Altro"],
                    index=0 if not profile[5] else (
                        ["", "Tempo indeterminato", "Tempo determinato", "Apprendistato", "A chiamata", "Collaborazione", "Altro"].index(profile[5])
                        if profile[5] in ["", "Tempo indeterminato", "Tempo determinato", "Apprendistato", "A chiamata", "Collaborazione", "Altro"] else 0
                    )
                )
                contract_end = c2.text_input("Scadenza contratto (AAAA-MM-GG)", value=profile[6] or "")
                weekly_hours = c1.number_input("Ore settimanali contrattuali", min_value=0.0, value=float(profile[7] or 0), step=1.0)
                emergency_contact = c2.text_input("Contatto di emergenza", value=profile[8] or "")
                notes = st.text_area("Note anagrafiche", value=profile[9] or "")
                save = st.form_submit_button("Salva scheda", type="primary")

            if save:
                conn = get_conn()
                conn.execute(
                    """
                    INSERT INTO employee_profiles(
                        employee_id, phone, email, tax_code, iban, address,
                        contract_type, contract_end, weekly_hours,
                        emergency_contact, notes
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(employee_id) DO UPDATE SET
                        phone=excluded.phone, email=excluded.email,
                        tax_code=excluded.tax_code, iban=excluded.iban,
                        address=excluded.address, contract_type=excluded.contract_type,
                        contract_end=excluded.contract_end,
                        weekly_hours=excluded.weekly_hours,
                        emergency_contact=excluded.emergency_contact,
                        notes=excluded.notes
                    """,
                    (
                        emp_id, phone, email, tax_code, iban, address,
                        contract_type, contract_end, weekly_hours,
                        emergency_contact, notes
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Scheda dipendente aggiornata.")

        with tabs[1]:
            conn = get_conn()
            costs = pd.read_sql_query(
                """
                SELECT year Anno, month Mese, hours Ore, net_pay Netto,
                       gross_pay Lordo, company_cost "Costo azienda"
                FROM monthly_costs
                WHERE employee_id=?
                ORDER BY year DESC, month DESC
                """,
                conn,
                params=(emp_id,),
            )
            fringe = pd.read_sql_query(
                """
                SELECT benefit_date Data, amount Importo, category Categoria, note Nota
                FROM fringe_benefits WHERE employee_id=?
                ORDER BY benefit_date DESC
                """,
                conn,
                params=(emp_id,),
            )
            extra = pd.read_sql_query(
                """
                SELECT payment_date Data, amount Importo, reason Motivo,
                       payment_method Modalità, regularized Regolarizzato
                FROM extra_payments WHERE employee_id=?
                ORDER BY payment_date DESC
                """,
                conn,
                params=(emp_id,),
            )
            conn.close()

            if costs.empty:
                st.info("Nessun costo mensile importato.")
            else:
                costs["Mese"] = costs["Mese"].map(MONTHS)
                st.dataframe(costs, use_container_width=True, hide_index=True)
                chart = costs.copy()
                chart["Periodo"] = chart["Anno"].astype(str) + "-" + chart["Mese"]
                st.line_chart(chart.set_index("Periodo")[["Costo azienda"]])

            st.markdown("#### Fringe benefit")
            st.dataframe(fringe, use_container_width=True, hide_index=True)
            st.markdown("#### Importi extra registrati")
            st.dataframe(extra, use_container_width=True, hide_index=True)

        with tabs[2]:
            with st.form("event_form"):
                e1, e2 = st.columns(2)
                event_date = e1.date_input("Data evento")
                event_type = e2.selectbox(
                    "Tipo evento",
                    ["Assunzione", "Rinnovo", "Cambio livello", "Premio", "Formazione",
                     "Ferie", "Permesso", "Malattia", "Richiamo", "Nota", "Altro"]
                )
                title = st.text_input("Titolo")
                details = st.text_area("Dettagli")
                amount = st.number_input("Importo collegato", min_value=0.0, step=10.0)
                add_event = st.form_submit_button("Aggiungi alla timeline", type="primary")
            if add_event and title.strip():
                conn = get_conn()
                conn.execute(
                    """
                    INSERT INTO employee_events(employee_id, event_date, event_type, title, details, amount)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (emp_id, event_date.isoformat(), event_type, title.strip(), details, amount),
                )
                conn.commit()
                conn.close()
                st.success("Evento aggiunto.")

            conn = get_conn()
            events = pd.read_sql_query(
                """
                SELECT event_date Data, event_type Tipo, title Titolo, details Dettagli, amount Importo
                FROM employee_events WHERE employee_id=?
                ORDER BY event_date DESC, id DESC
                """,
                conn,
                params=(emp_id,),
            )
            conn.close()
            st.dataframe(events, use_container_width=True, hide_index=True)

        with tabs[3]:
            with st.form("doc_form"):
                d1, d2 = st.columns(2)
                doc_type = d1.selectbox(
                    "Tipo documento",
                    ["Contratto", "Documento identità", "Codice fiscale", "HACCP",
                     "Visita medica", "Sicurezza", "Permesso di soggiorno", "Altro"]
                )
                file_name = d2.text_input("Nome file o riferimento")
                issue_date = d1.text_input("Data rilascio (AAAA-MM-GG)")
                expiry_date = d2.text_input("Scadenza (AAAA-MM-GG)")
                status = d1.selectbox("Stato", ["Valido", "In scadenza", "Scaduto", "Da acquisire"])
                note = st.text_input("Nota documento")
                add_doc = st.form_submit_button("Registra documento", type="primary")
            if add_doc:
                conn = get_conn()
                conn.execute(
                    """
                    INSERT INTO employee_documents(
                        employee_id, document_type, file_name, issue_date,
                        expiry_date, status, note
                    )
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (emp_id, doc_type, file_name, issue_date, expiry_date, status, note),
                )
                conn.commit()
                conn.close()
                st.success("Documento registrato.")

            conn = get_conn()
            docs = pd.read_sql_query(
                """
                SELECT document_type Documento, file_name File, issue_date Rilascio,
                       expiry_date Scadenza, status Stato, note Nota
                FROM employee_documents WHERE employee_id=?
                ORDER BY expiry_date
                """,
                conn,
                params=(emp_id,),
            )
            conn.close()
            st.dataframe(docs, use_container_width=True, hide_index=True)

        with tabs[4]:
            with st.form("rating_form"):
                rating_date = st.date_input("Data valutazione")
                r1, r2, r3 = st.columns(3)
                punctuality = r1.slider("Puntualità", 1, 5, 3)
                professionalism = r2.slider("Professionalità", 1, 5, 3)
                sales = r3.slider("Capacità di vendita", 1, 5, 3)
                flexibility = r1.slider("Flessibilità", 1, 5, 3)
                teamwork = r2.slider("Lavoro di squadra", 1, 5, 3)
                leadership = r3.slider("Leadership", 1, 5, 3)
                note = st.text_area("Nota valutazione")
                add_rating = st.form_submit_button("Salva valutazione", type="primary")
            if add_rating:
                conn = get_conn()
                conn.execute(
                    """
                    INSERT INTO employee_ratings(
                        employee_id, rating_date, punctuality, professionalism,
                        sales, flexibility, teamwork, leadership, note
                    )
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (emp_id, rating_date.isoformat(), punctuality, professionalism,
                     sales, flexibility, teamwork, leadership, note),
                )
                conn.commit()
                conn.close()
                st.success("Valutazione registrata.")

            conn = get_conn()
            ratings = pd.read_sql_query(
                """
                SELECT rating_date Data, punctuality Puntualità,
                       professionalism Professionalità, sales Vendita,
                       flexibility Flessibilità, teamwork Squadra,
                       leadership Leadership, note Nota
                FROM employee_ratings WHERE employee_id=?
                ORDER BY rating_date DESC
                """,
                conn,
                params=(emp_id,),
            )
            conn.close()
            if not ratings.empty:
                ratings["Media"] = ratings[
                    ["Puntualità", "Professionalità", "Vendita", "Flessibilità", "Squadra", "Leadership"]
                ].mean(axis=1).round(2)
            st.dataframe(ratings, use_container_width=True, hide_index=True)

        with tabs[5]:
            st.write("Le note generali si modificano nella sezione **Dati e contratto**.")
            conn = get_conn()
            profile_notes = conn.execute(
                "SELECT notes FROM employee_profiles WHERE employee_id=?",
                (emp_id,),
            ).fetchone()
            conn.close()
            st.text_area("Note attuali", value=(profile_notes[0] if profile_notes else ""), height=220, disabled=True)

# -------------------- FRINGE --------------------

elif section == "Fringe benefit":
    st.title("Fringe benefit")
    conn = get_conn()
    employees = pd.read_sql_query("SELECT id, name FROM employees WHERE active=1 ORDER BY name", conn)
    conn.close()
    if employees.empty:
        st.info("Nessun dipendente presente.")
    else:
        with st.form("fringe_form"):
            name = st.selectbox("Dipendente", employees["name"])
            d = st.date_input("Data", value=date(selected_year, selected_month, 1))
            amount = st.number_input("Importo", min_value=0.0, step=10.0)
            category = st.selectbox("Categoria", ["Buoni", "Alloggio", "Auto", "Telefono", "Pasto", "Altro"])
            note = st.text_input("Nota")
            submit = st.form_submit_button("Registra fringe benefit", type="primary")
        if submit:
            emp_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
            conn = get_conn()
            conn.execute(
                "INSERT INTO fringe_benefits(employee_id, benefit_date, amount, category, note) VALUES(?,?,?,?,?)",
                (emp_id, d.isoformat(), amount, category, note),
            )
            conn.commit()
            conn.close()
            st.success("Fringe benefit registrato.")

# -------------------- EXTRA --------------------

elif section == "Extra da regolarizzare":
    st.title("Pagamenti extra da regolarizzare")
    st.warning(
        "Questa sezione serve a registrare importi extra per il controllo interno. "
        "Gli importi devono essere comunicati al consulente e regolarizzati secondo la normativa; "
        "il software non è progettato per occultare pagamenti."
    )
    conn = get_conn()
    employees = pd.read_sql_query("SELECT id, name FROM employees WHERE active=1 ORDER BY name", conn)
    conn.close()
    if employees.empty:
        st.info("Nessun dipendente presente.")
    else:
        with st.form("extra_form"):
            name = st.selectbox("Dipendente", employees["name"])
            d = st.date_input("Data pagamento", value=date(selected_year, selected_month, 1))
            amount = st.number_input("Importo extra", min_value=0.0, step=10.0)
            reason = st.text_input("Motivo obbligatorio")
            method = st.selectbox("Modalità", ["Da regolarizzare", "Bonifico", "Contanti registrati", "Altro"])
            note = st.text_area("Nota")
            submit = st.form_submit_button("Registra importo", type="primary")
        if submit:
            if not reason.strip():
                st.error("Inserisci il motivo.")
            else:
                emp_id = int(employees.loc[employees["name"] == name, "id"].iloc[0])
                conn = get_conn()
                conn.execute(
                    """
                    INSERT INTO extra_payments(employee_id, payment_date, amount, reason, payment_method, note)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (emp_id, d.isoformat(), amount, reason.strip(), method, note),
                )
                conn.commit()
                conn.close()
                st.success("Importo registrato come voce da regolarizzare.")

        conn = get_conn()
        extras = pd.read_sql_query(
            """
            SELECT x.id, e.name Dipendente, x.payment_date Data, x.amount Importo,
                   x.reason Motivo, x.payment_method Modalità, x.regularized Regolarizzato
            FROM extra_payments x JOIN employees e ON e.id=x.employee_id
            ORDER BY x.payment_date DESC
            """,
            conn,
        )
        conn.close()
        if not extras.empty:
            extras["Importo"] = extras["Importo"].map(euro)
            st.dataframe(extras.drop(columns=["id"]), use_container_width=True, hide_index=True)

# -------------------- SETTINGS --------------------

elif section == "Impostazioni mese":
    st.title("Dati economici del mese")
    conn = get_conn()
    row = conn.execute(
        "SELECT revenue, covers FROM monthly_revenue WHERE year=? AND month=?",
        (selected_year, selected_month),
    ).fetchone()
    conn.close()
    revenue = float(row[0]) if row else 0.0
    covers = int(row[1]) if row else 0

    with st.form("month_form"):
        new_revenue = st.number_input("Fatturato del mese", min_value=0.0, value=revenue, step=1000.0)
        new_covers = st.number_input("Coperti del mese", min_value=0, value=covers, step=10)
        submit = st.form_submit_button("Salva dati mese", type="primary")
    if submit:
        conn = get_conn()
        conn.execute(
            """
            INSERT INTO monthly_revenue(year, month, revenue, covers)
            VALUES(?,?,?,?)
            ON CONFLICT(year, month) DO UPDATE SET
                revenue=excluded.revenue, covers=excluded.covers
            """,
            (selected_year, selected_month, new_revenue, new_covers),
        )
        conn.commit()
        conn.close()
        st.success("Dati economici aggiornati.")
