#!/usr/bin/env python3
"""手势签到 Step7: 教师创建手势签到活动作为爆破实验场"""
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

s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"教师puid={puid_t}")

# ============ 1. 探测教师创建页面结构 ============
print("\n[1] 教师创建手势签到 — v2 createActive 探测")
# 参考真实App创建流程: activeType=2, otherId=3(手势)
# 尝试 v2 API JSON格式
v2_payloads = [
    # JSON体
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": 2, "otherId": 3,
     "signCode": "1236", "name": "手势签到", "ifTiJiao": 0},
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": 2, "otherId": 3,
     "gestureCode": "1236"},
]
for payload in v2_payloads:
    r = s_t.post(f"{BASE}/v2/apis/active/createActive",
                 json=payload,
                 headers={"Content-Type": "application/json",
                          "Referer": f"{BASE}/v2/apis/active/createActive"},
                 timeout=20)
    print(f"  JSON {list(payload.keys())}: HTTP {r.status_code}: {r.text[:200]}")

# form格式
form_payloads = [
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "otherId": "3", "signCode": "1236"},
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "otherId": "3",
     "signCode": "1236", "uid": puid_t},
]
for payload in form_payloads:
    r = s_t.post(f"{BASE}/v2/apis/active/createActive", data=payload,
                 headers={"X-Requested-With": "XMLHttpRequest"}, timeout=20)
    print(f"  FORM {list(payload.keys())}: HTTP {r.status_code}: {r.text[:200]}")

# ============ 2. 老接口ppt/activeAPI/createActive带手势参数 ============
print("\n[2] 老接口带手势参数")
old_payloads = [
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "otherId": "3",
     "signCode": "1236", "title": "手势签到"},
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "otherId": "3",
     "signCode": "1236", "name": "手势签到", "uid": puid_t},
]
for payload in old_payloads:
    r = s_t.post(f"{BASE}/ppt/activeAPI/createActive", data=payload,
                 headers={"X-Requested-With": "XMLHttpRequest"}, timeout=20)
    print(f"  {list(payload.keys())}: HTTP {r.status_code}: {r.text[:250]}")

# ============ 3. 抓真实创建页面找参数 ============
print("\n[3] 教师端创建页面")
teacher_pages = [
    f"{BASE}/v2/teacher/sign/createSign?courseId={COURSE_ID}&classId={CLASS_ID}",
    f"{BASE}/newsign/teacherCreate?courseId={COURSE_ID}&classId={CLASS_ID}",
    f"{BASE}/v2/apifactory/active/preCreateActive?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2",
    f"{BASE}/v2/apis/active/preCreateActive?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2&otherId=3",
]
for url in teacher_pages:
    try:
        r = s_t.get(url, timeout=15, allow_redirects=True)
        print(f"  {url.split('chaoxing.com')[1][:60]}: HTTP {r.status_code} len={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 2000 and "<" in r.text[:100]:
            # 找表单字段
            inputs = re.findall(r'name=["\'](\w+)["\']', r.text)
            if inputs:
                print(f"    表单字段: {list(set(inputs))[:20]}")
    except Exception as e:
        print(f"  异常: {e}")
