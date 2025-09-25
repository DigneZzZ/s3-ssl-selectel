#!/usr/bin/env python3

import requests
import sys
import os
import subprocess
import logging
from datetime import datetime
import shutil
from dotenv import load_dotenv

load_dotenv()

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False
    
    def send_success(self, domain: str, cert_id: str, expires_at: str):
        message = f"""✅ *SSL certificate updated successfully*

🌐 *Domain:* `{domain}`
🔑 *Certificate ID:* `{cert_id}`
📅 *Valid until:* {expires_at}
⏰ *Updated:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

Certificate successfully replaced in Object Storage container."""
        return self.send_message(message)
    
    def send_error(self, domain: str, error: str, step: str = ""):
        step_text = f" at step '{step}'" if step else ""
        message = f"""❌ *SSL certificate update failed*

🌐 *Domain:* `{domain}`
❗ *Error{step_text}:*
```
{error}
```
⏰ *Time:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

Manual check required!"""
        return self.send_message(message)


class SSLCertificateManager:
    def __init__(self):
        self.config = self._load_config()
        self.token = None
        self.logs = []
        self.setup_logging()
        
        self.telegram = None
        if self.config["telegram"]["enabled"]:
            self.telegram = TelegramNotifier(
                self.config["telegram"]["bot_token"],
                self.config["telegram"]["chat_id"]
            )
    
    def _load_config(self):
        domain = os.getenv("DOMAIN")
        
        return {
            "selectel": {
                "username": os.getenv("SELECTEL_USERNAME"),
                "password": os.getenv("SELECTEL_PASSWORD"),
                "account_id": os.getenv("SELECTEL_ACCOUNT_ID"),
                "project_id": os.getenv("SELECTEL_PROJECT_ID"),
                "auth_url": os.getenv("SELECTEL_AUTH_URL"),
                "storage_api_url": os.getenv("SELECTEL_STORAGE_API_URL"),
            },
            "storage": {
                "container_name": os.getenv("SELECTEL_CONTAINER_NAME"),
                "domain": domain,
                "current_cert_id": os.getenv("SELECTEL_CURRENT_CERT_ID"),
                "cert_name": os.getenv("SELECTEL_CERT_NAME"),
            },
            "domains": [d for d in [domain, os.getenv("WILDCARD_DOMAIN")] if d and d.strip()],
            "acme": {
                "script_path": os.getenv("ACME_SCRIPT_PATH"),
                "cert_dir": f"/root/.acme.sh/{domain}",
                "cert_file": f"/root/.acme.sh/{domain}/{domain}.cer",
                "key_file": f"/root/.acme.sh/{domain}/{domain}.key",
                "fullchain_file": f"/root/.acme.sh/{domain}/fullchain.cer",
                "ca_file": f"/root/.acme.sh/{domain}/ca.cer",
            },
            "install": {
                "cert_path": f"/etc/ssl/certs/{domain}.crt",
                "key_path": f"/etc/ssl/private/{domain}.key", 
                "fullchain_path": f"/etc/ssl/certs/{domain}.fullchain.pem",
            },
            "services": [],
            "telegram": {
                "enabled": os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
                "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
                "send_success": os.getenv("TELEGRAM_SEND_SUCCESS", "true").lower() == "true",
                "send_errors": os.getenv("TELEGRAM_SEND_ERRORS", "true").lower() == "true",
                "send_logs": os.getenv("TELEGRAM_SEND_LOGS", "true").lower() == "true",
            },
            "log": {
                "file": os.getenv("LOG_FILE", "/var/log/ssl-cert-renewal.log"),
                "level": os.getenv("LOG_LEVEL", "INFO"),
            }
        }
    
    def setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.config["log"]["level"]),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config["log"]["file"]),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log_and_store(self, message: str, level: str = "info"):
        self.logs.append(f"{datetime.now().strftime('%H:%M')} {message}")
        getattr(self.logger, level)(message)
    
    def get_iam_token(self):
        self.log_and_store("Getting IAM token...")
        
        payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self.config["selectel"]["username"],
                            "domain": {
                                "name": self.config["selectel"]["account_id"]
                            },
                            "password": self.config["selectel"]["password"]
                        }
                    }
                },
                "scope": {
                    "project": {
                        "id": self.config["selectel"]["project_id"]
                    }
                }
            }
        }
        
        try:
            response = requests.post(
                self.config["selectel"]["auth_url"],
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                self.token = response.headers.get('X-Subject-Token')
                self.log_and_store("✅ IAM token obtained successfully")
                return True
            else:
                self.log_and_store(f"❌ Token error: {response.status_code}", "error")
                return False
                
        except Exception as e:
            self.log_and_store(f"❌ Token exception: {e}", "error")
            return False
    
    def get_current_certificate_info(self):
        if not self.token:
            return None
        
        url = f"{self.config['selectel']['storage_api_url']}/v2/ssl"
        headers = {
            "X-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                certificates = response.json()
                domain_to_find = self.config["storage"]["domain"]
                
                for cert in certificates:
                    cert_domains = cert.get("domains", [])
                    if domain_to_find in cert_domains:
                        self.log_and_store(f"🎯 Found certificate for domain {domain_to_find}")
                        return cert
                
                self.log_and_store(f"⚠️ Certificate for domain {domain_to_find} not found", "warning")
                return None
                
        except Exception as e:
            self.log_and_store(f"❌ Certificate info error: {e}", "error")
            return None
    
    def renew_certificate_with_acme(self):
        self.log_and_store("🔄 Checking certificate renewal options...")
        
        if self._check_existing_certificate():
            self.log_and_store("✅ Using existing valid certificate")
            return True
        
        self.log_and_store("🔄 Attempting certificate renewal via acme.sh...")
        
        domains = self.config["domains"]
        if not domains:
            self.log_and_store("❌ No domains configured for certificate renewal", "error")
            return False
            
        primary_domain = domains[0]
        
        cmd = [
            self.config["acme"]["script_path"],
            "--renew",
            "-d", primary_domain
        ]
        
        for domain in domains[1:]:
            cmd.extend(["-d", domain])
        
        cmd.extend(["--force", "--always-force-new-domain-key"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.log_and_store("✅ Certificate renewed via acme.sh successfully")
                return True
            else:
                if ("rateLimited" in result.stderr or 
                    "too many certificates" in result.stderr or 
                    "rate limited" in result.stderr.lower()):
                    self.log_and_store("⚠️ Rate limit from Let's Encrypt - using existing certificate", "warning")
                    return self._check_existing_certificate_force()
                
                self.log_and_store(f"❌ acme.sh error: {result.stderr}", "error")
                return self._check_existing_certificate_force()
                
        except Exception as e:
            self.log_and_store(f"❌ acme.sh exception: {e}", "error")
            return self._check_existing_certificate_force()
    
    def _check_existing_certificate(self):
        cert_file = self.config["acme"]["cert_file"]
        
        if not os.path.exists(cert_file):
            return False
        
        try:
            result = subprocess.run([
                "openssl", "x509", "-in", cert_file, "-noout", "-enddate"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import re
                date_match = re.search(r'notAfter=(.+)', result.stdout)
                if date_match:
                    expiry_date = datetime.strptime(date_match.group(1), '%b %d %H:%M:%S %Y %Z')
                    days_left = (expiry_date - datetime.now()).days
                    if days_left > 30:
                        self.log_and_store(f"✅ Using existing certificate (valid for {days_left} days)")
                        return True
                        
        except Exception:
            pass
            
        return False
    
    def _check_existing_certificate_force(self):
        cert_file = self.config["acme"]["cert_file"]
        key_file = self.config["acme"]["key_file"]
        
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            self.log_and_store("❌ Main certificate files not found", "error")
            return False
        
        try:
            result = subprocess.run([
                "openssl", "x509", "-in", cert_file, "-noout", "-enddate"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import re
                date_match = re.search(r'notAfter=(.+)', result.stdout)
                if date_match:
                    expiry_date = datetime.strptime(date_match.group(1), '%b %d %H:%M:%S %Y %Z')
                    days_left = (expiry_date - datetime.now()).days
                    
                    if days_left > 0:
                        with open(cert_file, 'r') as f:
                            cert_content = f.read()
                        with open(key_file, 'r') as f:
                            key_content = f.read()
                        
                        if self._verify_cert_key_match(cert_content, key_content):
                            self.log_and_store(f"✅ Using existing certificate (valid for {days_left} days, rate limit)")
                            return True
                        else:
                            self.log_and_store("❌ Existing certificate and key don't match", "error")
                    else:
                        self.log_and_store(f"❌ Existing certificate expired {-days_left} days ago", "error")
                        
        except Exception as e:
            self.log_and_store(f"❌ Existing certificate check error: {e}", "error")
            
        return False
    
    def read_certificate_files(self):
        try:
            required_files = [
                self.config["acme"]["cert_file"],
                self.config["acme"]["key_file"],
                self.config["acme"]["fullchain_file"]
            ]
            
            missing_files = []
            for file_path in required_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
                    self.log_and_store(f"⚠️ File not found: {file_path}", "warning")
            
            if missing_files:
                self.log_and_store("🔍 Searching for alternative certificate files...", "info")
                cert_data = self._find_alternative_certificates()
                if cert_data:
                    return cert_data
                else:
                    self.log_and_store("❌ Alternative certificate files not found", "error")
                    return None
            
            with open(self.config["acme"]["cert_file"], 'r') as f:
                cert_content = f.read().strip()
            
            with open(self.config["acme"]["key_file"], 'r') as f:
                key_content = f.read().strip()
            
            with open(self.config["acme"]["fullchain_file"], 'r') as f:
                fullchain_content = f.read().strip()
            
            if not self._verify_cert_key_match(cert_content, key_content):
                self.log_and_store("❌ CRITICAL ERROR: Main files don't match!", "error")
                self.log_and_store("🔍 Searching for alternative matching files...", "info")
                
                cert_data = self._find_alternative_certificates()
                if cert_data:
                    return cert_data
                else:
                    self.log_and_store("❌ Matching alternative files not found", "error")
                    return None
            
            self.log_and_store("✅ Certificate files read and verified successfully")
            
            return {
                "certificate": cert_content,
                "private_key": key_content,
                "fullchain": fullchain_content
            }
            
        except Exception as e:
            self.log_and_store(f"❌ File reading error: {e}", "error")
            return None
    
    def _find_alternative_certificates(self):
        acme_dir = self.config["acme"]["cert_dir"]
        
        if not os.path.exists(acme_dir):
            self.log_and_store(f"❌ acme.sh directory not found: {acme_dir}", "error")
            return None
        
        try:
            cert_files = []
            key_files = []
            
            for filename in os.listdir(acme_dir):
                filepath = os.path.join(acme_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                
                if self._is_certificate_file(filepath):
                    cert_files.append(filepath)
                    self.log_and_store(f"🔍 Found certificate file: {filename}")
                
                elif self._is_key_file(filepath):
                    key_files.append(filepath)
                    self.log_and_store(f"🔍 Found key file: {filename}")
            
            self.log_and_store(f"📊 Found certificates: {len(cert_files)}, keys: {len(key_files)}")
            
            for cert_file in cert_files:
                for key_file in key_files:
                    with open(cert_file, 'r') as f:
                        cert_content = f.read().strip()
                    with open(key_file, 'r') as f:
                        key_content = f.read().strip()
                    
                    if self._verify_cert_key_match(cert_content, key_content):
                        self.log_and_store(f"✅ Found matching pair!")
                        self.log_and_store(f"   Certificate: {os.path.basename(cert_file)}")
                        self.log_and_store(f"   Key: {os.path.basename(key_file)}")
                        
                        fullchain_content = cert_content
                        ca_file = os.path.join(acme_dir, "ca.cer")
                        if os.path.exists(ca_file):
                            with open(ca_file, 'r') as f:
                                ca_content = f.read().strip()
                            fullchain_content = cert_content + "\n" + ca_content
                            self.log_and_store("✅ Added CA certificate to fullchain")
                        
                        return {
                            "certificate": cert_content,
                            "private_key": key_content,
                            "fullchain": fullchain_content
                        }
            
            self.log_and_store("❌ No matching pairs found among alternative files", "error")
            return None
            
        except Exception as e:
            self.log_and_store(f"❌ Alternative files search error: {e}", "error")
            return None
    
    def _is_certificate_file(self, filepath):
        try:
            result = subprocess.run([
                'openssl', 'x509', '-in', filepath, '-noout', '-subject'
            ], capture_output=True, text=True, timeout=10)
            return result.returncode == 0 and self.config["storage"]["domain"] in result.stdout
        except:
            return False
    
    def _is_key_file(self, filepath):
        try:
            result_rsa = subprocess.run([
                'openssl', 'rsa', '-in', filepath, '-noout', '-check'
            ], capture_output=True, text=True, timeout=10)
            
            if result_rsa.returncode == 0:
                return True
            
            result_pkey = subprocess.run([
                'openssl', 'pkey', '-in', filepath, '-noout'
            ], capture_output=True, text=True, timeout=10)
            
            return result_pkey.returncode == 0
        except:
            return False
    
    def _verify_cert_key_match(self, cert_content, key_content):
        try:
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt') as tmp_cert:
                tmp_cert.write(cert_content)
                tmp_cert_path = tmp_cert.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as tmp_key:
                tmp_key.write(key_content)
                tmp_key_path = tmp_key.name
            
            cert_result = subprocess.run([
                'openssl', 'x509', '-noout', '-modulus', '-in', tmp_cert_path
            ], capture_output=True, text=True, timeout=15)
            
            key_result = subprocess.run([
                'openssl', 'rsa', '-noout', '-modulus', '-in', tmp_key_path
            ], capture_output=True, text=True, timeout=15)
            
            os.unlink(tmp_cert_path)
            os.unlink(tmp_key_path)
            
            if cert_result.returncode == 0 and key_result.returncode == 0:
                return cert_result.stdout.strip() == key_result.stdout.strip()
                
        except Exception:
            pass
            
        return False
    
    def upload_certificate_to_storage(self, cert_data):
        url = f"{self.config['selectel']['storage_api_url']}/v2/ssl"
        
        headers = {
            "X-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        
        cert_content = cert_data["certificate"].strip()
        key_content = cert_data["private_key"].strip()
        
        final_key = self._convert_rsa_to_pkcs8(key_content)
        
        payload = {
            "name": f"{self.config['storage']['cert_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "certificate": cert_content,
            "private_key": final_key
        }
        
        try:
            self.log_and_store("📤 Uploading certificate to Object Storage...")
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code in [200, 201]:
                cert_info = response.json()
                cert_id = cert_info.get("id")
                self.log_and_store(f"🎉 SUCCESS! Certificate uploaded (ID: {cert_id})")
                return cert_id
            else:
                self.log_and_store(f"❌ Upload error: {response.status_code}", "error")
                self.log_and_store(f"Response: {response.text}", "error")
                return None
                
        except Exception as e:
            self.log_and_store(f"❌ Upload exception: {e}", "error")
            return None
    
    def _convert_rsa_to_pkcs8(self, key_content):
        if "-----BEGIN RSA PRIVATE KEY-----" not in key_content:
            return key_content
        
        try:
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as tmp_rsa:
                tmp_rsa.write(key_content)
                tmp_rsa_path = tmp_rsa.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key') as tmp_pkcs8:
                tmp_pkcs8_path = tmp_pkcs8.name
            
            result = subprocess.run([
                'openssl', 'pkcs8', '-topk8', '-inform', 'PEM', '-outform', 'PEM',
                '-nocrypt', '-in', tmp_rsa_path, '-out', tmp_pkcs8_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                with open(tmp_pkcs8_path, 'r') as f:
                    converted_key = f.read().strip()
                self.log_and_store("🔧 Key converted to PKCS#8 format")
                return converted_key
            
            os.unlink(tmp_rsa_path)
            os.unlink(tmp_pkcs8_path)
            
        except Exception as e:
            self.log_and_store(f"⚠️ Key conversion error: {e}", "warning")
        
        return key_content
    
    def wait_for_certificate_activation(self, cert_id):
        url = f"{self.config['selectel']['storage_api_url']}/v2/ssl"
        headers = {
            "X-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        
        max_attempts = 30
        wait_seconds = 10
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    certificates = response.json()
                    
                    for cert in certificates:
                        if cert.get("id") == cert_id:
                            badge_status = cert.get("badge_status", "unknown")
                            
                            if badge_status.lower() == "active":
                                self.log_and_store(f"🎉 Certificate activated!")
                                return True
                            elif badge_status.lower() == "pending":
                                self.log_and_store(f"⏳ Waiting for activation... (attempt {attempt}/{max_attempts})")
                                import time
                                time.sleep(wait_seconds)
                                continue
                            else:
                                self.log_and_store(f"❌ Unexpected status: {badge_status}", "error")
                                return False
                    
                    self.log_and_store(f"❌ Certificate {cert_id} not found!", "error")
                    return False
                    
            except Exception as e:
                if attempt == max_attempts:
                    self.log_and_store(f"❌ Status check error: {e}", "error")
                    return False
                
                import time
                time.sleep(wait_seconds)
        
        self.log_and_store("❌ Activation timeout exceeded", "error")
        return False
    
    def delete_old_certificate(self, cert_id):
        if not self.token:
            return False
        
        url = f"{self.config['selectel']['storage_api_url']}/v2/ssl/{cert_id}"
        headers = {
            "X-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            
            if response.status_code in [200, 204, 404]:
                self.log_and_store("✅ Old certificate deleted")
                return True
            else:
                self.log_and_store(f"⚠️ Deletion error: {response.status_code}", "warning")
                return False
                
        except Exception as e:
            self.log_and_store(f"⚠️ Deletion error: {e}", "warning")
            return False
    
    def install_certificates_locally(self, cert_data):
        self.log_and_store("📋 Installing certificates locally...")
        
        try:
            backup_suffix = datetime.now().strftime(".backup-%Y%m%d-%H%M%S")
            for path in [self.config["install"]["cert_path"], 
                        self.config["install"]["key_path"],
                        self.config["install"]["fullchain_path"]]:
                if os.path.exists(path):
                    shutil.copy2(path, path + backup_suffix)
            
            for path in [self.config["install"]["cert_path"], 
                        self.config["install"]["key_path"], 
                        self.config["install"]["fullchain_path"]]:
                os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(self.config["install"]["cert_path"], 'w') as f:
                f.write(cert_data["certificate"])
            
            with open(self.config["install"]["key_path"], 'w') as f:
                f.write(cert_data["private_key"])
            
            with open(self.config["install"]["fullchain_path"], 'w') as f:
                f.write(cert_data["fullchain"])
            
            os.chmod(self.config["install"]["key_path"], 0o600)
            os.chmod(self.config["install"]["cert_path"], 0o644)
            os.chmod(self.config["install"]["fullchain_path"], 0o644)
            
            self.log_and_store("✅ Certificates installed locally")
            return True
            
        except Exception as e:
            self.log_and_store(f"❌ Local installation error: {e}", "error")
            return False
    
    def run_renewal(self):
        self.log_and_store("=== Starting SSL certificate renewal ===")
        
        try:
            if not self.get_iam_token():
                return False
            
            initial_cert = self.get_current_certificate_info()
            
            if not self.renew_certificate_with_acme():
                self.log_and_store("❌ Failed to renew certificate via acme.sh", "error")
                return False
            
            cert_data = self.read_certificate_files()
            if not cert_data:
                self.log_and_store("❌ Failed to read certificate files", "error")
                return False
            
            if initial_cert:
                current_cert_id = initial_cert.get('id', self.config["storage"]["current_cert_id"])
                self.delete_old_certificate(current_cert_id)
            
            cert_id = self.upload_certificate_to_storage(cert_data)
            if not cert_id:
                self.log_and_store("❌ Failed to upload certificate to Object Storage", "error")
                return False
            
            if not self.wait_for_certificate_activation(cert_id):
                self.log_and_store("❌ Certificate activation failed", "error")
                return False
            
            if not self.install_certificates_locally(cert_data):
                self.log_and_store("❌ Failed to install certificates locally", "error")
            
            new_cert = self.get_current_certificate_info()
            if self.telegram and self.config["telegram"]["send_success"] and new_cert:
                self.telegram.send_success(
                    domain=self.config['storage']['domain'],
                    cert_id=new_cert.get('id', cert_id),
                    expires_at=new_cert.get('not_after', 'unknown')
                )
            
            self.log_and_store("🎉 Certificate renewal completed SUCCESSFULLY!")
            return True
            
        except Exception as e:
            self.log_and_store(f"❌ Critical error: {e}", "error")
            
            if self.telegram and self.config["telegram"]["send_errors"]:
                self.telegram.send_error(
                    domain=self.config['storage']['domain'],
                    error=str(e),
                    step="Critical error"
                )
            
            return False


def main():
    print("=== SSL Certificate Renewal for Selectel Object Storage ===")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    manager = SSLCertificateManager()
    
    success = manager.run_renewal()
    
    if success:
        print("✅ Certificate renewal completed successfully!")
        sys.exit(0)
    else:
        print("❌ Certificate renewal failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()