import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE_URL = "https://mobilelearn.chaoxing.com"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"

COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163767353"
STUDENT_UID = "431407443"
TEACHER_UID = "402644510"

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
    resp = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                                   "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                                   "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                                   "independentId": "0", "independentNameId": "0"},
                  allow_redirects=False, timeout=30)
    print(f"  Login response: {resp.status_code}, cookies: {[c.name for c in s.cookies]}")
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


def record_result(tag, detail, evidence):
    entry = {"tag": tag, "detail": detail, "evidence": evidence[:300]}
    results.append(entry)
    print(f"  [{tag}] {detail} | {evidence[:150]}")


def test_endpoint(session, method, url, data=None, params=None, tag="", files=None):
    try:
        if method == "GET":
            r = session.get(url, params=params, timeout=20, allow_redirects=False)
        else:
            if files:
                r = session.post(url, data=data, files=files, timeout=20, allow_redirects=False)
            else:
                r = session.post(url, data=data, timeout=20, allow_redirects=False)
        evidence = r.text[:300]
        detail = f"HTTP {r.status_code}"
        record_result(tag, detail, evidence)
        return r
    except Exception as e:
        record_result(tag, f"ERROR: {str(e)}", "")
        return None


def test_endpoint_multipart(session, url, data, tag):
    files_payload = {}
    for k, v in data.items():
        files_payload[k] = (None, str(v))
    return test_endpoint(session, "POST", url, files=files_payload, tag=tag + "_multipart")


print("=" * 60)
print("Step 1: Login")
print("=" * 60)

print("\n[Teacher Login]")
teacher_session, teacher_puid = login(TEACHER_PHONE, TEACHER_PWD)
print(f"  Teacher puid: {teacher_puid}")

time.sleep(1)

print("\n[Student Login]")
student_session, student_puid = login(STUDENT_PHONE, STUDENT_PWD)
print(f"  Student puid: {student_puid}")

time.sleep(1)

print("\n" + "=" * 60)
print("Step 2: Explore Student Sign-in APIs")
print("=" * 60)

sign_params_base = {
    "activeId": ACTIVE_ID,
    "uid": STUDENT_UID,
    "courseId": COURSE_ID,
    "classId": CLASS_ID,
    "lat": "39.908823",
    "lng": "116.397470",
    "address": "北京市天安门广场",
}

# ============================================================
# 1. Student sign-in interfaces
# ============================================================
print("\n--- 1. Student sign-in interfaces ---")

# stuSignajax - normal
stu_sign_url = f"{BASE_URL}/pptSign/stuSignajax"
data_normal = dict(sign_params_base)
test_endpoint(student_session, "POST", stu_sign_url, data=data_normal, tag="stu_stuSignajax_normal")
test_endpoint_multipart(student_session, stu_sign_url, data_normal, tag="stu_stuSignajax_normal")
test_endpoint(student_session, "GET", stu_sign_url, params=data_normal, tag="stu_stuSignajax_normal_GET")

# stuSignajax with status=2
for status_val in ["0", "1", "2", "3", "4", "5", "6"]:
    data_status = dict(sign_params_base)
    data_status["status"] = status_val
    test_endpoint(student_session, "POST", stu_sign_url, data=data_status, tag=f"stu_stuSignajax_status_{status_val}")

# preSign
presign_url = f"{BASE_URL}/pptSign/preSign"
presign_params = {"activeId": ACTIVE_ID, "courseId": COURSE_ID, "classId": CLASS_ID}
test_endpoint(student_session, "GET", presign_url, params=presign_params, tag="stu_preSign_GET")
test_endpoint(student_session, "POST", presign_url, data=presign_params, tag="stu_preSign_POST")

# doSign
dosign_url = f"{BASE_URL}/pptSign/doSign"
dosign_data = dict(sign_params_base)
test_endpoint(student_session, "POST", dosign_url, data=dosign_data, tag="stu_doSign_POST")
test_endpoint_multipart(student_session, dosign_url, dosign_data, tag="stu_doSign_POST")
test_endpoint(student_session, "GET", dosign_url, params=dosign_data, tag="stu_doSign_GET")

# signIn
signin_url = f"{BASE_URL}/pptSign/signIn"
signin_data = dict(sign_params_base)
test_endpoint(student_session, "POST", signin_url, data=signin_data, tag="stu_signIn_POST")
test_endpoint_multipart(student_session, signin_url, signin_data, tag="stu_signIn_POST")
test_endpoint(student_session, "GET", signin_url, params=signin_data, tag="stu_signIn_GET")

time.sleep(1)

# ============================================================
# 2. Student make-up / modify sign result interfaces
# ============================================================
print("\n--- 2. Student make-up / modify sign result interfaces ---")

modify_endpoints = [
    ("makeUpSign", "补签"),
    ("modifySignResult", "修改签到结果"),
    ("editSignResult", "编辑签到结果"),
    ("saveSignResult", "保存签到结果"),
    ("updateSignResult", "更新签到结果"),
    ("changeSignResult", "更改签到结果"),
    ("cancelSign", "取消签到"),
]

modify_data = dict(sign_params_base)
modify_data["status"] = "1"

for ep, desc in modify_endpoints:
    url = f"{BASE_URL}/pptSign/{ep}"
    test_endpoint(student_session, "POST", url, data=modify_data, tag=f"stu_{ep}_POST")
    test_endpoint_multipart(student_session, url, modify_data, tag=f"stu_{ep}_POST")
    test_endpoint(student_session, "GET", url, params=modify_data, tag=f"stu_{ep}_GET")
    # Also test with teacher for comparison
    test_endpoint(teacher_session, "POST", url, data=modify_data, tag=f"tch_{ep}_POST")

time.sleep(1)

# ============================================================
# 3. Other /pptSign/ endpoints
# ============================================================
print("\n--- 3. Other /pptSign/ endpoints ---")

other_endpoints = [
    "saveSign", "editSign", "setSign", "putSign", "addSign",
    "submitSign", "completeSign", "finishSign", "confirmSign",
    "verifySign", "checkSign", "resign", "reSign", "reSignIn",
    "refreshSign", "resetSign"
]

other_data = dict(sign_params_base)

for ep in other_endpoints:
    url = f"{BASE_URL}/pptSign/{ep}"
    test_endpoint(student_session, "POST", url, data=other_data, tag=f"stu_{ep}_POST")
    test_endpoint(student_session, "GET", url, params=other_data, tag=f"stu_{ep}_GET")

time.sleep(1)

# ============================================================
# 4. /v2/apis/sign/ endpoints
# ============================================================
print("\n--- 4. /v2/apis/sign/ endpoints ---")

v2_base = "https://mobilelearn.chaoxing.com/v2/apis/sign"
v2_endpoints = [
    "sign", "doSign", "submit", "modify", "edit",
    "update", "cancel", "makeup", "resign"
]

v2_data = dict(sign_params_base)
v2_data["status"] = "1"

for ep in v2_endpoints:
    url = f"{v2_base}/{ep}"
    test_endpoint(student_session, "POST", url, data=v2_data, tag=f"stu_v2_{ep}_POST")
    test_endpoint(student_session, "GET", url, params=v2_data, tag=f"stu_v2_{ep}_GET")
    test_endpoint(teacher_session, "POST", url, data=v2_data, tag=f"tch_v2_{ep}_POST")

time.sleep(1)

# ============================================================
# 5. Critical test: status parameter in stuSignajax
# ============================================================
print("\n--- 5. Critical test: stuSignajax with various status values (teacher comparison) ---")

for status_val in ["0", "1", "2", "3", "4", "5", "6"]:
    data_s = dict(sign_params_base)
    data_s["status"] = status_val
    test_endpoint(teacher_session, "POST", stu_sign_url, data=data_s, tag=f"tch_stuSignajax_status_{status_val}")

# Also test stuSignajax with different parameter combinations
extra_tests = [
    {"activeId": ACTIVE_ID, "uid": STUDENT_UID, "status": "2"},
    {"activeId": ACTIVE_ID, "uid": STUDENT_UID, "courseId": COURSE_ID, "classId": CLASS_ID, "status": "2", "lat": "", "lng": "", "address": ""},
    {"activeId": ACTIVE_ID, "uid": STUDENT_UID, "courseId": COURSE_ID, "classId": CLASS_ID, "status": "2", "isfrom": "1"},
]

for i, data_extra in enumerate(extra_tests):
    test_endpoint(student_session, "POST", stu_sign_url, data=data_extra, tag=f"stu_stuSignajax_extra_{i}")
    test_endpoint_multipart(student_session, stu_sign_url, data_extra, tag=f"stu_stuSignajax_extra_{i}")

time.sleep(1)

# ============================================================
# 6. Additional exploration: sign task detail & status query
# ============================================================
print("\n--- 6. Sign task detail & status query ---")

detail_endpoints = [
    (f"{BASE_URL}/pptSign/activetask", {"courseId": COURSE_ID, "classId": CLASS_ID, "activeId": ACTIVE_ID}, "activetask"),
    (f"{BASE_URL}/pptSign/stuSignResult", {"activeId": ACTIVE_ID, "uid": STUDENT_UID}, "stuSignResult"),
    (f"{BASE_URL}/pptSign/signResult", {"activeId": ACTIVE_ID, "uid": STUDENT_UID}, "signResult"),
    (f"{BASE_URL}/pptSign/getSignResult", {"activeId": ACTIVE_ID, "uid": STUDENT_UID}, "getSignResult"),
    (f"{BASE_URL}/pptSign/querySignResult", {"activeId": ACTIVE_ID, "uid": STUDENT_UID}, "querySignResult"),
    (f"{BASE_URL}/pptSign/signDetail", {"activeId": ACTIVE_ID, "uid": STUDENT_UID}, "signDetail"),
    (f"{BASE_URL}/pptSign/getSignDetail", {"activeId": ACTIVE_ID, "uid": STUDENT_UID}, "getSignDetail"),
    (f"{BASE_URL}/pptSign/signInfo", {"activeId": ACTIVE_ID}, "signInfo"),
    (f"{BASE_URL}/pptSign/getSignInfo", {"activeId": ACTIVE_ID}, "getSignInfo"),
    (f"{BASE_URL}/pptSign/activeDetail", {"activeId": ACTIVE_ID}, "activeDetail"),
    (f"{BASE_URL}/pptSign/taskDetail", {"activeId": ACTIVE_ID}, "taskDetail"),
]

for url, params, name in detail_endpoints:
    test_endpoint(student_session, "GET", url, params=params, tag=f"stu_{name}_GET")
    test_endpoint(student_session, "POST", url, data=params, tag=f"stu_{name}_POST")

time.sleep(1)

# ============================================================
# 7. Teacher-only endpoints for comparison
# ============================================================
print("\n--- 7. Teacher comparison on key endpoints ---")

teacher_modify_data = {
    "activeId": ACTIVE_ID,
    "uid": STUDENT_UID,
    "courseId": COURSE_ID,
    "classId": CLASS_ID,
    "status": "1",
    "lat": "39.908823",
    "lng": "116.397470",
    "address": "北京市天安门广场",
}

teacher_endpoints = [
    ("updateSignStatusByUidsV2", "teacher_updateSignStatusByUidsV2"),
    ("startSign", "teacher_startSign"),
    ("endSign", "teacher_endSign"),
    ("deleteSign", "teacher_deleteSign"),
]

for ep, tag in teacher_endpoints:
    url = f"{BASE_URL}/pptSign/{ep}"
    test_endpoint(teacher_session, "POST", url, data=teacher_modify_data, tag=tag)
    test_endpoint(student_session, "POST", url, data=teacher_modify_data, tag=f"stu_{tag}")

# ============================================================
# Save results
# ============================================================
print("\n" + "=" * 60)
print("Saving results...")
print("=" * 60)

with open("/workspace/student_sign_flow_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nTotal results: {len(results)}")
print("Results saved to /workspace/student_sign_flow_results.json")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

success_endpoints = []
no_permission_endpoints = []
other_endpoints_list = []

for r in results:
    ev = r["evidence"].lower()
    tag = r["tag"]
    if "success" in ev or "\"result\":true" in ev or "\"result\":1" in ev:
        success_endpoints.append(r)
    elif "无权限" in ev or "no permission" in ev or "forbidden" in ev or "权限" in ev:
        no_permission_endpoints.append(r)
    else:
        other_endpoints_list.append(r)

print(f"\n[SUCCESS-like responses] ({len(success_endpoints)}):")
for r in success_endpoints:
    print(f"  {r['tag']}: {r['detail']} | {r['evidence'][:100]}")

print(f"\n[No Permission responses] ({len(no_permission_endpoints)}):")
for r in no_permission_endpoints:
    print(f"  {r['tag']}: {r['detail']} | {r['evidence'][:100]}")

print(f"\n[Other responses] ({len(other_endpoints_list)}):")
for r in other_endpoints_list:
    print(f"  {r['tag']}: {r['detail']} | {r['evidence'][:100]}")

# Student vs Teacher differences
print("\n[Student-Teacher Differences]:")
student_tags = {r["tag"]: r for r in results if r["tag"].startswith("stu_")}
teacher_tags = {r["tag"]: r for r in results if r["tag"].startswith("tch_") or r["tag"].startswith("teacher_")}

for t_tag, t_result in teacher_tags.items():
    stu_tag = "stu_" + t_tag
    if stu_tag in student_tags:
        s_result = student_tags[stu_tag]
        if s_result["evidence"] != t_result["evidence"]:
            print(f"  DIFF: {t_tag}")
            print(f"    Teacher: {t_result['evidence'][:120]}")
            print(f"    Student: {s_result['evidence'][:120]}")
