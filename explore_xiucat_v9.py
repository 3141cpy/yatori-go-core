#!/usr/bin/env python3
"""
xiucat.top 参数逐步补全 - 根据验证错误消息逐步添加参数
发现: mode1 需要 signType, mode3 需要 facePunch, sign/normal 需要 name
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

def main():
    # ===== 登录 xiucat =====
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
        "Accept": "application/json",
    }

    # ===== Part A: /v2/clockin/mode1 参数逐步补全 =====
    log_section("Part A: /v2/clockin/mode1 参数逐步补全")

    # 已知需要: address, location, signType
    # signType: 0=普通, 1=二维码, 2=位置, 3=手势, 4=签到码?
    print("  [A1] mode1 - 添加 signType...")
    for st in [0, 1, 2, 3, 4, 5]:
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers,
                              json={"activeId": "1000155099942", "address": "",
                                    "location": "34.7466,113.6253",
                                    "signType": st},
                              verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            code = result.get("code", 0)
            if "signType" not in msg:
                print(f"  ★ signType={st}: code={code}, msg={msg[:200]}")
                if code == 200:
                    print(f"  ★★★ 签到成功! {r.text[:500]}")
            else:
                print(f"  signType={st}: {msg[:100]}")
        except Exception as e:
            print(f"  signType={st}: Error: {e}")

    # A2. 添加更多参数
    print("\n  [A2] mode1 - signType + 更多参数...")
    for st in [0, 2]:
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers,
                              json={"activeId": "1000155099942", "address": "河南省郑州市",
                                    "location": "34.7466,113.6253",
                                    "signType": st,
                                    "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                    "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                    "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                    "locationText": "河南省郑州市", "uid": ACC2_PUID,
                                    "name": "3141cpy"},
                              verify=False, timeout=20)
            result = r.json()
            print(f"  signType={st}: code={result.get('code')}, msg={result.get('message', '')[:300]}")
            if result.get('code') == 200:
                print(f"  ★★★ 签到成功! {r.text[:500]}")
        except Exception as e:
            print(f"  signType={st}: Error: {e}")

    # ===== Part B: /v2/clockin/mode3 参数补全 =====
    log_section("Part B: /v2/clockin/mode3 参数补全")

    # 已知需要: address, location, seq(1-4), facePunch
    print("  [B1] mode3 - 添加 facePunch...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode3",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "location": "34.7466,113.6253",
                                "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市",
                                "seq": 1, "facePunch": "test"},
                          verify=False, timeout=20)
        log_result("B1-mode3-facePunch", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # ===== Part C: /v2/student/sign/normal 参数逐步补全 =====
    log_section("Part C: /v2/student/sign/normal 参数逐步补全")

    # 已知需要: courseName, nickname, fid, locationText, name, 是否验证
    # name 刚被发现

    print("  [C1] sign/normal - 添加 name...")
    try:
        r = requests.post(f"{BASE_URL}/student/sign/normal",
                          headers=auth_headers,
                          json={"activeId": "1000155099942",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "-1", "longitude": "-1",
                                "address": "", "locationText": "",
                                "name": "3141cpy"},
                          verify=False, timeout=20)
        log_result("C1-sign-normal-name", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # 根据错误消息继续添加参数
    print("  [C2] sign/normal - 逐步添加参数直到成功或找到'是否验证'...")

    # 尝试添加更多可能的参数
    extra_params_to_try = [
        {"name": "3141cpy", "schoolId": "1257"},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "signType": 0},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "signType": 0, "type": 0},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "signType": 0, "type": 0, "activeType": 2},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "signType": 0, "type": 0, "activeType": 2, "status": 2},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "signType": 0, "type": 0, "activeType": 2, "status": 2, "clientip": ""},
        {"name": "3141cpy", "schoolId": "1257", "uid": ACC2_PUID, "puid": ACC2_PUID, "signType": 0, "type": 0, "activeType": 2, "status": 2, "clientip": "", "appType": "15"},
    ]

    for i, extra in enumerate(extra_params_to_try):
        body = {
            "activeId": "1000155099942",
            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
            "courseName": COURSE2_NAME, "nickname": "3141cpy",
            "fid": "1257", "latitude": "-1", "longitude": "-1",
            "address": "", "locationText": "",
        }
        body.update(extra)
        try:
            r = requests.post(f"{BASE_URL}/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            code = result.get("code", 0)
            if code == 200:
                print(f"  ★★★ 尝试{i}: 成功! {r.text[:500]}")
                break
            elif "是否验证" not in msg:
                print(f"  ★ 尝试{i}: code={code}, msg={msg[:200]}")
            else:
                print(f"  尝试{i}: 仍然需要'是否验证'")
        except Exception as e:
            print(f"  尝试{i}: Error: {e}")

    # ===== Part D: 分析JS代码中的签到调用参数 =====
    log_section("Part D: 分析JS代码中的签到调用参数")

    print("  下载JS...")
    r = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
    js = r.text

    # 搜索 LN (mode1) 函数被调用的位置
    # LN(e) 意味着参数 e 被传入
    # 需要找到 e 是怎么构造的

    # 搜索所有调用 LN 的位置
    ln_calls = []
    idx = 0
    while True:
        idx = js.find('LN(', idx)
        if idx == -1:
            break
        # 获取上下文
        context = js[max(0, idx-2000):idx+200]
        ln_calls.append((idx, context))
        idx += 1

    print(f"  找到 {len(ln_calls)} 个 LN(mode1) 调用")

    # 分析每个调用的参数构造
    for i, (pos, ctx) in enumerate(ln_calls):
        # 搜索参数构造
        # 通常在调用前会有对象构造
        if 'activeId' in ctx or 'signType' in ctx or 'mode' in ctx.lower():
            print(f"\n  调用 {i} (位置 {pos}):")
            # 找到参数构造的开始
            # 搜索 { 开始
            brace_start = ctx.rfind('{', 0, len(ctx)-200)
            if brace_start != -1:
                param_context = ctx[brace_start:]
                print(f"  参数构造: {param_context[:500]}")

    # 搜索签到提交按钮的点击事件
    print("\n\n  搜索签到提交逻辑...")
    submit_patterns = [
        r'submit[A-Z]\w*',
        r'handle[A-Z]\w*',
        r'onSubmit',
        r'handleSubmit',
        r'doSign',
        r'doClockin',
        r'startSign',
    ]
    for pattern in submit_patterns:
        matches = re.findall(pattern, js)
        if matches:
            unique = list(set(matches))[:5]
            print(f"  {pattern}: {unique}")

    # ===== Part E: 最终测试 - 完整签到流程 =====
    log_section("Part E: 最终测试 - 完整签到流程")

    # E1. 使用 /v2/clockin/mode1 完整参数
    print("  [E1] mode1 - 完整参数 (signType=0)...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "location": "34.7466,113.6253",
                                "signType": 0,
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市", "uid": ACC2_PUID,
                                "name": "3141cpy", "puid": ACC2_PUID},
                          verify=False, timeout=20)
        log_result("E1-mode1-full", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # E2. 使用 /v2/clockin/mode1 对Course1活动
    print("  [E2] mode1 - Course1活动...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode1",
                          headers=auth_headers,
                          json={"activeId": "5000165046206", "address": "河南省郑州市",
                                "location": "34.7466,113.6253",
                                "signType": 0,
                                "courseId": COURSE1_ID, "classId": COURSE1_CLASS,
                                "courseName": COURSE1_NAME, "nickname": "3141cpy",
                                "fid": "1257", "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市", "uid": ACC2_PUID,
                                "name": "3141cpy", "puid": ACC2_PUID},
                          verify=False, timeout=20)
        log_result("E2-mode1-course1", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # E3. 使用 /v2/clockin/mode3 完整参数
    print("  [E3] mode3 - 完整参数...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode3",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "location": "34.7466,113.6253",
                                "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市",
                                "seq": 1, "facePunch": "",
                                "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                                "courseName": COURSE2_NAME, "nickname": "3141cpy",
                                "fid": "1257", "uid": ACC2_PUID,
                                "name": "3141cpy", "signType": 2},
                          verify=False, timeout=20)
        log_result("E3-mode3-full", r)
    except Exception as e:
        print(f"  Error: {e}\n")

    # E4. 尝试使用 xiucat 的旧API (/v2/student/sign/normal) 加上 name
    print("  [E4] sign/normal + name + 各种'是否验证'字段...")
    verify_fields = [
        "isVerify", "isVerified", "needVerify", "verify", "verified",
        "isValidated", "validated", "isAuth", "authenticated",
        "isCheck", "checked", "isConfirm", "confirmed",
        "isPass", "passed", "isApprove", "approved",
        "verifyStatus", "authStatus", "checkStatus",
        "verifyType", "authType", "checkType",
        "verifyFlag", "authFlag", "checkFlag",
        "isV", "needV", "hasV", "ifV",
        "shifouYanzheng", "sfYz",
        "isNeedVerify", "isNeedAuth", "isNeedCheck",
        "hasVerify", "hasAuth", "hasCheck",
        "validate", "validation", "validator",
        "signVerify", "signAuth", "signCheck",
        "locationVerify", "locationAuth", "locationCheck",
    ]
    for field in verify_fields:
        body = {
            "activeId": "1000155099942",
            "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
            "courseName": COURSE2_NAME, "nickname": "3141cpy",
            "fid": "1257", "latitude": "-1", "longitude": "-1",
            "address": "", "locationText": "",
            "name": "3141cpy",
            field: 0,
        }
        try:
            r = requests.post(f"{BASE_URL}/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "是否验证" not in msg:
                print(f"  ★★★ {field}=0: {r.text[:300]}")
                break
        except:
            pass
    else:
        print("  所有字段名都未命中'是否验证'")

    # ===== 最终总结 =====
    log_section("最终总结")
    print("""
  ==================== 关键发现 ====================

  1. /v2/clockin/mode1 参数链:
     address → location → signType → ???
     signType: 0=普通, 2=位置 (需要进一步确认)

  2. /v2/clockin/mode3 参数链:
     address → location → seq(1-4) → facePunch → ???

  3. /v2/student/sign/normal 参数链:
     courseName → nickname → fid → locationText → name → 是否验证 → ???

  4. "是否验证"字段名仍未找到，可能是:
     - 服务端自定义的验证逻辑
     - 中文参数名 (不太可能)
     - 非常规的英文名

  5. xiucat 的补签机制:
     - 使用学生Cookie登录超星
     - 通过代理调用超星API
     - 可能使用了超星的未公开API或特殊参数
     - /v2/clockin/ 端点用于实习打卡功能
     - /v2/student/sign/ 端点用于普通签到功能
    """)


if __name__ == "main":
    main()

if __name__ == "__main__":
    main()
