"""
Xiaomi Mimo Auto-Registration v5 — Fully Automated
Jalankan: py auto_register.py

Flow:
1. Generate email (custom domain / gmail dot trick)
2. Open Playwright browser (visible, non-headless)
3. Auto-fill form + submit
4. reCAPTCHA: auto-pass on residential IP
5. Poll Gmail IMAP for verification code (auto-forward)
6. Auto-enter code + complete registration
7. Auto-login + create API key
8. Save to keys.json

Dependencies:
  pip install playwright requests
  playwright install chromium
"""

import asyncio
import json
import os
import re
import sys
import time
import random
import string
import imaplib
import email as email_lib
from pathlib import Path
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────
COUNT = 50
PASSWORD = "PelerKuda2026!"
REGION = "SG"

# Email provider: "custom_domain" | "gmail" | "outlook"
EMAIL_PROVIDER = "custom_domain"
DOMAIN = "yaybgent.web.id"

# Gmail (for polling forwarded verification codes)
GMAIL_USER = "yayblue3@gmail.com"
GMAIL_APP_PASS = "iueambozpuihsloc"

# Output
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
KEYS_FILE = Path("keys.json")

# ─── EMAIL GENERATORS ─────────────────────────────────────────
def generate_email():
    """Generate email based on provider setting."""
    if EMAIL_PROVIDER == "custom_domain":
        prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f"{prefix}@{DOMAIN}"
    elif EMAIL_PROVIDER == "outlook":
        prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{prefix}@outlook.com"
    else:  # gmail
        base = "yayblue3"
        insert_positions = list(range(1, len(base)))
        num_dots = random.randint(1, min(3, len(insert_positions)))
        positions = sorted(random.sample(insert_positions, num_dots))
        dotted = ""
        for i, c in enumerate(base):
            if i in positions:
                dotted += "."
            dotted += c
        return f"{dotted}@gmail.com"


# ─── GMAIL IMAP POLLING ──────────────────────────────────────
def poll_verification_code(max_wait=180):
    """
    Poll Gmail IMAP for Xiaomi verification code.
    Searches ALL recent emails, filters locally.
    Returns 6-digit code or None.
    """
    print("    📧 Polling Gmail IMAP for verification code...")
    
    start_time = time.time()
    
    while (time.time() - start_time) < max_wait:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASS)
            mail.select("INBOX")
            
            since = datetime.now().strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{since}")')
            
            if status == "OK" and messages[0]:
                msg_ids = messages[0].split()
                
                for msg_id in reversed(msg_ids[-10:]):
                    status, data = mail.fetch(msg_id, "(RFC822)")
                    if status != "OK":
                        continue
                    
                    msg = email_lib.message_from_bytes(data[0][1])
                    subject = msg.get("Subject", "")
                    fr = msg.get("From", "").lower()
                    
                    # Filter: xiaomi/mimo emails OR forwarded from custom domain
                    is_xiaomi = "xiaomi" in fr or "mimo" in fr
                    is_domain_fwd = DOMAIN.split(".")[0] in fr or "cloudflare" in fr or "forward" in fr
                    is_verification = any(kw in subject.lower() for kw in ["verification", "verifikasi", "code", "account", "mi account"])
                    
                    if not (is_xiaomi or is_domain_fwd or is_verification):
                        continue
                    
                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            if ct in ("text/plain", "text/html"):
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
                        code = codes[0]
                        print(f"    ✅ Code found: {code}")
                        mail.logout()
                        return code
            
            mail.logout()
            
        except Exception as e:
            print(f"    ⚠️ Poll error: {e}")
        
        elapsed = int(time.time() - start_time)
        if elapsed % 15 == 0:
            print(f"    ⏳ Waiting... ({elapsed}s)")
        
        time.sleep(5)
    
    print(f"    ❌ Timeout after {max_wait}s")
    return None


# ─── SAVE KEYS ────────────────────────────────────────────────
def save_key(email, password, api_key, provider):
    """Save successful registration to keys.json."""
    keys = []
    if KEYS_FILE.exists():
        with open(KEYS_FILE, "r") as f:
            keys = json.load(f)
    
    # Check duplicate
    existing_emails = [k["email"] for k in keys]
    if email in existing_emails:
        return
    
    entry = {
        "email": email,
        "password": password,
        "api_key": api_key,
        "provider": provider,
        "registered_at": datetime.now().isoformat(),
    }
    keys.append(entry)
    
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)
    
    print(f"    💾 Saved to keys.json ({len(keys)} total)")


# ─── REGISTER ACCOUNT ─────────────────────────────────────────
async def register_account(page, account_num):
    """Register 1 Xiaomi Mimo account — fully automated."""
    
    email_addr = generate_email()
    
    print(f"\n{'='*60}")
    print(f"  ACCOUNT #{account_num} | {email_addr}")
    print(f"{'='*60}")
    
    # Step 1: Navigate
    print("  [1/8] Navigating to Mimo register...")
    try:
        await page.goto("https://platform.xiaomimimo.com/login", timeout=30000)
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  ❌ Navigation error: {e}")
        return None
    
    # Step 2: Click Sign up
    print("  [2/8] Clicking Sign up...")
    try:
        await page.click("text=Sign up", timeout=10000)
        await page.wait_for_timeout(3000)
    except:
        current = page.url
        if "register" not in current:
            print(f"  ❌ No Sign up button. URL: {current}")
            return None
    
    # Step 3: Fill form
    print("  [3/8] Filling form...")
    try:
        email_input = await page.wait_for_selector("input[name=email], input[type=email]", timeout=5000)
        await email_input.fill(email_addr)
        await page.fill("input[name=password]", PASSWORD)
        await page.fill("input[name=repassword]", PASSWORD)
        
        # Check agreement checkbox
        cb = await page.query_selector("input[type=checkbox]")
        if cb and not await cb.is_checked():
            await cb.check()
        await page.wait_for_timeout(500)
    except Exception as e:
        print(f"  ❌ Form fill error: {e}")
        return None
    
    # Step 4: Click Next
    print("  [4/8] Clicking Next...")
    try:
        await page.click("button:has-text('Next'), button:has-text('Register')", timeout=5000)
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  ❌ Next button error: {e}")
        return None
    
    # Step 5: Handle reCAPTCHA
    print("  [5/8] Handling reCAPTCHA...")
    captcha_solved = False
    
    for frame in page.frames:
        if "recaptcha" in frame.url and "anchor" in frame.url:
            try:
                checkbox = await frame.wait_for_selector("#recaptcha-anchor", timeout=5000)
                if checkbox:
                    await checkbox.click()
                    await page.wait_for_timeout(5000)
                    
                    classes = await frame.evaluate("() => document.getElementById('recaptcha-anchor').className")
                    if "recaptcha-checkbox-checked" in classes:
                        print("  [5/8] ✅ reCAPTCHA auto-passed!")
                        captcha_solved = True
                    else:
                        print("  [5/8] ⚠️ reCAPTCHA challenge appeared!")
                        print("  [5/8] SOLVE CAPTCHA IN BROWSER, waiting 30s...")
                        await asyncio.get_event_loop().run_in_executor(
                            None, lambda: input("  Press Enter after solving captcha... ")
                        )
                        captcha_solved = True
            except:
                pass
    
    if not captcha_solved:
        print("  [5/8] No reCAPTCHA found")
    
    await page.wait_for_timeout(3000)
    
    # Step 6: Email verification code
    body_text = await page.inner_text("body")
    
    if any(kw in body_text.lower() for kw in ["code", "verification", "verify", "sent"]):
        print("  [6/8] Email verification needed!")
        
        code_input = await page.query_selector("input[name=code], input[type=tel], input[placeholder*='code'], input[placeholder*='Code']")
        if code_input:
            # Auto-poll Gmail
            code = poll_verification_code(max_wait=120)
            
            if not code:
                print("  [6/8] ❌ Auto-poll failed.")
                code = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("  Enter verification code manually: ").strip()
                )
            
            if code and len(code) == 6:
                await code_input.fill(code)
                await page.wait_for_timeout(500)
                
                btn = await page.query_selector("button:has-text('Verify'), button:has-text('Confirm'), button:has-text('Submit'), button[type=submit]")
                if btn:
                    await btn.click()
                else:
                    await page.keyboard.press("Enter")
                
                await page.wait_for_timeout(5000)
                print("  [6/8] ✅ Code submitted!")
            else:
                print("  [6/8] ❌ Invalid code")
                return None
        else:
            print("  [6/8] ⚠️ No code input found")
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("  Press Enter to continue... ")
            )
    
    # Step 7: Navigate to console
    print("  [7/8] Navigating to console...")
    try:
        await page.goto("https://platform.xiaomimimo.com/console/apikey", timeout=30000)
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  ⚠️ Console nav error: {e}")
    
    # Step 8: Get or create API key
    print("  [8/8] Getting API key...")
    api_key = None
    
    try:
        body_text = await page.inner_text("body")
        
        # Look for existing key (tp- or sk-)
        key_match = re.search(r'((?:tp|sk)-[a-zA-Z0-9_-]{20,})', body_text)
        if key_match:
            api_key = key_match.group(1)
            print(f"  [8/8] ✅ API KEY: {api_key}")
        else:
            # Try creating new key
            create_btn = await page.query_selector("button:has-text('Create'), button:has-text('New'), button:has-text('Generate'), button:has-text('Create New Key')")
            if create_btn:
                await create_btn.click()
                await page.wait_for_timeout(5000)
                
                # Confirm dialog
                confirm = await page.query_selector("button:has-text('Confirm'), button:has-text('OK'), button:has-text('Yes')")
                if confirm:
                    await confirm.click()
                    await page.wait_for_timeout(5000)
                
                # Check again
                body_text = await page.inner_text("body")
                key_match = re.search(r'((?:tp|sk)-[a-zA-Z0-9_-]{20,})', body_text)
                if key_match:
                    api_key = key_match.group(1)
                    print(f"  [8/8] ✅ NEW API KEY: {api_key}")
                else:
                    print(f"  [8/8] ⚠️ Key not found after create")
            else:
                print(f"  [8/8] ⚠️ No Create button found")
    except Exception as e:
        print(f"  [8/8] ⚠️ API key error: {e}")
    
    # Save result
    if api_key:
        save_key(email_addr, PASSWORD, api_key, EMAIL_PROVIDER)
    else:
        print(f"  ⚠️ Registered but no API key — check manually")
    
    return {"email": email_addr, "password": PASSWORD, "api_key": api_key}


# ─── MAIN ─────────────────────────────────────────────────────
async def main():
    from playwright.async_api import async_playwright
    
    print("="*60)
    print("  XIAOMI MIMO AUTO-REGISTRATION v5")
    print(f"  Provider: {EMAIL_PROVIDER.upper()}")
    if EMAIL_PROVIDER == "custom_domain":
        print(f"  Domain: {DOMAIN}")
    print(f"  Gmail (polling): {GMAIL_USER}")
    print(f"  Accounts: {COUNT}")
    print(f"  Output: {KEYS_FILE.absolute()}")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        )
        
        success = 0
        failed = 0
        keys = []
        
        for i in range(1, COUNT + 1):
            page = await context.new_page()
            try:
                result = await register_account(page, i)
                if result and result.get("api_key"):
                    success += 1
                    keys.append(result)
                else:
                    failed += 1
            except Exception as e:
                print(f"\n  ❌ FATAL ERROR: {e}")
                failed += 1
            finally:
                await page.close()
            
            # Delay between accounts (randomize)
            if i < COUNT:
                delay = random.randint(15, 30)
                print(f"\n  ⏳ Waiting {delay}s before next account...")
                await asyncio.sleep(delay)
        
        await browser.close()
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"  FINAL RESULTS")
    print(f"{'='*60}")
    print(f"  Total: {COUNT}")
    print(f"  ✅ Success: {success}")
    print(f"  ❌ Failed: {failed}")
    
    if keys:
        print(f"\n  API Keys:")
        for k in keys:
            print(f"    {k['email']} | {k['api_key']}")
    
    # Load existing keys.json and merge
    existing = []
    if KEYS_FILE.exists():
        with open(KEYS_FILE) as f:
            existing = json.load(f)
    
    print(f"\n  📁 Total keys in keys.json: {len(existing)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
