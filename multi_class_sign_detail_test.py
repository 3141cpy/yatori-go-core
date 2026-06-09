#!/usr/bin/env python3
"""多学生班级签到详情API测试脚本"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID_OLD = "257485372"
CLASS_ID_OLD = "132821141"
BASE = "https://mobilelearn.chaoxing.com"

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

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

def sep(title, char="=", width=80):
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")

def sub(title, char="-", width=60):
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")

# ============ 主逻辑 ============
def main():
    # ========== Part 1: 登录并查找课程 ==========
    sep("Part 1: 登录学生账号并查找课程 '好好学习，天天向上'")
    
    print("[*] 正在登录学生账号 18436633997 ...")
    s_student, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"[*] 学生 puid: {puid_s}")
    if not puid_s:
        print("[!!!] 学生登录失败，退出")
        sys.exit(1)
    
    print("[*] 正在获取课程列表 ...")
    r = s_student.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=30)
    courses_data = safe_json(r)
    
    # 打印所有课程
    new_course_id = None
    new_class_id = None
    
    if isinstance(courses_data, dict) and "channelList" in courses_data:
        print(f"\n[*] 找到 {len(courses_data['channelList'])} 个课程/班级:")
        for i, ch in enumerate(courses_data["channelList"]):
            content = ch.get("content", {})
            class_name = content.get("name", "未知") if isinstance(content, dict) else "未知"
            class_id = content.get("id", ch.get("key", "")) if isinstance(content, dict) else ""
            student_count = content.get("studentcount", "") if isinstance(content, dict) else ""
            role_type = content.get("roletype", "") if isinstance(content, dict) else ""
            
            # 课程信息嵌套在 content.course.data[0] 中
            course_info = {}
            course_data = content.get("course", {}) if isinstance(content, dict) else {}
            if isinstance(course_data, dict) and "data" in course_data:
                data_list = course_data["data"]
                if isinstance(data_list, list) and len(data_list) > 0:
                    course_info = data_list[0]
            
            course_name = course_info.get("name", "未知")
            course_id = course_info.get("id", "")
            teacher_name = course_info.get("teacherfactor", "")
            
            print(f"  [{i}] 班级名: {class_name}, 课程名: {course_name}")
            print(f"      courseId={course_id}, classId={class_id}, roletype={role_type}, 学生数={student_count}, 教师={teacher_name}")
            
            if "好好学习" in course_name and "天天向上" in course_name:
                new_course_id = str(course_id)
                new_class_id = str(class_id)
                print(f"      >>> 匹配目标课程！")
    else:
        print(f"[!] 课程列表返回格式异常: {json.dumps(courses_data, ensure_ascii=False)[:500]}")
    
    # 如果没找到，尝试遍历content嵌套
    if not new_course_id:
        print("\n[*] 在channelList中未找到，尝试遍历content嵌套 ...")
        if isinstance(courses_data, dict) and "channelList" in courses_data:
            for ch in courses_data["channelList"]:
                content = ch.get("content", {})
                if not isinstance(content, dict):
                    continue
                course_data = content.get("course", {})
                if isinstance(course_data, dict) and "data" in course_data:
                    for item in course_data["data"]:
                        name = item.get("name", "")
                        if "好好学习" in name:
                            print(f"  在content.course.data中找到: {json.dumps(item, ensure_ascii=False)[:300]}")
                            new_course_id = str(item.get("id", ""))
                            new_class_id = str(content.get("id", ch.get("key", "")))
                            break
    
    if not new_course_id:
        print("[!!!] 未找到课程 '好好学习，天天向上'，退出")
        sys.exit(1)
    
    print(f"\n[✓] 目标课程: courseId={new_course_id}, classId={new_class_id}")
    
    # ========== Part 2: 获取签到活动 ==========
    sep("Part 2: 获取新课程的签到活动")
    
    act_url = f"{BASE}/ppt/activeAPI/taskactivelist?courseId={new_course_id}&classId={new_class_id}&uid={puid_s}"
    r = s_student.get(act_url, headers=ajax_hdr, timeout=30)
    act_data = safe_json(r)
    
    sign_activities_new = []
    all_activities_new = []
    
    if isinstance(act_data, dict) and "activeList" in act_data:
        for a in act_data["activeList"]:
            aid = a.get("id", a.get("activeId", ""))
            atype = a.get("activeType", a.get("type", ""))
            aname = a.get("name", a.get("title", ""))
            astatus = a.get("status", a.get("state", ""))
            all_activities_new.append({"id": aid, "type": atype, "name": aname, "status": astatus})
            print(f"  活动: id={aid}, type={atype}, name={aname}, status={astatus}")
            if str(atype) == "2":
                sign_activities_new.append(a)
    else:
        print(f"[!] 活动列表返回异常: {json.dumps(act_data, ensure_ascii=False)[:500]}")
    
    if not sign_activities_new:
        print("[!] 新课程没有签到活动，尝试获取旧课程签到活动 ...")
    
    # 也获取旧课程的签到活动
    act_url_old = f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID_OLD}&classId={CLASS_ID_OLD}&uid={puid_s}"
    r_old = s_student.get(act_url_old, headers=ajax_hdr, timeout=30)
    act_data_old = safe_json(r_old)
    
    sign_activities_old = []
    if isinstance(act_data_old, dict) and "activeList" in act_data_old:
        for a in act_data_old["activeList"]:
            if str(a.get("activeType", a.get("type", ""))) == "2":
                sign_activities_old.append(a)
    
    print(f"\n[*] 新课程签到活动数: {len(sign_activities_new)}")
    print(f"[*] 旧课程签到活动数: {len(sign_activities_old)}")
    
    # ========== Part 3 & 4: 测试所有签到详情API ==========
    sep("Part 3 & 4: 测试所有签到详情API（新课程 vs 旧课程对比）")
    
    # 选择要测试的活动
    test_acts_new = sign_activities_new[:3] if sign_activities_new else []
    test_acts_old = sign_activities_old[:3] if sign_activities_old else []
    
    if not test_acts_new and not test_acts_old:
        print("[!!!] 没有可测试的签到活动，退出")
        sys.exit(1)
    
    # 对每个API进行对比测试
    def test_api(api_name, path, method="GET", extra_params=None):
        """测试一个API，在新旧课程中对比"""
        sub(f"API: {api_name} ({method})")
        
        results = {}
        
        for label, acts, cid, clid in [
            ("新课程(多学生)", test_acts_new, new_course_id, new_class_id),
            ("旧课程(单学生)", test_acts_old, COURSE_ID_OLD, CLASS_ID_OLD)
        ]:
            if not acts:
                print(f"  [{label}] 无签到活动，跳过")
                continue
            
            act = acts[0]
            aid = act.get("id", act.get("activeId", ""))
            
            params = f"activeId={aid}&classId={clid}&courseId={cid}&uid={puid_s}"
            if extra_params:
                params += f"&{extra_params}"
            
            url = f"{BASE}{path}?{params}"
            
            try:
                if method == "GET":
                    r = s_student.get(url, headers=ajax_hdr, timeout=30)
                else:
                    r = s_student.post(url, data=params, headers=ajax_hdr, timeout=30)
                
                result = safe_json(r)
                # 也保存原始文本
                raw_text = r.text[:2000] if r.text else ""
                results[label] = {"json": result, "status_code": r.status_code, "raw": raw_text}
                
                print(f"  [{label}] HTTP {r.status_code}")
                print(f"  [{label}] JSON: {json.dumps(result, ensure_ascii=False)[:500]}")
                if not isinstance(result, dict) or "_raw_text" in result:
                    print(f"  [{label}] Raw: {raw_text[:500]}")
            except Exception as e:
                results[label] = {"error": str(e)}
                print(f"  [{label}] 请求异常: {e}")
        
        # 对比
        if len(results) == 2:
            labels = list(results.keys())
            r1, r2 = results[labels[0]], results[labels[1]]
            if r1.get("json") != r2.get("json"):
                print(f"\n  !!!DIFFERENCE!!! 两个课程的响应不同!")
                print(f"    新课程: {json.dumps(r1.get('json', {}), ensure_ascii=False)[:300]}")
                print(f"    旧课程: {json.dumps(r2.get('json', {}), ensure_ascii=False)[:300]}")
            else:
                print(f"\n  两个课程的响应相同")
        
        # 检查敏感数据
        for label, res in results.items():
            raw = res.get("raw", "")
            json_data = res.get("json", {})
            json_str = json.dumps(json_data, ensure_ascii=False)
            
            # 检查是否包含其他学生数据
            has_other = False
            if isinstance(json_data, dict):
                # 检查是否有学生列表
                for key in ["data", "result", "list", "signList", "refreshList", "studentList"]:
                    val = json_data.get(key)
                    if isinstance(val, list) and len(val) > 1:
                        has_other = True
                        break
                    if isinstance(val, dict):
                        for k2 in ["signList", "refreshList", "studentList", "list"]:
                            if isinstance(val.get(k2), list) and len(val.get(k2)) > 1:
                                has_other = True
                                break
            
            if has_other:
                print(f"\n  !!!SENSITIVE!!! [{label}] 响应可能包含多个学生数据!")
                print(f"  !!!CRITICAL!!! 学生可能看到其他学生的签到信息!")
                print(f"  完整响应: {json.dumps(json_data, ensure_ascii=False)[:1000]}")
        
        return results
    
    # 3.1 refeashSignList4Json2 (GET)
    r1 = test_api("refeashSignList4Json2", "/pptSign/refeashSignList4Json2", "GET")
    
    # 3.2 refeashSignList4Json2 (POST)
    r2 = test_api("refeashSignList4Json2 (POST)", "/pptSign/refeashSignList4Json2", "POST")
    
    # 3.3 autoRefeashSignList4Json2
    r3 = test_api("autoRefeashSignList4Json2", "/pptSign/autoRefeashSignList4Json2", "GET")
    
    # 3.4 refeashSignList4Json
    r4 = test_api("refeashSignList4Json", "/pptSign/refeashSignList4Json", "GET")
    
    # 3.5 signedResult
    r5 = test_api("signedResult", "/pptSign/signedResult", "GET")
    
    # 3.6 signDetail (没有classId和courseId)
    sub("API: signDetail (GET)")
    sign_detail_results = {}
    for label, acts, cid, clid in [
        ("新课程(多学生)", test_acts_new, new_course_id, new_class_id),
        ("旧课程(单学生)", test_acts_old, COURSE_ID_OLD, CLASS_ID_OLD)
    ]:
        if not acts:
            continue
        aid = acts[0].get("id", acts[0].get("activeId", ""))
        url = f"{BASE}/pptSign/signDetail?activeId={aid}&uid={puid_s}"
        try:
            r = s_student.get(url, headers=ajax_hdr, timeout=30)
            result = safe_json(r)
            sign_detail_results[label] = {"json": result, "status_code": r.status_code, "raw": r.text[:2000]}
            print(f"  [{label}] HTTP {r.status_code}")
            print(f"  [{label}] JSON: {json.dumps(result, ensure_ascii=False)[:500]}")
        except Exception as e:
            sign_detail_results[label] = {"error": str(e)}
            print(f"  [{label}] 请求异常: {e}")
    
    if len(sign_detail_results) == 2:
        labels = list(sign_detail_results.keys())
        j1 = sign_detail_results[labels[0]].get("json")
        j2 = sign_detail_results[labels[1]].get("json")
        if j1 != j2:
            print(f"\n  !!!DIFFERENCE!!! signDetail 两个课程的响应不同!")
    
    # 3.7 v2/apis/sign/signIn
    sub("API: v2/apis/sign/signIn (GET)")
    v2_sign_results = {}
    for label, acts, cid, clid in [
        ("新课程(多学生)", test_acts_new, new_course_id, new_class_id),
        ("旧课程(单学生)", test_acts_old, COURSE_ID_OLD, CLASS_ID_OLD)
    ]:
        if not acts:
            continue
        aid = acts[0].get("id", acts[0].get("activeId", ""))
        url = f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}"
        try:
            r = s_student.get(url, headers=ajax_hdr, timeout=30)
            result = safe_json(r)
            v2_sign_results[label] = {"json": result, "status_code": r.status_code, "raw": r.text[:2000]}
            print(f"  [{label}] HTTP {r.status_code}")
            print(f"  [{label}] JSON: {json.dumps(result, ensure_ascii=False)[:800]}")
            
            # 深入检查是否包含其他学生数据
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    for key, val in data.items():
                        if isinstance(val, list) and len(val) > 1:
                            print(f"  !!!SENSITIVE!!! [{label}] data.{key} 包含 {len(val)} 条记录!")
                            for idx, item in enumerate(val[:5]):
                                print(f"    [{idx}]: {json.dumps(item, ensure_ascii=False)[:300]}")
                            if len(val) > 5:
                                print(f"    ... 还有 {len(val)-5} 条")
                elif isinstance(data, list) and len(data) > 1:
                    print(f"  !!!SENSITIVE!!! [{label}] data 是列表，包含 {len(data)} 条记录!")
        except Exception as e:
            v2_sign_results[label] = {"error": str(e)}
            print(f"  [{label}] 请求异常: {e}")
    
    # 3.8 preSign 页面
    sub("API: preSign 页面 (GET)")
    presign_results = {}
    for label, acts, cid, clid in [
        ("新课程(多学生)", test_acts_new, new_course_id, new_class_id),
        ("旧课程(单学生)", test_acts_old, COURSE_ID_OLD, CLASS_ID_OLD)
    ]:
        if not acts:
            continue
        aid = acts[0].get("id", acts[0].get("activeId", ""))
        url = f"{BASE}/newsign/preSign?activeId={aid}&courseId={cid}&classId={clid}"
        try:
            r = s_student.get(url, timeout=30)
            text = r.text
            
            # 检查 isTeacherViewOpen
            teacher_view = "未找到"
            if "isTeacherViewOpen" in text:
                # 尝试提取值
                import re
                m = re.search(r'isTeacherViewOpen["\s:=]+(["\w]+)', text)
                if m:
                    teacher_view = m.group(1)
                else:
                    # 找附近文本
                    idx = text.index("isTeacherViewOpen")
                    teacher_view = text[idx:idx+80]
            
            presign_results[label] = {"status_code": r.status_code, "teacher_view": teacher_view, "raw_len": len(text)}
            print(f"  [{label}] HTTP {r.status_code}, 页面长度: {len(text)}")
            print(f"  [{label}] isTeacherViewOpen: {teacher_view}")
            
            # 检查页面中是否包含其他学生信息
            if "studentList" in text or "signList" in text or "refreshList" in text:
                print(f"  !!!SENSITIVE!!! [{label}] preSign页面可能包含学生列表数据!")
                # 尝试提取
                for keyword in ["studentList", "signList", "refreshList"]:
                    if keyword in text:
                        idx = text.index(keyword)
                        snippet = text[max(0,idx-20):idx+200]
                        print(f"  关键词 '{keyword}' 附近: ...{snippet[:300]}...")
        except Exception as e:
            presign_results[label] = {"error": str(e)}
            print(f"  [{label}] 请求异常: {e}")
    
    # 3.9 shuaxin
    r9 = test_api("shuaxin", "/pptSign/shuaxin", "GET")
    
    # ========== Part 5: 深入检查是否有其他学生数据 ==========
    sep("Part 5: 深入检查 - 学生是否能看到其他学生签到数据")
    
    found_sensitive = False
    sensitive_data = {}
    
    # 对新课程中每个签到活动，详细检查 refeashSignList4Json2
    for idx, act in enumerate(test_acts_new):
        aid = act.get("id", act.get("activeId", ""))
        sub(f"新课程签到活动 #{idx+1}: activeId={aid}")
        
        # refeashSignList4Json2 详细检查
        url = f"{BASE}/pptSign/refeashSignList4Json2?activeId={aid}&classId={new_class_id}&courseId={new_course_id}&uid={puid_s}"
        try:
            r = s_student.get(url, headers=ajax_hdr, timeout=30)
            result = safe_json(r)
            print(f"  refeashSignList4Json2 完整响应:")
            print(f"  {json.dumps(result, ensure_ascii=False)[:1500]}")
            
            # 深入分析
            if isinstance(result, dict):
                data = result.get("data")
                if data is not None:
                    if isinstance(data, dict):
                        for key, val in data.items():
                            if isinstance(val, list):
                                print(f"  data.{key}: 列表长度={len(val)}")
                                for i, item in enumerate(val[:5]):
                                    print(f"    [{i}]: {json.dumps(item, ensure_ascii=False)[:300]}")
                                if len(val) > 1:
                                    found_sensitive = True
                                    sensitive_data[f"refeashSignList4Json2_act{aid}"] = result
                                    print(f"  !!!SENSITIVE!!! 发现多个条目!")
                            elif isinstance(val, str) and val.lower() not in ("false", "true", ""):
                                print(f"  data.{key} = {val}")
                    elif isinstance(data, list):
                        print(f"  data: 列表长度={len(data)}")
                        for i, item in enumerate(data[:5]):
                            print(f"    [{i}]: {json.dumps(item, ensure_ascii=False)[:300]}")
                        if len(data) > 1:
                            found_sensitive = True
                            sensitive_data[f"refeashSignList4Json2_act{aid}"] = result
                            print(f"  !!!SENSITIVE!!! 发现多个条目!")
                    elif isinstance(data, bool):
                        print(f"  data = {data} (布尔值)")
                    else:
                        print(f"  data = {data}")
        except Exception as e:
            print(f"  请求异常: {e}")
        
        # v2 signIn 详细检查
        url = f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}"
        try:
            r = s_student.get(url, headers=ajax_hdr, timeout=30)
            result = safe_json(r)
            print(f"\n  v2/signIn 完整响应:")
            print(f"  {json.dumps(result, ensure_ascii=False)[:1500]}")
            
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    for key, val in data.items():
                        if isinstance(val, list):
                            print(f"  data.{key}: 列表长度={len(val)}")
                            for i, item in enumerate(val[:5]):
                                print(f"    [{i}]: {json.dumps(item, ensure_ascii=False)[:300]}")
                            if len(val) > 1:
                                found_sensitive = True
                                sensitive_data[f"v2signIn_act{aid}"] = result
                                print(f"  !!!SENSITIVE!!! 发现多个学生条目!")
                elif isinstance(data, list) and len(data) > 1:
                    found_sensitive = True
                    sensitive_data[f"v2signIn_act{aid}"] = result
                    print(f"  !!!SENSITIVE!!! data是列表，包含 {len(data)} 条!")
        except Exception as e:
            print(f"  v2/signIn 请求异常: {e}")
        
        # signDetail 详细检查
        url = f"{BASE}/pptSign/signDetail?activeId={aid}&uid={puid_s}"
        try:
            r = s_student.get(url, headers=ajax_hdr, timeout=30)
            result = safe_json(r)
            print(f"\n  signDetail 完整响应:")
            print(f"  {json.dumps(result, ensure_ascii=False)[:1500]}")
        except Exception as e:
            print(f"  signDetail 请求异常: {e}")
    
    # ========== Part 6: 教师会话对比 ==========
    sep("Part 6: 教师会话对比测试")
    
    print("[*] 正在登录教师账号 19712720708 ...")
    s_teacher, puid_t = login("19712720708", "3.1415926Cpy")
    print(f"[*] 教师 puid: {puid_t}")
    
    if puid_t and test_acts_new:
        for idx, act in enumerate(test_acts_new[:2]):
            aid = act.get("id", act.get("activeId", ""))
            sub(f"教师视角 - 签到活动 #{idx+1}: activeId={aid}")
            
            # 教师 refeashSignList4Json2
            url = f"{BASE}/pptSign/refeashSignList4Json2?activeId={aid}&classId={new_class_id}&courseId={new_course_id}&uid={puid_t}"
            try:
                r = s_teacher.get(url, headers=ajax_hdr, timeout=30)
                result_t = safe_json(r)
                print(f"  [教师] refeashSignList4Json2:")
                print(f"  {json.dumps(result_t, ensure_ascii=False)[:1500]}")
                
                # 分析教师响应中的学生数据
                if isinstance(result_t, dict) and "data" in result_t:
                    data = result_t["data"]
                    if isinstance(data, dict):
                        for key, val in data.items():
                            if isinstance(val, list):
                                print(f"  data.{key}: 列表长度={len(val)}")
                                for i, item in enumerate(val[:10]):
                                    print(f"    [{i}]: {json.dumps(item, ensure_ascii=False)[:400]}")
                    elif isinstance(data, list):
                        print(f"  data: 列表长度={len(data)}")
                        for i, item in enumerate(data[:10]):
                            print(f"    [{i}]: {json.dumps(item, ensure_ascii=False)[:400]}")
            except Exception as e:
                print(f"  [教师] 请求异常: {e}")
            
            # 学生 vs 教师对比
            url_s = f"{BASE}/pptSign/refeashSignList4Json2?activeId={aid}&classId={new_class_id}&courseId={new_course_id}&uid={puid_s}"
            try:
                r_s = s_student.get(url_s, headers=ajax_hdr, timeout=30)
                result_s = safe_json(r_s)
                
                if result_s != result_t:
                    print(f"\n  !!!DIFFERENCE!!! 学生和教师的 refeashSignList4Json2 响应不同!")
                    print(f"  [学生]: {json.dumps(result_s, ensure_ascii=False)[:500]}")
                    print(f"  [教师]: {json.dumps(result_t, ensure_ascii=False)[:500]}")
                else:
                    print(f"\n  学生和教师的 refeashSignList4Json2 响应相同")
            except Exception as e:
                print(f"  学生对比请求异常: {e}")
            
            # 教师 v2/signIn
            url = f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_t}"
            try:
                r = s_teacher.get(url, headers=ajax_hdr, timeout=30)
                result_t2 = safe_json(r)
                print(f"\n  [教师] v2/signIn:")
                print(f"  {json.dumps(result_t2, ensure_ascii=False)[:1500]}")
                
                if isinstance(result_t2, dict) and "data" in result_t2:
                    data = result_t2["data"]
                    if isinstance(data, dict):
                        for key, val in data.items():
                            if isinstance(val, list):
                                print(f"  data.{key}: 列表长度={len(val)}")
                                for i, item in enumerate(val[:10]):
                                    print(f"    [{i}]: {json.dumps(item, ensure_ascii=False)[:400]}")
            except Exception as e:
                print(f"  [教师] v2/signIn 请求异常: {e}")
    else:
        if not puid_t:
            print("[!] 教师登录失败")
        if not test_acts_new:
            print("[!] 新课程无签到活动")
    
    # ========== 最终结论 ==========
    sep("最终结论")
    
    print(f"\n新课程: courseId={new_course_id}, classId={new_class_id}")
    print(f"旧课程: courseId={COURSE_ID_OLD}, classId={CLASS_ID_OLD}")
    print(f"新课程签到活动数: {len(sign_activities_new)}")
    print(f"旧课程签到活动数: {len(sign_activities_old)}")
    
    if found_sensitive:
        print(f"\n!!!CRITICAL!!! 学生在新课程(多学生班级)中可以看到其他学生的签到数据!")
        print(f"发现敏感数据的API: {list(sensitive_data.keys())}")
        print(f"\n完整敏感数据:")
        for key, val in sensitive_data.items():
            print(f"  {key}: {json.dumps(val, ensure_ascii=False)[:1000]}")
    else:
        print(f"\n学生无法通过测试的API看到其他学生的签到数据。")
        print(f"班级学生数量不影响API返回结果 - 学生只能看到自己的数据。")
    
    # 汇总所有差异
    print(f"\n--- 差异汇总 ---")
    print(f"如果上方有 !!!DIFFERENCE!!! 标记，说明同一API在不同课程中返回不同结果")
    print(f"如果上方有 !!!SENSITIVE!!! 标记，说明响应中包含多个学生数据")
    print(f"如果上方有 !!!CRITICAL!!! 标记，说明学生可以看到其他学生的签到详情")


if __name__ == "__main__":
    main()
