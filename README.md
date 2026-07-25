
# La Cambusa – Gestionale Personale

Prima versione funzionante del modulo di gestione dipendenti.

## Funzioni già presenti

- importazione del PDF “Costo del personale” del consulente;
- riconoscimento automatico del mese e dei dipendenti;
- costo aziendale ufficiale per singolo dipendente;
- retribuzioni lorde, oneri sociali, TFR e INAIL;
- anagrafica e assegnazione reparto;
- registrazione dei fringe benefit;
- registrazione separata degli importi extra da regolarizzare;
- fatturato e coperti del mese;
- incidenza del personale sul fatturato;
- costo gestionale per dipendente e per reparto;
- costo medio per ora e per coperto.

## Avvio

1. Installare Python 3.11 o superiore.
2. Aprire il terminale nella cartella del programma.
3. Installare i pacchetti:

   pip install -r requirements.txt

4. Avviare:

   streamlit run app.py

Il database `personale.db` viene creato automaticamente.

## Nota sugli extra

La sezione “Extra da regolarizzare” è un registro gestionale interno. Gli importi inseriti devono essere comunicati al consulente del lavoro e regolarizzati. Il programma non contiene funzioni di occultamento o cancellazione selettiva dei pagamenti.


## Avvio su Mac

1. Estrarre il file ZIP.
2. Aprire la cartella `gestionale_personale_cambusa`.
3. Fare doppio clic su `AVVIA_GESTIONALE_MAC.command`.

Se macOS blocca il file:
- clic destro sul file;
- scegliere **Apri**;
- confermare nuovamente **Apri**.

In alternativa, da Terminale:

```bash
cd /percorso/della/cartella/gestionale_personale_cambusa
chmod +x AVVIA_GESTIONALE_MAC.command
./AVVIA_GESTIONALE_MAC.command
```


## Novità versione 2

È stata aggiunta la scheda dipendente definitiva con:
- dati anagrafici e contrattuali;
- storico costi e paghe;
- storico fringe ed extra;
- timeline completa;
- documenti e scadenze;
- valutazioni periodiche;
- note generali.
