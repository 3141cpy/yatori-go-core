#!/usr/bin/env python3
"""Explore sign-in related APIs on first-tier ChaoXing domains."""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ── Config ──────────────────────────────────────────────────────────────────
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"
STU_PHONE = "18436633997"
STU_PWD = "3.1415926Cpy"
TEA_PHONE = "19712720708"
TEA_PWD = "3.1415926Cpy"

PC_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# ── Helper functions ────────────────────────────────────────────────────────
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

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def preview(text, maxlen=200):
    t = text.replace('\n', ' ').replace('\r', '')
    return t[:maxlen] + ('...' if len(t) > maxlen else '')

# ── Domain definitions ──────────────────────────────────────────────────────
DOMAINS = {
    "statisticyd.chaoxing.com": {
        "label": "GroupStatisticsDomain (统计域)",
        "paths": [
            "/sign/statistics", "/sign/detail", "/sign/list", "/sign/updateStatus",
            "/api/sign/statistics", "/api/sign/detail", "/api/sign/list",
            "/statistics/sign", "/statistics/signDetail",
            "/groupsign/list", "/group/sign/list",
            "/mooc-ans/sign/statistics", "/mooc-ans/pptSign/updateSignStatus",
            "/mooc-ans/newsign/updateSignStatus",
            "/mooc-ans/sign/updateSignStatus",
            "/pptSign/updateSignStatus", "/pptSign/stuSignajax",
            "/pptSign/updateSignStatusByUidsV2", "/pptSign/refeashSignList4Json2",
            "/newsign/updateSignStatus",
            "/v2/apis/sign/signIn",
            "/widget/sign/pcTeaSignController/updateSignStatus2",
        ]
    },
    "k.chaoxing.com": {
        "label": "ktDomain (课堂域)",
        "paths": [
            "/pptSign/updateSignStatus", "/pptSign/stuSignajax",
            "/pptSign/updateSignStatusByUidsV2", "/pptSign/refeashSignList4Json2",
            "/sign/updateStatus", "/sign/list", "/sign/detail",
            "/ktSign/updateStatus", "/ktSign/list",
            "/classroom/sign/list", "/classroom/sign/updateStatus",
            "/widget/sign/pcTeaSignController/updateSignStatus2",
            "/newsign/updateSignStatus",
            "/v2/apis/sign/signIn",
            "/api/sign/updateSignStatus", "/api/sign/list",
            "/v2/apis/sign/updateSignStatus",
        ]
    },
    "study-api.chaoxing.com": {
        "label": "studyApiDomain (学习API域)",
        "paths": [
            "/sign/updateStatus", "/sign/list", "/sign/detail",
            "/api/sign/updateSignStatus", "/api/sign/list",
            "/mooc-ans/sign/updateSignStatus", "/mooc-ans/pptSign/updateSignStatus",
            "/mooc-ans/newsign/updateSignStatus",
            "/v2/apis/sign/signIn", "/v2/apis/sign/updateSignStatus",
            "/pptSign/updateSignStatus", "/pptSign/stuSignajax",
            "/pptSign/refeashSignList4Json2",
            "/newsign/updateSignStatus",
            "/widget/sign/pcTeaSignController/updateSignStatus2",
        ]
    },
    "office.chaoxing.com": {
        "label": "officeDomain (办公域)",
        "paths": [
            "/front/sign/signIn", "/front/sign/updateSignStatus",
            "/front/sign/list", "/front/sign/detail",
            "/widget/sign/pcTeaSignController/updateSignStatus2",
            "/pptSign/updateSignStatus", "/pptSign/stuSignajax",
            "/pptSign/updateSignStatusByUidsV2", "/pptSign/refeashSignList4Json2",
            "/newsign/updateSignStatus",
            "/api/sign/updateSignStatus", "/api/sign/list",
            "/v2/apis/sign/signIn",
            "/sign/updateStatus", "/sign/list",
        ]
    },
    "task.chaoxing.com": {
        "label": "taskHttps (任务域)",
        "paths": [
            "/sign/updateStatus", "/sign/list", "/sign/detail",
            "/api/sign/updateSignStatus", "/api/sign/list",
            "/task/sign/updateStatus", "/task/sign/list",
            "/pptSign/updateSignStatus", "/pptSign/stuSignajax",
            "/pptSign/refeashSignList4Json2",
            "/newsign/updateSignStatus",
            "/v2/apis/sign/signIn",
            "/widget/sign/pcTeaSignController/updateSignStatus2",
        ]
    },
}

# ── Common sign-in params ───────────────────────────────────────────────────
def sign_params(uid):
    return {
        "activeId": ACTIVE_ID,
        "uid": uid,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
    }

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("ChaoXing 一级域 Sign-in API 探测")
    print("=" * 80)

    # Login both accounts
    print("\n[1] 登录学生账号...")
    stu_session, stu_puid = login(STU_PHONE, STU_PWD)
    print(f"    学生PUID: {stu_puid or '未获取到'}")

    print("[2] 登录教师账号...")
    tea_session, tea_puid = login(TEA_PHONE, TEA_PWD)
    print(f"    教师PUID: {tea_puid or '未获取到'}")

    if not stu_puid and not tea_puid:
        print("!!! 两个账号均登录失败，退出")
        sys.exit(1)

    # Results tracking
    alive_domains = {}
    found_endpoints = []
    critical_endpoints = []

    for domain, cfg in DOMAINS.items():
        label = cfg["label"]
        paths = cfg["paths"]
        base = f"https://{domain}"

        print(f"\n{'=' * 80}")
        print(f"▶ 探测域: {domain} ({label})")
        print(f"{'=' * 80}")

        # 1) Base URL accessibility
        print(f"\n  --- 基础连通性测试 ---")
        domain_alive = False
        for ua_label, ua_val in [("Mobile", get_mobile_ua()), ("PC", PC_UA)]:
            try:
                r = requests.get(base + "/", headers={"User-Agent": ua_val},
                                 verify=False, timeout=15, allow_redirects=True)
                domain_alive = True
                print(f"  [{domain}] GET / ({ua_label} UA) -> {r.status_code} | {preview(r.text, 150)}")
            except requests.exceptions.ConnectionError as e:
                err_msg = str(e)[:100]
                print(f"  [{domain}] GET / ({ua_label} UA) -> CONNECTION_REFUSED | {err_msg}")
            except requests.exceptions.Timeout:
                print(f"  [{domain}] GET / ({ua_label} UA) -> TIMEOUT")
            except Exception as e:
                print(f"  [{domain}] GET / ({ua_label} UA) -> ERROR: {type(e).__name__}: {str(e)[:80]}")

        if domain_alive:
            print(f"  !!!ALIVE!!! {domain} 可达")
            alive_domains[domain] = {"label": label, "endpoints": []}
        else:
            print(f"  ✗ {domain} 不可达，跳过路径探测")
            continue

        # 2) Path exploration with student & teacher sessions
        for role, session, puid in [("STU", stu_session, stu_puid), ("TEA", tea_session, tea_puid)]:
            if not puid:
                print(f"\n  --- {role} 跳过（未登录）---")
                continue

            print(f"\n  --- {role} (puid={puid}) 路径探测 ---")
            params = sign_params(puid)

            for path in paths:
                url = base + path
                # GET request
                for method in ["GET", "POST"]:
                    try:
                        if method == "GET":
                            r = session.get(url, params=params, timeout=15, allow_redirects=False, verify=False)
                        else:
                            r = session.post(url, data=params, timeout=15, allow_redirects=False, verify=False)

                        status = r.status_code
                        text_preview = preview(r.text, 180)

                        # Determine markers
                        markers = []
                        if status in (200, 201, 202):
                            # Check if response contains sign-in data
                            try:
                                j = r.json()
                                if isinstance(j, dict):
                                    if j.get("result") == 1 or j.get("result") is True:
                                        markers.append("!!!FOUND!!!")
                                        found_endpoints.append(f"{domain}{path} ({role} {method})")
                                        alive_domains[domain]["endpoints"].append(f"{method} {path} [{role}]")
                                    # Check if student can modify sign status
                                    if role == "STU" and "updateSignStatus" in path and j.get("result") in (1, True):
                                        markers.append("!!!CRITICAL!!!")
                                        critical_endpoints.append(f"{domain}{path} (STU {method})")
                                    # Also check for data fields
                                    if any(k in str(j).lower() for k in ["signdetail", "signlist", "statuslist", "signstatus"]):
                                        if "!!!FOUND!!!" not in markers:
                                            markers.append("!!!FOUND!!!")
                                            found_endpoints.append(f"{domain}{path} ({role} {method})")
                                            alive_domains[domain]["endpoints"].append(f"{method} {path} [{role}]")
                            except:
                                pass
                            # Check non-JSON sign data
                            if any(kw in r.text.lower() for kw in ["signstatus", "signdetail", "签到", "签到列表"]):
                                if "!!!FOUND!!!" not in markers:
                                    markers.append("!!!FOUND!!!")
                                    found_endpoints.append(f"{domain}{path} ({role} {method})")
                                    alive_domains[domain]["endpoints"].append(f"{method} {path} [{role}]")

                        elif status in (301, 302, 303, 307, 308):
                            loc = r.headers.get("Location", "?")
                            text_preview = f"Redirect -> {loc[:120]}"
                        elif status == 404:
                            pass  # silent skip
                        elif status == 403:
                            markers.append("FORBIDDEN")

                        marker_str = " ".join(markers)
                        if status != 404 or markers:  # Only print 404 if it has markers
                            print(f"  [{domain}] {method} {path} ({role}) -> {status} | {text_preview} {marker_str}")

                    except requests.exceptions.ConnectionError:
                        pass  # Skip silently for path-level connection errors
                    except requests.exceptions.Timeout:
                        print(f"  [{domain}] {method} {path} ({role}) -> TIMEOUT")
                    except Exception as e:
                        print(f"  [{domain}] {method} {path} ({role}) -> ERROR: {type(e).__name__}: {str(e)[:60]}")

        # Also try with PC UA for key paths
        if domain_alive and tea_puid:
            print(f"\n  --- TEA (PC UA) 关键路径探测 ---")
            pc_session = requests.Session()
            pc_session.verify = False
            # Copy cookies from teacher session
            for c in tea_session.cookies:
                pc_session.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
            pc_session.headers.update({"User-Agent": PC_UA, "Accept": "application/json, text/plain, */*"})

            key_paths = [p for p in paths if any(kw in p for kw in ["updateSignStatus", "refeashSignList", "stuSignajax", "signIn"])]
            params = sign_params(tea_puid)

            for path in key_paths:
                url = base + path
                for method in ["GET", "POST"]:
                    try:
                        if method == "GET":
                            r = pc_session.get(url, params=params, timeout=15, allow_redirects=False, verify=False)
                        else:
                            r = pc_session.post(url, data=params, timeout=15, allow_redirects=False, verify=False)

                        status = r.status_code
                        text_preview = preview(r.text, 180)
                        markers = []

                        if status in (200, 201, 202):
                            try:
                                j = r.json()
                                if isinstance(j, dict) and (j.get("result") == 1 or j.get("result") is True):
                                    markers.append("!!!FOUND!!!")
                                    found_endpoints.append(f"{domain}{path} (TEA-PC {method})")
                                    alive_domains[domain]["endpoints"].append(f"{method} {path} [TEA-PC]")
                            except:
                                pass
                        elif status in (301, 302, 303, 307, 308):
                            loc = r.headers.get("Location", "?")
                            text_preview = f"Redirect -> {loc[:120]}"
                        elif status == 403:
                            markers.append("FORBIDDEN")

                        marker_str = " ".join(markers)
                        if status != 404 or markers:
                            print(f"  [{domain}] {method} {path} (TEA-PC) -> {status} | {text_preview} {marker_str}")

                    except requests.exceptions.ConnectionError:
                        pass
                    except requests.exceptions.Timeout:
                        print(f"  [{domain}] {method} {path} (TEA-PC) -> TIMEOUT")
                    except Exception as e:
                        print(f"  [{domain}] {method} {path} (TEA-PC) -> ERROR: {type(e).__name__}: {str(e)[:60]}")

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n\n{'=' * 80}")
    print("探测结果汇总")
    print(f"{'=' * 80}")

    print(f"\n可达域 ({len(alive_domains)}):")
    if alive_domains:
        for domain, info in alive_domains.items():
            ep_count = len(info["endpoints"])
            print(f"  !!!ALIVE!!! {domain} ({info['label']}) - 有效端点: {ep_count}")
            for ep in info["endpoints"]:
                print(f"      • {ep}")
    else:
        print("  无可达域")

    print(f"\n有效Sign-in端点 ({len(found_endpoints)}):")
    if found_endpoints:
        for ep in found_endpoints:
            print(f"  !!!FOUND!!! {ep}")
    else:
        print("  无有效端点")

    print(f"\n学生可修改签到状态端点 ({len(critical_endpoints)}):")
    if critical_endpoints:
        for ep in critical_endpoints:
            print(f"  !!!CRITICAL!!! {ep}")
    else:
        print("  无（学生无法修改签到状态）")

    print(f"\n{'=' * 80}")
    print("探测完成")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
