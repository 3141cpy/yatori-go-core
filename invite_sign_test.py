#!/usr/bin/env python3
"""测试超星邀请签到功能 - 探索 xiucat.top 可能使用的修改签到状态方法"""

import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ==================== 登录函数 ====================
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

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

# ==================== 工具函数 ====================
def safe_get(session, url, **kwargs):
    """安全的 GET 请求"""
    try:
        r = session.get(url, timeout=15, **kwargs)
        return r
    except Exception as e:
        return None

def safe_post(session, url, **kwargs):
    """安全的 POST 请求"""
    try:
        r = session.post(url, timeout=15, **kwargs)
        return r
    except Exception as e:
        return None

def print_response(label, resp):
    """打印响应信息"""
    if resp is None:
        print(f"  [{label}] 请求失败/超时")
        return
    print(f"  [{label}] Status: {resp.status_code}")
    try:
        body = resp.text[:2000]
        print(f"  [{label}] Body: {body}")
    except:
        print(f"  [{label}] Body: (无法读取)")

# ==================== 主测试 ====================
def main():
    print("=" * 80)
    print("超星邀请签到功能测试")
    print("=" * 80)

    # ---------- 登录 ----------
    print("\n" + "=" * 80)
    print("登录账号")
    print("=" * 80)

    print("\n[1] 登录学生账号 18436633997 ...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"  学生PUID: {stu_puid}")
    print(f"  Cookies: {[(c.name, c.value[:30]) for c in stu_session.cookies]}")

    print("\n[2] 登录教师账号 19712720708 ...")
    tea_session, tea_puid = login("19712720708", "3.1415926Cpy")
    print(f"  教师PUID: {tea_puid}")
    print(f"  Cookies: {[(c.name, c.value[:30]) for c in tea_session.cookies]}")

    COURSE_ID = "257485372"
    CLASS_ID = "132821141"

    # ==================== Test 1: 探索超星邀请签到端点 ====================
    print("\n" + "=" * 80)
    print("Test 1: 探索超星邀请签到端点")
    print("=" * 80)

    invite_endpoints = [
        # mobilelearn 域名
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/invite/create"),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/invite/create"),
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/invite/verify"),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/invite/verify"),
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/invite/sign"),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/invite/sign"),
        ("GET", "https://mobilelearn.chaoxing.com/newsign/invite/create"),
        ("POST", "https://mobilelearn.chaoxing.com/newsign/invite/create"),
        ("GET", "https://mobilelearn.chaoxing.com/v2/apis/sign/invite"),
        # mooc1-api 域名
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/create"),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/create"),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/verify"),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/verify"),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/sign"),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/sign"),
        # 额外可能的端点
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/invite"),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/invite"),
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/invite/join"),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/invite/join"),
    ]

    print("\n--- 使用教师会话测试 ---")
    for method, url in invite_endpoints:
        label = f"{method} {url.split('.com')[-1]}"
        if method == "GET":
            resp = safe_get(tea_session, url, params={"courseId": COURSE_ID, "classId": CLASS_ID})
        else:
            resp = safe_post(tea_session, url, data={"courseId": COURSE_ID, "classId": CLASS_ID})
        print_response(label, resp)

    print("\n--- 使用学生会话测试 ---")
    for method, url in invite_endpoints:
        label = f"{method} {url.split('.com')[-1]}"
        if method == "GET":
            resp = safe_get(stu_session, url, params={"courseId": COURSE_ID, "classId": CLASS_ID})
        else:
            resp = safe_post(stu_session, url, data={"courseId": COURSE_ID, "classId": CLASS_ID})
        print_response(label, resp)

    # ==================== Test 2: xiucat.top V2 API ====================
    print("\n" + "=" * 80)
    print("Test 2: xiucat.top V2 API 邀请签到功能")
    print("=" * 80)

    xiucat_base = "https://api-test.xiucat.top/v2/student"

    # 登录 xiucat V2 API
    print("\n--- 登录 xiucat V2 API ---")
    xiucat_session = requests.Session()
    xiucat_session.verify = False
    xiucat_session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36"
    })

    login_resp = safe_post(xiucat_session, f"{xiucat_base}/auth/login",
                           json={"phone": "18436633997", "password": "3.1415926Cpy"})
    print_response("xiucat login", login_resp)

    # 如果登录成功，提取 token
    xiucat_token = ""
    if login_resp and login_resp.status_code == 200:
        try:
            data = login_resp.json()
            xiucat_token = data.get("data", {}).get("token", "") or data.get("token", "")
            print(f"  xiucat token: {xiucat_token[:50]}..." if xiucat_token else "  未获取到 token")
        except:
            print("  无法解析登录响应")

    if xiucat_token:
        xiucat_session.headers.update({"Authorization": f"Bearer {xiucat_token}"})

    # 测试各端点
    xiucat_endpoints = [
        ("POST", f"{xiucat_base}/sign/invite/create", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", f"{xiucat_base}/sign/invite/verify", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", f"{xiucat_base}/sign/invite/checkInfo", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", f"{xiucat_base}/sign/invite/location", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("POST", f"{xiucat_base}/sign/invite/qrcode", {"courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    for method, url, params in xiucat_endpoints:
        label = f"{method} {url.split('/v2/')[-1]}"
        if method == "GET":
            resp = safe_get(xiucat_session, url, params=params)
        else:
            resp = safe_post(xiucat_session, url, json=params)
        print_response(label, resp)

    # 也尝试不带 token
    print("\n--- 不带 token 测试 ---")
    no_auth_session = requests.Session()
    no_auth_session.verify = False
    no_auth_session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    })
    for method, url, params in xiucat_endpoints:
        label = f"no-auth {method} {url.split('/v2/')[-1]}"
        if method == "GET":
            resp = safe_get(no_auth_session, url, params=params)
        else:
            resp = safe_post(no_auth_session, url, json=params)
        print_response(label, resp)

    # ==================== Test 3: 签到码/手势码获取 ====================
    print("\n" + "=" * 80)
    print("Test 3: 签到码/手势码获取")
    print("=" * 80)

    signcode_endpoints = [
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/getSignCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/getSignCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/getSignCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("POST", "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/getSignCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/getSignCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/getSignCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # V2 API 刷新二维码
        ("GET", "https://mobilelearn.chaoxing.com/v2/apis/sign/refreshQRCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("POST", "https://mobilelearn.chaoxing.com/v2/apis/sign/refreshQRCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # 额外可能的端点
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/signCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/pptSign/getCode",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # 教师端签到管理
        ("GET", "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/signInfo",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/managerSign",
         {"courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    print("\n--- 教师会话 ---")
    for method, url, params in signcode_endpoints:
        label = f"{method} {url.split('.com')[-1]}"
        if method == "GET":
            resp = safe_get(tea_session, url, params=params)
        else:
            resp = safe_post(tea_session, url, data=params)
        print_response(label, resp)

    print("\n--- 学生会话 ---")
    for method, url, params in signcode_endpoints:
        label = f"{method} {url.split('.com')[-1]}"
        if method == "GET":
            resp = safe_get(stu_session, url, params=params)
        else:
            resp = safe_post(stu_session, url, data=params)
        print_response(label, resp)

    # ==================== Test 4: 签到码暴力测试 ====================
    print("\n" + "=" * 80)
    print("Test 4: 签到码暴力测试")
    print("=" * 80)

    # 先获取当前活动签到列表
    print("\n--- 获取当前签到活动列表 ---")
    activity_urls = [
        f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/getSignInfo?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/pptSign/stuSignajax?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]
    for url in activity_urls:
        label = f"GET {url.split('.com')[-1]}"
        resp = safe_get(stu_session, url)
        print_response(label, resp)

    # 测试 stuSignajax 签到接口
    print("\n--- 测试 stuSignajax 签到接口 ---")
    common_codes = ["000000", "123456", "111111", "666666", "888888", "999999",
                    "123123", "654321", "111222", "000001", "999998", "135790"]

    for code in common_codes:
        url = "https://mobilelearn.chaoxing.com/pptSign/stuSignajax"
        params = {
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
            "signCode": code,
        }
        resp = safe_get(stu_session, url, params=params)
        if resp:
            try:
                body = resp.text[:500]
                # 检查是否有不同于"签到码错误"的响应
                print(f"  Code={code}: Status={resp.status_code}, Body={body}")
            except:
                print(f"  Code={code}: 读取失败")
        else:
            print(f"  Code={code}: 请求失败")

    # 也测试 POST 方式
    print("\n--- 测试 POST stuSignajax ---")
    for code in ["123456", "000000"]:
        url = "https://mobilelearn.chaoxing.com/pptSign/stuSignajax"
        data = {
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
            "signCode": code,
        }
        resp = safe_post(stu_session, url, data=data)
        print_response(f"POST signCode={code}", resp)

    # ==================== 额外探索: 查找签到活动ID ====================
    print("\n" + "=" * 80)
    print("额外探索: 查找签到活动ID和签到详情")
    print("=" * 80)

    # 获取课程任务列表
    print("\n--- 获取课程任务列表 ---")
    task_urls = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/work/getAllWork?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/pptSign/getSignDetail?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/getSignDetail?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]
    for url in task_urls:
        label = f"GET {url.split('.com')[-1]}"
        # 教师端
        resp = safe_get(tea_session, url)
        print_response(f"Teacher {label}", resp)
        # 学生端
        resp = safe_get(stu_session, url)
        print_response(f"Student {label}", resp)

    # 尝试获取签到活动列表（教师视角）
    print("\n--- 教师获取签到活动 ---")
    tea_sign_urls = [
        f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/getSignList?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/signList?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/pptSign/teacherSign?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]
    for url in tea_sign_urls:
        label = f"GET {url.split('.com')[-1]}"
        resp = safe_get(tea_session, url)
        print_response(label, resp)

    # ==================== 额外探索: 邀请签到特定参数 ====================
    print("\n" + "=" * 80)
    print("额外探索: 邀请签到特定参数测试")
    print("=" * 80)

    # 尝试带更多参数的邀请签到
    print("\n--- 带完整参数的邀请签到创建 (教师) ---")
    invite_create_params = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "signType": "4",  # 4 可能是邀请签到类型
        "latitude": "",
        "longitude": "",
        "address": "",
    }
    invite_create_urls = [
        "https://mobilelearn.chaoxing.com/pptSign/invite/create",
        "https://mobilelearn.chaoxing.com/pptSign/sign",
        "https://mobilelearn.chaoxing.com/pptSign/teacherSign",
        "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/create",
    ]
    for url in invite_create_urls:
        label = f"POST {url.split('.com')[-1]}"
        resp = safe_post(tea_session, url, data=invite_create_params)
        print_response(label, resp)

    # 尝试学生端邀请签到
    print("\n--- 学生端邀请签到验证 ---")
    invite_verify_params = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "signCode": "123456",
        "inviteCode": "test",
    }
    invite_verify_urls = [
        "https://mobilelearn.chaoxing.com/pptSign/invite/verify",
        "https://mobilelearn.chaoxing.com/pptSign/invite/sign",
        "https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
        "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/verify",
        "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/invite/sign",
    ]
    for url in invite_verify_urls:
        label = f"POST {url.split('.com')[-1]}"
        resp = safe_post(stu_session, url, data=invite_verify_params)
        print_response(label, resp)

    # ==================== 额外探索: 检查签到类型枚举 ====================
    print("\n" + "=" * 80)
    print("额外探索: 签到类型枚举 (signType)")
    print("=" * 80)

    # 尝试不同 signType 值创建签到
    print("\n--- 教师创建不同类型签到 ---")
    for sign_type in ["0", "1", "2", "3", "4", "5"]:
        url = "https://mobilelearn.chaoxing.com/pptSign/sign"
        data = {
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
            "signType": sign_type,
            "latitude": "",
            "longitude": "",
            "address": "",
        }
        resp = safe_post(tea_session, url, data=data)
        print_response(f"signType={sign_type}", resp)

    # ==================== 额外探索: V2 API 签到接口 ====================
    print("\n" + "=" * 80)
    print("额外探索: V2 API 签到接口")
    print("=" * 80)

    v2_endpoints = [
        ("GET", f"https://mobilelearn.chaoxing.com/v2/apis/sign/signInfo?courseId={COURSE_ID}&classId={CLASS_ID}"),
        ("GET", f"https://mobilelearn.chaoxing.com/v2/apis/sign/signList?courseId={COURSE_ID}&classId={CLASS_ID}"),
        ("GET", f"https://mobilelearn.chaoxing.com/v2/apis/sign/create?courseId={COURSE_ID}&classId={CLASS_ID}"),
        ("POST", f"https://mobilelearn.chaoxing.com/v2/apis/sign/create"),
        ("GET", f"https://mobilelearn.chaoxing.com/v2/apis/sign/invite?courseId={COURSE_ID}&classId={CLASS_ID}"),
        ("POST", f"https://mobilelearn.chaoxing.com/v2/apis/sign/invite"),
        ("GET", f"https://mobilelearn.chaoxing.com/v2/apis/sign/qrcode?courseId={COURSE_ID}&classId={CLASS_ID}"),
    ]

    print("\n--- 教师会话 ---")
    for method, url in v2_endpoints:
        label = f"{method} {url.split('.com')[-1]}"
        if method == "GET":
            resp = safe_get(tea_session, url)
        else:
            resp = safe_post(tea_session, url, json={"courseId": COURSE_ID, "classId": CLASS_ID})
        print_response(label, resp)

    print("\n--- 学生会话 ---")
    for method, url in v2_endpoints:
        label = f"{method} {url.split('.com')[-1]}"
        if method == "GET":
            resp = safe_get(stu_session, url)
        else:
            resp = safe_post(stu_session, url, json={"courseId": COURSE_ID, "classId": CLASS_ID})
        print_response(label, resp)

    # ==================== 额外探索: 检查 xiucat.top 主站 ====================
    print("\n" + "=" * 80)
    print("额外探索: xiucat.top 主站和 API")
    print("=" * 80)

    xiucat_urls = [
        "https://xiucat.top",
        "https://api.xiucat.top",
        "https://api.xiucat.top/v2/student/auth/login",
        "https://api-test.xiucat.top",
        "https://api-test.xiucat.top/v2",
    ]
    for url in xiucat_urls:
        label = f"GET {url}"
        resp = safe_get(requests.Session(), url)
        print_response(label, resp)

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
