"""
Gmail Verification Code Monitor
Runs on VPS: python3 gmail_monitor.py
Polls Gmail IMAP for new Xiaomi verification codes
and prints them to stdout (use with cron or as background process)
"""

import imaplib
import email as email_lib
import re
import time
import json
from datetime import datetime

GMAIL_USER = "yayblue3@gmail.com"
GMAIL_APP_PASS = "iueambozpuihsloc"
POLL_INTERVAL = 10  # seconds
seen_codes = set()


def check_xiaomi_codes():
    """Check for new Xiaomi verification codes"""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        mail.select("INBOX")
        
        since = datetime.now().strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{since}" FROM "xiaomi")')
        
        if status != "OK" or not messages[0]:
            mail.logout()
            return []
        
        results = []
        msg_ids = messages[0].split()
        
        for msg_id in reversed(msg_ids[-10:]):
            status, data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            
            msg = email_lib.message_from_bytes(data[0][1])
            subject = msg.get("Subject", "")
            msg_id_header = msg.get("Message-ID", str(msg_id))
            
            if msg_id_header in seen_codes:
                continue
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() in ("text/plain", "text/html"):
                        try:
                            body += part.get_payload(decode=True).decode(errors="replace")
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors="replace")
                except:
                    pass
            
            # Extract 6-digit code
            codes = re.findall(r'\b(\d{6})\b', body)
            if codes:
                seen_codes.add(msg_id_header)
                results.append({
                    "code": codes[0],
                    "subject": subject[:80],
                    "date": msg.get("Date", ""),
                })
        
        mail.logout()
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        return []


def main():
    print(f"📱 Gmail Verification Code Monitor")
    print(f"   Polling {GMAIL_USER} every {POLL_INTERVAL}s")
    print(f"   Press Ctrl+C to stop\n")
    
    while True:
        try:
            codes = check_xiaomi_codes()
            for c in codes:
                print(f"\n{'='*50}")
                print(f"🔐 XIAOMI VERIFICATION CODE: {c['code']}")
                print(f"   Subject: {c['subject']}")
                print(f"   Date: {c['date']}")
                print(f"{'='*50}\n")
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    main()
