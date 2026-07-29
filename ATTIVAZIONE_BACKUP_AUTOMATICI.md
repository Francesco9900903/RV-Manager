# Attivazione backup automatici

1. Eseguire in Supabase:
   `sql/MIGRAZIONE_ENTERPRISE_4_1_BACKUP.sql`

2. In GitHub aprire:
   Settings → Secrets and variables → Actions.

3. Creare due Repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_SECRET_KEY`

4. Aprire la scheda Actions del repository.

5. Se richiesto, abilitare i workflow.

6. Aprire `Backup automatico RV Manager` e premere
   `Run workflow` per il primo test.

7. Nell'app aprire:
   Stato del sistema → Backup automatici.

8. Attivare la funzione, scegliere frequenza, ora e conservazione.

Il workflow GitHub controlla ogni ora se un backup è dovuto.
Non viene creato un backup ogni ora: viene rispettata la frequenza
salvata nell'app.

Nota:
il backup JSON contiene le principali tabelle applicative.
I PDF nei bucket `payslips` ed `employee-documents` non vengono duplicati
dentro il JSON. Restano protetti nello Storage Supabase.
