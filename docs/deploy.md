<!-- markdownlint-disable -->
# Deployment Guide on Google Compute Engine

MDK Crypto Trading runs in a continuous 24/7 loop. The chosen solution is a Google Compute Engine VM with Docker Compose.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [1. Creating the VM](#1-creating-the-vm)
- [2. SSH access to the VM](#2-ssh-access-to-the-vm)
- [3. Installing Docker on the VM](#3-installing-docker-on-the-vm)
- [4. First deployment](#4-first-deployment)
- [5. Updating (new code version)](#5-updating-new-code-version)
- [6. Useful commands](#6-useful-commands)
- [7. 🔍 Troubleshooting](#7--troubleshooting)
- [📚 References](#-references)

---

## Prerequisites

- Google Cloud Platform account with billing enabled
- `gcloud` CLI installed on your local machine ([download here](https://cloud.google.com/sdk/docs/install)) — after installation, run `gcloud init` to authenticate and select the project
- GitHub repo up to date with all production files
- API keys ready: Binance, OpenAI, Gemini, Anthropic

---

## 1. Creating the VM

### Option A — Google Cloud Console (web interface)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Menu → **Compute Engine** → **VM Instances** → **Create Instance**
3. Configure:
   - Name: `mdk-crypto-trading`
   - Region: `europe-west1`, Zone: `europe-west1-b`
   - Machine type: **E2** series, then **e2-micro** (0.25 vCPU, 1 GB RAM)
   - Boot disk: click **Change** → Ubuntu 24.04 LTS, 10 GB, standard persistent disk
4. Click **Create**

### Option B — `gcloud` CLI (from local terminal)

```bash
gcloud compute instances create mdk-crypto-trading \
  --zone=europe-west1-b \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=10GB \
  --boot-disk-type=pd-standard
```

> **Region note**: the VM must be in Europe (`europe-west1`). Binance blocks connections from the United States, so regions like `us-central1` will not work.
> **Firewall note**: the bot only makes outbound calls to Binance and the AI APIs. No inbound port needs to be opened.

---

## 2. SSH access to the VM

### From the `gcloud` CLI (recommended — more stable)

```bash
gcloud compute ssh mdk-crypto-trading --zone=europe-west1-b
```

The first time, gcloud automatically generates the SSH keys. When it asks for a passphrase, **set one**: it protects the key in case the file is stolen. To avoid re-entering it on every connection, use `ssh-agent`:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/google_compute_engine
```

### From the Google Cloud Console (browser alternative)

1. Menu → **Compute Engine** → **VM Instances**
2. Click **SSH** next to the `mdk-crypto-trading` VM
3. A browser terminal opens directly on the VM

> **Note**: the browser-based SSH session can be unstable. If it crashes frequently, use the `gcloud` CLI from a local terminal instead.

---

## 3. Installing Docker on the VM

Once inside the VM via SSH, run these commands in sequence:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install required dependencies
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add the current user to the docker group (avoids using sudo every time)
sudo usermod -aG docker $USER

# Reload the session to apply the group change
newgrp docker
```

Verify that Docker works:

```bash
docker --version
docker compose version
```

---

## 4. First deployment

### 4a. Clone the repo onto the VM

**Recommended method — read-only SSH deploy key:**

A deploy key is an SSH key linked to a single repo. It has a restricted scope (that repo only), leaves no token in the shell history, and can be revoked instantly from the GitHub page.

1. **On the VM**, generate the key:

```bash
ssh-keygen -t ed25519 -C "mdk-crypto-trading-deploy" -f ~/.ssh/github_mdk_crypto
```

> When it asks for a passphrase, **set one**. To avoid re-entering it every time: `eval "$(ssh-agent -s)" && ssh-add ~/.ssh/github_mdk_crypto`.

2. Copy the public key:

```bash
cat ~/.ssh/github_mdk_crypto.pub
```

3. **On GitHub**: repo → **Settings** → **Deploy keys** → **Add deploy key**. Paste the public key. Leave "Allow write access" **disabled** (read-only is enough).

4. **On the VM**, create or update `~/.ssh/config`:

```txt
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_mdk_crypto
  IdentitiesOnly yes
```

5. Clone via SSH:

```bash
git clone git@github.com:<your-username>/mdk_crypto_trading.git
cd mdk_crypto_trading
```

### 4b. Create the `.env` file on the VM

The `.env` file is never committed to GitHub — it must be created manually on the VM:

```bash
nano .env
```

Paste the contents of your local `.env` (API keys, configuration, etc.), then save with `Ctrl+O`, `Enter`, `Ctrl+X`.

See [.env.example](../.env.example) for the complete list of required variables.

### 4c. Start the container

```bash
docker compose up -d
```

Docker will download Python, install the dependencies and start the bot in the background.

Check that it's running:

```bash
docker compose ps
```

Read the logs in real time:

```bash
docker compose logs -f
```

---

## 5. Updating (new code version)

When there's a new code version on GitHub:

```bash
cd mdk_crypto_trading

# Pull the latest changes
git pull

# Rebuild the image and restart the container
docker compose up -d --build
```

The bot stops for a few seconds during the rebuild, then restarts automatically.

---

## 6. Useful commands

### Container status

```bash
docker compose ps
```

### Real-time logs

```bash
docker compose logs -f
```

### Logs of the last 100 events

```bash
docker compose logs --tail=100
```

### Stopping the bot

```bash
docker compose down
```

Docker sends `SIGTERM` to the container and waits up to `stop_grace_period` (configured as `60s` in `docker-compose.yaml`) before forcing `SIGKILL`. The runner catches the signal, completes the current cycle, writes the "Shutdown" log and sends the stop notification via Telegram. LLM+Binance cycles can take 30-40s: the 60s grace period comfortably covers the worst case.

### Restarting the bot (without rebuilding)

```bash
docker compose restart
```

This is also the command to use to **reset a tripped circuit breaker**: after 3 identical consecutive errors, `TradingRunner` suspends the cycles and sends the `[ALARM] CIRCUIT BREAKER TRIPPED` Telegram notification. The container stays alive and healthy, but stops operating until it is manually restarted. See `docs/observability.md` for details.

### Checking VM resources

```bash
# CPU and RAM
htop

# Disk space
df -h
```

### Freeing up disk space (Docker cleanup)

After multiple rebuilds, Docker accumulates unused images and layers that take up several GB. To remove them all at once:

```bash
docker system prune -a
```

It asks for confirmation before proceeding. It does not touch the running container or the volumes with the bot's data.

To see how much space the bot's logs and events take up before deciding whether to clean them:

```bash
du -sh ~/mdk_crypto_trading/logs/
du -sh ~/mdk_crypto_trading/data/
```

To start fresh (deletes logs, JSONL events, DM memory and performance reports):

```bash
sudo rm -rf ~/mdk_crypto_trading/logs/events/
sudo rm -f ~/mdk_crypto_trading/logs/mdk_crypto_trading.log*
sudo rm -rf ~/mdk_crypto_trading/data/memory/
sudo rm -f ~/mdk_crypto_trading/data/performance_reports/*.md
```

### Downloading logs and events locally

Logs and events are created by Docker as `root`. To download them you need to create a tarball with `sudo` on the VM, then transfer it locally.

**On the VM** (with the user that owns the project, e.g. `<project-user>`):

```bash
cd ~/mdk_crypto_trading
sudo tar czf ~/logs_export.tar.gz logs/
sudo chown $USER:$USER ~/logs_export.tar.gz
exit
```

**If the tarball was created by a different user** (e.g. `<project-user>`) than the one you connect with via SSH (e.g. `<ssh-user>`):

```bash
sudo cp /home/<project-user>/logs_export.tar.gz ~/
sudo chown $USER:$USER ~/logs_export.tar.gz
```

**From your local Mac/PC**:

```bash
gcloud compute scp --zone=europe-west1-b mdk-crypto-trading:/home/<project-user>/logs_export.tar.gz ./
tar xzf logs_export.tar.gz -C logs/
rm logs_export.tar.gz
```

> **Note**: `gcloud scp` connects with the default user (`<ssh-user>`), but the tarball is in `<project-user>`'s home directory. Using the absolute path `/home/<project-user>/` avoids the "No such file or directory" error.

**Cleanup on the VM** (removing temporary tarballs):

```bash
rm ~/logs_export.tar.gz
sudo rm -f /home/<project-user>/logs_export.tar.gz
```

> **Note — upgrading from a previous version**: if you already have files in `logs/` or `data/` created by the old container (which ran as `root`), run this command **once** on the VM to align the permissions:

  ```bash
  sudo chown -R 1000:1000 ~/mdk_crypto_trading/logs/ ~/mdk_crypto_trading/data/
  ```

> After this step, `sudo` will no longer be needed for any log operation.

---

## 7. 🔍 Troubleshooting

### The container starts and immediately stops

Check the logs to see the error:

```bash
docker compose logs
```

Common causes:

- **Missing variable in `.env`**: check that all keys are present
- **Syntax error in `.env`**: no spaces around `=`, no quotes unless necessary

### "Permission denied" error with Docker

You need to reopen the SSH session after adding the user to the `docker` group:

```bash
exit
# log back in via SSH
```

### Binance error "Service unavailable from a restricted location"

The VM is in a region blocked by Binance (e.g. the United States). The VM must be recreated in a European region such as `europe-west1` (Belgium). See section 1.

### The bot doesn't connect to Binance or the AI APIs

- Verify that the API keys in the VM's `.env` are correct
- Check that the VM has internet access (test: `curl https://api.binance.com/api/v3/ping`)
- Verify that the Binance keys have the correct permissions (read + trading)

### The project is not in the SSH user's home directory

If the project was cloned by a different user than the one used to log in via SSH, the folder will not be visible in your own home directory. To find the project and work with it:

```bash
# Search for the project folder
sudo find /home -name "mdk_crypto_trading" -type d

# If the project is under another user (e.g. <project-user>), switch to that user
sudo su - <project-user>
cd mdk_crypto_trading
```

From here you can run `git pull`, `docker compose up -d --build`, etc. To exit and return to your own user:

```bash
exit
```

### Disk space exhausted

Logs can grow over time. Check with:

```bash
df -h
du -sh mdk_crypto_trading/logs/
```

If needed, clear old logs:

```bash
find mdk_crypto_trading/logs/events/ -name "*.jsonl" -mtime +30 -delete
```

### "Permission denied" error when deleting logs or memory

Files in `logs/` and `data/` are created by the container and belong to the system user under which Docker runs on the VM (typically `ubuntu` on GCE). Your SSH user (`<project-user>`) is not the same owner, so `sudo` is needed to delete them:

```bash
sudo rm -rf ~/mdk_crypto_trading/logs/events/
sudo rm -f ~/mdk_crypto_trading/logs/mdk_crypto_trading.log*
sudo rm -rf ~/mdk_crypto_trading/data/memory/
sudo rm -f ~/mdk_crypto_trading/data/performance_reports/*.md
```

To check who owns the files at any time:

```bash
ls -la ~/mdk_crypto_trading/logs/
ls -la ~/mdk_crypto_trading/data/
```

---

### The VM restarts and the bot doesn't start

With `restart: unless-stopped` in `docker-compose.yaml`, Docker automatically restarts the container when the VM reboots. If that doesn't happen, start Docker manually:

```bash
sudo systemctl enable docker
sudo systemctl start docker
cd mdk_crypto_trading
docker compose up -d
```

---

### Expanding the VM disk

If the disk approaches 80% usage, it's worth growing it from 10 GB to 20 GB. This operation does not require stopping the bot or rebooting the VM.

**1. From the GCP console** (without shutting down the VM):

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Menu → **Compute Engine** → **Disks**
3. Click on the VM's disk (`mdk-crypto-trading`)
4. Click **Edit** → change the size to `20` GB → **Save**

**2. On the VM**, expand the partition to use the added space:

```bash
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
```

Verify the result:

```bash
df -h
```

The disk now shows ~20 GB available. The bot keeps running without interruption throughout the whole procedure.

---

## 📚 References

- **Code**: `Dockerfile`, `docker-compose.yaml`
- **Related docs**: `docs/config.md`
- **External resources**:
  - [Google Compute Engine](https://cloud.google.com/compute/docs)
  - [Docker Compose](https://docs.docker.com/compose/)
  - [gcloud CLI](https://cloud.google.com/sdk/docs/install)
