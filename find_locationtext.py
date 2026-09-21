#!/usr/bin/env python3
"""查找学生端位置签到活动响应中的教师指定地点名字字段"""
import base64, hashlib, json, uuid, requests, urllib3, re, sys
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

def safe_json(r):
    try: return r.json()
    except: return None

s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"学生puid={puid_s}")

# 目标活动：新发布的位置签到
AID = "5000173244062"

# 学生端签到页面 — PC H5
pages = [
    ("pcstuSign", f"{BASE}/widget/sign/pcstuSign?activeId={AID}"),
    ("pcStuSign-caps", f"{BASE}/widget/sign/pcStuSign?activeId={AID}"),
    ("stuSign", f"{BASE}/widget/sign/stuSign?activeId={AID}"),
    ("sign-detail", f"{BASE}/widget/sign/detail?activeId={AID}"),
]

for name, url in pages:
    try:
        r = s_s.get(url, timeout=20, allow_redirects=True)
        text = r.text
        print(f"\n=== [{name}] {url}")
        print(f"  HTTP {r.status_code}, len={len(text)}")
        # 搜索位置相关字段
        for kw in ["locationtext", "locationText", "textlocation", "textLocation",
                   "place", "address", "addressText", "location", "签到地点", "附近"]:
            for m in re.finditer(r'["\']?(' + kw + r')["\']?\s*[:=]\s*["\']([^"\']{2,80})["\']', text, re.I):
                val = m.group(2)
                if val and not val.startswith("$"):
                    print(f"  [字段] {m.group(1)} = {val}")
            # 也查中文提示
        for m in re.finditer(r'(距[^<"]{0,10}(?:地点|位置)[^<"]{0,20})', text):
            print(f"  [提示] {m.group(1)}")
        if len(text) < 3000:
            print(f"  RAW: {text[:1500]}")
    except Exception as e:
        print(f"  [{name}] 异常: {e}")

# v2 detail API 再试（上次500，尝试不同参数组合）
print("\n=== V2/API detail 接口 ===")
detail_apis = [
    f"{BASE}/v2/apis/active/getActiveDetail?activeId={AID}&uid={puid_s}",
    f"{BASE}/v2/apis/active/getActiveDetail?activeId={AID}",
    f"{BASE}/ppt/activeAPI/getActiveDetail?activeId={AID}&uid={puid_s}&courseId=257485372&classId=132821141",
    f"{BASE}/ppt/activeAPI/getActiveDetail?activeId={AID}&uid={puid_s}",
    f"{BASE}/v2/apis/sign/getActiveDetail?activeId={AID}&uid={puid_s}",
    f"{BASE}/v2/apis/sign/activeDetail?activeId={AID}&uid={puid_s}",
]
for url in detail_apis:
    try:
        r = s_s.get(url, timeout=15)
        d = safe_json(r)
        path = url.split("chaoxing.com")[1][:60]
        if d:
            # 递归搜索位置字段
            def search_pos(obj, prefix=""):
                found = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        kl = k.lower()
                        if any(x in kl for x in ["location", "address", "place", "lat", "lng", "lon", "text"]):
                            found.append(f"{prefix}{k}={v}")
                        if isinstance(v, (dict, list)):
                            found += search_pos(v, f"{prefix}{k}.")
                elif isinstance(obj, list):
                    for i, v in enumerate(obj[:5]):
                        found += search_pos(v, f"{prefix}[{i}].")
                return found
            found = search_pos(d)
            print(f"\n  {path}: HTTP {r.status_code}")
            print(f"    result={d.get('result') if isinstance(d, dict) else '?'}")
            for f in found[:20]:
                print(f"    {f}")
            if not found:
                print(f"    无位置字段: {json.dumps(d, ensure_ascii=False)[:300]}")
        else:
            print(f"\n  {path}: HTTP {r.status_code}, 非JSON: {r.text[:100]}")
    except Exception as e:
        print(f"  异常: {e}")

# signIn 详情（学生视角获取活动信息）
print("\n=== v2/apis/sign/signIn ===")
r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
            params={"activeId": AID, "uid": puid_s, "latitude": "-1", "longitude": "-1"}, timeout=20)
print(f"  HTTP {r.status_code}: {r.text[:600]}")

# 尝试学生端获取活动信息的其他接口
print("\n=== 其他可能接口 ===")
others = [
    ("ppt/activeAPI/activeDetail", {"activeId": AID, "uid": puid_s}),
    ("ppt/activeAPI/getActiveInfo", {"activeId": AID, "uid": puid_s}),
    ("v2/apis/active/student/activeDetail", {"activeId": AID, "uid": puid_s}),
    ("v2/apis/active/student/detail", {"activeId": AID, "uid": puid_s}),
    ("pptSign/getActiveDetail", {"activeId": AID, "uid": puid_s}),
    ("newsign/getActiveDetail", {"activeId": AID, "uid": puid_s}),
]
for path, params in others:
    try:
        r = s_s.get(f"{BASE}/{path}", params=params, timeout=15)
        d = safe_json(r)
        body = r.text[:300]
        if r.status_code == 200 and d and d.get("result") == 1:
            print(f"\n  [成功] {path}:")
            print(f"    {json.dumps(d, ensure_ascii=False)[:800]}")
        else:
            print(f"  {path}: HTTP {r.status_code}, {body[:120]}")
    except Exception as e:
        print(f"  {path}: 异常 {e}")
