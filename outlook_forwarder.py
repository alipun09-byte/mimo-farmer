"""
Outlook Email Generator + Gmail Polling (Forwarding Method)
Flow: Generate random@outlook.com → Forward to Gmail → Poll Gmail IMAP
"""

import random
import string
import time
import imaplib
import email
from email.header import decode_header

class OutlookForwarder:
    def __init__(self, gmail_user, gmail_app_password):
        self.gmail_user = gmail_user
        self.gmail_password = gmail_app_password
        self.imap_server = "imap.gmail.com"
        
    def generate_outlook_email(self, prefix=None):
        """Generate random Outlook email address"""
        if not prefix:
            prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{prefix}@outlook.com"
    
    def wait_for_verification_code(self, target_email, timeout=120):
        """
        Poll Gmail IMAP for verification code sent to target_email
        (email forwarded from Outlook to Gmail)
        """
        print(f"[📧] Polling Gmail untuk kode verifikasi ke {target_email}...")
        
        start = time.time()
        mail = None
        
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.gmail_user, self.gmail_password)
            mail.select("INBOX")
            
            while (time.time() - start) < timeout:
                # Search for emails from Xiaomi/Mi
                status, messages = mail.search(None, '(FROM "mi.com" OR FROM "xiaomi.com")')
                
                if status != "OK" or not messages[0]:
                    time.sleep(3)
                    continue
                
                # Get latest 5 emails
                msg_ids = messages[0].split()
                for msg_id in msg_ids[-5:]:
                    status, msg_data = mail.fetch(msg_id, "(RFC822)")
                    
                    if status != "OK":
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Get email subject
                            subject = self._decode_header(msg["Subject"])
                            
                            # Get email body
                            body = self._get_email_body(msg)
                            
                            # Extract verification code
                            code = self._extract_code(body)
                            
                            if code:
                                print(f"[✅] Kode ditemukan: {code}")
                                return code
                
                print(f"[⏳] Belum ada kode... ({int(time.time() - start)}s)")
                time.sleep(5)
            
            print(f"[❌] Timeout {timeout}s — kode tidak ditemukan")
            return None
            
        except Exception as e:
            print(f"[❌] Error polling Gmail: {e}")
            return None
        finally:
            if mail:
                try:
                    mail.logout()
                except:
                    pass
    
    def _decode_header(self, header_text):
        """Decode email header"""
        if not header_text:
            return ""
        decoded = decode_header(header_text)
        return ''.join([
            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
            for part, encoding in decoded
        ])
    
    def _get_email_body(self, msg):
        """Extract email body text"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        return body
    
    def _extract_code(self, text):
        """Extract 6-digit verification code from email"""
        import re
        # Pattern: 6 digits in a row
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
        return None


# === USAGE EXAMPLE ===
if __name__ == "__main__":
    # Gmail credentials (for polling forwarded emails)
    GMAIL_USER = "yayblue3@gmail.com"
    GMAIL_APP_PASSWORD = "iueambozpuihsloc"
    
    forwarder = OutlookForwarder(GMAIL_USER, GMAIL_APP_PASSWORD)
    
    # Generate Outlook email
    outlook_email = forwarder.generate_outlook_email()
    print(f"[📧] Generated: {outlook_email}")
    print(f"[📧] Email ini akan di-forward ke Gmail lu.")
    print(f"[📧] Registrasi ke Xiaomi pake email ini...")
    
    # Simulate waiting for code
    print("\n[⏳] Tunggu kode verifikasi (max 120 detik)...")
    code = forwarder.wait_for_verification_code(outlook_email, timeout=120)
    
    if code:
        print(f"\n[✅] Kode berhasil ditangkap: {code}")
    else:
        print(f"\n[❌] Gagal dapat kode dalam 120 detik")
