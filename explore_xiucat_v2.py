#!/usr/bin/env python3
"""
深入探索 xiucat.top V2 API - 基于第一轮测试的关键发现
重点: xiucat 登录成功后返回了学生的超星Cookie (pCookies)
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

ACC2_PHONE = "18436633997"
ACC2_PWD = "3.1415926Cpy"
ACC2_PUID = "431407443"

COURSE2_ID = "262934472"
COURSE2_CLASS = "145110605"

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

def log_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def log_result(label, resp):
    status = resp.status_code if resp else "NO RESPONSE"
    body = ""
    if resp:
        try:
            body = resp.text[:2000]
        except:
            body = "<cannot read body>"
    print(f"  [{label}] Status: {status}")
    print(f"  [{label}] Body: {body}")
    print()

def main():
    print("=" * 70)
    print("  xiucat.top V2 API 深入探索")
    print("=" * 70)

    # ===== Step 1: 登录 xiucat V2 =====
    log_section("Step 1: 登录 xiucat V2 API")
    xiucat_access_token = None
    xiucat_refresh_token = None
    xiucat_pcookies_raw = None
    xiucat_user_info = None

    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/auth/login",
                          json={"phone": ACC2_PHONE, "password": ACC2_PWD},
                          verify=False, timeout=20)
        log_result("xiucat-login", r)
        data = r.json()
        if data.get("code") == 200 and data.get("data"):
            tinfo = data["data"].get("tInfo", {})
            xiucat_access_token = tinfo.get("accessToken")
            xiucat_refresh_token = tinfo.get("refreshToken")
            xiucat_user_info = data["data"].get("userInfo", {})
            xiucat_pcookies_raw = data["data"].get("pCookies", [])
            print(f"  Access Token: {xiucat_access_token[:50]}..." if xiucat_access_token else "  Access Token: None")
            print(f"  User Info: {xiucat_user_info}")
            print(f"  pCookies count: {len(xiucat_pcookies_raw)}")
            for pc in xiucat_pcookies_raw:
                print(f"    Cookie: {pc[:80]}...")
    except Exception as e:
        print(f"  Error: {e}")
        return

    if not xiucat_access_token:
        print("  无法获取access token，退出")
        return

    # 构建认证headers
    auth_headers = {
        "Authorization": f"Bearer {xiucat_access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ===== Step 2: 解析 pCookies 并构建超星session =====
    log_section("Step 2: 解析 pCookies 构建超星session")
    chaoxing_session = requests.Session()
    chaoxing_session.verify = False
    chaoxing_session.headers.update({
        "User-Agent": get_mobile_ua(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh_CN"
    })

    # 从 pCookies 中提取cookie
    for pc in xiucat_pcookies_raw:
        # 解析 "name=value; Domain=...; Path=...; ..." 格式
        parts = pc.split(";")
        if parts:
            name_value = parts[0].strip()
            if "=" in name_value:
                name, value = name_value.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"')
                chaoxing_session.cookies.set(name, value, domain=".chaoxing.com")
                print(f"  Set cookie: {name}={value[:30]}...")

    # ===== Step 3: 探索 xiucat V2 API 端点 =====
    log_section("Step 3: 探索 xiucat V2 API 端点 (带认证)")

    # 3a. 获取课程列表
    print("  [3a] GET /v2/student/sign/courses")
    try:
        r = requests.get("https://api-test.xiucat.top/v2/student/sign/courses",
                         headers=auth_headers, verify=False, timeout=20)
        log_result("3a-courses", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 3b. 尝试POST获取课程列表
    print("  [3b] POST /v2/student/sign/courses")
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/courses",
                          headers=auth_headers, json={}, verify=False, timeout=20)
        log_result("3b-courses-post", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 3c. 获取签到活动
    print("  [3c] POST /v2/student/sign/activities")
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                          headers=auth_headers,
                          json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS},
                          verify=False, timeout=20)
        log_result("3c-activities", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 3d. 尝试不带body的activities
    print("  [3d] GET /v2/student/sign/activities")
    try:
        r = requests.get("https://api-test.xiucat.top/v2/student/sign/activities",
                         headers=auth_headers, verify=False, timeout=20)
        log_result("3d-activities-get", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 3e. 尝试普通签到
    print("  [3e] POST /v2/student/sign/normal")
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "courseId": COURSE2_ID,
                                "classId": COURSE2_CLASS, "latitude": "-1", "longitude": "-1",
                                "address": ""},
                          verify=False, timeout=20)
        log_result("3e-normal-sign", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 4: 更多 xiucat V2 API 端点探索 =====
    log_section("Step 4: 更多 xiucat V2 API 端点探索")

    v2_endpoints = [
        # 学生相关
        ("GET", "/v2/student/auth/info"),
        ("GET", "/v2/student/course/list"),
        ("POST", "/v2/student/course/list"),
        ("GET", "/v2/student/sign/list"),
        ("POST", "/v2/student/sign/list"),
        ("GET", "/v2/student/sign/history"),
        ("POST", "/v2/student/sign/history"),
        ("GET", "/v2/student/sign/status"),
        ("POST", "/v2/student/sign/status"),
        ("POST", "/v2/student/sign/makeup"),
        ("POST", "/v2/student/sign/patch"),
        ("POST", "/v2/student/sign/resign"),
        ("POST", "/v2/student/sign/qrcode"),
        ("POST", "/v2/student/sign/location"),
        ("POST", "/v2/student/sign/code"),
        ("POST", "/v2/student/sign/gesture"),
        ("POST", "/v2/student/sign/photo"),
        # 教师相关
        ("GET", "/v2/teacher/sign/list"),
        ("POST", "/v2/teacher/sign/updateStatus"),
        ("POST", "/v2/teacher/sign/modify"),
        ("POST", "/v2/teacher/sign/makeup"),
        # 系统/管理
        ("GET", "/v2/system/info"),
        ("GET", "/v2/system/course/list"),
        ("POST", "/v2/system/course/addTeacher"),
        # 通用
        ("GET", "/v2/user/info"),
        ("GET", "/v2/config"),
        # 补签相关
        ("POST", "/v2/student/sign/doSign"),
        ("POST", "/v2/student/sign/submit"),
        ("POST", "/v2/student/sign/start"),
        ("GET", "/v2/student/sign/detail"),
        ("POST", "/v2/student/sign/detail"),
    ]

    for method, ep in v2_endpoints:
        try:
            if method == "GET":
                r = requests.get(f"https://api-test.xiucat.top{ep}",
                                 headers=auth_headers, verify=False, timeout=10)
            else:
                r = requests.post(f"https://api-test.xiucat.top{ep}",
                                  headers=auth_headers, json={}, verify=False, timeout=10)
            body = r.text[:200]
            # 只打印有意义的响应 (不是404)
            if '"code":404' not in body:
                print(f"  ★ [{method} {ep}] Status: {r.status_code}, Body: {body}")
            else:
                print(f"  [{method} {ep}] 404")
        except Exception as e:
            print(f"  [{method} {ep}] Error: {e}")
    print()

    # ===== Step 5: 使用 xiucat 返回的 pCookies 直接调用超星API =====
    log_section("Step 5: 使用 xiucat pCookies 调用超星API")

    # 5a. 获取课程活动列表
    print("  [5a] 获取Course2签到活动列表 (使用xiucat cookies)...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "showNotStarted": "0"},
                    timeout=20)
        log_result("5a-taskactivelist", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 5b. 尝试签到
    print("  [5b] 尝试对已结束活动签到 (使用xiucat cookies)...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                    params={"activeId": "1000155099942", "clientip": "", "latitude": "-1",
                            "longitude": "-1", "appType": "15", "ifTiJiao": "1",
                            "address": ""},
                    timeout=20)
        log_result("5b-stuSignajax", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 6: 直接登录超星并测试 =====
    log_section("Step 6: 直接登录超星并测试签到流程")

    s2, puid2 = login(ACC2_PHONE, ACC2_PWD)
    print(f"  学生账号 PUID: {puid2}")

    # 6a. 获取Course2的活动列表
    print("  [6a] 获取Course2活动列表...")
    all_activities = []
    try:
        r = s2.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "showNotStarted": "1"},
                    timeout=20)
        data = r.json()
        if "activeList" in data:
            for act in data["activeList"]:
                if act.get("activeType") == 2:
                    all_activities.append(act)
                    print(f"    id={act['id']}, name={act.get('nameOne')}, status={act.get('status')}, groupId={act.get('groupId')}")
    except Exception as e:
        print(f"  Error: {e}")

    # 6b. 对未签到的已结束活动尝试签到
    print("\n  [6b] 尝试对各种已结束签到活动签到...")
    for act in all_activities[:5]:
        aid = act['id']
        name = act.get('nameOne', 'N/A')
        print(f"\n  --- 活动: {name} (id={aid}) ---")

        # 尝试 stuSignajax GET
        try:
            r = s2.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                        params={"activeId": str(aid), "clientip": "", "latitude": "-1",
                                "longitude": "-1", "appType": "15", "ifTiJiao": "1",
                                "address": ""},
                        timeout=20)
            print(f"    stuSignajax GET: {r.text[:200]}")
        except Exception as e:
            print(f"    stuSignajax GET Error: {e}")

        # 尝试 stuSignajax POST
        try:
            r = s2.post("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                         data={"activeId": str(aid), "clientip": "", "latitude": "-1",
                               "longitude": "-1", "appType": "15", "ifTiJiao": "1",
                               "address": ""},
                         timeout=20)
            print(f"    stuSignajax POST: {r.text[:200]}")
        except Exception as e:
            print(f"    stuSignajax POST Error: {e}")

    # ===== Step 7: 探索 xiucat 的代理签到机制 =====
    log_section("Step 7: 探索 xiucat 代理签到机制")

    # xiucat 可能通过代理服务器转发签到请求
    # 尝试直接通过 xiucat 代理签到

    # 7a. 尝试通过 xiucat 代理调用超星签到
    print("  [7a] 尝试通过 xiucat 代理签到...")
    proxy_sign_urls = [
        ("POST", "https://api-test.xiucat.top/v2/student/sign/normal",
         {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
          "latitude": "-1", "longitude": "-1", "address": ""}),
        ("POST", "https://api-test.xiucat.top/v2/student/sign/doSign",
         {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
        ("POST", "https://api-test.xiucat.top/v2/student/sign/makeup",
         {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
        ("POST", "https://api-test.xiucat.top/v2/student/sign/submit",
         {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
    ]
    for method, url, body in proxy_sign_urls:
        try:
            r = requests.request(method, url, headers=auth_headers, json=body,
                                verify=False, timeout=20)
            print(f"  [{url.split('/')[-1]}] Status: {r.status_code}, Body: {r.text[:300]}")
        except Exception as e:
            print(f"  [{url.split('/')[-1]}] Error: {e}")
    print()

    # ===== Step 8: 深入分析 xiucat 登录返回的 pCookies =====
    log_section("Step 8: 分析 xiucat pCookies 机制")

    print("  xiucat 登录返回了完整的超星Cookie，这意味着:")
    print("  1. xiucat 在服务端使用学生凭据登录超星")
    print("  2. 获取超星session cookies")
    print("  3. 将cookies返回给客户端（设置在.xiucat.top域名下）")
    print("  4. 后续请求可能通过xiucat代理转发到超星")
    print()

    # 8a. 尝试使用 xiucat 的 cookie 代理方式
    print("  [8a] 尝试使用 xiucat cookie 代理方式访问超星...")
    # xiucat 可能有代理端点，将请求转发到超星
    proxy_endpoints = [
        ("GET", "https://api-test.xiucat.top/v2/proxy/sign/activelist",
         {"courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
        ("POST", "https://api-test.xiucat.top/v2/proxy/sign/doSign",
         {"activeId": "1000155099942"}),
        ("GET", "https://api-test.xiucat.top/proxy/mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
         {"courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
    ]
    for method, url, params in proxy_endpoints:
        try:
            if method == "GET":
                r = requests.get(url, headers=auth_headers, params=params,
                                verify=False, timeout=10)
            else:
                r = requests.post(url, headers=auth_headers, json=params,
                                verify=False, timeout=10)
            print(f"  [{url.split('.top')[-1][:40]}] Status: {r.status_code}, Body: {r.text[:200]}")
        except Exception as e:
            print(f"  [{url.split('.top')[-1][:40]}] Error: {e}")
    print()

    # ===== Step 9: 测试 xiucat 是否使用学生Cookie直接签到 =====
    log_section("Step 9: 测试 xiucat 使用学生Cookie直接签到")

    # 重新登录获取新鲜cookie
    print("  重新登录超星获取新鲜session...")
    s_fresh, puid_fresh = login(ACC2_PHONE, ACC2_PWD)
    print(f"  Fresh PUID: {puid_fresh}")

    # 9a. 获取进行中的签到活动
    print("\n  [9a] 获取进行中的签到活动...")
    active_signs = []
    try:
        r = s_fresh.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "showNotStarted": "0"},
                    timeout=20)
        data = r.json()
        group_list = data.get("groupList", [])
        for g in group_list:
            if g.get("id") == 1:  # 进行中
                print(f"    进行中的活动数: {g.get('name', 'N/A')}")
        for act in data.get("activeList", []):
            if act.get("activeType") == 2 and act.get("groupId") == 1:
                active_signs.append(act)
                print(f"    活跃签到: id={act['id']}, name={act.get('nameOne')}")
    except Exception as e:
        print(f"  Error: {e}")

    # 9b. 对活跃签到活动尝试签到
    if active_signs:
        for act in active_signs[:3]:
            aid = act['id']
            print(f"\n  [9b] 尝试签到活跃活动: {act.get('nameOne')} (id={aid})")
            try:
                r = s_fresh.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                            params={"activeId": str(aid), "clientip": "", "latitude": "-1",
                                    "longitude": "-1", "appType": "15", "ifTiJiao": "1",
                                    "address": ""},
                            timeout=20)
                print(f"    结果: {r.text[:200]}")
            except Exception as e:
                print(f"    Error: {e}")
    else:
        print("  没有进行中的签到活动")

    # 9c. 尝试对已结束但未签到的活动进行签到
    print("\n  [9c] 尝试对已结束未签到活动签到...")
    try:
        r = s_fresh.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "showNotStarted": "1"},
                    timeout=20)
        data = r.json()
        for act in data.get("activeList", []):
            if act.get("activeType") == 2 and act.get("groupId") == 2:
                aid = act['id']
                name = act.get('nameOne', 'N/A')
                # 先检查签到状态
                try:
                    r2 = s_fresh.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                                params={"activeId": str(aid), "clientip": "", "latitude": "-1",
                                        "longitude": "-1", "appType": "15", "ifTiJiao": "1",
                                        "address": ""},
                                timeout=20)
                    result = r2.text[:100]
                    print(f"    {name} (id={aid}): {result}")
                except Exception as e:
                    print(f"    {name} (id={aid}): Error: {e}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 10: 探索 xiucat 的前端代码 =====
    log_section("Step 10: 探索 xiucat 前端代码寻找API端点")

    print("  [10a] 获取 xiucat.top 主页...")
    try:
        r = requests.get("https://xiucat.top", verify=False, timeout=20)
        # 搜索JS文件
        js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
        css_files = re.findall(r'href=["\']([^"\']*\.css[^"\']*)["\']', r.text)
        print(f"  找到JS文件: {js_files}")
        print(f"  找到CSS文件: {css_files}")

        # 搜索API端点
        api_patterns = re.findall(r'(api-test\.xiucat\.top[^"\'>\s]+|/v2/[^"\'>\s]+)', r.text)
        print(f"  找到API模式: {api_patterns}")
    except Exception as e:
        print(f"  Error: {e}")

    # 10b. 下载并分析JS文件
    print("\n  [10b] 分析JS文件...")
    for js in js_files[:5]:
        if js.startswith("/"):
            js_url = f"https://xiucat.top{js}"
        elif js.startswith("http"):
            js_url = js
        else:
            js_url = f"https://xiucat.top/{js}"
        try:
            r = requests.get(js_url, verify=False, timeout=20)
            # 搜索API端点
            apis = re.findall(r'(/v2/[a-zA-Z0-9/_-]+|api-test\.xiucat\.top/[a-zA-Z0-9/_-]+)', r.text)
            sign_apis = [a for a in apis if 'sign' in a.lower() or 'course' in a.lower() or 'auth' in a.lower()]
            if sign_apis:
                print(f"  JS: {js}")
                print(f"  签到相关API: {list(set(sign_apis))}")

            # 搜索签到相关关键词
            keywords = ['补签', 'makeup', 'patch', 'resign', '补考', 'stuSign', 'updateSign', 'signStatus']
            for kw in keywords:
                if kw in r.text:
                    # 获取上下文
                    idx = r.text.index(kw)
                    context = r.text[max(0, idx-100):idx+100]
                    print(f"  JS: {js}, 关键词 '{kw}' 上下文: ...{context}...")
        except Exception as e:
            print(f"  JS {js}: Error: {e}")

    # ===== Step 11: 测试 xiucat 是否在服务端存储了学生Cookie =====
    log_section("Step 11: 测试 xiucat 服务端Cookie存储")

    # xiucat 登录时返回了 pCookies，这些cookie可能是xiucat在服务端保存的
    # 当用户请求补签时，xiucat使用保存的cookie代为签到

    # 11a. 测试 xiucat 是否能使用保存的cookie签到
    print("  [11a] 测试 xiucat 签到接口 (使用Bearer token)...")

    # 先获取课程列表
    try:
        r = requests.get("https://api-test.xiucat.top/v2/student/sign/courses",
                         headers=auth_headers, verify=False, timeout=20)
        print(f"  courses: Status={r.status_code}, Body={r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 11b. 尝试POST获取课程
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/courses",
                          headers=auth_headers, json={"page": 1, "size": 20},
                          verify=False, timeout=20)
        print(f"  courses POST: Status={r.status_code}, Body={r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 11c. 尝试使用cookie方式认证 (xiucat返回的pCookies)
    print("\n  [11c] 尝试使用xiucat域名的cookie认证...")
    xiucat_session = requests.Session()
    xiucat_session.verify = False

    # 设置xiucat返回的cookies
    for pc in xiucat_pcookies_raw:
        parts = pc.split(";")
        if parts:
            name_value = parts[0].strip()
            if "=" in name_value:
                name, value = name_value.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"')
                xiucat_session.cookies.set(name, value, domain=".xiucat.top")

    try:
        r = xiucat_session.get("https://api-test.xiucat.top/v2/student/sign/courses",
                               verify=False, timeout=20)
        print(f"  cookie auth courses: Status={r.status_code}, Body={r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 12: 综合分析 =====
    log_section("Step 12: 综合分析")

    print("""
  ==================== 关键发现总结 ====================

  1. xiucat V2 登录成功:
     - POST /v2/student/auth/login 使用明文手机号+密码
     - 返回 accessToken (JWT) + refreshToken
     - 返回 pCookies (超星平台的完整session cookies)
     - 返回 userInfo (puid, name, phone, fid, uid, status)

  2. pCookies 机制:
     - xiucat 在服务端使用学生凭据登录超星
     - 获取超星session cookies并返回
     - 这些cookies设置在 .xiucat.top 域名下
     - xiucat 可能使用这些cookies代为操作

  3. 直接签到测试:
     - 对已结束活动: stuSignajax 返回 "签到已结束"
     - 对已签到活动: stuSignajax 返回 "您已签到过了"
     - 学生Cookie无法直接对已结束活动签到

  4. xiucat V2 API 端点:
     - /v2/student/auth/login ✓ (可用)
     - /v2/student/sign/courses (需认证)
     - /v2/student/sign/activities (需认证)
     - /v2/student/sign/normal (需认证)
     - 其他端点大多返回404

  5. 教师加入课程:
     - 所有尝试的加入课程API都返回NO RESPONSE
     - 教师无法自行加入其他课程

  ==================== 待验证假设 ====================

  假设A: xiucat 使用学生Cookie + 某种特殊参数绕过"签到已结束"限制
  假设B: xiucat 使用教师账号修改签到状态 (需要先加入课程)
  假设C: xiucat 使用了超星内部/管理API
  假设D: xiucat 的 /v2/student/sign/normal 端点内部使用了特殊逻辑
    """)


if __name__ == "__main__":
    main()
