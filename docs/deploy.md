# Guida al Deploy su Google Compute Engine

MDK Crypto Trading gira in loop continuo 24/7. La soluzione scelta è una VM Google Compute Engine con Docker Compose.

---

## Prerequisiti

- Account Google Cloud Platform con billing attivato
- `gcloud` CLI installato sul PC locale ([scarica qui](https://cloud.google.com/sdk/docs/install))
- Repo GitHub aggiornata con tutti i file di produzione
- Chiavi API pronte: Binance, OpenAI, Gemini, Anthropic

---

## 1. Creazione della VM

### Opzione A — Google Cloud Console (interfaccia web)

1. Vai su [console.cloud.google.com](https://console.cloud.google.com)
2. Menu → **Compute Engine** → **Istanze VM** → **Crea istanza**
3. Configura:
   - Nome: `mdk-crypto-trading`
   - Regione: `us-central1`, Zona: `us-central1-a` (free tier)
   - Tipo di macchina: `e2-micro` (0.25 vCPU, 1 GB RAM — free tier)
   - Sistema operativo: Ubuntu 24.04 LTS
   - Disco: 10 GB standard (free tier)
4. Clicca **Crea**

### Opzione B — `gcloud` CLI (da terminale locale)

```bash
gcloud compute instances create mdk-crypto-trading \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=10GB \
  --boot-disk-type=pd-standard
```

> **Nota firewall**: il bot fa solo chiamate in uscita verso Binance e le API AI. Non serve aprire nessuna porta in entrata.

---

## 2. Accesso SSH alla VM

### Da Google Cloud Console

1. Menu → **Compute Engine** → **Istanze VM**
2. Clicca su **SSH** accanto alla VM `mdk-crypto-trading`
3. Si apre un terminale browser direttamente sulla VM

### Da `gcloud` CLI

```bash
gcloud compute ssh mdk-crypto-trading --zone=us-central1-a
```

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

## 7. Troubleshooting

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

### Il bot non si connette a Binance o alle API AI

- Verifica che le chiavi API siano corrette nel `.env` sulla VM
- Controlla che la VM abbia accesso a internet (test: `curl https://api.binance.com/api/v3/ping`)
- Verifica che le chiavi Binance abbiano i permessi corretti (lettura + trading)

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

### La VM si riavvia e il bot non parte

Con `restart: unless-stopped` in `docker-compose.yaml`, Docker riavvia il container automaticamente al reboot della VM. Se non succede, avvia Docker manualmente:

```bash
sudo systemctl enable docker
sudo systemctl start docker
cd mdk_crypto_trading
docker compose up -d
```
