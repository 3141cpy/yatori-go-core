#!/usr/bin/env python3
"""手势签到 Step2: 获取isSecond=1真实手势页面，提取提交API与锁定逻辑"""
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

AID = "5000173244801"  # 最新进行中的手势签到

# getPPTActiveInfo — 新活动signCode是否泄露
r = s_s.get(f"{BASE}/v2/apis/active/getPPTActiveInfo", params={"activeId": AID},
            headers={"X-Requested-With": "XMLHttpRequest"}, timeout=20)
try:
    info = r.json()["data"]
    print(f"[getPPTActiveInfo] activeType={info.get('activeType')} otherId={info.get('otherId')}")
    print(f"  signCode = '{info.get('signCode')}' ← 是否泄露手势码")
    print(f"  content = {info.get('content')}")
except Exception as e:
    print(f"  异常: {e} {r.text[:200]}")

# isSecond=1 手势页面
r = s_s.get(f"{BASE}/newsign/preSign",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": AID,
                    "uid": puid_s, "role": "0", "appType": "15", "isSecond": "1",
                    "isTeacherViewOpen": "0"},
            timeout=20, allow_redirects=True)
text = r.text
print(f"\n[isSecond页面] HTTP {r.status_code} len={len(text)}")
with open("/workspace/gesture_second.html", "w", encoding="utf-8") as f:
    f.write(text)
print(f"  URL: {r.url[:120]}")

# 提取所有JS文件
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', text)
print(f"\n[JS文件]")
for js in js_files:
    print(f"  {js}")

# 提取页面内关键逻辑
print(f"\n[关键代码]")
for kw in ["signCode", "gesture", "锁定", "等待", "尝试", "错误", "次数", "stuSignajax", "sendData", "enc"]:
    for m in re.finditer(kw + r'[^\n]{0,100}', text):
        line = m.group(0).strip()
        if line:
            print(f"  [{kw}] {line[:130]}")
            break  # 每个关键词只显示首个

# 下载页面专属JS分析（sign相关）
print(f"\n[下载页面JS分析]")
session_ua = s_s.headers.get("User-Agent")
for js in js_files:
    if "sign" in js.lower() or "gesture" in js.lower():
        if js.startswith("//"): js = "https:" + js
        if js.startswith("/"): js = "https://mobilelearn.chaoxing.com" + js
        try:
            rj = requests.get(js, headers={"User-Agent": session_ua}, verify=False, timeout=15)
            if rj.status_code == 200 and len(rj.text) > 500:
                fname = "/workspace/gesture_js_" + js.split("/")[-1].split("?")[0]
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(rj.text)
                print(f"  已保存: {fname} ({len(rj.text)}字节)")
        except Exception as e:
            print(f"  {js}: {e}")
