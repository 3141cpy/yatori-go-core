#!/usr/bin/env python3
"""手势签到调研 Step1: 找到手势活动 + getPPTActiveInfo是否泄露手势码"""
import base64, hashlib, json, uuid, requests, urllib3, re
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

s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"学生puid={puid_s}")

# 1. 找手势签到活动
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = r.json()
print("\n[活动列表]")
gesture_aid = None
for item in d.get("activeList", []):
    name = item.get("nameOne", "")
    aid = item["id"]
    status = item.get("status")
    print(f"  aid={aid} name={name} status={status} url={item.get('url','')[:80]}")
    if "手势" in name:
        gesture_aid = str(aid)
        g_status = status
        g_url = item.get("url", "")

if not gesture_aid:
    print("未找到手势签到活动!")
    exit(1)

print(f"\n目标手势活动: aid={gesture_aid} status={g_status}")

# 2. getPPTActiveInfo — 是否泄露signCode
r = s_s.get(f"{BASE}/v2/apis/active/getPPTActiveInfo",
            params={"activeId": gesture_aid},
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Referer": f"https://mobilelearn.chaoxing.com/page/sign/signIn?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={gesture_aid}&fid=22757&timetable=0"},
            timeout=20)
print(f"\n[getPPTActiveInfo] HTTP {r.status_code}")
try:
    info = r.json()["data"]
    with open("/workspace/gesture_active_info.json", "w", encoding="utf-8") as f:
        json.dump(r.json(), f, ensure_ascii=False, indent=2)
    print(f"  activeType={info.get('activeType')} (2=手势)")
    print(f"  signCode = '{info.get('signCode')}'  ← 关键！是否泄露手势码")
    print(f"  content = {info.get('content')}")
    print(f"  ifNeedVCode = {info.get('ifNeedVCode')}")
    print(f"  status={info.get('status')} attendNum={info.get('attendNum')}")
    print(f"  完整响应已存 gesture_active_info.json")
except Exception as e:
    print(f"  解析失败: {e}: {r.text[:300]}")

# 3. 访问手势签到页面（preSign）看页面结构
print(f"\n[3] 手势签到页面分析")
r = s_s.get(f"{BASE}/newsign/preSign",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": gesture_aid,
                    "general": "1", "sys": "1", "ls": "1", "appType": "15", "uid": puid_s,
                    "isTeacherViewOpen": "0"},
            timeout=20, allow_redirects=True)
print(f"  HTTP {r.status_code} len={len(r.text)} URL={r.url[:100]}")
with open("/workspace/gesture_presign.html", "w", encoding="utf-8") as f:
    f.write(r.text)
# 找手势相关JS/接口
for m in re.finditer(r'(sign[A-Za-z]*|gesture[A-Za-z]*|enc|code)["\']?\s*[:=]\s*["\']?[\w\-]{2,60}', r.text[:50000], re.I):
    pass
# 搜索API路径
apis = set(re.findall(r'["\'](/[a-zA-Z][\w/\-]*(?:sign|Sign)[\w/\-]*)["\']', r.text))
print(f"  页面内sign相关API: {list(apis)[:20]}")
for m in re.finditer(r'(stuSignajax|signCode|gesture|手势|锁定|请等待|尝试次数)[^\n]{0,80}', r.text):
    print(f"  [HIT] {m.group(0)[:100]}")
