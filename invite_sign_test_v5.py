#!/usr/bin/env python3
"""xiucat.top V2 API 签到 - 完整参数探索"""

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
    print("xiucat.top V2 API 签到 - 完整参数探索")
    print("=" * 80)

    # 登录
    print("\n[1] 登录 xiucat V2 API")
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
    print(f"  登录成功")

    # 创建邀请
    print("\n[2] 创建邀请签到")
    create_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create",
                           json={"courseId": "257485372", "classId": "132821141"})
    create_data = create_resp.json()
    invite_token = create_data["data"]["token"]
    print(f"  inviteToken: {invite_token}")

    # 获取签到配置
    print("\n[3] 获取签到配置")
    checkinfo_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                              params={"token": invite_token, "activeId": "257485372"})
    checkinfo_data = checkinfo_resp.json()
    other_id = checkinfo_data["data"]["otherId"]
    print(f"  otherId: {other_id}")

    # Step 4: 探索 sign/normal 的 "是否验证" 参数
    print("\n[4] 探索 sign/normal 的 '是否验证' 参数")
    # 尝试不同的参数名
    verify_param_tests = [
        {"activeId": str(other_id), "courseName": "测试课程", "ifVerify": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "ifVerify": 1},
        {"activeId": str(other_id), "courseName": "测试课程", "isVerify": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "isVerify": 1},
        {"activeId": str(other_id), "courseName": "测试课程", "verify": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "needVerify": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "ifNeedVCode": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "ifPhoto": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "checkFace": 0},
        {"activeId": str(other_id), "courseName": "测试课程", "openCheckFaceFlag": 0},
    ]
    for params in verify_param_tests:
        label = f"normal({list(params.keys())[-1]}={list(params.values())[-1]})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=params)
        print_resp(label, resp)

    # Step 5: 探索 sign/location 的 locationText 参数
    print("\n[5] 探索 sign/location 的 locationText 参数")
    location_sign_tests = [
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "locationText": "北京"},
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "locationText": "北京", "latitude": "39.9042", "longitude": "116.4074"},
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "locationText": "北京", "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京"},
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "locationText": "北京", "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京", "token": invite_token},
    ]
    for i, params in enumerate(location_sign_tests):
        label = f"location_step{i+1}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=params)
        print_resp(label, resp)

    # Step 6: 探索 sign/qrCode 的完整参数
    print("\n[6] 探索 sign/qrCode 的完整参数")
    qrcode_sign_tests = [
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "enc": "test", "locationText": "北京"},
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "enc": "test", "locationText": "北京", "token": invite_token},
        {"activeId": str(other_id), "courseName": "测试课程", "nickname": "3141cpy",
         "enc": invite_token, "locationText": "北京", "token": invite_token},
    ]
    for i, params in enumerate(qrcode_sign_tests):
        label = f"qr_step{i+1}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/qrCode", json=params)
        print_resp(label, resp)

    # Step 7: 综合测试 - 用所有已知参数
    print("\n[7] 综合测试 - 用所有已知参数")
    full_params_tests = [
        # sign/normal 完整
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token,
         "nickname": "3141cpy", "courseId": "257485372", "classId": "132821141",
         "ifVerify": 0, "ifPhoto": 0, "ifNeedVCode": 0, "openCheckFaceFlag": 0,
         "latitude": "39.9042", "longitude": "116.4074", "address": "北京",
         "locationText": "北京"},
        # sign/location 完整
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token,
         "nickname": "3141cpy", "courseId": "257485372", "classId": "132821141",
         "latitude": "39.9042", "longitude": "116.4074", "address": "北京",
         "locationText": "北京", "ifVerify": 0, "ifPhoto": 0, "ifNeedVCode": 0,
         "openCheckFaceFlag": 0},
        # sign/qrCode 完整
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token,
         "nickname": "3141cpy", "courseId": "257485372", "classId": "132821141",
         "enc": "test", "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京", "locationText": "北京", "ifVerify": 0, "ifPhoto": 0,
         "ifNeedVCode": 0, "openCheckFaceFlag": 0},
    ]
    endpoints = ["normal", "location", "qrCode"]
    for i, (params, endpoint) in enumerate(zip(full_params_tests, endpoints)):
        label = f"full_{endpoint}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/{endpoint}", json=params)
        print_resp(label, resp)

    # Step 8: 探索邀请签到的 qrcode 端点
    print("\n[8] 探索 invite/qrcode 端点 - enc 参数")
    # enc 可能是二维码加密内容
    invite_qrcode_tests = [
        {"inviteToken": invite_token, "activeId": str(other_id), "enc": "0"},
        {"inviteToken": invite_token, "activeId": str(other_id), "enc": "1"},
        {"inviteToken": invite_token, "activeId": str(other_id), "enc": "123456"},
        {"inviteToken": invite_token, "activeId": str(other_id), "enc": invite_token},
        {"inviteToken": invite_token, "activeId": "257485372", "enc": "0"},
        {"inviteToken": invite_token, "activeId": "257485372", "enc": "1"},
    ]
    for params in invite_qrcode_tests:
        label = f"invite_qrcode(enc={params['enc'][:20]}, activeId={params['activeId']})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
        print_resp(label, resp)

    # Step 9: 探索 sign/invite/create 的 activeId 参数
    print("\n[9] 探索 sign/invite/create 带 activeId")
    create_with_activeid = [
        {"courseId": "257485372", "classId": "132821141", "activeId": str(other_id)},
        {"courseId": "257485372", "classId": "132821141", "activeId": "257485372"},
    ]
    for params in create_with_activeid:
        label = f"create(activeId={params['activeId']})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create", json=params)
        print_resp(label, resp)
        if resp:
            try:
                data = resp.json()
                if data.get("code") == 200:
                    new_token = data["data"]["token"]
                    print(f"  新 inviteToken: {new_token}")
                    # 用新 token 验证
                    verify_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify",
                                           params={"token": new_token})
                    print_resp(f"verify new token", verify_resp)
                    # 用新 token checkInfo
                    check_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                                          params={"token": new_token, "activeId": params['activeId']})
                    print_resp(f"checkInfo new token", check_resp)
            except:
                pass

    # Step 10: 尝试 sign/normal 带 ifVerify 和其他验证参数
    print("\n[10] 尝试 sign/normal 带验证参数")
    normal_verify_tests = [
        {"activeId": str(other_id), "courseName": "测试课程", "ifVerify": 0,
         "token": invite_token, "nickname": "3141cpy"},
        {"activeId": str(other_id), "courseName": "测试课程", "ifVerify": 1,
         "token": invite_token, "nickname": "3141cpy"},
        {"activeId": str(other_id), "courseName": "测试课程", "ifVerify": 0,
         "token": invite_token, "nickname": "3141cpy",
         "courseId": "257485372", "classId": "132821141"},
        {"activeId": str(other_id), "courseName": "测试课程", "ifVerify": 0,
         "token": invite_token, "nickname": "3141cpy",
         "courseId": "257485372", "classId": "132821141",
         "latitude": "39.9042", "longitude": "116.4074", "address": "北京"},
    ]
    for i, params in enumerate(normal_verify_tests):
        label = f"normal_verify{i+1}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=params)
        print_resp(label, resp)

    print("\n" + "=" * 80)
    print("完整参数探索完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
