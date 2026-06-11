#!/usr/bin/env python3
"""
Tier 6 - Follow-up: Track 302 redirects on mh.chaoxing.com and test HTTP paths
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

FE_PATHS = [
    "/sign/updateSignStatus",
    "/sign/stuSignajax",
    "/api/sign/updateSignStatus",
    "/page/sign/updateSignStatus",
    "/widget/sign/updateSignStatus",
]

def trunc(text, maxlen=500):
    t = text.replace('\n', ' ').replace('\r', '')
    return t[:maxlen] + "..." if len(t) > maxlen else t

def main():
    print("=" * 80)
    print("Tier 6 - Follow-up: 302 Redirects & HTTP Path Testing")
    print("=" * 80)

    # Login as student
    print("\n[*] Logging in as student...")
    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"    Student PUID: {stu_puid}")
    sign_params = get_sign_params(stu_puid)

    # ── Part 1: Follow 302 redirects on mh.chaoxing.com ────────────
    print(f"\n{'=' * 80}")
    print("[*] Part 1: Following 302 redirects on mh.chaoxing.com")
    print(f"{'=' * 80}")

    all_paths = list(COMMON_SIGN_PATHS) + FE_PATHS
    seen = set()
    unique_paths = []
    for p in all_paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)

    for path in unique_paths:
        for method in ["GET", "POST"]:
            url = f"https://mh.chaoxing.com{path}"
            try:
                if method == "GET":
                    r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=True)
                else:
                    r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=True)

                # Show redirect chain
                if len(r.history) > 0:
                    chain = " -> ".join([f"{resp.status_code}@{resp.headers.get('Location','?')[:80]}" for resp in r.history])
                    print(f"  [{method}] {url}")
                    print(f"    Redirect chain: {chain}")
                    print(f"    Final: {r.status_code} @ {r.url}")
                    print(f"    Body: {trunc(r.text, 300)}")
                else:
                    print(f"  [{method}] {url} -> {r.status_code} (no redirect)")
                    print(f"    Body: {trunc(r.text, 300)}")
            except Exception as e:
                print(f"  [{method}] {url} -> ERROR: {type(e).__name__}: {e}")

    # ── Part 2: Test HTTP (non-SSL) on domains that had SSL issues ─
    print(f"\n{'=' * 80}")
    print("[*] Part 2: Testing HTTP paths on apps.ananas.chaoxing.com & cs-api.chaoxing.com")
    print(f"{'=' * 80}")

    for dom in ["apps.ananas.chaoxing.com", "cs-api.chaoxing.com"]:
        print(f"\n  --- {dom} ---")
        for path in unique_paths:
            url = f"http://{dom}{path}"
            for method in ["GET", "POST"]:
                try:
                    if method == "GET":
                        r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=False)
                    else:
                        r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=False)

                    if r.status_code not in (404, 502):
                        print(f"  [FOUND] {method} {url} -> {r.status_code}")
                        print(f"    Body: {trunc(r.text, 300)}")
                except requests.exceptions.ConnectionError:
                    pass
                except Exception as e:
                    print(f"  [ERROR] {method} {url} -> {type(e).__name__}: {e}")

    # ── Part 3: Test HTTP on apps.chaoxing.com, appswh.chaoxing.com, resource.chaoxing.com ─
    print(f"\n{'=' * 80}")
    print("[*] Part 3: Testing HTTP paths on apps/appswh/resource domains")
    print(f"{'=' * 80}")

    APPS_PATHS = [
        "/app/sign/updateSignStatus",
        "/app/pptSign/updateSignStatus",
        "/course/sign/updateSignStatus",
        "/course/pptSign/updateSignStatus",
    ]

    for dom in ["apps.chaoxing.com", "appswh.chaoxing.com", "resource.chaoxing.com"]:
        print(f"\n  --- {dom} ---")
        test_paths = unique_paths + APPS_PATHS
        for path in test_paths:
            url = f"http://{dom}{path}"
            for method in ["GET", "POST"]:
                try:
                    if method == "GET":
                        r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=False)
                    else:
                        r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=False)

                    if r.status_code not in (404,):
                        print(f"  [FOUND] {method} {url} -> {r.status_code}")
                        print(f"    Body: {trunc(r.text, 300)}")
                except requests.exceptions.ConnectionError:
                    pass
                except Exception as e:
                    print(f"  [ERROR] {method} {url} -> {type(e).__name__}: {e}")

    print(f"\n{'=' * 80}")
    print("END OF FOLLOW-UP REPORT")
    print("=" * 80)

if __name__ == "__main__":
    main()
