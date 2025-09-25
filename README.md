# 🔒 SSL Certificate Automation for Selectel Object Storage

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Selectel](https://img.shields.io/badge/Selectel-Object%20Storage-orange.svg)](https://selectel.ru/)
[![Let's Encrypt](https://img.shields.io/badge/Let's%20Encrypt-Automated-green.svg)](https://letsencrypt.org/)

> 🌍 **Language:** **🇺🇸 English** | [🇷🇺 Русский](README.ru.md)

I created this tool after getting tired of manually updating SSL certificates for my domains hosted on Selectel Object Storage. The built-in certificate manager kept having issues, so I decided to automate the whole process using Let's Encrypt and acme.sh.

---

## 🚀 What This Does

The script automatically:

✅ **Generates or renews SSL certificates** using Let's Encrypt via acme.sh  
✅ **Uploads certificates to Selectel Object Storage** using their API  
✅ **Handles all certificate validation** and key format conversions  
✅ **Sends notifications via Telegram** when something goes wrong (or right)  
✅ **Installs certificates locally** for backup purposes  
✅ **Gracefully handles rate limiting** from Let's Encrypt  

---

## 🎯 Why I Made This

Selectel's certificate management can be finicky, especially when you have wildcard domains. I needed something reliable that would run monthly and just work without me having to think about it. The script handles rate limiting from Let's Encrypt gracefully and will use existing valid certificates when needed.

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/ssl-automation-selectel.git
cd ssl-automation-selectel
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure settings

```bash
cp .env.example .env
nano .env  # fill in your details
```

### 4. Test run

```bash
python ssl_renewal.py
```

---

## 🔧 Configuration

All configuration is done through the `.env` file. The paths are automatically generated based on your domain, so you only need to specify the domain once and everything else gets calculated.

### 📝 Required Settings

#### **Selectel credentials:**

- Your Selectel cloud username and password
- Account ID and project ID from your Selectel dashboard
- Container name where your domain is hosted

#### **Domain settings:**

- **Main domain** (`DOMAIN`) is required (e.g., example.com)
- **Wildcard domain** (`WILDCARD_DOMAIN`) is optional (e.g., *.example.com)

#### **Telegram notifications** (optional but recommended):

- Bot token and chat ID for notifications
- I highly recommend setting this up so you know when renewals happen

---

## 🛠️ How It Works

The script is pretty smart about handling different scenarios:

### 📋 Normal renewal

1. **Gets new certificates** from Let's Encrypt and uploads to Selectel
2. **Validates certificate/key pairs** automatically
3. **Sends success notification** via Telegram

### ⚠️ Rate limited by Let's Encrypt

1. **Detects rate limiting** from API response
2. **Uses existing valid certificates** instead of failing
3. **Continues operation** without interruption

### 🔍 Mismatched files

1. **Automatically searches** for valid certificate/key pairs
2. **Checks backup directories** if main files are corrupted
3. **Restores from backups** when needed

---

## ⏰ Scheduling

I run this monthly via cron:

```bash
# Every 1st day of month at 3:00 AM
0 3 1 * * /path/to/your/script/ssl_renewal.py
```

### 📊 Systemd monitoring (optional)

Create service files for better monitoring:

```ini
# /etc/systemd/system/ssl-renewal.service
[Unit]
Description=SSL Certificate Renewal
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/path/to/ssl-automation
ExecStart=/usr/bin/python3 ssl_renewal.py
```

```ini
# /etc/systemd/system/ssl-renewal.timer
[Unit]
Description=SSL Certificate Renewal Timer
Requires=ssl-renewal.service

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
```

---

## 🆘 Troubleshooting

### ❌ "Certificate and key don't match" errors

The script will automatically try to find matching pairs in your acme.sh directory. This usually happens when acme.sh creates new certificates but doesn't update all files consistently.

### 🚫 Rate limit errors from Let's Encrypt

The script handles this gracefully and will use existing valid certificates. Let's Encrypt allows 5 certificates per week for the same domain set.

### 🔑 Selectel API errors

Make sure your credentials are correct and you have the right project ID. The script uses Selectel's v2 SSL API which requires specific permissions.

---

## 📦 Dependencies

- **Python 3.6+**
- **requests library** — for HTTP requests to APIs
- **python-dotenv library** — for loading environment variables
- **acme.sh installed and configured** — for Let's Encrypt certificates
- **OpenSSL tools** — for certificate validation and conversion

---

## 🔒 Security Notes

- ⚠️ **The `.env` file contains sensitive credentials** — keep it secure
- 🔐 **Private keys are automatically converted** to PKCS#8 format for Selectel
- 💾 **Backup copies of certificates are created** before any changes
- 🛡️ **All API calls use proper authentication** headers

---

## 🌟 What's Different About This

Unlike other SSL automation tools, this one is specifically designed for Selectel Object Storage. It handles their API quirks and certificate format requirements automatically. I've been using it for several months without issues.

The script also gracefully handles Let's Encrypt rate limiting by using existing valid certificates when new ones can't be issued. This means your sites stay online even if you hit API limits.

---

## 📈 Project Status

- ✅ **Stable release** — used in production for several months
- 🔄 **Active maintenance** — regular updates and bug fixes
- 📝 **Complete documentation** — detailed setup and usage guides
- 🌍 **Multilingual** — English and Russian documentation

---

## 🤝 Contributing

1. **🌟 Star the repository** if you find it useful
2. **🐛 Report bugs** via Issues
3. **💡 Suggest improvements** via Pull Requests
4. **📖 Improve documentation**

---

## 📄 License

**MIT** — Use it however you want. If you find bugs or have improvements, feel free to contribute.

---

<div align="center">

### 🎯 Made with ❤️ for SSL automation

**[⭐ Star](https://github.com/DigneZzZ/s3-ssl-selecte)** • **[🐛 Issues](https:/DigneZzZ/s3-ssl-selecte/issues)** • **[📖 Wiki](https://github.com/DigneZzZ/s3-ssl-selecte/wiki)**


</div>
