#!/usr/bin/env python3
"""访问学生端签到真实入口 newsign/preSign，查找教师指定地点字段"""
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

AID = "5000173244062"

# 学生端签到入口（来自taskactivelist的url字段）
pre_url = (f"{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}"
           f"&activePrimaryId={AID}&general=1&sys=1&ls=1&appType=15&uid={puid_s}&isTeacherViewOpen=0")
print(f"\n[1] GET newsign/preSign ...")
r = s_s.get(pre_url, timeout=20, allow_redirects=True)
text = r.text
print(f"  最终URL: {r.url}")
print(f"  HTTP {r.status_code}, len={len(text)}")

if r.status_code == 200:
    # 搜索位置相关字段
    print("\n  [位置字段搜索]")
    for m in re.finditer(r'["\']?(locationtext|locationText|textlocation|textLocation|addressText|address|place|location)["\']?\s*[:=]\s*["\']([^"\']{2,100})["\']', text, re.I):
        print(f"    {m.group(1)} = {m.group(2)}")
    # 经纬度
    for m in re.finditer(r'["\']?(latitude|longitude|lat\b|lng\b|lon\b|location_x|location_y)["\']?\s*[:=]\s*["\']?(-?\d+\.?\d*)', text, re.I):
        print(f"    {m.group(1)} = {m.group(2)}")
    # 中文提示
    for m in re.finditer(r'(请在[^<"]{2,30}附近|签到地点[^<"]{0,30}|位置签到[^<"]{0,30})', text):
        print(f"    [提示] {m.group(0)[:80]}")
    # 保存完整HTML供分析
    with open("/workspace/presign_page.html", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n  完整HTML已保存到 presign_page.html")
    print(f"\n  HTML片段预览:")
    # 找body内容
    body_m = re.search(r'<body[^>]*>(.{500,3000}?)</body>', text, re.S)
    if body_m:
        print(f"  {body_m.group(1)[:2500]}")
    else:
        print(f"  {text[:2500]}")
else:
    print(f"  失败: {text[:300]}")
    # 尝试POST
    print("\n[1b] POST newsign/preSign ...")
    r = s_s.post(pre_url, timeout=20, allow_redirects=True)
    print(f"  HTTP {r.status_code}, len={len(r.text)}")
    if r.status_code == 200:
        for m in re.finditer(r'["\']?(locationtext|locationText|address|place)["\']?\s*[:=]\s*["\']([^"\']{2,100})["\']', r.text, re.I):
            print(f"    {m.group(1)} = {m.group(2)}")
        with open("/workspace/presign_page.html", "w", encoding="utf-8") as f:
            f.write(r.text)
