#!/usr/bin/env python3
"""
ChaoXing Platform Endpoint Scanner - Authorized Security Audit
Scans /newsign/ and /pptSign/ paths using student account only.
"""
import base64, hashlib, json, uuid, requests, urllib3, time, sys, os, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
BASE = "https://mobilelearn.chaoxing.com"

PHONE = "18436633997"
PWD = "3.1415926Cpy"
PUID = "431407443"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
AID = "5000163891319"

# Thread-local storage for sessions
_thread_local = threading.local()

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
    r = s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                            "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                            "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    print(f"[LOGIN] Status: {r.status_code}", flush=True)
    puid_val = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid_val = c.value
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    return s, puid_val

def get_thread_session(cookies_dict, headers_dict):
    """Get or create a thread-local session with the same cookies/headers"""
    if not hasattr(_thread_local, 'session'):
        s = requests.Session()
        s.verify = False
        s.headers.update(headers_dict)
        for name, value in cookies_dict.items():
            s.cookies.set(name, value)
        _thread_local.session = s
    return _thread_local.session

# ============================================================
# Endpoint lists
# ============================================================

VERBS = [
    "add", "save", "create", "insert", "submit", "do", "student", "stu", "sign", "start", "pre", "quick",
    "makeUp", "resign", "modify", "change", "delete", "cancel", "stop", "end", "close", "confirm", "check",
    "verify", "get", "query", "list", "detail", "info", "count", "batch", "sync", "update", "set", "edit",
    "remove", "clear", "approve", "reject", "review", "export", "handle", "process", "execute", "trigger",
    "fetch", "load", "read", "write", "append", "merge", "copy", "move", "replace", "toggle", "enable",
    "disable", "grant", "revoke", "assign", "transfer", "backup", "restore", "refresh", "reset", "retry",
    "reopen", "notify", "alert", "log", "debug", "trace", "monitor", "health", "ping", "status", "version",
    "config", "setting", "preference", "option", "feature", "flag", "switch", "rule", "policy", "permission",
    "role", "user", "group", "team", "org", "project", "app", "module", "plugin", "extension", "hook",
    "callback", "event", "message", "queue", "task", "job", "worker", "session", "token", "auth", "login",
    "logout", "password", "profile", "account", "dashboard", "report", "chart", "analytics", "search",
    "filter", "sort", "page", "cache", "store", "db", "database", "table", "field", "record", "document",
    "file", "folder", "resource", "asset", "content", "template", "layout", "component", "widget", "element",
    "item", "entry", "value", "key", "id", "uuid", "hash", "signature", "certificate", "credential", "secret",
    "code", "captcha", "otp", "location", "gps", "coordinate", "latitude", "longitude", "distance", "radius",
    "area", "region", "zone", "boundary", "geofence", "beacon", "qr", "barcode", "scan", "camera", "sensor",
    "device", "hardware", "firmware", "software", "os", "browser", "client", "server", "proxy", "gateway",
    "router", "firewall", "domain", "host", "port", "protocol", "scheme", "method", "header", "cookie",
    "storage", "memory", "network", "bandwidth", "latency", "concurrency", "thread", "container", "cloud",
    "cluster", "node", "service", "endpoint", "route", "middleware", "filter", "handler", "controller",
    "repository", "model", "entity", "dto", "form", "request", "response", "result", "error", "warning",
    "metric", "notification", "email", "sms", "push", "webhook", "stream", "flow", "workflow", "pipeline",
    "cron", "schedule", "timer", "delay", "timeout", "retry", "buffer", "pool", "stack", "tree", "graph",
    "list", "map", "set", "array", "dict", "string", "number", "boolean", "date", "time", "datetime",
    "timestamp", "duration", "interval", "range", "window", "page", "block", "chunk", "segment", "fragment",
    "piece", "part", "portion", "slice", "division", "category", "type", "kind", "sort", "tag", "name",
    "title", "description", "summary", "body", "header", "footer", "button", "link", "input", "field",
    "value", "default", "validation", "message", "icon", "image", "animation", "style", "theme", "color",
    "font", "size", "position", "display"
]

NOUNS = [
    "Sign", "SignRecord", "SignStatus", "SignInfo", "SignDetail", "SignResult", "SignLog", "SignHistory",
    "Active", "Activity", "Task", "Record", "Status", "User", "Student", "Member", "Course", "Class",
    "Clazz", "Lesson", "Chapter", "Section", "Unit", "Module", "Topic", "Subject", "Category", "Tag",
    "Label", "Group", "Team", "Role", "Permission", "Rule", "Policy", "Config", "Setting", "Preference",
    "Option", "Feature", "Flag", "Switch", "Toggle", "Notification", "Message", "Alert", "Warning",
    "Error", "Exception", "Log", "Debug", "Trace", "Metric", "Event", "Report", "Chart", "Dashboard",
    "Search", "Filter", "Sort", "Page", "Cache", "Store", "Database", "Table", "Field", "Document",
    "File", "Folder", "Resource", "Asset", "Content", "Template", "Layout", "Component", "Widget",
    "Element", "Item", "Entry", "Value", "Key", "Id", "Uuid", "Hash", "Signature", "Certificate",
    "Credential", "Secret", "Password", "Token", "Code", "Captcha", "Otp", "Location", "Coordinate",
    "Latitude", "Longitude", "Distance", "Radius", "Area", "Region", "Zone", "Boundary", "Geofence",
    "Beacon", "Qr", "Barcode", "Scan", "Camera", "Sensor", "Device", "Hardware", "Firmware", "Software",
    "Os", "Browser", "App", "Client", "Server", "Proxy", "Gateway", "Router", "Firewall", "Domain",
    "Host", "Port", "Protocol", "Scheme", "Method", "Header", "Cookie", "Session", "Storage", "Memory",
    "Network", "Bandwidth", "Latency", "Concurrency", "Thread", "Container", "Cloud", "Cluster", "Node",
    "Service", "Endpoint", "Route", "Middleware", "Handler", "Controller", "Repository", "Model", "Entity",
    "Dto", "Form", "Request", "Response", "Result", "Error", "Warning", "Info", "Debug", "Log", "Metric",
    "Event", "Alert", "Notification", "Email", "Sms", "Push", "Webhook", "Callback", "Queue", "Topic",
    "Channel", "Stream", "Flow", "Workflow", "Pipeline", "Job", "Task", "Cron", "Schedule", "Timer",
    "Delay", "Timeout", "Retry", "Cache", "Buffer", "Pool", "Stack", "Tree", "Graph", "List", "Map",
    "Set", "Array", "Dict", "String", "Number", "Boolean", "Date", "Time", "Datetime", "Timestamp",
    "Duration", "Interval", "Range", "Window", "Page", "Block", "Chunk", "Segment", "Fragment", "Piece",
    "Part", "Portion", "Slice", "Division", "Category", "Type", "Kind", "Sort", "Tag", "Name", "Title",
    "Description", "Summary", "Content", "Body", "Header", "Footer", "Button", "Link", "Input", "Field",
    "Value", "Default", "Validation", "Message", "Icon", "Image", "Animation", "Style", "Theme", "Color",
    "Font", "Size", "Position", "Display"
]

STANDALONE = [
    "signIn", "signUp", "doSign", "submit", "modify", "change", "delete", "cancel", "stop", "end",
    "close", "confirm", "check", "verify", "get", "query", "list", "detail", "info", "count", "batch",
    "sync", "update", "set", "edit", "remove", "clear", "approve", "reject", "review", "export", "handle",
    "process", "execute", "trigger", "fetch", "load", "read", "write", "append", "merge", "copy", "move",
    "replace", "toggle", "enable", "disable", "grant", "revoke", "assign", "transfer", "backup", "restore",
    "refresh", "reset", "retry", "reopen", "notify", "alert", "log", "debug", "trace", "monitor", "health",
    "ping", "status", "version", "config", "setting", "preference", "option", "feature", "flag", "switch",
    "rule", "policy", "permission", "role", "user", "group", "team", "org", "project", "app", "module",
    "plugin", "extension", "hook", "callback", "event", "message", "queue", "task", "job", "worker",
    "session", "token", "auth", "login", "logout", "password", "profile", "account", "dashboard", "report",
    "chart", "analytics", "search", "filter", "sort", "page", "cache", "store", "db", "database", "table",
    "field", "record", "document", "file", "folder", "resource", "asset", "content", "template", "layout",
    "component", "widget", "element", "item", "entry", "value", "key", "id", "uuid", "hash", "signature",
    "certificate", "credential", "secret", "code", "captcha", "otp", "location", "gps", "coordinate",
    "latitude", "longitude", "distance", "radius", "area", "region", "zone", "boundary", "geofence",
    "beacon", "qr", "barcode", "scan", "camera", "sensor", "device", "hardware", "firmware", "software",
    "os", "browser", "client", "server", "proxy", "gateway", "router", "firewall", "domain", "host",
    "port", "protocol", "scheme", "method", "header", "cookie", "storage", "memory", "network", "bandwidth",
    "latency", "concurrency", "thread", "container", "cloud", "cluster", "node", "service", "endpoint",
    "route", "middleware", "handler", "controller", "repository", "model", "entity", "dto", "form",
    "request", "response", "result", "error", "warning", "metric", "notification", "email", "sms", "push",
    "webhook", "stream", "flow", "workflow", "pipeline", "cron", "schedule", "timer", "delay", "timeout",
    "retry", "buffer", "pool", "stack", "tree", "graph", "list", "map", "set", "array", "dict", "string",
    "number", "boolean", "date", "time", "datetime", "timestamp", "duration", "interval", "range", "window",
    "page", "block", "chunk", "segment", "fragment", "piece", "part", "portion", "slice", "division",
    "category", "type", "kind", "sort", "tag", "name", "title", "description", "summary", "body", "header",
    "footer", "button", "link", "input", "field", "value", "default", "validation", "message", "icon",
    "image", "animation", "style", "theme", "color", "font", "size", "position", "display"
]

PPTSIGN_ENDPOINTS = [
    "stuSignAjaxNew", "stuSignajaxNew", "stuSignNew", "stuSignV2", "signV2", "signNew", "signInV2",
    "signInNew", "qrCodeSign", "qrcodeSign", "scanSign", "scanQrCode", "locationSign", "gestureSign",
    "numberSign", "signByCode", "signByEnc", "signByToken", "getSignStuInfo", "getStuSignInfo",
    "stuSignInfo", "getSignStatus", "signStatus", "checkSignStatus", "activeSignList", "signList",
    "getSignList", "getActiveSign", "activeSign", "startSign", "endSign", "stopSign", "cancelSign",
    "deleteSign", "removeSign", "createSign", "addSign", "saveSign", "updateSign", "modifySign",
    "changeSign", "batchSign", "quickSign", "autoSign", "manualSign", "makeupSign", "lateSign",
    "leaveSign", "absentSign", "presentSign", "normalSign", "codeSign", "passwordSign", "faceSign",
    "fingerprintSign", "wifiSign", "bleSign", "nfcSign", "lbsSign", "gpsSign", "mapSign", "geoSign",
    "distanceSign", "rangeSign", "areaSign", "zoneSign", "regionSign", "nearbySign", "proximitySign",
    "beaconSign", "ibeaconSign", "eddystoneSign", "altBeaconSign"
]

def is_html_error(text):
    if not text:
        return False
    stripped = text.strip()
    return stripped.startswith("<!DOCTYPE") or stripped.startswith("<html") or stripped.startswith("<HTML")

# Global session info for thread-local session creation
_session_cookies = {}
_session_headers = {}

def test_endpoint_threadsafe(base_url, endpoint, method, params=None):
    """Test a single endpoint with GET or POST using thread-local session"""
    session = get_thread_session(_session_cookies, _session_headers)
    url = f"{base_url}/{endpoint}"
    try:
        if method == "GET":
            r = session.get(url, params=params, timeout=8, allow_redirects=False)
        else:
            r = session.post(url, data=params, timeout=8, allow_redirects=False)

        if r.status_code == 404:
            return None

        text = ""
        try:
            text = r.text[:500]
        except:
            text = "(cannot decode)"

        if is_html_error(text):
            return None

        return {
            "endpoint": endpoint,
            "method": method,
            "url": url,
            "status": r.status_code,
            "response_preview": text[:300]
        }
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None

def generate_newsign_endpoints():
    seen = set()
    endpoints = []
    for v in VERBS:
        for n in NOUNS:
            ep = v + n
            if ep not in seen:
                seen.add(ep)
                endpoints.append(ep)
    for s in STANDALONE:
        if s not in seen:
            seen.add(s)
            endpoints.append(s)
    return endpoints

def scan_newsign(puid):
    """Part 1: Scan /newsign/ endpoints"""
    print("\n" + "="*80, flush=True)
    print("PART 1: Scanning /newsign/ endpoints", flush=True)
    print("="*80, flush=True)

    base_url = f"{BASE}/newsign"
    endpoints = generate_newsign_endpoints()
    total = len(endpoints) * 2
    print(f"[INFO] Total /newsign/ endpoints to test: {len(endpoints)} (x2 methods = {total} requests)", flush=True)

    base_params = {
        "activeId": AID,
        "uid": puid,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "status": "1",
        "remark": ""
    }

    results = []
    tested = 0
    found = 0
    lock = threading.Lock()

    def test_one(args):
        ep, method = args
        return test_endpoint_threadsafe(base_url, ep, method, params=base_params)

    tasks = []
    for ep in endpoints:
        tasks.append((ep, "GET"))
        tasks.append((ep, "POST"))

    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = {executor.submit(test_one, t): t for t in tasks}
        for future in as_completed(futures):
            with lock:
                tested += 1
            if tested % 1000 == 0:
                print(f"  [PROGRESS] Tested {tested}/{total} endpoints, found {found} so far...", flush=True)
            result = future.result()
            if result:
                with lock:
                    results.append(result)
                    found += 1
                print(f"  [FOUND] {result['method']} /newsign/{result['endpoint']} -> HTTP {result['status']}", flush=True)

    print(f"\n[SUMMARY] /newsign/ scan complete: {tested} tested, {found} found", flush=True)
    return results

def scan_pptsign(puid):
    """Part 2: Scan /pptSign/ endpoints"""
    print("\n" + "="*80, flush=True)
    print("PART 2: Scanning /pptSign/ endpoints", flush=True)
    print("="*80, flush=True)

    base_url = f"{BASE}/pptSign"
    base_params = {
        "activeId": AID,
        "uid": puid,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "status": "1",
        "remark": ""
    }

    results = []
    tested = 0
    found = 0
    lock = threading.Lock()

    tasks = []
    for ep in PPTSIGN_ENDPOINTS:
        tasks.append((ep, "GET", base_params.copy()))
        tasks.append((ep, "POST", base_params.copy()))

    def test_one_ppt(task):
        ep, method, params = task
        return test_endpoint_threadsafe(base_url, ep, method, params=params)

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(test_one_ppt, t): t for t in tasks}
        for future in as_completed(futures):
            with lock:
                tested += 1
            result = future.result()
            if result:
                with lock:
                    results.append(result)
                    found += 1
                print(f"  [FOUND] {result['method']} /pptSign/{result['endpoint']} -> HTTP {result['status']}", flush=True)

    print(f"\n[SUMMARY] /pptSign/ basic scan: {tested} tested, {found} found", flush=True)

    # Deep test: stuSignajax with parameter variations
    print("\n[INFO] Deep testing stuSignajax/stuSignAjaxNew with parameter variations...", flush=True)
    deep_results = []

    variations = []
    # status variations for stuSignajax
    for st in [1, 0, 2]:
        p = base_params.copy()
        p["status"] = str(st)
        variations.append(("stuSignajax", "GET", p))
        variations.append(("stuSignajax", "POST", p.copy()))

    # enc variations for stuSignajax
    for enc_val in ["test", "empty", "random"]:
        for method in ["GET", "POST"]:
            p = base_params.copy()
            p["enc"] = enc_val
            variations.append(("stuSignajax", method, p))

    # appType variations for stuSignajax
    for app_type in [0, 1, 15]:
        for method in ["GET", "POST"]:
            p = base_params.copy()
            p["appType"] = str(app_type)
            variations.append(("stuSignajax", method, p))

    # location variations for stuSignajax
    for method in ["GET", "POST"]:
        p = base_params.copy()
        p["latitude"] = "39.9042"
        p["longitude"] = "116.4074"
        p["appType"] = "0"
        variations.append(("stuSignajax", method, p))

    # stuSignAjaxNew variations
    for st in [1, 0, 2]:
        for method in ["GET", "POST"]:
            p = base_params.copy()
            p["status"] = str(st)
            variations.append(("stuSignAjaxNew", method, p))

    for enc_val in ["test", "empty", "random"]:
        for method in ["GET", "POST"]:
            p = base_params.copy()
            p["enc"] = enc_val
            variations.append(("stuSignAjaxNew", method, p))

    for app_type in [0, 1, 15]:
        for method in ["GET", "POST"]:
            p = base_params.copy()
            p["appType"] = str(app_type)
            variations.append(("stuSignAjaxNew", method, p))

    for method in ["GET", "POST"]:
        p = base_params.copy()
        p["latitude"] = "39.9042"
        p["longitude"] = "116.4074"
        p["appType"] = "0"
        variations.append(("stuSignAjaxNew", method, p))

    deep_tested = 0
    deep_found = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(test_one_ppt, v): v for v in variations}
        for future in as_completed(futures):
            deep_tested += 1
            result = future.result()
            if result:
                deep_results.append(result)
                deep_found += 1
                print(f"  [DEEP FOUND] {result['method']} /pptSign/{result['endpoint']} -> HTTP {result['status']}", flush=True)

    print(f"\n[SUMMARY] /pptSign/ deep test: {deep_tested} tested, {deep_found} found", flush=True)

    all_results = results + deep_results
    return all_results

def main():
    print("="*80, flush=True)
    print("ChaoXing Platform Endpoint Scanner - Authorized Security Audit", flush=True)
    print("="*80, flush=True)

    # Login
    print("\n[STEP 1] Logging in with student account...", flush=True)
    session, puid_val = login(PHONE, PWD)
    if not puid_val:
        puid_val = PUID
    print(f"[LOGIN] PUID: {puid_val}", flush=True)
    print(f"[LOGIN] Cookies: {dict(session.cookies)}", flush=True)

    # Set global session info for thread-local sessions
    global _session_cookies, _session_headers
    _session_cookies = dict(session.cookies)
    _session_headers = dict(session.headers)

    # Part 1: /newsign/ scan
    t1 = time.time()
    newsign_results = scan_newsign(puid_val)
    t1_elapsed = time.time() - t1
    print(f"[TIME] /newsign/ scan took {t1_elapsed:.1f}s", flush=True)

    # Part 2: /pptSign/ scan
    t2 = time.time()
    pptsign_results = scan_pptsign(puid_val)
    t2_elapsed = time.time() - t2
    print(f"[TIME] /pptSign/ scan took {t2_elapsed:.1f}s", flush=True)

    # Save results
    print("\n" + "="*80, flush=True)
    print("SAVING RESULTS", flush=True)
    print("="*80, flush=True)

    total_newsign_tested = len(generate_newsign_endpoints()) * 2
    with open("/workspace/task2_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "scan_type": "/newsign/ endpoint scan",
            "puid": puid_val,
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
            "activeId": AID,
            "total_tested": total_newsign_tested,
            "found_count": len(newsign_results),
            "elapsed_seconds": round(t1_elapsed, 1),
            "results": newsign_results
        }, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] /workspace/task2_results.json ({len(newsign_results)} endpoints)", flush=True)

    with open("/workspace/task3_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "scan_type": "/pptSign/ endpoint scan (student account)",
            "puid": puid_val,
            "courseId": COURSE_ID,
            "classId": CLASS_ID,
            "activeId": AID,
            "found_count": len(pptsign_results),
            "elapsed_seconds": round(t2_elapsed, 1),
            "results": pptsign_results
        }, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] /workspace/task3_results.json ({len(pptsign_results)} endpoints)", flush=True)

    # Print summary
    print("\n" + "="*80, flush=True)
    print("FINAL SUMMARY - ALL DISCOVERED ENDPOINTS (non-404, non-HTML-error)", flush=True)
    print("="*80, flush=True)

    print(f"\n--- /newsign/ endpoints ({len(newsign_results)}) ---", flush=True)
    for r in sorted(newsign_results, key=lambda x: (x["endpoint"], x["method"])):
        print(f"  [{r['method']}] /newsign/{r['endpoint']} -> HTTP {r['status']}", flush=True)

    print(f"\n--- /pptSign/ endpoints ({len(pptsign_results)}) ---", flush=True)
    for r in sorted(pptsign_results, key=lambda x: (x["endpoint"], x["method"])):
        print(f"  [{r['method']}] /pptSign/{r['endpoint']} -> HTTP {r['status']}", flush=True)

    print(f"\n[TOTAL] /newsign/ found: {len(newsign_results)}, /pptSign/ found: {len(pptsign_results)}", flush=True)
    print("[DONE] Scan complete.", flush=True)

if __name__ == "__main__":
    main()
