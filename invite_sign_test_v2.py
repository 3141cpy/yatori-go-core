#!/usr/bin/env python3
"""深入测试 xiucat.top V2 API 邀请签到功能 - 基于第一轮发现"""

import json, requests, urllib3, time

urllib3.disable_warnings()

XIUCAT_BASE = "https://api-test.xiucat.top/v2/student"

def safe_req(method, session, url, **kwargs):
    try:
        if method == "GET":
            r = session.get(url, timeout=20, **kwargs)
        else:
            r = session.post(url, timeout=20, **kwargs)
        return r
    except Exception as e:
        print(f"  请求异常: {e}")
        return None

def print_resp(label, resp):
    if resp is None:
        print(f"  [{label}] 请求失败")
        return
    print(f"  [{label}] Status: {resp.status_code}")
    try:
        body = resp.text[:3000]
        print(f"  [{label}] Body: {body}")
    except:
        print(f"  [{label}] Body: (无法读取)")

def main():
    print("=" * 80)
    print("xiucat.top V2 API 邀请签到深入测试")
    print("=" * 80)

    # Step 1: 登录获取 token
    print("\n[1] 登录 xiucat V2 API (学生账号)")
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36"
    })

    login_resp = safe_req("POST", s, f"{XIUCAT_BASE}/auth/login",
                          json={"phone": "18436633997", "password": "3.1415926Cpy"})
    print_resp("login", login_resp)

    if not login_resp or login_resp.status_code not in (200, 201):
        print("登录失败，退出")
        return

    login_data = login_resp.json()
    access_token = login_data["data"]["tInfo"]["accessToken"]
    refresh_token = login_data["data"]["tInfo"]["refreshToken"]
    user_info = login_data["data"]["userInfo"]
    p_cookies = login_data["data"].get("pCookies", [])

    print(f"\n  accessToken: {access_token[:80]}...")
    print(f"  refreshToken: {refresh_token[:80]}...")
    print(f"  userInfo: {json.dumps(user_info, ensure_ascii=False)}")
    print(f"  pCookies count: {len(p_cookies)}")

    # 设置 Authorization header
    s.headers.update({"Authorization": f"Bearer {access_token}"})

    # Step 2: 测试 invite/create - 创建邀请签到
    print("\n[2] 测试 invite/create - 创建邀请签到")
    # 尝试不同参数组合
    create_tests = [
        {"courseId": "257485372", "classId": "132821141"},
        {"courseId": "257485372", "classId": "132821141", "signType": "4"},
        {"activeId": "", "courseId": "257485372", "classId": "132821141"},
        {"courseId": "257485372", "classId": "132821141", "activeId": "0"},
    ]
    for params in create_tests:
        label = f"create({json.dumps(params, separators=(',', ':'))})"
        resp = safe_req("POST", s, f"{XIUCAT_BASE}/sign/invite/create", json=params)
        print_resp(label, resp)

    # Step 3: 测试 invite/verify - 验证邀请
    print("\n[3] 测试 invite/verify - 验证邀请")
    verify_tests = [
        {"token": "test", "courseId": "257485372", "classId": "132821141"},
        {"token": "123456", "activeId": "0"},
        {"token": "abc", "activeId": "1"},
    ]
    for params in verify_tests:
        label = f"verify({json.dumps(params, separators=(',', ':'))})"
        resp = safe_req("GET", s, f"{XIUCAT_BASE}/sign/invite/verify", params=params)
        print_resp(label, resp)

    # Step 4: 测试 invite/checkInfo - 检查签到信息
    print("\n[4] 测试 invite/checkInfo - 检查签到信息")
    checkinfo_tests = [
        {"activeId": "0"},
        {"activeId": "1"},
        {"activeId": "257485372"},
        {"activeId": "test"},
    ]
    for params in checkinfo_tests:
        label = f"checkInfo(activeId={params['activeId']})"
        resp = safe_req("GET", s, f"{XIUCAT_BASE}/sign/invite/checkInfo", params=params)
        print_resp(label, resp)

    # Step 5: 测试 invite/location - 获取位置
    print("\n[5] 测试 invite/location - 获取位置")
    location_tests = [
        {"activeId": "0"},
        {"activeId": "1"},
    ]
    for params in location_tests:
        label = f"location(activeId={params['activeId']})"
        resp = safe_req("GET", s, f"{XIUCAT_BASE}/sign/invite/location", params=params)
        print_resp(label, resp)

    # Step 6: 测试 invite/qrcode - 二维码
    print("\n[6] 测试 invite/qrcode - 二维码")
    qrcode_tests = [
        {"inviteToken": "test"},
        {"inviteToken": "123456"},
        {"inviteToken": "abc"},
    ]
    for params in qrcode_tests:
        label = f"qrcode(inviteToken={params['inviteToken']})"
        resp = safe_req("POST", s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
        print_resp(label, resp)

    # Step 7: 探索更多 V2 API 端点
    print("\n[7] 探索更多 V2 API 端点")
    extra_endpoints = [
        ("GET", f"{XIUCAT_BASE}/sign/list", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/activeList", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/taskList", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/info", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/status", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/doSign", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/normal", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/location", {"courseId": "257485372", "classId": "132821141",
                     "latitude": "39.9042", "longitude": "116.4074", "address": "北京"}),
        ("GET", f"{XIUCAT_BASE}/sign/qrCode", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/qrCode", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/course/list", {}),
        ("GET", f"{XIUCAT_BASE}/course/info", {"courseId": "257485372"}),
        ("GET", f"{XIUCAT_BASE}/user/info", {}),
        ("GET", f"{XIUCAT_BASE}/auth/check", {}),
        ("GET", f"{XIUCAT_BASE}/auth/refresh", {}),
    ]
    for method, url, params in extra_endpoints:
        label = f"{method} {url.split('/v2/')[-1]}"
        if method == "GET":
            resp = safe_req("GET", s, url, params=params)
        else:
            resp = safe_req("POST", s, url, json=params)
        print_resp(label, resp)

    # Step 8: 尝试用教师账号登录 xiucat
    print("\n[8] 用教师账号登录 xiucat V2 API")
    tea_login_resp = safe_req("POST", s, f"{XIUCAT_BASE}/auth/login",
                              json={"phone": "19712720708", "password": "3.1415926Cpy"})
    print_resp("teacher login", tea_login_resp)

    if tea_login_resp and tea_login_resp.status_code in (200, 201):
        tea_data = tea_login_resp.json()
        tea_token = tea_data["data"]["tInfo"]["accessToken"]
        print(f"  教师token: {tea_token[:80]}...")

        # 用教师 token 测试邀请签到创建
        tea_s = requests.Session()
        tea_s.verify = False
        tea_s.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {tea_token}",
            "User-Agent": "Mozilla/5.0"
        })

        print("\n  教师创建邀请签到:")
        resp = safe_req("POST", tea_s, f"{XIUCAT_BASE}/sign/invite/create",
                        json={"courseId": "257485372", "classId": "132821141"})
        print_resp("teacher create", resp)

    # Step 9: 探索 V2 API 的其他路径
    print("\n[9] 探索 V2 API 其他路径")
    v2_paths = [
        ("GET", "https://api-test.xiucat.top/v2/"),
        ("GET", "https://api-test.xiucat.top/v2/student/"),
        ("GET", "https://api-test.xiucat.top/v2/teacher/"),
        ("GET", "https://api-test.xiucat.top/v2/admin/"),
        ("GET", "https://api-test.xiucat.top/v2/student/sign/"),
        ("GET", "https://api-test.xiucat.top/v2/student/sign/invite/"),
        ("GET", "https://api-test.xiucat.top/api/"),
        ("GET", "https://api-test.xiucat.top/health"),
        ("GET", "https://api-test.xiucat.top/api-docs"),
        ("GET", "https://api-test.xiucat.top/swagger"),
        ("GET", "https://api-test.xiucat.top/v2/docs"),
    ]
    for method, url in v2_paths:
        resp = safe_req(method, s, url)
        print_resp(f"{method} {url}", resp)

    # Step 10: 用 pCookies 做代理签到测试
    print("\n[10] 使用 pCookies 直接测试超星签到 (通过 xiucat 代理)")
    # 解析 pCookies
    cookie_dict = {}
    for ck in p_cookies:
        parts = ck.split(";")[0]
        if "=" in parts:
            k, v = parts.split("=", 1)
            cookie_dict[k.strip()] = v.strip()

    print(f"  解析出的 cookies: {list(cookie_dict.keys())}")

    # 创建使用 xiucat 返回 cookies 的 session
    proxy_s = requests.Session()
    proxy_s.verify = False
    for k, v in cookie_dict.items():
        proxy_s.cookies.set(k, v, domain=".chaoxing.com")
    proxy_s.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    # 测试超星签到接口
    test_urls = [
        f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?courseId=257485372&classId=132821141",
        f"https://mooc1-api.chaoxing.com/mooc-ans/pptSign/stuSignajax?courseId=257485372&classId=132821141",
    ]
    for url in test_urls:
        label = f"proxy GET {url.split('.com')[-1]}"
        resp = safe_req("GET", proxy_s, url)
        print_resp(label, resp)

    print("\n" + "=" * 80)
    print("深入测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
