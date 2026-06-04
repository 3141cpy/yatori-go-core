#!/usr/bin/env python3
"""QR Session Fix Test - 修复session cookie问题并全面测试超星QR签到端点"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

# ============================================================
# 基础工具函数
# ============================================================

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

def safe_json(r):
    try:
        return r.json()
    except:
        return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

def print_separator(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def print_result(label, resp, show_headers=False):
    print(f"\n  [{label}]")
    print(f"    Status Code: {resp.status_code}")
    print(f"    URL: {resp.url}")
    if show_headers:
        print(f"    Response Headers:")
        for k, v in resp.headers.items():
            if k.lower() in ('set-cookie', 'location', 'content-type', 'server'):
                print(f"      {k}: {v[:100]}")
    try:
        j = resp.json()
        txt = json.dumps(j, ensure_ascii=False, indent=2)
        if len(txt) > 800:
            txt = txt[:800] + "..."
        print(f"    Response JSON: {txt}")
    except:
        txt = resp.text[:500]
        print(f"    Response Text: {txt}")

# ============================================================
# 登录函数 - 带域名cookie修复
# ============================================================

def login(phone, pwd, label=""):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh_CN"
    })

    # 登录
    r = s.post(LOGIN_URL, data={
        "fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
        "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
        "independentId": "0", "independentNameId": "0"
    }, allow_redirects=False, timeout=30)

    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value

    if label:
        print(f"  [{label}] 登录结果: status={r.status_code}, puid={puid}")

    # 关键修复: 访问 mooc1-api 域名以建立该域名的session cookies
    print(f"  正在访问 mooc1-api 域名以建立session...")
    try:
        r1 = s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
        print(f"    mooc1-api backclazzdata: status={r1.status_code}")
    except Exception as e:
        print(f"    mooc1-api backclazzdata: ERROR={e}")

    try:
        r2 = s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
        print(f"    i.chaoxing.com/base: status={r2.status_code}")
    except Exception as e:
        print(f"    i.chaoxing.com/base: ERROR={e}")

    try:
        r3 = s.get("https://mooc1.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
        print(f"    mooc1.chaoxing.com backclazzdata: status={r3.status_code}")
    except Exception as e:
        print(f"    mooc1.chaoxing.com backclazzdata: ERROR={e}")

    # 打印所有cookies
    print(f"\n  登录后所有Cookies:")
    for c in s.cookies:
        val = c.value if len(c.value) <= 30 else c.value[:30] + "..."
        print(f"    {c.name}={val}  domain={c.domain}  path={c.path}")

    return s, puid

# ============================================================
# 获取cpi值
# ============================================================

def get_cpi(s, course_id, class_id):
    """从课程列表API获取cpi值"""
    try:
        r = s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata",
                   params={"view": "json", "m": "0"}, timeout=20)
        j = safe_json(r)
        if isinstance(j, dict) and "channelList" in j:
            for ch in j["channelList"]:
                if isinstance(ch, dict) and "content" in ch:
                    content = ch["content"]
                    if isinstance(content, dict):
                        if str(content.get("courseid")) == course_id or str(content.get("id")) == course_id:
                            cpi = content.get("cpi", "")
                            if cpi:
                                print(f"    找到cpi: {cpi} (courseId={content.get('courseid')})")
                                return str(cpi)
        # 尝试从其他字段获取
        if isinstance(j, dict) and "data" in j:
            data = j["data"]
            if isinstance(data, dict):
                cpi = data.get("cpi", "")
                if cpi:
                    return str(cpi)
        print(f"    未从backclazzdata找到cpi, 响应片段: {json.dumps(j, ensure_ascii=False)[:300]}")
    except Exception as e:
        print(f"    获取cpi失败: {e}")
    return ""

# ============================================================
# 主测试流程
# ============================================================

def main():
    print_separator("Part 1: 验证session cookies在mooc1-api域名上的工作情况")

    # 学生登录
    print("\n--- 学生登录 ---")
    stu_s, stu_puid = login("18436633997", "3.1415926Cpy", "学生")
    print(f"  学生PUID: {stu_puid}")

    # 教师登录
    print("\n--- 教师登录 ---")
    tea_s, tea_puid = login("19712720708", "3.1415926Cpy", "教师")
    print(f"  教师PUID: {tea_puid}")

    # 测试mooc1-api已知可用端点
    print("\n--- 测试mooc1-api已知端点 (学生) ---")
    try:
        r = stu_s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata",
                       params={"view": "json", "m": "0"}, timeout=20)
        j = safe_json(r)
        if isinstance(j, dict) and "result" in j:
            print(f"    结果: result={j.get('result')}, msg={j.get('msg', '')[:100]}")
        elif isinstance(j, dict) and "channelList" in j:
            print(f"    结果: 成功获取channelList, 共{len(j['channelList'])}个频道")
        else:
            txt = json.dumps(j, ensure_ascii=False)[:300]
            print(f"    结果: {txt}")
    except Exception as e:
        print(f"    错误: {e}")

    # ============================================================
    print_separator("Part 2: 测试 /qr/updateqrstatus (带正确session)")

    # 获取学生cpi
    print("\n--- 获取学生cpi ---")
    stu_cpi = get_cpi(stu_s, COURSE_ID, CLASS_ID)
    if not stu_cpi:
        stu_cpi = stu_puid  # fallback
        print(f"    使用puid作为cpi fallback: {stu_cpi}")
    else:
        print(f"    学生cpi: {stu_cpi}")

    # 获取教师cpi
    print("\n--- 获取教师cpi ---")
    tea_cpi = get_cpi(tea_s, COURSE_ID, CLASS_ID)
    if not tea_cpi:
        tea_cpi = tea_puid
        print(f"    使用puid作为cpi fallback: {tea_cpi}")
    else:
        print(f"    教师cpi: {tea_cpi}")

    # 测试 updateqrstatus - 学生 (allow_redirects=True)
    print("\n--- 测试 /qr/updateqrstatus (学生, allow_redirects=True) ---")
    base_params = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "uuid": "test",
        "qrcEnc": "test",
        "cpi": stu_cpi,
        "objectId": "",
        "liveDetectionStatus": "0",
        "signt": "",
        "signk": "",
        "cxtime": "",
        "cxcid": "",
        "knowledgeid": "0",
        "videojobid": "",
        "videoCollectTime": "0",
        "chaptervideoobjectid": ""
    }

    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/qr/updateqrstatus",
                        data=base_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=True, timeout=20)
        print_result("学生 /qr/updateqrstatus (redirect=True)", r, show_headers=True)
    except Exception as e:
        print(f"    错误: {e}")

    # 测试 updateqrstatus - 学生 (allow_redirects=False)
    print("\n--- 测试 /qr/updateqrstatus (学生, allow_redirects=False) ---")
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/qr/updateqrstatus",
                        data=base_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("学生 /qr/updateqrstatus (redirect=False)", r, show_headers=True)
        if r.status_code in (301, 302, 303, 307, 308):
            print(f"    !!! 重定向到: {r.headers.get('Location', 'N/A')}")
    except Exception as e:
        print(f"    错误: {e}")

    # ============================================================
    print_separator("Part 3: 测试 /mooc-ans/qr/updateqrstatus 完整参数")

    # 3.1 基本参数
    print("\n--- 3.1 基本参数 (form-urlencoded) ---")
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=base_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("基本参数", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.2 添加 activeId
    print("\n--- 3.2 添加 activeId ---")
    params_with_active = dict(base_params)
    params_with_active["activeId"] = ""
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=params_with_active,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("添加activeId", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.3 添加 uid
    print("\n--- 3.3 添加 uid ---")
    params_with_uid = dict(base_params)
    params_with_uid["uid"] = stu_puid
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=params_with_uid,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("添加uid", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.4 添加 status
    print("\n--- 3.4 添加 status ---")
    params_with_status = dict(base_params)
    params_with_status["status"] = "1"
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=params_with_status,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("添加status=1", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.5 添加 enc (不同于qrcEnc)
    print("\n--- 3.5 添加 enc ---")
    params_with_enc = dict(base_params)
    params_with_enc["enc"] = "test"
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=params_with_enc,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("添加enc=test", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.6 添加 mid
    print("\n--- 3.6 添加 mid ---")
    params_with_mid = dict(base_params)
    params_with_mid["mid"] = stu_puid
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=params_with_mid,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("添加mid", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.7 添加 type
    print("\n--- 3.7 添加 type ---")
    params_with_type = dict(base_params)
    params_with_type["type"] = "sign"
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=params_with_type,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("添加type=sign", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.8 全部参数组合
    print("\n--- 3.8 全部参数组合 ---")
    all_params = dict(base_params)
    all_params.update({
        "activeId": "",
        "uid": stu_puid,
        "status": "1",
        "enc": "test",
        "mid": stu_puid,
        "type": "sign",
        "version": "2",
        "appType": "1",
    })
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        data=all_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("全部参数组合", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 3.9 JSON Content-Type测试
    print("\n--- 3.9 JSON Content-Type测试 ---")
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                        json=all_params,
                        allow_redirects=False, timeout=20)
        print_result("JSON Content-Type", r)
    except Exception as e:
        print(f"    错误: {e}")

    # ============================================================
    print_separator("Part 4: 获取并使用cpi值")

    # 尝试从课程详情API获取cpi
    print("\n--- 尝试从课程详情API获取cpi ---")
    try:
        r = stu_s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata",
                       params={"view": "json", "m": "0"}, timeout=20)
        j = safe_json(r)
        # 深度搜索cpi
        cpi_found = []
        def find_cpi(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "cpi" and v:
                        cpi_found.append({"path": f"{path}.{k}", "value": v})
                    find_cpi(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    find_cpi(v, f"{path}[{i}]")
        find_cpi(j)
        for cf in cpi_found:
            print(f"    找到cpi: path={cf['path']}, value={cf['value']}")
        if not cpi_found:
            txt = json.dumps(j, ensure_ascii=False)[:500]
            print(f"    未找到cpi, 响应: {txt}")
    except Exception as e:
        print(f"    错误: {e}")

    # 使用cpi重新测试
    if stu_cpi and stu_cpi != stu_puid:
        print(f"\n--- 使用获取到的cpi={stu_cpi}重新测试 ---")
        params_with_real_cpi = dict(base_params)
        params_with_real_cpi["cpi"] = stu_cpi
        params_with_real_cpi["uid"] = stu_puid
        params_with_real_cpi["mid"] = stu_puid
        try:
            r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus",
                            data=params_with_real_cpi,
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                            allow_redirects=False, timeout=20)
            print_result("使用真实cpi", r)
        except Exception as e:
            print(f"    错误: {e}")

    # ============================================================
    print_separator("Part 5: 测试 /mooc-ans/qr/getqrstatus")

    # Go源码中的参数: uuid, enc, clazzid, courseid, cpi, collectionTime, mid, videoObjectId, videoRandomCollectTime, chapterId
    getqr_params = {
        "uuid": "test",
        "enc": "test",
        "clazzid": CLASS_ID,
        "courseid": COURSE_ID,
        "cpi": stu_cpi,
        "collectionTime": "0",
        "mid": stu_puid,
        "videoObjectId": "",
        "videoRandomCollectTime": "0",
        "chapterId": "0"
    }

    print("\n--- 学生: /mooc-ans/qr/getqrstatus ---")
    try:
        r = stu_s.get("https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus",
                       params=getqr_params, allow_redirects=False, timeout=20)
        print_result("学生 getqrstatus", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 教师测试
    getqr_params_tea = dict(getqr_params)
    getqr_params_tea["cpi"] = tea_cpi
    getqr_params_tea["mid"] = tea_puid

    print("\n--- 教师: /mooc-ans/qr/getqrstatus ---")
    try:
        r = tea_s.get("https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus",
                       params=getqr_params_tea, allow_redirects=False, timeout=20)
        print_result("教师 getqrstatus", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 也测试POST方式
    print("\n--- 学生: /mooc-ans/qr/getqrstatus (POST) ---")
    try:
        r = stu_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus",
                        data=getqr_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("学生 getqrstatus POST", r)
    except Exception as e:
        print(f"    错误: {e}")

    # ============================================================
    print_separator("Part 6: 尝试获取QR code enc值")

    # 6.1 尝试 /mooc-ans/qr/produce
    print("\n--- 6.1 尙试生成QR码 /mooc-ans/qr/produce ---")
    produce_params = {
        "clazzId": CLASS_ID,
        "courseId": COURSE_ID,
        "cpi": tea_cpi,
        "mid": tea_puid,
    }
    try:
        r = tea_s.get("https://mooc1-api.chaoxing.com/mooc-ans/qr/produce",
                       params=produce_params, allow_redirects=False, timeout=20)
        print_result("教师 /mooc-ans/qr/produce GET", r)
    except Exception as e:
        print(f"    错误: {e}")

    try:
        r = tea_s.post("https://mooc1-api.chaoxing.com/mooc-ans/qr/produce",
                        data=produce_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("教师 /mooc-ans/qr/produce POST", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 6.2 尝试 /qr/produce
    print("\n--- 6.2 尝试 /qr/produce ---")
    try:
        r = tea_s.get("https://mooc1-api.chaoxing.com/qr/produce",
                       params=produce_params, allow_redirects=False, timeout=20)
        print_result("教师 /qr/produce GET", r)
    except Exception as e:
        print(f"    错误: {e}")

    try:
        r = tea_s.post("https://mooc1-api.chaoxing.com/qr/produce",
                        data=produce_params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        allow_redirects=False, timeout=20)
        print_result("教师 /qr/produce POST", r)
    except Exception as e:
        print(f"    错误: {e}")

    # 6.3 从活动列表API获取enc
    print("\n--- 6.3 从活动列表API获取enc ---")
    try:
        r = tea_s.get("https://mooc1-api.chaoxing.com/mooc-ans/phone/activelist",
                       params={"clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": tea_cpi},
                       allow_redirects=False, timeout=20)
        j = safe_json(r)
        txt = json.dumps(j, ensure_ascii=False, indent=2)
        if len(txt) > 1000:
            txt = txt[:1000] + "..."
        print(f"    活动列表: {txt}")

        # 搜索enc字段
        enc_found = []
        def find_enc(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if "enc" in k.lower() and v:
                        enc_found.append({"path": f"{path}.{k}", "value": str(v)[:100]})
                    find_enc(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    find_enc(v, f"{path}[{i}]")
        find_enc(j)
        for ef in enc_found:
            print(f"    ***IMPORTANT*** 找到enc: path={ef['path']}, value={ef['value']}")
    except Exception as e:
        print(f"    错误: {e}")

    # 6.4 尝试其他活动API
    print("\n--- 6.4 尝试其他活动API ---")
    try:
        r = tea_s.get("https://mooc1-api.chaoxing.com/mooc-ans/phone/activelist2",
                       params={"clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": tea_cpi},
                       allow_redirects=False, timeout=20)
        j = safe_json(r)
        txt = json.dumps(j, ensure_ascii=False)[:500]
        print(f"    activelist2: {txt}")
    except Exception as e:
        print(f"    错误: {e}")

    try:
        r = tea_s.get("https://mooc1-api.chaoxing.com/mooc-ans/phone/taskactivelist",
                       params={"clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": tea_cpi},
                       allow_redirects=False, timeout=20)
        j = safe_json(r)
        txt = json.dumps(j, ensure_ascii=False)[:500]
        print(f"    taskactivelist: {txt}")
    except Exception as e:
        print(f"    错误: {e}")

    # ============================================================
    print_separator("Part 7: 测试 mobilelearn 域名")

    mobilelearn_endpoints = [
        "/pptSign/updateqrstatus",
        "/qr/updateqrstatus",
        "/mooc-ans/qr/updateqrstatus",
    ]

    for ep in mobilelearn_endpoints:
        url = f"https://mobilelearn.chaoxing.com{ep}"
        print(f"\n--- 测试 {url} (学生) ---")

        # GET
        try:
            r = stu_s.get(url, params=base_params, allow_redirects=False, timeout=20)
            print_result(f"GET {ep}", r, show_headers=True)
        except Exception as e:
            print(f"    GET错误: {e}")

        # POST
        try:
            r = stu_s.post(url, data=base_params,
                           headers={"Content-Type": "application/x-www-form-urlencoded"},
                           allow_redirects=False, timeout=20)
            print_result(f"POST {ep}", r, show_headers=True)
        except Exception as e:
            print(f"    POST错误: {e}")

    # ============================================================
    print_separator("Part 8: 验证数据修改")

    # 对任何返回成功类响应的端点进行前后对比
    print("\n--- 8.1 查询当前QR签到状态 (学生) ---")
    status_endpoints = [
        ("mooc1-api getqrstatus", "https://mooc1-api.chaoxing.com/mooc-ans/qr/getqrstatus", "GET", getqr_params),
    ]

    before_results = {}
    for name, url, method, params in status_endpoints:
        try:
            if method == "GET":
                r = stu_s.get(url, params=params, allow_redirects=False, timeout=20)
            else:
                r = stu_s.post(url, data=params,
                               headers={"Content-Type": "application/x-www-form-urlencoded"},
                               allow_redirects=False, timeout=20)
            j = safe_json(r)
            before_results[name] = j
            txt = json.dumps(j, ensure_ascii=False)[:300]
            print(f"    [{name}] BEFORE: {txt}")
        except Exception as e:
            print(f"    [{name}] BEFORE错误: {e}")
            before_results[name] = None

    # 尝试执行签到操作
    print("\n--- 8.2 尝试执行签到操作 ---")
    sign_attempts = [
        ("mooc1-ans updateqrstatus (全部参数)", "https://mooc1-api.chaoxing.com/mooc-ans/qr/updateqrstatus", all_params),
        ("mooc1-api /qr/updateqrstatus", "https://mooc1-api.chaoxing.com/qr/updateqrstatus", all_params),
    ]

    for name, url, params in sign_attempts:
        try:
            r = stu_s.post(url, data=params,
                           headers={"Content-Type": "application/x-www-form-urlencoded"},
                           allow_redirects=False, timeout=20)
            j = safe_json(r)
            txt = json.dumps(j, ensure_ascii=False)[:300]
            print(f"    [{name}]: {txt}")

            # 检查是否成功
            if isinstance(j, dict):
                result = j.get("result", j.get("status", ""))
                if result in (1, "1", True, "true", "success"):
                    print(f"    !!!CRITICAL!!! 签到可能成功! name={name}")
        except Exception as e:
            print(f"    [{name}]错误: {e}")

    # 等待2秒后再次查询
    print("\n--- 8.3 等待2秒后再次查询 ---")
    time.sleep(2)

    for name, url, method, params in status_endpoints:
        try:
            if method == "GET":
                r = stu_s.get(url, params=params, allow_redirects=False, timeout=20)
            else:
                r = stu_s.post(url, data=params,
                               headers={"Content-Type": "application/x-www-form-urlencoded"},
                               allow_redirects=False, timeout=20)
            j = safe_json(r)
            after_txt = json.dumps(j, ensure_ascii=False)[:300]
            print(f"    [{name}] AFTER: {after_txt}")

            # 对比
            if before_results.get(name) is not None:
                before_txt = json.dumps(before_results[name], ensure_ascii=False, sort_keys=True)
                after_txt_full = json.dumps(j, ensure_ascii=False, sort_keys=True)
                if before_txt != after_txt_full:
                    print(f"    ***IMPORTANT*** 状态发生变化! name={name}")
                    print(f"      BEFORE: {before_txt[:200]}")
                    print(f"      AFTER:  {after_txt_full[:200]}")
        except Exception as e:
            print(f"    [{name}] AFTER错误: {e}")

    # ============================================================
    print_separator("额外测试: 尝试不同的API路径和参数组合")

    # 测试 /mooc-ans/qr/ 相关的所有端点
    qr_paths = [
        "/mooc-ans/qr/produce",
        "/mooc-ans/qr/getqrstatus",
        "/mooc-ans/qr/updateqrstatus",
        "/mooc-ans/qr/preSign",
        "/mooc-ans/qr/sign",
        "/mooc-ans/qr/checkqrstatus",
        "/mooc-ans/qr/qrcstatus",
    ]

    print("\n--- 探测QR相关API路径 ---")
    for path in qr_paths:
        url = f"https://mooc1-api.chaoxing.com{path}"
        try:
            r = stu_s.get(url, params={"clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": stu_cpi, "uuid": "test"},
                          allow_redirects=False, timeout=15)
            status = r.status_code
            txt = r.text[:200] if r.text else ""
            if status != 404:
                print(f"    {path}: status={status}, body={txt[:150]}")
            else:
                print(f"    {path}: 404 Not Found")
        except Exception as e:
            print(f"    {path}: ERROR={e}")

    # 测试 /mooc-ans/sign/ 相关端点
    sign_paths = [
        "/mooc-ans/sign/preSign",
        "/mooc-ans/sign/sign",
        "/mooc-ans/sign/checkSign",
        "/mooc-ans/sign/stuSign",
        "/mooc-ans/sign/doSign",
    ]

    print("\n--- 探测sign相关API路径 ---")
    for path in sign_paths:
        url = f"https://mooc1-api.chaoxing.com{path}"
        try:
            r = stu_s.get(url, params={"clazzid": CLASS_ID, "courseid": COURSE_ID, "cpi": stu_cpi},
                          allow_redirects=False, timeout=15)
            status = r.status_code
            txt = r.text[:200] if r.text else ""
            if status != 404:
                print(f"    {path}: status={status}, body={txt[:150]}")
            else:
                print(f"    {path}: 404 Not Found")
        except Exception as e:
            print(f"    {path}: ERROR={e}")

    # ============================================================
    print_separator("综合总结")

    print("""
  测试完成。关键发现:
  1. Session cookie修复: 通过访问mooc1-api域名建立session
  2. /qr/updateqrstatus 重定向问题: 检查是否仍然重定向
  3. /mooc-ans/qr/updateqrstatus 参数完整性: 检查哪些参数组合不再返回"参数不完整"
  4. cpi值: 是否成功获取
  5. QR enc值: 是否能通过任何API获取
  6. mobilelearn域名: 端点是否可用
  7. 数据修改验证: 签到操作是否生效
    """)

if __name__ == "__main__":
    main()
