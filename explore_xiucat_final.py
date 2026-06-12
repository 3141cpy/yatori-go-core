#!/usr/bin/env python3
"""
xiucat.top 最终参数测试 - 修复版
关键发现: mode1 + signType 后报 "Cannot read properties of undefined (reading 'startsWith')"
说明缺少一个字符串参数，服务端对其调用 .startsWith()
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

def log_result(label, resp):
    status = resp.status_code if resp else "NO RESPONSE"
    body = resp.text[:2000] if resp else ""
    print(f"  [{label}] Status: {status}")
    print(f"  [{label}] Body: {body}\n")

def main():
    # 登录
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

    # ===== Part A: /v2/clockin/mode1 - 找到导致 startsWith 错误的参数 =====
    print("\n" + "=" * 70)
    print("  Part A: /v2/clockin/mode1 - 找到 startsWith 参数")
    print("=" * 70)

    # 已知: address, location, signType 通过了验证
    # 服务端对某个未提供的参数调用了 .startsWith()
    # 常见的可能是: enc, signCode, token, url, type, mode 等

    # A1. 尝试添加各种字符串参数
    print("  [A1] mode1 - 逐个添加字符串参数...")
    string_params = [
        "enc", "signCode", "token", "url", "type", "mode",
        "signToken", "accessToken", "authToken", "sessionId",
        "otherJson", "extraJson", "config", "setting",
        "photo", "image", "imageUrl", "photoUrl",
        "gesture", "gestureData", "qrcode", "qrCode",
        "code", "signCode", "checkCode",
        "objectId", "objectIdStr", "id", "aid",
        "cpi", "personId", "openc", "courseIdStr",
        "version", "build", "platform", "device",
        "studentId", "teacherId", "classIdStr",
    ]

    base_body = {
        "activeId": "1000155099942",
        "address": "",
        "location": "34.7466,113.6253",
        "signType": 0,
    }

    for param in string_params:
        body = dict(base_body)
        body[param] = "test"
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            code = result.get("code", 0)
            if "startsWith" not in msg:
                print(f"  ★ {param}='test': code={code}, msg={msg[:200]}")
            else:
                pass  # 仍然报startsWith错误
        except:
            pass

    # A2. 尝试更可能相关的参数
    print("\n  [A2] mode1 - 更可能相关的参数...")
    more_params = [
        "otherJson", "otherJsonStr", "other", "extra",
        "signSetting", "signConfig", "signOption",
        "punchConfig", "punchSetting",
        "groupConfig", "groupSetting",
        "facialCheckInMode", "faceCheckMode",
        "isOnTimeSign", "onTimeSign",
        "punchOnFirstStartTime", "punchOnFirstEndTime",
        "punchOnSecondStartTime", "punchOnSecondEndTime",
        "punchOffFirstStartTime", "punchOffFirstEndTime",
        "punchOffSecondStartTime", "punchOffSecondEndTime",
    ]

    for param in more_params:
        body = dict(base_body)
        body[param] = "test"
        try:
            r = requests.post(f"{BASE_URL}/clockin/mode1",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            code = result.get("code", 0)
            if "startsWith" not in msg:
                print(f"  ★ {param}='test': code={code}, msg={msg[:200]}")
        except:
            pass

    # A3. 从JS代码中搜索可能的参数
    print("\n  [A3] 从JS代码中搜索参数...")
    r_js = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
    js = r_js.text

    # 搜索 mode1 相关的参数构造
    # 找到调用 LN 的位置，然后向上搜索参数构造
    ln_idx = js.find('LN(')
    if ln_idx != -1:
        # 搜索更大范围的上下文
        big_context = js[max(0, ln_idx-5000):ln_idx+1000]
        # 搜索对象属性
        props = re.findall(r'(\w+)\s*:\s*[a-zA-Z_.]+', big_context)
        relevant_props = [p for p in set(props) if len(p) > 3 and not p.startswith('_')]
        print(f"  附近属性: {sorted(relevant_props)[:50]}")

    # 搜索签到页面组件
    # 搜索 "checkin/detail" 页面
    checkin_idx = js.find('checkin/detail')
    if checkin_idx != -1:
        # 获取签到详情页面的代码
        detail_context = js[max(0, checkin_idx-10000):checkin_idx+5000]
        # 搜索参数构造
        sign_params = re.findall(r'(\w+)\s*:\s*(?:e\.value|t\.value|n\.value|formData)', detail_context)
        print(f"  签到页面参数: {list(set(sign_params))[:30]}")

        # 搜索 activeId 附近的代码
        active_idx = detail_context.find('activeId')
        while active_idx != -1:
            ctx = detail_context[max(0, active_idx-300):active_idx+300]
            print(f"\n  activeId 上下文: {ctx[:400]}")
            active_idx = detail_context.find('activeId', active_idx + 1)
            if active_idx > 5000:
                break

    # ===== Part B: /v2/clockin/mode3 完整参数 =====
    print("\n" + "=" * 70)
    print("  Part B: /v2/clockin/mode3 完整参数")
    print("=" * 70)

    # mode3 需要: address, location, seq(1-4), facePunch
    print("  [B1] mode3 - facePunch=''...")
    try:
        r = requests.post(f"{BASE_URL}/clockin/mode3",
                          headers=auth_headers,
                          json={"activeId": "1000155099942", "address": "河南省郑州市",
                                "location": "34.7466,113.6253",
                                "latitude": "34.7466", "longitude": "113.6253",
                                "locationText": "河南省郑州市",
                                "seq": 1, "facePunch": ""},
                          verify=False, timeout=20)
        log_result("B1-mode3", r)
    except Exception as e:
        print(f"  Error: {e}")

    # ===== Part C: /v2/student/sign/normal - 尝试更多"是否验证"字段 =====
    print("=" * 70)
    print("  Part C: /v2/student/sign/normal - 更多'是否验证'字段")
    print("=" * 70)

    # 尝试中文拼音变体
    chinese_verify_fields = [
        "shifouYanzheng", "shiFouYanzheng", "sfYz", "sfyz",
        "isYanzheng", "yanzheng", "isYz",
        "buqian", "isBuqian", "makeupSign",
        "isMakeup", "isBuQian", "buQian",
    ]

    base_sign_body = {
        "activeId": "1000155099942",
        "courseId": COURSE2_ID, "classId": COURSE2_CLASS,
        "courseName": COURSE2_NAME, "nickname": "3141cpy",
        "fid": "1257", "latitude": "-1", "longitude": "-1",
        "address": "", "locationText": "",
        "name": "3141cpy",
    }

    for field in chinese_verify_fields:
        for val in [0, 1]:
            body = dict(base_sign_body)
            body[field] = val
            try:
                r = requests.post(f"{BASE_URL}/student/sign/normal",
                                  headers=auth_headers, json=body, verify=False, timeout=10)
                result = r.json()
                msg = result.get("message", "")
                if "是否验证" not in msg:
                    print(f"  ★★★ {field}={val}: {r.text[:300]}")
                    break
            except:
                pass
        else:
            continue
        break

    # 尝试数字类型参数
    print("\n  尝试数字类型参数...")
    num_fields = [
        "verify", "isVerify", "needVerify", "verified",
        "isValid", "validated", "isAuth", "authenticated",
        "isCheck", "checked", "isConfirm", "confirmed",
        "isPass", "passed", "isApprove", "approved",
        "verifyStatus", "authStatus", "checkStatus",
        "verifyType", "authType", "checkType",
        "verifyFlag", "authFlag", "checkFlag",
        "isV", "needV", "hasV", "ifV",
        "signVerify", "signAuth", "signCheck",
        "locationVerify", "locationAuth", "locationCheck",
        "identityVerify", "identityCheck",
        "faceVerify", "faceCheck",
        "photoVerify", "photoCheck",
        "isNeedVerify", "isNeedAuth", "isNeedCheck",
        "hasVerify", "hasAuth", "hasCheck",
        "validate", "validation", "validator",
        "signValidate", "signVerified",
        "isValidate", "needValidate", "hasValidate",
        "isVerified", "needVerified", "hasVerified",
        "isAuthenticated", "needAuthenticated",
        "isConfirmed", "needConfirmed",
        "isPassed", "needPassed",
        "isApproved", "needApproved",
        "verifyNum", "authNum", "checkNum",
        "verifyCode", "authCode", "checkCode",
        "isLogin", "isSigned", "signed",
        "type", "signType", "activeType",
        "mode", "signMode",
        "iv", "nv", "av", "cv",
        "isV2", "v2", "v",
        "status", "signStatus",
        "result", "signResult",
        "code", "signCode",
        "flag", "signFlag",
        "option", "signOption",
        "setting", "signSetting",
        "config", "signConfig",
        "param", "signParam",
        "data", "signData",
        "info", "signInfo",
        "detail", "signDetail",
        "extra", "signExtra",
        "other", "signOther",
        "note", "signNote",
        "remark", "signRemark",
        "desc", "signDesc",
        "comment", "signComment",
        "reason", "signReason",
        "source", "signSource",
        "from", "signFrom",
        "channel", "signChannel",
        "method", "signMethod",
        "action", "signAction",
        "operation", "signOperation",
        "step", "signStep",
        "phase", "signPhase",
        "stage", "signStage",
        "level", "signLevel",
        "grade", "signGrade",
        "score", "signScore",
        "point", "signPoint",
        "value", "signValue",
        "key", "signKey",
        "token", "signToken",
        "secret", "signSecret",
        "hash", "signHash",
        "salt", "signSalt",
        "nonce", "signNonce",
        "timestamp", "signTimestamp",
        "time", "signTime",
        "date", "signDate",
        "duration", "signDuration",
        "timeout", "signTimeout",
        "limit", "signLimit",
        "max", "signMax",
        "min", "signMin",
        "count", "signCount",
        "total", "signTotal",
        "page", "signPage",
        "size", "signSize",
        "offset", "signOffset",
        "sort", "signSort",
        "order", "signOrder",
        "direction", "signDirection",
        "group", "signGroup",
        "category", "signCategory",
        "tag", "signTag",
        "label", "signLabel",
        "name", "signName",
        "title", "signTitle",
        "content", "signContent",
        "text", "signText",
        "message", "signMessage",
        "description", "signDescription",
        "summary", "signSummary",
        "abstract", "signAbstract",
        "body", "signBody",
        "payload", "signPayload",
        "input", "signInput",
        "output", "signOutput",
        "request", "signRequest",
        "response", "signResponse",
        "callback", "signCallback",
        "webhook", "signWebhook",
        "notify", "signNotify",
        "alert", "signAlert",
        "warning", "signWarning",
        "error", "signError",
        "success", "signSuccess",
        "fail", "signFail",
        "retry", "signRetry",
        "cancel", "signCancel",
        "abort", "signAbort",
        "stop", "signStop",
        "start", "signStart",
        "begin", "signBegin",
        "end", "signEnd",
        "pause", "signPause",
        "resume", "signResume",
        "reset", "signReset",
        "refresh", "signRefresh",
        "reload", "signReload",
        "update", "signUpdate",
        "delete", "signDelete",
        "remove", "signRemove",
        "add", "signAdd",
        "create", "signCreate",
        "insert", "signInsert",
        "modify", "signModify",
        "change", "signChange",
        "replace", "signReplace",
        "swap", "signSwap",
        "move", "signMove",
        "copy", "signCopy",
        "paste", "signPaste",
        "cut", "signCut",
        "select", "signSelect",
        "deselect", "signDeselect",
        "check", "signCheck",
        "uncheck", "signUncheck",
        "toggle", "signToggle",
        "enable", "signEnable",
        "disable", "signDisable",
        "show", "signShow",
        "hide", "signHide",
        "visible", "signVisible",
        "hidden", "signHidden",
        "display", "signDisplay",
        "render", "signRender",
        "draw", "signDraw",
        "paint", "signPaint",
        "fill", "signFill",
        "clear", "signClear",
        "clean", "signClean",
        "wash", "signWash",
        "dry", "signDry",
        "wet", "signWet",
    ]

    print(f"  测试 {len(num_fields)} 个字段名...")
    found = False
    for field in num_fields:
        body = dict(base_sign_body)
        body[field] = 0
        try:
            r = requests.post(f"{BASE_URL}/student/sign/normal",
                              headers=auth_headers, json=body, verify=False, timeout=10)
            result = r.json()
            msg = result.get("message", "")
            if "是否验证" not in msg:
                print(f"  ★★★ {field}=0: {r.text[:300]}")
                found = True
                break
        except:
            pass

    if not found:
        print("  所有字段名都未命中")

    # ===== Part D: 使用 xiucat cookies 通过超星代理签到 =====
    print("\n" + "=" * 70)
    print("  Part D: 使用 xiucat cookies 直接调用超星签到API")
    print("=" * 70)

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

    # D1. 获取签到活动详情
    print("  [D1] 获取签到活动详情 (preSign页面)...")
    try:
        r = chaoxing_session.get("https://mobilelearn.chaoxing.com/newsign/preSign",
                    params={"courseId": COURSE2_ID, "classId": COURSE2_CLASS,
                            "activePrimaryId": "1000155099942", "general": "1",
                            "sys": "1", "ls": "1", "appType": "15",
                            "uid": ACC2_PUID, "isTeacherViewOpen": "0"},
                    timeout=20)
        print(f"  Status: {r.status_code}, Length: {len(r.text)}")
        # 搜索关键信息
        if '签到已结束' in r.text:
            print("  页面显示: 签到已结束")
        if 'general' in r.text:
            print("  页面包含 general 参数")
        # 搜索JS中的签到逻辑
        scripts = re.findall(r'src=["\']([^"\']+)["\']', r.text)
        print(f"  外部JS: {scripts}")
    except Exception as e:
        print(f"  Error: {e}")

    # D2. 尝试通过CXJSBridge签到
    print("\n  [D2] 下载CXJSBridge.js...")
    try:
        r = chaoxing_session.get("https://mobilelearn-static.chaoxing.com/mobilelearn/front/mobile/sign/js/CXJSBridge.js",
                                 timeout=20)
        print(f"  CXJSBridge.js 长度: {len(r.text)}")
        # 搜索签到函数
        sign_funcs = re.findall(r'function\s+(\w*[Ss]ign\w*)', r.text)
        print(f"  签到函数: {list(set(sign_funcs))[:10]}")
    except Exception as e:
        print(f"  Error: {e}")

    # D3. 尝试直接签到 (使用不同的参数组合)
    print("\n  [D3] 直接签到测试...")
    sign_attempts = [
        # 尝试带 general=1 参数
        {"activeId": "1000155099942", "clientip": "", "latitude": "-1",
         "longitude": "-1", "appType": "15", "ifTiJiao": "1", "address": "",
         "general": "1"},
        # 尝试带 sys=1 参数
        {"activeId": "1000155099942", "clientip": "", "latitude": "-1",
         "longitude": "-1", "appType": "15", "ifTiJiao": "1", "address": "",
         "sys": "1"},
        # 尝试带 ls=1 参数
        {"activeId": "1000155099942", "clientip": "", "latitude": "-1",
         "longitude": "-1", "appType": "15", "ifTiJiao": "1", "address": "",
         "ls": "1"},
    ]

    for i, params in enumerate(sign_attempts):
        try:
            r = chaoxing_session.get("https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                        params=params, timeout=20)
            print(f"  尝试{i}: {r.text[:200]}")
        except Exception as e:
            print(f"  尝试{i}: Error: {e}")

    # ===== 最终总结 =====
    print("\n" + "=" * 70)
    print("  最终总结")
    print("=" * 70)
    print("""
  ==================== 关键发现 ====================

  1. xiucat V2 API 签到端点:
     - /v2/clockin/mode1: 需要 activeId, address, location, signType
       signType通过后报 "Cannot read properties of undefined (reading 'startsWith')"
       说明还缺少一个字符串参数

     - /v2/clockin/mode3: 需要 activeId, address, location, seq(1-4), facePunch

     - /v2/student/sign/normal: 需要 courseName, nickname, fid, locationText, name
       还需要 "是否验证" 数字参数 (字段名未知)

  2. 超星直接签到:
     - stuSignajax 对已结束活动返回 "签到已结束"
     - 无法通过添加参数绕过

  3. xiucat 的补签机制推测:
     A. xiucat 服务端使用学生Cookie调用超星的未公开API
     B. xiucat 使用教师账号修改签到状态 (需要先加入课程)
     C. xiucat 使用了超星内部的管理API
     D. xiucat 的 /v2/clockin/ 端点可能实现了特殊的签到逻辑
    """)


if __name__ == "__main__":
    main()
