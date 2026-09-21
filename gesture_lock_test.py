#!/usr/bin/env python3
"""手势签到 Step4: GET方式checkSignCode — 锁定阈值与机制测试"""
import base64, hashlib, json, uuid, requests, urllib3, re, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"
COURSE_ID = "257485372"

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
print(f"学生puid={puid_s}\n")

AID_B = "5000173244790"  # 锁定测试活动

def check_code(s, aid, code, method="GET"):
    if method == "GET":
        r = s.get(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
                  params={"activeId": aid, "signCode": code}, headers=AJAX_HDR, timeout=15)
    else:
        r = s.post(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
                   params={"activeId": aid, "signCode": code}, headers=AJAX_HDR, timeout=15)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text[:150]

# 先单个验证GET
sc, resp = check_code(s_s, AID_B, "987654321")
print(f"[GET验证] signCode=987654321 → HTTP {sc} {json.dumps(resp, ensure_ascii=False)[:200] if isinstance(resp, dict) else resp}\n")

# 错误尝试循环 — 找锁定阈值
print("[锁定阈值测试]")
locked = False
for i in range(1, 15):
    code = str(100000 + i * 137)
    sc, resp = check_code(s_s, AID_B, code)
    msg = json.dumps(resp, ensure_ascii=False)[:160] if isinstance(resp, dict) else str(resp)[:160]
    print(f"  尝试{i}: {code} → HTTP {sc} {msg}")
    if isinstance(resp, dict) and resp.get("result") == -1:
        print(f"\n  *** 第{i}次触发锁定 ***")
        print(f"  完整响应: {json.dumps(resp, ensure_ascii=False)}")
        locked = True
        break
    time.sleep(0.4)

# 锁定后测试
if locked:
    print(f"\n[锁定后行为]")
    sc, resp = check_code(s_s, AID_B, "123456")
    print(f"  继续错误尝试: HTTP {sc} {json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else resp}")

    # 换新会话（新Cookie）是否绕过
    s2, puid2 = login("18436633997", "3.1415926Cpy")
    sc, resp = check_code(s2, AID_B, "111222333")
    print(f"  新会话错误尝试: HTTP {sc} {json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else resp}")

    # stuSignajax 是否也被锁
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": AID_B, "courseId": COURSE_ID, "uid": puid_s, "clientip": "",
                       "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0",
                       "signCode": "98765"}, headers=AJAX_HDR, timeout=15)
    print(f"  锁定后stuSignajax: {r.text[:120]}")

    # 另一个活动是否被锁（锁定范围: 按活动还是按用户）
    sc, resp = check_code(s_s, "5000173244801", "987654321")
    print(f"  另一活动checkSignCode: HTTP {sc} {json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else resp}")
