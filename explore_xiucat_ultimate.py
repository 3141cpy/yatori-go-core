#!/usr/bin/env python3
"""
xiucat.top 最终测试 - 确认签到机制和补签方法
关键发现:
- ifNeedVCode = "是否验证" 字段 ✓
- API通过学生Cookie调用超星签到
- 已结束活动返回"签到已结束"
- 活跃活动返回"不在可签到范围内"(需要正确位置)
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

BASE_URL = "https://api-test.xiucat.top/v2"

def log_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def main():
    # 登录
    log_section("登录 xiucat V2")
    r = requests.post(f"{BASE_URL}/student/auth/login",
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
    }

    # ===== Step 1: 获取课程列表 =====
    log_section("Step 1: 获取课程列表")
    r = requests.get(f"{BASE_URL}/student/sign/courses",
                     headers=auth_headers, verify=False, timeout=20)
    courses = r.json().get("data", [])
    for c in courses:
        print(f"  课程: {c.get('cName')} (csId={c.get('csId')}, clId={c.get('clId')}, tch={c.get('tch')})")

    # ===== Step 2: 获取活动列表 =====
    log_section("Step 2: 获取活动列表")
    for cid, clid, cname in [(COURSE2_ID, COURSE2_CLASS, COURSE2_NAME),
                              (COURSE1_ID, COURSE1_CLASS, COURSE1_NAME)]:
        print(f"\n  课程: {cname} (csId={cid}, clId={clid})")
        try:
            r = requests.post(f"{BASE_URL}/student/sign/activities",
                              headers=auth_headers,
                              json={"courseId": cid, "classId": clid, "fid": "1257"},
                              verify=False, timeout=20)
            result = r.json()
            activities = result.get("data", [])
            if activities:
                for act in activities:
                    print(f"    活动: id={act.get('aId')}, name={act.get('aName')}, "
                          f"status={act.get('status')}, type={act.get('type')}, "
                          f"ifNeedVCode={act.get('ifNeedVCode')}, ifPhoto={act.get('ifPhoto')}")
            else:
                print(f"    无活动, 响应: {r.text[:300]}")
        except Exception as e:
            print(f"    Error: {e}")

    # ===== Step 3: 获取签到位置信息 =====
    log_section("Step 3: 获取签到位置信息")

    # 3a. 获取Course2活动位置
    print("  [3a] 获取Course2活动位置...")
    for aid in ["1000155099942", "1000155014067"]:
        try:
            r = requests.get(f"{BASE_URL}/student/sign/location",
                             headers=auth_headers,
                             params={"activeId": aid},
                             verify=False, timeout=20)
            print(f"    activeId={aid}: {r.text[:300]}")
        except Exception as e:
            print(f"    Error: {e}")

    # 3b. 获取Course1活动位置
    print("\n  [3b] 获取Course1活动位置...")
    for aid in ["5000165046206", "5000165046204", "5000165046200"]:
        try:
            r = requests.get(f"{BASE_URL}/student/sign/location",
                             headers=auth_headers,
                             params={"activeId": aid},
                             verify=False, timeout=20)
            print(f"    activeId={aid}: {r.text[:300]}")
        except Exception as e:
            print(f"    Error: {e}")

    # ===== Step 4: 获取签到Token =====
    log_section("Step 4: 获取签到Token")
    try:
        r = requests.get(f"{BASE_URL}/student/sign/token",
                         headers=auth_headers, verify=False, timeout=20)
        print(f"  Token: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 5: 获取签到检查信息 =====
    log_section("Step 5: 获取签到检查信息")
    for aid in ["1000155099942", "5000165046206"]:
        try:
            r = requests.get(f"{BASE_URL}/student/sign/checkInfo",
                             headers=auth_headers,
                             params={"activeId": aid},
                             verify=False, timeout=20)
            print(f"  activeId={aid}: {r.text[:500]}")
        except Exception as e:
            print(f"  Error: {e}")

    # ===== Step 6: 获取人脸ID =====
    log_section("Step 6: 获取人脸ID")
    try:
        r = requests.get(f"{BASE_URL}/student/sign/face-id",
                         headers=auth_headers, verify=False, timeout=20)
        print(f"  Face ID: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 7: 获取签到记录 =====
    log_section("Step 7: 获取签到记录")
    try:
        r = requests.get(f"{BASE_URL}/student/sign/records",
                         headers=auth_headers,
                         params={"page": 1, "limit": 10},
                         verify=False, timeout=20)
        print(f"  Records: {r.text[:1000]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 8: 获取班级群组 =====
    log_section("Step 8: 获取班级群组")
    try:
        # 先获取token
        r = requests.get(f"{BASE_URL}/student/sign/token",
                         headers=auth_headers, verify=False, timeout=20)
        token_data = r.json()
        tk = ""
        if token_data.get("data"):
            tk = token_data["data"].get("tk", "")
        print(f"  Token: {tk[:50]}...")

        if tk:
            r = requests.get(f"{BASE_URL}/student/sign/clazzGroup",
                             headers=auth_headers,
                             params={"uid": ACC2_PUID, "token": tk},
                             verify=False, timeout=20)
            print(f"  ClazzGroup: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 9: 测试活跃活动签到 (使用正确位置) =====
    log_section("Step 9: 测试活跃活动签到 (使用正确位置)")

    # 先获取Course1活动的位置信息
    print("  [9a] 获取Course1活动位置信息...")
    course1_location = None
    try:
        r = requests.get(f"{BASE_URL}/student/sign/location",
                         headers=auth_headers,
                         params={"activeId": "5000165046206"},
                         verify=False, timeout=20)
        result = r.json()
        if result.get("data"):
            loc = result["data"]
            course1_location = loc
            print(f"  位置: {json.dumps(loc, ensure_ascii=False)[:300]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 使用正确位置签到
    if course1_location:
        lat = course1_location.get("lcLa", course1_location.get("latitude", "34.7466"))
        lng = course1_location.get("lcLo", course1_location.get("longitude", "113.6253"))
        addr = course1_location.get("lcTxt", course1_location.get("name", "河南省郑州市"))

        print(f"\n  [9b] 使用位置签到: lat={lat}, lng={lng}, addr={addr}")
        try:
            r = requests.post(f"{BASE_URL}/student/sign/location",
                              headers=auth_headers,
                              json={"activeId": "5000165046206",
                                    "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                                    "courseName": COURSE1_NAME, "nickname": "3141cpy",
                                    "fid": "1257",
                                    "latitude": str(lat), "longitude": str(lng),
                                    "address": addr, "locationText": addr,
                                    "name": "3141cpy",
                                    "ifNeedVCode": 0, "currentFaceId": ""},
                              verify=False, timeout=20)
            print(f"  签到结果: {r.text[:500]}")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("  无法获取位置信息")

    # ===== Step 10: 测试邀请签到 =====
    log_section("Step 10: 测试邀请签到")

    # 10a. 创建邀请
    print("  [10a] 创建签到邀请...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/invite/create",
                          headers=auth_headers,
                          json={"defaultLocation": {"name": "河南省郑州市",
                                                    "latitude": 34.7466,
                                                    "longitude": 113.6253}},
                          verify=False, timeout=20)
        print(f"  创建邀请: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 11: 测试 gesture-code 签到 =====
    log_section("Step 11: 测试手势/签到码签到")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/gesture-code",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": "",
                                "gestureCode": "1234"},
                          verify=False, timeout=20)
        print(f"  gesture-code: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 12: 测试 picture 签到 =====
    log_section("Step 12: 测试拍照签到")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/picture",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy",
                                "ifNeedVCode": 0, "currentFaceId": ""},
                          verify=False, timeout=20)
        print(f"  picture: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 13: 测试 group 签到 =====
    log_section("Step 13: 测试群组签到")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/group",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS},
                          verify=False, timeout=20)
        print(f"  group: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 14: 测试 group-aid =====
    log_section("Step 14: 测试群组活动ID")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/group-aid",
                          headers=auth_headers,
                          json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS},
                          verify=False, timeout=20)
        print(f"  group-aid: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 15: 使用超星Cookie直接签到 (对比测试) =====
    log_section("Step 15: 使用超星Cookie直接签到 (对比测试)")

    # 构建超星session
    chaoxing_session = requests.Session()
    chaoxing_session.verify = False
    chaoxing_session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    })

    for pc in pcookies:
        parts = pc.split(";")
        if parts:
            name_value = parts[0].strip()
            if "=" in name_value:
                name, value = name_value.split("=", 1)
                chaoxing_session.cookies.set(name.strip(), value.strip().strip('"'), domain=".chaoxing.com")

    # 15a. 获取签到活动详情
    print("  [15a] 获取签到活动详情...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/getSignDetail",
                    params={"activeId": "5000165046206"},
                    timeout=20)
        print(f"  签到详情: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 15b. 直接签到
    print("\n  [15b] 直接签到 (Course1活动)...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                    params={"activeId": "5000165046206", "clientip": "",
                            "latitude": "-1", "longitude": "-1",
                            "appType": "15", "ifTiJiao": "1", "address": ""},
                    timeout=20)
        print(f"  直接签到: {r.text[:300]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 15c. 获取签到活动列表 (超星API)
    print("\n  [15c] 获取签到活动列表 (超星API)...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
                    params={"courseId": COURSE1_ID, "classId": COURSE1_CLASS, "showNotStarted": "0"},
                    timeout=20)
        data = r.json()
        for act in data.get("activeList", []):
            if act.get("activeType") == 2:
                print(f"    活动: id={act['id']}, name={act.get('nameOne')}, "
                      f"status={act.get('status')}, groupId={act.get('groupId')}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== 最终总结 =====
    log_section("最终总结")
    print("""
  ==================== 关键发现 ====================

  1. xiucat V2 API 完整签到流程:
     a. 登录: POST /v2/student/auth/login → 获取token + pCookies
     b. 课程: GET /v2/student/sign/courses → 获取课程列表
     c. 活动: POST /v2/student/sign/activities → 获取签到活动 (需要fid)
     d. 位置: GET /v2/student/sign/location → 获取活动位置 (需要activeId)
     e. 签到: POST /v2/student/sign/normal|location|qrcode|gesture-code|picture
        参数: activeId, courseId, classId, courseName, nickname, fid,
              latitude, longitude, address, locationText, name,
              ifNeedVCode, currentFaceId

  2. "是否验证" = ifNeedVCode (0=不需要, 1=需要)

  3. 签到机制:
     - xiucat 使用学生的超星Cookie代理调用超星签到API
     - 对活跃活动: 可以签到 (需要正确位置)
     - 对已结束活动: 返回"签到已结束" (超星服务端拒绝)

  4. 补签问题:
     - xiucat的V2 API无法直接对已结束活动签到
     - 超星服务端会拒绝已结束活动的签到请求
     - xiucat的"补签"可能使用了其他方法:
       A. 教师账号修改签到状态 (需要先加入课程)
       B. 超星内部/管理API
       C. 特殊参数绕过"签到已结束"检查
       D. 仅对活跃活动有效，"补签"只是快速签到

  5. 邀请签到:
     - /v2/student/sign/invite/create - 创建邀请
     - /v2/student/sign/invite/verify - 验证邀请
     - /v2/student/sign/invite/checkInfo - 检查信息
     - /v2/student/sign/invite/location - 获取位置
     - /v2/student/sign/invite/qrcode - 二维码签到
     这是"帮签"功能，让好友帮忙扫码签到
    """)


if __name__ == "__main__":
    main()
