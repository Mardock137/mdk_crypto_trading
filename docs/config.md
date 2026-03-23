# ⚙️ Configurazione (`config/`)

## Obiettivo

La cartella `config/` contiene le configurazioni statiche del sistema.
Qui vivono regole operative, prompt runtime e configurazioni dei modelli, separate dai segreti presenti nel file `.env`.

## Struttura iniziale

- `config/trading.yaml`: regole operative statiche del sistema, come `min_order_usdc`
- `config/prompts/`: prompt runtime caricati dal codice
- `config/llm_models/`: configurazioni dei modelli LLM usati dagli agenti

## Distinzione tra `config/` e `.env`

- `.env`: chiavi API, modalita' di esecuzione, URL e variabili riservate
- `config/`: regole e configurazioni applicative che descrivono il comportamento del sistema
