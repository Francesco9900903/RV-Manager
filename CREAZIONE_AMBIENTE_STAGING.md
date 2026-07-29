# Creazione ambiente staging

1. Creare un secondo progetto Supabase dedicato allo staging.
2. Non copiare buste paga o documenti reali.
3. Applicare tutte le migrazioni SQL nello stesso ordine della produzione.
4. Creare account di prova per:
   - manager;
   - dipendente A;
   - dipendente B.
5. Creare una seconda app Streamlit collegata al branch `develop`.
6. Nei Secrets della seconda app usare il modello
   `templates/secrets.staging.example.toml`.
7. Verificare che nel menu compaia il banner STAGING.
8. Eseguire i test RLS tra dipendente A e B.
9. Portare le modifiche in produzione solo dopo il collaudo.

Produzione e staging devono avere:
- progetti Supabase differenti;
- chiavi differenti;
- Storage differente;
- dati differenti;
- app Streamlit differenti.
