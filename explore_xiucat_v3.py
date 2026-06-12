#!/usr/bin/env python3
"""
xiucat.top V2 API 深入测试 - 使用正确的参数
基于前两轮测试发现:
- /v2/student/sign/activities 需要 schoolId
- /v2/student/sign/normal 需要 courseName, nickname
- /v2/student/sign/qrcode, /v2/student/sign/location 需要 nickname
"""

import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

ACC2_PHONE = "18436633997"
ACC2_PWD = "3.1415926Cpy"
ACC2_PUID = "431407443"

COURSE2_ID = "262934472"
COURSE2_CLASS = "145110605"
COURSE2_NAME = "好好学习，天天向上"
COURSE2_TEACHER = "刘俊琦"

COURSE1_ID = "257485372"
COURSE1_CLASS = "132821141"
COURSE1_NAME = "111"
COURSE1_TEACHER = "陈鹏宇"

def log_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def log_result(label, resp):
    status = resp.status_code if resp else "NO RESPONSE"
    body = ""
    if resp:
        try:
            body = resp.text[:2000]
        except:
            body = "<cannot read body>"
    print(f"  [{label}] Status: {status}")
    print(f"  [{label}] Body: {body}")
    print()

def main():
    print("=" * 70)
    print("  xiucat.top V2 API 参数测试")
    print("=" * 70)

    # ===== Step 1: 登录 xiucat =====
    log_section("Step 1: 登录 xiucat V2")
    r = requests.post("https://api-test.xiucat.top/v2/student/auth/login",
                      json={"phone": ACC2_PHONE, "password": ACC2_PWD},
                      verify=False, timeout=20)
    data = r.json()
    token = data["data"]["tInfo"]["accessToken"]
    user_info = data["data"]["userInfo"]
    print(f"  Token: {token[:50]}...")
    print(f"  UserInfo: {json.dumps(user_info, ensure_ascii=False)}")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ===== Step 2: 获取课程列表 =====
    log_section("Step 2: 获取课程列表")
    r = requests.get("https://api-test.xiucat.top/v2/student/sign/courses",
                     headers=auth_headers, verify=False, timeout=20)
    log_result("courses", r)
    courses = r.json().get("data", [])
    for c in courses:
        print(f"  课程: {c.get('cName')} (csId={c.get('csId')}, clId={c.get('clId')}, tch={c.get('tch')})")

    # ===== Step 3: 获取签到活动 (带schoolId) =====
    log_section("Step 3: 获取签到活动 (带schoolId)")

    # 3a. 尝试 fid=0 (从userInfo获取)
    print("  [3a] 尝试 schoolId=0...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                      headers=auth_headers,
                      json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "0"},
                      verify=False, timeout=20)
    log_result("3a-activities-fid0", r)

    # 3b. 尝试 fid=1257 (从教师账号获取)
    print("  [3b] 尝试 schoolId=1257...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                      headers=auth_headers,
                      json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257"},
                      verify=False, timeout=20)
    log_result("3b-activities-fid1257", r)

    # 3c. 尝试 schoolId=12 (从学生cookie的spaceFid获取)
    print("  [3c] 尝试 schoolId=12...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                      headers=auth_headers,
                      json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "12"},
                      verify=False, timeout=20)
    log_result("3c-activities-fid12", r)

    # 3d. 尝试不带schoolId，带更多参数
    print("  [3d] 尝试更多参数...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                      headers=auth_headers,
                      json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "schoolId": "0", "courseName": COURSE2_NAME},
                      verify=False, timeout=20)
    log_result("3d-activities-more", r)

    # 3e. 尝试Course1
    print("  [3e] 尝试Course1活动...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                      headers=auth_headers,
                      json={"courseId": COURSE1_ID, "classId": COURSE1_CLASS, "schoolId": "0"},
                      verify=False, timeout=20)
    log_result("3e-activities-course1", r)

    # ===== Step 4: 尝试签到 (normal) =====
    log_section("Step 4: 尝试签到 (normal)")

    # 4a. 基本参数
    print("  [4a] normal签到 - 基本参数...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                      headers=auth_headers,
                      json={"activeId": "1000155099942",
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "courseName": COURSE2_NAME, "nickname": "3141cpy",
                            "latitude": "-1", "longitude": "-1", "address": ""},
                      verify=False, timeout=20)
    log_result("4a-normal-basic", r)

    # 4b. 添加更多参数
    print("  [4b] normal签到 - 更多参数...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                      headers=auth_headers,
                      json={"activeId": "1000155099942",
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "courseName": COURSE2_NAME, "nickname": "3141cpy",
                            "schoolId": "0", "fid": "0",
                            "latitude": "-1", "longitude": "-1", "address": "",
                            "clientip": "", "appType": "15", "ifTiJiao": "1"},
                      verify=False, timeout=20)
    log_result("4b-normal-more", r)

    # 4c. 尝试对已签到的活动签到
    print("  [4c] normal签到 - 已签到活动...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                      headers=auth_headers,
                      json={"activeId": "1000155014067",
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "courseName": COURSE2_NAME, "nickname": "3141cpy",
                            "latitude": "-1", "longitude": "-1", "address": ""},
                      verify=False, timeout=20)
    log_result("4c-normal-signed", r)

    # 4d. 尝试对Course1的活动签到
    print("  [4d] normal签到 - Course1活动...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                      headers=auth_headers,
                      json={"activeId": "5000165046206",
                            "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                            "courseName": COURSE1_NAME, "nickname": "3141cpy",
                            "latitude": "-1", "longitude": "-1", "address": ""},
                      verify=False, timeout=20)
    log_result("4d-normal-course1", r)

    # ===== Step 5: 尝试二维码签到 =====
    log_section("Step 5: 尝试二维码签到 (qrcode)")

    # 5a. 基本参数
    print("  [5a] qrcode签到 - 基本参数...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/qrcode",
                      headers=auth_headers,
                      json={"activeId": "1000155099942",
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "courseName": COURSE2_NAME, "nickname": "3141cpy",
                            "signCode": "1234"},
                      verify=False, timeout=20)
    log_result("5a-qrcode-basic", r)

    # 5b. 更多参数
    print("  [5b] qrcode签到 - 更多参数...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/qrcode",
                      headers=auth_headers,
                      json={"activeId": "1000155099942",
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "courseName": COURSE2_NAME, "nickname": "3141cpy",
                            "signCode": "1234", "schoolId": "0",
                            "latitude": "-1", "longitude": "-1", "address": ""},
                      verify=False, timeout=20)
    log_result("5b-qrcode-more", r)

    # ===== Step 6: 尝试位置签到 =====
    log_section("Step 6: 尝试位置签到 (location)")

    print("  [6a] location签到 - 基本参数...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/location",
                      headers=auth_headers,
                      json={"activeId": "1000155099942",
                            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "courseName": COURSE2_NAME, "nickname": "3141cpy",
                            "latitude": "34.7466", "longitude": "113.6253",
                            "address": "河南省郑州市"},
                      verify=False, timeout=20)
    log_result("6a-location-basic", r)

    # ===== Step 7: 探索 xiucat 前端JS代码 =====
    log_section("Step 7: 分析 xiucat 前端JS代码")

    print("  [7a] 下载 xiucat 主页...")
    try:
        r = requests.get("https://xiucat.top", verify=False, timeout=20)
        html = r.text
        print(f"  HTML长度: {len(html)}")

        # 搜索所有script标签
        import re
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
        inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"  外部JS: {scripts}")
        print(f"  内联JS数量: {len(inline_scripts)}")

        for s in inline_scripts:
            if len(s.strip()) > 10:
                print(f"  内联JS: {s[:500]}")

        # 搜索API端点
        api_refs = re.findall(r'(api-test\.xiucat\.top[^"\'>\s]*|/v2/[a-zA-Z0-9/_-]+)', html)
        print(f"  API引用: {list(set(api_refs))}")

    except Exception as e:
        print(f"  Error: {e}")

    # 7b. 下载script.js
    print("\n  [7b] 下载 script.js...")
    try:
        r = requests.get("https://xiucat.top/script.js", verify=False, timeout=20)
        js_content = r.text
        print(f"  JS长度: {len(js_content)}")

        # 搜索API端点
        api_refs = re.findall(r'(/v2/[a-zA-Z0-9/_-]+|api-test\.xiucat\.top[^"\'>\s]*)', js_content)
        print(f"  API引用: {list(set(api_refs))}")

        # 搜索签到相关
        sign_refs = re.findall(r'(sign[a-zA-Z]*|补签|makeup|patch|resign)', js_content, re.IGNORECASE)
        print(f"  签到相关: {list(set(sign_refs))}")

        # 搜索fetch/axios调用
        fetch_calls = re.findall(r'(fetch|axios|XMLHttpRequest|\.get|\.post)\s*\([^)]{0,200}\)', js_content)
        print(f"  HTTP调用: {fetch_calls[:10]}")

        # 打印完整JS
        print(f"\n  完整JS内容:\n{js_content[:5000]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 7c. 下载styles.css
    print("\n  [7c] 下载 styles.css...")
    try:
        r = requests.get("https://xiucat.top/styles.css", verify=False, timeout=20)
        print(f"  CSS长度: {len(r.text)}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 8: 尝试更多 xiucat API 端点组合 =====
    log_section("Step 8: 更多 xiucat API 端点组合")

    # 8a. 尝试不同的签到类型
    sign_types = [
        ("normal", {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                    "courseName": COURSE2_NAME, "nickname": "3141cpy",
                    "latitude": "-1", "longitude": "-1", "address": ""}),
        ("qrcode", {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                    "courseName": COURSE2_NAME, "nickname": "3141cpy",
                    "signCode": "1234", "latitude": "-1", "longitude": "-1", "address": ""}),
        ("location", {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                      "courseName": COURSE2_NAME, "nickname": "3141cpy",
                      "latitude": "34.7466", "longitude": "113.6253", "address": "河南省郑州市"}),
    ]

    for sign_type, body in sign_types:
        print(f"  [8a] POST /v2/student/sign/{sign_type}...")
        try:
            r = requests.post(f"https://api-test.xiucat.top/v2/student/sign/{sign_type}",
                              headers=auth_headers, json=body, verify=False, timeout=20)
            log_result(f"8a-{sign_type}", r)
        except Exception as e:
            print(f"  Error: {e}\n")

    # 8b. 尝试带 isMakeup 参数
    print("  [8b] 尝试带 isMakeup 参数...")
    for sign_type in ["normal", "qrcode", "location"]:
        body = {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                "latitude": "-1", "longitude": "-1", "address": "",
                "isMakeup": True, "makeup": True}
        try:
            r = requests.post(f"https://api-test.xiucat.top/v2/student/sign/{sign_type}",
                              headers=auth_headers, json=body, verify=False, timeout=20)
            print(f"  {sign_type}+isMakeup: Status={r.status_code}, Body={r.text[:300]}")
        except Exception as e:
            print(f"  {sign_type}+isMakeup: Error: {e}")
    print()

    # ===== Step 9: 测试 xiucat 对进行中活动的签到 =====
    log_section("Step 9: 测试 xiucat 对进行中活动的签到")

    # 先用超星API获取进行中的签到活动
    AES_KEY_LOCAL = b"u2oh6Vu^HWe4_AES"
    def aes_enc_local(p):
        c = AES.new(AES_KEY_LOCAL, AES.MODE_CBC, AES_KEY_LOCAL)
        return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

    def schild_sign_local(model, locale, version, build, imei):
        SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
        parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
                 f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
                 f"(@Kalimdor)_{imei}"]
        return hashlib.md5(" ".join(parts).encode()).hexdigest()

    def get_mobile_ua_local():
        imei = uuid.uuid4().hex[:32]
        sc = schild_sign_local("MI10", "zh_CN", "6.7.2", "10941_314", imei)
        return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
                f"(schild:{sc}) (device:MI10) Language/zh_CN "
                f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
                f"(@Kalimdor)_{imei}")

    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua_local()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s.post("https://passport2.chaoxing.com/fanyalogin",
           data={"fid": "-1", "uname": aes_enc_local(ACC2_PHONE), "password": aes_enc_local(ACC2_PWD),
                 "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                 "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                 "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass

    # 获取进行中的活动
    print("  [9a] 获取进行中的签到活动...")
    active_signs = []
    for cid, clid in [(COURSE2_ID, COURSE2_CLASS), (COURSE1_ID, COURSE1_CLASS)]:
        try:
            r = s.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                        params={"courseId": cid, "classId": clid, "showNotStarted": "0"},
                        timeout=20)
            data = r.json()
            for act in data.get("activeList", []):
                if act.get("activeType") == 2 and act.get("groupId") == 1:
                    active_signs.append((cid, clid, act))
                    print(f"    进行中: id={act['id']}, name={act.get('nameOne')}, course={cid}")
        except Exception as e:
            print(f"    Error: {e}")

    if active_signs:
        for cid, clid, act in active_signs[:3]:
            aid = act['id']
            cname = COURSE2_NAME if cid == COURSE2_ID else COURSE1_NAME
            print(f"\n  [9b] 通过xiucat签到进行中活动: {act.get('nameOne')} (id={aid})")
            try:
                r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                                  headers=auth_headers,
                                  json={"activeId": str(aid), "courseId": cid, "classId": clid,
                                        "courseName": cname, "nickname": "3141cpy",
                                        "latitude": "-1", "longitude": "-1", "address": ""},
                                  verify=False, timeout=20)
                log_result(f"9b-normal-{aid}", r)
            except Exception as e:
                print(f"  Error: {e}")
    else:
        print("  没有进行中的签到活动")

    # ===== Step 10: 测试 xiucat 对未签到的已结束活动 =====
    log_section("Step 10: 测试 xiucat 对未签到的已结束活动")

    # 找到未签到的已结束活动
    print("  [10a] 查找未签到的已结束活动...")
    unsigned_ended = []
    try:
        r = s.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "showNotStarted": "1"},
                    timeout=20)
        data = r.json()
        for act in data.get("activeList", []):
            if act.get("activeType") == 2 and act.get("groupId") == 2:
                # 检查是否已签到
                try:
                    r2 = s.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                                params={"activeId": str(act['id']), "clientip": "", "latitude": "-1",
                                        "longitude": "-1", "appType": "15", "ifTiJiao": "1",
                                        "address": ""},
                                timeout=20)
                    result = r2.text
                    if "签到已结束" in result:
                        unsigned_ended.append(act)
                        print(f"    未签到已结束: id={act['id']}, name={act.get('nameOne')}")
                except:
                    pass
    except Exception as e:
        print(f"  Error: {e}")

    # 对未签到的已结束活动通过xiucat签到
    if unsigned_ended:
        for act in unsigned_ended[:3]:
            aid = act['id']
            print(f"\n  [10b] 通过xiucat签到未签到已结束活动: {act.get('nameOne')} (id={aid})")
            try:
                r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                                  headers=auth_headers,
                                  json={"activeId": str(aid), "courseId": COURSE2_ID,
                                        "classId": COURSE2_CLASS, "courseName": COURSE2_NAME,
                                        "nickname": "3141cpy",
                                        "latitude": "-1", "longitude": "-1", "address": ""},
                                  verify=False, timeout=20)
                log_result(f"10b-normal-{aid}", r)
            except Exception as e:
                print(f"  Error: {e}")
    else:
        print("  没有找到未签到的已结束活动")

    # ===== Step 11: 最终分析 =====
    log_section("Step 11: 最终分析")

    print("""
  ==================== 最终分析 ====================

  xiucat.top 的补签机制分析:

  1. xiucat V2 API 架构:
     - 登录: POST /v2/student/auth/login (手机号+密码)
     - 课程: GET /v2/student/sign/courses
     - 活动: POST /v2/student/sign/activities (需要schoolId)
     - 签到: POST /v2/student/sign/normal (需要courseName, nickname)
     - 二维码签到: POST /v2/student/sign/qrcode (需要nickname)
     - 位置签到: POST /v2/student/sign/location (需要nickname)

  2. xiucat 的核心机制:
     - 使用学生的超星凭据在服务端登录
     - 保存学生的超星session cookies
     - 通过代理方式调用超星API

  3. 补签的关键问题:
     - 直接调用超星stuSignajax对已结束活动返回"签到已结束"
     - xiucat的V2 API是否能绕过此限制？

  4. 可能的补签方式:
     A. xiucat在服务端使用教师账号修改签到状态
     B. xiucat使用了超星的内部/管理API
     C. xiucat通过某种方式绕过"签到已结束"检查
     D. xiucat的V2 API内部实现了特殊逻辑
    """)


if __name__ == "__main__":
    main()
