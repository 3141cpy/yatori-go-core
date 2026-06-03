#!/usr/bin/env python3
"""
深入探索 /newsign/ 路径 - 新版签到系统
关键发现: 活动详情中的url字段指向 /newsign/preSign
这可能是一个独立于 /pptSign/ 的新版签到系统
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

# ======================================================================
# 1. 获取活动列表 - 提取url字段
# ======================================================================
print("=" * 100)
print("[1] 获取活动列表 - 提取url字段")
print("=" * 100)

r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)

activity_urls = {}
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        aid = str(item.get("id", ""))
        atype = item.get("activeType", "")
        name = item.get("nameOne", "")
        url = item.get("url", "")
        status = item.get("status", "")
        activity_urls[aid] = url
        print(f"  id={aid}, type={atype}, status={status}, name={name}")
        print(f"    url={url[:150]}")

# ======================================================================
# 2. 访问newsign/preSign页面 - 获取HTML和JS
# ======================================================================
print(f"\n{'=' * 100}")
print("[2] 访问newsign/preSign页面")
print("=" * 100)

# 找一个有url的活动
test_aid = None
test_url = None
for aid, url in activity_urls.items():
    if url and "newsign" in url:
        test_aid = aid
        test_url = url
        break

if not test_aid:
    # 手动构造
    test_aid = "5000163891319"
    test_url = f"{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={test_aid}"

print(f"  测试活动: aid={test_aid}")
print(f"  测试URL: {test_url}")

# 访问preSign页面
r = s_s.get(test_url, timeout=20)
print(f"  preSign页面: HTTP {r.status_code}, len={len(r.text)}")
if r.status_code == 200 and len(r.text) > 0:
    # 保存HTML用于分析
    with open("/workspace/newsign_preSign.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"  HTML已保存到 /workspace/newsign_preSign.html")

    # 提取JS中的API调用
    api_patterns = [
        r'url["\s:]*["\']([^"\']+)["\']',
        r'ajax\(["\']([^"\']+)["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.[a-z]+\(["\']([^"\']+)["\']',
        r'\.post\(["\']([^"\']+)["\']',
        r'\.get\(["\']([^"\']+)["\']',
        r'href=["\']([^"\']+)["\']',
        r'action=["\']([^"\']+)["\']',
        r'/newsign/[a-zA-Z]+',
        r'/pptSign/[a-zA-Z]+',
        r'/v2/apis/[a-zA-Z/]+',
    ]

    found_apis = set()
    for pattern in api_patterns:
        matches = re.findall(pattern, r.text)
        for m in matches:
            if any(kw in m for kw in ["sign", "active", "ppt", "newsign", "v2/apis"]):
                found_apis.add(m)

    print(f"\n  发现的API路径 ({len(found_apis)}):")
    for api in sorted(found_apis):
        print(f"    {api}")

    # 提取JavaScript文件URL
    js_urls = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', r.text)
    print(f"\n  JavaScript文件 ({len(js_urls)}):")
    for js_url in js_urls:
        print(f"    {js_url}")

else:
    print(f"  页面为空或不可访问")

# ======================================================================
# 3. 对多个活动访问preSign页面
# ======================================================================
print(f"\n{'=' * 100}")
print("[3] 对多个活动访问preSign页面")
print("=" * 100)

for aid, url in list(activity_urls.items())[:5]:
    if not url:
        url = f"{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={aid}"

    r = s_s.get(url, timeout=20)
    print(f"  aid={aid}: HTTP {r.status_code}, len={len(r.text)}")

    if r.status_code == 200 and len(r.text) > 100:
        # 查找API
        apis = re.findall(r'/newsign/[a-zA-Z]+', r.text)
        apis += re.findall(r'/pptSign/[a-zA-Z]+', r.text)
        apis += re.findall(r'/v2/apis/[a-zA-Z/]+', r.text)
        if apis:
            print(f"    APIs: {', '.join(set(apis))}")

        # 查找enc/token等关键参数
        enc_matches = re.findall(r'enc["\s:=]+["\']([^"\']+)["\']', r.text)
        token_matches = re.findall(r'token["\s:=]+["\']([^"\']+)["\']', r.text)
        if enc_matches:
            print(f"    enc: {enc_matches}")
        if token_matches:
            print(f"    token: {token_matches}")

# ======================================================================
# 4. /newsign/ 路径端点深度探索
# ======================================================================
print(f"\n{'=' * 100}")
print("[4] /newsign/ 路径端点深度探索")
print("=" * 100)

# 教师先设为缺勤
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
         data={"uids": PUID_S, "status": "0", "remark": ""},
         headers=ajax_hdr, timeout=20)
time.sleep(2)

newsign_endpoints = [
    # 签到相关
    ("sign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("signIn", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("doSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("submitSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("studentSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("stuSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("quickSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("qrCodeSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID, "enc": ""}),
    ("scanSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("locationSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID, "latitude": "34.78", "longitude": "113.66"}),
    # 状态修改相关
    ("updateSignStatus", "POST", {"uids": PUID_S, "status": "1", "remark": "", "activeId": test_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S}),
    ("changeSignStatus", "POST", {"activeId": test_aid, "uid": PUID_S, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("modifySignStatus", "POST", {"activeId": test_aid, "uid": PUID_S, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    # 记录相关
    ("addSignRecord", "POST", {"activeId": test_aid, "uid": PUID_S, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("saveSignRecord", "POST", {"activeId": test_aid, "uid": PUID_S, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("insertSignRecord", "POST", {"activeId": test_aid, "uid": PUID_S, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
    # 详情相关
    ("getActiveDetail", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("activeDetail", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("signDetail", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("getSignDetail", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("signInfo", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("getSignInfo", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    # preSign POST
    ("preSign", "POST", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
    ("preSign", "GET", {"activeId": test_aid, "uid": PUID_S, "courseId": COURSE_ID, "classId": CLASS_ID}),
]

interesting_results = []

for ep, method, params in newsign_endpoints:
    try:
        if method == "POST":
            r = s_s.post(f"{BASE}/newsign/{ep}", data=params, headers=ajax_hdr, timeout=15)
        else:
            r = s_s.get(f"{BASE}/newsign/{ep}", params=params, timeout=15)

        resp_text = r.text[:150]
        is_interesting = (
            "success" in resp_text.lower() or
            "签到" in resp_text or
            (r.status_code == 200 and len(r.text) > 10 and not r.text.startswith("<!DOCTYPE") and not r.text.startswith("<!doctype"))
        )

        marker = "<<" if is_interesting else "  "
        print(f"  {marker} /newsign/{ep} ({method}): HTTP {r.status_code}, {resp_text}")

        if is_interesting:
            interesting_results.append({
                "endpoint": f"/newsign/{ep}",
                "method": method,
                "status_code": r.status_code,
                "response": resp_text,
                "params": params
            })
    except Exception as e:
        print(f"  /newsign/{ep} ({method}): ERROR {e}")

# ======================================================================
# 5. 对有趣的结果进行深入测试 - 验证数据是否真正变化
# ======================================================================
print(f"\n{'=' * 100}")
print("[5] 对有趣的结果进行深入测试")
print("=" * 100)

for item in interesting_results:
    ep = item["endpoint"]
    method = item["method"]
    params = item["params"]

    # 查询当前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": test_aid, "uid": PUID_S}, timeout=20)
    before = get_status(safe_json(r))

    # 调用API
    if method == "POST":
        r = s_s.post(f"{BASE}{ep}", data=params, headers=ajax_hdr, timeout=15)
    else:
        r = s_s.get(f"{BASE}{ep}", params=params, timeout=15)

    time.sleep(2)

    # 查询修改后状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": test_aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))

    if before != after:
        print(f"  *** 状态变化! {ep}: {before} -> {after} ***")
    else:
        print(f"  {ep}: {before} -> {after} (未变)")

# ======================================================================
# 6. 尝试不同类型的签到活动
# ======================================================================
print(f"\n{'=' * 100}")
print("[6] 不同类型签到活动测试")
print("=" * 100)

# 获取所有签到活动
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)

sign_activities = {}
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        atype = str(item.get("activeType", ""))
        if atype == "2":  # 签到类型
            name = item.get("nameOne", "")
            aid = str(item.get("id", ""))
            sign_activities[aid] = name

# 对每种签到类型测试
for aid, name in list(sign_activities.items())[:5]:
    print(f"\n  --- 活动: {name} (aid={aid}) ---")

    # 设为缺勤
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
    time.sleep(2)

    # 查询状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    before = get_status(safe_json(r))

    # 测试newsign/updateSignStatus
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": PUID_S, "status": "1", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": PUID_S},
                 headers=ajax_hdr, timeout=20)
    time.sleep(2)

    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
    after = get_status(safe_json(r))

    if before != after:
        print(f"  *** newsign/updateSignStatus 状态变化! {before} -> {after} ***")
    else:
        print(f"  newsign/updateSignStatus: {before} -> {after}")

    # 恢复
    s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": PUID_S, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)

# ======================================================================
# 7. 探索newsign/preSign页面中的JS API
# ======================================================================
print(f"\n{'=' * 100}")
print("[7] 探索newsign/preSign页面JS API")
print("=" * 100)

# 下载并分析JS文件
js_urls_to_fetch = [
    f"{BASE}/newsign/static/js/sign.js",
    f"{BASE}/newsign/static/js/main.js",
    f"{BASE}/newsign/static/js/app.js",
    f"{BASE}/newsign/static/js/chunk-vendors.js",
    f"{BASE}/js/newsign/sign.js",
    f"{BASE}/newsign/js/sign.js",
    f"{BASE}/newsign/js/main.js",
]

for js_url in js_urls_to_fetch:
    try:
        r = s_s.get(js_url, timeout=10)
        if r.status_code == 200 and len(r.text) > 50:
            print(f"  {js_url}: HTTP {r.status_code}, len={len(r.text)}")
            # 提取API路径
            apis = re.findall(r'["\'](/[^"\']*sign[^"\']*)["\']', r.text)
            apis += re.findall(r'["\'](/newsign/[^"\']*)["\']', r.text)
            apis += re.findall(r'["\'](/pptSign/[^"\']*)["\']', r.text)
            apis += re.findall(r'["\'](/v2/apis/[^"\']*)["\']', r.text)
            if apis:
                print(f"    APIs: {', '.join(set(apis)[:20])}")
        else:
            print(f"  {js_url}: HTTP {r.status_code}")
    except:
        pass

# ======================================================================
# 8. 尝试从preSign页面获取enc参数
# ======================================================================
print(f"\n{'=' * 100}")
print("[8] 从preSign页面获取enc参数")
print("=" * 100)

for aid, name in list(sign_activities.items())[:3]:
    # 访问preSign页面
    url = f"{BASE}/newsign/preSign?courseId={COURSE_ID}&classId={CLASS_ID}&activePrimaryId={aid}"
    r = s_s.get(url, timeout=20)

    if r.status_code == 200 and len(r.text) > 0:
        # 搜索enc
        enc_matches = re.findall(r'enc["\s:=]+["\']([^"\']+)["\']', r.text)
        # 搜索token
        token_matches = re.findall(r'token["\s:=]+["\']([^"\']+)["\']', r.text)
        # 搜索signType
        signtype_matches = re.findall(r'signType["\s:=]+["\']?([^"\'<\s,]+)', r.text)
        # 搜索activeType
        activetype_matches = re.findall(r'activeType["\s:=]+["\']?([^"\'<\s,]+)', r.text)

        print(f"  {name} (aid={aid}):")
        if enc_matches:
            print(f"    enc: {enc_matches}")
        if token_matches:
            print(f"    token: {token_matches}")
        if signtype_matches:
            print(f"    signType: {signtype_matches}")
        if activetype_matches:
            print(f"    activeType: {activetype_matches}")

        # 如果有enc，尝试用enc签到
        if enc_matches:
            enc = enc_matches[0]
            print(f"    尝试用enc签到: {enc[:50]}...")

            # 设为缺勤
            s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": PUID_S, "status": "0", "remark": ""},
                     headers=ajax_hdr, timeout=20)
            time.sleep(2)

            # 用enc签到
            r = s_s.get(f"{BASE}/pptSign/updateqrstatus",
                        params={"activeId": aid, "uid": PUID_S, "enc": enc},
                        timeout=20)
            print(f"    updateqrstatus: HTTP {r.status_code}, {r.text[:100]}")

            # 验证
            time.sleep(2)
            r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": PUID_S}, timeout=20)
            after = get_status(safe_json(r))
            if after == 1:
                print(f"    *** 签到成功！***")
            else:
                print(f"    签到后状态: {after}")

            # 恢复
            s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": PUID_S, "status": "1", "remark": ""},
                     headers=ajax_hdr, timeout=20)

# 恢复主测试活动
s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
         params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": test_aid},
         data={"uids": PUID_S, "status": "1", "remark": ""},
         headers=ajax_hdr, timeout=20)

print("\n测试完成")
