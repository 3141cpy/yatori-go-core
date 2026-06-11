#!/usr/bin/env python3
"""
Deep dive into interesting findings from Tiers 9-11
"""
import base64, hashlib, json, uuid, requests, urllib3, time
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

def get_sign_params(uid):
    return {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

print("=" * 80)
print("Deep Dive - Interesting Findings from Tiers 9-11")
print("=" * 80)

# Login
print("\n[*] Logging in as student...")
stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
print(f"    Student PUID: {stu_puid}")
if not stu_puid:
    stu_puid = "431407443"

print("\n[*] Logging in as teacher...")
tea_session, tea_puid = login("19712720708", "3.1415926Cpy")
print(f"    Teacher PUID: {tea_puid}")
if not tea_puid:
    tea_puid = "402644510"

# ============================================================
# 1. contestyd.chaoxing.com - Has /v2/apis/sign/signIn returning JSON
# ============================================================
print("\n" + "=" * 80)
print("1. contestyd.chaoxing.com - /v2/apis/sign/signIn returns JSON")
print("=" * 80)

domain = "contestyd.chaoxing.com"
sign_params = get_sign_params(stu_puid)

# Test with student - GET
print("\n[Student] GET /v2/apis/sign/signIn")
try:
    r = stu_session.get(f"https://{domain}/v2/apis/sign/signIn", params=sign_params, timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Headers: {dict(r.headers)}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# Test with student - POST
print("\n[Student] POST /v2/apis/sign/signIn")
try:
    r = stu_session.post(f"https://{domain}/v2/apis/sign/signIn", data=sign_params, timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# Test with student - POST JSON
print("\n[Student] POST JSON /v2/apis/sign/signIn")
try:
    r = stu_session.post(f"https://{domain}/v2/apis/sign/signIn", json=sign_params, timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# Test with teacher
print("\n[Teacher] GET /v2/apis/sign/signIn")
try:
    r = tea_session.get(f"https://{domain}/v2/apis/sign/signIn", params=get_sign_params(tea_puid), timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# Explore more paths on contestyd
print("\n[Exploring more paths on contestyd.chaoxing.com]")
extra_paths = [
    "/v2/apis/sign/",
    "/v2/apis/",
    "/v2/",
    "/api/",
    "/api/sign/",
    "/pptSign/stuSignajax",
    "/pptSign/updateSignStatus",
    "/newsign/updateSignStatus",
    "/widget/sign/pcTeaSignController/updateSignStatus2",
]
for path in extra_paths:
    try:
        r = stu_session.get(f"https://{domain}{path}", params=sign_params, timeout=8, verify=False)
        if r.status_code != 404:
            print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except:
        pass

# ============================================================
# 2. ss.zhizhen.com - Has sign-in endpoints returning 401
# ============================================================
print("\n" + "=" * 80)
print("2. ss.zhizhen.com - Sign-in endpoints returning 401")
print("=" * 80)

domain = "ss.zhizhen.com"

# Test with student session (ChaoXing cookies)
for path in ["/pptSign/updateSignStatus", "/pptSign/stuSignajax", "/newsign/updateSignStatus"]:
    print(f"\n[Student] GET {path}")
    try:
        r = stu_session.get(f"https://{domain}{path}", params=sign_params, timeout=15, verify=False)
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:300]}")
    except Exception as e:
        print(f"  Error: {e}")

# Try with Zhizhen login redirect
print("\n[Student] Following login redirect...")
try:
    r = stu_session.get(f"https://{domain}/pptSign/stuSignajax", params=sign_params, timeout=15, verify=False, allow_redirects=True)
    print(f"  Final URL: {r.url}")
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# Test auth.zhizhen.com
print("\n[*] Testing auth.zhizhen.com")
try:
    r = stu_session.get("https://auth.zhizhen.com/", timeout=10, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 3. ss.chaoxing.com - All paths return 302 redirects
# ============================================================
print("\n" + "=" * 80)
print("3. ss.chaoxing.com - All paths return 302 redirects")
print("=" * 80)

domain = "ss.chaoxing.com"

# Follow redirects
print("\n[Student] GET /pptSign/stuSignajax (follow redirects)")
try:
    r = stu_session.get(f"https://{domain}/pptSign/stuSignajax", params=sign_params, timeout=15, verify=False, allow_redirects=True)
    print(f"  Final URL: {r.url}")
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# Check redirect location without following
print("\n[Student] GET /pptSign/stuSignajax (no redirect)")
try:
    r = stu_session.get(f"https://{domain}/pptSign/stuSignajax", params=sign_params, timeout=15, verify=False, allow_redirects=False)
    print(f"  Status: {r.status_code}")
    print(f"  Location: {r.headers.get('Location', 'N/A')}")
except Exception as e:
    print(f"  Error: {e}")

# Test with teacher
print("\n[Teacher] GET /pptSign/updateSignStatus (follow redirects)")
try:
    r = tea_session.get(f"https://{domain}/pptSign/updateSignStatus", params=get_sign_params(tea_puid), timeout=15, verify=False, allow_redirects=True)
    print(f"  Final URL: {r.url}")
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 4. vspace.chaoxing.com - Returns HTML for GET, JSON for POST
# ============================================================
print("\n" + "=" * 80)
print("4. vspace.chaoxing.com - GET returns HTML, POST returns JSON")
print("=" * 80)

domain = "vspace.chaoxing.com"

# POST with sign params
print("\n[Student] POST /pptSign/updateSignStatus")
try:
    r = stu_session.post(f"https://{domain}/pptSign/updateSignStatus", data=sign_params, timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# POST with JSON
print("\n[Student] POST JSON /pptSign/updateSignStatus")
try:
    r = stu_session.post(f"https://{domain}/pptSign/updateSignStatus", json=sign_params, timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 5. x.chaoxing.com - /v2/apis/sign/signIn returns 500
# ============================================================
print("\n" + "=" * 80)
print("5. x.chaoxing.com - /v2/apis/sign/signIn returns 500")
print("=" * 80)

domain = "x.chaoxing.com"

print("\n[Student] GET /v2/apis/sign/signIn")
try:
    r = stu_session.get(f"https://{domain}/v2/apis/sign/signIn", params=sign_params, timeout=15, verify=False)
    print(f"  Status: {r.status_code}")
    print(f"  Body: {r.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# Explore more on x.chaoxing.com
extra_x_paths = [
    "/v2/apis/", "/v2/", "/api/", "/api/sign/", "/pptSign/", 
    "/pptSign/stuSignajax", "/newsign/", "/widget/sign/",
]
print("\n[Exploring x.chaoxing.com]")
for path in extra_x_paths:
    try:
        r = stu_session.get(f"https://{domain}{path}", timeout=8, verify=False)
        if r.status_code not in (404, 403, 0):
            print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except:
        pass

# ============================================================
# 6. passport2.chaoxing.com - Authentication domain
# ============================================================
print("\n" + "=" * 80)
print("6. passport2.chaoxing.com - Authentication domain")
print("=" * 80)

domain = "passport2.chaoxing.com"

# Test sign-in paths on passport2
print("\n[Student] Testing sign paths on passport2")
for path in ["/pptSign/updateSignStatus", "/newsign/updateSignStatus", "/v2/apis/sign/signIn"]:
    try:
        r = stu_session.get(f"https://{domain}{path}", params=sign_params, timeout=8, verify=False, allow_redirects=False)
        print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  GET {path} -> Error: {e}")

# ============================================================
# 7. sso.chaoxing.com - SSO domain
# ============================================================
print("\n" + "=" * 80)
print("7. sso.chaoxing.com - SSO domain")
print("=" * 80)

domain = "sso.chaoxing.com"

# Test SSO specific paths
sso_paths = [
    "/api/", "/login", "/logout", "/auth", "/sso/", "/cas/",
    "/pptSign/stuSignajax", "/v2/apis/sign/signIn",
]
print("\n[Student] Testing SSO paths")
for path in sso_paths:
    try:
        r = stu_session.get(f"https://{domain}{path}", timeout=8, verify=False, allow_redirects=False)
        if r.status_code not in (404, 0):
            print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except:
        pass

# ============================================================
# 8. intellectual-education-k8s.chaoxing.com
# ============================================================
print("\n" + "=" * 80)
print("8. intellectual-education-k8s.chaoxing.com - K8s deployment")
print("=" * 80)

domain = "intellectual-education-k8s.chaoxing.com"

for scheme in ["http", "https"]:
    try:
        r = stu_session.get(f"{scheme}://{domain}/", timeout=10, verify=False)
        print(f"  {scheme}:// root -> {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  {scheme}:// root -> Error: {e}")

# ============================================================
# 9. jcxygl.chaoxing.com - Educational administration
# ============================================================
print("\n" + "=" * 80)
print("9. jcxygl.chaoxing.com - Educational administration")
print("=" * 80)

domain = "jcxygl.chaoxing.com"

edu_paths = ["/", "/api/", "/sign/", "/pptSign/stuSignajax", "/v2/apis/sign/signIn"]
for path in edu_paths:
    try:
        r = stu_session.get(f"https://{domain}{path}", timeout=8, verify=False, allow_redirects=False)
        print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  GET {path} -> Error: {e}")

# ============================================================
# 10. jwdatatb.chaoxing.com - Educational data
# ============================================================
print("\n" + "=" * 80)
print("10. jwdatatb.chaoxing.com - Educational data")
print("=" * 80)

domain = "jwdatatb.chaoxing.com"

for path in ["/", "/api/", "/sign/", "/pptSign/stuSignajax"]:
    try:
        r = stu_session.get(f"https://{domain}{path}", timeout=8, verify=False, allow_redirects=False)
        print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  GET {path} -> Error: {e}")

# ============================================================
# 11. ketang-zhizhen.chaoxing.com - Classroom Zhizhen
# ============================================================
print("\n" + "=" * 80)
print("11. ketang-zhizhen.chaoxing.com - Classroom Zhizhen")
print("=" * 80)

domain = "ketang-zhizhen.chaoxing.com"

for path in ["/", "/api/", "/sign/", "/pptSign/stuSignajax", "/v2/apis/sign/signIn"]:
    try:
        r = stu_session.get(f"https://{domain}{path}", timeout=8, verify=False, allow_redirects=False)
        print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  GET {path} -> Error: {e}")

# ============================================================
# 12. wx.chaoxing.com - WeChat domain
# ============================================================
print("\n" + "=" * 80)
print("12. wx.chaoxing.com - WeChat domain")
print("=" * 80)

domain = "wx.chaoxing.com"

for path in ["/", "/api/", "/sign/", "/pptSign/stuSignajax", "/v2/apis/sign/signIn"]:
    try:
        r = stu_session.get(f"https://{domain}{path}", timeout=8, verify=False, allow_redirects=False)
        print(f"  GET {path} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  GET {path} -> Error: {e}")

print("\n" + "=" * 80)
print("Deep dive complete!")
print("=" * 80)
