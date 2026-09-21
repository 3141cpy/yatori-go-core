#!/usr/bin/env python3
"""检查taskactivelist完整字段 + signInfo接口 + 带完整参数的学生签到页"""
import base64, hashlib, json, uuid, requests, urllib3, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"
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

s_s, puid_s = login("18436633997", "3.1415926Cpy")
print(f"学生puid={puid_s}")

AID = "5000173244062"

# 1. taskactivelist 完整字段
print("\n[1] taskactivelist 中该活动的完整字段:")
r = s_s.get(f"{BASE}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = r.json()
for item in d.get("activeList", []):
    if str(item.get("id")) == AID:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        break

# 2. widget/sign/pcstuSign 带完整参数（模拟App打开签到页）
print("\n[2] pcstuSign 页面（App完整参数）:")
pc_url = (f"{BASE}/widget/sign/pcstuSign?activeId={AID}&uid={puid_s}"
          f"&classId={CLASS_ID}&courseId={COURSE_ID}&appType=15&general=1&code=&uf=&dura="
          f"&ifNeedVCode=0&isJoin=false&location_x=&location_y=")
r = s_s.get(pc_url, timeout=20, allow_redirects=True)
text = r.text
print(f"  HTTP {r.status_code}, len={len(text)}")
# 搜索所有可能含位置的字段
for m in re.finditer(r'(locationtext|locationText|textlocation|address|place|签到地点|请在[^<"]{2,30}附近)[^<"]{0,40}', text, re.I):
    print(f"  [HIT] {m.group(0)[:100]}")
if r.status_code == 200 and len(text) > 1000:
    # 提取页面中的配置JSON或变量
    for m in re.finditer(r'(?:var|let|const|window\.)\s*(\w+)\s*=\s*(\{[^;]{10,2000}\})', text):
        print(f"  [JS变量] {m.group(1)} = {m.group(2)[:300]}")
    # form inputs
    for m in re.finditer(r'<input[^>]*name=["\']?(\w+)["\']?[^>]*value=["\']?([^"\'>]{0,60})', text):
        print(f"  [input] {m.group(1)} = {m.group(2)}")
    # 显示前2000字符
    print(f"  HTML预览: {text[:2000]}")

# 3. pptSign/signInfo
print("\n[3] pptSign/signInfo:")
r = s_s.get(f"{BASE}/pptSign/signInfo", params={"activeId": AID}, timeout=15)
print(f"  HTTP {r.status_code}: {r.text[:400]}")

# 4. v2 sign/signInfo
print("\n[4] v2/apis/sign/signInfo:")
r = s_s.get(f"{BASE}/v2/apis/sign/signInfo", params={"activeId": AID, "uid": puid_s}, timeout=15)
print(f"  HTTP {r.status_code}: {r.text[:400]}")

# 5. 教师端信息（对照）— 用教师账号看active详情，看是否有locationText
print("\n[5] 教师端getActiveDetail对照:")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
r = s_t.get(f"{BASE}/v2/apis/active/getActiveDetail",
            params={"activeId": AID, "uid": puid_t, "courseId": COURSE_ID, "classId": CLASS_ID}, timeout=15)
print(f"  HTTP {r.status_code}: {r.text[:600]}")

# 6. activeAPI/taskactivelist with more params
print("\n[6] activeAPI/getActiveDetail 再试不同路径:")
for path in ["ppt/activeAPI/getActiveDetail", "pptSign/getActiveDetail", "newsign/getActiveDetail",
             "v2/apis/active/getActiveDetail"]:
    for extra in [{"uid": puid_s}, {"uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}]:
        try:
            r = s_s.get(f"{BASE}/{path}", params={"activeId": AID, **extra}, timeout=10)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                print(f"  [OK] {path} {extra}: {r.text[:500]}")
            elif r.status_code != 500:
                print(f"  {path} {list(extra.keys())}: HTTP {r.status_code}, {r.text[:100]}")
        except Exception as e:
            print(f"  {path}: {e}")
