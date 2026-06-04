#!/usr/bin/env python3
"""Quick script to examine the teacher's newsign/preSign page for QR enc generation logic."""

import base64, hashlib, json, uuid, requests, urllib3, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def schild_sign(model, locale, version, build, imei):
    parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
             f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
             f"(@Kalimdor)_{imei}"]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def get_mobile_ua():
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
            f"(schild:{sc}) (device:MI10) Language/zh_CN "
            f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
            f"(@Kalimdor)_{imei}")

def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                            "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                            "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    return s, puid

# Login
print("Logging in as teacher...")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"  puid: {puid_t}")

# QR code sign-in activity
QR_AID = "5000163964324"  # 二维码签到

# Get teacher's newsign/preSign page - full HTML
print(f"\nGetting teacher's newsign/preSign page for aid={QR_AID}...")
url = f"https://mobilelearn.chaoxing.com/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={QR_AID}&general=1&sys=1&ls=1&appType=15&uid={puid_t}"
r = s_t.get(url, allow_redirects=False, timeout=20)
print(f"  Status: {r.status_code}, Length: {len(r.text)}")

# Save full HTML for analysis
with open("/workspace/teacher_presign_qr.html", "w") as f:
    f.write(r.text)
print(f"  Saved to /workspace/teacher_presign_qr.html")

# Extract and print all script contents
scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"\n  Found {len(scripts)} script tags")

for i, script in enumerate(scripts):
    if any(kw in script.lower() for kw in ['enc', 'qr', 'sign', 'activeid', 'uuid', 'qrcode']):
        print(f"\n  === Script {i} (relevant, {len(script)} chars) ===")
        print(script[:2000])
        if len(script) > 2000:
            print(f"  ... (truncated, {len(script)} total chars)")

# Also look for hidden inputs and data attributes
hidden_inputs = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', r.text)
for hi in hidden_inputs:
    print(f"\n  Hidden input: {hi}")

data_attrs = re.findall(r'data-[a-zA-Z-]+=["\'][^"\']*["\']', r.text)
for da in data_attrs:
    if any(kw in da.lower() for kw in ['enc', 'qr', 'sign', 'active', 'uuid']):
        print(f"  Data attr: {da}")

# Look for AJAX calls that might fetch enc values
ajax_calls = re.findall(r'\$\.(?:get|post|ajax)\s*\([^)]+\)', r.text)
for ac in ajax_calls:
    if any(kw in ac.lower() for kw in ['enc', 'qr', 'sign', 'active']):
        print(f"\n  AJAX call: {ac[:300]}")

# Look for fetch calls
fetch_calls = re.findall(r'fetch\s*\([^)]+\)', r.text)
for fc in fetch_calls:
    print(f"\n  Fetch call: {fc[:300]}")

# Also try the student's preSign page
print(f"\n\nLogging in as student...")
s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"  puid: {puid_s}")

print(f"\nGetting student's newsign/preSign page for aid={QR_AID}...")
url = f"https://mobilelearn.chaoxing.com/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={QR_AID}&general=1&sys=1&ls=1&appType=15&uid={puid_s}&isTeacherViewOpen=0"
r = s_s.get(url, allow_redirects=False, timeout=20)
print(f"  Status: {r.status_code}, Length: {len(r.text)}")

with open("/workspace/student_presign_qr.html", "w") as f:
    f.write(r.text)
print(f"  Saved to /workspace/student_presign_qr.html")

scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"\n  Found {len(scripts)} script tags")

for i, script in enumerate(scripts):
    if any(kw in script.lower() for kw in ['enc', 'qr', 'sign', 'activeid', 'uuid', 'qrcode']):
        print(f"\n  === Script {i} (relevant, {len(script)} chars) ===")
        print(script[:2000])

# Now try the known QR aid (5000163891319) which the student already signed
SIGNED_QR_AID = "5000163891319"
print(f"\n\nGetting student's newsign/preSign page for SIGNED QR aid={SIGNED_QR_AID}...")
url = f"https://mobilelearn.chaoxing.com/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={SIGNED_QR_AID}&general=1&sys=1&ls=1&appType=15&uid={puid_s}&isTeacherViewOpen=0"
r = s_s.get(url, allow_redirects=False, timeout=20)
print(f"  Status: {r.status_code}, Length: {len(r.text)}")

with open("/workspace/student_presign_signed_qr.html", "w") as f:
    f.write(r.text)

scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
for i, script in enumerate(scripts):
    if any(kw in script.lower() for kw in ['enc', 'qr', 'sign', 'activeid', 'uuid', 'qrcode']):
        print(f"\n  === Script {i} (relevant, {len(script)} chars) ===")
        print(script[:2000])

# Try to find the in-progress activity (groupList showed "进行中(1)")
print("\n\nLooking for in-progress activities...")
r = s_s.get(f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}&groupId=1", timeout=20)
d = r.json() if r.text.startswith('{') else {}
print(f"  groupId=1 response: {json.dumps(d, ensure_ascii=False)[:1000]}")

# Try different group IDs
for gid in [0, 1, 2]:
    r = s_s.get(f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}&groupId={gid}", timeout=20)
    d = r.json() if r.text.startswith('{') else {}
    active_list = d.get("activeList", [])
    if active_list:
        print(f"\n  groupId={gid}: {len(active_list)} activities")
        for act in active_list[:3]:
            print(f"    aid={act.get('id')}, name={act.get('nameOne')}, status={act.get('status')}, type={act.get('activeType')}")
