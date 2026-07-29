# Piano di rifattorizzazione progressiva

La UI resta temporaneamente in `legacy_app.py`.
Le funzioni vengono spostate una alla volta, senza cambiare il comportamento.

Ordine:
1. funzioni pure del portale dipendente;
2. autenticazione e account;
3. timbrature e timesheet;
4. documenti e buste paga;
5. dashboard e business intelligence;
6. notifiche e audit;
7. eliminazione finale di `legacy_app.py`.

Ogni estrazione deve:
- avere test automatici;
- mantenere gli stessi input/output;
- essere collaudata su `develop`;
- essere portata in `main` solo dopo verifica.
