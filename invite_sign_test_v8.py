#!/usr/bin/env python3
"""xiucat.top V2 API - 用真实 aId 完成签到流程"""

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
    print("xiucat.top V2 API - 用真实 aId 完成签到流程")
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

    # Step 3: 获取签到活动列表
    print("\n[3] 获取签到活动列表")
    activities_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/activities",
                               json={"fid": str(stu_fid), "courseId": "257485372", "classId": "132821141"})
    print_resp("activities", activities_resp)

    activities = []
    if activities_resp:
        try:
            data = activities_resp.json()
            if data.get("code") == 200:
                activities = data["data"]
                print(f"\n  ★ 获取到 {len(activities)} 个签到活动:")
                for act in activities:
                    print(f"    aId={act['aId']}, name={act['aName']}, status={act['status']}, endTime={act['endTime']}")
        except:
            pass

    # Step 4: 用真实的 aId 测试签到
    print("\n[4] 用真实的 aId 测试签到")
    if activities:
        # 用最近的签到活动测试
        test_aids = [str(activities[0]["aId"]), str(activities[2]["aId"])]
        for aid in test_aids:
            print(f"\n  --- 测试 aId={aid} ---")

            # sign/normal
            normal_params = {
                "activeId": aid,
                "courseName": "测试课程",
                "ifNeedVCode": 0,
                "nickname": "3141cpy",
                "courseId": "257485372",
                "classId": "132821141",
            }
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=normal_params)
            print_resp(f"normal aId={aid}", resp)

            # sign/location
            location_params = {
                "activeId": aid,
                "courseName": "测试课程",
                "ifNeedVCode": 0,
                "nickname": "3141cpy",
                "courseId": "257485372",
                "classId": "132821141",
                "locationText": "北京",
                "latitude": "39.9042",
                "longitude": "116.4074",
                "address": "北京",
            }
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=location_params)
            print_resp(f"location aId={aid}", resp)

            # sign/qrCode
            qrcode_params = {
                "activeId": aid,
                "courseName": "测试课程",
                "ifNeedVCode": 0,
                "nickname": "3141cpy",
                "courseId": "257485372",
                "classId": "132821141",
                "enc": "test",
                "locationText": "北京",
                "latitude": "39.9042",
                "longitude": "116.4074",
                "address": "北京",
            }
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/qrCode", json=qrcode_params)
            print_resp(f"qrCode aId={aid}", resp)

    # Step 5: 创建邀请 + 用真实 aId 签到
    print("\n[5] 创建邀请 + 用真实 aId 签到")
    create_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create",
                           json={"courseId": "257485372", "classId": "132821141"})
    invite_token = create_resp.json()["data"]["token"]
    print(f"  inviteToken: {invite_token}")

    if activities:
        aid = str(activities[0]["aId"])
        print(f"\n  用 aId={aid} + inviteToken 签到:")

        # sign/normal with invite token
        normal_params = {
            "activeId": aid,
            "courseName": "测试课程",
            "ifNeedVCode": 0,
            "token": invite_token,
            "nickname": "3141cpy",
            "courseId": "257485372",
            "classId": "132821141",
        }
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=normal_params)
        print_resp("normal with invite", resp)

        # sign/location with invite token
        location_params = {
            "activeId": aid,
            "courseName": "测试课程",
            "ifNeedVCode": 0,
            "token": invite_token,
            "nickname": "3141cpy",
            "courseId": "257485372",
            "classId": "132821141",
            "locationText": "北京",
            "latitude": "39.9042",
            "longitude": "116.4074",
            "address": "北京",
        }
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=location_params)
        print_resp("location with invite", resp)

    # Step 6: 教师创建邀请 + 学生用真实 aId 签到
    print("\n[6] 教师创建邀请 + 学生用真实 aId 签到")
    tea_create_resp = safe_req("POST", tea_s, f"{XIUCAT_BASE}/sign/invite/create",
                               json={"courseId": "257485372", "classId": "132821141"})
    tea_invite_token = tea_create_resp.json()["data"]["token"]
    print(f"  教师邀请token: {tea_invite_token}")

    if activities:
        aid = str(activities[0]["aId"])

        # 学生验证教师邀请
        verify_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/verify",
                               params={"token": tea_invite_token})
        print_resp("student verify teacher invite", verify_resp)

        # 学生用教师邀请签到
        print(f"\n  学生用教师邀请 + aId={aid} 签到:")
        normal_params = {
            "activeId": aid,
            "courseName": "测试课程",
            "ifNeedVCode": 0,
            "token": tea_invite_token,
            "nickname": "3141cpy",
            "courseId": "257485372",
            "classId": "132821141",
        }
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=normal_params)
        print_resp("student normal with teacher invite", resp)

        location_params = {
            "activeId": aid,
            "courseName": "测试课程",
            "ifNeedVCode": 0,
            "token": tea_invite_token,
            "nickname": "3141cpy",
            "courseId": "257485372",
            "classId": "132821141",
            "locationText": "北京",
            "latitude": "39.9042",
            "longitude": "116.4074",
            "address": "北京",
        }
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=location_params)
        print_resp("student location with teacher invite", resp)

    # Step 7: invite/qrcode 探索 - enc 和 vCodeType
    print("\n[7] invite/qrcode 探索 - enc 和验证码类型")
    if activities:
        aid = str(activities[0]["aId"])
        qrcode_tests = [
            {"inviteToken": invite_token, "activeId": aid, "enc": "0", "vCodeType": 0},
            {"inviteToken": invite_token, "activeId": aid, "enc": "0", "vCodeType": 1},
            {"inviteToken": invite_token, "activeId": aid, "enc": "0", "codeType": 0},
            {"inviteToken": invite_token, "activeId": aid, "enc": "0", "type": 0},
            {"inviteToken": invite_token, "activeId": aid, "enc": "0", "signType": 0},
            {"inviteToken": invite_token, "activeId": aid, "enc": "0", "ifNeedVCode": 0},
        ]
        for params in qrcode_tests:
            extra_key = [k for k in params if k not in ("inviteToken", "activeId", "enc")][0]
            label = f"invite_qr(enc=0, {extra_key}={params[extra_key]})"
            resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
            print_resp(label, resp)

    # Step 8: 探索 checkInfo 用真实 aId
    print("\n[8] 探索 checkInfo 用真实 aId")
    if activities:
        for act in activities[:3]:
            aid = str(act["aId"])
            check_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                                  params={"token": invite_token, "activeId": aid})
            print_resp(f"checkInfo aId={aid} ({act['aName']})", check_resp)

    # Step 9: 探索 location 用真实 aId
    print("\n[9] 探索 location 用真实 aId")
    if activities:
        for act in activities[:3]:
            aid = str(act["aId"])
            loc_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/location",
                                params={"token": invite_token, "activeId": aid})
            print_resp(f"location aId={aid} ({act['aName']})", loc_resp)

    # Step 10: 用超星原始接口验证签到状态
    print("\n[10] 用超星原始接口验证签到状态")
    if activities:
        aid = str(activities[0]["aId"])
        # 用 xiucat 返回的 pCookies
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

        # 查询签到状态
        status_urls = [
            f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={aid}&courseId=257485372&classId=132821141",
            f"https://mobilelearn.chaoxing.com/pptSign/signInfo?activeId={aid}",
        ]
        for url in status_urls:
            label = f"GET {url.split('.com')[-1][:60]}"
            resp = safe_req("GET", proxy_s, url)
            print_resp(label, resp)

    print("\n" + "=" * 80)
    print("完整签到流程测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
