import subprocess
import json
import time
import re
import os
import warnings
warnings.filterwarnings("ignore")

MOBILE_UA = "Dalvik/2.1.0 (Linux; U; Android 11; M2007J3SC Build/RKQ1.200826.002) (device:M2007J3SC) Language/zh_CN com.chaoxing.mobile/ChaoXingStudy_3_5.1.3_android_phone_613_74"

LOGIN_URL = "https://passport2-api.chaoxing.com/v11/loginregister"
WEB_LOGIN_URL = "https://passport2.chaoxing.com/fanyaloginnew"
COURSE_URL = "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata"
ACTIVITY_URL = "https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist"
SIGN_DETAIL_URL = "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo"

TEACHER_UNAME = "19712720708"
TEACHER_CODE = "3.1415926Cpy"
STUDENT_UNAME = "18436633997"
STUDENT_CODE = "3.1415926Cpy"

COURSE_ID = "257485372"
CLASS_ID = "132821141"

API_ENDPOINTS = [
    "/ppt/activeAPI/getPPTActiveInfo",
    "/ppt/activeAPI/taskactivelist",
    "/ppt/activeAPI/startSign",
    "/ppt/activeAPI/endActive",
    "/ppt/activeAPI/updateSignStatus",
    "/ppt/activeAPI/signedResult",
    "/ppt/activeAPI/getActiveDetail",
    "/ppt/activeAPI/modifySign",
    "/pptSign/signedResult",
    "/pptSign/updateSign",
    "/pptSign/updateSignStatus",
    "/pptSign/preSign",
    "/pptSign/stuSignajax",
    "/pptSign/teacherSignajax",
    "/pptSign/signResult",
    "/pptSign/modifySignResult",
    "/pptSign/changeSignStatus",
]

results = []

def log(msg):
    print(msg, flush=True)
    results.append(str(msg))

def parse_cookie_jar(path):
    cookies = {}
    if not os.path.exists(path):
        return cookies
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") and not line.startswith("#HttpOnly_"):
                continue
            actual_line = line
            if line.startswith("#HttpOnly_"):
                actual_line = line[len("#HttpOnly_"):]
            parts = actual_line.split("\t")
            if len(parts) >= 7:
                domain = parts[0]
                name = parts[5]
                value = parts[6]
                if domain not in cookies:
                    cookies[domain] = {}
                cookies[domain][name] = value
    return cookies

def write_cookie_jar(path, cookies_dict):
    with open(path, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# https://curl.se/docs/http-cookies.html\n")
        f.write("# This file was generated! Edit at your own risk.\n\n")
        for domain, cookies in cookies_dict.items():
            for name, value in cookies.items():
                http_only = "#HttpOnly_" if "JSESSIONID" in name else ""
                f.write(f"{http_only}{domain}\tFALSE\t/\tFALSE\t0\t{name}\t{value}\n")

def curl_request(url, cookie_jar, method="GET", data=None, params=None, timeout=15, extra_headers=None):
    if params:
        sep = "&" if "?" in url else "?"
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        url = url + sep + param_str

    cmd = [
        "curl", "-s", "-k",
        "-L", "--max-redirs", "10",
        "--max-time", str(timeout),
        "-H", f"User-Agent: {MOBILE_UA}",
        "-b", cookie_jar,
        "-c", cookie_jar,
    ]

    if extra_headers:
        for h in extra_headers:
            cmd.extend(["-H", h])

    if method == "POST" and data:
        cmd.extend(["-X", "POST"])
        for k, v in data.items():
            cmd.extend(["-d", f"{k}={v}"])

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

def curl_request_with_headers(url, cookie_jar, method="GET", data=None, params=None, timeout=15, extra_headers=None):
    if params:
        sep = "&" if "?" in url else "?"
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        url = url + sep + param_str

    cmd = [
        "curl", "-s", "-k",
        "-D", "/tmp/curl_headers.txt",
        "-L", "--max-redirs", "10",
        "--max-time", str(timeout),
        "-H", f"User-Agent: {MOBILE_UA}",
        "-b", cookie_jar,
        "-c", cookie_jar,
    ]

    if extra_headers:
        for h in extra_headers:
            cmd.extend(["-H", h])

    if method == "POST" and data:
        cmd.extend(["-X", "POST"])
        for k, v in data.items():
            cmd.extend(["-d", f"{k}={v}"])

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        headers = ""
        if os.path.exists("/tmp/curl_headers.txt"):
            with open("/tmp/curl_headers.txt", "r") as f:
                headers = f.read()
        return result.stdout, headers
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    except Exception as e:
        return f"ERROR: {e}", ""

def login_and_get_session(uname, code, label):
    cookie_jar = f"/tmp/chaoxing_{label}_cookies.txt"
    if os.path.exists(cookie_jar):
        os.remove(cookie_jar)

    # Strategy: Use API login first to get UID, then use web SSO flow
    # Step 1: API login to get UID
    data = {
        "uname": uname,
        "code": code,
        "loginType": "1",
        "roleSelect": "true",
    }
    login_result = curl_request(LOGIN_URL, cookie_jar, method="POST", data=data)
    log(f"[API LOGIN] {uname}")

    uid = None
    web_url = None
    try:
        rj = json.loads(login_result)
        uid = rj.get("uid", None)
        web_url = rj.get("webUrl", None)
        if not uid and web_url and "uid=" in web_url:
            uid = web_url.split("uid=")[1].split("&")[0]
    except:
        pass
    log(f"  UID: {uid}")

    # Step 2: Use web login form to establish proper SSO session
    # First visit the login page to get JSESSIONID for passport2.chaoxing.com
    curl_request("https://passport2.chaoxing.com/login", cookie_jar)

    # Now login via the web form
    web_data = {
        "fid": "-1",
        "uname": uname,
        "password": code,
        "refer": "https://i.chaoxing.com/base",
        "t": "true",
        "forbidotherurl": "0",
        "validate": "",
        "doubleFactorLogin": "0",
        "independentId": "0",
    }

    # Try the fanyaloginnew endpoint
    result, headers = curl_request_with_headers(
        WEB_LOGIN_URL, cookie_jar,
        method="POST", data=web_data,
        extra_headers=[
            "Referer: https://passport2.chaoxing.com/login",
            "X-Requested-With: XMLHttpRequest",
            "Content-Type: application/x-www-form-urlencoded",
        ]
    )
    log(f"[WEB LOGIN] Response: {result[:500]}")
    log(f"[WEB LOGIN] Headers: {headers[:500]}")

    # Step 3: Visit i.chaoxing.com/base to establish session there
    result = curl_request("https://i.chaoxing.com/base", cookie_jar)
    is_login = "登录" in result[:500]
    log(f"[BASE] is_login_page={is_login}")

    # Step 4: If still not logged in, try alternative web login
    if is_login:
        log("[BASE] Still on login page, trying alternative login...")

        # Try login with the standard form
        alt_data = {
            "uname": uname,
            "password": code,
        }
        result = curl_request(
            "https://passport2.chaoxing.com/fanyaloginnew",
            cookie_jar,
            method="POST",
            data=alt_data,
            extra_headers=[
                "Referer: https://passport2.chaoxing.com/login",
            ]
        )
        log(f"[ALT LOGIN] Response: {result[:500]}")

        # Visit base again
        result = curl_request("https://i.chaoxing.com/base", cookie_jar)
        is_login = "登录" in result[:500]
        log(f"[BASE-2] is_login_page={is_login}")

    # Print final cookies
    cookies = parse_cookie_jar(cookie_jar)
    log(f"[FINAL COOKIES] domains: {list(cookies.keys())}")
    for domain, cks in cookies.items():
        log(f"  {domain}: {list(cks.keys())}")

    # Test mooc1-api
    result = curl_request(COURSE_URL, cookie_jar, params={"view": "3", "courseType": "1"})
    is_login = "登录" in result[:500]
    log(f"[MOOC1-TEST] is_login_page={is_login}")

    # If mooc1-api works, try mobilelearn
    if not is_login:
        result = curl_request(ACTIVITY_URL, cookie_jar, params={
            "courseId": COURSE_ID, "classId": CLASS_ID, "uid": uid or "0"
        })
        log(f"[MOBILELEARN-TEST] response[:300]: {result[:300]}")

    return cookie_jar, uid

def get_courses(cookie_jar, label):
    result = curl_request(COURSE_URL, cookie_jar, params={"view": "3", "courseType": "1"})
    log(f"\n[{label} COURSES]")

    try:
        rj = json.loads(result)
        channel_list = rj.get("channelList", [])
        if not channel_list:
            log(f"  channelList empty. Response: {result[:500]}")
            return []
        for ch in channel_list:
            cinfo = ch.get("course", {})
            cname = cinfo.get("name", "N/A")
            cid = cinfo.get("id", "N/A")
            clist = ch.get("clazzList", [])
            class_info = ""
            for cl in clist:
                class_info += f"\n    classId={cl.get('id','?')}, className={cl.get('name','?')}"
            log(f"  courseId={cid}, courseName={cname}{class_info}")
        return channel_list
    except Exception as e:
        log(f"  JSON parse error: {e}")
        log(f"  Response[:500]: {result[:500]}")
        return []

def get_activities(cookie_jar, uid, label):
    params = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "uid": uid or "0",
    }
    result = curl_request(ACTIVITY_URL, cookie_jar, params=params)
    log(f"\n[{label} ACTIVITIES]")

    activities = []
    try:
        rj = json.loads(result)
        act_list = rj.get("activeList", [])
        error_msg = rj.get("errorMsg", "")
        if error_msg:
            log(f"  errorMsg: {error_msg}")
        if not act_list:
            log(f"  activeList empty. Response: {result[:500]}")
            return []
        for act in act_list:
            aid = act.get("id", "N/A")
            atype = act.get("type", "N/A")
            aname = act.get("nameOne", "")
            status = act.get("status", "N/A")
            is_existed = act.get("isExisted", "N/A")
            log(f"  activeId={aid}, type={atype}, name={aname}, status={status}, isExisted={is_existed}")
            activities.append(act)
        return act_list
    except Exception as e:
        log(f"  JSON parse error: {e}")
        log(f"  Response[:500]: {result[:500]}")
        return []

def check_student_sign_status(cookie_jar, active_id, student_uid):
    detail_params = {"activeId": active_id}
    result = curl_request(SIGN_DETAIL_URL, cookie_jar, params=detail_params)
    log(f"  [SIGN DETAIL v2] activeId={active_id}")
    log(f"  detail: {result[:500]}")

    v1_url = "https://mobilelearn.chaoxing.com/ppt/activeAPI/getPPTActiveInfo"
    result2 = curl_request(v1_url, cookie_jar, params=detail_params)
    log(f"  [SIGN DETAIL v1] activeId={active_id}")
    log(f"  detail: {result2[:500]}")

    sign_result_url = "https://mobilelearn.chaoxing.com/pptSign/signedResult"
    params2 = {"activeId": active_id}
    for m in ["GET", "POST"]:
        if m == "GET":
            result3 = curl_request(sign_result_url, cookie_jar, params=params2)
        else:
            result3 = curl_request(sign_result_url, cookie_jar, method="POST", data=params2)
        log(f"  [SIGNED RESULT {m}] activeId={active_id}")
        log(f"  result: {result3[:500]}")

def enumerate_apis(cookie_jar, active_id=None, uid=None):
    base = "https://mobilelearn.chaoxing.com"
    log(f"\n{'='*80}")
    log("API ENUMERATION RESULTS")
    log(f"{'='*80}")

    meaningful_apis = []

    for endpoint in API_ENDPOINTS:
        url = base + endpoint
        for method in ["GET", "POST"]:
            try:
                params = {}
                if active_id and str(active_id) != "0":
                    params["activeId"] = str(active_id)
                if uid:
                    params["uid"] = str(uid)
                if "taskactivelist" in endpoint:
                    params["courseId"] = COURSE_ID
                    params["classId"] = CLASS_ID

                if method == "GET":
                    body = curl_request(url, cookie_jar, params=params, timeout=10)
                else:
                    body = curl_request(url, cookie_jar, method="POST", data=params, timeout=10)

                is_html = body.strip().startswith("<!DOCTYPE") or body.strip().startswith("<html")
                is_500 = "500 Internal Server Error" in body[:200]
                is_empty = len(body.strip()) < 5
                is_meaningful = not is_html and not is_500 and not is_empty and body != "TIMEOUT"

                tag = " *** MEANINGFUL ***" if is_meaningful else ""
                log(f"\n[{method}] {endpoint}")
                log(f"  Response: {body[:500]}{tag}")

                if is_meaningful:
                    meaningful_apis.append({
                        "endpoint": endpoint,
                        "method": method,
                        "response": body[:500],
                    })
            except Exception as e:
                log(f"\n[{method}] {endpoint}")
                log(f"  Error: {e}")

    # v2 APIs
    log(f"\n--- 额外v2 API测试 ---")
    v2_endpoints = [
        "/v2/apis/active/getPPTActiveInfo",
        "/v2/apis/active/startSign",
        "/v2/apis/active/endActive",
        "/v2/apis/active/updateSignStatus",
        "/v2/apis/active/signedResult",
        "/v2/apis/active/modifySign",
        "/v2/apis/sign/startSign",
        "/v2/apis/sign/endActive",
        "/v2/apis/sign/updateSignStatus",
        "/v2/apis/sign/signedResult",
        "/v2/apis/sign/modifySign",
    ]

    for endpoint in v2_endpoints:
        url = base + endpoint
        for method in ["GET", "POST"]:
            try:
                params = {"activeId": str(active_id or "0")}
                if method == "GET":
                    body = curl_request(url, cookie_jar, params=params, timeout=10)
                else:
                    body = curl_request(url, cookie_jar, method="POST", data=params, timeout=10)
                is_html = body.strip().startswith("<!DOCTYPE") or body.strip().startswith("<html")
                is_500 = "500 Internal Server Error" in body[:200]
                is_empty = len(body.strip()) < 5
                is_meaningful = not is_html and not is_500 and not is_empty and body != "TIMEOUT"
                tag = " *** MEANINGFUL ***" if is_meaningful else ""
                log(f"\n[{method}] {endpoint}")
                log(f"  Response: {body[:500]}{tag}")
                if is_meaningful:
                    meaningful_apis.append({
                        "endpoint": endpoint,
                        "method": method,
                        "response": body[:500],
                    })
            except Exception as e:
                log(f"\n[{method}] {endpoint} => Error: {e}")

    # Summary
    log(f"\n{'='*80}")
    log("MEANINGFUL API SUMMARY")
    log(f"{'='*80}")
    if not meaningful_apis:
        log("  (none found)")
    for api in meaningful_apis:
        log(f"  [{api['method']}] {api['endpoint']}")
        log(f"    Response: {api['response'][:300]}")

    log(f"\n{'='*80}")
    log("POTENTIAL SIGN-STATUS-MODIFY APIs")
    log(f"{'='*80}")
    modify_keywords = ["modify", "update", "change"]
    found = False
    for api in meaningful_apis:
        ep = api["endpoint"].lower()
        if any(kw in ep for kw in modify_keywords):
            found = True
            log(f"  ** [{api['method']}] {api['endpoint']}")
            log(f"     Response: {api['response'][:300]}")
    if not found:
        log("  (none found among meaningful APIs)")

    return meaningful_apis

def main():
    log("=" * 80)
    log("学习通安全审计 - 任务1: 确认测试环境")
    log("=" * 80)

    log("\n" + "=" * 40)
    log("--- 教师账号 ---")
    log("=" * 40)
    t_jar, t_uid = login_and_get_session(TEACHER_UNAME, TEACHER_CODE, "teacher")

    log("\n--- 教师课程列表 ---")
    t_courses = get_courses(t_jar, "TEACHER")

    log("\n--- 教师活动列表 ---")
    t_activities = get_activities(t_jar, t_uid, "TEACHER")

    log("\n" + "=" * 40)
    log("--- 学生账号 ---")
    log("=" * 40)
    s_jar, s_uid = login_and_get_session(STUDENT_UNAME, STUDENT_CODE, "student")

    log("\n--- 学生课程列表 ---")
    s_courses = get_courses(s_jar, "STUDENT")

    log("\n--- 学生活动列表 ---")
    s_activities = get_activities(s_jar, s_uid, "STUDENT")

    log("\n" + "=" * 40)
    log("--- 签到活动缺勤检查 ---")
    log("=" * 40)

    sign_activities = []
    for act in s_activities:
        if act.get("type") == 2:
            sign_activities.append(act)
    if not sign_activities:
        log("学生活动列表中无签到活动，从教师列表获取...")
        for act in t_activities:
            if act.get("type") == 2:
                sign_activities.append(act)

    if sign_activities:
        for act in sign_activities:
            aid = act.get("id", "")
            log(f"\n检查签到活动: activeId={aid}, name={act.get('nameOne','')}")
            check_student_sign_status(s_jar, aid, s_uid)
    else:
        log("未找到任何签到活动")

    log("\n" + "=" * 80)
    log("学习通安全审计 - 任务2: 教师端签到管理API发现")
    log("=" * 80)

    first_sign_id = None
    for act in sign_activities:
        first_sign_id = act.get("id", None)
        if first_sign_id:
            break
    if not first_sign_id:
        first_sign_id = "0"

    log(f"\n使用 activeId={first_sign_id}, uid={t_uid} 进行API枚举")
    meaningful = enumerate_apis(t_jar, active_id=first_sign_id, uid=t_uid)

    with open("/workspace/deep_sign_test_result1.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(str(r) for r in results))
    log(f"\n结果已保存到 /workspace/deep_sign_test_result1.txt")

if __name__ == "__main__":
    main()
