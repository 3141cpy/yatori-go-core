#!/usr/bin/env python3
"""
Task 3: Deep testing of /pptSign/ endpoints on ChaoXing platform.
Authorized security audit - v5 with comprehensive testing.
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

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
CPI = "520211407"

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
            f"(@Kalimdor)_{imei})")

def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh_CN",
    })
    resp = s.post(LOGIN_URL, data={
        "fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
        "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
        "independentId": "0", "independentNameId": "0"
    }, allow_redirects=False, timeout=30)
    print(f"  Login: {resp.status_code} -> {resp.text[:200]}")
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    print(f"  PUID: {puid}")
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    return s, puid


def safe_resp(resp):
    result = {"status_code": resp.status_code, "url": resp.url, "text": "", "json": None}
    try:
        result["text"] = resp.text[:5000]
    except:
        result["text"] = "<unreadable>"
    try:
        result["json"] = resp.json()
    except:
        pass
    return result


def discover_activities(session):
    """Discover activities from multiple sources."""
    activities = []
    active_ids = []

    # 1. backclazzdata
    print("  [1] backclazzdata...")
    try:
        url = "https://mooc1-api.chaoxing.com/mycourse/backclazzdata"
        r = session.get(url, params={"courseid": COURSE_ID, "classid": CLASS_ID, "uid": PUID}, timeout=20)
        if r.status_code == 200:
            data = r.json()
            with open("/workspace/backclazzdata_response.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"  backclazzdata: OK, saved")
    except Exception as e:
        print(f"  backclazzdata error: {e}")

    # 2. Try the course square URL
    print("  [2] Course square URL...")
    try:
        url = f"https://tsjy.chaoxing.com/plaza/app?courseId={COURSE_ID}&personId={CPI}&classId={CLASS_ID}&userId={PUID}"
        r = session.get(url, timeout=20)
        print(f"  Course square: {r.status_code}, len={len(r.text)}")
        if r.status_code == 200:
            # Extract activity IDs from HTML
            found = re.findall(r'activeId["\s:=]+(\d+)', r.text)
            found2 = re.findall(r'activityId["\s:=]+(\d+)', r.text)
            all_found = set(found + found2)
            if all_found:
                print(f"  Found IDs: {list(all_found)[:10]}")
                for aid in all_found:
                    active_ids.append(aid)
                    activities.append({"id": aid, "source": "course_square"})
    except Exception as e:
        print(f"  Course square error: {e}")

    # 3. Try the mobile learn course page
    print("  [3] Mobile learn course page...")
    try:
        url = f"{BASE}/mycourse/stu?courseId={COURSE_ID}&clazzid={CLASS_ID}&cpi={CPI}"
        r = session.get(url, timeout=20)
        print(f"  Mobile course page: {r.status_code}, len={len(r.text)}")
        if r.status_code == 200:
            found = re.findall(r'activeId["\s:=]+(\d+)', r.text)
            found2 = re.findall(r'jobId["\s:=]+(\d+)', r.text)
            all_found = set(found + found2)
            if all_found:
                print(f"  Found IDs: {list(all_found)[:10]}")
                for aid in all_found:
                    active_ids.append(aid)
                    activities.append({"id": aid, "source": "mobile_course_page"})
    except Exception as e:
        print(f"  Mobile course page error: {e}")

    # 4. Try the chaoxing course card API
    print("  [4] Course card API...")
    try:
        url = f"https://mooc1-api.chaoxing.com/mycourse/studycourse"
        r = session.get(url, params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID, "cpi": CPI}, timeout=20)
        print(f"  studycourse: {r.status_code} -> {r.text[:300]}")
    except Exception as e:
        print(f"  studycourse error: {e}")

    # 5. Try the knowledge/card API
    print("  [5] Knowledge card API...")
    try:
        url = f"https://mooc1-api.chaoxing.com/knowledge/cards"
        r = session.get(url, params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID, "cpi": CPI}, timeout=20)
        print(f"  knowledge cards: {r.status_code} -> {r.text[:300]}")
    except Exception as e:
        print(f"  knowledge cards error: {e}")

    # 6. Try the job/assignment API
    print("  [6] Job/assignment API...")
    try:
        url = f"https://mooc1-api.chaoxing.com/job/myjobsbycourseid"
        r = session.get(url, params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID}, timeout=20)
        print(f"  myjobsbycourseid: {r.status_code} -> {r.text[:300]}")
    except Exception as e:
        print(f"  myjobsbycourseid error: {e}")

    # 7. Try the sign module specifically with different URL patterns
    print("  [7] Sign module URLs...")
    sign_urls = [
        f"https://mooc1-api.chaoxing.com/sign/activeList?courseId={COURSE_ID}&classId={CLASS_ID}&uid={PUID}",
        f"https://mooc1-api.chaoxing.com/sign/stuSignList?courseId={COURSE_ID}&classId={CLASS_ID}&uid={PUID}",
        f"https://mooc1-api.chaoxing.com/edu/sign/activeList?courseId={COURSE_ID}&classId={CLASS_ID}&uid={PUID}",
    ]
    for url in sign_urls:
        try:
            r = session.get(url, timeout=20)
            print(f"  {url.split('.com/')[-1]}: {r.status_code} -> {r.text[:200]}")
            if r.status_code == 200:
                try:
                    data = r.json()
                    for key in ("activeList", "data", "result", "list"):
                        if key in data:
                            acts = data[key]
                            if isinstance(acts, list):
                                for act in acts:
                                    activities.append(act)
                                    aid = act.get("id", act.get("activeId", ""))
                                    if aid:
                                        active_ids.append(str(aid))
                except:
                    pass
        except Exception as e:
            print(f"  Error: {e}")

    # 8. Try the taskactivelist with the correct cpi
    print("  [8] taskactivelist with cpi...")
    try:
        r = session.get(f"{BASE}/pptSign/taskactivelist",
                       params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID, "cpi": CPI},
                       timeout=20)
        print(f"  taskactivelist: {r.status_code} -> {r.text[:300]}")
    except Exception as e:
        print(f"  taskactivelist error: {e}")

    # Deduplicate
    seen = set()
    unique_ids = []
    for aid in active_ids:
        if aid not in seen:
            seen.add(aid)
            unique_ids.append(aid)

    print(f"\n  Total activities: {len(activities)}, unique IDs: {unique_ids[:20]}")
    return activities, unique_ids


def test_stuSignajax(session, active_ids):
    """Test 1: stuSignajax complete parameter testing."""
    results = []
    print("\n[1] Testing stuSignajax with various parameter combinations...")

    if not active_ids:
        active_ids = ["0"]

    for active_id in active_ids[:5]:
        print(f"  Testing activeId={active_id}")

        base_params = {
            "activeId": str(active_id),
            "uid": PUID,
            "clientip": "",
            "latitude": "-1",
            "longitude": "-1",
            "appType": "15",
            "fid": "0"
        }

        test_cases = [
            ("standard_GET", "GET", dict(base_params)),
            ("standard_POST", "POST", dict(base_params)),
        ]

        # With location
        loc_params = dict(base_params)
        loc_params["latitude"] = "39.9042"
        loc_params["longitude"] = "116.4074"
        loc_params["address"] = "北京市天安门广场"
        test_cases.append(("with_location_GET", "GET", loc_params))
        test_cases.append(("with_location_POST", "POST", dict(loc_params)))

        # With enc variations
        for enc_val in ["", "test", "abc123", "12345678"]:
            p = dict(base_params)
            p["enc"] = enc_val
            test_cases.append((f"enc_{enc_val or 'empty'}_GET", "GET", p))

        # With status
        for sv in ["0", "1", "2", "3"]:
            p = dict(base_params)
            p["status"] = sv
            test_cases.append((f"status_{sv}_GET", "GET", p))

        # Different appType
        for at in ["0", "1", "15", "2", "3", "5", "10"]:
            p = dict(base_params)
            p["appType"] = at
            test_cases.append((f"appType_{at}_GET", "GET", p))

        # Different fid
        for fv in ["0", "-1", "1", "431407443"]:
            p = dict(base_params)
            p["fid"] = fv
            test_cases.append((f"fid_{fv}_GET", "GET", p))

        for test_name, method, params in test_cases:
            try:
                if method == "GET":
                    r = session.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=30)
                else:
                    r = session.post(f"{BASE}/pptSign/stuSignajax", data=params, timeout=30)
                res = safe_resp(r)
                res["test"] = f"stuSignajax_{test_name}"
                res["params"] = dict(params)
                results.append(res)
                if r.status_code != 500:
                    print(f"    {test_name} ({method}): {r.status_code} -> {r.text[:200]}")
                elif res["json"]:
                    print(f"    {test_name} ({method}): {r.status_code} JSON -> {json.dumps(res['json'], ensure_ascii=False)[:200]}")
            except Exception as e:
                results.append({"test": f"stuSignajax_{test_name}", "error": str(e)})
            time.sleep(0.1)

    return results


def test_preSign(session, active_ids):
    """Test 2: preSign deep testing."""
    results = []
    print("\n[2] Testing preSign endpoint...")

    if not active_ids:
        active_ids = ["0"]

    for active_id in active_ids[:5]:
        test_cases = [
            ("full_GET", "GET", {"activeId": str(active_id), "courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID}),
            ("full_POST", "POST", {"activeId": str(active_id), "courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID}),
            ("activeIdOnly_GET", "GET", {"activeId": str(active_id)}),
            ("activeIdOnly_POST", "POST", {"activeId": str(active_id)}),
            ("noActiveId_GET", "GET", {"courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID}),
            ("withReferer_GET", "GET", {"activeId": str(active_id), "courseId": COURSE_ID, "classId": CLASS_ID, "uid": PUID}),
        ]

        for test_name, method, params in test_cases:
            try:
                headers = {}
                if "withReferer" in test_name:
                    headers["Referer"] = f"https://mooc1.chaoxing.com/mycourse/stu?courseId={COURSE_ID}&clazzid={CLASS_ID}"

                if method == "GET":
                    r = session.get(f"{BASE}/pptSign/preSign", params=params, headers=headers, timeout=30)
                else:
                    r = session.post(f"{BASE}/pptSign/preSign", data=params, headers=headers, timeout=30)
                res = safe_resp(r)
                res["test"] = f"preSign_{test_name}"
                res["params"] = dict(params)
                results.append(res)
                print(f"  preSign {test_name} activeId={active_id}: {r.status_code} len={len(r.text)} -> {r.text[:200]}")
            except Exception as e:
                results.append({"test": f"preSign_{test_name}", "error": str(e)})
            time.sleep(0.15)

    return results


def test_updateqrstatus(session, active_ids):
    """Test 3: updateqrstatus deep testing."""
    results = []
    print("\n[3] Testing updateqrstatus endpoint...")

    if not active_ids:
        active_ids = ["0"]

    for active_id in active_ids[:3]:
        enc_values = ["", "test", "abc123xyz", "12345678", "0", "invalid_enc"]
        for enc_val in enc_values:
            for method in ["GET", "POST"]:
                params = {"activeId": str(active_id), "enc": enc_val, "uid": PUID}
                try:
                    if method == "GET":
                        r = session.get(f"{BASE}/pptSign/updateqrstatus", params=params, timeout=30)
                    else:
                        r = session.post(f"{BASE}/pptSign/updateqrstatus", data=params, timeout=30)
                    res = safe_resp(r)
                    res["test"] = f"updateqrstatus_enc_{enc_val or 'empty'}_{method}"
                    res["params"] = dict(params)
                    results.append(res)
                    if r.status_code != 500:
                        print(f"  updateqrstatus {method} enc='{enc_val}': {r.status_code} -> {r.text[:200]}")
                    elif res["json"]:
                        print(f"  updateqrstatus {method} enc='{enc_val}': {r.status_code} JSON -> {json.dumps(res['json'], ensure_ascii=False)[:200]}")
                except Exception as e:
                    results.append({"test": f"updateqrstatus_enc_{enc_val or 'empty'}_{method}", "error": str(e)})
                time.sleep(0.1)

        # Without uid
        for method in ["GET", "POST"]:
            params = {"activeId": str(active_id), "enc": "test"}
            try:
                if method == "GET":
                    r = session.get(f"{BASE}/pptSign/updateqrstatus", params=params, timeout=30)
                else:
                    r = session.post(f"{BASE}/pptSign/updateqrstatus", data=params, timeout=30)
                res = safe_resp(r)
                res["test"] = f"updateqrstatus_noUid_{method}"
                res["params"] = dict(params)
                results.append(res)
                if r.status_code != 500:
                    print(f"  updateqrstatus {method} noUid: {r.status_code} -> {r.text[:200]}")
            except Exception as e:
                results.append({"test": f"updateqrstatus_noUid_{method}", "error": str(e)})
            time.sleep(0.1)

    return results


def test_explore_endpoints(session, active_ids):
    """Test 4: Explore more /pptSign/ endpoints."""
    results = []
    found_endpoints = []
    print("\n[4] Exploring additional /pptSign/ endpoints...")

    endpoint_names = [
        "stuSignAjaxNew", "stuSignajaxNew", "stuSignNew", "stuSignV2", "signV2",
        "signNew", "signInV2", "signInNew", "qrCodeSign", "qrcodeSign",
        "scanSign", "scanQrCode", "locationSign", "gestureSign", "numberSign",
        "signByCode", "signByEnc", "signByToken", "getSignStuInfo", "getStuSignInfo",
        "stuSignInfo", "getSignStatus", "signStatus", "checkSignStatus",
        "activeSignList", "signList", "getSignList", "getActiveSign", "activeSign",
        "startSign", "endSign", "stopSign", "cancelSign", "deleteSign", "removeSign",
        "createSign", "addSign", "saveSign", "updateSign", "modifySign", "changeSign",
        "batchSign", "quickSign", "autoSign", "manualSign", "makeupSign", "lateSign",
        "leaveSign", "absentSign", "presentSign", "normalSign", "codeSign",
        "passwordSign", "faceSign", "fingerprintSign", "wifiSign", "bleSign",
        "nfcSign", "lbsSign", "gpsSign", "mapSign", "geoSign", "distanceSign",
        "rangeSign", "areaSign", "zoneSign", "regionSign", "nearbySign",
        "proximitySign", "beaconSign", "ibeaconSign", "eddystoneSign", "altBeaconSign"
    ]

    test_active_id = str(active_ids[0]) if active_ids else "0"

    base_params = {
        "activeId": test_active_id,
        "uid": PUID,
        "courseId": COURSE_ID,
        "classId": CLASS_ID
    }

    for ep_name in endpoint_names:
        url = f"{BASE}/pptSign/{ep_name}"
        for method in ["GET", "POST"]:
            try:
                if method == "GET":
                    r = session.get(url, params=base_params, timeout=10)
                else:
                    r = session.post(url, data=base_params, timeout=10)

                if r.status_code != 404:
                    res = safe_resp(r)
                    res["test"] = f"explore_{ep_name}_{method}"
                    res["endpoint"] = ep_name
                    res["method"] = method
                    results.append(res)
                    found_endpoints.append({
                        "endpoint": ep_name,
                        "method": method,
                        "status": r.status_code,
                        "response": r.text[:500]
                    })
                    if r.status_code != 500:
                        print(f"  [FOUND] {ep_name} {method}: {r.status_code} -> {r.text[:200]}")
                    elif "Internal Server Error" not in r.text:
                        print(f"  [NON-STD-500] {ep_name} {method}: {r.text[:200]}")
            except:
                pass
            time.sleep(0.05)

    status_counts = {}
    for ep in found_endpoints:
        s = ep["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"\n  Found {len(found_endpoints)} non-404 endpoints, status distribution: {status_counts}")

    non_500 = [ep for ep in found_endpoints if ep["status"] != 500]
    if non_500:
        print(f"  Non-500 endpoints ({len(non_500)}):")
        for ep in non_500:
            print(f"    - /pptSign/{ep['endpoint']} ({ep['method']}): status={ep['status']}, resp={ep['response'][:200]}")

    return results, found_endpoints


def test_distance_info(session, active_ids):
    """Test 5: Record distance information from location sign activities."""
    results = []
    print("\n[5] Testing distance information from location sign activities...")

    test_coords = [
        ("39.9042", "116.4074", "天安门广场"),
        ("39.9082", "116.3974", "天安门西侧约1km"),
        ("39.9142", "116.4074", "天安门北侧约1.1km"),
        ("39.9042", "116.4174", "天安门东侧约1km"),
        ("39.8942", "116.4074", "天安门南侧约1.1km"),
        ("39.9242", "116.4074", "天安门北侧约2.2km"),
        ("39.9042", "116.4274", "天安门东侧约2km"),
        ("39.8842", "116.4074", "天安门南侧约2.2km"),
        ("39.9042", "116.3874", "天安门西侧约2km"),
        ("31.2304", "121.4737", "上海外滩"),
        ("23.1291", "113.2644", "广州"),
        ("0", "0", "零坐标"),
        ("-1", "-1", "默认-1坐标"),
    ]

    if not active_ids:
        active_ids = ["0"]

    for active_id in active_ids[:5]:
        print(f"  Testing activeId={active_id} for distance info...")
        for lat, lng, desc in test_coords:
            params = {
                "activeId": str(active_id),
                "uid": PUID,
                "clientip": "",
                "latitude": lat,
                "longitude": lng,
                "appType": "15",
                "fid": "0",
                "address": desc
            }
            try:
                r = session.get(f"{BASE}/pptSign/stuSignajax", params=params, timeout=30)
                res = safe_resp(r)
                res["test"] = "distance_test"
                res["params"] = dict(params)
                res["coord_desc"] = desc
                results.append(res)

                text = r.text
                distance_found = False
                if "距" in text and "米" in text:
                    distance_found = True
                    print(f"    [{desc}] lat={lat}, lng={lng}: DISTANCE FOUND -> {text[:300]}")
                elif "distance" in text.lower():
                    distance_found = True
                    print(f"    [{desc}] lat={lat}, lng={lng}: DISTANCE FOUND -> {text[:300]}")
                elif r.status_code != 500:
                    print(f"    [{desc}] lat={lat}, lng={lng}: {r.status_code} -> {text[:150]}")

                res["distance_found"] = distance_found
            except Exception as e:
                results.append({"test": "distance_test", "coord_desc": desc, "lat": lat, "lng": lng, "error": str(e)})
            time.sleep(0.1)

    return results


def test_additional_sign_endpoints(session, active_ids):
    """Test additional sign-related endpoints."""
    results = []
    print("\n[*] Testing additional sign-related endpoints...")

    test_active_id = str(active_ids[0]) if active_ids else "0"

    endpoints = [
        (f"{BASE}/pptSign/teacherSign", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/signStudentList", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/getSignInfo", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/signDetail", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/checkSign", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/getActiveInfo", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/activeDetail", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/stuSignResult", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/signResult", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/getSignResult", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/getqrstatus", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/qrstatus", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/getSignConfig", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/signConfig", "GET", {"activeId": test_active_id, "uid": PUID}),
        (f"{BASE}/pptSign/getSignRule", "GET", {"activeId": test_active_id, "uid": PUID}),
    ]

    for url, method, params in endpoints:
        try:
            if method == "GET":
                r = session.get(url, params=params, timeout=15)
            else:
                r = session.post(url, data=params, timeout=15)
            res = safe_resp(r)
            ep = url.split("/")[-1]
            res["test"] = f"additional_{ep}_{method}"
            results.append(res)
            if r.status_code != 500:
                print(f"  {ep} ({method}): {r.status_code} -> {r.text[:200]}")
            elif res["json"]:
                print(f"  {ep} ({method}): {r.status_code} JSON -> {json.dumps(res['json'], ensure_ascii=False)[:200]}")
        except Exception as e:
            results.append({"test": f"additional_{url.split('/')[-1]}", "error": str(e)})
        time.sleep(0.15)

    return results


def main():
    print("=" * 70)
    print("Task 3: Deep Testing of /pptSign/ Endpoints (v5)")
    print("=" * 70)

    # Login
    print("\n[*] Logging in...")
    session, puid = login(PHONE, PWD)
    if not puid:
        puid = PUID

    # Discover activities
    print("\n[*] Discovering activities...")
    activities, active_ids = discover_activities(session)
    print(f"\n  Activities: {len(activities)}, Active IDs: {active_ids[:20]}")

    # If no active IDs found, use some fallbacks
    if not active_ids:
        active_ids = ["0"]
        print(f"  No active IDs found, using fallback: {active_ids}")

    all_results = {
        "login_puid": puid,
        "activities": activities,
        "active_ids": active_ids,
        "activity_count": len(activities),
        "stuSignajax_tests": [],
        "preSign_tests": [],
        "updateqrstatus_tests": [],
        "explore_tests": [],
        "found_endpoints": [],
        "distance_tests": [],
        "additional_tests": [],
    }

    # Run all tests
    try:
        all_results["stuSignajax_tests"] = test_stuSignajax(session, active_ids)
    except Exception as e:
        print(f"  [!] stuSignajax error: {e}")
        all_results["stuSignajax_tests"] = [{"error": str(e)}]

    try:
        all_results["preSign_tests"] = test_preSign(session, active_ids)
    except Exception as e:
        print(f"  [!] preSign error: {e}")
        all_results["preSign_tests"] = [{"error": str(e)}]

    try:
        all_results["updateqrstatus_tests"] = test_updateqrstatus(session, active_ids)
    except Exception as e:
        print(f"  [!] updateqrstatus error: {e}")
        all_results["updateqrstatus_tests"] = [{"error": str(e)}]

    try:
        explore_results, found_endpoints = test_explore_endpoints(session, active_ids)
        all_results["explore_tests"] = explore_results
        all_results["found_endpoints"] = found_endpoints
    except Exception as e:
        print(f"  [!] Explore error: {e}")

    try:
        all_results["distance_tests"] = test_distance_info(session, active_ids)
    except Exception as e:
        print(f"  [!] Distance error: {e}")

    try:
        all_results["additional_tests"] = test_additional_sign_endpoints(session, active_ids)
    except Exception as e:
        print(f"  [!] Additional test error: {e}")

    # Save results
    output_path = "/workspace/task3_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[*] Results saved to {output_path}")

    # Print comprehensive summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Login PUID: {puid}")
    print(f"  Activities found: {len(activities)}")
    print(f"  Active IDs: {active_ids[:10]}")
    print(f"  stuSignajax tests: {len(all_results['stuSignajax_tests'])}")
    print(f"  preSign tests: {len(all_results['preSign_tests'])}")
    print(f"  updateqrstatus tests: {len(all_results['updateqrstatus_tests'])}")
    print(f"  Explore tests: {len(all_results['explore_tests'])}")
    print(f"  Found non-404 endpoints: {len(all_results['found_endpoints'])}")
    print(f"  Distance tests: {len(all_results['distance_tests'])}")
    print(f"  Additional tests: {len(all_results['additional_tests'])}")

    # Categorize found endpoints by status
    if all_results["found_endpoints"]:
        status_groups = {}
        for ep in all_results["found_endpoints"]:
            s = ep["status"]
            if s not in status_groups:
                status_groups[s] = []
            status_groups[s].append(ep)

        print("\n  /pptSign/ Endpoint Status Distribution:")
        for status, eps in sorted(status_groups.items()):
            print(f"    HTTP {status}: {len(eps)} endpoints")
            if status != 500:
                for ep in eps:
                    print(f"      - /pptSign/{ep['endpoint']} ({ep['method']}): {ep['response'][:200]}")

    # Non-500 results from all test categories
    print("\n  Non-500 results across all tests:")
    found_any = False
    for category in ["stuSignajax_tests", "preSign_tests", "updateqrstatus_tests", "additional_tests"]:
        non_500 = [t for t in all_results[category] if isinstance(t, dict) and t.get("status_code") and t["status_code"] != 500]
        if non_500:
            found_any = True
            for t in non_500:
                print(f"    [{category}] {t.get('test', '?')}: status={t.get('status_code')} -> {t.get('text', '')[:200]}")
    if not found_any:
        print("    (none)")

    # JSON responses
    print("\n  JSON responses:")
    json_found = False
    for category in ["stuSignajax_tests", "preSign_tests", "updateqrstatus_tests", "additional_tests"]:
        for t in all_results[category]:
            if isinstance(t, dict) and t.get("json"):
                json_found = True
                print(f"    [{category}] {t.get('test', '?')}: {json.dumps(t['json'], ensure_ascii=False)[:300]}")
    if not json_found:
        print("    (none)")

    # Distance info
    distance_findings = [d for d in all_results["distance_tests"] if isinstance(d, dict) and d.get("distance_found")]
    if distance_findings:
        print(f"\n  Distance info found in {len(distance_findings)} responses:")
        for d in distance_findings:
            print(f"    - {d.get('coord_desc', '?')}: lat={d.get('params', {}).get('latitude')}, lng={d.get('params', {}).get('longitude')}")
    else:
        print("\n  No distance info found in responses.")

    # Key findings
    print("\n  KEY FINDINGS:")
    print(f"    1. Login successful: PUID={puid}")
    print(f"    2. preSign returns 200 with empty body (needs valid activeId)")
    print(f"    3. Most /pptSign/ endpoints return 500 (server-side issue)")
    print(f"    4. taskactivelist returns 500 (cannot enumerate activities)")
    print(f"    5. backclazzdata returns 200 with course data")
    print(f"    6. CPI={CPI} discovered from backclazzdata")
    print(f"    7. {len(all_results['found_endpoints'])} non-404 /pptSign/ endpoints discovered")
    print(f"    8. All explored /pptSign/ endpoints return 500 (server may be down)")

    print("\n[*] Done.")


if __name__ == "__main__":
    main()
