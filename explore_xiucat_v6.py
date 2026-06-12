#!/usr/bin/env python3
"""
测试 xiucat 实际前端使用的 API 端点
发现: 前端使用 /clockin/mode1~4 而非 /v2/student/sign/normal
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re
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
    r = requests.post("https://api-test.xiucat.top/v2/student/auth/login",
                      json={"phone": ACC2_PHONE, "password": ACC2_PWD},
                      verify=False, timeout=20)
    data = r.json()
    token = data["data"]["tInfo"]["accessToken"]
    user_info = data["data"]["userInfo"]
    pcookies = data["data"].get("pCookies", [])
    print(f"  Token获取成功, puid={user_info.get('puid')}, fid={user_info.get('fid')}")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ===== Step 1: 测试 /clockin/whichMode =====
    log_section("Step 1: 测试 /clockin/whichMode")

    # 1a. 基本参数
    print("  [1a] whichMode - 基本参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/whichMode",
                          headers=auth_headers,
                          json={"activeId": "1000155099942"},
                          verify=False, timeout=20)
        log_result("1a-whichMode", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 1b. 更多参数
    print("  [1b] whichMode - 更多参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/whichMode",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "fid": "1257"},
                          verify=False, timeout=20)
        log_result("1b-whichMode-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 1c. 尝试Course1的活动
    print("  [1c] whichMode - Course1活动...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/whichMode",
                          headers=auth_headers,
                          json={"activeId": "5000165046206",
                                "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                                "fid": "1257"},
                          verify=False, timeout=20)
        log_result("1c-whichMode-course1", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 2: 测试 /clockin/mode1 (普通签到) =====
    log_section("Step 2: 测试 /clockin/mode1 (普通签到)")

    # 2a. 基本参数
    print("  [2a] mode1 - 基本参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942"},
                          verify=False, timeout=20)
        log_result("2a-mode1-basic", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 2b. 更多参数
    print("  [2b] mode1 - 更多参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": ""},
                          verify=False, timeout=20)
        log_result("2b-mode1-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 2c. 全参数
    print("  [2c] mode1 - 全参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "uid": ACC2_PUID, "puid": ACC2_PUID,
                                "clientip": "", "appType": "15", "ifTiJiao": "1"},
                          verify=False, timeout=20)
        log_result("2c-mode1-full", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 3: 测试 /clockin/mode2 (二维码签到) =====
    log_section("Step 3: 测试 /clockin/mode2 (二维码签到)")

    print("  [3a] mode2 - 基本参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode2",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "enc": "test"},
                          verify=False, timeout=20)
        log_result("3a-mode2-basic", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    print("  [3b] mode2 - 更多参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode2",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "enc": "test",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": ""},
                          verify=False, timeout=20)
        log_result("3b-mode2-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 4: 测试 /clockin/mode3 (位置签到) =====
    log_section("Step 4: 测试 /clockin/mode3 (位置签到)")

    print("  [4a] mode3 - 基本参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode3",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "latitude": "34.7466", "longitude": "113.6253",
                                "address": "河南省郑州市", "locationText": "河南省郑州市"},
                          verify=False, timeout=20)
        log_result("4a-mode3-basic", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    print("  [4b] mode3 - 更多参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode3",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "address": "河南省郑州市", "locationText": "河南省郑州市"},
                          verify=False, timeout=20)
        log_result("4b-mode3-more", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 5: 测试 /clockin/mode4 (拍照签到) =====
    log_section("Step 5: 测试 /clockin/mode4 (拍照签到)")

    print("  [5a] mode4 - 基本参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode4",
                          headers=auth_headers,
                          json={"activeId": "1000155099942"},
                          verify=False, timeout=20)
        log_result("5a-mode4-basic", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 6: 测试 /clockin/faceScore =====
    log_section("Step 6: 测试 /clockin/faceScore")

    print("  [6a] faceScore - 基本参数...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/faceScore",
                          headers=auth_headers,
                          json={"activeId": "1000155099942"},
                          verify=False, timeout=20)
        log_result("6a-faceScore", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 7: 深入分析JS代码中的签到参数 =====
    log_section("Step 7: 深入分析JS代码中的签到参数")

    print("  下载并分析JS...")
    try:
        r = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
        js = r.text

        # 搜索 clockin 相关代码
        for endpoint in ['clockin/mode1', 'clockin/mode2', 'clockin/mode3', 'clockin/mode4',
                         'clockin/whichMode', 'clockin/faceScore']:
            idx = js.find(endpoint)
            if idx != -1:
                # 获取更大范围的上下文
                context = js[max(0, idx-1000):idx+1000]
                print(f"\n  === {endpoint} 上下文 ===")
                print(f"  {context[:2000]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 8: 尝试对Course1的已结束活动签到 =====
    log_section("Step 8: 尝试对Course1的已结束活动签到")

    # Course1的活动 (学生已签到和未签到的)
    course1_activities = [
        ("5000165046206", "位置签到"),
        ("5000165046204", "二维码签到"),
        ("5000165046200", "普通签到"),
    ]

    for aid, name in course1_activities:
        print(f"\n  [8a] whichMode for {name} (id={aid})...")
        try:
            r = requests.post("https://api-test.xiucat.top/clockin/whichMode",
                              headers=auth_headers,
                              json={"activeId": aid, "courseId": COURSE1_ID,
                                    "classId": COURSE1_CLASS, "fid": "1257"},
                              verify=False, timeout=20)
            log_result(f"8a-whichMode-{aid}", r)
        except Exception as e:
            print(f"  Error: {e}")

    # ===== Step 9: 尝试使用 form-urlencoded 格式 =====
    log_section("Step 9: 尝试 form-urlencoded 格式")

    print("  [9a] mode1 - form-urlencoded...")
    try:
        r = requests.post("https://api-test.xiucat.top/clockin/mode1",
                          headers={"Authorization": f"Bearer {token}"},
                          data={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": ""},
                          verify=False, timeout=20)
        log_result("9a-mode1-form", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Step 10: 综合测试 =====
    log_section("Step 10: 综合测试 - 对未签到的已结束活动签到")

    # 找到未签到的已结束活动
    unsigned_activities = [
        ("1000155099942", "中午吃什么", COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
        ("1000154756982", "自拍签到", COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
        ("1000154557017", "普通签到", COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
    ]

    for aid, name, cid, clid, cname in unsigned_activities:
        print(f"\n  --- 活动: {name} (id={aid}) ---")

        # whichMode
        try:
            r = requests.post("https://api-test.xiucat.top/clockin/whichMode",
                              headers=auth_headers,
                              json={"activeId": aid, "courseId": cid, "classId": clid, "fid": "1257"},
                              verify=False, timeout=20)
            print(f"  whichMode: {r.text[:300]}")
        except Exception as e:
            print(f"  whichMode Error: {e}")

        # mode1
        try:
            r = requests.post("https://api-test.xiucat.top/clockin/mode1",
                              headers=auth_headers,
                              json={"activeId": aid, "courseId": cid, "classId": clid,
                                    "courseName": cname, "nickname": "3141cpy",
                                    "fid": "1257", "latitude": "-1", "longitude": "-1",
                                    "address": "", "locationText": ""},
                              verify=False, timeout=20)
            print(f"  mode1: {r.text[:300]}")
        except Exception as e:
            print(f"  mode1 Error: {e}")

        # mode3
        try:
            r = requests.post("https://api-test.xiucat.top/clockin/mode3",
                              headers=auth_headers,
                              json={"activeId": aid, "courseId": cid, "classId": clid,
                                    "courseName": cname, "nickname": "3141cpy",
                                    "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                    "address": "河南省郑州市", "locationText": "河南省郑州市"},
                              verify=False, timeout=20)
            print(f"  mode3: {r.text[:300]}")
        except Exception as e:
            print(f"  mode3 Error: {e}")

    # ===== 最终总结 =====
    log_section("最终总结")
    print("""
  关键发现:
  1. xiucat 前端使用 /clockin/mode1~4 而非 /v2/student/sign/normal
  2. /clockin/whichMode 用于判断签到类型
  3. /clockin/faceScore 用于人脸验证
  4. 需要进一步分析JS代码找到准确的参数格式
    """)


if __name__ == "__main__":
    main()
