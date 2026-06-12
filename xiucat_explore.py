#!/usr/bin/env python3
"""
综合安全探测脚本 - beta-a.xiucat.top
授权安全审计
"""

import requests
import json
import time
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://beta-a.xiucat.top"
TIMEOUT = 15
RESULTS = {}

session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
})

def make_request(method, url, **kwargs):
    """发送请求并记录响应详情"""
    try:
        resp = session.request(method, url, timeout=TIMEOUT, allow_redirects=True, **kwargs)
        result = {
            "status_code": resp.status_code,
            "url": resp.url,
            "redirect_history": [r.status_code for r in resp.history] if resp.history else [],
            "headers": dict(resp.headers),
            "body_preview": resp.text[:2000] if resp.text else "",
            "body_length": len(resp.content),
            "content_type": resp.headers.get("Content-Type", ""),
        }
        return result
    except requests.exceptions.SSLError as e:
        return {"error": f"SSL Error: {e}"}
    except requests.exceptions.Timeout:
        return {"error": "Timeout"}
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection Error: {e}"}
    except Exception as e:
        return {"error": f"Exception: {type(e).__name__}: {e}"}

def analyze_headers(headers):
    """分析响应头"""
    analysis = {}
    interesting_headers = [
        "Server", "X-Powered-By", "X-AspNet-Version", "X-Frame-Options",
        "X-Content-Type-Options", "Strict-Transport-Security",
        "Content-Security-Policy", "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials", "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers", "X-RateLimit-Limit",
        "X-RateLimit-Remaining", "X-Request-Id", "Set-Cookie",
    ]
    for h in interesting_headers:
        if h in headers:
            analysis[h] = headers[h]
    # 查找自定义头
    for h in headers:
        if h.lower().startswith("x-") and h not in interesting_headers:
            analysis[f"[Custom] {h}"] = headers[h]
    return analysis

def detect_tech_stack(result):
    """技术栈检测"""
    tech = []
    if not result or "error" in result:
        return tech
    
    body = result.get("body_preview", "").lower()
    headers = result.get("headers", {})
    server = headers.get("Server", "").lower()
    x_powered = headers.get("X-Powered-By", "").lower()
    
    # Spring Boot
    if "whitelabel" in body or "spring" in body or "springboot" in x_powered:
        tech.append("Spring Boot")
    
    # Express.js
    if "express" in x_powered or "x-powered-by: express" in str(headers).lower():
        tech.append("Express.js")
    
    # Django
    if "django" in x_powered or "csrfmiddleware" in body:
        tech.append("Django")
    
    # Flask
    if "flask" in x_powered or "werkzeug" in x_powered:
        tech.append("Flask/Werkzeug")
    
    # Nginx
    if "nginx" in server:
        tech.append(f"Nginx ({server})")
    
    # Apache
    if "apache" in server:
        tech.append(f"Apache ({server})")
    
    # Node.js
    if "node" in x_powered or "x-request-id" in headers:
        tech.append("Possibly Node.js")
    
    # Cloudflare
    if "cloudflare" in server or "cf-ray" in headers:
        tech.append("Cloudflare CDN")
    
    # 其他
    if x_powered and x_powered not in ["express", "flask", "werkzeug", "django"]:
        tech.append(f"X-Powered-By: {headers.get('X-Powered-By')}")
    
    return tech

def analyze_error(result):
    """分析错误信息"""
    if not result or "error" in result:
        return None
    
    body = result.get("body_preview", "")
    findings = []
    
    # 检查是否泄露内部路径
    import re
    paths = re.findall(r'(?:\/(?:home|usr|var|opt|app|src|tmp|etc)\/[\w\/\.\-]+)', body)
    if paths:
        findings.append(f"内部路径泄露: {paths}")
    
    # 检查堆栈跟踪
    if "traceback" in body.lower() or "exception" in body.lower() or "stack" in body.lower():
        findings.append("可能泄露堆栈跟踪")
    
    # 检查SQL错误
    if "sql" in body.lower() and ("error" in body.lower() or "syntax" in body.lower()):
        findings.append("可能泄露SQL错误信息")
    
    # 检查JSON格式
    if body.strip().startswith("{") or body.strip().startswith("["):
        findings.append("返回JSON格式响应")
        try:
            j = json.loads(body)
            if isinstance(j, dict):
                findings.append(f"JSON键: {list(j.keys())}")
        except:
            pass
    
    # 检查HTML格式
    if "<html" in body.lower() or "<!doctype" in body.lower():
        findings.append("返回HTML页面")
    
    # 检查API结构泄露
    if "api" in body.lower() and ("endpoint" in body.lower() or "route" in body.lower() or "path" in body.lower()):
        findings.append("可能泄露API路由结构")
    
    return findings if findings else None

# ============================================================
# 1. 基础URL探测
# ============================================================
print("=" * 80)
print("1. 基础URL探测")
print("=" * 80)

base_paths = ["/", "/favicon.ico", "/robots.txt", "/sitemap.xml"]
for path in base_paths:
    url = BASE_URL + path
    print(f"\n[GET] {url}")
    result = make_request("GET", url)
    RESULTS[f"GET {path}"] = result
    if "error" in result:
        print(f"  ❌ {result['error']}")
    else:
        print(f"  状态码: {result['status_code']}")
        print(f"  Content-Type: {result['content_type']}")
        print(f"  Body长度: {result['body_length']}")
        if result['redirect_history']:
            print(f"  重定向历史: {result['redirect_history']}")
        headers_analysis = analyze_headers(result['headers'])
        if headers_analysis:
            print(f"  关键响应头: {json.dumps(headers_analysis, ensure_ascii=False, indent=4)}")
        tech = detect_tech_stack(result)
        if tech:
            print(f"  技术栈: {tech}")
        err = analyze_error(result)
        if err:
            print(f"  错误分析: {err}")
        if result['body_preview']:
            print(f"  响应体预览: {result['body_preview'][:500]}")

# ============================================================
# 2. 通用API路径枚举
# ============================================================
print("\n" + "=" * 80)
print("2. 通用API路径枚举")
print("=" * 80)

common_paths = [
    "/api/", "/api/v1/", "/api/v2/",
    "/api/sign", "/api/signIn", "/api/login", "/api/auth", "/api/user",
    "/api/chaoxing", "/api/cx", "/api/attendance", "/api/checkin",
    "/api/sign/update", "/api/sign/status",
    "/sign", "/login", "/auth", "/user", "/chaoxing",
    "/health", "/status", "/info", "/version",
    "/swagger-ui.html", "/swagger-ui/", "/api-docs",
    "/v2/api-docs", "/v3/api-docs",
    "/actuator", "/actuator/health", "/actuator/env", "/actuator/info",
    "/actuator/mappings", "/actuator/beans", "/actuator/configprops", "/actuator/routes",
    "/graphql", "/graphiql",
    "/.env", "/.git/config",
    "/config", "/admin", "/dashboard", "/console", "/debug", "/test",
    "/ws", "/websocket",
]

interesting_results = {}

for path in common_paths:
    url = BASE_URL + path
    # GET
    get_result = make_request("GET", url)
    RESULTS[f"GET {path}"] = get_result
    
    status = get_result.get("status_code", "ERR") if "error" not in get_result else "ERR"
    body_len = get_result.get("body_length", 0)
    
    marker = ""
    if status != 404 and status != "ERR":
        marker = " ⭐"
        interesting_results[f"GET {path}"] = get_result
    elif status == "ERR":
        marker = " ❌"
    
    print(f"  GET  {path:50s} → {status} (len={body_len}){marker}")
    
    # POST
    post_result = make_request("POST", url)
    RESULTS[f"POST {path}"] = post_result
    
    p_status = post_result.get("status_code", "ERR") if "error" not in post_result else "ERR"
    p_len = post_result.get("body_length", 0)
    
    p_marker = ""
    if p_status != 404 and p_status != "ERR":
        p_marker = " ⭐"
        interesting_results[f"POST {path}"] = post_result
    elif p_status == "ERR":
        p_marker = " ❌"
    
    print(f"  POST {path:50s} → {p_status} (len={p_len}){p_marker}")
    
    time.sleep(0.3)  # 避免过快请求

# ============================================================
# 3. 超星特定路径
# ============================================================
print("\n" + "=" * 80)
print("3. 超星特定路径探测")
print("=" * 80)

cx_paths = [
    "/api/pptSign/updateSignStatus",
    "/api/pptSign/updateSignStatusByUidsV2",
    "/api/pptSign/stuSignajax",
    "/api/newsign/updateSignStatus",
    "/api/widget/sign/pcTeaSignController/updateSignStatus2",
    "/api/v2/apis/sign/signIn",
    "/pptSign/updateSignStatus",
    "/pptSign/updateSignStatusByUidsV2",
    "/newsign/updateSignStatus",
    "/widget/sign/pcTeaSignController/updateSignStatus2",
    "/v2/apis/sign/signIn",
    "/mooc-ans/pptSign/updateSignStatusByUidsV2",
]

for path in cx_paths:
    url = BASE_URL + path
    get_result = make_request("GET", url)
    RESULTS[f"GET {path}"] = get_result
    
    status = get_result.get("status_code", "ERR") if "error" not in get_result else "ERR"
    body_len = get_result.get("body_length", 0)
    
    marker = ""
    if status != 404 and status != "ERR":
        marker = " ⭐"
        interesting_results[f"GET {path}"] = get_result
    elif status == "ERR":
        marker = " ❌"
    
    print(f"  GET  {path:60s} → {status} (len={body_len}){marker}")
    
    post_result = make_request("POST", url)
    RESULTS[f"POST {path}"] = post_result
    
    p_status = post_result.get("status_code", "ERR") if "error" not in post_result else "ERR"
    p_len = post_result.get("body_length", 0)
    
    p_marker = ""
    if p_status != 404 and p_status != "ERR":
        p_marker = " ⭐"
        interesting_results[f"POST {path}"] = post_result
    elif p_status == "ERR":
        p_marker = " ❌"
    
    print(f"  POST {path:60s} → {p_status} (len={p_len}){p_marker}")
    
    time.sleep(0.3)

# ============================================================
# 4. 有趣结果的详细分析
# ============================================================
print("\n" + "=" * 80)
print("4. 非默认响应详细分析")
print("=" * 80)

for key, result in interesting_results.items():
    print(f"\n{'─' * 60}")
    print(f"[{key}]")
    if "error" in result:
        print(f"  错误: {result['error']}")
        continue
    print(f"  状态码: {result['status_code']}")
    print(f"  最终URL: {result['url']}")
    print(f"  Content-Type: {result['content_type']}")
    print(f"  Body长度: {result['body_length']}")
    if result['redirect_history']:
        print(f"  重定向: {result['redirect_history']}")
    
    headers_analysis = analyze_headers(result['headers'])
    if headers_analysis:
        print(f"  关键响应头:")
        for k, v in headers_analysis.items():
            print(f"    {k}: {v}")
    
    tech = detect_tech_stack(result)
    if tech:
        print(f"  技术栈: {tech}")
    
    err = analyze_error(result)
    if err:
        print(f"  错误/信息分析:")
        for e in err:
            print(f"    - {e}")
    
    print(f"  响应体预览:")
    preview = result['body_preview'][:800]
    for line in preview.split('\n')[:20]:
        print(f"    {line}")

# ============================================================
# 5. POST参数测试
# ============================================================
print("\n" + "=" * 80)
print("5. POST参数测试 (对非404端点)")
print("=" * 80)

post_test_paths = set()
for key, result in interesting_results.items():
    if key.startswith("POST ") and "error" not in result and result.get("status_code") != 404:
        post_test_paths.add(key.replace("POST ", ""))

# 也对一些关键路径强制测试
forced_test_paths = [
    "/api/login", "/api/auth", "/api/sign", "/api/signIn",
    "/login", "/auth", "/api/sign/update", "/api/sign/status",
    "/api/user", "/api/chaoxing", "/api/cx",
    "/api/pptSign/updateSignStatus",
    "/api/pptSign/updateSignStatusByUidsV2",
    "/api/newsign/updateSignStatus",
    "/api/v2/apis/sign/signIn",
]

for p in forced_test_paths:
    post_test_paths.add(p)

test_bodies = [
    ("空body", {}),
    ("JSON登录", {"json": {"phone": "18436633997", "password": "3.1415926Cpy"}, "headers_override": {"Content-Type": "application/json"}}),
    ("Form登录", {"data": {"phone": "18436633997", "password": "3.1415926Cpy"}, "headers_override": {"Content-Type": "application/x-www-form-urlencoded"}}),
    ("JSON签到", {"json": {"activeId": "5000163891319", "status": "1", "uid": "431407443"}, "headers_override": {"Content-Type": "application/json"}}),
    ("Form签到", {"data": {"activeId": "5000163891319", "status": "1", "uid": "431407443"}, "headers_override": {"Content-Type": "application/x-www-form-urlencoded"}}),
]

for path in sorted(post_test_paths):
    url = BASE_URL + path
    print(f"\n  测试路径: {path}")
    for test_name, test_data in test_bodies:
        headers_override = test_data.pop("headers_override", {})
        kwargs = {}
        kwargs.update(test_data)
        if headers_override:
            kwargs["headers"] = {**session.headers, **headers_override}
        
        result = make_request("POST", url, **kwargs)
        status = result.get("status_code", "ERR") if "error" not in result else "ERR"
        body_len = result.get("body_length", 0)
        body_preview = result.get("body_preview", "")[:200] if "error" not in result else ""
        
        print(f"    {test_name:15s} → {status} (len={body_len})")
        if status not in [404, "ERR"] and body_preview:
            print(f"      响应: {body_preview[:150]}")
        
        time.sleep(0.2)

# ============================================================
# 6. CORS测试
# ============================================================
print("\n" + "=" * 80)
print("6. CORS测试")
print("=" * 80)

cors_test_paths = ["/", "/api/", "/api/login", "/api/sign", "/api/auth", "/api/user"]
for path in cors_test_paths:
    url = BASE_URL + path
    print(f"\n  测试CORS: {path}")
    
    # 带Origin的GET
    result = make_request("GET", url, headers={"Origin": "https://evil.com"})
    if "error" not in result:
        acao = result['headers'].get("Access-Control-Allow-Origin", "未设置")
        acac = result['headers'].get("Access-Control-Allow-Credentials", "未设置")
        acam = result['headers'].get("Access-Control-Allow-Methods", "未设置")
        print(f"    GET Origin: https://evil.com")
        print(f"      ACAO: {acao}")
        print(f"      ACAC: {acac}")
        print(f"      ACAM: {acam}")
        
        if acao == "https://evil.com":
            print(f"      ⚠️ CORS配置不当: 反射了恶意Origin!")
        elif acao == "*":
            print(f"      ⚠️ CORS配置为通配符 *")
    
    # OPTIONS预检
    result = make_request("OPTIONS", url, headers={
        "Origin": "https://evil.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    })
    if "error" not in result:
        acao = result['headers'].get("Access-Control-Allow-Origin", "未设置")
        acac = result['headers'].get("Access-Control-Allow-Credentials", "未设置")
        acam = result['headers'].get("Access-Control-Allow-Methods", "未设置")
        acah = result['headers'].get("Access-Control-Allow-Headers", "未设置")
        print(f"    OPTIONS预检")
        print(f"      ACAO: {acao}")
        print(f"      ACAC: {acac}")
        print(f"      ACAM: {acam}")
        print(f"      ACAH: {acah}")
    
    time.sleep(0.3)

# ============================================================
# 7. 技术指纹汇总
# ============================================================
print("\n" + "=" * 80)
print("7. 技术指纹汇总")
print("=" * 80)

all_tech = set()
for key, result in RESULTS.items():
    tech = detect_tech_stack(result)
    for t in tech:
        all_tech.add(t)

if all_tech:
    for t in sorted(all_tech):
        print(f"  - {t}")
else:
    print("  未检测到明确技术栈特征")

# 收集所有唯一Server头
servers = set()
for key, result in RESULTS.items():
    if "error" not in result and "headers" in result:
        s = result["headers"].get("Server", "")
        if s:
            servers.add(s)
if servers:
    print(f"\n  Server头: {servers}")

# 收集所有X-Powered-By
xpb = set()
for key, result in RESULTS.items():
    if "error" not in result and "headers" in result:
        s = result["headers"].get("X-Powered-By", "")
        if s:
            xpb.add(s)
if xpb:
    print(f"  X-Powered-By: {xpb}")

# ============================================================
# 8. 状态码统计
# ============================================================
print("\n" + "=" * 80)
print("8. 响应状态码统计")
print("=" * 80)

status_counts = {}
non_404_results = {}
for key, result in RESULTS.items():
    if "error" in result:
        status = "ERROR"
    else:
        status = result.get("status_code", "UNKNOWN")
    status_counts[status] = status_counts.get(status, 0) + 1
    if status != 404 and status != "ERROR":
        non_404_results[key] = result

for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")

# ============================================================
# 9. 完整结果保存
# ============================================================
output_file = "/workspace/xiucat_explore_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    # 简化结果以减少文件大小
    simplified = {}
    for key, result in RESULTS.items():
        if "error" in result:
            simplified[key] = {"error": result["error"]}
        else:
            simplified[key] = {
                "status_code": result["status_code"],
                "url": result["url"],
                "content_type": result["content_type"],
                "body_length": result["body_length"],
                "body_preview": result["body_preview"][:500],
                "headers": result["headers"],
            }
    json.dump(simplified, f, ensure_ascii=False, indent=2)

print(f"\n完整结果已保存到: {output_file}")
print("\n" + "=" * 80)
print("探测完成!")
print("=" * 80)
