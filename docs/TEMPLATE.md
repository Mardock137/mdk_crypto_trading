<!-- markdownlint-disable -->
# Template documentazione

> **Questo file è un template, non un documento operativo.**
> Per creare un nuovo doc: copia tutto il contenuto dalla riga `---` in giù, sostituisci i placeholder e rimuovi le sezioni non pertinenti al documento.

## Regole

- Il titolo principale (`#`) non ha mai emoji.
- Le sezioni (`##`) usano sempre l'emoji corrispondente dalla tabella qui sotto.
- Non tutte le sezioni sono obbligatorie: usa solo quelle che hanno senso per il documento.
- Le sezioni obbligatorie per tutti i documenti sono: 📋 Indice, 📄 Panoramica, 📚 Riferimenti.

## Emoji per sezione

| Sezione              | Emoji |
|----------------------|-------|
| Indice               | 📋    |
| Panoramica           | 📄    |
| Come funziona        | ⚙️    |
| Configurazione       | 🔧    |
| Testing              | 🧪    |
| Troubleshooting      | 🔍    |
| Riferimenti          | 📚    |
| Sicurezza            | 🔒    |
| Avvio rapido / Setup | 🚀    |
| Manutenzione         | 🔄    |
| Funzionalità         | ⭐    |
| Note / Avvertenze    | ⚠️    |
| Best practices       | ✅    |

> Questa lista può essere espansa con nuove sezioni ed emoji.

---

# Titolo del documento

Breve descrizione di cosa tratta questo documento e perché esiste.

---

## 📋 Indice

- [📄 Panoramica](#-panoramica)
- [⚙️ Come funziona](#️-come-funziona)
- [🔧 Configurazione](#-configurazione)
- [🧪 Testing](#-testing)
- [🔍 Troubleshooting](#-troubleshooting)
- [📚 Riferimenti](#-riferimenti)

---

## 📄 Panoramica

Spiegazione chiara del sistema/funzionalità. Cosa fa, perché esiste, come si inserisce nel progetto.

Se utile, includere un elenco dei punti chiave:

- Punto 1
- Punto 2
- Punto 3

---

## ⚙️ Come funziona

Dettagli tecnici: architettura, flusso, componenti coinvolti.

Se utile, includere diagrammi (Mermaid, ASCII) o tabelle.

```text
[Richiesta] → [Componente A] → [Componente B] → [Risultato]
```

### Sottosezione (se necessaria)

Per argomenti complessi, spezzare in sottosezioni logiche.

---

## 🔧 Configurazione

Variabili d'ambiente, file di config, setup necessario.

```env
VARIABILE_ESEMPIO=valore
```

---

## 🧪 Testing

Come testare questa funzionalità (test automatici e/o manuali).

```bash
pytest tests/path/to/test_file.py -v
```

---

## 🔍 Troubleshooting

### Problema: Descrizione breve del problema

**Causa**: Spiegazione.

**Soluzione**: Passi per risolvere.

---

## 📚 Riferimenti

- **Codice**: `src/path/to/file.py`
- **Test**: `tests/path/to/test_file.py`
- **Doc correlati**: `docs/altro_documento.md`
- **Risorse esterne**: [Nome](https://url)
