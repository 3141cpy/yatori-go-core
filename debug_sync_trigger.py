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
    return s, puid

s_s, puid_s = login("18436633997", "3.1415926Cpy")
base = "https://mobilelearn.chaoxing.com"

# 测试活动5000139561997（未签到的手势签到）
aid = "5000139561997"
print(f"测试活动 {aid} - 学生触发同步方式:")

# 1. 修改
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid, "classId": "132821141", "courseId": "257485372", "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  修改: {r.text}")

time.sleep(1)

# 2. 学生调用V2触发同步（虽然返回"无权限"，但可能触发缓存刷新）
r = s_s.post(f"{base}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  学生V2触发: {r.text[:100]}")

time.sleep(2)

# 3. 查询
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = r.json()
status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  查询: status={status}, {json.dumps(d, ensure_ascii=False)[:200]}")

# 4. 尝试学生调用旧路径updateSignStatus触发
aid2 = "5000139506185"
print(f"\n测试活动 {aid2} - 旧路径触发:")
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid2},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid2, "classId": "132821141", "courseId": "257485372", "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  修改: {r.text}")

time.sleep(1)

# 旧路径触发
r = s_s.post(f"{base}/pptSign/updateSignStatus",
             data={"activeId": aid2, "classId": "132821141", "courseId": "257485372",
                   "uid": puid_s, "studentId": puid_s, "status": "1"},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  旧路径触发: {r.text[:100]}")

time.sleep(2)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid2, "uid": puid_s}, timeout=20)
d = r.json()
status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  查询: status={status}, {json.dumps(d, ensure_ascii=False)[:200]}")

# 5. 尝试多次调用newsign/updateSignStatus触发
aid3 = "5000139410559"
print(f"\n测试活动 {aid3} - 多次调用触发:")
for i in range(3):
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid3},
                 data={"uids": puid_s, "status": "1", "remark": "",
                       "activeId": aid3, "classId": "132821141", "courseId": "257485372", "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  第{i+1}次修改: {r.text}")
    time.sleep(1)

r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid3, "uid": puid_s}, timeout=20)
d = r.json()
status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  查询: status={status}, {json.dumps(d, ensure_ascii=False)[:200]}")
