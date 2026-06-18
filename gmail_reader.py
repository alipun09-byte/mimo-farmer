"""
Gmail Reader — IMAP reader for verification codes.
Supports Gmail with App Password authentication.
"""

import imaplib
import email
from email.header import decode_header
import re
import time
import json

class GmailReader:
    def __init__(self, email_address, app_password):
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
    
    def connect(self):
        """Connect to Gmail IMAP"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.email_address, self.app_password)
            print(f"Connected to Gmail: {self.email_address}")
            return True
        except Exception as e:
            print(f"Gmail connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Gmail IMAP"""
        try:
            self.mail.logout()
            print("Disconnected from Gmail")
        except:
            pass
    
    def wait_for_code(self, sender_filter, max_wait=120, interval=10):
        """Wait for verification code from specific sender"""
        if not self.connect():
            return None
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            code = self._check_inbox(sender_filter)
            if code:
                self.disconnect()
                return code
            time.sleep(interval)
        
        self.disconnect()
        return None
    
    def _check_inbox(self, sender_filter):
        """Check inbox for verification code"""
        try:
            self.mail.select("INBOX")
            
            # Search for unread emails from specific sender
            status, messages = self.mail.search(None, f'(UNSEEN FROM "{sender_filter}")')
            
            if status != "OK":
                return None
            
            for msg_id in messages[0].split():
                status, msg_data = self.mail.fetch(msg_id, "(RFC822)")
                
                if status != "OK":
                    continue
                
                # Parse email
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Get body
                body = self._get_body(msg)
                
                # Extract 6-digit code
                code = self._extract_code(body)
                if code:
                    print(f"Found verification code: {code}")
                    return code
            
            return None
            
        except Exception as e:
            print(f"Inbox check error: {e}")
            return None
    
    def _get_body(self, msg):
        """Extract body from email message"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body += payload.decode(charset, errors="ignore")
                
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_content = payload.decode(charset, errors="ignore")
                        # Simple HTML to text conversion
                        text = re.sub(r'<[^>]+>', ' ', html_content)
                        body += text
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="ignore")
        
        return body
    
    def _extract_code(self, text):
        """Extract 6-digit verification code"""
        patterns = [
            r'\b(\d{6})\b',
            r'code:\s*(\d{6})',
            r'verification\s+code:\s*(\d{6})',
            r'is\s+(\d{6})',
            r'Your\s+code\s+is\s+(\d{6})',
            r'Kode\s+verifikasi\s+anda\s+adalah\s+(\d{6})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def get_all_messages(self, sender_filter=None, limit=10):
        """Get all messages (for debugging)"""
        if not self.connect():
            return []
        
        try:
            self.mail.select("INBOX")
            
            if sender_filter:
                status, messages = self.mail.search(None, f'(FROM "{sender_filter}")')
            else:
                status, messages = self.mail.search(None, "ALL")
            
            if status != "OK":
                return []
            
            msg_list = []
            for msg_id in messages[0].split()[-limit:]:
                status, msg_data = self.mail.fetch(msg_id, "(RFC822)")
                
                if status == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if encoding:
                        subject = subject.decode(encoding)
                    
                    msg_list.append({
                        "from": msg["From"],
                        "subject": subject,
                        "date": msg["Date"]
                    })
            
            self.disconnect()
            return msg_list
            
        except Exception as e:
            print(f"Get messages error: {e}")
            self.disconnect()
            return []

if __name__ == "__main__":
    # Test Gmail reader
    reader = GmailReader(
        email_address="yayblue3@gmail.com",
        app_password="iueambozpuihsloc"
    )
    
    print("Testing Gmail connection...")
    if reader.connect():
        messages = reader.get_all_messages(limit=5)
        print(f"Found {len(messages)} messages:")
        for msg in messages:
            print(f"  From: {msg['from']}")
            print(f"  Subject: {msg['subject']}")
            print(f"  Date: {msg['date']}")
            print()
        reader.disconnect()
