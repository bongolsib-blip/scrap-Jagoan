import os
import random
import string
import time
import cloudscraper  # Ganti requests dengan cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import unquote

# Jeda waktu acak
time.sleep(random.randint(60, 600))

REMEMBER_COOKIE = os.getenv("REMEMBER_COOKIE")
CF_CLEARANCE = os.getenv("CF_CLEARANCE")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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

form_url = "https://panel.jagoanssh.com/account/create/38?protocol=vmess"

print("[DEBUG] Mengakses halaman form via CloudScraper...")
res_get = session.get(form_url)

print("[DEBUG] Mengakses halaman form...")
res_get = session.get(form_url, headers=headers)

if "login" in res_get.url.lower():
    print("[GAGAL] Sesi/Cookie kedaluwarsa.")
    exit(1)

soup = BeautifulSoup(res_get.text, 'html.parser')
meta_token = soup.find('meta', {'name': 'csrf-token'})

if not meta_token:
    print(f"[LOG] Gagal menemukan meta csrf-token.")
    print(f"[DEBUG] URL terakhir setelah GET: {res_get.url}")
    print(f"[DEBUG] Status Code GET: {res_get.status_code}")
    print(f"[DEBUG] Cuplikan HTML dari Server:\n{res_get.text[:500]}") # Cetak 500 karakter pertama
    exit(1)

csrf_token = meta_token['content']
raw_xsrf = session.cookies.get('XSRF-TOKEN')
decoded_xsrf = unquote(raw_xsrf) if raw_xsrf else ""

random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
username = f'{random_suffix}'
print(f'[+] Username baru: {username}')

payload = {
    "_token": csrf_token,
    "_server": "idray.jagoanip.my.id",
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
clash_raw = details.get("clash", "")
vmess_tls = details.get("vmess_tls", "")
expired_date = details.get("expired", "")

if not clash_raw:
    print("[GAGAL] Data Clash tidak ditemukan dalam respons.")
    exit(1)

# Format ulang teks Clash agar sesuai persis dengan struktur yang kamu inginkan
clash_formatted = f"""proxies:
  - name: {username}
    server: idray.jagoanip.my.id
    port: 443
    type: vmess
    uuid: {details.get("uuid")}
    alterId: 0
    cipher: auto
    tls: true
    skip-cert-verify: true
    servername: idray.jagoanip.my.id
    network: ws
    ws-opts:
      path: /vvip
      headers:
        Host: idray.jagoanip.my.id
    udp: true
"""

# 1. Simpan ke file lokal (misal: proxy.yaml)
with open("proxy.yaml", "w") as f:
    f.write(clash_formatted)
print("[LOG] File proxy.yaml berhasil dibuat.")

# 2. Kirim pesan ke Telegram
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    telegram_message = (
        f"✅ **Akun Vmess Berhasil Dibuat!**\n\n"
        f"👤 Username: `{username}`\n"
        f"📅 Expired: `{expired_date}`\n\n"
        f"🔗 **Link Vmess TLS:**\n`{vmess_tls}`\n\n"
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
