# Strategia branch

## main
Contiene esclusivamente la versione stabile usata in produzione.

## develop
Contiene le modifiche in fase di prova.

## Procedura consigliata
1. Creare il branch `develop` da `main`.
2. Applicare e testare le modifiche su `develop`.
3. Aprire una Pull Request verso `main`.
4. Verificare che GitHub Actions completi compilazione e test.
5. Fare merge solo dopo il collaudo manuale.
