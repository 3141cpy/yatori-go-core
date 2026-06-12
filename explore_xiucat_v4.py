#!/usr/bin/env python3
"""
xiucat.top V2 API 精确参数测试
基于前几轮测试发现:
- /v2/student/sign/activities 需要 schoolId (字段名可能不是schoolId)
- /v2/student/sign/normal 需要 "是否验证" 数字参数
- /v2/student/sign/qrcode 需要 enc 字符串
- /v2/student/sign/location 需要 locationText 字符串
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
    print(f"  Token获取成功, puid={user_info.get('puid')}")

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # ===== Step 1: 探索 activities 的 schoolId 字段名 =====
    log_section("Step 1: 探索 activities 的 schoolId 字段名")

    # 尝试不同的字段名
    school_id_fields = [
        {"schoolId": "1257"},
        {"fid": "1257"},
        {"school_id": "1257"},
        {"schoolid": "1257"},
        {"schoolFid": "1257"},
        {"orgId": "1257"},
        {"orgid": "1257"},
        {"universityId": "1257"},
        {"university": "1257"},
        {"collegeId": "1257"},
        {"institutionId": "1257"},
        {"schooldId": "1257"},  # typo version
    ]

    for params in school_id_fields:
        body = {"courseId": COURSE2_ID, "classId": COURSE2_CLASS}
        body.update(params)
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "学校ID不能为空" not in msg:
                print(f"  ★ {list(params.keys())[0]}={list(params.values())[0]}: {r.text[:300]}")
            else:
                key = list(params.keys())[0]
                print(f"  {key}: 仍然报学校ID不能为空")
        except Exception as e:
            print(f"  Error: {e}")

    # 尝试同时传多个字段
    print("\n  尝试同时传多个字段...")
    body = {"courseId": COURSE2_ID, "classId": COURSE2_CLASS,
            "schoolId": "1257", "fid": "1257", "schoolFid": "1257"}
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                          headers=auth_headers, json=body, verify=False, timeout=10)
        log_result("multi-fields", r)
    except Exception as e:
        print(f"  Error: {e}")

    # 尝试字符串数字
    print("  尝试 schoolId 为字符串 '1257' vs 数字 1257...")
    for sid in ["1257", 1257, "0", 0]:
        body = {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": sid}
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "学校ID不能为空" not in msg:
                print(f"  ★ schoolId={sid} (type={type(sid).__name__}): {r.text[:300]}")
            else:
                print(f"  schoolId={sid} (type={type(sid).__name__}): 仍然报学校ID不能为空")
        except Exception as e:
            print(f"  Error: {e}")

    # ===== Step 2: 探索 normal 签到的 "是否验证" 字段 =====
    log_section("Step 2: 探索 normal 签到的 '是否验证' 字段")

    base_body = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
    }

    # 尝试不同的"是否验证"字段名
    verify_fields = [
        {"isVerify": 0},
        {"isVerify": 1},
        {"isVerify": "0"},
        {"needVerify": 0},
        {"needVerify": 1},
        {"verify": 0},
        {"verify": 1},
        {"ifVerify": 0},
        {"ifVerify": 1},
        {"isValidation": 0},
        {"isValidation": 1},
        {"needValidation": 0},
        {"needValidation": 1},
        {"isCheck": 0},
        {"isCheck": 1},
        {"ifTiJiao": 0},
        {"ifTiJiao": 1},
        {"ifTiJiao": "0"},
        {"ifTiJiao": "1"},
    ]

    for vf in verify_fields:
        body = dict(base_body)
        body.update(vf)
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "是否验证必须是数字" not in msg:
                print(f"  ★ {list(vf.keys())[0]}={list(vf.values())[0]}: {r.text[:300]}")
            else:
                key = list(vf.keys())[0]
                print(f"  {key}: 仍然报是否验证必须是数字")
        except Exception as e:
            print(f"  Error: {e}")

    # ===== Step 3: 探索 qrcode 签到的 enc 字段 =====
    log_section("Step 3: 探索 qrcode 签到的 enc 字段")

    qrcode_base = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "enc": "test",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
    }

    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/qrcode",
                          headers=auth_headers, json=qrcode_base, verify=False, timeout=20)
        log_result("qrcode-with-enc", r)
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 4: 探索 location 签到的 locationText 字段 =====
    log_section("Step 4: 探索 location 签到的 locationText 字段")

    location_base = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "latitude": "34.7466",
        "longitude": "113.6253",
        "address": "河南省郑州市",
        "locationText": "河南省郑州市",
    }

    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/location",
                          headers=auth_headers, json=location_base, verify=False, timeout=20)
        log_result("location-with-locationText", r)
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 5: 查找 xiucat 实际的前端应用 =====
    log_section("Step 5: 查找 xiucat 实际前端应用")

    # xiucat.top 主页只是一个导航站，实际应用可能在其他子域名
    possible_urls = [
        "https://app.xiucat.top",
        "https://sign.xiucat.top",
        "https://m.xiucat.top",
        "https://web.xiucat.top",
        "https://student.xiucat.top",
        "https://h5.xiucat.top",
        "https://user.xiucat.top",
        "https://dashboard.xiucat.top",
        "https://panel.xiucat.top",
    ]

    for url in possible_urls:
        try:
            r = requests.get(url, verify=False, timeout=10, allow_redirects=True)
            content_type = r.headers.get("Content-Type", "")
            print(f"  [{url}] Status: {r.status_code}, Type: {content_type}, Body: {r.text[:200]}")
        except requests.exceptions.SSLError:
            print(f"  [{url}] SSL Error")
        except requests.exceptions.ConnectTimeout:
            print(f"  [{url}] Connection Timeout")
        except Exception as e:
            err_type = type(e).__name__
            print(f"  [{url}] {err_type}: {str(e)[:80]}")

    # ===== Step 6: 检查 xiucat 主页的链接 =====
    log_section("Step 6: 检查 xiucat 主页的链接")

    try:
        r = requests.get("https://xiucat.top", verify=False, timeout=20)
        import re
        # 找到所有链接
        links = re.findall(r'href=["\']([^"\']+)["\']', r.text)
        print(f"  所有链接:")
        for link in links:
            print(f"    {link}")

        # 找到所有按钮/卡片链接
        btn_links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*btn[^"\']*["\']', r.text)
        print(f"\n  按钮链接:")
        for link in btn_links:
            print(f"    {link}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 7: 尝试更多的参数组合 =====
    log_section("Step 7: 尝试更多参数组合")

    # 7a. normal 签到 - 尝试所有可能的参数
    print("  [7a] normal 签到 - 全参数...")
    full_body = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
        "schoolId": "1257",
        "fid": "1257",
        "uid": ACC2_PUID,
        "puid": ACC2_PUID,
        "isVerify": 0,
        "needVerify": 0,
        "ifVerify": 0,
        "clientip": "",
        "appType": "15",
        "ifTiJiao": "1",
        "general": "1",
        "sys": "1",
        "ls": "1",
    }
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                          headers=auth_headers, json=full_body, verify=False, timeout=20)
        log_result("7a-normal-full", r)
    except Exception as e:
        print(f"  Error: {e}")

    # 7b. 尝试把所有参数都加上
    print("  [7b] normal 签到 - 极端全参数...")
    extreme_body = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
        "schoolId": "1257",
        "fid": "1257",
        "uid": ACC2_PUID,
        "puid": ACC2_PUID,
        "isVerify": 0,
        "needVerify": 0,
        "ifVerify": 0,
        "verify": 0,
        "isValidation": 0,
        "needValidation": 0,
        "isCheck": 0,
        "clientip": "",
        "appType": "15",
        "ifTiJiao": "1",
        "general": "1",
        "sys": "1",
        "ls": "1",
        "type": "0",
        "signType": "0",
        "activeType": "2",
        "status": "2",
        "isMakeup": 0,
        "makeup": 0,
    }
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                          headers=auth_headers, json=extreme_body, verify=False, timeout=20)
        log_result("7b-normal-extreme", r)
    except Exception as e:
        print(f"  Error: {e}")

    # 7c. 尝试 location 签到全参数
    print("  [7c] location 签到 - 全参数...")
    location_full = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "latitude": "34.7466",
        "longitude": "113.6253",
        "address": "河南省郑州市",
        "locationText": "河南省郑州市",
        "schoolId": "1257",
        "fid": "1257",
        "uid": ACC2_PUID,
        "puid": ACC2_PUID,
        "isVerify": 0,
        "needVerify": 0,
        "ifVerify": 0,
        "verify": 0,
        "clientip": "",
        "appType": "15",
        "ifTiJiao": "1",
    }
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/location",
                          headers=auth_headers, json=location_full, verify=False, timeout=20)
        log_result("7c-location-full", r)
    except Exception as e:
        print(f"  Error: {e}")

    # 7d. 尝试 qrcode 签到全参数
    print("  [7d] qrcode 签到 - 全参数...")
    qrcode_full = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "enc": "test_enc_value",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
        "schoolId": "1257",
        "fid": "1257",
        "uid": ACC2_PUID,
        "puid": ACC2_PUID,
        "isVerify": 0,
        "needVerify": 0,
        "ifVerify": 0,
        "verify": 0,
        "clientip": "",
        "appType": "15",
        "ifTiJiao": "1",
    }
    try:
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/qrcode",
                          headers=auth_headers, json=qrcode_full, verify=False, timeout=20)
        log_result("7d-qrcode-full", r)
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 8: 尝试通过 xiucat 的代理直接调用超星API =====
    log_section("Step 8: 尝试通过 xiucat 代理调用超星API")

    # xiucat 登录返回了 pCookies，这些cookie设置在 .xiucat.top 域名下
    # 这意味着 xiucat 的前端可以通过这些cookie直接访问超星的API
    # 但由于跨域限制，前端无法直接访问 chaoxing.com
    # 所以 xiucat 一定有一个代理服务器来转发请求

    # 尝试找到代理端点
    proxy_patterns = [
        "/v2/proxy",
        "/v2/api/proxy",
        "/v2/chaoxing",
        "/v2/cx",
        "/api/proxy",
        "/proxy",
    ]
    for pattern in proxy_patterns:
        try:
            r = requests.get(f"https://api-test.xiucat.top{pattern}",
                             headers=auth_headers, verify=False, timeout=10)
            if r.status_code != 404 or "Cannot GET" not in r.text:
                print(f"  ★ [{pattern}] Status: {r.status_code}, Body: {r.text[:200]}")
            else:
                print(f"  [{pattern}] 404")
        except Exception as e:
            print(f"  [{pattern}] Error: {e}")

    # ===== Step 9: 分析 xiucat JWT token =====
    log_section("Step 9: 分析 xiucat JWT token")

    # 解码JWT (不验证签名)
    try:
        parts = token.split(".")
        if len(parts) == 3:
            # 解码payload
            payload = parts[1]
            # 补齐base64 padding
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding
            decoded = base64.b64decode(payload)
            payload_data = json.loads(decoded)
            print(f"  JWT Payload: {json.dumps(payload_data, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"  JWT解码错误: {e}")

    # ===== Step 10: 尝试 activities 端点的其他参数名 =====
    log_section("Step 10: activities 端点参数名穷举")

    # 也许字段名是中文拼音或其他变体
    param_attempts = [
        {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257", "fid": "1257"},
        {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257", "fid": "1257", "courseName": COURSE2_NAME},
        {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257", "fid": "1257", "uid": ACC2_PUID},
        {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257", "fid": "1257", "puid": ACC2_PUID},
        {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257", "fid": "1257", "nickname": "3141cpy"},
        {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "schoolId": "1257", "fid": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "courseName": COURSE2_NAME, "nickname": "3141cpy"},
    ]

    for i, body in enumerate(param_attempts):
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "学校ID不能为空" not in msg:
                print(f"  ★ 尝试{i}: {r.text[:300]}")
            else:
                print(f"  尝试{i}: 仍然报学校ID不能为空")
        except Exception as e:
            print(f"  尝试{i}: Error: {e}")

    # 尝试 schoolId 作为查询参数
    print("\n  尝试 schoolId 作为查询参数...")
    try:
        r = requests.post(f"https://api-test.xiucat.top/v2/student/sign/activities?schoolId=1257",
                          headers=auth_headers,
                          json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS},
                          verify=False, timeout=10)
        log_result("activities-query-param", r)
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    main()
