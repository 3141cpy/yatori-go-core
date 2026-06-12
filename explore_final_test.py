#!/usr/bin/env python3
"""
下载 student-sign 模块并测试 ifNeedVCode 参数
"""

import requests, urllib3, re, json

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

def main():
    # ===== 1. 下载 student-sign 模块 =====
    print("=" * 70)
    print("  1. 下载 student-sign.CSp55DiW.js")
    print("=" * 70)

    r = requests.get("https://cx.xiucat.top/assets/student-sign.CSp55DiW.js",
                     verify=False, timeout=30)
    js = r.text
    print(f"JS长度: {len(js)}")
    print(f"\n完整内容:\n{js}")

    # ===== 2. 下载 xuexitongQrcode 模块 =====
    print("\n" + "=" * 70)
    print("  2. 下载 xuexitongQrcode.SyNWpVNz.js")
    print("=" * 70)

    r = requests.get("https://cx.xiucat.top/assets/xuexitongQrcode.SyNWpVNz.js",
                     verify=False, timeout=30)
    js2 = r.text
    print(f"JS长度: {len(js2)}")
    if len(js2) < 30000:
        print(f"\n完整内容:\n{js2}")
    else:
        # 搜索关键函数
        for kw in ['Oe', 'Re', 'je', 'De', 'Ve']:
            idx = js2.find(kw + '(')
            if idx != -1:
                context = js2[max(0, idx-200):idx+500]
                print(f"\n  {kw} 位置 {idx}:")
                print(f"  {context[:500]}")

    # ===== 3. 下载 useDefaultLocation 模块 =====
    print("\n" + "=" * 70)
    print("  3. 下载 useDefaultLocation.DyP27wt5.js")
    print("=" * 70)

    r = requests.get("https://cx.xiucat.top/assets/useDefaultLocation.DyP27wt5.js",
                     verify=False, timeout=30)
    js3 = r.text
    print(f"JS长度: {len(js3)}")
    if len(js3) < 30000:
        print(f"\n完整内容:\n{js3}")

    # ===== 4. 下载 useFaceObjectId 模块 =====
    print("\n" + "=" * 70)
    print("  4. 下载 useFaceObjectId.r2TjA-na.js")
    print("=" * 70)

    r = requests.get("https://cx.xiucat.top/assets/useFaceObjectId.r2TjA-na.js",
                     verify=False, timeout=30)
    js4 = r.text
    print(f"JS长度: {len(js4)}")
    if len(js4) < 30000:
        print(f"\n完整内容:\n{js4}")

    # ===== 5. 测试 ifNeedVCode 参数 =====
    print("\n" + "=" * 70)
    print("  5. 测试 ifNeedVCode 参数")
    print("=" * 70)

    # 登录
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
    }

    # 5a. /v2/student/sign/normal + ifNeedVCode
    print("\n  [5a] sign/normal + ifNeedVCode=0...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 5b. ifNeedVCode=1
    print("\n  [5b] sign/normal + ifNeedVCode=1...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 1},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 5c. /v2/student/sign/qrcode + ifNeedVCode
    print("\n  [5c] sign/qrcode + ifNeedVCode=0...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/qrcode",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "enc": "test",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 5d. /v2/student/sign/location + ifNeedVCode
    print("\n  [5d] sign/location + ifNeedVCode=0...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/location",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "address": "河南省郑州市", "locationText": "河南省郑州市",
                                "name": "3141cpy",
                                "ifNeedVCode": 0},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== 6. 测试完整的签到流程 =====
    print("\n" + "=" * 70)
    print("  6. 测试完整签到流程 (使用正确的参数)")
    print("=" * 70)

    # 从QR scan代码中提取的参数:
    # nickname, activeId, enc, courseName, ifNeedVCode, currentFaceId
    # 加上位置信息: latitude, longitude, address, locationText

    # 6a. 普通签到 (mode1 via student/sign/normal)
    print("  [6a] 普通签到 - sign/normal...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 6b. 位置签到 (sign/location)
    print("\n  [6b] 位置签到 - sign/location...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/location",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "address": "河南省郑州市", "locationText": "河南省郑州市",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 6c. 二维码签到 (sign/qrcode)
    print("\n  [6c] 二维码签到 - sign/qrcode...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/qrcode",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "enc": "test_enc",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== 7. 测试对Course1的活动签到 =====
    print("\n" + "=" * 70)
    print("  7. 测试对Course1的活动签到")
    print("=" * 70)

    # 7a. Course1活动
    print("  [7a] Course1 - sign/normal...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "5000165046206",
                                "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                                "courseName": COURSE1_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== 8. 测试对已结束活动的签到 =====
    print("\n" + "=" * 70)
    print("  8. 测试对已结束活动的签到 (补签)")
    print("=" * 70)

    # 8a. 已结束活动 - sign/normal
    print("  [8a] 已结束活动 - sign/normal...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 8b. 已结束活动 - sign/location
    print("\n  [8b] 已结束活动 - sign/location...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/location",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "address": "河南省郑州市", "locationText": "河南省郑州市",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    main()
