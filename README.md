# 🌐 CDN Manager Bot

A powerful Telegram-based DNS management platform that lets you manage CDN providers directly from Telegram.

Current supported provider:

* ✅ Cloudflare

Planned providers:

* 🚧 BunnyCDN
* 🚧 Gcore
* 🚧 CloudFront
* 🚧 Fastly
* 🚧 Akamai
* 🚧 Custom CDN Plugins

CDN Manager Bot is designed to become a centralized Telegram control panel for multiple CDN providers.

---

# ✨ Features

### Telegram DNS Management

* Browse all Cloudflare zones
* View DNS records
* Create DNS records
* Edit DNS records
* Delete DNS records
* Refresh records instantly

### Supported Record Types

* A
* AAAA
* CNAME
* TXT
* MX
* SRV

### Security

* Admin-only access
* Cloudflare API Token authentication
* Environment-based configuration
* Permission validation

### CLI Management Panel

Built-in management script inspired by:

* x-ui
* 3x-ui

Run:

```bash
cdn
```

from anywhere on your server.

### Service Management

* Start Bot
* Stop Bot
* Restart Bot
* Enable Auto Start
* Disable Auto Start
* View Logs
* Check Status

### Update System

* Update to latest version
* Install specific versions
* Roll back to previous releases

### Configuration Manager

Modify:

* Telegram Bot Token
* Admin Telegram ID
* Cloudflare API Token

without manually editing files.

---

# 📦 Installation

Install using a single command:

```bash
bash <(curl -Ls https://raw.githubusercontent.com/YOUR_USERNAME/CDN-BOT/main/install.sh)
```

or

```bash
wget -qO- https://raw.githubusercontent.com/YOUR_USERNAME/CDN-BOT/main/install.sh | bash
```

The installer will:

* Install dependencies
* Create Python virtual environment
* Configure systemd service
* Create configuration files
* Ask for required credentials
* Start the bot automatically

---

# 🚀 Quick Start

After installation:

```bash
cdn
```

You will see:

```text
CDN Manager Bot Script ( v1.1.0 )

0) Exit

1) Install
2) Update
3) Install Specific Version
4) Uninstall
5) Service Manager
6) Start Bot
7) Stop Bot
8) Restart Bot
9) View Logs
10) Config Manager
11) Help

Bot Status : Running
Auto Start : Enabled

Please enter a number [0-11]:
```

---

# 🔧 Configuration

The installer will ask for:

## Telegram Bot Token

Create one using:

1. Open Telegram
2. Search for:

```text
@BotFather
```

3. Send:

```text
/newbot
```

4. Follow instructions
5. Copy the generated token

Example:

```text
123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Telegram Numeric ID

Get your Telegram ID:

1. Search for:

```text
@userinfobot
```

2. Start the bot
3. Send any message
4. Copy your numeric ID

Example:

```text
123456789
```

---

## Cloudflare API Token

Login to Cloudflare Dashboard.

Navigate to:

```text
Profile
└── API Tokens
```

Click:

```text
Create Token
```

Choose:

```text
Edit zone DNS
```

using:

```text
Use Template
```

Permissions:

```text
Zone → DNS → Edit
Zone → Zone → Read
```

Zone Resources:

```text
Specific Zone
```

or

```text
All Zones
```

Recommended:

```text
All Zones
```

Client IP Address Filtering:

```text
Leave Empty
```

Token TTL:

```text
No Expiration
```

Create the token and copy it into the installer.

---

# 📂 Installation Paths

Application Directory:

```text
/usr/local/cdn-manager
```

Bot Directory:

```text
/usr/local/cdn-manager/cdn_manager_bot
```

Environment File:

```text
/usr/local/cdn-manager/cdn_manager_bot/.env
```

Systemd Service:

```text
/etc/systemd/system/cdn-manager-bot.service
```

Global Command:

```text
cdn
```

---

# 🖥 Service Management

Open manager:

```bash
cdn
```

Choose:

```text
5) Service Manager
```

Available actions:

```text
1) Enable Auto Start
2) Disable Auto Start
3) Start Service
4) Stop Service
5) Restart Service
6) Service Status
```

---

# ⚙ Config Manager

Open:

```bash
cdn
```

Then:

```text
10) Config Manager
```

Available actions:

```text
1) Edit Bot Token
2) Edit Admin ID
3) Edit Cloudflare API Token
4) Show Current Configuration
```

Changes are written directly to:

```text
/usr/local/cdn-manager/cdn_manager_bot/.env
```

---

# 📜 Logs

View logs from the manager:

```text
9) View Logs
```

or manually:

```bash
journalctl -u cdn-manager-bot -f
```

---

# 🔄 Updates

Update to latest version:

```bash
cdn
```

Then select:

```text
2) Update
```

---

# ⏪ Install Specific Version

To install an older release:

```bash
cdn
```

Select:

```text
3) Install Specific Version
```

Example:

```text
1.0.1
1.1.1
```

The installer will fetch and install the selected Git tag.

---

# 🆘 Help Menu

Inside:

```bash
cdn
```

Select:

```text
11) Help
```

Available guides:

```text
1) How to create Telegram Bot Token
2) How to get Telegram Numeric ID
3) How to create Cloudflare API Token
4) Installation Paths
```

---

# 📁 Repository Structure

```text
CDN-BOT/
│
├── install.sh
├── uninstall.sh
├── README.md
│
└── cdn_manager_bot/
    ├── bot.py
    ├── config.py
    ├── database.py
    ├── cloudflare_api.py
    ├── requirements.txt
    │
    ├── handlers/
    ├── keyboards/
    ├── utils/
    ├── logs/
    │
    └── systemd/
        └── cdn-manager-bot.service
```

---

# 🔒 Security Notes

* Never share your `.env` file.
* Never publish your Cloudflare API Token.
* Never publish your Telegram Bot Token.
* Use the minimum required Cloudflare permissions.
* Restrict access to trusted administrators only.

---

# 🗺 Roadmap

### Version 1.x

* Cloudflare DNS Management
* Telegram Control Panel
* CLI Management Script

### Version 2.x

* Multi-CDN Support
* Provider Selection
* Account Profiles

### Version 3.x

* Multi-Admin Support
* Audit Logs
* Role-Based Access Control

---

