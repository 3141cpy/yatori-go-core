#!/usr/bin/env python3
"""
探索超星第二、三层域名的签到相关API
Second Tier: Alternative APIs (7 domains)
Third Tier: Infrastructure (8 domains)
"""

import base64, hashlib, json, uuid, requests, urllib3, time, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

# ============ 常量 ============
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
ACTIVE_ID = "5000163891319"

STUDENT_PHONE = "18436633997"
STUDENT_PWD = "3.1415926Cpy"

TIMEOUT_BASE = 10
TIMEOUT_API = 15

# ============ 工具函数 ============
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

def classify_response(data, status_code, text):
    """分类响应：是否包含签到数据、是否可修改签到状态"""
    is_found = False
    is_critical = False
    reasons = []

    if status_code == 200:
        try:
            d = data if isinstance(data, dict) else {}
            # 检查是否返回了签到相关数据
            text_lower = text.lower() if text else ""
            sign_keywords = ["sign", "签到", "signtype", "signid", "activeid",
                           "issign", "signstatus", "signresult", "stusign",
                           "signlist", "signinfo", "attendance"]
            for kw in sign_keywords:
                if kw in text_lower:
                    is_found = True
                    reasons.append(f"含关键词:{kw}")
                    break

            # 检查是否可以修改签到状态
            if isinstance(d, dict):
                result_val = str(d.get("result", d.get("data", ""))).lower()
                status_val = str(d.get("status", "")).lower()
                msg_val = str(d.get("msg", d.get("message", ""))).lower()

                # 成功修改的标志
                if d.get("result") in (1, "1", True, "true") or status_val in ("success", "ok", "1", "true"):
                    if any(kw in text_lower for kw in ["sign", "签到"]):
                        is_critical = True
                        reasons.append("返回成功状态+签到关键词")

                # 明确的签到成功消息
                success_msgs = ["签到成功", "sign success", "已签到", "签到完成", "signsuccess"]
                for sm in success_msgs:
                    if sm in msg_val or sm in text_lower:
                        is_critical = True
                        reasons.append(f"签到成功消息:{sm}")
                        break

                # 有签到数据字段
                sign_data_fields = ["signid", "signstatus", "signtype", "stusign", "signresult"]
                for sf in sign_data_fields:
                    if sf in d:
                        is_found = True
                        reasons.append(f"含数据字段:{sf}")

                # result=1 且包含签到相关
                if d.get("result") in (1, "1", True, "true"):
                    if any(kw in text_lower for kw in ["sign", "签到"]):
                        is_critical = True
                        reasons.append("result=1+签到关键词")
        except:
            pass

    return is_found, is_critical, reasons

# ============ 域名与路径定义 ============
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

DOMAIN_CONFIGS = {
    # === 第二层 ===
    "mobile.fanya.chaoxing.com": {
        "tier": 2, "label": "泛亚移动端", "key": "mobileFyDomain",
        "extra_paths": ["/fanya/sign/updateSignStatus", "/fanya/sign/stuSignajax",
                       "/fanya/pptSign/updateSignStatus", "/fanya/pptSign/updateSignStatusByUidsV2",
                       "/fanya/pptSign/refeashSignList4Json2", "/fanya/pptSign/stuSignajax",
                       "/fanya/newsign/updateSignStatus"]
    },
    "mobilelearn.fy.chaoxing.com": {
        "tier": 2, "label": "泛亚学习端", "key": "mobileLearnFyDomain",
        "extra_paths": ["/fanya/sign/updateSignStatus", "/fanya/sign/stuSignajax",
                       "/fanya/pptSign/updateSignStatus", "/fanya/pptSign/updateSignStatusByUidsV2",
                       "/fanya/pptSign/refeashSignList4Json2", "/fanya/pptSign/stuSignajax",
                       "/fanya/newsign/updateSignStatus"]
    },
    "mooc2-ans.chaoxing.com": {
        "tier": 2, "label": "MOOC2 ANS", "key": "mooc2AnsDomain",
        "extra_paths": ["/mooc-ans/sign/updateSignStatus", "/mooc-ans/sign/stuSignajax",
                       "/mooc-ans/pptSign/updateSignStatus", "/mooc-ans/pptSign/updateSignStatusByUidsV2",
                       "/mooc-ans/pptSign/refeashSignList4Json2", "/mooc-ans/pptSign/stuSignajax",
                       "/mooc-ans/newsign/updateSignStatus"]
    },
    "bigdata-api.chaoxing.com": {
        "tier": 2, "label": "大数据API", "key": "bigdataDomain",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/course/sign/updateSignStatus", "/course/sign/stuSignajax",
                       "/api/course/sign/updateSignStatus", "/api/course/sign/stuSignajax",
                       "/api/sign/updateSignStatus", "/api/sign/stuSignajax"]
    },
    "bigdata-ans.chaoxing.com": {
        "tier": 2, "label": "大数据ANS", "key": "CourseDomain",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/course/sign/updateSignStatus", "/course/sign/stuSignajax",
                       "/api/course/sign/updateSignStatus", "/api/course/sign/stuSignajax",
                       "/api/sign/updateSignStatus", "/api/sign/stuSignajax"]
    },
    "fystat-ans.chaoxing.com": {
        "tier": 2, "label": "泛亚统计", "key": "fyStatDomainHttps",
        "extra_paths": ["/sign/statistics", "/sign/detail", "/sign/updateSignStatus",
                       "/api/sign/updateSignStatus", "/api/sign/statistics", "/api/sign/detail"]
    },
    "stat2-ans.chaoxing.com": {
        "tier": 2, "label": "统计2", "key": "stat2DomainHttps",
        "extra_paths": ["/sign/statistics", "/sign/detail", "/sign/updateSignStatus",
                       "/api/sign/updateSignStatus", "/api/sign/statistics", "/api/sign/detail"]
    },
    # === 第三层 ===
    "passport2-api.chaoxing.com": {
        "tier": 3, "label": "认证API", "key": "passport2ApiDomainHttps",
        "extra_paths": ["/sign/updateSignStatus", "/api/sign/updateSignStatus",
                       "/auth/sign/updateSignStatus", "/user/sign/updateSignStatus"]
    },
    "uc.chaoxing.com": {
        "tier": 3, "label": "用户中心", "key": "ucDomain",
        "extra_paths": ["/sign/updateSignStatus", "/user/sign/updateSignStatus",
                       "/user/sign/stuSignajax", "/sign/stuSignajax"]
    },
    "uc1-ans.chaoxing.com": {
        "tier": 3, "label": "用户中心ANS", "key": "uc1Domain",
        "extra_paths": ["/sign/updateSignStatus", "/user/sign/updateSignStatus",
                       "/user/sign/stuSignajax", "/sign/stuSignajax"]
    },
    "structureyd.chaoxing.com": {
        "tier": 3, "label": "结构域名", "key": "structureDomainHttps",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/api/sign/updateSignStatus"]
    },
    "v1.chaoxing.com": {
        "tier": 3, "label": "V1域名", "key": "v1Domain",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/api/sign/updateSignStatus"]
    },
    "mobilewx.chaoxing.com": {
        "tier": 3, "label": "微信端", "key": "mobileWxDomain",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/wx/sign/updateSignStatus", "/wx/sign/stuSignajax",
                       "/wechat/sign/updateSignStatus", "/wechat/sign/stuSignajax"]
    },
    "manage.learn.chaoxing.com": {
        "tier": 3, "label": "管理端", "key": "manageLearnDomain",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/manage/sign/updateSignStatus", "/manage/sign/stuSignajax",
                       "/admin/sign/updateSignStatus", "/admin/sign/stuSignajax"]
    },
    "manage.yd.chaoxing.com": {
        "tier": 3, "label": "管理端YD", "key": "manageydDomainHttp",
        "extra_paths": ["/sign/updateSignStatus", "/sign/stuSignajax",
                       "/manage/sign/updateSignStatus", "/manage/sign/stuSignajax",
                       "/admin/sign/updateSignStatus", "/admin/sign/stuSignajax"]
    },
}

# ============ 签到请求参数 ============
def get_sign_params(uid):
    return {
        "activeId": ACTIVE_ID,
        "uid": uid,
        "courseId": COURSE_ID,
        "classId": CLASS_ID,
        "signType": "0",
        "clientType": "1",
    }

# ============ 主流程 ============
def main():
    print("=" * 80)
    print("超星第二、三层域名签到API探索")
    print("=" * 80)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"活跃签到ID: {ACTIVE_ID}")
    print(f"课程ID: {COURSE_ID}, 班级ID: {CLASS_ID}")
    print()

    # 登录学生账号
    print("[*] 正在登录学生账号...")
    student_session, student_puid = login(STUDENT_PHONE, STUDENT_PWD)
    if not student_puid:
        print("[!] 警告: 未获取到学生PUID, 尝试从cookie中获取")
        for c in student_session.cookies:
            if c.name in ("UID", "_uid"):
                student_puid = c.value
    print(f"[*] 学生PUID: {student_puid}")
    print()

    # 结果汇总
    results = []

    for domain, config in DOMAIN_CONFIGS.items():
        tier = config["tier"]
        label = config["label"]
        key = config["key"]
        tier_label = "第二层" if tier == 2 else "第三层"

        print("=" * 80)
        print(f"[{tier_label}] {domain} ({label}) [{key}]")
        print("=" * 80)

        domain_result = {
            "domain": domain, "tier": tier_label, "label": label, "key": key,
            "alive": False, "found_endpoints": [], "critical_endpoints": []
        }

        # 1. 测试基础URL可达性
        base_url = f"https://{domain}"
        try:
            r = student_session.get(base_url, timeout=TIMEOUT_BASE, allow_redirects=True)
            domain_result["alive"] = True
            print(f"  !!!ALIVE!!! GET / => {r.status_code} (len={len(r.text)})")
            # 截取前200字符
            snippet = r.text[:200].replace('\n', ' ').replace('\r', '')
            print(f"    响应片段: {snippet}")
        except requests.exceptions.SSLError as e:
            # 尝试HTTP
            try:
                base_url_http = f"http://{domain}"
                r = student_session.get(base_url_http, timeout=TIMEOUT_BASE, allow_redirects=True)
                domain_result["alive"] = True
                print(f"  !!!ALIVE!!! (HTTP) GET / => {r.status_code} (len={len(r.text)})")
                snippet = r.text[:200].replace('\n', ' ').replace('\r', '')
                print(f"    响应片段: {snippet}")
            except Exception as e2:
                print(f"  [X] 不可达 (HTTPS/HTTP均失败): {str(e2)[:100]}")
                results.append(domain_result)
                continue
        except Exception as e:
            # 尝试HTTP
            try:
                base_url_http = f"http://{domain}"
                r = student_session.get(base_url_http, timeout=TIMEOUT_BASE, allow_redirects=True)
                domain_result["alive"] = True
                print(f"  !!!ALIVE!!! (HTTP) GET / => {r.status_code} (len={len(r.text)})")
                snippet = r.text[:200].replace('\n', ' ').replace('\r', '')
                print(f"    响应片段: {snippet}")
            except Exception as e2:
                print(f"  [X] 不可达: {str(e)[:100]}")
                results.append(domain_result)
                continue

        # 2. 测试签到相关路径
        all_paths = list(COMMON_SIGN_PATHS) + config.get("extra_paths", [])
        # 去重
        seen = set()
        unique_paths = []
        for p in all_paths:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)

        sign_params = get_sign_params(student_puid)

        for path in unique_paths:
            url = f"https://{domain}{path}"
            # 也尝试HTTP
            url_http = f"http://{domain}{path}"

            for proto_url in [url, url_http]:
                proto_tag = "HTTPS" if proto_url.startswith("https") else "HTTP"
                try:
                    # 先GET
                    r = student_session.get(proto_url, params=sign_params, timeout=TIMEOUT_API,
                                           allow_redirects=False)
                    data = safe_json(r)
                    is_found, is_critical, reasons = classify_response(data, r.status_code, r.text)

                    status_tag = ""
                    if is_critical:
                        status_tag = " !!!CRITICAL!!!"
                        domain_result["critical_endpoints"].append(f"{proto_tag} GET {path}")
                    elif is_found:
                        status_tag = " !!!FOUND!!!"
                        domain_result["found_endpoints"].append(f"{proto_tag} GET {path}")

                    if r.status_code != 404:
                        print(f"  [{proto_tag}] GET {path} => {r.status_code}{status_tag}")
                        if is_found or is_critical:
                            print(f"    原因: {', '.join(reasons)}")
                        # 显示响应摘要
                        resp_text = r.text[:300].replace('\n', ' ').replace('\r', '')
                        print(f"    响应: {resp_text}")

                    # 如果GET返回了有意义的状态码，也尝试POST
                    if r.status_code in (200, 302, 403, 401):
                        try:
                            r2 = student_session.post(proto_url, data=sign_params, timeout=TIMEOUT_API,
                                                     allow_redirects=False)
                            data2 = safe_json(r2)
                            is_found2, is_critical2, reasons2 = classify_response(data2, r2.status_code, r2.text)

                            status_tag2 = ""
                            if is_critical2:
                                status_tag2 = " !!!CRITICAL!!!"
                                domain_result["critical_endpoints"].append(f"{proto_tag} POST {path}")
                            elif is_found2:
                                status_tag2 = " !!!FOUND!!!"
                                domain_result["found_endpoints"].append(f"{proto_tag} POST {path}")

                            print(f"  [{proto_tag}] POST {path} => {r2.status_code}{status_tag2}")
                            if is_found2 or is_critical2:
                                print(f"    原因: {', '.join(reasons2)}")
                            resp_text2 = r2.text[:300].replace('\n', ' ').replace('\r', '')
                            print(f"    响应: {resp_text2}")
                        except Exception:
                            pass

                except requests.exceptions.SSLError:
                    if proto_url.startswith("https"):
                        continue  # 会尝试HTTP
                except Exception as e:
                    err_str = str(e)[:80]
                    if "404" not in err_str and "Not Found" not in err_str:
                        pass  # 不打印404类错误

        # 如果HTTPS和HTTP都不可达，尝试直接用域名+路径
        if not domain_result["found_endpoints"] and not domain_result["critical_endpoints"]:
            # 尝试一些带完整mooc-ans前缀的路径
            extra_prefix_paths = [
                f"/mooc-ans{p}" for p in ["/pptSign/updateSignStatus", "/pptSign/stuSignajax",
                                           "/newsign/updateSignStatus", "/sign/updateSignStatus"]
            ]
            for path in extra_prefix_paths:
                for proto in ["https", "http"]:
                    proto_url = f"{proto}://{domain}{path}"
                    proto_tag = proto.upper()
                    try:
                        r = student_session.get(proto_url, params=sign_params, timeout=TIMEOUT_API,
                                               allow_redirects=False)
                        data = safe_json(r)
                        is_found, is_critical, reasons = classify_response(data, r.status_code, r.text)

                        if r.status_code != 404:
                            status_tag = ""
                            if is_critical:
                                status_tag = " !!!CRITICAL!!!"
                                domain_result["critical_endpoints"].append(f"{proto_tag} GET {path}")
                            elif is_found:
                                status_tag = " !!!FOUND!!!"
                                domain_result["found_endpoints"].append(f"{proto_tag} GET {path}")
                            print(f"  [{proto_tag}] GET {path} => {r.status_code}{status_tag}")
                            if is_found or is_critical:
                                print(f"    原因: {', '.join(reasons)}")
                            resp_text = r.text[:300].replace('\n', ' ').replace('\r', '')
                            print(f"    响应: {resp_text}")
                    except:
                        pass

        results.append(domain_result)
        print()

    # ============ 汇总表 ============
    print()
    print("=" * 100)
    print("汇总表")
    print("=" * 100)
    print(f"{'层级':<6} {'域名':<35} {'标签':<12} {'存活':<6} {'发现端点':<8} {'危险端点':<8}")
    print("-" * 100)
    for r in results:
        alive_str = "✓" if r["alive"] else "✗"
        found_count = len(r["found_endpoints"])
        critical_count = len(r["critical_endpoints"])
        print(f"{r['tier']:<6} {r['domain']:<35} {r['label']:<12} {alive_str:<6} {found_count:<8} {critical_count:<8}")

    # 详细发现
    print()
    print("=" * 100)
    print("详细发现")
    print("=" * 100)

    any_found = False
    for r in results:
        if r["found_endpoints"] or r["critical_endpoints"]:
            any_found = True
            print(f"\n[{r['tier']}] {r['domain']} ({r['label']})")
            if r["found_endpoints"]:
                print(f"  !!!FOUND!!! 端点 ({len(r['found_endpoints'])}):")
                for ep in r["found_endpoints"]:
                    print(f"    - {ep}")
            if r["critical_endpoints"]:
                print(f"  !!!CRITICAL!!! 端点 ({len(r['critical_endpoints'])}):")
                for ep in r["critical_endpoints"]:
                    print(f"    - {ep}")

    if not any_found:
        print("\n[!] 未在任何域名上发现签到相关端点")

    # 存活域名统计
    alive_domains = [r for r in results if r["alive"]]
    print(f"\n存活域名: {len(alive_domains)}/{len(results)}")
    print(f"有发现的域名: {len([r for r in results if r['found_endpoints']])}/{len(results)}")
    print(f"有危险端点的域名: {len([r for r in results if r['critical_endpoints']])}/{len(results)}")

    print("\n" + "=" * 100)
    print("探索完成")
    print("=" * 100)


if __name__ == "__main__":
    main()
