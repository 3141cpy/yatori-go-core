#!/usr/bin/env python3
"""
ChaoXing (超星学习通) /v2/apis/ Sign Endpoints & Multi-Domain API Testing
Authorized Security Audit
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"

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
    return s, puid

# ============================================================
# Test helpers
# ============================================================

def test_endpoint(session, url, method="GET", data=None, params=None, timeout=15):
    """Test a single endpoint, return result dict."""
    result = {
        "url": url,
        "method": method,
        "status": None,
        "response_text": None,
        "response_len": 0,
        "error": None,
        "latency_ms": 0,
    }
    try:
        t0 = time.time()
        if method == "GET":
            r = session.get(url, params=params, timeout=timeout, allow_redirects=False)
        else:
            r = session.post(url, data=data, timeout=timeout, allow_redirects=False)
        result["status"] = r.status_code
        result["response_text"] = r.text[:2000]
        result["response_len"] = len(r.text)
        result["latency_ms"] = int((time.time() - t0) * 1000)
    except requests.exceptions.Timeout:
        result["error"] = "TIMEOUT"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"CONNECTION_ERROR: {str(e)[:200]}"
    except Exception as e:
        result["error"] = f"ERROR: {str(e)[:200]}"
    return result

def build_url(base, path):
    """Build URL ensuring proper joining."""
    base = base.rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}"

# ============================================================
# Part A: /v2/apis/ Sign Endpoints
# ============================================================

SIGN_ENDPOINTS = [
    "signIn", "signUp", "doSign", "submit", "modify", "update", "cancel",
    "makeup", "resign", "quickSign", "qrCodeSign", "preSign", "startSign",
    "endSign", "stopSign", "deleteSign", "removeSign", "createSign", "addSign",
    "saveSign", "batchSign", "autoSign", "manualSign", "status", "detail",
    "info", "list", "count", "check", "verify", "confirm", "approve", "reject",
    "review", "export", "report", "statistic", "analysis", "config", "setting",
    "rule", "policy", "template", "history", "log", "record", "result", "score",
    "grade", "rank", "sort", "filter", "search", "query",
]

ACTIVE_ENDPOINTS = [
    "detail", "student/activelist", "teacher/activelist", "startSign",
    "endSign", "create", "delete", "update", "modify", "list", "info",
    "status", "count",
]

V2_APIS_PREFIXES = [
    "sign", "active", "course", "class", "task", "member", "student",
    "teacher", "activity",
]

def run_part_a(session, course_id, class_id, puid):
    """Test /v2/apis/ sign-related endpoints."""
    results = []
    base = "https://mobilelearn.chaoxing.com"

    # Common params to include
    common_params = {
        "courseId": course_id,
        "classId": class_id,
        "puid": puid,
    }
    common_data = {
        "courseId": course_id,
        "classId": class_id,
    }

    print("=" * 70)
    print("Part A: /v2/apis/sign/ 端点测试")
    print("=" * 70)

    # 1) /v2/apis/sign/* endpoints
    for ep in SIGN_ENDPOINTS:
        url = build_url(base, f"v2/apis/sign/{ep}")
        for method in ["GET", "POST"]:
            r = test_endpoint(session, url, method=method,
                              params=common_params if method == "GET" else None,
                              data=common_data if method == "POST" else None)
            r["category"] = "/v2/apis/sign/"
            r["endpoint"] = ep
            results.append(r)
            status_str = f"{r['status']}" if r['status'] else r['error']
            print(f"  [{method}] /v2/apis/sign/{ep} => {status_str} ({r['latency_ms']}ms)")
        time.sleep(0.15)

    # 2) /v2/apis/active/* endpoints
    print()
    for ep in ACTIVE_ENDPOINTS:
        url = build_url(base, f"v2/apis/active/{ep}")
        for method in ["GET", "POST"]:
            r = test_endpoint(session, url, method=method,
                              params=common_params if method == "GET" else None,
                              data=common_data if method == "POST" else None)
            r["category"] = "/v2/apis/active/"
            r["endpoint"] = ep
            results.append(r)
            status_str = f"{r['status']}" if r['status'] else r['error']
            print(f"  [{method}] /v2/apis/active/{ep} => {status_str} ({r['latency_ms']}ms)")
        time.sleep(0.15)

    # 3) /v2/apis/{prefix}/* with wildcard sub-endpoints
    print()
    test_sub_eps = ["list", "detail", "info", "status", "create", "update", "delete"]
    for prefix in V2_APIS_PREFIXES:
        for sub in test_sub_eps:
            url = build_url(base, f"v2/apis/{prefix}/{sub}")
            for method in ["GET", "POST"]:
                r = test_endpoint(session, url, method=method,
                                  params=common_params if method == "GET" else None,
                                  data=common_data if method == "POST" else None)
                r["category"] = f"/v2/apis/{prefix}/"
                r["endpoint"] = sub
                results.append(r)
                status_str = f"{r['status']}" if r['status'] else r['error']
                print(f"  [{method}] /v2/apis/{prefix}/{sub} => {status_str} ({r['latency_ms']}ms)")
            time.sleep(0.1)

    return results

# ============================================================
# Part B: Multi-Domain API Testing
# ============================================================

DOMAIN_PATHS = {
    "mooc1-api.chaoxing.com": [
        "/mooc-ans/sign/signIn",
        "/mooc-ans/sign/updateSignStatus",
        "/mooc-ans/sign/doSign",
        "/mooc-ans/pptSign/stuSignajax",
        "/mooc-ans/pptSign/updateSignStatusByUidsV2",
        "/mooc-ans/pptSign/updateSignStatus",
        "/mooc-ans/newsign/updateSignStatus",
        "/mooc-ans/newsign/signIn",
        "/mooc-ans/ppt/activeAPI/taskactivelist",
        "/mooc-ans/ppt/activeAPI/createActive",
    ],
    "learn.chaoxing.com": [
        "/apis/sign/signIn",
        "/apis/sign/updateSignStatus",
        "/apis/pptSign/stuSignajax",
        "/apis/pptSign/updateSignStatusByUidsV2",
        "/apis/newsign/updateSignStatus",
    ],
    "office.chaoxing.com": [
        "/front/sign/signIn",
        "/front/sign/updateSignStatus",
        "/front/sign/stuSignajax",
    ],
    "mooc1.chaoxing.com": [
        "/mycourse/sign/signIn",
        "/mycourse/sign/updateSignStatus",
        "/mycourse/sign/doSign",
        "/mycourse/sign/stuSignajax",
        "/api/sign/signIn",
        "/api/sign/updateSignStatus",
        "/api/sign/doSign",
        "/api/sign/list",
    ],
    "i.chaoxing.com": [
        "/base/apis/sign/signIn",
        "/base/apis/sign/updateSignStatus",
        "/base/apis/sign/doSign",
        "/base/apis/sign/list",
        "/base/apis/sign/status",
    ],
}

def run_part_b(session, course_id, class_id, puid):
    """Test multi-domain API endpoints."""
    results = []

    common_params = {
        "courseId": course_id,
        "classId": class_id,
        "puid": puid,
    }
    common_data = {
        "courseId": course_id,
        "classId": class_id,
    }

    print()
    print("=" * 70)
    print("Part B: 多域名 API 测试")
    print("=" * 70)

    for domain, paths in DOMAIN_PATHS.items():
        print(f"\n--- 域名: {domain} ---")
        for path in paths:
            url = f"https://{domain}{path}"
            for method in ["GET", "POST"]:
                r = test_endpoint(session, url, method=method,
                                  params=common_params if method == "GET" else None,
                                  data=common_data if method == "POST" else None)
                r["category"] = f"multi-domain:{domain}"
                r["endpoint"] = path
                results.append(r)
                status_str = f"{r['status']}'" if r['status'] else r['error']
                print(f"  [{method}] {domain}{path} => {status_str} ({r['latency_ms']}ms)")
            time.sleep(0.15)

    return results

# ============================================================
# Analysis & Summary
# ============================================================

def analyze_results(all_results):
    """Analyze results and generate summary."""
    summary = {
        "total_requests": len(all_results),
        "by_status": {},
        "by_category": {},
        "accessible_endpoints": [],
        "auth_required_endpoints": [],
        "not_found_endpoints": [],
        "error_endpoints": [],
        "domain_differences": {},
    }

    for r in all_results:
        # Status distribution
        if r["status"]:
            key = str(r["status"])
        else:
            key = r.get("error", "UNKNOWN")[:30]
        summary["by_status"][key] = summary["by_status"].get(key, 0) + 1

        # Category distribution
        cat = r.get("category", "unknown")
        if cat not in summary["by_category"]:
            summary["by_category"][cat] = {"total": 0, "by_status": {}}
        summary["by_category"][cat]["total"] += 1
        skey = str(r["status"]) if r["status"] else (r.get("error", "UNKNOWN")[:30])
        summary["by_category"][cat]["by_status"][skey] = summary["by_category"][cat]["by_status"].get(skey, 0) + 1

        # Classify
        ep_label = f"[{r['method']}] {r['url']}"
        if r["status"] == 200:
            summary["accessible_endpoints"].append(ep_label)
        elif r["status"] in (301, 302, 303, 307, 308):
            summary["auth_required_endpoints"].append(ep_label)
        elif r["status"] == 404:
            summary["not_found_endpoints"].append(ep_label)
        elif r["status"] in (401, 403):
            summary["auth_required_endpoints"].append(ep_label)
        elif r["error"]:
            summary["error_endpoints"].append(ep_label)

    # Domain permission differences
    # Compare same logical endpoint across domains
    domain_map = {}  # path_tail -> {domain: status}
    for r in all_results:
        if "multi-domain:" in r.get("category", ""):
            domain = r["category"].split(":")[1]
            path_tail = r["endpoint"].split("/")[-1]
            key = f"{path_tail}_{r['method']}"
            if key not in domain_map:
                domain_map[key] = {}
            domain_map[key][domain] = r["status"]

    for key, domains in domain_map.items():
        statuses = set(str(v) for v in domains.values() if v)
        if len(statuses) > 1:
            summary["domain_differences"][key] = domains

    return summary

def print_summary(summary, all_results):
    """Print a readable summary."""
    print()
    print("=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    print(f"总请求数: {summary['total_requests']}")
    print()

    print("HTTP 状态码分布:")
    for status, count in sorted(summary["by_status"].items()):
        print(f"  {status}: {count} 次")
    print()

    print("各分类统计:")
    for cat, info in sorted(summary["by_category"].items()):
        print(f"  {cat}: 共 {info['total']} 请求")
        for s, c in sorted(info["by_status"].items()):
            print(f"    - {s}: {c}")
    print()

    print(f"可访问端点 (200): {len(summary['accessible_endpoints'])} 个")
    for ep in summary["accessible_endpoints"][:30]:
        print(f"  ✓ {ep}")
    if len(summary["accessible_endpoints"]) > 30:
        print(f"  ... 还有 {len(summary['accessible_endpoints']) - 30} 个")
    print()

    print(f"需要认证/重定向 (3xx/401/403): {len(summary['auth_required_endpoints'])} 个")
    for ep in summary["auth_required_endpoints"][:15]:
        print(f"  🔒 {ep}")
    if len(summary["auth_required_endpoints"]) > 15:
        print(f"  ... 还有 {len(summary['auth_required_endpoints']) - 15} 个")
    print()

    print(f"未找到 (404): {len(summary['not_found_endpoints'])} 个")
    print(f"连接错误: {len(summary['error_endpoints'])} 个")
    print()

    if summary["domain_differences"]:
        print("域名权限差异 (同一端点在不同域名返回不同状态码):")
        for key, domains in sorted(summary["domain_differences"].items()):
            print(f"  {key}:")
            for d, s in sorted(domains.items()):
                print(f"    {d} => {s}")
    else:
        print("域名权限差异: 未发现显著差异")

    # Show interesting response snippets for accessible endpoints
    print()
    print("可访问端点的响应摘要:")
    for r in all_results:
        if r["status"] == 200 and r["response_text"]:
            resp = r["response_text"][:300].replace("\n", " ").strip()
            print(f"  [{r['method']}] {r['url']}")
            print(f"    响应: {resp[:200]}")
            print()

# ============================================================
# Main
# ============================================================

def main():
    phone = "18436633997"
    pwd = "3.1415926Cpy"
    course_id = "257485372"
    class_id = "132821141"

    print("正在登录超星学习通...")
    session, puid = login(phone, pwd)
    print(f"登录完成, puid={puid}")

    if not puid:
        print("警告: 未获取到 puid, 可能登录失败, 继续测试...")

    # Part A
    part_a_results = run_part_a(session, course_id, class_id, puid)

    # Part B
    part_b_results = run_part_b(session, course_id, class_id, puid)

    # Combine
    all_results = part_a_results + part_b_results

    # Analyze
    summary = analyze_results(all_results)

    # Print summary
    print_summary(summary, all_results)

    # Save results
    output = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "puid": puid,
            "courseId": course_id,
            "classId": class_id,
            "total_requests": len(all_results),
        },
        "summary": summary,
        "results": all_results,
    }

    with open("/workspace/task4_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到 /workspace/task4_results.json")
    print(f"总请求数: {len(all_results)}")

if __name__ == "__main__":
    main()
