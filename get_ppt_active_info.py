#!/usr/bin/env python3
"""实测 getPPTActiveInfo 接口 — 检查教师指定签到地点泄露"""
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

# 用户提供的真实浏览器请求（App内嵌页 signIn 的XHR）
hdr = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "zh-CN,zh;q=0.9",
    "x-requested-with": "XMLHttpRequest",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "Referer": f"https://mobilelearn.chaoxing.com/page/sign/signIn?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={AID}&fid=22757&timetable=0",
}

r = s_s.get(f"{BASE}/v2/apis/active/getPPTActiveInfo",
            params={"activeId": AID},
            headers=hdr, timeout=20)
print(f"\n[getPPTActiveInfo] HTTP {r.status_code}")
print(f"响应: {r.text[:2000]}")

try:
    d = r.json()
    # 递归提取所有含位置/经纬度的字段
    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{prefix}{k}"
                if isinstance(v, (str, int, float)) and v not in ("", None):
                    kl = k.lower()
                    if any(x in kl for x in ["location", "lat", "lon", "lng", "address", "place", "text", "name", "range", "distance", "radius"]):
                        print(f"  [字段] {p} = {v}")
                if isinstance(v, (dict, list)):
                    walk(v, p + ".")
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:10]):
                walk(v, f"{prefix}[{i}].")
    print("\n[关键字段提取]")
    walk(d)
    # 完整保存
    with open("/workspace/ppt_active_info.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("\n完整响应已保存到 ppt_active_info.json")
except Exception as e:
    print(f"JSON解析失败: {e}")
