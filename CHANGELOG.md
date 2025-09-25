# 📝 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2025-09-25

### 🎉 Initial Release

#### ✨ Added
- **SSL Certificate Automation** for Selectel Object Storage
- **Let's Encrypt integration** via acme.sh
- **Dynamic path generation** based on domain configuration
- **Telegram notifications** for success and error reporting
- **Rate limit handling** from Let's Encrypt API
- **Certificate/key validation** with automatic mismatch recovery
- **Backup file recovery** from acme.sh directories
- **PKCS#8 key format conversion** for Selectel compatibility
- **Local certificate installation** with backup creation
- **Environment variable configuration** via .env file
- **Multilingual documentation** (English and Russian)

#### 🔧 Configuration Features
- **Flexible domain setup** with optional wildcard support
- **Comprehensive logging** with configurable levels  
- **Selective Telegram notifications** (success/error/logs)
- **Customizable file paths** and certificate names

#### 🛡️ Security Features
- **Secure credential handling** via environment variables
- **Certificate validation** before upload
- **Backup creation** before any modifications
- **Proper file permissions** for private keys

#### 📚 Documentation
- **Complete setup guide** with examples
- **Troubleshooting section** for common issues
- **Security best practices** 
- **Systemd service configuration** examples
- **Cron scheduling** recommendations

---

## 🔮 Planned Features

### 🚀 Version 1.1.0 (Coming Soon)
- [ ] **Multi-domain support** in single configuration
- [ ] **DNS challenge support** for wildcard certificates
- [ ] **Certificate expiry monitoring** with advance warnings
- [ ] **Docker container** for easy deployment
- [ ] **Web dashboard** for monitoring and management

### 🎯 Version 1.2.0 (Future)
- [ ] **Multiple cloud provider support** (CloudFlare, AWS)
- [ ] **Certificate revocation** handling
- [ ] **Advanced retry mechanisms** with exponential backoff
- [ ] **Health check endpoints** for monitoring
- [ ] **Grafana/Prometheus metrics** export

---

## 🐛 Known Issues

### Current Limitations
- **Single domain configuration** per instance
- **Manual acme.sh setup** required
- **Linux/Unix only** (Windows not tested)

### Workarounds
- Run multiple instances for multiple domains
- Follow acme.sh documentation for initial setup
- Use WSL on Windows environments

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### 🎖️ Contributors
- **[@yourusername](https://github.com/yourusername)** - Initial development and maintenance

---

## 📊 Version History

| Version | Date | Description | Downloads |
|---------|------|-------------|-----------|
| 1.0.0 | 2025-09-25 | Initial release | [![Downloads](https://img.shields.io/github/downloads/yourusername/ssl-automation-selectel/v1.0.0/total.svg)](https://github.com/yourusername/ssl-automation-selectel/releases/tag/v1.0.0) |

---

<div align="center">

**[🏠 Home](README.md)** • **[📖 Documentation](https://github.com/yourusername/ssl-automation-selectel/wiki)** • **[🐛 Issues](https://github.com/yourusername/ssl-automation-selectel/issues)**

</div>