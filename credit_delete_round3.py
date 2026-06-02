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
    print(f"  {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"课堂积分API & 删除签到活动 - 第三轮深入探索")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    # ========== A. 通过课程页面JS源码找积分API ==========
    print("\n" + "=" * 80)
    print("[A] 课程页面JS源码分析 - 寻找积分API")
    print("=" * 80)

    # A.1 教师端课程管理页面
    print("\n--- A.1 教师端课程管理页面 ---")
    teacher_pages = [
        f"https://mooc1.chaoxing.com/mycourse/teacherindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/teacher/statistic?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/teacher/studydata?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/teacher/signstatistic?courseid={COURSE_ID}&clazzid={CLASS_ID}",
    ]

    for url in teacher_pages:
        try:
            r = s_t.get(url, timeout=20, allow_redirects=True)
            print(f"\n  {url[:70]}: HTTP {r.status_code}, len={len(r.text)}")

            if r.status_code == 200 and len(r.text) > 100:
                # 搜索积分/经验值/表现分相关关键词
                credit_refs = re.findall(r'(?:credit|积分|score|point|经验值|经验|互动分|表现分|课堂积分|classpoint|classscore)[^"\';\s]{0,80}', r.text, re.I)
                api_refs = re.findall(r'["\']([^"\']*(?:credit|score|point|积分|经验|互动)[^"\']*)["\']', r.text, re.I)
                js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)

                if credit_refs:
                    print(f"    积分引用({len(credit_refs)}): {credit_refs[:5]}")
                    rec(f"A1-credit-{url.split('/')[-1][:15]}", f"积分引用: {credit_refs[:5]}", str(credit_refs[:10])[:300])
                if api_refs:
                    print(f"    API引用({len(api_refs)}): {api_refs[:5]}")
                    rec(f"A1-api-{url.split('/')[-1][:15]}", f"API引用: {api_refs[:5]}", str(api_refs[:10])[:300])
                if js_urls:
                    print(f"    JS文件({len(js_urls)}): {js_urls[:3]}")
        except Exception as e:
            print(f"    ERROR: {e}")

    # A.2 学生端课程页面
    print("\n--- A.2 学生端课程页面 ---")
    student_pages = [
        f"https://mooc1.chaoxing.com/mycourse/stuindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/studyprocess?courseid={COURSE_ID}&clazzid={CLASS_ID}",
    ]

    for url in student_pages:
        try:
            r = s_s.get(url, timeout=20, allow_redirects=True)
            print(f"\n  {url[:70]}: HTTP {r.status_code}, len={len(r.text)}")

            if r.status_code == 200 and len(r.text) > 100:
                credit_refs = re.findall(r'(?:credit|积分|score|point|经验值|经验|互动分|表现分|课堂积分|classpoint|classscore)[^"\';\s]{0,80}', r.text, re.I)
                api_refs = re.findall(r'["\']([^"\']*(?:credit|score|point|积分|经验|互动)[^"\']*)["\']', r.text, re.I)
                js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)

                if credit_refs:
                    print(f"    积分引用({len(credit_refs)}): {credit_refs[:5]}")
                    rec(f"A2-credit-{url.split('/')[-1][:15]}", f"积分引用: {credit_refs[:5]}", str(credit_refs[:10])[:300])
                if api_refs:
                    print(f"    API引用({len(api_refs)}): {api_refs[:5]}")
                    rec(f"A2-api-{url.split('/')[-1][:15]}", f"API引用: {api_refs[:5]}", str(api_refs[:10])[:300])
                if js_urls:
                    print(f"    JS文件({len(js_urls)}): {js_urls[:3]}")

                    # 下载JS文件分析
                    for js_url in js_urls[:5]:
                        if not js_url.startswith("http"):
                            js_url = f"https://mooc1.chaoxing.com{js_url}" if js_url.startswith("/") else f"https://mooc1.chaoxing.com/{js_url}"
                        try:
                            r_js = s_s.get(js_url, timeout=15)
                            if r_js.status_code == 200:
                                # 搜索积分相关API
                                js_credit = re.findall(r'["\']([^"\']*(?:credit|score|point|积分|经验|互动)[^"\']*)["\']', r_js.text, re.I)
                                js_api = re.findall(r'(?:fetch|ajax|post|get|axios)\s*\(?[\'"]([^\'"]+)', r_js.text)
                                if js_credit:
                                    print(f"      JS {js_url[:50]}: credit={js_credit[:3]}")
                                    rec(f"A2-js-credit", f"JS积分API: {js_credit[:3]}", str(js_credit[:5])[:300])
                                if js_api:
                                    sign_apis = [a for a in js_api if "sign" in a.lower() or "credit" in a.lower() or "score" in a.lower() or "point" in a.lower()]
                                    if sign_apis:
                                        print(f"      JS {js_url[:50]}: sign/credit APIs={sign_apis[:3]}")
                                        rec(f"A2-js-api", f"JS签到/积分API: {sign_apis[:3]}", str(sign_apis[:5])[:300])
                        except:
                            pass
        except Exception as e:
            print(f"    ERROR: {e}")

    # ========== B. 积分API - 直接测试mooc1-api已知路径模式 ==========
    print("\n" + "=" * 80)
    print("[B] 积分API - 直接测试已知路径模式")
    print("=" * 80)

    # 学习通的课堂积分可能叫"classpoint"或"classexperience"
    credit_api_patterns = [
        # 课堂积分
        ("GET", f"https://mooc1-api.chaoxing.com/mooc-ans/classpoint/{STUDENT_PUID}", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", f"https://mooc1-api.chaoxing.com/mooc-ans/classexperience/{STUDENT_PUID}", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        ("GET", f"https://mooc1-api.chaoxing.com/mooc-ans/studyprocess/{STUDENT_PUID}", {"courseId": COURSE_ID, "classId": CLASS_ID}),
        # 课堂表现/互动
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/interaction/studentlist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/interaction/statistic", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # 签到积分
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/sign/statistic", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/sign/scorelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # 课堂积分（v2）
        ("GET", "https://mooc1-api.chaoxing.com/v2/apis/credit/getCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/v2/apis/score/getScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/v2/apis/point/getPoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # mobilelearn域名
        ("GET", f"{base}/v2/apis/credit/getCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", f"{base}/v2/apis/score/getScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", f"{base}/v2/apis/point/getPoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        # pptSign积分
        ("GET", f"{base}/pptSign/getCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", f"{base}/pptSign/scoreList", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
    ]

    for method, url, params in credit_api_patterns:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                params_copy = dict(params)
                params_copy["uid"] = puid_s if label == "学生" else puid_t
                r = session.get(url, params=params_copy, timeout=15)
                if r.status_code != 404 and len(r.text) > 5 and "404" not in r.text[:100]:
                    short = url.replace("https://", "").split("/")[1][:20] + "/" + url.split("/")[-1][:20]
                    rec(f"B-credit-{short}-{label}",
                        f"{label} GET: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== C. 删除签到活动 - /ppt/activeAPI/ 路径 ==========
    print("\n" + "=" * 80)
    print("[C] 删除签到活动 - /ppt/activeAPI/ 路径")
    print("=" * 80)

    # 获取活动列表
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []

    # 找一个已结束的签到活动用于删除测试
    test_aid = None
    for act in active_list:
        aid = str(act.get("id", ""))
        nameTwo = act.get("nameTwo", "")
        # 使用一个已结束的活动
        if nameTwo and "结束" not in nameTwo:
            test_aid = aid
            break
    if not test_aid:
        test_aid = str(active_list[-1].get("id", "")) if active_list else "5000163776554"

    print(f"  测试活动ID: {test_aid}")

    # /ppt/activeAPI/ 路径下的删除/结束API
    ppt_active_apis = [
        ("/ppt/activeAPI/deleteActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s, "id": test_aid}),
        ("/ppt/activeAPI/delActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s, "id": test_aid}),
        ("/ppt/activeAPI/removeActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s, "id": test_aid}),
        ("/ppt/activeAPI/endActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}),
        ("/ppt/activeAPI/stopActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}),
        ("/ppt/activeAPI/closeActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}),
        ("/ppt/activeAPI/finishActive", {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}),
    ]

    for path, data in ppt_active_apis:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                data_copy = dict(data)
                data_copy["uid"] = puid_s if label == "学生" else puid_t
                r = session.post(f"{base}{path}", data=data_copy,
                                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15, allow_redirects=False)
                short = path.split("/")[-1][:25]
                if r.status_code != 404:
                    rec(f"C-pptActive-{short}-{label}",
                        f"{label} POST {path}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== D. /newsign/endSign 和 /newsign/deleteSign 带DB_STRATEGY ==========
    print("\n" + "=" * 80)
    print("[D] /newsign/ 带DB_STRATEGY参数测试")
    print("=" * 80)

    newsign_with_db = [
        ("/newsign/endSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/deleteSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
        ("/newsign/cancelSign", {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID}),
    ]

    for path, data in newsign_with_db:
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                data_copy = dict(data)
                data_copy["uid"] = puid_s if label == "学生" else puid_t
                r = session.post(f"{base}{path}",
                                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                                 data=data_copy,
                                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15, allow_redirects=False)
                short = path.split("/")[-1][:25]
                rec(f"D-newsign-db-{short}-{label}",
                    f"{label} POST {path}+DB: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== 保存结果 ==========
    print("\n" + "=" * 80)
    print("[保存结果]")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credit_delete_round3_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    # 汇总关键发现
    print("\n  关键发现:")
    for r_item in results:
        detail = str(r_item.get("detail", ""))
        evidence = str(r_item.get("evidence", ""))
        if any(kw in detail.lower() or kw in evidence.lower() for kw in ["success", '"status":1', '"result":1', "积分引用", "api引用", "js积分", "js签到"]):
            print(f"    🔴 {r_item['tag']}: {detail[:120]}")
        elif "无权限" not in detail and "404" not in detail and "500" not in detail:
            print(f"    ⚡ {r_item['tag']}: {detail[:120]}")

if __name__ == "__main__":
    run()
