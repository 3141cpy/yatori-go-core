#!/usr/bin/env python3
"""手势签到 Step6: V2 API错误是否计入锁定计数器（决定性测试）"""
import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"

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

AID_C = "5000173244649"  # 之前: 3次V2错误 + 1次checkSignCode错误

# V2 API连续错误10次
print("[V2 API连续错误10次 — 是否触发锁定]")
for i in range(10):
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
                params={"activeId": AID_C, "uid": puid_s, "latitude": "-1", "longitude": "-1",
                        "signCode": f"8887776{i}"}, timeout=20)
    try:
        d = r.json()
        msg = d.get("errorMsg", "")
        print(f"  V2尝试{i+1}: result={d.get('result')} {msg[:80]}")
        if "锁定" in msg:
            print(f"  *** V2错误也计入计数器! 第{i+1}次触发 ***")
            break
    except:
        print(f"  V2尝试{i+1}: HTTP {r.status_code} {r.text[:80]}")
    time.sleep(0.3)

# checkSignCode当前状态
r = s_s.get(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": AID_C, "signCode": "444555666"}, headers=AJAX_HDR, timeout=15)
try:
    print(f"\n[checkSignCode最终状态] {json.dumps(r.json(), ensure_ascii=False)[:150]}")
except:
    print(f"\n[checkSignCode最终状态] HTTP {r.status_code}: {r.text[:150]}")
