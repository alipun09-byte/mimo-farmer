"""
Main Orchestrator — Xiaomi Mimo Auto-Registration System.
Coordinates all modules for mass account creation.
"""

import asyncio
import json
import os
import sys
import time
import random
from datetime import datetime
from typing import Dict, List, Optional

from email_generator import EmailGenerator
from gmail_reader import GmailReader
from captcha_solver import CaptchaSolver
from proxy_manager import ProxyManager
from xiaomi_register import XiaomiRegister
from mimo_client import MimoClient

class MimoFarmer:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.output_dir = self.config.get("output_dir", "./output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize modules
        self.email_generator = EmailGenerator(service="emailnator")
        self.gmail_reader = GmailReader(
            email_address=self.config["gmail_register"]["email"],
            app_password=self.config["gmail_register"]["app_password"]
        )
        self.captcha_solver = CaptchaSolver(
            mode=self.config["captcha"]["mode"],
            boterdrop_url=self.config["captcha"].get("boterdrop_url", "http://localhost:8000"),
            twocaptcha_api_key=self.config["captcha"].get("twocaptcha_api_key")
        )
        self.proxy_manager = ProxyManager(proxies=self.config.get("proxies", []))
        
        # Load proxies from file if exists
        if os.path.exists("proxies.txt"):
            self.proxy_manager.load_from_file("proxies.txt")
        
        # Stats
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "api_keys": []
        }
        
        # Log file
        self.log_file = os.path.join(self.output_dir, f"registration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    async def run(self):
        """Main execution loop"""
        print(f"Starting Mimo Farmer - {self.config['count']} accounts")
        print(f"Output directory: {self.output_dir}")
        print(f"Log file: {self.log_file}")
        print("-" * 50)
        
        start_time = time.time()
        
        for i in range(self.config["count"]):
            print(f"\n[{i+1}/{self.config['count']}] Starting registration...")
            
            try:
                result = await self._register_account(i)
                
                if result:
                    self.stats["success"] += 1
                    self.stats["api_keys"].append(result)
                    self._log_result(result, "SUCCESS")
                else:
                    self.stats["failed"] += 1
                    self._log_result({"account": i}, "FAILED")
                
            except Exception as e:
                print(f"Account {i+1} failed: {e}")
                self.stats["failed"] += 1
                self._log_result({"account": i, "error": str(e)}, "ERROR")
            
            self.stats["total"] += 1
            
            # Delay between registrations
            if i < self.config["count"] - 1:
                delay = random.randint(self.config["delay_min"], self.config["delay_max"])
                print(f"Waiting {delay} seconds before next registration...")
                time.sleep(delay)
        
        # Final report
        elapsed = time.time() - start_time
        print("\n" + "=" * 50)
        print("FARMING COMPLETE")
        print(f"Total: {self.stats['total']}")
        print(f"Success: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Time: {elapsed:.1f} seconds")
        print("=" * 50)
        
        # Save API keys to files
        self._save_api_keys()
    
    async def _register_account(self, account_index: int) -> Optional[Dict]:
        """Register a single account"""
        result = {
            "account_index": account_index,
            "timestamp": datetime.now().isoformat(),
            "email": None,
            "password": None,
            "sso_cookie": None,
            "api_key": None,
            "plan_code": None
        }
        
        # Generate email
        print("Generating email...")
        email_data = self.email_generator.generate_email()
        email = email_data["email"]
        password = self.config["default_password"]
        result["email"] = email
        result["password"] = password
        print(f"Email: {email}")
        
        # Get proxy
        proxy = self.proxy_manager.get_proxy()
        if proxy:
            print(f"Using proxy: {proxy}")
        
        # Step 1: Get registration data via Playwright
        print("Step 1: Getting registration data...")
        register = XiaomiRegister(headless=self.config["playwright"]["headless"])
        await register.start()
        
        try:
            reg_data = await register.get_registration_data(email, password)
            
            if not reg_data:
                print("Failed to get registration data")
                return None
            
            print(f"Got _sign: {reg_data.get('_sign', 'N/A')[:20]}...")
            
            # Step 2: Solve captcha
            print("Step 2: Solving captcha...")
            captcha_token = self.captcha_solver.solve_recaptcha_enterprise(
                sitekey="6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4",
                page_url="https://account.xiaomi.com/pass/register"
            )
            
            if not captcha_token:
                print("Failed to solve captcha")
                return None
            
            print("Captcha solved!")
            
            # Step 3: Send registration email
            print("Step 3: Sending registration email...")
            # This would be done via requests with the captured encrypted values
            # For now, we'll simulate the flow
            
            # Step 4: Wait for verification code
            print("Step 4: Waiting for verification code...")
            code = self.gmail_reader.wait_for_code(
                sender_filter="account.xiaomi.com",
                max_wait=120,
                interval=10
            )
            
            if not code:
                print("Failed to get verification code")
                return None
            
            print(f"Got verification code: {code}")
            
            # Step 5: Complete registration
            print("Step 5: Completing registration...")
            # This would verify the code and complete registration
            
            # Step 6: Follow SSO redirect
            print("Step 6: Following SSO redirect...")
            sso_cookie = await register.follow_sso_redirect()
            
            if not sso_cookie:
                print("Failed to get SSO cookie")
                return None
            
            result["sso_cookie"] = sso_cookie
            print(f"Got SSO cookie: {sso_cookie[:20]}...")
            
            # Step 7: Bind email
            print("Step 7: Binding email...")
            bind_email = self.config["gmail_bind"]["email"]
            mimo_client = MimoClient(sso_cookie=sso_cookie, proxy=proxy)
            
            bind_result = mimo_client.bind_email(bind_email)
            
            if "error" in bind_result:
                print(f"Bind email failed: {bind_result['error']}")
                return None
            
            # Step 8: Wait for bind verification code
            print("Step 8: Waiting for bind verification code...")
            bind_code = self.gmail_reader.wait_for_code(
                sender_filter="xiaomimimo.com",
                max_wait=120,
                interval=10
            )
            
            if not bind_code:
                print("Failed to get bind verification code")
                return None
            
            print(f"Got bind code: {bind_code}")
            
            # Step 9: Confirm bind
            print("Step 9: Confirming bind...")
            confirm_result = mimo_client.confirm_bind(bind_email, bind_code)
            
            if "error" in confirm_result:
                print(f"Confirm bind failed: {confirm_result['error']}")
                return None
            
            print("Email bound successfully!")
            
            # Step 10: Wait for plan activation
            print("Step 10: Waiting for plan activation...")
            if not mimo_client.wait_for_plan_activation(max_wait=60, interval=5):
                print("Plan activation timeout")
                return None
            
            # Step 11: Create API key
            print("Step 11: Creating API key...")
            api_key_result = mimo_client.create_apikey()
            
            if "error" in api_key_result:
                print(f"Create API key failed: {api_key_result['error']}")
                return None
            
            result["api_key"] = api_key_result.get("apiKey") or api_key_result.get("key")
            result["plan_code"] = mimo_client.get_plan_detail().get("planCode")
            
            print(f"API key created: {result['api_key'][:20]}...")
            
            return result
            
        finally:
            await register.stop()
    
    def _log_result(self, result: Dict, status: str):
        """Log registration result"""
        log_entry = f"[{datetime.now().isoformat()}] {status}: {json.dumps(result)}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def _save_api_keys(self):
        """Save API keys to files"""
        # Group by plan code
        plan_groups = {}
        
        for key_data in self.stats["api_keys"]:
            plan = key_data.get("plan_code") or "no_plan"
            if plan not in plan_groups:
                plan_groups[plan] = []
            plan_groups[plan].append(key_data)
        
        # Save to plan-specific files
        for plan, keys in plan_groups.items():
            filename = os.path.join(self.output_dir, f"apikeys_{plan}.txt")
            with open(filename, 'w') as f:
                for key in keys:
                    line = f"{key['email']}|{key['password']}|{key['api_key']}|{plan}\n"
                    f.write(line)
            print(f"Saved {len(keys)} keys to {filename}")
        
        # Save full details to JSON
        json_file = os.path.join(self.output_dir, f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_file, 'w') as f:
            json.dump(self.stats["api_keys"], f, indent=2)
        print(f"Full details saved to {json_file}")

async def main():
    """Main entry point"""
    farmer = MimoFarmer()
    await farmer.run()

if __name__ == "__main__":
    asyncio.run(main())
