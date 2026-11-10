import os
import random
import string
import time
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import unquote
import requests
import base64
import json

REMEMBER_COOKIE = os.getenv("REMEMBER_COOKIE")
CF_CLEARANCE = os.getenv("CF_CLEARANCE")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Header persis seperti kode awalmu
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36",
    "Origin": "https://panel.jagoanssh.com",
    "Accept": "application/json, text/plain, */*"
}

# Gunakan cloudscraper session
session = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'android',
        'desktop': False
    }
)

cookies = {
    "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d": REMEMBER_COOKIE,
    "cf_clearance": CF_CLEARANCE
}
session.cookies.update(cookies)

form_url = "https://panel.jagoanssh.com/account/create/40?protocol=vmess"

print("[DEBUG] Mengakses halaman form via CloudScraper...")
res_get = session.get(form_url, headers=headers)

if "login" in res_get.url.lower():
    print("[GAGAL] Sesi/Cookie kedaluwarsa atau tertolak ke halaman login.")
    exit(1)

soup = BeautifulSoup(res_get.text, 'html.parser')
meta_token = soup.find('meta', {'name': 'csrf-token'})

if not meta_token:
    print(f"[LOG] Gagal menemukan meta csrf-token.")
    print(f"[DEBUG] URL terakhir setelah GET: {res_get.url}")
    print(f"[DEBUG] Status Code GET: {res_get.status_code}")
    print(f"[DEBUG] Cuplikan HTML dari Server:\n{res_get.text[:500]}")
    exit(1)

csrf_token = meta_token['content']
raw_xsrf = session.cookies.get('XSRF-TOKEN')
decoded_xsrf = unquote(raw_xsrf) if raw_xsrf else ""

random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
username = f'{random_suffix}'
print(f'[+] Username baru: {username}')

payload = {
    "_token": csrf_token,
    "_server": "sgray.jagoanip.my.id",
    "username": username,
    "duration": "trial",
    "protocol": "vmess"
}

headers_post = headers.copy()
headers_post.update({
    "Referer": form_url,
    "X-Requested-With": "XMLHttpRequest",
    "X-CSRF-TOKEN": csrf_token,
    "X-XSRF-TOKEN": decoded_xsrf,
    "Content-Type": "application/json"
})

print("[DEBUG] Mengirim request pembuatan akun...")
response = session.post(
    "https://panel.jagoanssh.com/account/create-action",
    json=payload,
    headers=headers_post
)

if response.status_code != 200:
    print(f"[GAGAL] Status Code: {response.status_code}")
    print(response.text)
    exit(1)

res_json = response.json()
details = res_json.get("details", {})
vmess_tls = details.get("vmess_tls", "")
expired_date = details.get("expired", "")
uuid = details.get("uuid", "")

if not uuid:
    print("[GAGAL] Data UUID tidak ditemukan dalam respons.")
    print(response.text)
    exit(1)

clash_formatted = f"""proxies:
  - name: {username}
    server: 104.17.2.81
    port: 443
    type: vmess
    uuid: {uuid}
    alterId: 0
    cipher: auto
    tls: true
    skip-cert-verify: true
    servername: sgray.jagoanip.my.id
    network: ws
    ws-opts:
      path: /vvip
      headers:
        Host: sgray.jagoanip.my.id
    udp: true
"""
# Buat dictionary konfigurasi VMess versi JSON untuk di-encode ke Base64 (standar vmess://)
vmess_config = {
    "v": "2",
    "ps": username,
    "add": "104.17.2.81",
    "port": "443",
    "id": uuid,
    "aid": "0",
    "net": "ws",
    "type": "none",
    "host": "idray.jagoanip.my.id",
    "path": "/vvip",
    "tls": "tls",
    "sni": "idray.jagoanip.my.id"
}

# Encode ke string base64 khas link vmess://
json_str = json.dumps(vmess_config)
base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
vmess_link_bug = f"vmess://{base64_str}"

# Simpan ke file terpisah (misal: vmess_bug.txt)
with open("vmess_bug.txt", "w") as f:
    f.write(vmess_link_bug)
print("[LOG] File vmess_bug.txt berhasil dibuat.")

# 1. Simpan ke file lokal (proxy.yaml)
with open("proxy.yaml", "w") as f:
    f.write(clash_formatted)
print("[LOG] File proxy.yaml berhasil dibuat.")

# 2. Kirim pesan ke Telegram
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    telegram_message = (
        f"✅ *Akun Vmess Berhasil Dibuat!*\n\n"
        f"👤 Username: `{username}`\n"
        f"📅 Expired: `{expired_date}`\n\n"
        f"🔗 *Link Vmess TLS:*\n`{vmess_tls}`\n\n"
        f"📂 Format Clash:\n```yaml\n{clash_formatted}\n```"
    )
    
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    tg_payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": telegram_message,
        "parse_mode": "Markdown"
    }
    
    tg_res = requests.post(tg_url, json=tg_payload)
    if tg_res.status_code == 200:
        print("[LOG] Berhasil mengirim pesan ke Telegram.")
    else:
        print(f"[LOG] Gagal kirim Telegram: {tg_res.text}")
