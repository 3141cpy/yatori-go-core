#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSRF漏洞综合测试脚本 - 超星学习通
测试模块: 作业/考试、人脸识别、云盘、其他模块
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量配置 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"

STUDENT_PHONE = "18436933997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

# 结果收集
results = []

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

def trunc_resp(text, maxlen=200):
    if not text:
        return ""
    t = text.strip()[:maxlen]
    return t

def classify_csrf(variant_results):
    """
    variant_results: list of dict with keys: variant, status_code, success, resp_snippet
    success = True means the server processed the request (not blocked by CSRF)
    """
    blocked = sum(1 for r in variant_results if not r.get("success", False))
    total = len(variant_results)
    if total == 0:
        return "UNKNOWN", ""
    # If all variants succeed => FULL CSRF vulnerability
    if blocked == 0:
        return "FULL", "所有CSRF变体均成功，无任何CSRF防护"
    # If some blocked, some not => PARTIAL
    if blocked < total:
        return "PARTIAL", f"{blocked}/{total} 变体被阻止，存在部分CSRF防护"
    # All blocked
    return "NONE", "所有CSRF变体均被阻止，CSRF防护有效"

def test_csrf_variants(session, method, url, params=None, data=None, json_body=None, files=None, desc=""):
    """
    Test an endpoint with multiple CSRF variants.
    Returns list of variant results.
    """
    variant_results = []

    # Variant 1: GET request (simplest CSRF)
    if method.upper() in ("GET", "BOTH"):
        try:
            r = session.get(url, params=params, timeout=20, allow_redirects=False)
            success = r.status_code == 200
            variant_results.append({
                "variant": "GET请求",
                "status_code": r.status_code,
                "success": success,
                "resp_snippet": trunc_resp(r.text)
            })
        except Exception as e:
            variant_results.append({
                "variant": "GET请求",
                "status_code": "ERR",
                "success": False,
                "resp_snippet": str(e)[:200]
            })

    # Variant 2: POST without Referer
    if method.upper() in ("POST", "BOTH"):
        headers_no_ref = {k: v for k, v in session.headers.items() if k.lower() != "referer"}
        try:
            r = session.post(url, data=data, json=json_body, files=files, timeout=20,
                           allow_redirects=False, headers=headers_no_ref)
            success = r.status_code == 200
            variant_results.append({
                "variant": "POST无Referer",
                "status_code": r.status_code,
                "success": success,
                "resp_snippet": trunc_resp(r.text)
            })
        except Exception as e:
            variant_results.append({
                "variant": "POST无Referer",
                "status_code": "ERR",
                "success": False,
                "resp_snippet": str(e)[:200]
            })

        # Variant 3: POST with evil Referer
        try:
            r = session.post(url, data=data, json=json_body, files=files, timeout=20,
                           allow_redirects=False, headers={"Referer": "https://evil.com/"})
            success = r.status_code == 200
            variant_results.append({
                "variant": "POST evil Referer",
                "status_code": r.status_code,
                "success": success,
                "resp_snippet": trunc_resp(r.text)
            })
        except Exception as e:
            variant_results.append({
                "variant": "POST evil Referer",
                "status_code": "ERR",
                "success": False,
                "resp_snippet": str(e)[:200]
            })

        # Variant 4: POST with evil Origin
        try:
            r = session.post(url, data=data, json=json_body, files=files, timeout=20,
                           allow_redirects=False, headers={"Origin": "https://evil.com"})
            success = r.status_code == 200
            variant_results.append({
                "variant": "POST evil Origin",
                "status_code": r.status_code,
                "success": success,
                "resp_snippet": trunc_resp(r.text)
            })
        except Exception as e:
            variant_results.append({
                "variant": "POST evil Origin",
                "status_code": "ERR",
                "success": False,
                "resp_snippet": str(e)[:200]
            })

        # Variant 5: POST without X-Requested-With
        headers_no_xrw = {k: v for k, v in session.headers.items() if k.lower() != "x-requested-with"}
        try:
            r = session.post(url, data=data, json=json_body, files=files, timeout=20,
                           allow_redirects=False, headers=headers_no_xrw)
            success = r.status_code == 200
            variant_results.append({
                "variant": "POST无X-Requested-With",
                "status_code": r.status_code,
                "success": success,
                "resp_snippet": trunc_resp(r.text)
            })
        except Exception as e:
            variant_results.append({
                "variant": "POST无X-Requested-With",
                "status_code": "ERR",
                "success": False,
                "resp_snippet": str(e)[:200]
            })

    return variant_results

def print_variant_results(endpoint, variant_results):
    """Print results for a single endpoint's CSRF variants."""
    print(f"\n  端点: {endpoint}")
    print(f"  {'变体':<25} {'状态码':<10} {'成功':<8} {'响应摘要'}")
    print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*40}")
    for vr in variant_results:
        succ = "是" if vr["success"] else "否"
        print(f"  {vr['variant']:<25} {str(vr['status_code']):<10} {succ:<8} {vr['resp_snippet'][:80]}")

def record_result(module, endpoint, method, csrf_status, impact, notes):
    results.append({
        "module": module,
        "endpoint": endpoint,
        "method": method,
        "csrf_status": csrf_status,
        "impact": impact,
        "notes": notes
    })
    marker = ""
    if csrf_status == "FULL":
        marker = " !!!CSRF!!!"
    elif csrf_status == "PARTIAL":
        marker = " ***PARTIAL***"
    print(f"  >> CSRF状态: {csrf_status}{marker} | 影响: {impact} | 备注: {notes}")


# ============ 主测试流程 ============
def main():
    print("=" * 80)
    print("超星学习通 CSRF 漏洞综合测试")
    print("=" * 80)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # ---- 登录 ----
    print("[*] 正在登录学生账号...")
    stu_sess, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {stu_puid or '未获取'}")

    print("[*] 正在登录教师账号...")
    tea_sess, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {tea_puid or '未获取'}")
    print()

    if not stu_puid and not tea_puid:
        print("[!] 两个账号均登录失败，继续测试但结果可能不准确")
    print()

    # ================================================================
    # Part 1: 作业/考试模块 CSRF 测试
    # ================================================================
    print("=" * 80)
    print("Part 1: 作业/考试模块 CSRF 测试")
    print("=" * 80)

    work_exam_endpoints = [
        # (url, method, params/data description)
        ("https://mooc1-api.chaoxing.com/mooc-ans/work/doHomeWork",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0", "userid": stu_puid},
         "提交作业"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/work/saveWork",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "workId": "0", "userid": stu_puid},
         "保存作业"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/exam/test/reStartTest",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0"},
         "重新开始考试"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/exam/test/saveExam",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0"},
         "保存考试"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/exam/test/submitExam",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0"},
         "提交考试"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/work/addStudentWork",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "workId": "0", "userid": stu_puid},
         "添加学生作业"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/api/work/startwork",
         "GET",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0", "enc": "0"},
         "开始作业API"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/api/exam/startexam",
         "GET",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0"},
         "开始考试API"),
        # mooc1.chaoxing.com variants
        ("https://mooc1.chaoxing.com/mooc-ans/work/doHomeWork",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0", "userid": stu_puid},
         "提交作业(mooc1)"),
        ("https://mooc1.chaoxing.com/mooc-ans/exam/test/submitExam",
         "POST",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "api": "1", "workId": "0", "answerId": "0"},
         "提交考试(mooc1)"),
    ]

    for url, method, data, desc in work_exam_endpoints:
        print(f"\n--- 测试: {desc} ---")
        print(f"    URL: {url}")
        print(f"    方法: {method}")
        vr = test_csrf_variants(stu_sess, method, url, data=data, desc=desc)
        print_variant_results(url, vr)
        csrf_status, csrf_note = classify_csrf(vr)
        impact = ""
        if "提交" in desc or "保存" in desc:
            impact = "可伪造提交/保存操作"
        elif "重新" in desc:
            impact = "可伪造重开考试"
        elif "开始" in desc:
            impact = "可伪造开始作业/考试"
        elif "添加" in desc:
            impact = "可伪造添加作业"
        else:
            impact = "可伪造相关操作"
        record_result("作业/考试", url, method, csrf_status, impact, f"{desc}; {csrf_note}")
        time.sleep(0.5)

    # ================================================================
    # Part 2: 人脸识别模块 CSRF 测试
    # ================================================================
    print("\n" + "=" * 80)
    print("Part 2: 人脸识别模块 CSRF 测试")
    print("=" * 80)

    # 2.1 updateqrstatus
    print("\n--- 2.1 更新二维码状态 (updateqrstatus) ---")
    url = "https://mooc1-api.chaoxing.com/qr/updateqrstatus"
    data = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": "test_csrf",
        "qrcEnc": "test",
        "objectId": "test",
        "failCount": "0",
        "compareResult": "0"
    }
    vr = test_csrf_variants(stu_sess, "POST", url, data=data)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("人脸识别", url, "POST", csrf_status, "可伪造人脸识别签到状态", csrf_note)
    time.sleep(0.5)

    # 2.2 clientfacecheckstatus
    print("\n--- 2.2 客户端人脸检测状态 (clientfacecheckstatus) ---")
    url = "https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus"
    params = {
        "courseId": COURSE_ID,
        "clazzId": CLASS_ID,
        "cpi": "0",
        "chapterId": "0",
        "objectId": "test",
        "type": "1"
    }
    vr = test_csrf_variants(stu_sess, "BOTH", url, params=params, data=params)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("人脸识别", url, "GET/POST", csrf_status, "可获取/伪造人脸检测状态", csrf_note)
    time.sleep(0.5)

    # 2.3 uploadInfo
    print("\n--- 2.3 上传学习信息 (uploadInfo) ---")
    url = "https://mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo"
    data = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "knowledgeId": "0",
        "uuid": "",
        "qrcEnc": "",
        "objectId": "test"
    }
    vr = test_csrf_variants(stu_sess, "POST", url, data=data)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("人脸识别", url, "POST", csrf_status, "可伪造学习信息上传", csrf_note)
    time.sleep(0.5)

    # 2.4 continuelearn
    print("\n--- 2.4 继续学习 (continuelearn) ---")
    url = "https://mooc1-api.chaoxing.com/mooc-ans/facephoto/continuelearn"
    params = {
        "courseId": COURSE_ID,
        "clazzId": CLASS_ID,
        "cpi": "0",
        "objectId": "test",
        "errorLogId": "0",
        "type": "1"
    }
    vr = test_csrf_variants(stu_sess, "GET", url, params=params)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("人脸识别", url, "GET", csrf_status, "可伪造继续学习请求绕过人脸", csrf_note)
    time.sleep(0.5)

    # 2.5 startface
    print("\n--- 2.5 开始人脸识别 (startface) ---")
    url = "https://mooc1-api.chaoxing.com/mooc-ans/knowledge/startface"
    params = {
        "clazzid": CLASS_ID,
        "courseid": COURSE_ID,
        "knowledgeid": "0",
        "cpi": "0",
        "type": "1"
    }
    vr = test_csrf_variants(stu_sess, "GET", url, params=params)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("人脸识别", url, "GET", csrf_status, "可伪造发起人脸识别", csrf_note)
    time.sleep(0.5)

    # ================================================================
    # Part 3: 云盘模块 CSRF 测试
    # ================================================================
    print("\n" + "=" * 80)
    print("Part 3: 云盘模块 CSRF 测试")
    print("=" * 80)

    # 3.1 uservalid - token获取
    print("\n--- 3.1 获取用户Token (uservalid) ---")
    url = "https://pan-yz.chaoxing.com/api/token/uservalid"
    vr = test_csrf_variants(stu_sess, "GET", url)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    # Check if token is in response
    token_found = False
    for vr_item in vr:
        if vr_item["success"] and ("token" in vr_item["resp_snippet"].lower() or "token" in vr_item["resp_snippet"]):
            token_found = True
            break
    impact = "可获取用户云盘Token(信息泄露)" if token_found else "可能获取用户Token"
    record_result("云盘", url, "GET", csrf_status, impact, csrf_note)
    time.sleep(0.5)

    # 3.2 upload - 文件上传
    print("\n--- 3.2 文件上传 (upload) ---")
    url = "https://pan-yz.chaoxing.com/upload"
    # Test POST without file first (to check if endpoint is reachable)
    vr = test_csrf_variants(stu_sess, "POST", url, data={"puid": stu_puid or "0"})
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("云盘", url, "POST", csrf_status, "可伪造文件上传", csrf_note)
    time.sleep(0.5)

    # 3.3 groupweb resource endpoints (GET - trivially exploitable)
    print("\n--- 3.3 资源管理端点 (groupweb - GET方法) ---")
    resource_endpoints = [
        (f"https://groupweb.chaoxing.com/pc/resource/addResource?bbsid=test&pid=-1&type=yunpan&params=[]",
         "GET", "添加资源"),
        (f"https://groupweb.chaoxing.com/pc/resource/addResourceFolder?bbsid=test&name=CSRF_TEST&pid=-1",
         "GET", "添加资源文件夹"),
        (f"https://groupweb.chaoxing.com/pc/resource/deleteResourceFile?bbsid=test&recIds=1",
         "GET", "删除资源文件"),
        (f"https://groupweb.chaoxing.com/pc/resource/deleteResourceFolder?bbsid=test&folderIds=1",
         "GET", "删除资源文件夹"),
        (f"https://groupweb.chaoxing.com/pc/resource/moveResource?bbsid=test&recIds=1&targetId=-1",
         "GET", "移动资源"),
        (f"https://groupweb.chaoxing.com/pc/resource/updateResourceFolderName?bbsid=test&folderId=1&name=CSRF_TEST",
         "GET", "重命名资源文件夹"),
    ]

    for url, method, desc in resource_endpoints:
        print(f"\n  测试: {desc}")
        vr = test_csrf_variants(stu_sess, method, url)
        print_variant_results(url, vr)
        csrf_status, csrf_note = classify_csrf(vr)
        impact = ""
        if "删除" in desc:
            impact = "可伪造删除资源(GET方法极易利用)"
        elif "添加" in desc:
            impact = "可伪造添加资源(GET方法极易利用)"
        elif "移动" in desc:
            impact = "可伪造移动资源(GET方法极易利用)"
        elif "重命名" in desc:
            impact = "可伪造重命名资源(GET方法极易利用)"
        record_result("云盘", url, "GET", csrf_status, impact, f"{desc}; {csrf_note}")
        time.sleep(0.3)

    # ================================================================
    # Part 4: 其他模块 CSRF 测试
    # ================================================================
    print("\n" + "=" * 80)
    print("Part 4: 其他模块 CSRF 测试")
    print("=" * 80)

    # 4.1 AI模块
    print("\n--- 4.1 AI模块 ---")
    url = "https://stat2-ans.chaoxing.com/stat2/bot/talk-v1"
    json_body = {"question": "test", "courseId": COURSE_ID}
    vr = test_csrf_variants(stu_sess, "POST", url, json_body=json_body)
    print_variant_results(url, vr)
    csrf_status, csrf_note = classify_csrf(vr)
    record_result("AI模块", url, "POST", csrf_status, "可伪造AI对话请求", csrf_note)
    time.sleep(0.5)

    # 4.2 讨论模块
    print("\n--- 4.2 讨论模块 ---")
    discussion_endpoints = [
        ("https://mooc1-api.chaoxing.com/mooc-ans/bbscircle/topic/add",
         "POST",
         {"courseId": COURSE_ID, "clazzId": CLASS_ID, "title": "CSRF_TEST", "content": "CSRF_TEST"},
         "添加话题"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/bbscircle/reply/add",
         "POST",
         {"courseId": COURSE_ID, "clazzId": CLASS_ID, "topicId": "0", "content": "CSRF_TEST"},
         "添加回复"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/bbscircle/topic/delete",
         "POST",
         {"courseId": COURSE_ID, "clazzId": CLASS_ID, "topicId": "0"},
         "删除话题"),
    ]

    for url, method, data, desc in discussion_endpoints:
        print(f"\n  测试: {desc}")
        vr = test_csrf_variants(stu_sess, method, url, data=data)
        print_variant_results(url, vr)
        csrf_status, csrf_note = classify_csrf(vr)
        impact = ""
        if "删除" in desc:
            impact = "可伪造删除讨论话题"
        elif "添加" in desc:
            impact = "可伪造发布讨论内容"
        record_result("讨论", url, "POST", csrf_status, impact, f"{desc}; {csrf_note}")
        time.sleep(0.3)

    # 4.3 通知模块
    print("\n--- 4.3 通知模块 ---")
    notice_endpoints = [
        ("https://mooc1-api.chaoxing.com/mooc-ans/notice/send",
         "POST",
         {"courseId": COURSE_ID, "clazzId": CLASS_ID, "content": "CSRF_TEST"},
         "发送通知"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/notice/delete",
         "POST",
         {"courseId": COURSE_ID, "clazzId": CLASS_ID, "noticeId": "0"},
         "删除通知"),
    ]

    for url, method, data, desc in notice_endpoints:
        print(f"\n  测试: {desc}")
        vr = test_csrf_variants(stu_sess, method, url, data=data)
        print_variant_results(url, vr)
        csrf_status, csrf_note = classify_csrf(vr)
        impact = ""
        if "发送" in desc:
            impact = "可伪造发送通知"
        elif "删除" in desc:
            impact = "可伪造删除通知"
        record_result("通知", url, "POST", csrf_status, impact, f"{desc}; {csrf_note}")
        time.sleep(0.3)

    # 4.4 个人信息模块
    print("\n--- 4.4 个人信息模块 ---")
    personal_endpoints = [
        ("https://mooc1-api.chaoxing.com/mooc-ans/user/updateUserInfo",
         "POST",
         {"nickname": "CSRF_TEST", "sex": "0"},
         "更新用户信息"),
        ("https://passport2-api.chaoxing.com/api/updateUserFaceid",
         "POST",
         {"faceid": "test"},
         "更新人脸ID"),
    ]

    for url, method, data, desc in personal_endpoints:
        print(f"\n  测试: {desc}")
        vr = test_csrf_variants(stu_sess, method, url, data=data)
        print_variant_results(url, vr)
        csrf_status, csrf_note = classify_csrf(vr)
        impact = ""
        if "人脸" in desc:
            impact = "可伪造更新人脸识别数据"
        elif "用户信息" in desc:
            impact = "可伪造修改用户信息"
        record_result("个人信息", url, "POST", csrf_status, impact, f"{desc}; {csrf_note}")
        time.sleep(0.3)

    # ================================================================
    # 汇总报告
    # ================================================================
    print("\n" + "=" * 80)
    print("CSRF漏洞测试汇总报告")
    print("=" * 80)

    # Count
    full_count = sum(1 for r in results if r["csrf_status"] == "FULL")
    partial_count = sum(1 for r in results if r["csrf_status"] == "PARTIAL")
    none_count = sum(1 for r in results if r["csrf_status"] == "NONE")
    unknown_count = sum(1 for r in results if r["csrf_status"] == "UNKNOWN")

    print(f"\n总计测试端点: {len(results)}")
    print(f"  完全CSRF漏洞 (FULL):   {full_count} !!!CSRF!!!")
    print(f"  部分CSRF防护 (PARTIAL): {partial_count} ***PARTIAL***")
    print(f"  CSRF防护有效 (NONE):    {none_count}")
    print(f"  未知状态 (UNKNOWN):     {unknown_count}")

    print("\n" + "-" * 120)
    print(f"| {'模块':<10} | {'端点':<70} | {'方法':<8} | {'CSRF状态':<10} | {'影响':<25} | {'备注':<30} |")
    print(f"|{'-'*12}|{'-'*72}|{'-'*10}|{'-'*12}|{'-'*27}|{'-'*32}|")
    for r in results:
        marker = ""
        if r["csrf_status"] == "FULL":
            marker = " !!!CSRF!!!"
        elif r["csrf_status"] == "PARTIAL":
            marker = " ***PARTIAL***"
        endpoint_short = r["endpoint"][:68] if len(r["endpoint"]) > 68 else r["endpoint"]
        impact_short = r["impact"][:23] if len(r["impact"]) > 23 else r["impact"]
        notes_short = r["notes"][:28] if len(r["notes"]) > 28 else r["notes"]
        print(f"| {r['module']:<10} | {endpoint_short:<70} | {r['method']:<8} | {r['csrf_status']:<10} | {impact_short:<25} | {notes_short:<30} |{marker}")

    print("\n" + "=" * 80)
    print("高危端点列表 (FULL CSRF):")
    print("=" * 80)
    for r in results:
        if r["csrf_status"] == "FULL":
            print(f"  !!!CSRF!!! {r['module']} | {r['endpoint']} | {r['method']} | {r['impact']}")

    print("\n" + "=" * 80)
    print("部分防护端点列表 (PARTIAL CSRF):")
    print("=" * 80)
    for r in results:
        if r["csrf_status"] == "PARTIAL":
            print(f"  ***PARTIAL*** {r['module']} | {r['endpoint']} | {r['method']} | {r['impact']}")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
