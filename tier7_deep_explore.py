#!/usr/bin/env python3
"""Tier 7 - Deep exploration of api.im.chaoxing.com HTTP endpoints"""

import base64, hashlib, json, uuid, requests, urllib3
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

def main():
    print("=" * 80)
    print("Tier 7 - Deep Exploration: api.im.chaoxing.com (HTTP)")
    print("=" * 80)

    stu_session, stu_puid = login("18436633997", "3.1415926Cpy")
    print(f"Student PUID: {stu_puid}")
    uid = stu_puid or "431407443"

    base = "http://api.im.chaoxing.com"

    # The base page revealed: /verifiable/chat?rid=60
    # Let's explore this and related paths
    deep_paths = [
        # From base page discovery
        "/verifiable/chat",
        "/verifiable/chat?rid=60",
        "/verifiable",
        # Chat-related
        "/chat",
        "/chat/list",
        "/chat/send",
        "/chat/history",
        "/chat/conversation",
        # API chat
        "/api/chat/list",
        "/api/chat/send",
        "/api/chat/history",
        # V1 chat
        "/v1/chat/list",
        "/v1/chat/send",
        "/v1/chat/history",
        # Verifiable endpoints
        "/verifiable/list",
        "/verifiable/send",
        "/verifiable/message",
        # IM specific
        "/im/verifiable/chat",
        "/im/verifiable/list",
        # Sign on IM domain (HTTP)
        "/pptSign/updateSignStatus",
        "/pptSign/stuSignajax",
        "/newsign/updateSignStatus",
        "/sign/updateSignStatus",
        "/api/sign/updateSignStatus",
        "/v2/apis/sign/signIn",
        # WebSocket-like
        "/ws",
        "/websocket",
        "/socket.io",
        # API endpoints
        "/api",
        "/api/v1",
        "/api/v2",
        "/v1",
        "/v2",
        # User info on IM
        "/api/user/info",
        "/api/user/getUserInfo",
        "/v1/user/info",
        # Contact
        "/api/contact/list",
        "/api/contact/search",
        "/v1/contact/list",
        # Message
        "/api/message/list",
        "/api/message/unread",
        "/v1/message/list",
        # Notice
        "/api/notice/list",
        "/api/notice/unread",
        # Group
        "/api/group/list",
        "/api/group/create",
        # Common
        "/health",
        "/actuator",
        "/swagger-ui.html",
        "/doc.html",
        "/favicon.ico",
    ]

    sign_params = {
        "activeId": "5000163891319",
        "uid": uid,
        "courseId": "257485372",
        "classId": "132821141",
        "signType": "0",
        "clientType": "1",
    }

    findings = []

    for path in deep_paths:
        for method in ["GET", "POST"]:
            url = base + path
            try:
                if method == "GET":
                    r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=False, verify=False)
                else:
                    r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=False, verify=False)

                status = r.status_code
                body = r.text[:800] if r.text else ""
                ct = r.headers.get("Content-Type", "")

                # Skip 404 and HTML error pages
                if status == 404:
                    continue
                if status in (400, 500) and body.strip().startswith("<!doctype"):
                    continue

                is_interesting = False
                severity = "LOW"

                # Check for interesting content
                bl = body.lower()
                if any(k in bl for k in ["sign", "签到", "success", "result", "chat", "message", "user", "contact", "notice", "verifiable", "conversation", "group"]):
                    is_interesting = True
                    severity = "MEDIUM"
                    if any(k in bl for k in ["success", "已签到", "签到成功", "\"result\":true"]):
                        if "update" in path.lower() or "sign" in path.lower():
                            severity = "CRITICAL"
                        else:
                            severity = "HIGH"

                if not is_interesting and not body.strip().startswith("<!doctype") and not body.strip().startswith("<html") and body.strip():
                    is_interesting = True

                if is_interesting or status not in (400, 500, 502, 503):
                    entry = {
                        "path": path,
                        "method": method,
                        "status": status,
                        "content_type": ct,
                        "severity": severity,
                        "body_preview": body[:500],
                    }
                    findings.append(entry)
                    marker = "🚨" if severity == "CRITICAL" else ("⚠️" if severity == "HIGH" else ("📌" if severity == "MEDIUM" else "ℹ️"))
                    print(f"  {marker} [{method}] {path} -> {status} [{severity}] CT: {ct}")
                    print(f"     响应: {body[:200]}")

                if status in (301, 302, 303, 307, 308):
                    loc = r.headers.get("Location", "")
                    print(f"  🔀 REDIRECT: [{method}] {path} -> {loc}")

            except Exception as e:
                pass

    print(f"\n{'=' * 60}")
    print(f"发现总结: {len(findings)} 个有趣端点")
    for f in findings:
        print(f"  [{f['method']}] {f['path']} -> {f['status']} [{f['severity']}]")
        print(f"    {f['body_preview'][:150]}")

    # Also test contactsyd.chaoxing.com more deeply
    print(f"\n{'=' * 60}")
    print("Deep Exploration: contactsyd.chaoxing.com")
    print(f"{'=' * 60}")

    base2 = "https://contactsyd.chaoxing.com"
    contacts_paths = [
        "/contacts/list",
        "/contacts/search",
        "/contacts/getContacts",
        "/api/contacts/list",
        "/api/contacts/search",
        "/api/contacts/getContacts",
        "/v1/contacts/list",
        "/v1/contacts/search",
        "/v1/contacts/getContacts",
        "/user/getUserInfo",
        "/user/info",
        "/api/user/info",
        "/sign/updateSignStatus",
        "/pptSign/updateSignStatus",
        "/pptSign/stuSignajax",
        "/health",
        "/actuator",
    ]

    for path in contacts_paths:
        for method in ["GET", "POST"]:
            url = base2 + path
            try:
                if method == "GET":
                    r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=False, verify=False)
                else:
                    r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=False, verify=False)

                status = r.status_code
                body = r.text[:500] if r.text else ""

                if status == 404:
                    continue
                if status in (400, 500) and body.strip().startswith("<!doctype"):
                    continue

                bl = body.lower()
                is_interesting = any(k in bl for k in ["sign", "签到", "success", "contact", "user", "result", "message"])
                if not is_interesting and not body.strip().startswith("<!doctype") and body.strip():
                    is_interesting = True

                if is_interesting:
                    print(f"  📌 [{method}] {path} -> {status}")
                    print(f"     响应: {body[:200]}")

            except:
                pass

    # Test im.chaoxing.com more deeply (HTTPS)
    print(f"\n{'=' * 60}")
    print("Deep Exploration: im.chaoxing.com (HTTPS)")
    print(f"{'=' * 60}")

    base3 = "https://im.chaoxing.com"
    im_deep_paths = [
        "/api/user/info",
        "/api/chat/list",
        "/api/chat/send",
        "/api/contact/list",
        "/api/contact/search",
        "/api/message/list",
        "/api/group/list",
        "/api/notice/list",
        "/verifiable/chat",
        "/verifiable/chat?rid=60",
        "/v1/user/info",
        "/v1/chat/list",
        "/v1/contact/list",
        "/v1/message/list",
        "/sign/updateSignStatus",
        "/pptSign/updateSignStatus",
        "/pptSign/stuSignajax",
    ]

    for path in im_deep_paths:
        for method in ["GET", "POST"]:
            url = base3 + path
            try:
                if method == "GET":
                    r = stu_session.get(url, params=sign_params, timeout=15, allow_redirects=False, verify=False)
                else:
                    r = stu_session.post(url, data=sign_params, timeout=15, allow_redirects=False, verify=False)

                status = r.status_code
                body = r.text[:500] if r.text else ""

                if status == 404:
                    continue
                if status in (400, 500) and body.strip().startswith("<!doctype"):
                    continue

                bl = body.lower()
                is_interesting = any(k in bl for k in ["sign", "签到", "success", "contact", "user", "result", "message", "chat", "im"])
                if not is_interesting and not body.strip().startswith("<!doctype") and body.strip():
                    is_interesting = True

                if is_interesting:
                    print(f"  📌 [{method}] {path} -> {status}")
                    print(f"     响应: {body[:200]}")

            except:
                pass

if __name__ == "__main__":
    main()
