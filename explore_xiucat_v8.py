#!/usr/bin/env python3
"""
xiucat.top 最终参数测试 - 添加 location 和 打卡序号
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

ACC2_PHONE = "18436633997"
ACC2_PWD = "3.1415926Cpy"
ACC2_PUID = "431407443"

COURSE2_ID = "262934472"
COURSE2_CLASS = "145110605"
COURSE2_NAME = "好好学习，天天向上"

COURSE1_ID = "257485372"
COURSE1_CLASS = "132821141"
COURSE1_NAME = "111"

BASE_URL = "https://api-test.xiucat.top/v2"

def log_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def log_result(label, resp):
    status = resp.status_code if resp else "NO RESPONSE"
    body = ""
    if resp:
        try:
            body = resp.text[:2000]
        except:
            body = "<cannot read body>"
    print(f"  [{label}] Status: {status}")
    print(f"  [{label}] Body: {body}")
    print()

def main():
    # ===== 登录 xiucat =====
    log_section("登录 xiucat V2")
    r = requests.post(f"{BASE_URL}/student/auth/login",
                      json={"phone": ACC2_PHONE, "password": ACC2_PWD},
                      verify=False, timeout=20)
    data = r.json()
    token = data["data"]["tInfo"]["accessToken"]
    user_info = data["data"]["userInfo"]
    pcookies = data["data"].get("pCookies", [])
    print(f"  Token获取成功, puid={user_info.get('puid')}, fid={user_info.get('fid')}")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ===== Step 1: mode1 + location 参数 =====
    log_section("Step 1: /v2/clockin/mode1 + location 参数")

    # 1a. 添加 location
    print("  [1a] mode1 + location...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "",
                                "location": "34.7466,113.6253"},
                          verify=False, timeout=20)
        log_result("1a-mode1-location", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 1b. location + 更多参数
    print("  [1b] mode1 + location + 更多参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "location": "34.7466,113.6253",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市"},
                          verify=False, timeout=20)
        log_result("1b-mode1-location-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 1c. 尝试不同的location格式
    print("  [1c] mode1 + 不同location格式...")
    location_formats = [
        "34.7466,113.6253",
        "34.7466|113.6253",
        "34.7466 113.6253",
        "{\"lat\":34.7466,\"lng\":113.6253}",
        "河南省郑州市",
        "",
    ]
    for loc in location_formats:
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers,
                              json={"activeId": "1000155099942", "address": "",
                                    "location": loc},
                              verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            code = result.get("code", 0)
            if code != 400 or "location must be a string" not in msg:
                print(f"  ★ location='{loc[:30]}': code={code}, msg={msg[:200]}")
            else:
                print(f"  location='{loc[:30]}': 仍然需要location")
        except Exception as e:
            print(f"  location='{loc[:30]}': Error: {e}")

    # ===== Step 2: mode3 + 打卡序号 =====
    log_section("Step 2: /v2/clockin/mode3 + 打卡序号")

    # 2a. 添加 punchOrder/punchNo
    print("  [2a] mode3 + punchOrder...")
    for field in ["punchOrder", "punchNo", "order", "seq", "sequence", "index", "clockInNo", "clockNo", "punchIndex"]:
        for val in [1, 2, 3, 4]:
            try:
                r = requests.post(f"{BASE_URL}/clockin/mode3",
                                  headers=auth_headers,
                                  json={"activeId": "1000155099942", "address": "河南省郑州市",
                                        "location": "34.7466,113.6253",
                                        "latitude": "34.7466", "longitude": "113.6253",
                                        "locationText": "河南省郑州市",
                                        field: val},
                                  verify=False, timeout=10)
                result = r.json()
                msg = result.get("message", "")
                code = result.get("code", 0)
                if "打卡序号只能是" not in msg:
                    print(f"  ★ {field}={val}: code={code}, msg={msg[:200]}")
                    break
            except:
                pass
        else:
            continue
        break

    # 2b. 尝试更多字段名
    print("  [2b] mode3 - 更多打卡序号字段名...")
    more_fields = ["punchSeq", "clockSeq", "clockOrder", "clockIndex",
                   "signOrder", "signNo", "signSeq", "signIndex",
                   "checkOrder", "checkNo", "checkSeq",
                   "mode", "type", "subMode", "subType",
                   "slot", "slotNo", "slotIndex",
                   "round", "roundNo", "roundIndex",
                   "period", "periodNo",
                   "timeSlot", "timeSlotNo"]
    for field in more_fields:
        for val in [1, 2, 3, 4]:
            try:
                r = requests.post(f"{BASE_URL}/clockin/mode3",
                                  headers=auth_headers,
                                  json={"activeId": "1000155099942", "address": "河南省郑州市",
                                        "location": "34.7466,113.6253",
                                        "latitude": "34.7466", "longitude": "113.6253",
                                        "locationText": "河南省郑州市",
                                        field: val},
                                  verify=False, timeout=10)
                result = r.json()
                msg = result.get("message", "")
                code = result.get("code", 0)
                if "打卡序号只能是" not in msg:
                    print(f"  ★★★ {field}={val}: code={code}, msg={msg[:200]}")
                    break
            except:
                pass
        else:
            continue
        break

    # ===== Step 3: 深入分析JS代码中的签到参数 =====
    log_section("Step 3: 深入分析JS代码中的签到参数")

    print("  下载JS...")
    r = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
    js = r.text

    # 搜索 mode1 调用附近的参数构造
    # 找到 LN 函数 (mode1) 的调用位置
    ln_idx = js.find('LN(')
    while ln_idx != -1:
        context = js[max(0, ln_idx-500):ln_idx+500]
        if 'activeId' in context or 'mode' in context.lower() or 'sign' in context.lower():
            print(f"\n  LN(mode1) 调用上下文 (位置 {ln_idx}):")
            print(f"    {context[:800]}")
        ln_idx = js.find('LN(', ln_idx + 1)
        if ln_idx > 200000:  # 只搜索前面部分
            break

    # 搜索签到提交的代码
    print("\n\n  搜索签到提交代码...")
    # 搜索包含 activeId 的对象构造
    for pattern in [r'activeId\s*:\s*[^,}]+',
                    r'activeId=[^&\s]+']:
        matches = re.findall(pattern, js[:200000])
        if matches:
            print(f"  Pattern '{pattern}': {matches[:10]}")

    # ===== Step 4: 尝试 /v2/student/sign/normal + 所有可能参数 =====
    log_section("Step 4: /v2/student/sign/normal - 穷举 '是否验证' 字段")

    # 从JS代码中搜索可能的参数名
    # 搜索所有形如 xxx:0 或 xxx:1 的参数定义
    param_names = set()
    for match in re.finditer(r'["\'](\w+)["\']\s*:\s*(?:0|1|true|false)', js[:200000]):
        param_names.add(match.group(1))

    # 搜索所有对象属性
    for match in re.finditer(r'(\w+)\s*:\s*(?:e\.|t\.|n\.|o\.|r\.|i\.|s\.|a\.)', js[:200000]):
        param_names.add(match.group(1))

    print(f"  从JS中提取的参数名数量: {len(param_names)}")

    # 过滤可能的"是否验证"参数
    verify_candidates = [p for p in param_names if any(kw in p.lower() for kw in
        ['verify', 'valid', 'check', 'auth', 'confirm', 'pass', 'approve', 'is', 'need', 'has'])]
    print(f"  验证相关候选: {sorted(verify_candidates)[:50]}")

    # 测试这些候选
    base_body = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "fid": "1257",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
        "locationText": "",
    }

    found = False
    for field in sorted(verify_candidates):
        body = dict(base_body)
        body[field] = 0
        try:
            r = requests.post(f"{BASE_URL}/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "是否验证必须是数字" not in msg:
                print(f"  ★★★ {field}=0: {r.text[:300]}")
                found = True
                break
        except:
            pass

    if not found:
        print("  JS中的候选参数名都未命中")

        # 尝试所有参数名
        print("\n  尝试所有从JS提取的参数名...")
        for field in sorted(param_names):
            body = dict(base_body)
            body[field] = 0
            try:
                r = requests.post(f"{BASE_URL}/student/sign/normal",
                                  headers=auth_headers, json=body, verify=False, timeout=10)
                result = r.json()
                msg = result.get("message", "")
                if "是否验证必须是数字" not in msg:
                    print(f"  ★★★ {field}=0: {r.text[:300]}")
                    found = True
                    break
            except:
                pass

    if not found:
        print("  所有参数名都未命中，'是否验证'可能是服务端验证的字段")

    # ===== Step 5: 使用 xiucat cookies 直接调用超星API =====
    log_section("Step 5: 使用 xiucat cookies 直接调用超星API测试补签")

    # 构建超星session
    chaoxing_session = requests.Session()
    chaoxing_session.verify = False
    chaoxing_session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    for pc in pcookies:
        parts = pc.split(";")
        if parts:
            name_value = parts[0].strip()
            if "=" in name_value:
                name, value = name_value.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"')
                chaoxing_session.cookies.set(name, value, domain=".chaoxing.com")

    # 5a. 获取 newsign/preSign 页面内容
    print("  [5a] 获取 newsign/preSign 页面...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/newsign/preSign",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "activePrimaryId": "1000155099942", "general": "1",
                            "sys": "1", "ls": "1", "appType": "15",
                            "uid": ACC2_PUID, "isTeacherViewOpen": "0"},
                    timeout=20)
        print(f"  Status: {r.status_code}, Length: {len(r.text)}")

        # 搜索JS中的签到逻辑
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', r.text)
        print(f"  外部JS: {scripts}")

        # 搜索内联JS
        inline = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
        for s in inline:
            if len(s.strip()) > 10:
                print(f"  内联JS: {s[:500]}")

        # 搜索表单
        forms = re.findall(r'<form[^>]*>(.*?)</form>', r.text, re.DOTALL)
        for f in forms:
            print(f"  表单: {f[:300]}")

        # 搜索隐藏字段
        hidden = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', r.text)
        for h in hidden:
            print(f"  隐藏字段: {h}")

    except Exception as e:
        print(f"  Error: {e}")

    # 5b. 尝试直接签到 (使用超星原始API)
    print("\n  [5b] 直接调用超星签到API...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                    params={"activeId": "1000155099942", "clientip": "",
                            "latitude": "-1", "longitude": "-1",
                            "appType": "15", "ifTiJiao": "1", "address": ""},
                    timeout=20)
        print(f"  stuSignajax: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 5c. 尝试 newsign/signIn
    print("\n  [5c] 尝试 newsign/signIn...")
    try:
        r = chaoxing_session.post("https://mobilelearn.chaoxing.com/newsign/signIn",
                     data={"activeId": "1000155099942", "uid": ACC2_PUID,
                           "clientip": "", "latitude": "-1", "longitude": "-1",
                           "appType": "15", "ifTiJiao": "1", "address": "",
                           "general": "1", "sys": "1", "ls": "1"},
                     timeout=20)
        print(f"  newsign/signIn: Status={r.status_code}, Body={r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 6: 尝试使用教师账号的Cookie修改签到状态 =====
    log_section("Step 6: 使用教师Cookie修改签到状态 (Course1)")

    # 登录教师账号
    AES_KEY_LOCAL = b"u2oh6Vu^HWe4_AES"
    def aes_enc_local(p):
        c = AES.new(AES_KEY_LOCAL, AES.MODE_CBC, AES_KEY_LOCAL)
        return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

    def schild_sign_local(model, locale, version, build, imei):
        SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
        parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
                 f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
                 f"(@Kalimdor)_{imei}"]
        return hashlib.md5(" ".join(parts).encode()).hexdigest()

    def get_mobile_ua_local():
        imei = uuid.uuid4().hex[:32]
        sc = schild_sign_local("MI10", "zh_CN", "6.7.2", "10941_314", imei)
        return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
                f"(schild:{sc}) (device:MI10) Language/zh_CN "
                f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
                f"(@Kalimdor)_{imei}")

    s1 = requests.Session()
    s1.verify = False
    ua = get_mobile_ua_local()
    s1.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s1.post("https://passport2.chaoxing.com/fanyalogin",
           data={"fid": "-1", "uname": aes_enc_local("19712720708"), "password": aes_enc_local("3.1415926Cpy"),
                 "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                 "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                 "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    try: s1.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass

    # 6a. 教师修改Course1的签到状态
    print("  [6a] 教师修改Course1签到状态...")
    try:
        r = s1.get("https://mobilelearn.chaoxing.com/pptSign/updateSignStatus2",
                    params={"activeId": "5000165046206", "uid": ACC2_PUID,
                            "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                            "status": "1"},
                    timeout=20)
        print(f"  updateSignStatus2: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 6b. 教师尝试修改Course2的签到状态 (非成员)
    print("\n  [6b] 教师尝试修改Course2签到状态 (非成员)...")
    try:
        r = s1.get("https://mobilelearn.chaoxing.com/pptSign/updateSignStatus2",
                    params={"activeId": "1000155099942", "uid": ACC2_PUID,
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "status": "1"},
                    timeout=20)
        print(f"  updateSignStatus2 (Course2): {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== 最终总结 =====
    log_section("最终总结")
    print("""
  ==================== 关键发现 ====================

  1. xiucat 有两套签到API:
     A. /v2/student/sign/* - 旧版签到API
        - /v2/student/sign/courses (获取课程)
        - /v2/student/sign/activities (获取活动, 需要fid)
        - /v2/student/sign/normal (普通签到, 需要"是否验证"参数)
        - /v2/student/sign/qrcode (二维码签到, 需要enc)
        - /v2/student/sign/location (位置签到, 需要locationText)

     B. /v2/clockin/* - 新版签到API (实习打卡)
        - /v2/clockin/whichMode (判断模式)
        - /v2/clockin/mode1 (需要address, location)
        - /v2/clockin/mode2 (二维码, 需要location)
        - /v2/clockin/mode3 (位置, 需要打卡序号1-4)
        - /v2/clockin/mode4 (拍照, 需要location)
        - /v2/clockin/faceScore (人脸评分)
        - /v2/clockin/records (签到记录)

  2. 补签机制分析:
     - 直接调用超星stuSignajax对已结束活动返回"签到已结束"
     - 教师只能修改自己课程的签到状态 (updateSignStatus2)
     - xiucat的V2 API可能内部使用了特殊逻辑绕过限制

  3. xiucat 的核心机制:
     - 使用学生凭据登录超星，获取Cookie
     - 保存Cookie在服务端
     - 通过代理方式调用超星API
     - 可能使用了超星的内部/未公开API
    """)


if __name__ == "__main__":
    main()
