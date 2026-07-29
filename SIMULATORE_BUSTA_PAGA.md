# Simulatore busta paga – Enterprise 4.2

Il menu contiene la nuova voce `Simulazione busta paga`.

La versione include le tabelle in vigore da maggio 2026 per:
- CCNL Turismo Confcommercio – aziende alberghiere;
- alberghi minori.

Il simulatore calcola indicativamente:
- lordo mensile;
- contributi del dipendente;
- IRPEF e addizionali stimate;
- netto mensile;
- contributi aziendali;
- INAIL stimata;
- ratei di tredicesima e quattordicesima;
- TFR;
- ferie e permessi;
- costo mensile e annuale dell'azienda.

Tutti i parametri percentuali sono modificabili nella schermata.

## Installazione

1. Caricare i file della versione 4.2.
2. Non è presente la cartella `.github`.
3. Eseguire in Supabase SQL Editor:
   `sql/MIGRAZIONE_ENTERPRISE_4_2_SIMULAZIONI_BUSTA_PAGA.sql`

La migrazione serve solo per il pulsante `Salva simulazione`.
Il calcolo e il download del preventivo funzionano anche senza archivio.

## Avvertenza

Il simulatore è uno strumento previsionale. Non sostituisce il cedolino,
il consulente del lavoro o la verifica del corretto inquadramento.
