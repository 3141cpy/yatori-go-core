#!/usr/bin/env python3
"""xiucat.top V2 API 邀请签到 - 完成签到流程测试"""

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
    print("xiucat.top V2 API 邀请签到 - 完成签到流程测试")
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
    print(f"  学生登录成功")

    # Step 2: 创建邀请
    print("\n[2] 创建邀请签到")
    create_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create",
                           json={"courseId": "257485372", "classId": "132821141"})
    create_data = create_resp.json()
    invite_token = create_data["data"]["token"]
    print(f"  inviteToken: {invite_token}")

    # Step 3: 验证邀请
    print("\n[3] 验证邀请")
    verify_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify",
                           params={"token": invite_token})
    print_resp("verify", verify_resp)

    # Step 4: 获取签到配置 (用 courseId 作为 activeId)
    print("\n[4] 获取签到配置 (activeId=courseId)")
    checkinfo_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                              params={"token": invite_token, "activeId": "257485372"})
    print_resp("checkInfo", checkinfo_resp)

    # 解析签到配置
    other_id = None
    if checkinfo_resp:
        try:
            data = checkinfo_resp.json()
            if data.get("code") == 200:
                config = data["data"]
                other_id = config.get("otherId")
                print(f"\n  ★ 签到配置:")
                print(f"    otherId: {other_id}")
                print(f"    ifPhoto: {config.get('ifPhoto')}")
                print(f"    ifNeedVCode: {config.get('ifNeedVCode')}")
                print(f"    ifopenAddress: {config.get('ifopenAddress')}")
                print(f"    openCheckFaceFlag: {config.get('openCheckFaceFlag')}")
                print(f"    hasFaceImage: {config.get('hasFaceImage')}")
        except:
            pass

    if not other_id:
        print("  未获取到 otherId，尝试用已知值 4687248")
        other_id = 4687248

    # Step 5: 用 otherId 作为 activeId 重新获取签到信息
    print(f"\n[5] 用 otherId={other_id} 作为 activeId 重新获取签到信息")
    checkinfo_resp2 = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                               params={"token": invite_token, "activeId": str(other_id)})
    print_resp("checkInfo with otherId", checkinfo_resp2)

    # Step 6: 用 otherId 获取位置信息
    print(f"\n[6] 用 otherId={other_id} 获取位置信息")
    location_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/location",
                             params={"token": invite_token, "activeId": str(other_id)})
    print_resp("location with otherId", location_resp)

    # Step 7: 用 otherId 获取二维码
    print(f"\n[7] 用 otherId={other_id} 获取二维码")
    qrcode_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode",
                           json={"inviteToken": invite_token, "activeId": str(other_id), "enc": "test"})
    print_resp("qrcode with otherId", qrcode_resp)

    # Step 8: 尝试 sign/normal 签到 (带完整参数)
    print(f"\n[8] 尝试 sign/normal 签到 (带完整参数)")
    normal_sign_tests = [
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "courseId": "257485372", "classId": "132821141"},
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "nickname": "3141cpy"},
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "nickname": "3141cpy", "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京"},
    ]
    for params in normal_sign_tests:
        label = f"normal({json.dumps({k: v[:20] if isinstance(v, str) and len(v) > 20 else v for k, v in params.items()}, separators=(',', ':'))})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=params)
        print_resp(label, resp)

    # Step 9: 尝试 sign/location 签到 (带完整参数)
    print(f"\n[9] 尝试 sign/location 签到 (带完整参数)")
    location_sign_tests = [
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "nickname": "3141cpy", "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京"},
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "nickname": "3141cpy", "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京", "courseId": "257485372", "classId": "132821141"},
    ]
    for params in location_sign_tests:
        label = f"location_sign"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=params)
        print_resp(label, resp)

    # Step 10: 尝试 sign/qrCode 签到 (带完整参数)
    print(f"\n[10] 尝试 sign/qrCode 签到 (带完整参数)")
    qrcode_sign_tests = [
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "nickname": "3141cpy", "enc": "test"},
        {"activeId": str(other_id), "token": invite_token, "courseName": "测试课程",
         "nickname": "3141cpy", "enc": invite_token},
    ]
    for params in qrcode_sign_tests:
        label = f"qrCode_sign"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/qrCode", json=params)
        print_resp(label, resp)

    # Step 11: 探索 sign/normal 需要的所有参数
    print(f"\n[11] 逐步添加参数探索 sign/normal")
    # 先用最少的参数
    step_params = [
        {"activeId": str(other_id)},
        {"activeId": str(other_id), "courseName": "测试课程"},
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token},
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token, "nickname": "3141cpy"},
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token, "nickname": "3141cpy",
         "courseId": "257485372"},
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token, "nickname": "3141cpy",
         "courseId": "257485372", "classId": "132821141"},
        {"activeId": str(other_id), "courseName": "测试课程", "token": invite_token, "nickname": "3141cpy",
         "courseId": "257485372", "classId": "132821141", "latitude": "39.9042",
         "longitude": "116.4074", "address": "北京"},
    ]
    for i, params in enumerate(step_params):
        label = f"step{i+1}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=params)
        print_resp(label, resp)

    # Step 12: 探索 sign/location 需要的所有参数
    print(f"\n[12] 逐步添加参数探索 sign/location")
    step_params2 = [
        {"activeId": str(other_id), "nickname": "3141cpy"},
        {"activeId": str(other_id), "nickname": "3141cpy", "courseName": "测试课程"},
        {"activeId": str(other_id), "nickname": "3141cpy", "courseName": "测试课程",
         "token": invite_token},
        {"activeId": str(other_id), "nickname": "3141cpy", "courseName": "测试课程",
         "token": invite_token, "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京"},
        {"activeId": str(other_id), "nickname": "3141cpy", "courseName": "测试课程",
         "token": invite_token, "latitude": "39.9042", "longitude": "116.4074",
         "address": "北京", "courseId": "257485372", "classId": "132821141"},
    ]
    for i, params in enumerate(step_params2):
        label = f"loc_step{i+1}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=params)
        print_resp(label, resp)

    # Step 13: 探索 sign/qrCode 需要的所有参数
    print(f"\n[13] 逐步添加参数探索 sign/qrCode")
    step_params3 = [
        {"activeId": str(other_id), "nickname": "3141cpy", "enc": "test"},
        {"activeId": str(other_id), "nickname": "3141cpy", "enc": "test",
         "courseName": "测试课程"},
        {"activeId": str(other_id), "nickname": "3141cpy", "enc": "test",
         "courseName": "测试课程", "token": invite_token},
        {"activeId": str(other_id), "nickname": "3141cpy", "enc": invite_token,
         "courseName": "测试课程", "token": invite_token},
    ]
    for i, params in enumerate(step_params3):
        label = f"qr_step{i+1}"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/qrCode", json=params)
        print_resp(label, resp)

    # Step 14: 尝试直接用超星原始签到接口 (通过 xiucat 代理的 cookies)
    print(f"\n[14] 直接用超星原始签到接口 (通过 xiucat 代理的 cookies)")
    # 从登录响应获取 pCookies
    p_cookies = stu_data["data"].get("pCookies", [])
    cookie_dict = {}
    for ck in p_cookies:
        parts = ck.split(";")[0]
        if "=" in parts:
            k, v = parts.split("=", 1)
            cookie_dict[k.strip()] = v.strip()

    proxy_s = requests.Session()
    proxy_s.verify = False
    for k, v in cookie_dict.items():
        proxy_s.cookies.set(k, v, domain=".chaoxing.com")
    proxy_s.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    # 尝试获取签到活动列表
    print("\n  获取课程签到活动:")
    activity_urls = [
        f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?courseId=257485372&classId=132821141&activeId={other_id}",
        f"https://mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/getSignInfo?courseId=257485372&classId=132821141&activeId={other_id}",
    ]
    for url in activity_urls:
        label = f"GET {url.split('.com')[-1]}"
        resp = safe_req("GET", proxy_s, url)
        print_resp(label, resp)

    # Step 15: 尝试使用 xiucat 的 sign/invite/create 创建签到后，用超星原始接口签到
    print(f"\n[15] 尝试使用 xiucat 创建的邀请，通过超星原始接口签到")
    # 超星签到接口需要 activeId，otherId 可能就是 activeId
    sign_urls = [
        f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?courseId=257485372&classId=132821141&activeId={other_id}&signCode=&latitude=&longitude=&address=",
        f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?courseId=257485372&classId=132821141&activeId={other_id}&type=4&signCode=&latitude=&longitude=&address=",
    ]
    for url in sign_urls:
        label = f"GET {url.split('.com')[-1][:80]}"
        resp = safe_req("GET", proxy_s, url)
        print_resp(label, resp)

    print("\n" + "=" * 80)
    print("签到流程测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
