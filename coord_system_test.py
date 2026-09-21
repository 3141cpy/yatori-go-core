#!/usr/bin/env python3
"""排除坐标系问题：分别提交BD09/GCJ02/WGS84坐标，确认服务端坐标系及地名与选点是否一致"""
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

location_text = "河南省郑州市二七区航海西路街道道李村 道李村南治安室"

# 百度地理编码原始结果（BD09）
bd_lat, bd_lng = 34.72127824654225, 113.67716667306249

# 转换链
def bd09_to_gcj02(bd_lat, bd_lng):
    x = bd_lng - 0.0065; y = bd_lat - 0.006
    z = math.sqrt(x*x + y*y) - 0.00002 * math.sin(y * math.pi * 3000/180)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * math.pi * 3000/180)
    return z * math.sin(theta), z * math.cos(theta)  # gcj_lat, gcj_lng

def gcj02_to_wgs84(gcj_lat, gcj_lng):
    dlat = -0.000095 * math.sin(3 * math.pi * gcj_lat / 180) + 0.000038 * math.sin(5 * math.pi * gcj_lat / 180)
    dlng = 0.000466 * math.cos(3 * math.pi * gcj_lng / 180) + 0.000016 * math.cos(5 * math.pi * gcj_lng / 180)
    return gcj_lat + dlat, gcj_lng + dlng

gcj_lat, gcj_lng = bd09_to_gcj02(bd_lat, bd_lng)
wgs_lat, wgs_lng = gcj02_to_wgs84(gcj_lat, gcj_lng)

# 百度POI搜索确认"道李村南治安室"标注位置
print("[1] 百度Place搜索POI确切位置:")
try:
    r = requests.get("https://api.map.baidu.com/place/v2/search",
                     params={"query": "道李村南治安室", "region": "郑州市", "output": "json", "ak": BAIDU_MAP_AK},
                     timeout=15)
    d = r.json()
    for p in d.get("results", [])[:3]:
        loc = p.get("location", {})
        print(f"  POI: {p.get('name')} addr={p.get('address','')[:40]} loc=({loc.get('lat')}, {loc.get('lng')})")
except Exception as e:
    print(f"  异常: {e}")

# 分别提交三种坐标系坐标
print(f"\n[2] 坐标系测试（三边测量已确认教师实际选点≈WGS84(34.7208, 113.5812)）:")
tests = [
    ("BD09原始", bd_lat, bd_lng),
    ("GCJ02", gcj_lat, gcj_lng),
    ("WGS84", wgs_lat, wgs_lng),
]
for name, lat, lng in tests:
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": AID, "uid": puid_s, "clientip": "",
                       "latitude": str(lat), "longitude": str(lng),
                       "appType": "15", "fid": "0", "address": location_text},
                 headers=AJAX_HDR, timeout=15)
    print(f"  {name} ({lat:.6f},{lng:.6f}): {r.text[:90]}")
    time.sleep(0.5)

# 对照：三边测量成功坐标（已知在范围内）
print(f"\n[3] 对照 - 三边测量成功过的坐标:")
r = s_s.post(f"{BASE}/pptSign/stuSignajax",
             data={"activeId": AID, "uid": puid_s, "clientip": "",
                   "latitude": "34.725762", "longitude": "113.571210",
                   "appType": "15", "fid": "0", "address": location_text},
             headers=AJAX_HDR, timeout=15)
print(f"  (34.725762,113.571210): {r.text[:90]}")

# 计算地理编码点与三边测量点的实际距离
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

print(f"\n[4] 距离分析:")
tri_lat, tri_lng = 34.7208, 113.5812
print(f"  地理编码点(WGS84)到三边测量教师点: {haversine(wgs_lat, wgs_lng, tri_lat, tri_lng):.0f}米")
print(f"  地理编码点(BD09)到三边测量教师点: {haversine(bd_lat, bd_lng, tri_lat, tri_lng):.0f}米")
print(f"""
结论判定:
- 若BD09提交距离也是9km → 地名与教师实际选点不符（教师选点不在POI处）
- 若BD09提交距离很小 → 是坐标系转换问题，locationText+正确坐标系可直接签到
""")
