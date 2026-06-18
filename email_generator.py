"""
Email Generator — Generate temporary emails from multiple services.
Supports: emailnator.com, generator.email, internxt.com
"""

import random
import string
import time
import requests
import json
import re

SERVICES = {
    "emailnator": "https://www.emailnator.com",
    "generator_email": "https://generator.email",
    "internxt": "https://internxt.com/temporary-email"
}

class EmailGenerator:
    def __init__(self, service="emailnator"):
        self.service = service
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
    
    def generate_email(self, prefix=None):
        """Generate random email address"""
        if not prefix:
            prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        if self.service == "emailnator":
            return self._generate_emailnator(prefix)
        elif self.service == "generator_email":
            return self._generate_generator_email(prefix)
        elif self.service == "internxt":
            return self._generate_internxt(prefix)
        else:
            raise ValueError(f"Unknown service: {self.service}")
    
    def get_inbox(self, email_address):
        """Get inbox for email address"""
        if self.service == "emailnator":
            return self._get_inbox_emailnator(email_address)
        elif self.service == "generator_email":
            return self._get_inbox_generator_email(email_address)
        elif self.service == "internxt":
            return self._get_inbox_internxt(email_address)
        else:
            raise ValueError(f"Unknown service: {self.service}")
    
    def wait_for_code(self, email_address, max_wait=120, interval=5):
        """Wait for verification code in inbox"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            messages = self.get_inbox(email_address)
            for msg in messages:
                code = self._extract_code(msg.get("body", ""))
                if code:
                    return code
            time.sleep(interval)
        return None
    
    def _extract_code(self, text):
        """Extract 6-digit verification code"""
        patterns = [
            r'\b(\d{6})\b',
            r'code:\s*(\d{6})',
            r'verification\s+code:\s*(\d{6})',
            r'is\s+(\d{6})'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _generate_emailnator(self, prefix):
        """Generate email using emailnator.com"""
        try:
            # EmailNator uses an API endpoint
            response = self.session.post(
                "https://www.emailnator.com/generate-email",
                headers={
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                json={"email": ["dotGmail"]}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "email" in data:
                    return {
                        "email": data["email"],
                        "token": data.get("token", ""),
                        "service": "emailnator"
                    }
            
            # Fallback: generate random email
            return {
                "email": f"{prefix}@emailnator.com",
                "token": "",
                "service": "emailnator"
            }
            
        except Exception as e:
            print(f"EmailNator error: {e}")
            return {
                "email": f"{prefix}@emailnator.com",
                "token": "",
                "service": "emailnator"
            }
    
    def _generate_generator_email(self, prefix):
        """Generate email using generator.email"""
        try:
            response = self.session.get("https://generator.email/")
            if response.status_code == 200:
                # Extract email from page
                match = re.search(r'id="email_ch_text"[^>]*>([^<]+)', response.text)
                if match:
                    return {
                        "email": match.group(1).strip(),
                        "token": "",
                        "service": "generator_email"
                    }
            
            return {
                "email": f"{prefix}@generator.email",
                "token": "",
                "service": "generator_email"
            }
            
        except Exception as e:
            print(f"Generator.email error: {e}")
            return {
                "email": f"{prefix}@generator.email",
                "token": "",
                "service": "generator_email"
            }
    
    def _generate_internxt(self, prefix):
        """Generate email using internxt.com"""
        try:
            response = self.session.get("https://internxt.com/temporary-email")
            if response.status_code == 200:
                # Internxt generates email on page load
                match = re.search(r'data-email="([^"]+)"', response.text)
                if match:
                    return {
                        "email": match.group(1),
                        "token": "",
                        "service": "internxt"
                    }
            
            return {
                "email": f"{prefix}@internxt.com",
                "token": "",
                "service": "internxt"
            }
            
        except Exception as e:
            print(f"Internxt error: {e}")
            return {
                "email": f"{prefix}@internxt.com",
                "token": "",
                "service": "internxt"
            }
    
    def _get_inbox_emailnator(self, email_address):
        """Get inbox from emailnator.com"""
        try:
            response = self.session.post(
                "https://www.emailnator.com/inbox",
                headers={
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                json={"email": email_address}
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = []
                for msg in data.get("messageData", []):
                    messages.append({
                        "from": msg.get("from", ""),
                        "subject": msg.get("subject", ""),
                        "body": msg.get("message", ""),
                        "time": msg.get("time", "")
                    })
                return messages
            
            return []
            
        except Exception as e:
            print(f"EmailNator inbox error: {e}")
            return []
    
    def _get_inbox_generator_email(self, email_address):
        """Get inbox from generator.email"""
        try:
            # Extract domain from email
            domain = email_address.split("@")[1]
            username = email_address.split("@")[0]
            
            response = self.session.get(f"https://generator.email/inbox/{username}")
            if response.status_code == 200:
                # Parse messages from HTML
                messages = []
                matches = re.findall(r'class="email_item".*?</div>', response.text, re.DOTALL)
                for match in matches:
                    from_match = re.search(r'class="email_from".*?>([^<]+)', match)
                    subject_match = re.search(r'class="email_subject".*?>([^<]+)', match)
                    body_match = re.search(r'class="email_body".*?>(.*?)</div>', match, re.DOTALL)
                    
                    messages.append({
                        "from": from_match.group(1).strip() if from_match else "",
                        "subject": subject_match.group(1).strip() if subject_match else "",
                        "body": body_match.group(1).strip() if body_match else "",
                        "time": ""
                    })
                
                return messages
            
            return []
            
        except Exception as e:
            print(f"Generator.email inbox error: {e}")
            return []
    
    def _get_inbox_internxt(self, email_address):
        """Get inbox from internxt.com"""
        try:
            # Internxt uses API
            response = self.session.get(
                f"https://internxt.com/api/temporary-email/inbox",
                params={"email": email_address}
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = []
                for msg in data.get("messages", []):
                    messages.append({
                        "from": msg.get("from", ""),
                        "subject": msg.get("subject", ""),
                        "body": msg.get("text", "") or msg.get("html", ""),
                        "time": msg.get("createdAt", "")
                    })
                return messages
            
            return []
            
        except Exception as e:
            print(f"Internxt inbox error: {e}")
            return []

def generate_email(service="emailnator", prefix=None):
    """Quick function to generate email"""
    gen = EmailGenerator(service=service)
    return gen.generate_email(prefix)

def get_verification_code(email_address, service="emailnator", max_wait=120):
    """Quick function to get verification code"""
    gen = EmailGenerator(service=service)
    return gen.wait_for_code(email_address, max_wait=max_wait)

if __name__ == "__main__":
    # Test all services
    services = ["emailnator", "generator_email", "internxt"]
    for service in services:
        print(f"\n=== Testing {service} ===")
        gen = EmailGenerator(service=service)
        result = gen.generate_email()
        print(f"Generated: {result['email']}")
        print(f"Service: {result['service']}")
