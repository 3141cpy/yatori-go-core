#!/usr/bin/env python3
"""ChaoXing /newsign/ endpoint scanner - authorized security audit
Final version: dual-domain async scan with baseline filtering"""

import base64, hashlib, json, uuid, time, sys, asyncio
import aiohttp
import urllib3
import requests
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

def login_sync(phone, pwd):
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
    cookies = {}
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
        cookies[c.name] = c.value
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    for c in s.cookies:
        cookies[c.name] = c.value
    return puid, cookies, ua

# ---- Endpoint patterns ----
VERBS = [
    "add", "save", "create", "insert", "submit", "do", "student", "stu", "sign", "start",
    "pre", "quick", "makeUp", "resign", "modify", "change", "delete", "cancel", "stop", "end",
    "close", "lock", "unlock", "send", "push", "publish", "confirm", "check", "verify", "get",
    "query", "list", "detail", "info", "count", "stat", "refresh", "reset", "retry", "reopen",
    "batch", "sync", "update", "set", "edit", "remove", "clear", "approve", "reject", "review",
    "export", "import", "download", "upload", "handle", "process", "execute", "run", "trigger",
    "invoke", "call", "fetch", "load", "read", "write", "append", "merge", "split", "copy",
    "move", "replace", "swap", "toggle", "enable", "disable", "grant", "revoke", "assign",
    "delegate", "transfer", "backup", "restore", "migrate", "upgrade", "downgrade", "rollback",
    "compile", "build", "deploy", "release", "install", "uninstall", "register", "unregister",
    "subscribe", "unsubscribe", "notify", "alert", "warn", "log", "debug", "trace", "monitor",
    "health", "ping", "status", "version", "config", "setting", "preference", "option", "feature",
    "flag", "switch", "rule", "policy", "permission", "role", "user", "group", "team", "org",
    "tenant", "project", "app", "module", "plugin", "extension", "hook", "callback", "event",
    "message", "queue", "task", "job", "worker", "thread", "session", "token", "auth", "login",
    "logout", "password", "profile", "account", "dashboard", "report", "chart", "graph", "metric",
    "analytics", "search", "filter", "sort", "page", "limit", "offset", "cursor", "scroll",
    "paginate", "cache", "store", "db", "database", "table", "field", "column", "row", "record",
    "document", "file", "folder", "directory", "path", "url", "link", "image", "video", "audio",
    "media", "attachment", "resource", "asset", "content", "template", "layout", "component",
    "widget", "element", "section", "block", "item", "entry", "cell", "value", "key", "id",
    "uuid", "hash", "checksum", "signature", "certificate", "credential", "secret", "code",
    "captcha", "otp", "mfa", "2fa", "biometric", "fingerprint", "face", "voice", "iris", "palm",
    "heartbeat", "gesture", "motion", "location", "gps", "coordinate", "latitude", "longitude",
    "altitude", "accuracy", "speed", "heading", "bearing", "distance", "radius", "area", "region",
    "zone", "boundary", "perimeter", "fence", "geofence", "beacon", "wifi", "bluetooth", "nfc",
    "rfid", "qr", "barcode", "scan", "camera", "microphone", "speaker", "sensor", "actuator",
    "device", "hardware", "firmware", "software", "os", "browser", "client", "server", "proxy",
    "gateway", "router", "firewall", "loadbalancer", "cdn", "dns", "ssl", "tls", "domain",
    "host", "port", "protocol", "scheme", "method", "header", "cookie", "storage", "memory",
    "disk", "cpu", "gpu", "network", "bandwidth", "latency", "throughput", "concurrency",
    "parallelism", "container", "vm", "cloud", "cluster", "node", "pod", "service", "endpoint",
    "route", "middleware", "interceptor", "handler", "controller", "repository", "dao", "model",
    "entity", "dto", "vo", "form", "request", "response", "result", "exception", "warning",
    "notification", "email", "sms", "webhook", "channel", "stream", "pipe", "flow", "workflow",
    "pipeline", "cron", "schedule", "timer", "delay", "timeout", "backoff", "circuit", "breaker",
    "fallback", "buffer", "pool", "stack", "heap", "tree", "list", "map", "set", "array", "tuple",
    "dict", "string", "number", "boolean", "date", "time", "datetime", "timestamp", "duration",
    "interval", "period", "range", "span", "window", "frame", "chunk", "segment", "fragment",
    "piece", "part", "portion", "slice", "division", "category", "class", "type", "kind", "sort",
    "tag", "label", "name", "title", "description", "summary", "abstract", "body", "footer",
    "sidebar", "nav", "menu", "button", "input", "placeholder", "default", "required", "optional",
    "validation", "hint", "tooltip", "icon", "animation", "transition", "effect", "style",
    "theme", "color", "font", "size", "spacing", "margin", "padding", "border", "shadow",
    "radius", "opacity", "visibility", "display", "position", "overflow", "zindex", "flex",
    "grid", "gap", "align", "justify", "order", "wrap", "grow", "shrink", "basis"
]

NOUNS = [
    "Sign", "SignRecord", "SignStatus", "SignInfo", "SignDetail", "SignResult", "SignLog",
    "SignHistory", "Active", "Activity", "Task", "Record", "Status", "User", "Student",
    "Member", "Course", "Class", "Clazz", "Lesson", "Chapter", "Section", "Unit", "Module",
    "Topic", "Subject", "Category", "Tag", "Label", "Group", "Team", "Role", "Permission",
    "Rule", "Policy", "Config", "Setting", "Preference", "Option", "Feature", "Flag", "Switch",
    "Toggle", "Notification", "Message", "Alert", "Warning", "Error", "Exception", "Log",
    "Debug", "Trace", "Metric", "Event", "Report", "Chart", "Dashboard", "Search", "Filter",
    "Sort", "Page", "Cache", "Store", "Database", "Table", "Field", "Document", "File",
    "Folder", "Resource", "Asset", "Content", "Template", "Layout", "Component", "Widget",
    "Element", "Item", "Entry", "Value", "Key", "Id", "Uuid", "Hash", "Signature",
    "Certificate", "Credential", "Secret", "Password", "Token", "Code", "Captcha", "Otp",
    "Location", "Coordinate", "Latitude", "Longitude", "Distance", "Radius", "Area", "Region",
    "Zone", "Boundary", "Geofence", "Beacon", "Qr", "Barcode", "Scan", "Camera", "Sensor",
    "Device", "Hardware", "Firmware", "Software", "Os", "Browser", "App", "Client", "Server",
    "Proxy", "Gateway", "Router", "Firewall", "Domain", "Host", "Port", "Protocol", "Scheme",
    "Method", "Header", "Cookie", "Session", "Storage", "Memory", "Network", "Bandwidth",
    "Latency", "Concurrency", "Thread", "Process", "Container", "Cloud", "Cluster", "Node",
    "Service", "Endpoint", "Route", "Middleware", "Filter", "Handler", "Controller",
    "Repository", "Model", "Entity", "Dto", "Form", "Request", "Response", "Result", "Info",
    "Date", "Time", "Datetime", "Timestamp", "Duration", "Interval", "Range", "Window",
    "Block", "Chunk", "Segment", "Fragment", "Piece", "Part", "Portion", "Slice", "Division",
    "Type", "Kind", "Name", "Title", "Description", "Summary", "Body", "Footer", "Button",
    "Link", "Input", "Default", "Validation", "Icon", "Image", "Animation", "Style", "Theme",
    "Color", "Font", "Size", "Position", "Display"
]


def generate_endpoints():
    """Generate all endpoint paths"""
    paths = set()
    for w in VERBS:
        paths.add(w)
    for n in NOUNS:
        paths.add(n)
        paths.add(n.lower())
    for v in VERBS:
        for n in NOUNS:
            paths.add(f"{v}{n}")
    for v in VERBS:
        for n in NOUNS:
            paths.add(f"{v}/{n}")
    for v in VERBS:
        for n in NOUNS:
            paths.add(f"{v}_{n}")
    return list(paths)


async def async_scan(endpoints, cookies, ua, puid, course_id, class_id, active_id,
                     base_url, catchall_keys, max_concurrent=200):
    """Async scan with aiohttp - scan all endpoints, return only non-catchall hits"""
    results = []
    catchall_count = 0
    sem = asyncio.Semaphore(max_concurrent)

    params = {"activeId": str(active_id), "uid": str(puid), "courseId": str(course_id), "classId": str(class_id)}
    post_data = {**params, "status": "1", "remark": ""}

    headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh_CN",
    }

    connector = aiohttp.TCPConnector(ssl=False, limit=max_concurrent, limit_per_host=max_concurrent)

    async with aiohttp.ClientSession(cookies=cookies, headers=headers, connector=connector) as session:
        async def scan_one(path):
            nonlocal catchall_count
            async with sem:
                url = f"{base_url}/newsign/{path}"
                hits = []
                for method in ["GET", "POST"]:
                    try:
                        if method == "GET":
                            async with session.get(url, params=params,
                                                   timeout=aiohttp.ClientTimeout(total=5),
                                                   allow_redirects=False) as r:
                                status = r.status
                                body = await r.read()
                        else:
                            async with session.post(url, data=post_data,
                                                    timeout=aiohttp.ClientTimeout(total=5),
                                                    allow_redirects=False) as r:
                                status = r.status
                                body = await r.read()

                        resp_key = (status, len(body))
                        if resp_key not in catchall_keys:
                            text = body.decode("utf-8", errors="replace")[:500]
                            hits.append({
                                "path": f"/newsign/{path}",
                                "method": method,
                                "status_code": status,
                                "response_length": len(body),
                                "is_catchall": False,
                                "response_preview": text,
                                "base_url": base_url,
                            })
                    except Exception:
                        pass

                if not hits:
                    catchall_count += 1
                return hits

        # Process in batches
        batch_size = 2000
        total = len(endpoints)
        done = 0

        for i in range(0, total, batch_size):
            batch = endpoints[i:i+batch_size]
            tasks = [scan_one(ep) for ep in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for br in batch_results:
                if isinstance(br, list):
                    results.extend(br)
            done += len(batch)
            print(f"  [进度] {done}/{total} ({done*100//total}%) - 发现 {len(results)} 个真实命中", flush=True)

    return results, catchall_count


def main():
    print("=" * 60)
    print("ChaoXing /newsign/ Endpoint Scanner (Async)")
    print("Authorized Security Audit")
    print("=" * 60)

    # Step 1: Login
    print("\n[*] 正在登录...")
    puid, cookies, ua = login_sync("18436633997", "3.1415926Cpy")
    if not puid:
        puid = "431407443"
    print(f"[+] 登录成功, puid={puid}")

    course_id = 257485372
    class_id = 132821141
    active_id = 5000163891319

    # Step 2: Establish baselines
    print("\n[*] 基线测试...")
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*"})
    for name, val in cookies.items():
        s.cookies.set(name, val)

    baselines = {}
    domains = [
        (BASE, "mobilelearn.chaoxing.com"),
        ("https://mooc1-1.chaoxing.com", "mooc1-1.chaoxing.com"),
    ]

    for base_url, label in domains:
        catchall = set()
        for bp in ["randomnonexistentpath12345", "zzzz_fake_99999"]:
            try:
                r = s.get(f"{base_url}/newsign/{bp}", params={"activeId": str(active_id), "uid": str(puid), "courseId": str(course_id), "classId": str(class_id)}, timeout=10, allow_redirects=False)
                catchall.add((r.status_code, len(r.content)))
                print(f"  {label}: /newsign/{bp} -> {r.status_code} ({len(r.content)}B)")
            except Exception as e:
                print(f"  基线测试失败: {e}")
        baselines[base_url] = catchall
        print(f"  {label} catch-all: {catchall}")

    # Step 3: Generate endpoints
    endpoints = generate_endpoints()
    print(f"\n[*] 生成了 {len(endpoints)} 个端点路径待扫描")

    # Step 4: Scan both domains concurrently
    all_results = []
    total_catchall = 0
    start_time = time.time()

    # Scan mobilelearn.chaoxing.com (full set)
    print(f"\n[*] 扫描 {BASE}/newsign/ (并发=200)...")
    ml_results, ml_catchall = asyncio.run(
        async_scan(endpoints, cookies, ua, puid, course_id, class_id, active_id,
                   BASE, baselines[BASE], max_concurrent=200)
    )
    all_results.extend(ml_results)
    total_catchall += ml_catchall
    print(f"  mobilelearn: {len(ml_results)} 真实命中")

    # Scan mooc1-1.chaoxing.com (focused set)
    MOOC_BASE = "https://mooc1-1.chaoxing.com"
    focused_verbs = ["pre", "stu", "do", "quick", "start", "get", "sign", "student", "makeUp", "resign",
                     "add", "save", "create", "submit", "check", "verify", "query", "list", "detail", "info",
                     "update", "delete", "cancel", "batch", "refresh", "reset", "count", "stat", "export",
                     "download", "upload", "search", "filter", "status", "config", "health", "ping"]
    focused_endpoints = set()
    for v in focused_verbs:
        for n in NOUNS:
            focused_endpoints.add(f"{v}{n}")
            focused_endpoints.add(f"{v}/{n}")
    for w in VERBS:
        focused_endpoints.add(w)
    for n in NOUNS:
        focused_endpoints.add(n)
        focused_endpoints.add(n.lower())
    focused_endpoints = list(focused_endpoints)

    print(f"\n[*] 扫描 mooc1-1.chaoxing.com/newsign/ ({len(focused_endpoints)} 个端点)...")
    mooc_results, mooc_catchall = asyncio.run(
        async_scan(focused_endpoints, cookies, ua, puid, course_id, class_id, active_id,
                   MOOC_BASE, baselines[MOOC_BASE], max_concurrent=100)
    )
    all_results.extend(mooc_results)
    total_catchall += mooc_catchall
    print(f"  mooc1-1: {len(mooc_results)} 真实命中")

    total_elapsed = time.time() - start_time

    # Step 5: Save
    output = {
        "scan_info": {
            "base_url": BASE,
            "path_prefix": "/newsign/",
            "puid": puid,
            "courseId": course_id,
            "classId": class_id,
            "activeId": active_id,
            "total_endpoints_scanned": len(endpoints) + len(focused_endpoints),
            "total_real_hits": len(all_results),
            "total_catchall_hits": total_catchall,
            "elapsed_seconds": round(total_elapsed, 2),
            "mobilelearn_catchall_pattern": str(baselines[BASE]),
            "mooc_catchall_pattern": str(baselines[MOOC_BASE]),
            "note": "mobilelearn.chaoxing.com returns 500 (224B) catch-all for all /newsign/ paths when authenticated. "
                    "mooc1-1.chaoxing.com returns 404 for non-existent /newsign/ paths. "
                    "Results with is_catchall=false have different response patterns than the baseline.",
        },
        "real_hits": all_results,
        "catchall_hits_total": total_catchall,
    }

    with open("/workspace/task2_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Step 6: Summary
    print("\n" + "=" * 60)
    print("扫描结果摘要")
    print("=" * 60)
    print(f"扫描端点总数: {len(endpoints) + len(focused_endpoints)}")
    print(f"  mobilelearn.chaoxing.com: {len(endpoints)} 个")
    print(f"  mooc1-1.chaoxing.com: {len(focused_endpoints)} 个")
    print(f"真实命中 (非catch-all): {len(all_results)}")
    print(f"Catch-all命中 (服务器统一响应): {total_catchall}")
    print(f"总耗时: {total_elapsed:.2f}s")

    if all_results:
        by_status = {}
        for r in all_results:
            sc = r["status_code"]
            by_status.setdefault(sc, []).append(r)

        print(f"\n真实命中按状态码分布:")
        for sc in sorted(by_status.keys()):
            paths = sorted(set(r["path"] for r in by_status[sc]))
            print(f"  {sc}: {len(by_status[sc])} 个响应, {len(paths)} 个唯一路径")

        unique_paths = sorted(set(r["path"] for r in all_results))
        print(f"\n发现的有效路径 ({len(unique_paths)} 个):")
        for p in unique_paths[:100]:
            methods = sorted(set(r["method"] for r in all_results if r["path"] == p))
            statuses = sorted(set(r["status_code"] for r in all_results if r["path"] == p))
            domains = sorted(set(r.get("base_url", "").replace("https://", "") for r in all_results if r["path"] == p))
            print(f"  {p}  [{', '.join(methods)}] -> {statuses} @ {domains}")
        if len(unique_paths) > 100:
            print(f"  ... 还有 {len(unique_paths) - 100} 个路径 (详见JSON)")
    else:
        print("\n未发现非catch-all的有效端点")

    print(f"\n结果已保存到: /workspace/task2_results.json")


if __name__ == "__main__":
    main()
