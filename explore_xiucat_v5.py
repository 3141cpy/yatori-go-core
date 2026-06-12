#!/usr/bin/env python3
"""
xiucat.top V2 API 终极参数测试
关键发现:
- activities 需要 fid (不是 schoolId)
- 实际前端在 https://cx.xiucat.top/
- 所有签到类型都需要 "是否验证" 数字参数
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

    # ===== Step 1: 分析 cx.xiucat.top 前端 =====
    log_section("Step 1: 分析 cx.xiucat.top 前端")

    print("  [1a] 获取 cx.xiucat.top 主页...")
    try:
        r = requests.get("https://cx.xiucat.top/", verify=False, timeout=20,
                         headers={"User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36"})
        print(f"  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers.get('Content-Type', 'N/A')}")
        print(f"  HTML长度: {len(r.text)}")

        # 搜索JS文件
        js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
        css_files = re.findall(r'href=["\']([^"\']*\.css[^"\']*)["\']', r.text)
        print(f"  JS文件: {js_files}")
        print(f"  CSS文件: {css_files}")

        # 搜索API引用
        api_refs = re.findall(r'(api-test\.xiucat\.top[^"\'>\s]*|/v2/[a-zA-Z0-9/_-]+)', r.text)
        print(f"  API引用: {list(set(api_refs))}")

        # 打印部分HTML
        print(f"\n  HTML前2000字符:\n{r.text[:2000]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 1b. 下载JS文件
    print("\n  [1b] 下载并分析JS文件...")
    for js in js_files[:10]:
        if js.startswith("/"):
            js_url = f"https://cx.xiucat.top{js}"
        elif js.startswith("http"):
            js_url = js
        else:
            js_url = f"https://cx.xiucat.top/{js}"
        try:
            r = requests.get(js_url, verify=False, timeout=20)
            js_content = r.text

            # 搜索API端点
            api_refs = re.findall(r'(/v2/[a-zA-Z0-9/_-]+)', js_content)
            sign_refs = [a for a in api_refs if 'sign' in a.lower() or 'auth' in a.lower() or 'course' in a.lower()]

            # 搜索"是否验证"相关
            verify_refs = re.findall(r'(["\'])([a-zA-Z_]*[Vv]erif[a-zA-Z_]*|["\'][a-zA-Z_]*valid[a-zA-Z_]*|["\'][a-zA-Z_]*check[a-zA-Z_]*|["\'][a-zA-Z_]*auth[a-zA-Z_]*)\1', js_content)
            chinese_refs = re.findall(r'验证|是否|补签|makeup|patch', js_content)

            # 搜索参数定义
            param_defs = re.findall(r'(\w+)\s*:\s*(?:req|request|body|params|query|ctx)\.\w+', js_content)

            if sign_refs or chinese_refs or len(js_content) < 50000:
                print(f"\n  JS: {js} (长度: {len(js_content)})")
                if sign_refs:
                    print(f"  签到API: {list(set(sign_refs))}")
                if chinese_refs:
                    print(f"  中文关键词: {list(set(chinese_refs))}")
                if verify_refs:
                    print(f"  验证相关: {verify_refs[:10]}")
                if param_defs:
                    print(f"  参数定义: {list(set(param_defs))[:20]}")

                # 搜索所有可能的参数名
                all_params = re.findall(r'["\'](\w+)["\']\s*:', js_content)
                relevant_params = [p for p in set(all_params) if any(kw in p.lower() for kw in
                    ['verify', 'valid', 'check', 'auth', 'sign', 'makeup', 'school', 'fid', 'enc', 'location', 'course', 'active', 'status'])]
                if relevant_params:
                    print(f"  相关参数名: {sorted(relevant_params)}")

        except Exception as e:
            print(f"  JS {js}: Error: {e}")

    # ===== Step 2: 穷举 "是否验证" 字段名 =====
    log_section("Step 2: 穷举 '是否验证' 字段名")

    base_body = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID,
        "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME,
        "nickname": "3141cpy",
        "latitude": "-1",
        "longitude": "-1",
        "address": "",
        "fid": "1257",
        "locationText": "",
    }

    # 更多可能的字段名
    verify_field_names = [
        # 中文拼音
        "shifouYanzheng", "shiFouYanzheng", "sfYz", "isYz",
        # 英文变体
        "isVerified", "isVerified", "verified", "isValidated", "validated",
        "isAuth", "isAuthed", "authed", "authenticated",
        "needAuth", "needAuth", "requireAuth", "requireVerify",
        "checkStatus", "verifyStatus", "authStatus",
        "isNeedVerify", "isNeedAuth", "isNeedCheck",
        "hasVerify", "hasAuth", "hasCheck",
        "verifyType", "authType", "checkType",
        "verifyFlag", "authFlag", "checkFlag",
        "isPass", "isPassed", "passed",
        "isConfirm", "confirmed", "isConfirmed",
        "validate", "validation", "validator",
        # 数字型
        "verifyNum", "authNum", "checkNum",
        "verifyCode", "authCode",
        # 其他
        "isLogin", "isSigned", "signed",
        "type", "signType", "activeType",
        "mode", "signMode",
        # 常见缩写
        "iv", "nv", "av", "cv",
        "isV", "needV", "hasV",
        # 可能的中文拼音缩写
        "sfYz", "sfYz2", "sfyZ", "sfyz",
        # 其他可能
        "isV2", "v2", "v",
    ]

    found = False
    for field_name in verify_field_names:
        body = dict(base_body)
        body[field_name] = 0
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "是否验证必须是数字" not in msg:
                print(f"  ★★★ {field_name}=0: {r.text[:300]}")
                found = True
            else:
                pass  # 不打印失败的
        except Exception as e:
            pass

    if not found:
        print("  所有尝试的字段名都失败了，尝试其他方法...")

        # 尝试把字段名放在不同位置
        print("\n  尝试嵌套结构...")
        body = dict(base_body)
        body["options"] = {"isVerify": 0}
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            log_result("nested-options", r)
        except Exception as e:
            print(f"  Error: {e}")

    # ===== Step 3: 尝试通过 cx.xiucat.top 前端找到参数 =====
    log_section("Step 3: 通过 cx.xiucat.top 前端找到参数")

    # 获取所有JS资源
    print("  [3a] 获取 cx.xiucat.top 所有资源...")
    try:
        r = requests.get("https://cx.xiucat.top/", verify=False, timeout=20)
        html = r.text

        # 找到所有资源链接
        all_links = re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html)
        print(f"  所有资源: {all_links}")

        # 下载每个JS文件并搜索参数
        for link in all_links:
            if '.js' in link:
                if link.startswith('/'):
                    url = f"https://cx.xiucat.top{link}"
                elif link.startswith('http'):
                    url = link
                else:
                    url = f"https://cx.xiucat.top/{link}"

                try:
                    r2 = requests.get(url, verify=False, timeout=20)
                    js = r2.text

                    # 搜索关键词
                    keywords_found = []
                    for kw in ['是否验证', 'isVerify', 'isAuth', 'needVerify', '补签', 'makeup',
                               'schoolId', 'fid', 'enc', 'locationText', 'nickname', 'courseName',
                               'activeId', 'stuSign', 'updateSign']:
                        if kw in js:
                            keywords_found.append(kw)

                    if keywords_found:
                        print(f"\n  ★ JS: {link}")
                        print(f"  关键词: {keywords_found}")

                        # 搜索关键词上下文
                        for kw in keywords_found:
                            idx = 0
                            while True:
                                idx = js.find(kw, idx)
                                if idx == -1:
                                    break
                                context = js[max(0, idx-80):idx+80]
                                print(f"    '{kw}' 上下文: ...{context}...")
                                idx += len(kw)
                                if idx > len(js) - 80:
                                    break
                except Exception as e:
                    print(f"  {link}: Error: {e}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 4: 尝试不同的 Content-Type =====
    log_section("Step 4: 尝试不同的 Content-Type")

    # 也许参数需要通过 form-data 传递
    print("  [4a] 尝试 application/x-www-form-urlencoded...")
    try:
        form_data = {
            "activeId": "1000155099942",
            "courseId": COURSE2_ID,
            "classId": COURSE2_CLASS,
            "courseName": COURSE2_NAME,
            "nickname": "3141cpy",
            "latitude": "-1",
            "longitude": "-1",
            "address": "",
            "fid": "1257",
            "locationText": "",
            "isVerify": "0",
        }
        r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                          headers={"Authorization": f"Bearer {token}"},
                          data=form_data, verify=False, timeout=20)
        log_result("4a-form-urlencoded", r)
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 5: 尝试直接调用超星API (使用xiucat返回的cookies) =====
    log_section("Step 5: 使用 xiucat cookies 直接调用超星签到API")

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
                name = name.strip()
                value = value.strip().strip('"')
                chaoxing_session.cookies.set(name, value, domain=".chaoxing.com")

    # 5a. 尝试 newsign/preSign 页面 (可能包含特殊参数)
    print("  [5a] 获取 newsign/preSign 页面...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/newsign/preSign",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "activePrimaryId": "1000155099942", "general": "1",
                            "sys": "1", "ls": "1", "appType": "15",
                            "uid": ACC2_PUID, "isTeacherViewOpen": "0"},
                    timeout=20)
        print(f"  Status: {r.status_code}")
        print(f"  HTML长度: {len(r.text)}")

        # 搜索JS中的参数
        js_content = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
        for js in js_content:
            if len(js.strip()) > 10:
                print(f"  内联JS: {js[:500]}")

        # 搜索外部JS
        ext_js = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
        print(f"  外部JS: {ext_js}")

        # 搜索参数
        params_in_html = re.findall(r'(activeId|signId|enc|token|verify|auth|status|isVerify|needVerify)', r.text, re.IGNORECASE)
        print(f"  参数引用: {list(set(params_in_html))}")

    except Exception as e:
        print(f"  Error: {e}")

    # 5b. 尝试获取签到详情
    print("\n  [5b] 获取签到活动详情...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/getSignDetail",
                    params={"activeId": "1000155099942"},
                    timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # 5c. 尝试获取签到结果
    print("\n  [5c] 获取签到结果...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/signResult",
                    params={"activeId": "1000155099942", "uid": ACC2_PUID},
                    timeout=20)
        print(f"  Status: {r.status_code}, Body: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Step 6: 尝试通过 xiucat 的 V1 API =====
    log_section("Step 6: 探索 xiucat V1 API")

    v1_endpoints = [
        ("POST", "/v1/student/auth/login", {"phone": ACC2_PHONE, "password": ACC2_PWD}),
        ("POST", "/v1/auth/login", {"phone": ACC2_PHONE, "password": ACC2_PWD}),
        ("POST", "/v1/sign/courses", {}),
        ("POST", "/v1/sign/activities", {"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "fid": "1257"}),
        ("POST", "/v1/sign/normal", {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
        ("POST", "/v1/sign/makeup", {"activeId": "1000155099942", "courseId": COURSE2_ID, "classId": COURSE2_CLASS}),
        ("GET", "/v1/student/courses", {}),
        ("GET", "/v1/student/activities", {}),
    ]

    for method, ep, body in v1_endpoints:
        try:
            if method == "GET":
                r = requests.get(f"https://api-test.xiucat.top{ep}",
                                 headers=auth_headers, verify=False, timeout=10)
            else:
                r = requests.post(f"https://api-test.xiucat.top{ep}",
                                  headers=auth_headers, json=body, verify=False, timeout=10)
            if "404" not in r.text or "Cannot" not in r.text:
                print(f"  ★ [{method} {ep}] Status: {r.status_code}, Body: {r.text[:200]}")
            else:
                print(f"  [{method} {ep}] 404")
        except Exception as e:
            print(f"  [{method} {ep}] Error: {e}")

    # ===== Step 7: 最终尝试 - 完整的签到流程 =====
    log_section("Step 7: 完整签到流程测试")

    # 7a. 获取课程列表
    print("  [7a] 获取课程列表...")
    r = requests.get("https://api-test.xiucat.top/v2/student/sign/courses",
                     headers=auth_headers, verify=False, timeout=20)
    courses = r.json().get("data", [])

    # 7b. 获取活动列表
    print("  [7b] 获取Course2活动列表...")
    r = requests.post("https://api-test.xiucat.top/v2/student/sign/activities",
                      headers=auth_headers,
                      json={"courseId": COURSE2_ID, "classId": COURSE2_CLASS, "fid": "1257"},
                      verify=False, timeout=20)
    activities = r.json().get("data", [])
    print(f"  活动数: {len(activities)}")
    for act in activities:
        print(f"    id={act.get('aId')}, name={act.get('aName')}, status={act.get('status')}")

    # 7c. 尝试签到 - 添加所有可能的参数
    print("\n  [7c] 尝试签到 - 添加所有可能参数...")

    # 从错误信息 "是否验证必须是数字" 推断:
    # 这可能是一个布尔/数字字段，表示是否需要验证位置/身份
    # 在超星中，签到时有一个参数表示是否需要验证
    # 可能的字段名: isNeedCheck, isNeedVerify, needCheck, needVerify
    # 或者可能是: validate, validated, isValid

    # 让我尝试所有可能的参数名，包括驼峰和下划线变体
    all_possible_fields = []
    prefixes = ["is", "need", "has", "should", "must", "require", "can", "will", "if"]
    suffixes = ["Verify", "Valid", "Check", "Auth", "Validate", "Confirm", "Pass", "Approve",
                "verify", "valid", "check", "auth", "validate", "confirm", "pass", "approve"]
    for p in prefixes:
        for s in suffixes:
            all_possible_fields.append(p + s)

    # 添加更多变体
    all_possible_fields.extend([
        "validated", "verified", "checked", "authenticated", "confirmed",
        "isValid", "isVerified", "isChecked", "isAuthenticated",
        "needValidation", "needVerification", "needCheck", "needAuthentication",
        "validateFlag", "verifyFlag", "checkFlag", "authFlag",
        "validateStatus", "verifyStatus", "checkStatus", "authStatus",
        "isValidate", "isCheck", "isAuth",
        "validateType", "verifyType", "checkType", "authType",
        "signValidate", "signVerify", "signCheck", "signAuth",
        "locationVerify", "locationCheck", "locationAuth",
        "identityVerify", "identityCheck", "identityAuth",
        "faceVerify", "faceCheck", "faceAuth",
        "photoVerify", "photoCheck", "photoAuth",
    ])

    # 批量测试
    print(f"  测试 {len(all_possible_fields)} 个可能的字段名...")
    found_field = None
    for field in all_possible_fields:
        body = {
            "activeId": "1000155099942",
            "courseId": COURSE2_ID,
            "classId": COURSE2_CLASS,
            "courseName": COURSE2_NAME,
            "nickname": "3141cpy",
            "latitude": "-1",
            "longitude": "-1",
            "address": "",
            "fid": "1257",
            "locationText": "",
            field: 0,
        }
        try:
            r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "是否验证必须是数字" not in msg:
                print(f"  ★★★ 找到! {field}=0: {r.text[:300]}")
                found_field = field
                break
        except:
            pass

    if not found_field:
        print("  未找到正确的字段名")
    else:
        # 用找到的字段完成签到
        print(f"\n  使用字段 {found_field} 完成签到测试...")
        for val in [0, 1, 2]:
            body = {
                "activeId": "1000155099942",
                "courseId": COURSE2_ID,
                "classId": COURSE2_CLASS,
                "courseName": COURSE2_NAME,
                "nickname": "3141cpy",
                "latitude": "-1",
                "longitude": "-1",
                "address": "",
                "fid": "1257",
                "locationText": "",
                found_field: val,
            }
            try:
                r = requests.post("https://api-test.xiucat.top/v2/student/sign/normal",
                                  headers=auth_headers, json=body, verify=False, timeout=20)
                print(f"  {found_field}={val}: {r.text[:300]}")
            except Exception as e:
                print(f"  {found_field}={val}: Error: {e}")


if __name__ == "__main__":
    main()
