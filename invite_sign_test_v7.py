#!/usr/bin/env python3
"""xiucat.top V2 API - 探索 sign/activities 和完整签到流程"""

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
    print("xiucat.top V2 API - 探索 sign/activities 和完整签到流程")
    print("=" * 80)

    # 登录学生
    print("\n[1] 登录学生账号")
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
    stu_fid = stu_data["data"]["userInfo"]["fid"]
    print(f"  学生登录成功, fid={stu_fid}")

    # 登录教师
    print("\n[2] 登录教师账号")
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
    tea_fid = tea_data["data"]["userInfo"]["fid"]
    print(f"  教师登录成功, fid={tea_fid}")

    # Step 3: 探索 sign/activities 端点
    print("\n[3] 探索 sign/activities 端点")
    activities_tests = [
        {"schoolId": "0", "courseId": "257485372", "classId": "132821141"},
        {"schoolId": stu_fid, "courseId": "257485372", "classId": "132821141"},
        {"schoolId": "12", "courseId": "257485372", "classId": "132821141"},
        {"schoolId": "1257", "courseId": "257485372", "classId": "132821141"},
        {"fid": stu_fid, "courseId": "257485372", "classId": "132821141"},
        {"schoolId": "0"},
        {"schoolId": "0", "courseId": "257485372"},
    ]
    for params in activities_tests:
        label = f"activities({json.dumps(params, separators=(',', ':'))})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/activities", json=params)
        print_resp(label, resp)

    # Step 4: 用教师测试 sign/activities
    print("\n[4] 用教师测试 sign/activities")
    tea_activities_tests = [
        {"schoolId": tea_fid, "courseId": "257485372", "classId": "132821141"},
        {"schoolId": "1257", "courseId": "257485372", "classId": "132821141"},
    ]
    for params in tea_activities_tests:
        label = f"tea_activities({json.dumps(params, separators=(',', ':'))})"
        resp = safe_req("POST", tea_s, f"{XIUCAT_BASE}/sign/activities", json=params)
        print_resp(label, resp)

    # Step 5: 探索 invite/qrcode 的 enc 参数 (string 类型)
    print("\n[5] 探索 invite/qrcode 的 enc 参数 (string 类型)")
    # 先创建邀请
    create_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create",
                           json={"courseId": "257485372", "classId": "132821141"})
    invite_token = create_resp.json()["data"]["token"]
    print(f"  inviteToken: {invite_token}")

    enc_tests = [
        {"inviteToken": invite_token, "activeId": "257485372", "enc": "0"},
        {"inviteToken": invite_token, "activeId": "257485372", "enc": "1"},
        {"inviteToken": invite_token, "activeId": "257485372", "enc": "2"},
        {"inviteToken": invite_token, "activeId": "257485372", "enc": "test"},
        {"inviteToken": invite_token, "activeId": "257485372", "enc": invite_token},
    ]
    for params in enc_tests:
        label = f"invite_qr(enc={params['enc'][:20]})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
        print_resp(label, resp)

    # Step 6: 探索更多 sign 端点
    print("\n[6] 探索更多 sign 端点")
    more_sign_tests = [
        ("POST", f"{XIUCAT_BASE}/sign/start", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/launch", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/init", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/create", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/begin", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/preSign", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/prepare", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/current", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/ongoing", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/active", {"courseId": "257485372", "classId": "132821141"}),
    ]
    for method, url, params in more_sign_tests:
        label = f"{method} {url.split('/sign/')[-1]}"
        if method == "GET":
            resp = safe_req("GET", stu_s, url, params=params)
        else:
            resp = safe_req("POST", stu_s, url, json=params)
        print_resp(label, resp)

    # Step 7: 教师探索 sign 端点
    print("\n[7] 教师探索 sign 端点")
    tea_sign_tests = [
        ("POST", f"{XIUCAT_BASE}/sign/start", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/create", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/init", {"courseId": "257485372", "classId": "132821141"}),
    ]
    for method, url, params in tea_sign_tests:
        label = f"tea_{method} {url.split('/sign/')[-1]}"
        resp = safe_req("POST", tea_s, url, json=params)
        print_resp(label, resp)

    # Step 8: 探索 teacher 专用端点
    print("\n[8] 探索 teacher 专用端点")
    teacher_base = "https://api-test.xiucat.top/v2/teacher"
    teacher_tests = [
        ("POST", f"{teacher_base}/auth/login", {"phone": "19712720708", "password": "3.1415926Cpy"}),
        ("POST", f"{teacher_base}/sign/create", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{teacher_base}/sign/start", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{teacher_base}/sign/init", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{teacher_base}/sign/list", {"courseId": "257485372", "classId": "132821141"}),
    ]
    for method, url, params in teacher_tests:
        label = f"{method} {url.split('/v2/')[-1]}"
        if method == "GET":
            resp = safe_req("GET", tea_s, url, params=params)
        else:
            resp = safe_req("POST", tea_s, url, json=params)
        print_resp(label, resp)

    # Step 9: 尝试 sign/activities 带更多参数
    print("\n[9] 尝试 sign/activities 带更多参数")
    more_activities_tests = [
        {"schoolId": "0", "courseId": "257485372", "classId": "132821141", "page": 1, "pageSize": 10},
        {"schoolId": "0", "courseId": "257485372", "classId": "132821141", "type": "sign"},
        {"schoolId": "0", "courseId": "257485372", "classId": "132821141", "status": "active"},
        {"schoolId": "0", "courseId": "257485372", "classId": "132821141", "signType": "0"},
    ]
    for params in more_activities_tests:
        label = f"activities({json.dumps({k: v for k, v in params.items() if k not in ('courseId', 'classId', 'schoolId')}, separators=(',', ':'))})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/activities", json=params)
        print_resp(label, resp)

    # Step 10: 尝试 sign/activities 不带 courseId/classId
    print("\n[10] 尝试 sign/activities 不带 courseId/classId")
    minimal_activities = [
        {"schoolId": "0"},
        {"schoolId": "12"},
        {"schoolId": "1257"},
    ]
    for params in minimal_activities:
        label = f"activities(schoolId={params['schoolId']})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/activities", json=params)
        print_resp(label, resp)

    print("\n" + "=" * 80)
    print("探索完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
