#!/usr/bin/env python3
"""xiucat.top V2 API - 用正确位置完成签到"""

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
    print("xiucat.top V2 API - 用正确位置完成签到")
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

    # 教师位置: 郑州市金水区东三街, 34.789097634188714, 113.66507548089818
    TEACHER_LAT = "34.789097634188714"
    TEACHER_LON = "113.66507548089818"
    TEACHER_ADDR = "郑州市金水区东三街郑州大学综合设计研究院有限公司"

    # Step 2: 获取签到活动列表
    print("\n[2] 获取签到活动列表")
    activities_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/activities",
                               json={"fid": "0", "courseId": "257485372", "classId": "132821141"})
    activities = activities_resp.json()["data"]
    for act in activities:
        print(f"  aId={act['aId']}, name={act['aName']}, status={act['status']}")

    # Step 3: 用教师位置签到 - 位置签到 (aId=5000165046206)
    print("\n[3] 用教师位置签到 - 位置签到")
    location_aid = "5000165046206"

    # 先获取签到配置
    create_resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/create",
                           json={"courseId": "257485372", "classId": "132821141"})
    invite_token = create_resp.json()["data"]["token"]
    print(f"  inviteToken: {invite_token}")

    # 获取签到配置
    checkinfo_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                              params={"token": invite_token, "activeId": location_aid})
    checkinfo_data = checkinfo_resp.json()
    print(f"  签到配置: {json.dumps(checkinfo_data.get('data', {}), ensure_ascii=False)}")

    # 获取位置
    loc_resp = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/location",
                        params={"token": invite_token, "activeId": location_aid})
    loc_data = loc_resp.json()
    print(f"  位置信息: {json.dumps(loc_data.get('data', {}), ensure_ascii=False)}")

    # 用教师位置签到
    print("\n  --- sign/location 用教师位置 ---")
    location_params = {
        "activeId": location_aid,
        "courseName": "测试课程",
        "ifNeedVCode": 1,
        "token": invite_token,
        "nickname": "3141cpy",
        "courseId": "257485372",
        "classId": "132821141",
        "locationText": TEACHER_ADDR,
        "latitude": TEACHER_LAT,
        "longitude": TEACHER_LON,
        "address": TEACHER_ADDR,
    }
    resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/location", json=location_params)
    print_resp("location with teacher coords", resp)

    # Step 4: 用教师位置签到 - sign/normal
    print("\n  --- sign/normal 用教师位置 ---")
    normal_params = {
        "activeId": location_aid,
        "courseName": "测试课程",
        "ifNeedVCode": 1,
        "token": invite_token,
        "nickname": "3141cpy",
        "courseId": "257485372",
        "classId": "132821141",
        "locationText": TEACHER_ADDR,
        "latitude": TEACHER_LAT,
        "longitude": TEACHER_LON,
        "address": TEACHER_ADDR,
    }
    resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=normal_params)
    print_resp("normal with teacher coords", resp)

    # Step 5: 二维码签到 (aId=5000165046204)
    print("\n[5] 二维码签到")
    qrcode_aid = "5000165046204"

    # 获取签到配置
    checkinfo_resp2 = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                               params={"token": invite_token, "activeId": qrcode_aid})
    checkinfo_data2 = checkinfo_resp2.json()
    print(f"  签到配置: {json.dumps(checkinfo_data2.get('data', {}), ensure_ascii=False)}")

    # sign/qrCode
    qrcode_params = {
        "activeId": qrcode_aid,
        "courseName": "测试课程",
        "ifNeedVCode": 1,
        "token": invite_token,
        "nickname": "3141cpy",
        "courseId": "257485372",
        "classId": "132821141",
        "enc": "test",
        "locationText": TEACHER_ADDR,
        "latitude": TEACHER_LAT,
        "longitude": TEACHER_LON,
        "address": TEACHER_ADDR,
    }
    resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/qrCode", json=qrcode_params)
    print_resp("qrCode sign", resp)

    # Step 6: 普通签到 (aId=5000165046200)
    print("\n[6] 普通签到")
    normal_aid = "5000165046200"

    # 获取签到配置
    checkinfo_resp3 = safe_req("GET", stu_s, f"{XIUCAT_BASE}/sign/invite/checkInfo",
                               params={"token": invite_token, "activeId": normal_aid})
    checkinfo_data3 = checkinfo_resp3.json()
    print(f"  签到配置: {json.dumps(checkinfo_data3.get('data', {}), ensure_ascii=False)}")

    # sign/normal
    normal_params2 = {
        "activeId": normal_aid,
        "courseName": "测试课程",
        "ifNeedVCode": 1,
        "token": invite_token,
        "nickname": "3141cpy",
        "courseId": "257485372",
        "classId": "132821141",
    }
    resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/normal", json=normal_params2)
    print_resp("normal sign", resp)

    # Step 7: 用超星原始接口 - 直接用教师位置签到
    print("\n[7] 用超星原始接口 - 直接用教师位置签到")
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

    # 位置签到 - 用教师位置
    sign_url = (f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?"
                f"activeId={location_aid}&courseId=257485372&classId=132821141"
                f"&latitude={TEACHER_LAT}&longitude={TEACHER_LON}"
                f"&address={TEACHER_ADDR}")
    resp = safe_req("GET", proxy_s, sign_url)
    print_resp("chaoxing location sign", resp)

    # 普通签到
    sign_url2 = (f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?"
                 f"activeId={normal_aid}&courseId=257485372&classId=132821141")
    resp = safe_req("GET", proxy_s, sign_url2)
    print_resp("chaoxing normal sign", resp)

    # Step 8: 尝试不同位置偏移 - 看看签到范围
    print("\n[8] 尝试不同位置偏移 - 看看签到范围")
    # 教师位置附近的小偏移
    offsets = [
        ("34.789", "113.665", "附近1"),
        ("34.7895", "113.6655", "附近2"),
        ("34.790", "113.666", "附近3"),
        ("34.789098", "113.665075", "精确匹配"),
    ]
    for lat, lon, desc in offsets:
        url = (f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?"
               f"activeId={location_aid}&courseId=257485372&classId=132821141"
               f"&latitude={lat}&longitude={lon}&address=郑州")
        resp = safe_req("GET", proxy_s, url)
        if resp:
            print(f"  [{desc}] lat={lat}, lon={lon}: {resp.text[:200]}")

    # Step 9: 邀请签到 - invite/qrcode with ifNeedVCode
    print("\n[9] 邀请签到 - invite/qrcode with ifNeedVCode")
    invite_qr_tests = [
        {"inviteToken": invite_token, "activeId": location_aid, "enc": "0", "ifNeedVCode": 0},
        {"inviteToken": invite_token, "activeId": location_aid, "enc": "0", "ifNeedVCode": 1},
        {"inviteToken": invite_token, "activeId": normal_aid, "enc": "0", "ifNeedVCode": 0},
        {"inviteToken": invite_token, "activeId": normal_aid, "enc": "0", "ifNeedVCode": 1},
    ]
    for params in invite_qr_tests:
        label = f"invite_qr(aId={params['activeId']}, ifNeedVCode={params['ifNeedVCode']})"
        resp = safe_req("POST", stu_s, f"{XIUCAT_BASE}/sign/invite/qrcode", json=params)
        print_resp(label, resp)

    # Step 10: 完整签到流程总结
    print("\n" + "=" * 80)
    print("签到流程总结")
    print("=" * 80)
    print("""
已发现的 xiucat.top V2 API 邀请签到完整流程:

1. 登录: POST /v2/student/auth/login
   - Body: {"phone": "xxx", "password": "xxx"}
   - 返回: accessToken, refreshToken, pCookies, userInfo

2. 获取签到活动列表: POST /v2/student/sign/activities
   - Body: {"fid": "0", "courseId": "xxx", "classId": "xxx"}
   - 返回: [{aId, aName, status, endTime}]

3. 创建邀请: POST /v2/student/sign/invite/create
   - Body: {"courseId": "xxx", "classId": "xxx"}
   - 返回: {token, expiresIn, sharePath, hasFaceImage}

4. 验证邀请: GET /v2/student/sign/invite/verify?token=xxx
   - 返回: {valid, nickname, hasFaceImage, expiresAt}

5. 获取签到配置: GET /v2/student/sign/invite/checkInfo?token=xxx&activeId=aId
   - 返回: {ifPhoto, ifNeedVCode, otherId, ifopenAddress, openCheckFaceFlag, hasFaceImage}

6. 获取位置: GET /v2/student/sign/invite/location?token=xxx&activeId=aId
   - 返回: {lcTxt, lcLa, lcLo, isDefault}

7. 签到:
   - 普通签到: POST /v2/student/sign/normal
   - 位置签到: POST /v2/student/sign/location
   - 二维码签到: POST /v2/student/sign/qrCode
   - 必需参数: activeId, courseName, ifNeedVCode, nickname
   - 位置签到额外: locationText, latitude, longitude, address
   - 二维码签到额外: enc, locationText, latitude, longitude, address

签到类型 (otherId):
   - 0: 普通签到
   - 2: 二维码签到
   - 4: 位置签到

关键发现:
   - xiucat 通过代理超星 API 实现签到
   - 邀请签到的本质是: A 创建邀请 → B 用邀请中的位置信息签到
   - 位置签到需要使用教师指定的位置坐标
   - 普通签到已显示"您已签到过了"，说明之前通过 xiucat 签到成功过
""")

    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
