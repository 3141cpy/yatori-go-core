#!/usr/bin/env python3
"""
xiucat.top 最终签到测试 - 使用正确的 /v2/clockin/ API
发现: 正确路径是 /v2/clockin/mode1~4, /v2/clockin/whichMode
"""

import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

ACC2_PHONE = "18436633997"
ACC2_PWD = "3.1415926Cpy"
ACC2_PUID = "431407443"

COURSE2_ID = "262934472"
COURSE2_CLASS = "145110605"
COURSE2_NAME = "好好学习，天天向上"

COURSE1_ID = "257485372"
COURSE1_CLASS = "132821141"
COURSE1_NAME = "111"

BASE_URL = "https://api-test.xiucat.top/v2"

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
    # ===== 登录 xiucat =====
    log_section("登录 xiucat V2")
    r = requests.post(f"{BASE_URL}/student/auth/login",
                      json={"phone": ACC2_PHONE, "password": ACC2_PWD},
                      verify=False, timeout=20)
    data = r.json()
    token = data["data"]["tInfo"]["accessToken"]
    user_info = data["data"]["userInfo"]
    print(f"  Token获取成功, puid={user_info.get('puid')}, fid={user_info.get('fid')}")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ===== Step 1: /v2/clockin/mode1 参数探索 =====
    log_section("Step 1: /v2/clockin/mode1 参数探索")

    # 1a. 最小参数 (address="")
    print("  [1a] mode1 - address=''...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": ""},
                          verify=False, timeout=20)
        log_result("1a-mode1-address", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 1b. 更多参数
    print("  [1b] mode1 - 更多参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1"},
                          verify=False, timeout=20)
        log_result("1b-mode1-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 1c. 全参数
    print("  [1c] mode1 - 全参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市", "uid": ACC2_PUID,
                                "puid": ACC2_PUID, "clientip": "", "appType": "15",
                                "ifTiJiao": "1"},
                          verify=False, timeout=20)
        log_result("1c-mode1-full", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 2: /v2/clockin/whichMode 参数探索 =====
    log_section("Step 2: /v2/clockin/whichMode 参数探索")

    # 2a. 基本参数
    print("  [2a] whichMode - 基本参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/whichMode",
                          headers=auth_headers,
                          json={"activeId": "1000155099942"},
                          verify=False, timeout=20)
        log_result("2a-whichMode", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 2b. 更多参数
    print("  [2b] whichMode - 更多参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/whichMode",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "fid": "1257"},
                          verify=False, timeout=20)
        log_result("2b-whichMode-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 2c. 尝试Course1的活动
    print("  [2c] whichMode - Course1活动...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/whichMode",
                          headers=auth_headers,
                          json={"activeId": "5000165046206",
                                "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                                "fid": "1257"},
                          verify=False, timeout=20)
        log_result("2c-whichMode-course1", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 3: /v2/clockin/mode2 (二维码签到) =====
    log_section("Step 3: /v2/clockin/mode2 (二维码签到)")

    print("  [3a] mode2 - 基本参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode2",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "enc": "test", "address": ""},
                          verify=False, timeout=20)
        log_result("3a-mode2", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 4: /v2/clockin/mode3 (位置签到) =====
    log_section("Step 4: /v2/clockin/mode3 (位置签到)")

    print("  [4a] mode3 - 基本参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode3",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市"},
                          verify=False, timeout=20)
        log_result("4a-mode3", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 5: /v2/clockin/mode4 (拍照签到) =====
    log_section("Step 5: /v2/clockin/mode4 (拍照签到)")

    print("  [5a] mode4 - 基本参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode4",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": ""},
                          verify=False, timeout=20)
        log_result("5a-mode4", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 6: /v2/clockin/userInfo =====
    log_section("Step 6: /v2/clockin/userInfo")

    print("  [6a] GET /v2/clockin/userInfo...")
    try:
        r = requests.get(f"{BASE_URL}/clockin/userInfo",
                         headers=auth_headers, verify=False, timeout=20)
        log_result("6a-userInfo", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 7: /v2/clockin/records =====
    log_section("Step 7: /v2/clockin/records")

    print("  [7a] GET /v2/clockin/records...")
    try:
        r = requests.get(f"{BASE_URL}/clockin/records",
                         headers=auth_headers, verify=False, timeout=20)
        log_result("7a-records", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 8: 逐步补全 mode1 参数 =====
    log_section("Step 8: 逐步补全 mode1 参数")

    # 根据错误消息逐步添加参数
    params_to_try = [
        {"activeId": "1000155099942"},
        {"activeId": "1000155099942", "address": ""},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS, "courseName": COURSE2_NAME},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS, "courseName": COURSE2_NAME, "nickname": "3141cpy"},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS, "courseName": COURSE2_NAME, "nickname": "3141cpy", "fid": "1257"},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS, "courseName": COURSE2_NAME, "nickname": "3141cpy", "fid": "1257", "latitude": "-1"},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS, "courseName": COURSE2_NAME, "nickname": "3141cpy", "fid": "1257", "latitude": "-1", "longitude": "-1"},
        {"activeId": "1000155099942", "address": "", "courseId": COURSE2_ID, "classId": COURSE2_CLASS, "courseName": COURSE2_NAME, "nickname": "3141cpy", "fid": "1257", "latitude": "-1", "longitude": "-1", "locationText": ""},
    ]

    for i, params in enumerate(params_to_try):
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers, json=params, verify=False, timeout=20)
            result = r.json()
            msg = result.get("message", "")
            code = result.get("code", 0)
            if code == 200:
                print(f"  ★★★ 尝试{i}: 成功! {r.text[:500]}")
            elif code != 400 or i == len(params_to_try) - 1:
                print(f"  尝试{i}: code={code}, msg={msg[:200]}")
            else:
                # 只显示新的错误消息
                print(f"  尝试{i}: {msg[:100]}")
        except Exception as e:
            print(f"  尝试{i}: Error: {e}")

    # ===== Step 9: 完整的签到测试 =====
    log_section("Step 9: 完整签到测试 - 所有模式")

    # 对未签到的已结束活动测试所有模式
    unsigned_activities = [
        ("1000155099942", "中午吃什么", COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
        ("1000154756982", "自拍签到", COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
        ("1000154557017", "普通签到", COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
    ]

    for aid, name, cid, clid, cname in unsigned_activities:
        print(f"\n  --- 活动: {name} (id={aid}) ---")

        # mode1 (普通签到)
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers,
                              json={"activeId": aid, "address": "",
                                    "courseId": cid, "classId": clid,
                                    "courseName": cname, "nickname": "3141cpy",
                                    "fid": "1257", "latitude": "-1", "longitude": "-1",
                                    "locationText": ""},
                              verify=False, timeout=20)
            print(f"  mode1: {r.text[:300]}")
        except Exception as e:
            print(f"  mode1 Error: {e}")

        # mode3 (位置签到)
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode3",
                              headers=auth_headers,
                              json={"activeId": aid, "address": "河南省郑州市",
                                    "courseId": cid, "classId": clid,
                                    "courseName": cname, "nickname": "3141cpy",
                                    "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                    "locationText": "河南省郑州市"},
                              verify=False, timeout=20)
            print(f"  mode3: {r.text[:300]}")
        except Exception as e:
            print(f"  mode3 Error: {e}")

    # ===== Step 10: 测试 /v2/student/sign/normal (旧API) =====
    log_section("Step 10: 对比测试旧API /v2/student/sign/normal")

    print("  [10a] 旧API - 全参数...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "locationText": ""},
                          verify=False, timeout=20)
        log_result("10a-old-api", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 11: 探索更多 clockin 端点 =====
    log_section("Step 11: 探索更多 /v2/clockin/ 端点")

    more_endpoints = [
        ("GET", "/clockin/config"),
        ("GET", "/clockin/status"),
        ("POST", "/clockin/status"),
        ("GET", "/clockin/list"),
        ("POST", "/clockin/list"),
        ("GET", "/clockin/detail"),
        ("POST", "/clockin/detail"),
        ("POST", "/clockin/makeup"),
        ("POST", "/clockin/patch"),
        ("POST", "/clockin/resign"),
        ("POST", "/clockin/normal"),
        ("POST", "/clockin/qrcode"),
        ("POST", "/clockin/location"),
        ("POST", "/clockin/photo"),
        ("POST", "/clockin/gesture"),
        ("POST", "/clockin/code"),
        ("GET", "/clockin/activities"),
        ("POST", "/clockin/activities"),
        ("GET", "/clockin/courses"),
        ("POST", "/clockin/courses"),
    ]

    for method, ep in more_endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{ep}", headers=auth_headers,
                                verify=False, timeout=10)
            else:
                r = requests.post(f"{BASE_URL}{ep}", headers=auth_headers,
                                 json={"activeId": "1000155099942"},
                                 verify=False, timeout=10)
            body = r.text[:200]
            if "Cannot" not in body and "404" not in body:
                print(f"  ★ [{method} {ep}] Status: {r.status_code}, Body: {body}")
            else:
                print(f"  [{method} {ep}] 404")
        except Exception as e:
            print(f"  [{method} {ep}] Error: {e}")

    # ===== 最终总结 =====
    log_section("最终总结")
    print("""
  ==================== 关键发现 ====================

  1. xiucat V2 API 正确路径:
     - 登录: POST /v2/student/auth/login
     - 课程: GET /v2/student/sign/courses
     - 活动: POST /v2/student/sign/activities (需要fid)
     - 签到模式判断: POST /v2/clockin/whichMode
     - 普通签到: POST /v2/clockin/mode1
     - 二维码签到: POST /v2/clockin/mode2
     - 位置签到: POST /v2/clockin/mode3
     - 拍照签到: POST /v2/clockin/mode4
     - 人脸评分: POST /v2/clockin/faceScore
     - 用户信息: GET /v2/clockin/userInfo
     - 签到记录: GET /v2/clockin/records

  2. 签到API有两套:
     - /v2/student/sign/* (旧版, 需要"是否验证"参数)
     - /v2/clockin/* (新版, 前端实际使用)

  3. /v2/clockin/mode1 需要 address 参数
     /v2/clockin/whichMode 返回"没有获取到任何实习打卡任务"
     这可能意味着 whichMode 用于实习打卡，不是普通签到

  4. 补签机制待确认:
     - xiucat 可能使用学生Cookie直接签到
     - 或者使用教师账号修改签到状态
     - 需要进一步测试 /v2/clockin/mode1 的完整参数
    """)


if __name__ == "__main__":
    main()
