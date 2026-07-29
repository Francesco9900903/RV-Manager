# Enterprise 4.3 – Correzione CCNL Turismo

La schermata del simulatore ora distingue correttamente:

- **CCNL:** Turismo Confcommercio
- **Settore:** Albergo oppure Alberghi minori
- **Livello:** selezionato dalla tabella del settore
- **Tipo di contratto**

Il campo precedente **Comparto** non viene più mostrato.

## Installazione

Caricare i file della versione 4.3 sovrascrivendo quelli della 4.2.

Non è necessario eseguire una nuova migrazione SQL:
la tabella `payroll_simulations` creata con la 4.2 resta compatibile.

La cartella `.github` non è inclusa.
