import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

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

# 测试脚本中的活动ID=1000155099942
s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
base = "https://mobilelearn.chaoxing.com"

# 查询活动1000155099942的状态
aid = "1000155099942"
print(f"测试活动 {aid}:")

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
print(f"  学生查询: {json.dumps(d, ensure_ascii=False)[:300]}")

# 学生修改
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid, "classId": "", "courseId": "", "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  修改: {r.text}")

time.sleep(2)

# 学生查询
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
print(f"  修改后学生查询: status={get_status(d)}, {json.dumps(d, ensure_ascii=False)[:300]}")

# 教师V2触发
r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  教师V2: {r.text[:200]}")

time.sleep(2)

# 最终查询
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
print(f"  最终: status={get_status(d)}, {json.dumps(d, ensure_ascii=False)[:400]}")

# 现在测试课程111的活动
print(f"\n测试课程111最新活动:")
r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
            params={"courseId": "257485372", "classId": "132821141", "uid": puid_s}, timeout=20)
d = safe_json(r)
active_list = d.get("activeList", []) if isinstance(d, dict) else []
for act in active_list[:3]:
    aid2 = str(act.get("id", ""))
    nameTwo = act.get("nameTwo", "")
    r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid2, "uid": puid_s}, timeout=20)
    d2 = safe_json(r)
    print(f"  aid={aid2}, nameTwo={nameTwo}, status={get_status(d2)}")
