#!/usr/bin/env python3
"""补充验证：用正确的cpi参数测试签到API"""

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

def try_api(session, method, url, desc, data=None, timeout=20):
    print(f"\n{'='*60}")
    print(f"[{method}] {desc}")
    print(f"  URL: {url}")
    if data:
        print(f"  Data: {data}")
    try:
        if method == "GET":
            r = session.get(url, timeout=timeout, allow_redirects=True)
        else:
            r = session.post(url, data=data, timeout=timeout, allow_redirects=True)
        print(f"  状态码: {r.status_code}")
        try:
            resp = json.loads(r.text)
            print(f"  响应: {json.dumps(resp, ensure_ascii=False, indent=2)[:2000]}")
            return resp
        except:
            print(f"  响应(前500字符): {r.text[:500]}")
            return r.text
    except Exception as e:
        print(f"  请求失败: {e}")
        return None

# 登录
print("登录账号1 (19712720708)...")
s1, puid1 = login("19712720708", "3.1415926Cpy")
print(f"PUID: {puid1}")

time.sleep(1)

print("\n登录账号2 (18436633997)...")
s2, puid2 = login("18436633997", "3.1415926Cpy")
print(f"PUID: {puid2}")

# 账号1的课程1 cpi=482881077 (教师角色)
# 账号1的课程2 不在列表中（不是该课程成员）
# 账号2的课程1 cpi=520211407 (学生角色)
# 账号2的课程2 cpi=520211407 (学生角色)

CPI1_TEACHER = 482881077  # 账号1在课程1的教师cpi
CPI2_STUDENT = 520211407  # 账号2的学生cpi

print("\n" + "=" * 70)
print("测试1: 账号1在课程1(教师角色)发起签到 - 带cpi参数")
print("=" * 70)

# 尝试多种签到API路径
try_api(s1, "POST", 
        "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
        "课程1发起签到(无cpi)",
        {"courseId": "257485372", "classId": "132821141", "cpi": str(CPI1_TEACHER), 
         "signType": "0", "signDuration": "5"})

time.sleep(0.5)

try_api(s1, "POST",
        "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
        "课程1发起签到(带activeId)",
        {"courseId": "257485372", "classId": "132821141", "cpi": str(CPI1_TEACHER),
         "signType": "0", "signDuration": "5", "activeId": ""})

time.sleep(0.5)

# 尝试PC端签到API
try_api(s1, "POST",
        "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
        "课程1发起签到(PC端UA+完整参数)",
        {"courseId": "257485372", "classId": "132821141", "cpi": str(CPI1_TEACHER),
         "signType": "0", "signDuration": "5", "ut": "s"})

time.sleep(0.5)

# 尝试获取签到列表 - 带cpi
print("\n" + "=" * 70)
print("测试2: 获取课程1签到列表 - 带cpi参数")
print("=" * 70)

try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/sign/stuSignList?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}",
        "账号1-课程1签到列表(教师cpi)")

time.sleep(0.5)

# 尝试获取课程1的教师管理页面
print("\n" + "=" * 70)
print("测试3: 获取课程1教师管理页面")
print("=" * 70)

try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/visit/interaction?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}&ut=s",
        "课程1交互页面(教师cpi)")

time.sleep(0.5)

# 尝试获取课程2（账号1不是成员）
print("\n" + "=" * 70)
print("测试4: 账号1尝试访问课程2（不是成员）")
print("=" * 70)

try_api(s1, "POST",
        "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
        "账号1-课程2发起签到(不是成员)",
        {"courseId": "262934472", "classId": "145110605", "signType": "0", "signDuration": "5"})

time.sleep(0.5)

# 账号2尝试签到
print("\n" + "=" * 70)
print("测试5: 账号2(学生)尝试在课程1发起签到")
print("=" * 70)

try_api(s2, "POST",
        "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
        "账号2-课程1发起签到(学生角色)",
        {"courseId": "257485372", "classId": "132821141", "cpi": str(CPI2_STUDENT),
         "signType": "0", "signDuration": "5"})

time.sleep(0.5)

# 尝试其他可能的签到API路径
print("\n" + "=" * 70)
print("测试6: 尝试其他签到API路径")
print("=" * 70)

# 尝试fxpc签名API
try_api(s1, "POST",
        "https://mooc1-api.chaoxing.com/mooc-ans/sign/createSign",
        "课程1创建签到(createSign)",
        {"courseId": "257485372", "classId": "132821141", "cpi": str(CPI1_TEACHER),
         "signType": "0", "signDuration": "5"})

time.sleep(0.5)

# 尝试获取课程成员列表 - 带cpi
try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/clazz/memberList?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}&ut=s",
        "课程1成员列表(教师cpi)")

time.sleep(0.5)

# 尝试获取课程详情 - 带cpi
try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/clazz/getClassDetail?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}",
        "课程1详情(教师cpi)")

time.sleep(0.5)

# 尝试PC端web版API
print("\n" + "=" * 70)
print("测试7: PC端Web版API")
print("=" * 70)

# 创建web session
s1_web = requests.Session()
s1_web.verify = False
s1_web.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})
for c in s1.cookies:
    s1_web.cookies.set(c.name, c.value)

# 尝试PC端课程管理
try_api(s1_web, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/visit/interaction?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}&ut=s",
        "PC端-课程1交互页面(教师cpi)")

time.sleep(0.5)

# 尝试PC端签到管理
try_api(s1_web, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/sign/stuSignList?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}&ut=s",
        "PC端-课程1签到列表(教师cpi)")

time.sleep(0.5)

# 尝试获取课程1的教师信息
print("\n" + "=" * 70)
print("测试8: 确认课程1的教师信息")
print("=" * 70)

# 通过课程square URL获取信息
try_api(s1, "GET",
        "https://mooc1-api.chaoxing.com/mooc-ans/course/courseData?courseId=257485372&classId=132821141&cpi=482881077&ut=s",
        "课程1数据(教师cpi)")

time.sleep(0.5)

# 尝试获取课程角色
try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/course/role?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}",
        "课程1角色信息")

time.sleep(0.5)

# 尝试获取课程1的签到活动列表
try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/active/getActiveList?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}",
        "课程1活动列表(教师cpi)")

time.sleep(0.5)

# 尝试获取课程1的任务列表
try_api(s1, "GET",
        f"https://mooc1-api.chaoxing.com/mooc-ans/job/joblist?courseId=257485372&classId=132821141&cpi={CPI1_TEACHER}&ut=s",
        "课程1任务列表(教师cpi)")

print("\n" + "=" * 70)
print("补充验证完成")
print("=" * 70)
