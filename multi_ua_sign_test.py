#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多 User-Agent 签到状态修改 API 测试脚本
测试超星学习通平台不同 UA 下签到状态修改 API 是否生效
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

WAIT_AFTER_API = 2  # 每次调用 API 后等待秒数

# ============ 工具函数 ============

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()


def schild_sign(model, locale, version, build, imei):
    parts = [
        f"(schild:{SCHILD_SALT})",
        f"(device:{model})",
        f"Language/{locale}",
        f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
        f"(@Kalimdor)_{imei}",
    ]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()


def login_with_ua(phone, pwd, ua):
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh_CN",
    })
    try:
        s.post(
            LOGIN_URL,
            data={
                "fid": "-1",
                "uname": aes_enc(phone),
                "password": aes_enc(pwd),
                "refer": "http%3A%2F%2Fi.mooc.chaoxing.com",
                "t": "true",
                "forbidotherlogin": "0",
                "validate": "",
                "doubleFactorLogin": "0",
                "independentId": "0",
                "independentNameId": "0",
            },
            allow_redirects=False,
            timeout=30,
        )
    except Exception as e:
        print(f"  [WARN] 登录请求失败: {e}")

    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value

    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except Exception:
        pass
    try:
        s.get(
            "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
            timeout=20,
        )
    except Exception:
        pass
    return s, puid


def get_status(d):
    """从 V2 signIn API 返回值中提取 status 字段，data=None 时返回 None"""
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None


def get_update_time(d):
    """从 V2 signIn API 返回值中提取 updatetime 字段"""
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("updatetime")
    return None


def query_sign_status(session, active_id, puid):
    """查询签到状态"""
    url = f"{BASE}/v2/apis/sign/signIn"
    params = {"activeId": active_id, "uid": puid}
    try:
        r = session.get(url, params=params, timeout=20)
        return r.json()
    except Exception as e:
        print(f"  [WARN] 查询签到状态失败: {e}")
        return None


def get_activity_list(session, course_id, class_id, puid):
    """获取课程活动列表 - 使用正确的API路径"""
    url = f"{BASE}/ppt/activeAPI/taskactivelist"
    params = {
        "courseId": course_id,
        "classId": class_id,
        "uid": puid,
    }
    try:
        r = session.get(url, params=params, timeout=20)
        data = r.json()
        return data
    except Exception as e:
        print(f"  [WARN] 获取活动列表失败: {e}")
        return None


def find_test_activity(session, course_id, class_id, puid):
    """找到一个可用于测试的签到活动"""
    data = get_activity_list(session, course_id, class_id, puid)
    if not data or not isinstance(data, dict):
        return None
    items = data.get("activeList", [])
    if items:
        # 优先找签到类型(activeType=2)的活动
        for item in items:
            if str(item.get("activeType", "")) == "2":
                return item
        return items[0]
    return None


def restore_status(teacher_session, active_id, original_status, student_puid):
    """使用教师账号恢复学生签到状态 - 使用V2 API"""
    url = f"{BASE}/pptSign/updateSignStatusByUidsV2"
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": active_id,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://mobilelearn.chaoxing.com/",
        "X-Requested-With": "XMLHttpRequest",
    }
    if original_status is None:
        # 无记录 → 设为缺勤(0)即可删除记录
        data = {"uids": student_puid, "status": "0", "remark": ""}
    else:
        data = {"uids": student_puid, "status": str(original_status), "remark": ""}
    try:
        teacher_session.post(url, params=params, data=data, headers=headers, timeout=20)
    except Exception as e:
        print(f"  [WARN] 教师恢复状态失败: {e}")


# ============ User-Agent 定义 ============

def build_user_agents():
    """构建所有待测试的 User-Agent 列表"""
    imei = str(uuid.uuid4()).replace("-", "")[:15]
    uas = []

    # 1. Mobile App (with schild) - Android
    sign1 = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    ua1 = (
        f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 "
        f"Mobile Safari/537.36 (schild:{sign1}) (device:MI10) Language/zh_CN "
        f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
        f"(@Kalimdor)_{imei}"
    )
    uas.append(("Mobile App (Android 6.7.2, schild)", ua1))

    # 2. Mobile Web (no schild)
    ua2 = (
        "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
    )
    uas.append(("Mobile Web (Android, no schild)", ua2))

    # 3. PC Chrome
    ua3 = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    )
    uas.append(("PC Chrome", ua3))

    # 4. WeChat Embedded
    ua4 = (
        "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/107.0.0.0 "
        "Mobile Safari/537.36 MicroMessenger/8.0.30.2400(0x28001E35) "
        "NetType/WIFI Language/zh_CN"
    )
    uas.append(("WeChat Embedded", ua4))

    # 5. iPad
    ua5 = (
        "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/107.0.0.0 "
        "Mobile/15E148 Safari/604.1"
    )
    uas.append(("iPad", ua5))

    # 6. Old Android App (older version)
    sign6 = schild_sign("MI10", "zh_CN", "6.5.0", "10850_312", imei)
    ua6 = (
        f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 "
        f"Mobile Safari/537.36 (schild:{sign6}) (device:MI10) Language/zh_CN "
        f"com.chaoxing.mobile/ChaoXingStudy_3_6.5.0_android_phone_10850_312 "
        f"(@Kalimdor)_{imei}"
    )
    uas.append(("Old Android App (6.5.0, schild)", ua6))

    # 7. iPhone App
    sign7 = schild_sign("iPhone14,2", "zh_CN", "6.7.2", "10941_314", imei)
    ua7 = (
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        f"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
        f"(schild:{sign7}) (device:iPhone14,2) Language/zh_CN "
        f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
        f"(@Kalimdor)_{imei}"
    )
    uas.append(("iPhone App (schild)", ua7))

    return uas


# ============ API 测试定义 ============

def build_api_tests(active_id, student_puid):
    """构建所有待测试的 API 调用列表"""
    tests = []

    # API 1: /newsign/updateSignStatus
    tests.append({
        "name": "newsign/updateSignStatus",
        "method": "POST",
        "url": f"{BASE}/newsign/updateSignStatus",
        "params": {
            "DB_STRATEGY": "PRIMARY_KEY",
            "STRATEGY_PARA": "activeId",
            "activeId": active_id,
        },
        "data": {
            "uids": student_puid,
            "status": "1",
            "remark": "",
            "activeId": active_id,
            "classId": CLASS_ID,
            "courseId": COURSE_ID,
            "uid": student_puid,
        },
    })

    # API 2: /pptSign/updateSignStatus
    tests.append({
        "name": "pptSign/updateSignStatus",
        "method": "POST",
        "url": f"{BASE}/pptSign/updateSignStatus",
        "params": {},
        "data": {
            "activeId": active_id,
            "classId": CLASS_ID,
            "courseId": COURSE_ID,
            "uid": student_puid,
            "studentId": student_puid,
            "status": "1",
        },
    })

    # API 3: /pptSign/updateSignStatusByUidsV2
    tests.append({
        "name": "pptSign/updateSignStatusByUidsV2",
        "method": "POST",
        "url": f"{BASE}/pptSign/updateSignStatusByUidsV2",
        "params": {
            "DB_STRATEGY": "PRIMARY_KEY",
            "STRATEGY_PARA": "activeId",
            "activeId": active_id,
        },
        "data": {
            "uids": student_puid,
            "status": "1",
            "remark": "",
        },
    })

    # API 4: /pptSign/stuSignajax (with status)
    tests.append({
        "name": "pptSign/stuSignajax (with status=1)",
        "method": "POST",
        "url": f"{BASE}/pptSign/stuSignajax",
        "params": {},
        "data": {
            "activeId": active_id,
            "uid": student_puid,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0",
            "status": "1",
        },
    })

    # API 5: /pptSign/stuSignajax (without status)
    tests.append({
        "name": "pptSign/stuSignajax (no status)",
        "method": "POST",
        "url": f"{BASE}/pptSign/stuSignajax",
        "params": {},
        "data": {
            "activeId": active_id,
            "uid": student_puid,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0",
        },
    })

    return tests


def call_api(session, api_test):
    """调用单个 API，返回响应文本"""
    try:
        r = session.post(
            api_test["url"],
            params=api_test.get("params", {}),
            data=api_test.get("data", {}),
            timeout=20,
        )
        return r.text
    except Exception as e:
        return f"ERROR: {e}"


def generate_curl_command(api_test, session_headers, student_puid):
    """根据 API 测试定义生成 curl 命令"""
    url = api_test["url"]
    params = api_test.get("params", {})
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"

    data_parts = []
    for k, v in api_test.get("data", {}).items():
        data_parts.append(f"-d '{k}={v}'")

    cookie_str = "; ".join(f"{k}={v}" for k, v in session_headers.get("Cookie", "").split("; ") if k and v) if "Cookie" in session_headers else ""

    ua = session_headers.get("User-Agent", "")
    cmd = f"curl -X POST '{url}'"
    cmd += f" \\\n  -H 'User-Agent: {ua}'"
    cmd += f" \\\n  -H 'Content-Type: application/x-www-form-urlencoded'"
    if cookie_str:
        cmd += f" \\\n  -H 'Cookie: {cookie_str}'"
    for d in data_parts:
        cmd += f" \\\n  {d}"
    return cmd


# ============ 主测试流程 ============

def main():
    print("=" * 80)
    print("  多 User-Agent 签到状态修改 API 测试")
    print("  超星学习通平台 - 签到 API UA 差异检测")
    print("=" * 80)
    print()

    # 1. 教师登录（使用 Mobile App UA）
    print("[1] 教师账号登录...")
    teacher_imei = str(uuid.uuid4()).replace("-", "")[:15]
    teacher_sign = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", teacher_imei)
    teacher_ua = (
        f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 "
        f"Mobile Safari/537.36 (schild:{teacher_sign}) (device:MI10) Language/zh_CN "
        f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
        f"(@Kalimdor)_{teacher_imei}"
    )
    teacher_session, teacher_puid = login_with_ua(TEACHER_PHONE, TEACHER_PWD, teacher_ua)
    if not teacher_puid:
        print("  [ERROR] 教师登录失败，无法获取 puid")
        sys.exit(1)
    print(f"  教师登录成功, puid={teacher_puid}")
    print()

    # 2. 获取签到活动
    print("[2] 获取签到活动列表...")
    activity = find_test_activity(teacher_session, COURSE_ID, CLASS_ID, TEACHER_PUID)
    if not activity:
        print("  [ERROR] 未找到可用的签到活动，使用硬编码活动ID...")
        # 使用已知的签到活动ID
        active_id = "5000163891319"
        activity = {"id": active_id, "nameOne": "二维码签到(硬编码)"}
    else:
        active_id = str(activity.get("id", activity.get("activeId", "")))
        if not active_id:
            print("  [ERROR] 活动 ID 为空，退出测试")
            sys.exit(1)
    print(f"  使用活动: id={active_id}, name={activity.get('name', 'N/A')}")
    print()

    # 3. 构建 User-Agent 列表
    user_agents = build_user_agents()
    print(f"[3] 共 {len(user_agents)} 个 User-Agent 待测试")
    print()

    # 4. 测试结果收集
    all_results = []
    changed_results = []  # 记录状态发生改变的结果
    curl_commands = []

    # 5. 逐个 UA 测试
    for ua_idx, (ua_label, ua_string) in enumerate(user_agents, 1):
        print("=" * 70)
        print(f"  [{ua_idx}/{len(user_agents)}] 测试 UA: {ua_label}")
        print(f"  UA: {ua_string[:80]}...")
        print("=" * 70)

        # 学生使用当前 UA 登录
        print(f"  -> 学生登录 (UA: {ua_label})...")
        student_session, student_puid = login_with_ua(STUDENT_PHONE, STUDENT_PWD, ua_string)
        if not student_puid:
            print(f"  [ERROR] 学生登录失败 (UA: {ua_label})，跳过此 UA")
            for api_test in build_api_tests(active_id, STUDENT_PUID):
                result = {
                    "ua_label": ua_label,
                    "ua_string": ua_string,
                    "api_name": api_test["name"],
                    "before_status": None,
                    "after_status": None,
                    "api_response": "LOGIN_FAILED",
                    "changed": False,
                }
                all_results.append(result)
            continue
        print(f"  -> 学生登录成功, puid={student_puid}")

        # 查询当前签到状态（原始状态）
        print(f"  -> 查询原始签到状态...")
        original_resp = query_sign_status(student_session, active_id, student_puid)
        original_status = get_status(original_resp)
        original_update_time = get_update_time(original_resp)
        print(f"  -> 原始状态: status={original_status}, updatetime={original_update_time}")

        # 构建 API 测试列表
        api_tests = build_api_tests(active_id, student_puid)

        for api_idx, api_test in enumerate(api_tests, 1):
            print()
            print(f"  [{ua_idx}.{api_idx}] API: {api_test['name']}")

            # 查询修改前状态
            before_resp = query_sign_status(student_session, active_id, student_puid)
            before_status = get_status(before_resp)
            before_update_time = get_update_time(before_resp)
            print(f"       修改前: status={before_status}, updatetime={before_update_time}")

            # 调用 API
            print(f"       调用 API: POST {api_test['url']}")
            api_response = call_api(student_session, api_test)
            print(f"       API 响应: {api_response[:200]}")

            # 等待
            time.sleep(WAIT_AFTER_API)

            # 查询修改后状态
            after_resp = query_sign_status(student_session, active_id, student_puid)
            after_status = get_status(after_resp)
            after_update_time = get_update_time(after_resp)
            print(f"       修改后: status={after_status}, updatetime={after_update_time}")

            # 判断状态是否改变
            changed = (before_status != after_status)
            if changed:
                print(f"       *** CHANGED *** 状态从 {before_status} 变为 {after_status}")
                changed_results.append({
                    "ua_label": ua_label,
                    "ua_string": ua_string,
                    "api_name": api_test["name"],
                    "before_status": before_status,
                    "after_status": after_status,
                    "api_response": api_response,
                })
                # 生成 curl 命令
                session_headers = dict(student_session.headers)
                cookies = "; ".join(f"{c.name}={c.value}" for c in student_session.cookies)
                session_headers["Cookie"] = cookies
                curl_cmd = generate_curl_command(api_test, session_headers, student_puid)
                curl_commands.append({
                    "ua_label": ua_label,
                    "api_name": api_test["name"],
                    "curl": curl_cmd,
                })
            else:
                print(f"       状态未改变 (before={before_status}, after={after_status})")

            # 记录结果
            result = {
                "ua_label": ua_label,
                "ua_string": ua_string,
                "api_name": api_test["name"],
                "before_status": before_status,
                "after_status": after_status,
                "before_updatetime": before_update_time,
                "after_updatetime": after_update_time,
                "api_response": api_response[:500] if api_response else None,
                "changed": changed,
            }
            all_results.append(result)

            # 如果状态改变了，恢复后再测下一个 API
            if changed:
                print(f"       -> 使用教师账号恢复原始状态...")
                time.sleep(1)
                restore_status(teacher_session, active_id, original_status, student_puid)
                time.sleep(2)
                # 验证恢复
                verify_resp = query_sign_status(teacher_session, active_id, student_puid)
                verify_status = get_status(verify_resp)
                print(f"       -> 恢复后状态: {verify_status}")

        # 每个 UA 测试完毕后，恢复原始状态
        print()
        print(f"  -> UA [{ua_label}] 测试完毕，恢复原始状态...")
        restore_status(teacher_session, active_id, original_status, student_puid)
        time.sleep(2)
        # 验证恢复
        verify_resp = query_sign_status(teacher_session, active_id, student_puid)
        verify_status = get_status(verify_resp)
        print(f"  -> 恢复后状态: {verify_status}")
        print()

    # ============ 输出结果 ============
    print()
    print("=" * 80)
    print("  测试结果汇总")
    print("=" * 80)
    print()

    # 表格输出
    header = f"{'UA':<35} {'API':<45} {'Before':<10} {'After':<10} {'Changed':<10}"
    print(header)
    print("-" * len(header))

    for r in all_results:
        changed_str = "*** CHANGED ***" if r["changed"] else ""
        before_str = str(r["before_status"]) if r["before_status"] is not None else "None"
        after_str = str(r["after_status"]) if r["after_status"] is not None else "None"
        print(
            f"{r['ua_label']:<35} "
            f"{r['api_name']:<45} "
            f"{before_str:<10} "
            f"{after_str:<10} "
            f"{changed_str:<10}"
        )

    print()

    # 改变的结果
    if changed_results:
        print("=" * 80)
        print("  状态发生改变的测试:")
        print("=" * 80)
        for cr in changed_results:
            print(f"  UA: {cr['ua_label']}")
            print(f"  API: {cr['api_name']}")
            print(f"  状态: {cr['before_status']} -> {cr['after_status']}")
            print(f"  响应: {cr['api_response'][:200]}")
            print()
    else:
        print("  没有发现状态改变的测试。")

    # 保存 JSON 结果
    results_file = "/workspace/multi_ua_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "active_id": active_id,
            "course_id": COURSE_ID,
            "class_id": CLASS_ID,
            "student_puid": STUDENT_PUID,
            "results": all_results,
            "changed_count": len(changed_results),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存到: {results_file}")

    # 保存 curl 命令
    curl_file = "/workspace/verify_curl_commands.txt"
    with open(curl_file, "w", encoding="utf-8") as f:
        f.write("# 签到状态修改成功 API 的 curl 命令\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 活动 ID: {active_id}\n\n")
        if curl_commands:
            for cc in curl_commands:
                f.write(f"# UA: {cc['ua_label']}\n")
                f.write(f"# API: {cc['api_name']}\n")
                f.write(f"{cc['curl']}\n\n")
        else:
            f.write("# 没有成功的修改命令\n")
    print(f"  curl 命令已保存到: {curl_file}")

    print()
    print("测试完成！")


if __name__ == "__main__":
    main()
