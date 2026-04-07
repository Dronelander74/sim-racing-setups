\# PMR Library (Base44-ready)



Questa cartella contiene la libreria setup di Project Motor Racing (PMR) pronta per l'import in Base44.



\## Contenuti

\- `base44\_setups\_catalog.jsonl`  

&#x20; Catalogo in formato JSONL: 1 riga = 1 setup, con `params` e `groups` già estratti.

\- `base44\_param\_rules\_seed.json`  

&#x20; Seed delle regole parametriche: per ogni parametro `min/max/count` (base per clamp e validazione).

\- `\_manifest\_from\_baseline.json`  

&#x20; Manifest di generazione con origine, conteggi e metadati.

\- `PMR\_ALL\_SETUPS\_FROM\_BASELINE.txt`  

&#x20; Listone con marker + XML normalizzato (backup/debug e reprocessing).



\## Stato dataset

\- Setup scritti: \*\*367\*\*

\- Parametri unici: \*\*232\*\*

(Fonti: `\_manifest\_from\_baseline.json`)



\## Uso in Base44

1\) Importa `base44\_setups\_catalog.jsonl` in una entity tipo `setups\_catalog`

2\) Importa `base44\_param\_rules\_seed.json` in una entity tipo `param\_rules`

3\) Generazione setup:

&#x20;  - seleziona baseline per `car + track` (fallback `\_Generic`)

&#x20;  - modifica solo gruppi “safe” (es. tyres/alignment/suspension/aero/diff/brakes/electronics/gearbox)

&#x20;  - clamp su min/max usando `param\_rules`



\## Note

\- I parametri di telemetria (`game-\*`) e FFB (`ffb-\*`) sono presenti nei dati, ma in genere non vanno modificati automaticamente.

