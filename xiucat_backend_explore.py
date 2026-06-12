#!/usr/bin/env python3
"""
Authorized security audit: Explore backend API at https://beta-a.xiucat.top
to understand how it modifies ChaoXing (学习通) sign-in status.
"""

import requests
import json
import time
import sys

BASE = "https://beta-a.xiucat.top"
TIMEOUT = 10

# Collect all results
results = []

def probe(method, path, data=None, json_data=None, desc=""):
    url = f"{BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=TIMEOUT, allow_redirects=True, verify=True)
        elif method == "POST":
            r = requests.post(url, timeout=TIMEOUT, data=data, json=json_data, allow_redirects=True, verify=True)
        elif method == "OPTIONS":
            r = requests.options(url, timeout=TIMEOUT, allow_redirects=True, verify=True)
        elif method == "PUT":
            r = requests.put(url, timeout=TIMEOUT, json=json_data, allow_redirects=True, verify=True)
        else:
            return

        info = {
            "method": method,
            "url": url,
            "desc": desc,
            "status": r.status_code,
            "headers": dict(r.headers),
            "body": r.text[:3000] if r.text else "",
            "content_type": r.headers.get("Content-Type", ""),
        }

        # Mark interesting responses (not 404, not 502/503)
        if r.status_code not in (404, 502, 503, 504):
            info["INTERESTING"] = True
        else:
            info["INTERESTING"] = False

        results.append(info)

        # Print on the fly for interesting ones
        if info["INTERESTING"]:
            print(f"\n{'='*80}")
            print(f"[INTERESTING] {method} {url}")
            print(f"  Status: {r.status_code}")
            print(f"  Content-Type: {info['content_type']}")
            print(f"  Server: {r.headers.get('Server', 'N/A')}")
            print(f"  X-Powered-By: {r.headers.get('X-Powered-By', 'N/A')}")
            print(f"  CORS Allow-Origin: {r.headers.get('Access-Control-Allow-Origin', 'N/A')}")
            print(f"  Body ({len(r.text)} chars): {r.text[:2000]}")
            print(f"{'='*80}")
        else:
            print(f"  [{r.status_code}] {method} {path}")

    except requests.exceptions.SSLError as e:
        print(f"  [SSL_ERROR] {method} {path}: {e}")
        results.append({"method": method, "url": url, "error": f"SSL: {e}"})
    except requests.exceptions.ConnectionError as e:
        print(f"  [CONN_ERROR] {method} {path}: {e}")
        results.append({"method": method, "url": url, "error": f"Connection: {e}"})
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {method} {path}")
        results.append({"method": method, "url": url, "error": "Timeout"})
    except Exception as e:
        print(f"  [ERROR] {method} {path}: {type(e).__name__}: {e}")
        results.append({"method": method, "url": url, "error": f"{type(e).__name__}: {e}"})


# ============================================================
# Phase 1: Base URL exploration
# ============================================================
print("\n" + "="*80)
print("PHASE 1: Base URL exploration")
print("="*80)

base_paths = [
    "/", "/api", "/api/", "/docs", "/swagger", "/swagger-ui.html",
    "/api-docs", "/v1", "/v2", "/health", "/status", "/info",
    "/version", "/actuator", "/actuator/health", "/actuator/env",
    "/actuator/info", "/actuator/mappings", "/actuator/beans",
    "/actuator/configprops", "/robots.txt", "/sitemap.xml",
    "/.env", "/.git/config", "/favicon.ico",
    "/openapi.json", "/openapi.yaml", "/swagger.json", "/swagger/v1/swagger.json",
    "/api/swagger.json", "/api/openapi.json",
]

for p in base_paths:
    probe("GET", p, desc="base exploration")
    time.sleep(0.2)

# ============================================================
# Phase 2: Sign-in related API paths
# ============================================================
print("\n" + "="*80)
print("PHASE 2: Sign-in related API paths")
print("="*80)

sign_paths = [
    "/api/sign", "/api/sign/in", "/api/sign/status", "/api/sign/update",
    "/api/sign/modify", "/api/chaoxing/sign", "/api/chaoxing/signIn",
    "/api/chaoxing/updateSignStatus", "/api/chaoxing/attendance",
    "/api/v1/sign", "/api/v1/signIn", "/api/v1/attendance",
    "/api/v2/sign", "/api/v2/signIn",
    "/sign", "/sign/in", "/sign/status", "/signIn",
    "/login", "/auth", "/user", "/course", "/class", "/attendance",
    "/api/user", "/api/course", "/api/class",
    "/api/active", "/api/activity", "/api/task",
]

for p in sign_paths:
    probe("GET", p, desc="sign-in GET")
    time.sleep(0.2)

# Try POST on sign-related paths
sign_post_paths = [
    "/api/sign", "/api/sign/in", "/api/sign/status", "/api/sign/update",
    "/api/sign/modify", "/api/chaoxing/sign", "/api/chaoxing/signIn",
    "/api/chaoxing/updateSignStatus",
    "/sign", "/sign/in", "/signIn",
]

for p in sign_post_paths:
    probe("POST", p, desc="sign-in POST (empty)")
    time.sleep(0.2)

# ============================================================
# Phase 3: ChaoXing-specific paths
# ============================================================
print("\n" + "="*80)
print("PHASE 3: ChaoXing-specific paths")
print("="*80)

cx_paths = [
    "/api/pptSign", "/api/newsign", "/api/widget/sign",
    "/pptSign", "/newsign",
    "/chaoxing", "/cx", "/cx/sign", "/cx/signIn", "/cx/attendance",
    "/api/cx", "/api/cx/sign", "/api/cx/signIn", "/api/cx/attendance",
    "/api/chaoxing", "/api/chaoxing/login",
]

for p in cx_paths:
    probe("GET", p, desc="chaoxing GET")
    time.sleep(0.2)

for p in ["/api/pptSign", "/api/newsign", "/pptSign", "/newsign"]:
    probe("POST", p, desc="chaoxing POST (empty)")
    time.sleep(0.2)

# ============================================================
# Phase 4: Authentication paths
# ============================================================
print("\n" + "="*80)
print("PHASE 4: Authentication paths")
print("="*80)

auth_paths = [
    "/api/login", "/api/auth", "/api/token", "/api/user/login",
    "/login", "/auth/login", "/register", "/oauth", "/sso",
    "/api/register", "/api/oauth", "/api/sso",
    "/api/user/register", "/api/user/info",
    "/api/auth/login", "/api/auth/token", "/api/auth/callback",
]

for p in auth_paths:
    probe("GET", p, desc="auth GET")
    time.sleep(0.2)

# POST login with dummy data
for p in ["/api/login", "/api/user/login", "/login", "/auth/login"]:
    probe("POST", p, data={"phone": "test", "password": "test"}, desc="auth POST (dummy)")
    time.sleep(0.2)

# ============================================================
# Phase 5: OPTIONS for CORS on interesting paths
# ============================================================
print("\n" + "="*80)
print("PHASE 5: OPTIONS (CORS) probing")
print("="*80)

cors_paths = [
    "/", "/api", "/api/sign", "/api/login", "/api/chaoxing",
    "/api/pptSign", "/api/newsign", "/api/user",
]

for p in cors_paths:
    probe("OPTIONS", p, desc="CORS OPTIONS")
    time.sleep(0.2)

# ============================================================
# Phase 6: Try common ChaoXing parameter patterns on POST
# ============================================================
print("\n" + "="*80)
print("PHASE 6: Parameterized POST requests")
print("="*80)

# Try POST to /api/sign with ChaoXing-style params
cx_params = {
    "activeId": "12345",
    "courseId": "67890",
    "classId": "11111",
    "uid": "22222",
    "status": "1",
    "signType": "0",
}

probe("POST", "/api/sign", json_data=cx_params, desc="POST /api/sign with CX params (json)")
time.sleep(0.3)
probe("POST", "/api/sign", data=cx_params, desc="POST /api/sign with CX params (form)")
time.sleep(0.3)

# Try login-style params
login_params = {
    "phone": "13800138000",
    "password": "test123",
}
probe("POST", "/api/login", json_data=login_params, desc="POST /api/login with phone/password (json)")
time.sleep(0.3)

# Try cookie-based auth
cookie_params = {
    "cookie": "test_cookie",
    "token": "test_token",
    "uid": "12345",
}
probe("POST", "/api/chaoxing/sign", json_data=cookie_params, desc="POST /api/chaoxing/sign with cookie/token")
time.sleep(0.3)

# Try fid/uname/denc params (ChaoXing specific)
cx_auth_params = {
    "fid": "1234",
    "uname": "test",
    "denc": "test",
    "duid": "test",
}
probe("POST", "/api/sign", json_data=cx_auth_params, desc="POST /api/sign with CX auth params")
time.sleep(0.3)

# ============================================================
# Phase 7: Additional discovery paths
# ============================================================
print("\n" + "="*80)
print("PHASE 7: Additional discovery paths")
print("="*80)

extra_paths = [
    "/api/config", "/api/settings", "/api/help", "/api/about",
    "/api/monitor", "/api/debug", "/api/test", "/api/ping",
    "/api/health", "/api/status", "/api/version", "/api/info",
    "/config", "/settings", "/help", "/about",
    "/monitor", "/debug", "/test", "/ping",
    "/graphql", "/api/graphql",
    "/ws", "/api/ws", "/socket.io",
    "/api/index", "/index", "/index.html",
    "/api/admin", "/admin",
    "/api/dashboard", "/dashboard",
    "/api/report", "/report",
    "/api/queue", "/api/task", "/api/job",
    "/api/notification", "/api/notify",
    "/api/school", "/api/college", "/api/teacher",
    "/api/student", "/api/stu",
    "/.well-known/openid-configuration",
    "/.well-known/security.txt",
    "/security.txt",
    "/crossdomain.xml",
    "/clientaccesspolicy.xml",
    "/web.config",
    "/web.xml",
    "/package.json",
    "/composer.json",
    "/Gemfile",
    "/requirements.txt",
    "/Dockerfile",
    "/docker-compose.yml",
    "/.gitignore",
    "/.git/HEAD",
    "/wp-json", "/wp-login.php",
    "/phpmyadmin",
    "/console",
    "/management",
    "/trace",
    "/metrics",
    "/env",
    "/beans",
    "/mappings",
]

for p in extra_paths:
    probe("GET", p, desc="extra discovery")
    time.sleep(0.15)

# ============================================================
# Phase 8: Try PUT method on sign endpoints
# ============================================================
print("\n" + "="*80)
print("PHASE 8: PUT method on sign endpoints")
print("="*80)

put_paths = [
    "/api/sign", "/api/sign/status", "/api/sign/update",
    "/api/chaoxing/sign", "/api/chaoxing/updateSignStatus",
]

for p in put_paths:
    probe("PUT", p, json_data=cx_params, desc="PUT with CX params")
    time.sleep(0.2)

# ============================================================
# Summary
# ============================================================
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

interesting = [r for r in results if r.get("INTERESTING")]
errors = [r for r in results if "error" in r]
all_checked = len(results)

print(f"\nTotal requests made: {all_checked}")
print(f"Interesting responses (non-404/5xx): {len(interesting)}")
print(f"Errors: {len(errors)}")

print("\n--- INTERESTING RESPONSES ---")
for r in interesting:
    print(f"\n  {r['method']} {r['url']}")
    print(f"    Status: {r['status']}")
    print(f"    Content-Type: {r.get('content_type', 'N/A')}")
    hdrs = r.get('headers', {})
    print(f"    Server: {hdrs.get('Server', 'N/A')}")
    print(f"    X-Powered-By: {hdrs.get('X-Powered-By', 'N/A')}")
    print(f"    CORS Allow-Origin: {hdrs.get('Access-Control-Allow-Origin', 'N/A')}")
    print(f"    CORS Allow-Methods: {hdrs.get('Access-Control-Allow-Methods', 'N/A')}")
    print(f"    CORS Allow-Headers: {hdrs.get('Access-Control-Allow-Headers', 'N/A')}")
    body = r.get('body', '')
    if body:
        print(f"    Body: {body[:1500]}")

# Save full results to JSON
with open("/workspace/xiucat_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nFull results saved to /workspace/xiucat_results.json")

# Group by status code
from collections import Counter
status_counts = Counter(r.get("status", "error") for r in results)
print("\n--- STATUS CODE DISTRIBUTION ---")
for code, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"  {code}: {count}")

# Technology clues
print("\n--- TECHNOLOGY CLUES ---")
servers = set()
powered_by = set()
for r in interesting:
    h = r.get("headers", {})
    if h.get("Server"):
        servers.add(h["Server"])
    if h.get("X-Powered-By"):
        powered_by.add(h["X-Powered-By"])
print(f"  Server headers: {servers if servers else 'None found'}")
print(f"  X-Powered-By headers: {powered_by if powered_by else 'None found'}")
