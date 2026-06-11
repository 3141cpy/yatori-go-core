#!/usr/bin/env python3
"""
Tier 8 - Phase 2: Deep proxy path exploration
Focus: GET method on proxy paths, follow 301 redirects, test with different approaches
"""

import base64, hashlib, json, uuid, requests, urllib3, time
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

def get_sign_params(uid):
    return {
        "activeId": ACTIVE_ID,
        "uid": uid,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "signType": "0",
        "clientType": "1",
    }

def req(session, url, method="GET", params=None, data=None, json_data=None, headers_extra=None, follow=False, timeout=15):
    try:
        h = {}
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
        elif method == "OPTIONS":
            r = session.options(url, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        elif method == "PUT":
            r = session.put(url, data=data, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        else:
            return None, None, None
        return r.status_code, r.text[:3000], dict(r.headers)
    except Exception as e:
        return f"ERROR: {str(e)[:100]}", "", {}

def main():
    print("=" * 80)
    print("TIER 8 Phase 2: Deep Proxy Path Exploration")
    print("=" * 80)

    print("\n[*] Logging in...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {stu_puid}")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    Teacher PUID: {tea_puid}")

    noauth = requests.Session()
    noauth.verify = False
    noauth.headers.update({"User-Agent": get_mobile_ua()})

    # ========================================
    # TEST 1: Follow 301 redirects on base paths
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 1: Follow 301 Redirects on Base Paths")
    print("=" * 80)

    base_urls = [
        "https://noteyd.chaoxing.com/proxy",
        "https://noteyd.chaoxing.com/comm",
        "https://appswh.chaoxing.com/projectapp",
        "https://appswh.chaoxing.com/hbqyg",
    ]

    for url in base_urls:
        print(f"\n--- {url} ---")
        # Follow redirects with student session
        status, text, hdrs = req(stu_session, url, follow=True)
        print(f"  [Student] Final: {status}, Location: {hdrs.get('Location', 'N/A')}")
        if text and status != "404":
            print(f"  Body preview: {text[:200]}")

        # Follow redirects with no auth
        status, text, hdrs = req(noauth, url, follow=True)
        print(f"  [NoAuth] Final: {status}, Location: {hdrs.get('Location', 'N/A')}")
        if text and status != "404":
            print(f"  Body preview: {text[:200]}")

    # ========================================
    # TEST 2: GET method on proxy sign-in paths
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 2: GET Method on Proxy Sign-in Paths (405 means POST not allowed, try GET)")
    print("=" * 80)

    proxy_paths = [
        ("noteyd_proxy", "https://noteyd.chaoxing.com/proxy"),
        ("noteyd_comm", "https://noteyd.chaoxing.com/comm"),
        ("appswh_epub", "https://appswh.chaoxing.com/epub"),
        ("appswh_board", "https://appswh.chaoxing.com/board"),
        ("appswh_projectapp", "https://appswh.chaoxing.com/projectapp"),
        ("appswh_hbqyg", "https://appswh.chaoxing.com/hbqyg"),
    ]

    sign_api_paths = [
        "pptSign/updateSignStatus",
        "pptSign/stuSignajax",
        "pptSign/refeashSignList4Json2",
        "newsign/updateSignStatus",
    ]

    for label, base in proxy_paths:
        print(f"\n--- {label}: {base} ---")
        for api in sign_api_paths:
            url = f"{base}/{api}"
            sign_params = get_sign_params(stu_puid)

            # GET with params
            status, text, hdrs = req(stu_session, url, method="GET", params=sign_params)
            if str(status) not in ("404", "405"):
                print(f"  [GET+params] {url} => {status}")
                print(f"    Body: {text[:200]}")

            # GET without params
            status, text, hdrs = req(stu_session, url, method="GET")
            if str(status) not in ("404", "405"):
                print(f"  [GET] {url} => {status}")
                print(f"    Body: {text[:200]}")

            # OPTIONS method
            status, text, hdrs = req(stu_session, url, method="OPTIONS")
            if str(status) not in ("404", "405"):
                print(f"  [OPTIONS] {url} => {status}")
                if hdrs.get("Allow"):
                    print(f"    Allow: {hdrs['Allow']}")

            # PUT method
            status, text, hdrs = req(stu_session, url, method="PUT", data=sign_params)
            if str(status) not in ("404", "405"):
                print(f"  [PUT] {url} => {status}")
                print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 3: Follow redirects on proxy sign-in paths
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 3: Follow Redirects on Proxy Sign-in Paths")
    print("=" * 80)

    for label, base in proxy_paths:
        print(f"\n--- {label}: {base} ---")
        for api in sign_api_paths[:2]:
            url = f"{base}/{api}"
            sign_params = get_sign_params(stu_puid)

            # POST with follow redirects
            status, text, hdrs = req(stu_session, url, method="POST", data=sign_params, follow=True)
            print(f"  [POST+follow] {url} => {status}")
            if text and str(status) not in ("404", "405"):
                print(f"    Body: {text[:200]}")

            # GET with follow redirects
            status, text, hdrs = req(stu_session, url, method="GET", params=sign_params, follow=True)
            print(f"  [GET+follow] {url} => {status}")
            if text and str(status) not in ("404", "405"):
                print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 4: Proxy path with trailing slash variations
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 4: Trailing Slash and Path Variations")
    print("=" * 80)

    variations = [
        "https://noteyd.chaoxing.com/proxy/",
        "https://noteyd.chaoxing.com/proxy/pptSign/",
        "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus/",
        "https://noteyd.chaoxing.com/comm/",
        "https://noteyd.chaoxing.com/comm/pptSign/",
    ]

    for url in variations:
        sign_params = get_sign_params(stu_puid)
        # GET
        status, text, hdrs = req(stu_session, url, method="GET")
        print(f"  [GET] {url} => {status}")
        if str(status) not in ("404",):
            print(f"    Body: {text[:150]}")

        # POST
        status, text, hdrs = req(stu_session, url, method="POST", data=sign_params)
        print(f"  [POST] {url} => {status}")
        if str(status) not in ("404", "405"):
            print(f"    Body: {text[:150]}")

    # ========================================
    # TEST 5: Proxy with different request patterns
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 5: Proxy with Custom Headers and Request Patterns")
    print("=" * 80)

    test_url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
    sign_params = get_sign_params(stu_puid)

    # X-Forwarded-For header
    headers_xff = {"X-Forwarded-For": "127.0.0.1", "X-Real-IP": "127.0.0.1"}
    status, text, hdrs = req(stu_session, test_url, method="POST", data=sign_params, headers_extra=headers_xff)
    print(f"  [POST+XFF] {test_url} => {status}")
    if str(status) not in ("404", "405"):
        print(f"    Body: {text[:200]}")

    # X-Original-URL header
    headers_orig = {"X-Original-URL": "/pptSign/updateSignStatus", "X-Rewrite-URL": "/pptSign/updateSignStatus"}
    status, text, hdrs = req(stu_session, test_url, method="POST", data=sign_params, headers_extra=headers_orig)
    print(f"  [POST+X-Original-URL] {test_url} => {status}")
    if str(status) not in ("404", "405"):
        print(f"    Body: {text[:200]}")

    # Content-Type: application/x-www-form-urlencoded explicitly
    headers_ct = {"Content-Type": "application/x-www-form-urlencoded"}
    status, text, hdrs = req(stu_session, test_url, method="POST", data=sign_params, headers_extra=headers_ct)
    print(f"  [POST+form-urlencoded] {test_url} => {status}")

    # No auth with same tests
    status, text, hdrs = req(noauth, test_url, method="POST", data=sign_params, headers_extra=headers_xff)
    print(f"  [NoAuth+XFF] {test_url} => {status}")
    if str(status) not in ("404", "405"):
        print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 6: Direct comparison - proxy vs direct API
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 6: Direct Comparison - Proxy vs Direct API Response")
    print("=" * 80)

    direct_urls = [
        "https://mooc1-api.chaoxing.com/pptSign/updateSignStatus",
        "https://mooc1-1.chaoxing.com/pptSign/updateSignStatus",
        "https://mooc1-2.chaoxing.com/pptSign/updateSignStatus",
    ]

    sign_params = get_sign_params(stu_puid)

    for direct_url in direct_urls:
        print(f"\n--- Direct: {direct_url} ---")
        # Direct access with auth
        status, text, hdrs = req(stu_session, direct_url, method="POST", data=sign_params)
        print(f"  [Direct+Auth] => {status}")
        print(f"    Body: {text[:200]}")

        # Direct access without auth
        status, text, hdrs = req(noauth, direct_url, method="POST", data=sign_params)
        print(f"  [Direct+NoAuth] => {status}")
        print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 7: Proxy path with specific mobile API patterns
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 7: Mobile API Patterns Through Proxy")
    print("=" * 80)

    mobile_api_paths = [
        "mooc-ans/api/pptSign/updateSignStatus",
        "mooc-ans/pptSign/updateSignStatus",
        "api/pptSign/updateSignStatus",
        "mooc/pptSign/updateSignStatus",
        "ans/pptSign/updateSignStatus",
        "mooc1-api/pptSign/updateSignStatus",
    ]

    for label, base in [("noteyd_proxy", "https://noteyd.chaoxing.com/proxy"),
                         ("noteyd_comm", "https://noteyd.chaoxing.com/comm")]:
        print(f"\n--- {label} ---")
        for api_path in mobile_api_paths:
            url = f"{base}/{api_path}"
            sign_params = get_sign_params(stu_puid)
            status, text, hdrs = req(stu_session, url, method="POST", data=sign_params)
            if str(status) not in ("404",):
                print(f"  [{status}] {url}")

    # ========================================
    # TEST 8: Check if proxy strips cookies/auth
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 8: Auth Behavior Analysis - Does Proxy Strip Cookies?")
    print("=" * 80)

    # Compare 405 response between auth and noauth more carefully
    # If the proxy strips auth, the 405 response should be identical
    # If it passes auth through, the 405 might contain different info
    test_urls_405 = [
        "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus",
        "https://noteyd.chaoxing.com/comm/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/epub/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/projectapp/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/hbqyg/pptSign/updateSignStatus",
    ]

    for url in test_urls_405:
        sign_params = get_sign_params(stu_puid)
        # Auth request
        s1, t1, h1 = req(stu_session, url, method="POST", data=sign_params)
        # No auth request
        s2, t2, h2 = req(noauth, url, method="POST", data=sign_params)
        # Teacher auth
        tea_params = get_sign_params(tea_puid)
        s3, t3, h3 = req(tea_session, url, method="POST", data=tea_params)

        print(f"\n  URL: {url}")
        print(f"  Student: {s1}, Content-Length: {h1.get('Content-Length', 'N/A')}, Server: {h1.get('Server', 'N/A')}")
        print(f"  NoAuth:  {s2}, Content-Length: {h2.get('Content-Length', 'N/A')}, Server: {h2.get('Server', 'N/A')}")
        print(f"  Teacher: {s3}, Content-Length: {h3.get('Content-Length', 'N/A')}, Server: {h3.get('Server', 'N/A')}")

        # Check if response bodies are identical
        if t1 == t2:
            print(f"  *** IDENTICAL response: Student == NoAuth (proxy does NOT differentiate auth)")
        else:
            print(f"  *** DIFFERENT response: Student != NoAuth (proxy DOES check auth)")
            print(f"  Student body: {t1[:100]}")
            print(f"  NoAuth body:  {t2[:100]}")

        if t1 == t3:
            print(f"  *** IDENTICAL response: Student == Teacher")
        else:
            print(f"  *** DIFFERENT response: Student != Teacher")

    # ========================================
    # TEST 9: Try accessing sign-in status APIs through proxy
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 9: Sign-in Status Query APIs Through Proxy")
    print("=" * 80)

    status_api_paths = [
        "pptSign/refreshSignList",  # Note: different from refeash
        "pptSign/signDetail",
        "pptSign/getSignDetail",
        "pptSign/preSign",
        "newsign/getSignDetail",
        "newsign/preSign",
        "v2/apis/sign/detail",
        "v2/apis/sign/status",
    ]

    for label, base in [("noteyd_proxy", "https://noteyd.chaoxing.com/proxy"),
                         ("noteyd_comm", "https://noteyd.chaoxing.com/comm")]:
        print(f"\n--- {label} ---")
        for api_path in status_api_paths:
            url = f"{base}/{api_path}"
            params = {"activeId": ACTIVE_ID, "uid": stu_puid, "courseId": COURSE_ID, "classId": CLASS_ID}
            # GET
            status, text, hdrs = req(stu_session, url, method="GET", params=params)
            if str(status) not in ("404",):
                print(f"  [GET] [{status}] {url}")
                if str(status) not in ("405",):
                    print(f"    Body: {text[:150]}")
            # POST
            status, text, hdrs = req(stu_session, url, method="POST", data=params)
            if str(status) not in ("404",):
                print(f"  [POST] [{status}] {url}")
                if str(status) not in ("405",):
                    print(f"    Body: {text[:150]}")

    print("\n" + "=" * 80)
    print("PHASE 2 COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
