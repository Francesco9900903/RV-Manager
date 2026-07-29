# Rilascio staging → produzione

1. Sviluppare sul branch `develop`.
2. Deploy automatico sull'app Streamlit di staging.
3. Eseguire test automatici.
4. Eseguire checklist manuale.
5. Eseguire matrice RLS.
6. Creare backup produzione.
7. Aprire Pull Request `develop` → `main`.
8. Fare merge.
9. Verificare deploy produzione.
10. Registrare la versione e il commit.
