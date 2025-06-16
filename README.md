# Digital Picture Frame Solution

> A private, self-hosted slideshow that runs on a low-power Linux box and lets **only me** upload new family photos & videos using my Microsoft account.

---

## 1  Overview

This project:

* Runs inside a Docker container on my Linux workstation.
* Serves a slideshow of images & videos to any device on my home LAN.
* Offers an **admin** dashboard to upload / delete media.
* Stores media **and** SQLite DB on a USB stick (bind-mounted), so data survives container rebuilds.
* Uses Python + Flask behind the **Waitress** WSGI server.
* Auto-restarts after host reboot (`restart: unless-stopped` in Compose).
* Calculates video length at upload time, guaranteeing each video plays through before advancing.

---

## 2  Motivation & Hardware

Commercial digital frames were pricey, closed, and inflexible.  
Instead I bought two cheap Android tablets, framed them, and pointed their kiosk browsers at `http://framebox.local/display`.  
Front-camera motion detection wakes the screen only when someone is nearby, and all heavy lifting stays on the server.

---

## 3  Key Features

| # | Feature | Notes |
|---|---------|-------|
| 1 | **Slideshow** (`/display`) | Images rotate every 10 s; videos run full length using duration stored in DB. |
| 2 | **Admin portal** (`/admin`) | Upload JPG/PNG/MP4/MOV, thumbnail auto-generated (Pillow / FFmpeg), delete items. |
| 3 | **Azure AD / Microsoft-account sign-in** | Admin page protected by Microsoft identity platform — no passwords stored locally. |
| 4 | **Video duration detection** | `ffprobe` extracts length; value cached in SQLite. |
| 5 | **USB persistence** | Media + `db.sqlite3` live on `/mnt/pictureframe_storage` outside the container. |
| 6 | **Dockerised** | Reproducible `Dockerfile`; runs under Waitress, not Flask dev server. |
| 7 | **LAN-only access** | Server firewall only exposes port 8085 to 192.168.0.0/16. |

---

## 4  How Microsoft sign-in works

### 4.1  Azure registration

| Setting | Value |
|---------|-------|
| **App registration name** | `PictureFrameAdmin` |
| **Supported account types** | *Personal Microsoft accounts* (or “Any AAD tenant + personal MSAs”) |
| **Redirect URIs** | `http://localhost:8085/auth/callback` (dev)<br>`http://<server-ip>:8085/auth/callback` (prod) |
| **Certificates & secrets → Client secret** | `HomePictureFrame` → copy VALUE |

*(No implicit-flow check-boxes; we use authorization-code flow.)*

### 4.2  Flow inside the code

```mermaid
sequenceDiagram
Browser->>/admin: GET
Admin-->>Browser: 302 /login
Browser->>/login: GET
login->>Microsoft: 302 /authorize?client_id=...&state=...
Microsoft-->>Browser: Sign-in UI
Browser->>Microsoft: Credentials
Microsoft-->>Browser: 302 /auth/callback?code=...
Browser->>/auth/callback: code
Flask(/auth/callback)->>Microsoft: POST /token (code, client_secret)
Microsoft-->>Flask: id_token + access_token
Flask-->>Browser: 302 /admin (cookie set)
Browser->>/admin: authenticated HTML
```

* **MSAL Python** adds `openid profile offline_access` automatically; our code requests `User.Read`.
* After token exchange the app stores `id_token_claims` in **Flask session** under `SESSION_KEY=user`.
* An allow-list check…

```python
user_email = (claims.get("email") or claims.get("preferred_username", "")).lower()
if user_email not in ALLOWED_EMAILS: return 403
```

…ensures **only `YOUR_EMAIL`** (or any comma-separated list in `.env`) can access admin routes.

No token is persisted to disk; logout clears the cookie and performs an Entra front-channel logout.

---

## 5  Folder layout

```
/opt/pictureframe
├── docker-compose.yml      # runtime definition
├── .env                    # secrets (chmod 600)
└── app/ Dockerfile ...     # source (optional on server if you pull image)
```

USB stick:

```
/mnt/pictureframe_storage/
├── media/                  # images, videos, thumbnails/
├── thumbnails/             # generated thumbs
└── db.sqlite3              # SQLite DB (bind-mounted)
```

---

## 6  Deployment (Docker Compose)

### 6.1  .env (never commit)

```env
# Azure identity
AZURE_CLIENT_ID=<GUID>
AZURE_CLIENT_SECRET=<secret>
AZURE_TENANT_ID=consumers
ALLOWED_EMAIL=YOUR_EMAIL

# Flask session signing
FLASK_SECRET_KEY=64_random_chars_here
```

```bash
chmod 600 /opt/pictureframe/.env
```

### 6.2  docker-compose.yml

```yaml
version: "3.9"

services:
  pictureframe:
    image: panog792/pictureframe:latest   # pulled from Docker Hub
    container_name: pictureframe
    restart: unless-stopped

    env_file:
      - .env

    ports:
      - "8085:8080"          # external:internal

    volumes:
      - /mnt/pictureframe_storage/media:/app/app/media
      - /mnt/pictureframe_storage/db.sqlite3:/app/app/db.sqlite3
```

### 6.3  Run / update

```bash
cd /opt/pictureframe
docker compose pull        # get latest image
docker compose up -d       # (re)start
docker compose logs -f     # tail logs
```

Rotate the client secret? → edit `.env`, `docker compose up -d`.

---

## 7  Development workflow

```bash
# Clone & create venv
git clone https://github.com/you/pictureframe.git
cd pictureframe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)        # load secrets
export FLASK_APP=app.app:app
flask run --host 0.0.0.0 --port 8085       # dev server
```

Push new image:

```bash
docker build -t panog792/pictureframe:latest .
docker push panog792/pictureframe:latest
```

Server: `docker compose pull && docker compose up -d`.

---

## 8  Security notes

* **Secrets stay on host**; not baked into image, not committed to Git.
* Flask `SESSION_COOKIE_SECURE` can be set when you terminate TLS in front (nginx / Caddy).
* Admin page is inaccessible to anyone without a Microsoft sign-in **and** e-mail allow-list match.
* All traffic remains LAN-only behind the firewall.

---

## 9  Conclusion

With Microsoft Entra sign-in, Docker Compose, and a USB-backed volume, the project is now:

* **Secure** – no local passwords, OAuth2/OIDC handled by Azure, single e-mail allow-list.
* **Resilient** – auto-restart, data persistent across images, easy secret rotation.
* **Portable** – one-line deploy on any Linux box with Docker.
* **Family-friendly** – tablets wake on motion, video timing is perfect, uploads happen from any phone browser on the same Wi-Fi.

Enjoy your private, customizable, and low-cost digital picture frame! 🖼️🚀

---

## 10  Authorship & License

**Author:** Panagiotis Georgiadis
© Panagiotis Georgiadis. All rights reserved.
Contact me for permission inquiries or contributions.


---

