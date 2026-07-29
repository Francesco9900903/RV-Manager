# Piano backup e ripristino

## Backup applicazione
- Creare una release GitHub della versione stabile.
- Conservare una copia ZIP del repository.
- Annotare il commit utilizzato da Streamlit Cloud.

## Backup database
- Usare il pulsante "Prepara backup JSON" nell'area Sicurezza.
- Conservare il file in uno spazio cifrato.
- Programmare anche backup nativi di Supabase.

## Backup Storage
I PDF di buste paga e documenti non sono inclusi nel JSON.
Esportare separatamente:
- bucket `payslips`;
- bucket `employee-documents`.

## Secrets
Non inserire mai chiavi nel repository.
Conservare:
- URL Supabase;
- chiave pubblica;
- chiave server/service role;
esclusivamente nei Secrets di Streamlit e in un password manager.

## Ripristino
1. Ripristinare database e Storage.
2. Ripristinare il repository GitHub.
3. Reinserire i Secrets.
4. Eseguire la checklist completa.
