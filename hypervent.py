import requests
import time
import re
import json
import random
import string
from bs4 import BeautifulSoup

BASE = "https://hypervent-referral-api.onrender.com"
DEFAULT_PASSWORD = "Haya666@"
OUTFILE = "hypervent.txt"

# ----------------- Utils -----------------
def random_name(length=None):
    if not length:
        length = random.randint(6, 10)
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ----------------- 1secmail -----------------
def get_new_email_1secmail():
    try:
        url = "https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data[0]
    except Exception as e:
        print("⚠️  1secmail gagal:", e)
        return None

def get_messages_1secmail(email):
    login, domain = email.split("@")
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
    return requests.get(url, timeout=15).json()

def read_message_1secmail(email, msg_id):
    login, domain = email.split("@")
    url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}"
    return requests.get(url, timeout=15).json()

# ----------------- mail.tm -----------------
def get_new_email_mailtm():
    try:
        doms = requests.get("https://api.mail.tm/domains", timeout=15).json()
        domain = doms["hydra:member"][0]["domain"]

        local = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        email = f"{local}@{domain}"
        password = "TempPass123!"

        acc = {"address": email, "password": password}
        requests.post("https://api.mail.tm/accounts", json=acc, timeout=15)

        token_resp = requests.post("https://api.mail.tm/token", json=acc, timeout=15).json()
        token = token_resp.get("token")
        return email, password, token
    except Exception as e:
        print("❌ mail.tm gagal:", e)
        return None, None, None

def get_messages_mailtm(token):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get("https://api.mail.tm/messages", headers=headers, timeout=15).json().get("hydra:member", [])

def read_message_mailtm(token, msg_id):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers, timeout=15).json()

# ----------------- OTP Helper -----------------
def extract_otp(raw):
    """Ekstrak angka 6 digit dari raw HTML / text"""
    if not raw:
        return None

    if isinstance(raw, list):
        raw = " ".join(raw)

    # parse HTML
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(" ", strip=True)

    m = re.findall(r"\b\d{6}\b", text)
    return m[-1] if m else None

# ----------------- Hypervent API -----------------
def register_account(email, referral=None):
    url = f"{BASE}/v1/auth/register"
    payload = {"email": email, "password": DEFAULT_PASSWORD, "name": random_name()}
    if referral:
        payload["referredBy"] = referral
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.hypervent.fi",
        "Referer": "https://www.hypervent.fi/",
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    try:
        data = r.json()
    except:
        data = {}
    token = data.get("data", {}).get("token")
    return token, r.text

def request_otp(token):
    url = f"{BASE}/v1/auth/email-verification-otp"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(url, headers=headers, timeout=15).json()

def verify_otp(token, otp):
    url = f"{BASE}/v1/auth/verify-email"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"otp": otp}, timeout=15)
    return r.ok, r.text

# ----------------- Main -----------------
if __name__ == "__main__":
    jumlah = int(input("Masukkan jumlah akun: "))
    referral = input("Masukkan referral code (opsional): ").strip() or None

    for i in range(1, jumlah + 1):
        print(f"\n=== Akun {i} ===")

        email = get_new_email_1secmail()
        use_mailtm, mailtm_token = False, None
        if not email:
            print("ℹ️  Fallback ke mail.tm")
            email, _, mailtm_token = get_new_email_mailtm()
            use_mailtm = True

        name = random_name()
        print(f"📧 Email     : {email}")
        print(f"👤 Name      : {name}")
        print(f"🔑 Password  : {DEFAULT_PASSWORD}")
        print(f"🎟️ Referral  : {referral}")

        token, reg_resp = register_account(email, referral)
        print("[REGISTER]", reg_resp)
        if not token:
            continue

        # retry OTP request until sukses
        while True:
            resp = request_otp(token)
            if "Email Verification OTP Sent Successfully" in str(resp):
                print("✅ [REQUEST OTP]", resp)
                break
            else:
                print("⚠️  Rate limited, tunggu 15s...")
                time.sleep(15)

        # kasih jeda 10 detik biar email sempat masuk
        time.sleep(10)

        otp = None
        for attempt in range(60):  # max 10 menit
            if use_mailtm:
                msgs = get_messages_mailtm(mailtm_token)
                print("[DEBUG MSGS]", msgs)  # debug inbox
                if msgs:
                    msg_id = msgs[0]["id"]
                    body = read_message_mailtm(mailtm_token, msg_id)
                    otp = extract_otp(body.get("html")) or extract_otp(body.get("text"))
                    if otp: break
            else:
                msgs = get_messages_1secmail(email)
                print("[DEBUG MSGS]", msgs)  # debug inbox
                if msgs:
                    msg_id = msgs[0]["id"]
                    body = read_message_1secmail(email, msg_id)
                    otp = extract_otp(body.get("htmlBody")) or extract_otp(body.get("body"))
                    if otp: break

            print(f"[INFO] Menunggu OTP (percobaan {attempt+1}/60)...")
            time.sleep(10)

        if not otp:
            print("❌ OTP tidak ditemukan")
            continue

        print("[OTP]", otp)
        ok, resp = verify_otp(token, otp)
        print("[VERIFY]", resp)

        if ok:
            with open(OUTFILE, "a") as f:
                f.write(f"{email}|{DEFAULT_PASSWORD}\n")
            print(f"✅ Disimpan ke {OUTFILE}")

        # delay sebelum akun berikutnya
        time.sleep(10)
