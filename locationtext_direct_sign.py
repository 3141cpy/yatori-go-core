#!/usr/bin/env python3
"""最终验证：locationText → 百度Place搜索POI坐标 → 直接签到（1次信息+1次搜索+1次签到）"""
import base64, hashlib, json, uuid, requests, urllib3, re, math, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"
BAIDU_MAP_AK = "xYjRz7D6pjc3xV516qReaRgcTdoZTyxP"

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
AID = "5000173244062"
AJAX_HDR = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

# POI搜索结果（BD09坐标）
poi_lat, poi_lng = 34.724321, 113.572719  # 道李村南治安室

def try_sign(lat, lng, address="河南省郑州市二七区航海西路街道道李村"):
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": AID, "uid": puid_s, "clientip": "",
                       "latitude": str(lat), "longitude": str(lng),
                       "appType": "15", "fid": "0", "address": address},
                 headers=AJAX_HDR, timeout=15)
    return r.text

print("[POI直签测试] 百度Place搜索POI坐标 (BD09: 34.724321, 113.572719)")
text = try_sign(poi_lat, poi_lng)
print(f"  BD09提交: {text[:120]}")

# 转GCJ02再试（排除坐标系）
def bd09_to_gcj02(bd_lat, bd_lng):
    x = bd_lng - 0.0065; y = bd_lat - 0.006
    z = math.sqrt(x*x + y*y) - 0.00002 * math.sin(y * math.pi * 3000/180)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000/180)
    return z * math.sin(theta), z * math.cos(theta)

gcj_lat, gcj_lng = bd09_to_gcj02(poi_lat, poi_lng)
text = try_sign(gcj_lat, gcj_lng)
print(f"  GCJ02提交({gcj_lat:.6f},{gcj_lng:.6f}): {text[:120]}")

# 最终状态
r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
            params={"activeId": AID, "uid": puid_s, "latitude": "-1", "longitude": "-1"}, timeout=20)
try:
    final = r.json()["data"]
    print(f"\n[状态] status={final.get('status')} lat={final.get('latitude')} lng={final.get('longitude')}")
except Exception:
    print(f"\n[状态] {r.text[:150]}")
