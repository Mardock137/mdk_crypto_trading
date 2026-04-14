# Guida al Deploy su Google Compute Engine

MDK Crypto Trading gira in loop continuo 24/7. La soluzione scelta è una VM Google Compute Engine con Docker Compose.

---

## 📋 Indice

- [Prerequisiti](#prerequisiti)
- [1. Creazione della VM](#1-creazione-della-vm)
- [2. Accesso SSH alla VM](#2-accesso-ssh-alla-vm)
- [3. Installazione Docker sulla VM](#3-installazione-docker-sulla-vm)
- [4. Primo Deploy](#4-primo-deploy)
- [5. Aggiornamento (nuova versione del codice)](#5-aggiornamento-nuova-versione-del-codice)
- [6. Comandi utili](#6-comandi-utili)
- [7. 🔍 Troubleshooting](#7--troubleshooting)
- [📚 Riferimenti](#-riferimenti)

---

## Prerequisiti

- Account Google Cloud Platform con billing attivato
- `gcloud` CLI installato sul PC locale ([scarica qui](https://cloud.google.com/sdk/docs/install)) — dopo l'installazione, lanciare `gcloud init` per autenticarsi e selezionare il progetto
- Repo GitHub aggiornata con tutti i file di produzione
- Chiavi API pronte: Binance, OpenAI, Gemini, Anthropic

---

## 1. Creazione della VM

### Opzione A — Google Cloud Console (interfaccia web)

1. Vai su [console.cloud.google.com](https://console.cloud.google.com)
2. Menu → **Compute Engine** → **Istanze VM** → **Crea istanza**
3. Configura:
   - Nome: `mdk-crypto-trading`
   - Regione: `europe-west1`, Zona: `europe-west1-b`
   - Tipo di macchina: serie **E2**, poi **e2-micro** (0.25 vCPU, 1 GB RAM)
   - Disco di avvio: clicca **Cambia** → Ubuntu 24.04 LTS, 10 GB, disco permanente standard
4. Clicca **Crea**

### Opzione B — `gcloud` CLI (da terminale locale)

```bash
gcloud compute instances create mdk-crypto-trading \
  --zone=europe-west1-b \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=10GB \
  --boot-disk-type=pd-standard
```

> **Nota regione**: la VM deve essere in Europa (`europe-west1`). Binance blocca le connessioni dagli Stati Uniti, quindi regioni come `us-central1` non funzionano.
> **Nota firewall**: il bot fa solo chiamate in uscita verso Binance e le API AI. Non serve aprire nessuna porta in entrata.

---

## 2. Accesso SSH alla VM

### Da `gcloud` CLI (raccomandato — più stabile)

```bash
gcloud compute ssh mdk-crypto-trading --zone=europe-west1-b
```

La prima volta gcloud genera automaticamente le chiavi SSH. Se chiede una passphrase, premere Invio per lasciarla vuota.

### Da Google Cloud Console (alternativa via browser)

1. Menu → **Compute Engine** → **Istanze VM**
2. Clicca su **SSH** accanto alla VM `mdk-crypto-trading`
3. Si apre un terminale browser direttamente sulla VM

> **Nota**: la sessione SSH via browser può essere instabile. Se crasha frequentemente, usare `gcloud` CLI dal terminale locale.

---

## 3. Installazione Docker sulla VM

Una volta dentro la VM via SSH, esegui questi comandi in sequenza:

```bash
# Aggiorna i pacchetti
sudo apt update && sudo apt upgrade -y

# Installa le dipendenze necessarie
sudo apt install -y ca-certificates curl gnupg lsb-release

# Aggiungi la chiave GPG ufficiale di Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Aggiungi il repository Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installa Docker Engine e Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Aggiungi l'utente corrente al gruppo docker (evita di usare sudo ogni volta)
sudo usermod -aG docker $USER

# Ricarica la sessione per applicare il gruppo
newgrp docker
```

Verifica che Docker funzioni:

```bash
docker --version
docker compose version
```

---

## 4. Primo Deploy

### 4a. Clona la repo dalla VM

**Opzione raccomandata — HTTPS con token GitHub:**

1. Vai su GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Genera un token con permesso `repo`
3. Clona con:

```bash
git clone https://<tuo-token>@github.com/<tuo-utente>/mdk_crypto_trading.git
cd mdk_crypto_trading
```

### 4b. Crea il file `.env` sulla VM

Il file `.env` non viene mai committato su GitHub — va creato manualmente sulla VM:

```bash
nano .env
```

Incolla il contenuto del tuo `.env` locale (le chiavi API, la configurazione, ecc.), poi salva con `Ctrl+O`, `Invio`, `Ctrl+X`.

Consulta [.env.example](../.env.example) per la lista completa delle variabili richieste.

### 4c. Avvia il container

```bash
docker compose up -d
```

Docker scaricherà Python, installerà le dipendenze e avvierà il bot in background.

Controlla che stia girando:

```bash
docker compose ps
```

Leggi i log in tempo reale:

```bash
docker compose logs -f
```

---

## 5. Aggiornamento (nuova versione del codice)

Quando c'è una nuova versione del codice su GitHub:

```bash
cd mdk_crypto_trading

# Scarica le ultime modifiche
git pull

# Ricostruisci l'immagine e riavvia il container
docker compose up -d --build
```

Il bot si ferma per pochi secondi durante il rebuild, poi riparte automaticamente.

---

## 6. Comandi utili

### Stato del container

```bash
docker compose ps
```

### Log in tempo reale

```bash
docker compose logs -f
```

### Log degli ultimi 100 eventi

```bash
docker compose logs --tail=100
```

### Fermare il bot

```bash
docker compose down
```

### Riavviare il bot (senza rebuild)

```bash
docker compose restart
```

### Controllare le risorse della VM

```bash
# CPU e RAM
htop

# Spazio disco
df -h
```

---

## 7. 🔍 Troubleshooting

### Il container si avvia e si chiude subito

Controlla i log per vedere l'errore:

```bash
docker compose logs
```

Cause comuni:

- **Variabile mancante nel `.env`**: controlla che tutte le chiavi siano presenti
- **Errore di sintassi nel `.env`**: nessun spazio intorno a `=`, nessuna virgolette se non necessarie

### Errore "permission denied" con Docker

Hai bisogno di riaprire la sessione SSH dopo aver aggiunto l'utente al gruppo `docker`:

```bash
exit
# riaccedi via SSH
```

### Errore Binance "Service unavailable from a restricted location"

La VM si trova in una regione bloccata da Binance (es. Stati Uniti). Bisogna ricreare la VM in una regione europea come `europe-west1` (Belgio). Vedi sezione 1.

### Il bot non si connette a Binance o alle API AI

- Verifica che le chiavi API siano corrette nel `.env` sulla VM
- Controlla che la VM abbia accesso a internet (test: `curl https://api.binance.com/api/v3/ping`)
- Verifica che le chiavi Binance abbiano i permessi corretti (lettura + trading)

### Il progetto non si trova nella home dell'utente SSH

Se il progetto è stato clonato da un utente diverso da quello con cui si accede via SSH, la cartella non sarà visibile nella propria home. Per trovare il progetto e operarci:

```bash
# Cerca la cartella del progetto
sudo find /home -name "mdk_crypto_trading" -type d

# Se il progetto è sotto un altro utente (es. chief), entra con quell'utente
sudo su - chief
cd mdk_crypto_trading
```

Da qui si possono eseguire `git pull`, `docker compose up -d --build`, ecc. Per uscire e tornare al proprio utente:

```bash
exit
```

### Spazio disco esaurito

I log possono crescere nel tempo. Controlla con:

```bash
df -h
du -sh mdk_crypto_trading/logs/
```

Se necessario, svuota i log vecchi:

```bash
find mdk_crypto_trading/logs/events/ -name "*.jsonl" -mtime +30 -delete
```

### Errore "Permission denied" quando si cancellano log o memory

I file in `logs/` e `data/memory/` vengono creati dal container Docker, che gira come `root`. L'utente SSH normale non ha i permessi per cancellarli con `rm` diretto. Usare `sudo`:

```bash
sudo rm -rf logs/events/
sudo rm -f logs/mdk_crypto_trading.log*
sudo rm -rf data/memory/
```

---

### La VM si riavvia e il bot non parte

Con `restart: unless-stopped` in `docker-compose.yaml`, Docker riavvia il container automaticamente al reboot della VM. Se non succede, avvia Docker manualmente:

```bash
sudo systemctl enable docker
sudo systemctl start docker
cd mdk_crypto_trading
docker compose up -d
```

---

## 📚 Riferimenti

- **Codice**: `Dockerfile`, `docker-compose.yaml`
- **Doc correlati**: `docs/config.md`
- **Risorse esterne**:
  - [Google Compute Engine](https://cloud.google.com/compute/docs)
  - [Docker Compose](https://docs.docker.com/compose/)
  - [gcloud CLI](https://cloud.google.com/sdk/docs/install)
