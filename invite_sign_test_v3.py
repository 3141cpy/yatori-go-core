#!/usr/bin/env python3
"""测试 xiucat.top V2 API 邀请签到完整流程"""

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
    print("xiucat.top V2 API 邀请签到完整流程测试")
    print("=" * 80)

    # Step 1: 学生登录
    print("\n[1] 学生登录 xiucat V2 API")
    stu_s = requests.Session()
    stu_s.verify = False
    stu_s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    })

    login_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/auth/login",
                          json={"phone": "18436633997", "password": "3.1415926Cpy"})
    stu_data = login_resp.json()
    stu_token = stu_data["data"]["tInfo"]["accessToken"]
    stu_s.headers.update({"Authorization": f"Bearer {stu_token}"})
    print(f"  学生登录成功, token: {stu_token[:50]}...")

    # Step 2: 教师登录
    print("\n[2] 教师登录 xiucat V2 API")
    tea_s = requests.Session()
    tea_s.verify = False
    tea_s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    })

    tea_login_resp = safe_req("POST", tea_s, f"{XIUCAT_BASE}/auth/login",
                              json={"phone": "19712720708", "password": "3.1415926Cpy"})
    tea_data = tea_login_resp.json()
    tea_token = tea_data["data"]["tInfo"]["accessToken"]
    tea_s.headers.update({"Authorization": f"Bearer {tea_token}"})
    print(f"  教师登录成功, token: {tea_token[:50]}...")

    # Step 3: 学生创建邀请签到
    print("\n[3] 学生创建邀请签到")
    create_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create",
                           json={"courseId": "257485372", "classId": "132821141"})
    print_resp("学生创建邀请", create_resp)

    invite_token = None
    if create_resp:
        try:
            data = create_resp.json()
            if data.get("code") == 200:
                invite_token = data["data"]["token"]
                expires_in = data["data"]["expiresIn"]
                share_path = data["data"]["sharePath"]
                has_face = data["data"]["hasFaceImage"]
                print(f"\n  ★ 邀请创建成功!")
                print(f"  inviteToken: {invite_token}")
                print(f"  expiresIn: {expires_in}秒 ({expires_in/60}分钟)")
                print(f"  sharePath: {share_path}")
                print(f"  hasFaceImage: {has_face}")
        except:
            pass

    if not invite_token:
        print("  创建邀请失败，退出")
        return

    # Step 4: 验证邀请链接 (用刚创建的 token)
    print("\n[4] 验证邀请链接 (用刚创建的 token)")
    verify_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify",
                           params={"token": invite_token})
    print_resp("verify with real token", verify_resp)

    # Step 5: 用另一个账号验证邀请
    print("\n[5] 用教师账号验证邀请")
    verify_resp2 = safe_req("GET", tea_s, f"{XIUCAT_BASE}/sign/invite/verify",
                            params={"token": invite_token})
    print_resp("teacher verify", verify_resp2)

    # Step 6: 检查签到信息 (checkInfo - 需要 token + activeId)
    print("\n[6] 检查签到信息 (checkInfo)")
    checkinfo_tests = [
        {"token": invite_token, "activeId": "0"},
        {"token": invite_token, "activeId": "1"},
        {"token": invite_token, "activeId": "257485372"},
        {"token": invite_token, "activeId": invite_token},
    ]
    for params in checkinfo_tests:
        label = f"checkInfo(activeId={params['activeId']})"
        resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo", params=params)
        print_resp(label, resp)

    # Step 7: 获取位置 (location - 需要 token + activeId)
    print("\n[7] 获取位置 (location)")
    location_tests = [
        {"token": invite_token, "activeId": "0"},
        {"token": invite_token, "activeId": "1"},
    ]
    for params in location_tests:
        label = f"location(activeId={params['activeId']})"
        resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/location", params=params)
        print_resp(label, resp)

    # Step 8: 二维码 (qrcode - 需要 inviteToken + activeId)
    print("\n[8] 二维码 (qrcode)")
    qrcode_tests = [
        {"inviteToken": invite_token, "activeId": "0"},
        {"inviteToken": invite_token, "activeId": "1"},
        {"inviteToken": invite_token, "activeId": "257485372"},
    ]
    for params in qrcode_tests:
        label = f"qrcode(activeId={params['activeId']})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
        print_resp(label, resp)

    # Step 9: 测试签到操作 (sign/normal, sign/location, sign/qrCode)
    print("\n[9] 测试签到操作")
    sign_tests = [
        ("POST", f"{XIUCAT_BASE}/sign/normal",
         {"activeId": "0", "token": invite_token}),
        ("POST", f"{XIUCAT_BASE}/sign/normal",
         {"activeId": "1", "token": invite_token}),
        ("POST", f"{XIUCAT_BASE}/sign/location",
         {"activeId": "0", "token": invite_token, "nickname": "测试",
          "latitude": "39.9042", "longitude": "116.4074", "address": "北京"}),
        ("POST", f"{XIUCAT_BASE}/sign/qrCode",
         {"activeId": "0", "token": invite_token, "nickname": "测试",
          "enc": "test", "signCode": "123456"}),
    ]
    for method, url, params in sign_tests:
        label = f"sign {url.split('/sign/')[-1]}"
        resp = safe_req("POST", stu_s, url, json=params)
        print_resp(label, resp)

    # Step 10: 教师也创建邀请，然后交叉验证
    print("\n[10] 教师创建邀请，然后学生验证")
    tea_create_resp = safe_req("POST", tea_s, f"{XIUCAT_BASE}/sign/invite/create",
                               json={"courseId": "257485372", "classId": "132821141"})
    print_resp("teacher create", tea_create_resp)

    tea_invite_token = None
    if tea_create_resp:
        try:
            data = tea_create_resp.json()
            if data.get("code") == 200:
                tea_invite_token = data["data"]["token"]
                print(f"  教师邀请token: {tea_invite_token}")
        except:
            pass

    if tea_invite_token:
        # 学生验证教师的邀请
        print("\n  学生验证教师邀请:")
        verify_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify",
                               params={"token": tea_invite_token})
        print_resp("student verify teacher invite", verify_resp)

        # 学生用教师邀请 checkInfo
        print("\n  学生用教师邀请 checkInfo:")
        check_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                              params={"token": tea_invite_token, "activeId": "0"})
        print_resp("student checkInfo teacher invite", check_resp)

        # 学生用教师邀请 qrcode
        print("\n  学生用教师邀请 qrcode:")
        qr_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode",
                           json={"inviteToken": tea_invite_token, "activeId": "0"})
        print_resp("student qrcode teacher invite", qr_resp)

    # Step 11: 探索邀请签到的完整参数 - 尝试更多参数组合
    print("\n[11] 探索邀请签到的完整参数")
    # 尝试 verify 带更多参数
    verify_more = [
        {"token": invite_token, "courseId": "257485372", "classId": "132821141"},
        {"token": invite_token, "activeId": "0", "courseId": "257485372"},
    ]
    for params in verify_more:
        label = f"verify({json.dumps(params, separators=(',', ':'))})"
        resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify", params=params)
        print_resp(label, resp)

    # Step 12: 尝试 sign/invite/sign 端点 (直接用邀请签到)
    print("\n[12] 尝试 sign/invite/sign 端点")
    invite_sign_tests = [
        ("POST", f"{XIUCAT_BASE}/sign/invite/sign",
         {"token": invite_token, "activeId": "0"}),
        ("GET", f"{XIUCAT_BASE}/sign/invite/sign",
         {"token": invite_token, "activeId": "0"}),
        ("POST", f"{XIUCAT_BASE}/sign/invite/doSign",
         {"token": invite_token, "activeId": "0"}),
        ("POST", f"{XIUCAT_BASE}/sign/invite/submit",
         {"token": invite_token, "activeId": "0"}),
        ("POST", f"{XIUCAT_BASE}/sign/invite/confirm",
         {"token": invite_token, "activeId": "0"}),
        ("POST", f"{XIUCAT_BASE}/sign/invite/checkin",
         {"token": invite_token, "activeId": "0"}),
    ]
    for method, url, params in invite_sign_tests:
        label = f"{method} {url.split('/invite/')[-1]}"
        if method == "GET":
            resp = safe_req("GET", stu_s, url, params=params)
        else:
            resp = safe_req("POST", stu_s, url, json=params)
        print_resp(label, resp)

    # Step 13: 尝试带 nickname 的邀请签到
    print("\n[13] 尝试带 nickname 的邀请签到")
    nickname_tests = [
        ("POST", f"{XIUCAT_BASE}/sign/invite/sign",
         {"token": invite_token, "activeId": "0", "nickname": "3141cpy"}),
        ("POST", f"{XIUCAT_BASE}/sign/invite/sign",
         {"token": invite_token, "activeId": "0", "nickname": "3141cpy",
          "latitude": "39.9042", "longitude": "116.4074", "address": "北京"}),
        ("POST", f"{XIUCAT_BASE}/sign/invite/qrcode",
         {"inviteToken": invite_token, "activeId": "0", "nickname": "3141cpy"}),
        ("POST", f"{XIUCAT_BASE}/sign/location",
         {"activeId": "0", "token": invite_token, "nickname": "3141cpy",
          "latitude": "39.9042", "longitude": "116.4074", "address": "北京"}),
    ]
    for method, url, params in nickname_tests:
        label = f"{url.split('/sign/')[-1]}"
        resp = safe_req("POST", stu_s, url, json=params)
        print_resp(label, resp)

    # Step 14: 尝试 sign/invite/create 带更多参数
    print("\n[14] 尝试 sign/invite/create 带更多参数")
    create_more = [
        {"courseId": "257485372", "classId": "132821141", "activeId": "1"},
        {"courseId": "257485372", "classId": "132821141", "signType": "1"},
        {"courseId": "257485372", "classId": "132821141", "signType": "2"},
        {"courseId": "257485372", "classId": "132821141", "signType": "3"},
    ]
    for params in create_more:
        label = f"create({json.dumps(params, separators=(',', ':'))})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create", json=params)
        print_resp(label, resp)

    # Step 15: 尝试使用 activeId 参数值
    print("\n[15] 探索 activeId 的含义 - 尝试不同值")
    # activeId 可能是签到活动ID，尝试用 courseId 或其他值
    activeid_tests = [
        {"token": invite_token, "activeId": invite_token},
        {"token": invite_token, "activeId": "257485372"},
        {"token": invite_token, "activeId": "132821141"},
        {"token": invite_token, "activeId": "431407443"},
    ]
    for params in activeid_tests:
        label = f"checkInfo(activeId={params['activeId'][:20]}...)"
        resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo", params=params)
        print_resp(label, resp)

    print("\n" + "=" * 80)
    print("完整流程测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
