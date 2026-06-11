#!/usr/bin/env python3
"""
Tier 8 - Phase 3: Advanced proxy path analysis
Focus: Understanding the 405 behavior, testing alternative proxy entry points
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

def req_detail(session, url, method="GET", params=None, data=None, json_data=None, headers_extra=None, follow=False, timeout=15):
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
        elif method == "HEAD":
            r = session.head(url, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        else:
            return None, None, None
        return r.status_code, r.text[:3000], dict(r.headers)
    except Exception as e:
        return f"ERROR: {str(e)[:100]}", "", {}

def main():
    print("=" * 80)
    print("TIER 8 Phase 3: Advanced Proxy Path Analysis")
    print("=" * 80)

    print("\n[*] Logging in...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {stu_puid}")

    noauth = requests.Session()
    noauth.verify = False
    noauth.headers.update({"User-Agent": get_mobile_ua()})

    # ========================================
    # TEST 1: Analyze the 405 response in detail
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 1: Full 405 Response Analysis")
    print("=" * 80)

    url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
    status, text, hdrs = req_detail(stu_session, url, method="POST", data={"activeId": ACTIVE_ID, "uid": stu_puid})
    print(f"  Status: {status}")
    print(f"  Headers: {json.dumps(hdrs, indent=2)}")
    print(f"  Full body:\n{text}")

    # ========================================
    # TEST 2: OPTIONS method to discover allowed methods
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 2: OPTIONS Method - Discover Allowed Methods")
    print("=" * 80)

    test_urls = [
        "https://noteyd.chaoxing.com/proxy",
        "https://noteyd.chaoxing.com/proxy/",
        "https://noteyd.chaoxing.com/proxy/pptSign",
        "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus",
        "https://noteyd.chaoxing.com/comm",
        "https://noteyd.chaoxing.com/comm/",
        "https://noteyd.chaoxing.com/comm/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/epub/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/projectapp/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/hbqyg/pptSign/updateSignStatus",
    ]

    for url in test_urls:
        status, text, hdrs = req_detail(stu_session, url, method="OPTIONS")
        allow = hdrs.get("Allow", "N/A")
        print(f"  OPTIONS {url} => {status}, Allow: {allow}")

        # Also try HEAD
        status, text, hdrs = req_detail(stu_session, url, method="HEAD")
        print(f"  HEAD {url} => {status}")

    # ========================================
    # TEST 3: Test proxy with specific Content-Types
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 3: Various Content-Type Tests on Proxy")
    print("=" * 80)

    url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
    content_types = [
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
        "application/xml",
        "text/html",
    ]

    sign_params = {"activeId": ACTIVE_ID, "uid": stu_puid, "courseId": COURSE_ID, "classId": CLASS_ID, "signType": "0", "clientType": "1"}

    for ct in content_types:
        h = {"Content-Type": ct}
        status, text, hdrs = req_detail(stu_session, url, method="POST", data=sign_params, headers_extra=h)
        print(f"  [{ct}] => {status}")
        if str(status) not in ("405",):
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 4: Test proxy root path with different methods
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 4: Proxy Root Path with Different Methods")
    print("=" * 80)

    root_urls = [
        "https://noteyd.chaoxing.com/proxy",
        "https://noteyd.chaoxing.com/proxy/",
        "https://noteyd.chaoxing.com/comm",
        "https://noteyd.chaoxing.com/comm/",
    ]

    for url in root_urls:
        print(f"\n  --- {url} ---")
        for method in ["GET", "POST", "OPTIONS", "HEAD"]:
            status, text, hdrs = req_detail(stu_session, url, method=method)
            allow = hdrs.get("Allow", "")
            ct = hdrs.get("Content-Type", "")
            cl = hdrs.get("Content-Length", "")
            print(f"    {method} => {status}, Allow: {allow}, CT: {ct[:50]}, CL: {cl}")

    # ========================================
    # TEST 5: Discover valid proxy sub-paths
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 5: Discover Valid Proxy Sub-paths")
    print("=" * 80)

    # The 405 on POST but 404 on GET suggests these paths exist but only accept certain methods
    # Try to find what paths return different status codes
    discovery_paths = [
        # Common web app paths
        "login", "auth", "token", "session", "user", "api",
        # ChaoXing specific
        "note", "notes", "document", "course", "class",
        # WebSocket-like
        "ws", "websocket", "socket", "connect",
        # Static resources
        "static", "assets", "js", "css", "img",
        # Health/admin
        "health", "status", "admin", "config", "info",
        # Proxy-specific
        "forward", "relay", "gateway", "route",
    ]

    for base in ["https://noteyd.chaoxing.com/proxy", "https://noteyd.chaoxing.com/comm"]:
        print(f"\n  --- {base} ---")
        for path in discovery_paths:
            url = f"{base}/{path}"
            # GET
            status, text, hdrs = req_detail(stu_session, url, method="GET")
            if str(status) not in ("404",):
                print(f"    [GET] {path} => {status}")
            # POST
            status, text, hdrs = req_detail(stu_session, url, method="POST", data={"test": "1"})
            if str(status) not in ("404", "405"):
                print(f"    [POST] {path} => {status}")

    # ========================================
    # TEST 6: Test noteyd.chaoxing.com root with various paths
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 6: noteyd.chaoxing.com Root Path Discovery")
    print("=" * 80)

    root_discovery = [
        "api", "v1", "v2", "login", "auth", "sign", "check",
        "index", "main", "home", "app", "web",
        "mooc", "study", "course", "clazz",
    ]

    for path in root_discovery:
        url = f"https://noteyd.chaoxing.com/{path}"
        status, text, hdrs = req_detail(stu_session, url, method="GET")
        if str(status) not in ("404",):
            print(f"  [GET] /{path} => {status}, CT: {hdrs.get('Content-Type', '')[:50]}")
        status, text, hdrs = req_detail(stu_session, url, method="POST", data={"test": "1"})
        if str(status) not in ("404", "405"):
            print(f"  [POST] /{path} => {status}")

    # ========================================
    # TEST 7: Test appswh.chaoxing.com root path discovery
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 7: appswh.chaoxing.com Root Path Discovery")
    print("=" * 80)

    for path in root_discovery:
        url = f"https://appswh.chaoxing.com/{path}"
        status, text, hdrs = req_detail(stu_session, url, method="GET")
        if str(status) not in ("404",):
            print(f"  [GET] /{path} => {status}, CT: {hdrs.get('Content-Type', '')[:50]}")

    # ========================================
    # TEST 8: Analyze the 400 response on base domain
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 8: Analyze 400 Response on Base Domain")
    print("=" * 80)

    url = "https://noteyd.chaoxing.com"
    status, text, hdrs = req_detail(stu_session, url, method="GET")
    print(f"  Status: {status}")
    print(f"  Headers: {json.dumps(hdrs, indent=2)}")
    print(f"  Full body:\n{text}")

    # ========================================
    # TEST 9: Test with different Host headers
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 9: Host Header Manipulation on Proxy")
    print("=" * 80)

    url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
    host_headers = [
        {"Host": "mooc1-api.chaoxing.com"},
        {"Host": "mooc1-1.chaoxing.com"},
        {"Host": "mooc1-2.chaoxing.com"},
        {"Host": "i.chaoxing.com"},
        {"X-Forwarded-Host": "mooc1-api.chaoxing.com"},
    ]

    for hh in host_headers:
        sign_params = {"activeId": ACTIVE_ID, "uid": stu_puid, "courseId": COURSE_ID, "classId": CLASS_ID, "signType": "0", "clientType": "1"}
        status, text, hdrs = req_detail(stu_session, url, method="POST", data=sign_params, headers_extra=hh)
        print(f"  {hh} => {status}")
        if str(status) not in ("405",):
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 10: Check if proxy path is a SPA (Single Page Application)
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 10: Check if Proxy Path is a SPA")
    print("=" * 80)

    # SPAs often serve the same HTML for all paths
    # Check if the 405 page is actually a custom error page from a SPA framework
    spa_paths = [
        "https://noteyd.chaoxing.com/proxy/index.html",
        "https://noteyd.chaoxing.com/proxy/main.html",
        "https://noteyd.chaoxing.com/proxy/app.js",
        "https://noteyd.chaoxing.com/proxy/manifest.json",
        "https://noteyd.chaoxing.com/proxy/favicon.ico",
        "https://noteyd.chaoxing.com/comm/index.html",
        "https://noteyd.chaoxing.com/comm/manifest.json",
    ]

    for url in spa_paths:
        status, text, hdrs = req_detail(stu_session, url, method="GET")
        print(f"  [GET] {url} => {status}, CT: {hdrs.get('Content-Type', '')[:50]}")
        if str(status) == "200":
            print(f"    Body: {text[:200]}")

    print("\n" + "=" * 80)
    print("PHASE 3 COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
