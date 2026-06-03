#!/usr/bin/env python3
"""
基于preSign页面JS逆向的精确签到测试
关键发现:
1. stuSignajax使用GET方法（不是POST！）
2. 参数包含ifTiJiao、validate、deviceCode等
3. 有进行中的活动(status=1)可以测试
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

# 获取活动列表 - 找进行中的活动
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)

ongoing_aids = []
ended_aids = []
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        aid = str(item.get("id", ""))
        atype = str(item.get("activeType", ""))
        status = str(item.get("status", ""))
        name = item.get("nameOne", "")
        if atype == "2" or atype == "74":  # 签到或签退
            if status == "1":
                ongoing_aids.append((aid, name, atype))
                print(f"  [进行中] id={aid}, type={atype}, name={name}")
            else:
                ended_aids.append((aid, name, atype))

if not ongoing_aids:
    print("  没有进行中的签到活动")
    # 使用已结束的活动
    test_aids = ended_aids[:3]
else:
    test_aids = ongoing_aids + ended_aids[:2]

# ======================================================================
# 测试1: 使用JS中发现的精确参数 - GET方法stuSignajax
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试1] 使用JS逆向参数 - GET方法stuSignajax")
print("=" * 100)

for aid, name, atype in test_aids[:3]:
    print(f"\n--- 活动: {name} (aid={aid}, type={atype}) ---")

    # 先查询当前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    d = safe_json(r)
    before = get_status(d)
    print(f"  当前状态: status={before}")

    # JS中的精确参数（GET方法）
    params_variations = [
        # 变体1: 完全模拟JS参数
        {
            "name": "测试学生",
            "address": "河南省郑州市",
            "activeId": aid,
            "courseId": COURSE_ID,
            "uid": PUID_S,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "fid": "0",
            "appType": "15",
            "ifTiJiao": "1",
            "validate": "",
            "deviceCode": uuid.uuid4().hex[:32],
            "vpProbability": "",
            "vpStrategy": "",
            "currentFaceId": "",
            "ifCFP": "1",
            "faceEnc": "",
            "faceCode": "",
        },
        # 变体2: ifTiJiao=2（不提交位置）
        {
            "name": "测试学生",
            "address": "",
            "activeId": aid,
            "courseId": COURSE_ID,
            "uid": PUID_S,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "fid": "0",
            "appType": "15",
            "ifTiJiao": "2",
            "validate": "",
            "deviceCode": uuid.uuid4().hex[:32],
            "vpProbability": "",
            "vpStrategy": "",
            "currentFaceId": "",
            "ifCFP": "1",
            "faceEnc": "",
            "faceCode": "",
        },
        # 变体3: 带位置信息
        {
            "name": "测试学生",
            "address": "河南省郑州市中原区",
            "activeId": aid,
            "courseId": COURSE_ID,
            "uid": PUID_S,
            "clientip": "",
            "latitude": "34.78",
            "longitude": "113.66",
            "fid": "0",
            "appType": "15",
            "ifTiJiao": "1",
            "validate": "",
            "deviceCode": uuid.uuid4().hex[:32],
            "vpProbability": "",
            "vpStrategy": "",
            "currentFaceId": "",
            "ifCFP": "1",
            "faceEnc": "",
            "faceCode": "",
        },
        # 变体4: 最简参数
        {
            "activeId": aid,
            "uid": PUID_S,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0",
            "ifTiJiao": "1",
        },
    ]

    for i, params in enumerate(params_variations):
        # GET方法（和JS一样）
        r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=20)
        print(f"  GET变体{i+1}: {r.text[:120]}")

        time.sleep(1)
        r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
        d = safe_json(r)
        after = get_status(d)
        if after != before and after is not None:
            print(f"  *** 状态变化! {before} -> {after} ***")
            break

        # POST方法
        r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=params, headers=ajax_hdr, timeout=20)
        print(f"  POST变体{i+1}: {r.text[:120]}")

        time.sleep(1)
        r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
        d = safe_json(r)
        after = get_status(d)
        if after != before and after is not None:
            print(f"  *** 状态变化! {before} -> {after} ***")
            break

# ======================================================================
# 测试2: /pptSign/check 端点
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试2] /pptSign/check 端点")
print("=" * 100)

for aid, name, atype in test_aids[:2]:
    print(f"\n--- 活动: {name} (aid={aid}) ---")

    # GET
    r = s_s.get(f"{BASE}/pptSign/check",
                params={"activeId": aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID},
                timeout=20)
    print(f"  check(GET): HTTP {r.status_code}, {r.text[:150]}")

    # POST
    r = s_s.post(f"{BASE}/pptSign/check",
                 data={"activeId": aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID},
                 headers=ajax_hdr, timeout=20)
    print(f"  check(POST): HTTP {r.status_code}, {r.text[:150]}")

# ======================================================================
# 测试3: /pptSign/find 端点
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试3] /pptSign/find 端点")
print("=" * 100)

for aid, name, atype in test_aids[:2]:
    r = s_s.get(f"{BASE}/pptSign/find",
                params={"activeId": aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID},
                timeout=20)
    print(f"  {name} find(GET): HTTP {r.status_code}, {r.text[:200]}")

    r = s_s.post(f"{BASE}/pptSign/find",
                 data={"activeId": aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID},
                 headers=ajax_hdr, timeout=20)
    print(f"  {name} find(POST): HTTP {r.status_code}, {r.text[:200]}")

# ======================================================================
# 测试4: /pptSign/find-exact-addr 端点
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试4] /pptSign/find-exact-addr 端点")
print("=" * 100)

for aid, name, atype in test_aids[:2]:
    r = s_s.get(f"{BASE}/pptSign/find-exact-addr",
                params={"activeId": aid, "uid": PUID_S},
                timeout=20)
    print(f"  {name} find-exact-addr(GET): HTTP {r.status_code}, {r.text[:200]}")

# ======================================================================
# 测试5: /pptSign/signReceipt 和 signReceipt2
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试5] /pptSign/signReceipt 端点")
print("=" * 100)

for aid, name, atype in test_aids[:2]:
    r = s_s.get(f"{BASE}/pptSign/signReceipt",
                params={"classId": CLASS_ID, "activeId": aid, "general": "1", "chatid": "", "appType": "15"},
                timeout=20)
    print(f"  {name} signReceipt(GET): HTTP {r.status_code}, {r.text[:150]}")

    r = s_s.get(f"{BASE}/pptSign/signReceipt2",
                params={"classId": CLASS_ID, "activeId": aid, "general": "1", "chatid": "", "appType": "15"},
                timeout=20)
    print(f"  {name} signReceipt2(GET): HTTP {r.status_code}, {r.text[:150]}")

# ======================================================================
# 测试6: /sign/signReceipt 端点
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试6] /sign/signReceipt 端点")
print("=" * 100)

for aid, name, atype in test_aids[:2]:
    r = s_s.get(f"{BASE}/sign/signReceipt",
                params={"classId": CLASS_ID, "activeId": aid, "general": "1", "chatid": "", "appType": "15"},
                timeout=20)
    print(f"  {name} /sign/signReceipt(GET): HTTP {r.status_code}, {r.text[:150]}")

# ======================================================================
# 测试7: /pptSign/check-face-result 端点
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试7] /pptSign/check-face-result 端点")
print("=" * 100)

for aid, name, atype in test_aids[:2]:
    r = s_s.get(f"{BASE}/pptSign/check-face-result",
                params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                timeout=20)
    print(f"  {name} check-face-result(GET): HTTP {r.status_code}, {r.text[:150]}")

# ======================================================================
# 测试8: 对进行中的活动，先设缺勤再尝试签到
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试8] 对进行中活动 - 先设缺勤再尝试签到")
print("=" * 100)

for aid, name, atype in ongoing_aids[:2]:
    print(f"\n--- 进行中活动: {name} (aid={aid}, type={atype}) ---")

    # 教师设为缺勤
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)

    # 查询状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    d = safe_json(r)
    before = get_status(d)
    print(f"  缺勤后状态: {before}")

    # 尝试1: newsign/updateSignStatus
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "1", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
                 headers=ajax_hdr, timeout=20)
    print(f"  newsign/updateSignStatus: {r.text[:100]}")
    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))
    if after != before and after is not None:
        print(f"  *** newsign/updateSignStatus 签到成功! {before} -> {after} ***")
    else:
        print(f"  newsign/updateSignStatus: {before} -> {after}")

    # 尝试2: stuSignajax GET（JS方式）
    params = {
        "name": "测试学生",
        "address": "河南省郑州市",
        "activeId": aid,
        "courseId": COURSE_ID,
        "uid": PUID_S,
        "clientip": "",
        "latitude": "-1",
        "longitude": "-1",
        "fid": "0",
        "appType": "15",
        "ifTiJiao": "1",
        "validate": "",
        "deviceCode": uuid.uuid4().hex[:32],
    }
    r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=20)
    print(f"  stuSignajax(GET-JS方式): {r.text[:120]}")
    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))
    if after == 1:
        print(f"  *** stuSignajax GET方式签到成功! ***")
    else:
        print(f"  stuSignajax GET: {before} -> {after}")

    # 尝试3: stuSignajax POST
    r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=params, headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax(POST): {r.text[:120]}")
    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))
    if after == 1:
        print(f"  *** stuSignajax POST方式签到成功! ***")
    else:
        print(f"  stuSignajax POST: {before} -> {after}")

    # 恢复
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)

# ======================================================================
# 测试9: 对已结束活动 - 先设缺勤再尝试签到
# ======================================================================
print(f"\n{'=' * 100}")
print("[测试9] 对已结束活动 - 先设缺勤再尝试签到")
print("=" * 100)

for aid, name, atype in ended_aids[:3]:
    print(f"\n--- 已结束活动: {name} (aid={aid}, type={atype}) ---")

    # 教师设为缺勤
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)

    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    before = get_status(safe_json(r))
    print(f"  缺勤后状态: {before}")

    # newsign/updateSignStatus
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "1", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
                 headers=ajax_hdr, timeout=20)
    print(f"  newsign/updateSignStatus: {r.text[:80]}")
    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))
    if after != before and after is not None:
        print(f"  *** 签到成功! {before} -> {after} ***")
    else:
        print(f"  newsign: {before} -> {after}")

    # stuSignajax GET
    params = {
        "activeId": aid, "uid": PUID_S, "courseId": COURSE_ID,
        "clientip": "", "latitude": "-1", "longitude": "-1",
        "fid": "0", "appType": "15", "ifTiJiao": "1",
        "validate": "", "address": "",
    }
    r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=20)
    print(f"  stuSignajax(GET): {r.text[:120]}")
    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))
    if after == 1:
        print(f"  *** stuSignajax GET签到成功! ***")

    # 恢复
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)

print("\n测试完成")
