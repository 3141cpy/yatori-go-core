#!/usr/bin/env python3
"""xiucat.top V2 API - 教师发起签到 + 学生邀请签到完整流程"""

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
    print("xiucat.top V2 API - 教师发起签到 + 学生邀请签到完整流程")
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
    print(f"  学生登录成功")

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
    print(f"  教师登录成功")

    # Step 3: 教师创建邀请签到
    print("\n[3] 教师创建邀请签到")
    tea_create_resp = safe_req("POST", tea_s, f"{XIUCAT_BASE}/sign/invite/create",
                               json={"courseId": "257485372", "classId": "132821141"})
    print_resp("teacher create invite", tea_create_resp)

    tea_invite_token = None
    if tea_create_resp:
        try:
            data = tea_create_resp.json()
            if data.get("code") == 200:
                tea_invite_token = data["data"]["token"]
                print(f"  教师邀请token: {tea_invite_token}")
        except:
            pass

    # Step 4: 学生验证教师的邀请
    print("\n[4] 学生验证教师的邀请")
    if tea_invite_token:
        verify_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify",
                               params={"token": tea_invite_token})
        print_resp("student verify teacher invite", verify_resp)

        # Step 5: 学生获取签到配置
        print("\n[5] 学生获取签到配置")
        checkinfo_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                                  params={"token": tea_invite_token, "activeId": "257485372"})
        print_resp("student checkInfo", checkinfo_resp)

        other_id = None
        if checkinfo_resp:
            try:
                data = checkinfo_resp.json()
                if data.get("code") == 200:
                    other_id = data["data"]["otherId"]
                    print(f"  otherId: {other_id}")
                    print(f"  配置: {json.dumps(data['data'], ensure_ascii=False)}")
            except:
                pass

        # Step 6: 学生获取位置信息
        print("\n[6] 学生获取位置信息")
        if other_id:
            location_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/location",
                                     params={"token": tea_invite_token, "activeId": str(other_id)})
            print_resp("student location", location_resp)

        # Step 7: 学生尝试签到 (sign/normal)
        print("\n[7] 学生尝试签到 (sign/normal)")
        if other_id:
            normal_params = {
                "activeId": str(other_id),
                "courseName": "测试课程",
                "ifNeedVCode": 0,
                "token": tea_invite_token,
                "nickname": "3141cpy",
                "courseId": "257485372",
                "classId": "132821141",
            }
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=normal_params)
            print_resp("student normal sign", resp)

        # Step 8: 学生尝试签到 (sign/location)
        print("\n[8] 学生尝试签到 (sign/location)")
        if other_id:
            location_params = {
                "activeId": str(other_id),
                "courseName": "测试课程",
                "nickname": "3141cpy",
                "locationText": "北京",
                "latitude": "39.9042",
                "longitude": "116.4074",
                "address": "北京",
                "ifNeedVCode": 0,
                "token": tea_invite_token,
                "courseId": "257485372",
                "classId": "132821141",
            }
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=location_params)
            print_resp("student location sign", resp)

        # Step 9: 学生尝试签到 (sign/qrCode)
        print("\n[9] 学生尝试签到 (sign/qrCode)")
        if other_id:
            qrcode_params = {
                "activeId": str(other_id),
                "courseName": "测试课程",
                "nickname": "3141cpy",
                "enc": "0",
                "locationText": "北京",
                "latitude": "39.9042",
                "longitude": "116.4074",
                "address": "北京",
                "ifNeedVCode": 0,
                "token": tea_invite_token,
                "courseId": "257485372",
                "classId": "132821141",
            }
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/qrCode", json=qrcode_params)
            print_resp("student qrCode sign", resp)

    # Step 10: 探索 invite/qrcode 端点 (验证码类型为数字)
    print("\n[10] 探索 invite/qrcode 端点")
    if tea_invite_token and other_id:
        invite_qr_tests = [
            {"inviteToken": tea_invite_token, "activeId": str(other_id), "enc": 0},
            {"inviteToken": tea_invite_token, "activeId": str(other_id), "enc": 1},
            {"inviteToken": tea_invite_token, "activeId": str(other_id), "enc": 2},
            {"inviteToken": tea_invite_token, "activeId": str(other_id), "enc": 3},
            {"inviteToken": tea_invite_token, "activeId": str(other_id), "enc": 4},
            {"inviteToken": tea_invite_token, "activeId": "257485372", "enc": 0},
        ]
        for params in invite_qr_tests:
            label = f"invite_qr(enc={params['enc']}, activeId={params['activeId']})"
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
            print_resp(label, resp)

    # Step 11: 用超星原始接口 - 教师发起签到
    print("\n[11] 用超星原始接口 - 教师发起签到")
    # 从教师 xiucat 登录获取 pCookies
    tea_pcookies = tea_data["data"].get("pCookies", [])
    tea_cookie_dict = {}
    for ck in tea_pcookies:
        parts = ck.split(";")[0]
        if "=" in parts:
            k, v = parts.split("=", 1)
            tea_cookie_dict[k.strip()] = v.strip()

    tea_proxy_s = requests.Session()
    tea_proxy_s.verify = False
    for k, v in tea_cookie_dict.items():
        tea_proxy_s.cookies.set(k, v, domain=".chaoxing.com")
    tea_proxy_s.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    # 教师发起普通签到
    print("\n  教师发起普通签到:")
    sign_create_urls = [
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/sign",
         {"courseId": "257485372", "classId": "132821141", "signType": "0"}),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/sign",
         {"courseId": "257485372", "classId": "132821141", "signType": "1"}),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/sign",
         {"courseId": "257485372", "classId": "132821141", "signType": "2"}),
        ("POST", "https://mobilelearn.chaoxing.com/pptSign/sign",
         {"courseId": "257485372", "classId": "132821141", "signType": "3"}),
    ]
    for method, url, data in sign_create_urls:
        label = f"teacher sign(signType={data['signType']})"
        resp = safe_req("POST", tea_proxy_s, url, data=data)
        print_resp(label, resp)

    # Step 12: 检查签到活动列表
    print("\n[12] 检查签到活动列表")
    # 学生获取课程任务
    stu_pcookies = stu_data["data"].get("pCookies", [])
    stu_cookie_dict = {}
    for ck in stu_pcookies:
        parts = ck.split(";")[0]
        if "=" in parts:
            k, v = parts.split("=", 1)
            stu_cookie_dict[k.strip()] = v.strip()

    stu_proxy_s = requests.Session()
    stu_proxy_s.verify = False
    for k, v in stu_cookie_dict.items():
        stu_proxy_s.cookies.set(k, v, domain=".chaoxing.com")
    stu_proxy_s.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    # 获取课程活动列表
    activity_urls = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/work/getAllWork?courseId=257485372&classId=132821141&cpi=0&ut=s",
        f"https://mooc1-api.chaoxing.com/mooc-ans/anywork/getAnyworkList?courseId=257485372&classId=132821141",
        f"https://mobilelearn.chaoxing.com/pptSign/activeList?courseId=257485372&classId=132821141",
    ]
    for url in activity_urls:
        label = f"GET {url.split('.com')[-1][:60]}"
        resp = safe_req("GET", stu_proxy_s, url)
        print_resp(label, resp)

    # Step 13: 探索 xiucat 的 sign/invite/create 返回的 otherId
    print("\n[13] 分析 otherId=4687248 的含义")
    # otherId 可能是超星的 activeId (签到活动ID)
    # 尝试用 otherId 直接在超星接口查询
    print("\n  用 otherId 在超星接口查询:")
    check_urls = [
        f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId=4687248&courseId=257485372&classId=132821141",
        f"https://mobilelearn.chaoxing.com/pptSign/signInfo?activeId=4687248",
        f"https://mooc1-api.chaoxing.com/mooc-ans/pptSign/signInfo?activeId=4687248",
    ]
    for url in check_urls:
        label = f"GET {url.split('.com')[-1][:60]}"
        resp = safe_req("GET", stu_proxy_s, url)
        print_resp(label, resp)

    # Step 14: 探索 xiucat 是否有获取活动列表的端点
    print("\n[14] 探索 xiucat 获取活动列表端点")
    activity_api_tests = [
        ("GET", f"{XIUCAT_BASE}/sign/activities", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/activeList", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/sign/tasks", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/course/activities", {"courseId": "257485372", "classId": "132821141"}),
        ("GET", f"{XIUCAT_BASE}/course/signList", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/activities", {"courseId": "257485372", "classId": "132821141"}),
        ("POST", f"{XIUCAT_BASE}/sign/activeList", {"courseId": "257485372", "classId": "132821141"}),
    ]
    for method, url, params in activity_api_tests:
        label = f"{method} {url.split('/student/')[-1]}"
        if method == "GET":
            resp = safe_req("GET", stu_s, url, params=params)
        else:
            resp = safe_req("POST", stu_s, url, json=params)
        print_resp(label, resp)

    # Step 15: 完整签到流程 - 用所有参数 + ifNeedVCode
    print("\n[15] 完整签到流程 - sign/normal with all params + ifNeedVCode")
    if other_id:
        full_normal = {
            "activeId": str(other_id),
            "courseName": "测试课程",
            "ifNeedVCode": 0,
            "token": tea_invite_token,
            "nickname": "3141cpy",
            "courseId": "257485372",
            "classId": "132821141",
            "latitude": "39.9042",
            "longitude": "116.4074",
            "address": "北京",
            "locationText": "北京",
            "ifPhoto": 0,
            "openCheckFaceFlag": 0,
            "ifopenAddress": 0,
        }
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=full_normal)
        print_resp("full normal sign", resp)

        full_location = {
            "activeId": str(other_id),
            "courseName": "测试课程",
            "ifNeedVCode": 0,
            "token": tea_invite_token,
            "nickname": "3141cpy",
            "courseId": "257485372",
            "classId": "132821141",
            "latitude": "39.9042",
            "longitude": "116.4074",
            "address": "北京",
            "locationText": "北京",
            "ifPhoto": 0,
            "openCheckFaceFlag": 0,
            "ifopenAddress": 0,
        }
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=full_location)
        print_resp("full location sign", resp)

    print("\n" + "=" * 80)
    print("完整流程测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
