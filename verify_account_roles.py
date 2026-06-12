#!/usr/bin/env python3
"""验证超星测试账号的身份和角色 - 精简版，只关注关键数据"""

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

results = []

def log(msg):
    print(msg)
    results.append(msg)

def safe_get(session, url, desc, timeout=20):
    log(f"\n[GET] {desc}")
    log(f"  URL: {url}")
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        log(f"  状态码: {r.status_code}")
        try:
            data = json.loads(r.text)
            log(f"  响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            return data
        except:
            log(f"  响应(非JSON, 前500字符): {r.text[:500]}")
            return r.text
    except Exception as e:
        log(f"  请求失败: {e}")
        return None

def safe_post(session, url, data, desc, timeout=20):
    log(f"\n[POST] {desc}")
    log(f"  URL: {url}")
    log(f"  Data: {data}")
    try:
        r = session.post(url, data=data, timeout=timeout, allow_redirects=True)
        log(f"  状态码: {r.status_code}")
        try:
            resp = json.loads(r.text)
            log(f"  响应: {json.dumps(resp, ensure_ascii=False, indent=2)}")
            return resp
        except:
            log(f"  响应(非JSON, 前500字符): {r.text[:500]}")
            return r.text
    except Exception as e:
        log(f"  请求失败: {e}")
        return None

# ============================================================
log("=" * 70)
log("超星测试账号身份验证 - 精简版")
log("=" * 70)

# ---- 登录 ----
log("\n=== 登录 ===")
s1, puid1 = login("19712720708", "3.1415926Cpy")
log(f"账号1 (19712720708) PUID: {puid1}")

time.sleep(1)

s2, puid2 = login("18436633997", "3.1415926Cpy")
log(f"账号2 (18436633997) PUID: {puid2}")

# ---- 账号1 课程列表（完整） ----
log("\n=== 账号1 课程列表 (backclazzdata) ===")
data1 = safe_get(s1, "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
         "账号1课程列表")

if data1 and isinstance(data1, dict):
    log(f"\n--- 账号1课程列表摘要 ---")
    log(f"result: {data1.get('result')}")
    log(f"msg: {data1.get('msg')}")
    log(f"createcourse: {data1.get('createcourse')}")
    log(f"teacherEndCourse: {data1.get('teacherEndCourse')}")
    log(f"stuEndCourse: {data1.get('stuEndCourse')}")
    
    channel_list = data1.get('channelList', [])
    log(f"课程总数: {len(channel_list)}")
    
    for i, ch in enumerate(channel_list):
        content = ch.get('content', {})
        roletype = content.get('roletype')
        class_name = content.get('name')
        course_data = content.get('course', {}).get('data', [])
        course_name = course_data[0].get('name', 'N/A') if course_data else 'N/A'
        course_id = course_data[0].get('id', 'N/A') if course_data else 'N/A'
        teacher = course_data[0].get('teacherfactor', 'N/A') if course_data else 'N/A'
        school_id = course_data[0].get('belongSchoolId', 'N/A') if course_data else 'N/A'
        class_id = ch.get('key')
        cpi = ch.get('cpi')
        isretire = content.get('isretire')
        
        # roletype: 1=教师, 2=助教, 3=学生
        role_name = {1: "教师", 2: "助教", 3: "学生"}.get(roletype, f"未知({roletype})")
        
        log(f"\n  课程#{i+1}:")
        log(f"    课程名: {course_name}")
        log(f"    courseId: {course_id}")
        log(f"    classId: {class_id}")
        log(f"    班级名: {class_name}")
        log(f"    roletype: {roletype} → {role_name}")
        log(f"    teacherfactor: {teacher}")
        log(f"    belongSchoolId: {school_id}")
        log(f"    cpi: {cpi}")
        log(f"    isretire: {isretire}")
        log(f"    studentcount: {content.get('studentcount')}")

time.sleep(1)

# ---- 账号2 课程列表 ----
log("\n=== 账号2 课程列表 (backclazzdata) ===")
data2 = safe_get(s2, "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
         "账号2课程列表")

if data2 and isinstance(data2, dict):
    log(f"\n--- 账号2课程列表摘要 ---")
    log(f"result: {data2.get('result')}")
    log(f"createcourse: {data2.get('createcourse')}")
    log(f"teacherEndCourse: {data2.get('teacherEndCourse')}")
    log(f"stuEndCourse: {data2.get('stuEndCourse')}")
    
    channel_list2 = data2.get('channelList', [])
    log(f"课程总数: {len(channel_list2)}")
    
    for i, ch in enumerate(channel_list2):
        content = ch.get('content', {})
        roletype = content.get('roletype')
        class_name = content.get('name')
        course_data = content.get('course', {}).get('data', [])
        course_name = course_data[0].get('name', 'N/A') if course_data else 'N/A'
        course_id = course_data[0].get('id', 'N/A') if course_data else 'N/A'
        teacher = course_data[0].get('teacherfactor', 'N/A') if course_data else 'N/A'
        class_id = ch.get('key')
        cpi = ch.get('cpi')
        isretire = content.get('isretire')
        
        role_name = {1: "教师", 2: "助教", 3: "学生"}.get(roletype, f"未知({roletype})")
        
        log(f"\n  课程#{i+1}:")
        log(f"    课程名: {course_name}")
        log(f"    courseId: {course_id}")
        log(f"    classId: {class_id}")
        log(f"    班级名: {class_name}")
        log(f"    roletype: {roletype} → {role_name}")
        log(f"    teacherfactor: {teacher}")
        log(f"    cpi: {cpi}")
        log(f"    isretire: {isretire}")
        log(f"    studentcount: {content.get('studentcount')}")

time.sleep(1)

# ---- 账号1 账号管理页面信息 ----
log("\n=== 账号1 账号管理页面 ===")
r = s1.get("https://passport2.chaoxing.com/mooc/accountManage", timeout=20)
# 从HTML中提取关键信息
import re
name_match = re.search(r'<p class="fr colorBlue"\s*>\s*(.*?)\s*</p>', r.text)
gender_match = re.search(r'性别.*?<p[^>]*>\s*<i[^>]*></i>\s*(.*?)\s*</p>', r.text, re.DOTALL)
phone_match = re.search(r'手机号.*?<p[^>]*>.*?(\d{3}\*+\d+)', r.text, re.DOTALL)
school_match = re.search(r'学校.*?<p[^>]*>.*?>(.*?)<', r.text, re.DOTALL)
role_match = re.search(r'身份.*?<p[^>]*>.*?>(.*?)<', r.text, re.DOTALL)

if name_match:
    log(f"姓名: {name_match.group(1).strip()}")
if gender_match:
    log(f"性别: {gender_match.group(1).strip()}")
if phone_match:
    log(f"手机号: {phone_match.group(1).strip()}")
# 搜索更多身份信息
faculty_match = re.search(r'院系.*?<p[^>]*>(.*?)</p>', r.text, re.DOTALL)
stu_no_match = re.search(r'学号.*?<p[^>]*>(.*?)</p>', r.text, re.DOTALL)
if faculty_match:
    log(f"院系: {faculty_match.group(1).strip()}")
if stu_no_match:
    log(f"学号: {stu_no_match.group(1).strip()}")

# 尝试从i.chaoxing.com/base获取信息
log("\n=== 账号1 i.chaoxing.com/base 信息 ===")
r_base = s1.get("https://i.chaoxing.com/base", timeout=20)
# 搜索学校名
school_in_base = re.search(r'<h1>(.*?)</h1>', r_base.text)
name_in_base = re.search(r'alt="">\s*<h1>(.*?)</h1>', r_base.text)
if school_in_base:
    log(f"学校: {school_in_base.group(1).strip()}")
if name_in_base:
    log(f"用户名: {name_in_base.group(1).strip()}")

time.sleep(1)

# ---- 账号1 尝试教师功能 ----
log("\n=== 账号1 尝试教师功能 ===")

# 尝试在课程1发起签到
log("\n--- 在课程1 (自己创建的课程) 发起签到 ---")
safe_post(s1, "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
          {"courseId": "257485372", "classId": "132821141", "signType": "0", "signDuration": "5"},
          "账号1-课程1发起签到")

time.sleep(1)

# 尝试在课程2发起签到
log("\n--- 在课程2 (别人创建的课程) 发起签到 ---")
safe_post(s1, "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
          {"courseId": "262934472", "classId": "145110605", "signType": "0", "signDuration": "5"},
          "账号1-课程2发起签到")

time.sleep(1)

# ---- 账号2 尝试教师功能 ----
log("\n=== 账号2 尝试教师功能 ===")

log("\n--- 账号2在课程1发起签到 ---")
safe_post(s2, "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
          {"courseId": "257485372", "classId": "132821141", "signType": "0", "signDuration": "5"},
          "账号2-课程1发起签到")

time.sleep(1)

log("\n--- 账号2在课程2发起签到 ---")
safe_post(s2, "https://mooc1-api.chaoxing.com/mooc-ans/sign/updateSignStatus2",
          {"courseId": "262934472", "classId": "145110605", "signType": "0", "signDuration": "5"},
          "账号2-课程2发起签到")

time.sleep(1)

# ---- 尝试获取课程1的签到列表 ----
log("\n=== 获取课程签到信息 ===")
safe_get(s1, "https://mooc1-api.chaoxing.com/mooc-ans/sign/stuSignList?courseId=257485372&classId=132821141",
         "账号1-课程1签到列表")

time.sleep(0.5)

safe_get(s1, "https://mooc1-api.chaoxing.com/mooc-ans/sign/stuSignList?courseId=262934472&classId=145110605",
         "账号1-课程2签到列表")

time.sleep(0.5)

# ---- 尝试获取课程成员列表（教师功能）----
log("\n=== 尝试获取课程成员列表 ===")
safe_get(s1, "https://mooc1-api.chaoxing.com/mooc-ans/clazz/memberList?courseId=257485372&classId=132821141&cpi=0",
         "账号1-课程1成员列表")

time.sleep(0.5)

# 尝试使用cpi参数
if data1 and isinstance(data1, dict):
    for ch in data1.get('channelList', []):
        if ch.get('key') == 132821141:
            cpi1 = ch.get('cpi')
            safe_get(s1, f"https://mooc1-api.chaoxing.com/mooc-ans/clazz/memberList?courseId=257485372&classId=132821141&cpi={cpi1}",
                     f"账号1-课程1成员列表(cpi={cpi1})")
            time.sleep(0.5)
            break

# ---- 尝试PC端API ----
log("\n=== 尝试PC端API ===")

# 使用web版UA访问
s1_web = requests.Session()
s1_web.verify = False
s1_web.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
# 复制cookies
for c in s1.cookies:
    s1_web.cookies.set(c.name, c.value)

# 尝试获取课程管理信息
safe_get(s1_web, "https://mooc1-api.chaoxing.com/mooc-ans/visit/interaction?courseId=257485372&classId=132821141&cpi=0&ut=s",
         "PC端-课程1交互页面")

time.sleep(0.5)

# 尝试获取课程角色信息（通过cpi）
if data1 and isinstance(data1, dict):
    for ch in data1.get('channelList', []):
        cid = ch.get('key')
        cpi = ch.get('cpi')
        content = ch.get('content', {})
        course_data = content.get('course', {}).get('data', [])
        cname = course_data[0].get('name', 'N/A') if course_data else 'N/A'
        roletype = content.get('roletype')
        
        if cid in (132821141, 145110605):
            safe_get(s1, f"https://mooc1-api.chaoxing.com/mooc-ans/visit/interaction?courseId={course_data[0].get('id') if course_data else ''}&classId={cid}&cpi={cpi}&ut=s",
                     f"课程'{cname}'交互页面(cpi={cpi}, roletype={roletype})")
            time.sleep(0.5)

# ---- 最终汇总 ----
log("\n" + "=" * 70)
log("=== 最终汇总 ===")
log("=" * 70)

log("\n关键发现:")
log("1. 账号1 (19712720708, puid=402644510):")
log("   - 姓名: 陈鹏宇")
log("   - 学校: 郑州大学 (fid=1257)")

if data1 and isinstance(data1, dict):
    teacher_courses = []
    student_courses = []
    other_courses = []
    for ch in data1.get('channelList', []):
        content = ch.get('content', {})
        roletype = content.get('roletype')
        course_data = content.get('course', {}).get('data', [])
        cname = course_data[0].get('name', 'N/A') if course_data else 'N/A'
        cid = course_data[0].get('id', 'N/A') if course_data else 'N/A'
        class_id = ch.get('key')
        teacher = course_data[0].get('teacherfactor', 'N/A') if course_data else 'N/A'
        
        entry = f"课程'{cname}'(courseId={cid}, classId={class_id}, teacher={teacher})"
        if roletype == 1:
            teacher_courses.append(entry)
        elif roletype == 3:
            student_courses.append(entry)
        else:
            other_courses.append(f"{entry} (roletype={roletype})")
    
    log(f"   - 作为教师的课程({len(teacher_courses)}个):")
    for c in teacher_courses:
        log(f"     * {c}")
    log(f"   - 作为学生的课程({len(student_courses)}个):")
    for c in student_courses:
        log(f"     * {c}")
    log(f"   - 其他角色({len(other_courses)}个):")
    for c in other_courses:
        log(f"     * {c}")
    log(f"   - createcourse字段: {data1.get('createcourse')}")

log("\n2. 账号2 (18436633997, puid=431407443):")
if data2 and isinstance(data2, dict):
    teacher_courses2 = []
    student_courses2 = []
    for ch in data2.get('channelList', []):
        content = ch.get('content', {})
        roletype = content.get('roletype')
        course_data = content.get('course', {}).get('data', [])
        cname = course_data[0].get('name', 'N/A') if course_data else 'N/A'
        cid = course_data[0].get('id', 'N/A') if course_data else 'N/A'
        class_id = ch.get('key')
        teacher = course_data[0].get('teacherfactor', 'N/A') if course_data else 'N/A'
        
        entry = f"课程'{cname}'(courseId={cid}, classId={class_id}, teacher={teacher})"
        if roletype == 1:
            teacher_courses2.append(entry)
        elif roletype == 3:
            student_courses2.append(entry)
    
    log(f"   - 作为教师的课程({len(teacher_courses2)}个):")
    for c in teacher_courses2:
        log(f"     * {c}")
    log(f"   - 作为学生的课程({len(student_courses2)}个):")
    for c in student_courses2:
        log(f"     * {c}")
    log(f"   - createcourse字段: {data2.get('createcourse')}")

log("\n3. 关键结论:")
log("   - roletype=1 表示教师, roletype=3 表示学生")
log("   - 账号1在课程1(courseId=257485372)中的角色需要确认")
log("   - 账号1在课程2(courseId=262934472)中的角色需要确认")
log("   - 超星平台的'教师'角色是课程级别的，不是账号级别的")
log("   - 一个用户可以在某些课程中是教师，在其他课程中是学生")

# 保存结果
with open("/workspace/verify_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
log("\n结果已保存到 /workspace/verify_results.txt")
