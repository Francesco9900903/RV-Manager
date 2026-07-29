# RV Manager v3 - Supabase

1. Sostituisci `app.py` e `requirements.txt` nel repository GitHub.
2. In Streamlit: Manage app → Settings → Secrets.
3. Inserisci:

```toml
[supabase]
url = "https://TUO-PROGETTO.supabase.co"
secret_key = "LA-TUA-SECRET-KEY"
```

Non caricare mai la secret key su GitHub.


## Correzione parser PDF
- riconosce il formato del prospetto La Cambusa;
- gestisce dipendenti spezzati su più pagine;
- rileva automaticamente mese e anno dal PDF.


## Versione 3.2 – Ore e accesso dipendenti

1. Eseguire `MIGRAZIONE_ORE_ACCESSI.sql` nel SQL Editor di Supabase.
2. Aggiungere nei Secrets di Streamlit anche:

```toml
publishable_key = "sb_publishable_..."
```

all'interno della sezione `[supabase]`.

3. Aggiornare `app.py` su GitHub.
4. L'area dipendente è disponibile aggiungendo `?area=dipendente` all'URL dell'app.
5. Creare ogni utente in Supabase → Authentication → Users.
6. Associare il relativo User UID da **Account dipendenti** nel gestionale.

Le ore inserite dal dipendente restano `submitted`; il responsabile le approva.
Solo le ore approvate alimentano il costo medio orario del cruscotto.


## Versione 3.3 – Timbratura digitale

- pulsante Entrata;
- pulsante Uscita;
- pausa in minuti;
- calcolo automatico delle ore giornaliere;
- invio automatico al responsabile;
- storico personale;
- vista amministratore delle timbrature.

Prima di aggiornare `app.py`, eseguire `MIGRAZIONE_TIMBRATURE.sql` nel SQL Editor di Supabase.


## Versione 3.4 – Procedura semplificata

- Il responsabile inserisce solo entrata, uscita e pausa.
- Ore ordinarie e straordinarie vengono calcolate automaticamente.
- Gli account dipendenti si creano direttamente dal gestionale.
- Non serve più creare manualmente gli utenti in Supabase Authentication.
- Area dipendente: `https://rv-manager.streamlit.app/?area=dipendente`

Per il login dipendente deve essere presente nei Secrets:

```toml
[supabase]
url = "https://..."
secret_key = "sb_secret_..."
publishable_key = "sb_publishable_..."
```


## Versione 3.5 – Buste paga private

Funzioni:
- caricamento del PDF cumulativo;
- riconoscimento per nome, matricola o codice fiscale;
- divisione automatica delle pagine;
- archivio privato Supabase Storage;
- pubblicazione per mese e dipendente;
- area dipendente con visualizzazione e download della sola busta personale;
- elenco delle pagine non riconosciute.

Installazione:
1. Eseguire `MIGRAZIONE_BUSTE_PAGA.sql` nel SQL Editor di Supabase.
2. Caricare il nuovo `app.py` su GitHub.
3. Riavviare Streamlit.
4. Rigenerare le chiavi Supabase prima di caricare documenti reali.


## Versione 3.6 stabile
- corretto l'errore `IndentationError` dell'area dipendente;
- verificata la compilazione completa di `app.py`;
- mantenute ore, timbrature, accessi e buste paga private.


## Versione 3.7 – Cedolini reali
- parser adattato al PDF reale del commercialista;
- riconoscimento tramite codice dipendente, nome e codice fiscale;
- periodo letto direttamente da ogni pagina;
- una pagina = una busta paga nel formato attuale;
- testato sul PDF campione da 13 pagine.


## Versione 3.8 – Correzione pubblicazione
- corretto l'upload dei PDF su Supabase Storage;
- ora viene passato un file binario `BytesIO`, come richiesto dal client Python;
- mantenuto il riconoscimento 13/13 del PDF campione;
- nessuna nuova migrazione SQL richiesta.


## Versione 3.9 – Dashboard e notifiche
- Home personale del dipendente;
- riepilogo ore, straordinari e giorni registrati;
- calendario presenze mensile;
- accesso rapido all'ultima busta paga;
- notifiche interne alla pubblicazione di una nuova busta paga;
- nuovi indicatori nel cruscotto manager;
- ferie e permessi non inclusi, come richiesto.


## RV Manager Enterprise 1.0
- dashboard manager intelligente;
- centro operativo e attività automatiche;
- presenti, ore e costo del giorno;
- anomalie su uscite mancanti e straordinari;
- calendario presenze e analisi per reparto;
- nessuna nuova migrazione SQL richiesta.


## Enterprise 1.1 – Timbratura smart
- entrata con un solo pulsante;
- uscita con un solo pulsante;
- pausa inserita solo al termine del turno;
- calcolo automatico delle ore;
- invio automatico al responsabile;
- elenco del personale attualmente in servizio;
- interfaccia ottimizzata per smartphone;
- nessuna nuova migrazione SQL richiesta.


## Enterprise 1.3 – Centro documenti
- archivio privato per ciascun dipendente;
- contratti, CU, HACCP, formazione, visite mediche e altri file;
- documenti con data e scadenza facoltativa;
- notifica automatica al dipendente;
- accesso esclusivo ai propri documenti tramite RLS;
- collegamenti temporanei firmati per apertura sicura.


## Enterprise 1.3.1 – Fix documenti privati
- corretta la visualizzazione nell'area dipendente;
- lettura server-side sempre filtrata sul dipendente autenticato;
- URL firmati generati dal client server;
- policy RLS resa robusta con funzione security definer.


## Enterprise 1.3.2 – Fix upload documenti
- corretto il TypeError causato da BytesIO;
- invio diretto dei bytes a Supabase Storage;
- nessuna nuova migrazione SQL richiesta.


## Enterprise 1.4 – Alert e scadenze
- centro notifiche manager;
- alert automatici per documenti scaduti o in scadenza;
- alert per turni aperti da oltre 10 ore;
- indicatori priorità alta/media/bassa;
- gestione letto/non letto;
- scadenze visibili anche nel cruscotto.


## Enterprise 1.5 – Cruscotto direzionale
- costo personale giornaliero e mensile;
- ore, straordinari, incidenza e costo/coperto;
- andamento economico degli ultimi 12 mesi;
- analisi ore e costi per reparto;
- personale presente e turni aperti;
- alert operativi e scadenze integrate;
- calendario presenze e indicatori approvazione;
- nessuna nuova migrazione SQL richiesta.


## Enterprise 1.6 – Business Intelligence del personale
- confronto automatico con il mese precedente;
- andamento costi, ore, straordinari e incidenza su 12 mesi;
- costo e ore per reparto;
- analisi per singolo dipendente;
- costo medio per ora e costo per coperto;
- lettura automatica delle variazioni e delle anomalie;
- nessuna nuova migrazione SQL richiesta.


## Enterprise 2.0 – Fondazione modulare

Questa versione avvia la migrazione da un unico `app.py` a una struttura
modulare senza eliminare le funzionalità già collaudate.

Nuovi componenti:
- package `rv_manager/`;
- AI Manager locale, basato sui dati reali e senza invio a servizi esterni;
- Registro eventi aziendali;
- primo test automatico;
- cartella `sql/` per le migrazioni;
- `legacy_app.py` isolato per consentire una migrazione progressiva.

Installazione:
1. eseguire `sql/MIGRAZIONE_ENTERPRISE_2_0_EVENT_LOG.sql`;
2. caricare su GitHub tutti i file e la cartella `rv_manager`;
3. mantenere `app.py`, `legacy_app.py`, `requirements.txt`;
4. riavviare Streamlit.


## Enterprise 2.1 – Audit Engine

Il registro eventi viene ora alimentato automaticamente dalle operazioni
principali:

- timbratura entrata e uscita;
- inserimento, approvazione e rifiuto ore;
- importazione costi paghe;
- pubblicazione buste paga;
- pubblicazione e archiviazione documenti;
- creazione account dipendente;
- fringe benefit ed extra;
- aggiornamento dei dati mensili.

Installazione:
1. eseguire `sql/MIGRAZIONE_ENTERPRISE_2_1_AUDIT_ENGINE.sql`;
2. caricare `app.py`, `legacy_app.py` e i moduli aggiornati;
3. riavviare Streamlit;
4. eseguire una nuova operazione per verificare il Registro eventi.


## Enterprise 3.0 – Interfaccia professionale

Novità grafiche:
- menu laterale scuro con icone;
- identità visiva RV Manager;
- metriche trasformate in card;
- tabelle e grafici con contenitori professionali;
- pulsanti, tab, input e alert uniformati;
- migliore leggibilità e spaziatura;
- interfaccia responsive per tablet e smartphone;
- nessuna migrazione SQL richiesta.

Installazione:
- sostituire `app.py` e `legacy_app.py`;
- caricare `theme.py` facoltativamente per la struttura modulare;
- mantenere i moduli già presenti;
- fare Commit e riavviare Streamlit.


## Enterprise 3.1 – AI Manager Pro

Novità:
- indice di attenzione da 0 a 100;
- briefing operativo del giorno;
- elenco automatico delle priorità;
- integrazione di presenze, ore, documenti, notifiche e costi;
- domande guidate con risposte basate sui dati reali;
- valutazione automatica di incidenza e straordinari;
- analisi del reparto con il maggiore peso;
- nessun invio di dati a servizi AI esterni;
- nessuna nuova migrazione SQL richiesta.

Installazione:
- sostituire `app.py` e `legacy_app.py`;
- mantenere i moduli già presenti;
- fare Commit e riavviare Streamlit.


## Enterprise 3.2 – Mobile Experience

Novità:
- home dipendente ottimizzata per smartphone;
- card rapide con stato, ore e straordinari;
- tab con icone e testi più compatti;
- pulsanti a tutta larghezza sui dispositivi mobili;
- sidebar più comoda su schermi piccoli;
- guida integrata per aggiungere l'app alla schermata Home;
- migliore leggibilità di tabelle, metriche e moduli.

Nota:
questa versione rende RV Manager installabile come collegamento web
dalla schermata Home, ma non aggiunge ancora offline o notifiche push native.

Nessuna migrazione SQL richiesta.


## Enterprise 3.3 – Dashboard Pro

Novità:
- sidebar mobile fissata a 230px;
- KPI principali in card colorate;
- stato presenti, ore, approvazioni e scadenze subito visibili;
- dashboard più leggibile su desktop e smartphone;
- badge colorati per la priorità delle notifiche;
- sezione Centro operativo più professionale;
- nessuna migrazione SQL richiesta.

Installazione:
- sostituire `app.py` e `legacy_app.py`;
- fare Commit e riavviare Streamlit.


## Enterprise 3.4 – Sicurezza, backup e collaudo

Novità:
- pannello diagnostico di sicurezza;
- verifica Secrets, tabelle e bucket;
- esportazione backup JSON;
- checklist di collaudo completa;
- controllo account associati ai dipendenti;
- configurazione Streamlit più restrittiva;
- query SQL diagnostica per RLS e bucket;
- manuale di backup e ripristino;
- manifest SHA-256 dei file.

Installazione:
- sostituire `app.py` e `legacy_app.py`;
- caricare anche `.streamlit/config.toml`;
- il file SQL è diagnostico e facoltativo;
- fare Commit e riavviare Streamlit.


## Enterprise 3.5 – Consolidamento tecnico

Obiettivi:
- nessuna nuova funzione visibile;
- riduzione del rischio di regressioni;
- avvio controllato tramite `app.py`;
- prima estrazione dal file `legacy_app.py`;
- test automatici;
- GitHub Actions su `main` e `develop`;
- documentazione per release stabile e strategia branch.

File principali aggiunti:
- `rv_manager/employee_portal_utils.py`
- `rv_manager/diagnostics.py`
- `.github/workflows/quality.yml`
- `scripts/check_project.py`
- `docs/STRATEGIA_BRANCH.md`
- `docs/RELEASE_STABILE.md`
- `docs/PIANO_RIFATTORIZZAZIONE.md`

Nessuna migrazione SQL richiesta.


## Enterprise 3.6 – Audit RLS e ambiente staging

Aggiunge:
- banner ambiente produzione/staging;
- pannello diagnostico RLS;
- vista SQL diagnostica non distruttiva;
- modelli Secrets separati;
- guida alla creazione di un progetto Supabase staging;
- matrice di test tra utenti;
- procedura di rilascio develop → main.

Installazione:
1. eseguire `sql/MIGRAZIONE_ENTERPRISE_3_6_DIAGNOSTICA_RLS.sql`;
2. sostituire `app.py` e `legacy_app.py`;
3. caricare la cartella `rv_manager`;
4. aggiungere nei Secrets della produzione:

   [app]
   environment = "production"
   project_label = "RV Manager Produzione"
   allow_real_data = true

5. creare successivamente un'app e un progetto Supabase separati
   per lo staging.


## Enterprise 3.7 – Usabilità, lingua italiana e costi

Modifiche:
- pulsanti Accesso rapido attivi;
- date visualizzate nel formato GG/MM/AAAA;
- Registro eventi tradotto in italiano;
- stati, gravità ed entità tradotti nelle tabelle;
- pulsanti di salvataggio rossi con testo bianco;
- terminologia dell'interfaccia uniformata in italiano;
- extra rinominati «Altro costo»;
- gli altri costi del mese vengono sommati al costo aziendale importato
  del dipendente per calcolare il costo complessivo;
- riepilogo immediato dopo la registrazione di un altro costo.

Nessuna nuova migrazione SQL richiesta.


## Enterprise 3.8 – Stato del sistema

La precedente pagina tecnica «Ambiente e RLS» è stata trasformata in
una pagina più chiara e commerciale: «Stato del sistema».

Controlli disponibili:
- connessione al database;
- presenza delle tabelle fondamentali;
- protezione RLS e policy;
- disponibilità dei bucket documenti e buste paga;
- configurazione produzione/staging;
- presenza di un backup registrato;
- versione software installata.

È disponibile il pulsante:
`Esegui controllo completo del sistema`

La sezione tecnica RLS rimane accessibile in un pannello espandibile.

Nessuna nuova migrazione SQL richiesta rispetto alla versione 3.7.


## Enterprise 4.0 – Affidabilità

Aggiornamento dedicato alla qualità commerciale e alla stabilità.

Migliorie:
- corretto il controllo di connessione al database;
- eliminata l'assunzione della colonna `employee_accounts.id`;
- aggiunto controllo delle prestazioni del database;
- messaggi tecnici nascosti dalla vista principale;
- errori mostrati con spiegazioni comprensibili;
- dettagli SQL disponibili solo nel pannello amministratore;
- controllo backup descritto come configurazione da completare, non come errore;
- versione aggiornata a Enterprise 4.0.

Nessuna nuova migrazione SQL richiesta.


## Enterprise 4.1 – Backup integrato

Il Centro backup è integrato nella pagina `Stato del sistema`.

Funzioni:
- backup manuale immediato;
- archiviazione nel bucket privato `system-backups`;
- download del backup appena creato;
- storico dei backup;
- verifica integrità SHA-256;
- download dei backup storici;
- configurazione backup automatici;
- frequenza giornaliera, settimanale o mensile;
- conservazione configurabile;
- workflow GitHub Actions per l'esecuzione automatica.

Installazione obbligatoria:
1. eseguire `sql/MIGRAZIONE_ENTERPRISE_4_1_BACKUP.sql`;
2. caricare tutti i file della versione 4.1;
3. configurare i Secrets GitHub indicati in
   `docs/ATTIVAZIONE_BACKUP_AUTOMATICI.md`.

Il ripristino automatico non è stato attivato in questa versione:
un ripristino dati è un'operazione distruttiva e deve essere effettuato
solo dopo verifica e conferma amministrativa.


## Enterprise 4.2 – Simulatore busta paga

Nuova voce nel menu per stimare netto e costo aziendale secondo il
CCNL Turismo Confcommercio – aziende alberghiere, con parametri
modificabili, dettaglio dei calcoli, preventivo stampabile e
salvataggio su Supabase.

Questa distribuzione non contiene la cartella nascosta `.github`.
