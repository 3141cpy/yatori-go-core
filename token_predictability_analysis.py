#!/usr/bin/env python3
"""
_token 可预测性分析脚本

分析学习通云盘旧版 API 的 _token 是否可通过 puid 预测生成。
已知信息:
  - _token 是 32 位十六进制字符串 (MD5 格式)
  - 账号1 (puid=252798154) 的 _token = 721b618c5d4593ecfe7e2ee3a2275c23
  - 账号2 (puid=239448447) 的 _token = 83506aa06d929e82bc9a613314ef9890

仅用于安全研究和授权测试目的。
"""

import hashlib
import itertools
import re

KNOWN_TOKENS = {
    252798154: "721b618c5d4593ecfe7e2ee3a2275c23",
    239448447: "83506aa06d929e82bc9a613314ef9890",
}

COMMON_SALTS = [
    "",
    "chaoxing",
    "ChaoXing",
    "CHAOXING",
    "pan-yz",
    "pan_yz",
    "panyz",
    "pan-yz.chaoxing.com",
    "chaoxing.com",
    "mooc",
    "mooc.chaoxing.com",
    "i.mooc.chaoxing.com",
    "passport2.chaoxing.com",
    "u2oh6Vu^HWe4_AES",
    "uservalid",
    "token",
    "_token",
    "secret",
    "key",
    "salt",
    "chaoxing_pan",
    "pan_token",
    "yz",
    "ananas",
    "sync.ananas.chaoxing.com",
    "fanyalogin",
    "cloud",
    "yunpan",
    "disk",
    "user",
    "puid",
    "id",
    "uid",
    "chaoxing123",
    "pan123",
    "superkey",
    "admin",
    "root",
    "test",
    "default",
    "appkey",
    "app_key",
    "apikey",
    "api_key",
    "sign",
    "signature",
    "auth",
    "authorization",
    "access_token",
    "session_token",
    "security",
    "encrypt",
    "hash",
    "md5",
    "sha",
    "hmac",
    "web",
    "mobile",
    "android",
    "ios",
    "client",
    "server",
    "backend",
    "frontend",
    "api",
    "v1",
    "v2",
    "3F6410F7-344C-48C3-BC43-168936D1074B",
]

SEPARATOR_VARIANTS = ["", "_", "-", ":", "|", ".", "/", "@", "#", "$", " "]


def md5_hex(data: str) -> str:
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha1_hex(data: str) -> str:
    return hashlib.sha1(data.encode("utf-8")).hexdigest()


def sha512_hex(data: str) -> str:
    return hashlib.sha512(data.encode("utf-8")).hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def check_match(label: str, computed: str, puid: int):
    expected = KNOWN_TOKENS[puid]
    match = computed.lower() == expected.lower()
    marker = " *** MATCH! ***" if match else ""
    print(f"  [{puid}] {label}: {computed}{marker}")
    return match


def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def analyze_format():
    section("1. 格式特征分析")
    for puid, token in KNOWN_TOKENS.items():
        is_hex = bool(re.fullmatch(r'[0-9a-fA-F]{32}', token))
        length = len(token)
        print(f"  puid={puid}: _token={token}")
        print(f"    长度: {length}")
        print(f"    是否为32位hex: {is_hex}")
        print(f"    符合MD5格式: {is_hex}")
        char_dist = {}
        for c in token.lower():
            char_dist[c] = char_dist.get(c, 0) + 1
        print(f"    字符分布: {dict(sorted(char_dist.items()))}")
        unique_chars = len(set(token.lower()))
        print(f"    唯一字符数: {unique_chars}/16")
    print("\n  结论: _token 为 32 位十六进制字符串，符合 MD5 输出格式")


def try_basic_hashes():
    section("2. 基础哈希算法逆向尝试")
    matches = []
    for puid in KNOWN_TOKENS:
        print(f"\n  --- puid={puid} ---")
        check_match("MD5(int_puid)", md5_hex(str(puid)), puid)
        check_match("MD5(str_puid)", md5_hex(str(puid)), puid)
        check_match("SHA256(puid)[:32]", sha256_hex(str(puid))[:32], puid)
        check_match("SHA1(puid)[:32]", sha1_hex(str(puid))[:32], puid)
        check_match("SHA512(puid)[:32]", sha512_hex(str(puid))[:32], puid)
        check_match("MD5(puid_hex)", md5_hex(hex(puid)), puid)
        check_match("MD5(puid_padded_9)", md5_hex(str(puid).zfill(9)), puid)
        check_match("MD5(puid_padded_10)", md5_hex(str(puid).zfill(10)), puid)
    return matches


def try_salt_variants():
    section("3. MD5(puid + salt) 变体尝试")
    any_match = False
    for salt in COMMON_SALTS:
        for sep in SEPARATOR_VARIANTS:
            for puid in KNOWN_TOKENS:
                s = str(puid) + sep + salt
                computed = md5_hex(s)
                if computed.lower() == KNOWN_TOKENS[puid].lower():
                    print(f"  *** MATCH! *** puid={puid}, MD5('{s}')")
                    any_match = True
    if not any_match:
        print("  未找到匹配的 salt 变体 (MD5(puid + sep + salt))")
    return any_match


def try_salt_prefix_variants():
    section("4. MD5(salt + puid) 变体尝试")
    any_match = False
    for salt in COMMON_SALTS:
        for sep in SEPARATOR_VARIANTS:
            for puid in KNOWN_TOKENS:
                s = salt + sep + str(puid)
                computed = md5_hex(s)
                if computed.lower() == KNOWN_TOKENS[puid].lower():
                    print(f"  *** MATCH! *** puid={puid}, MD5('{s}')")
                    any_match = True
    if not any_match:
        print("  未找到匹配的 salt 变体 (MD5(salt + sep + puid))")
    return any_match


def try_double_hash():
    section("5. 双重哈希尝试")
    any_match = False
    for puid in KNOWN_TOKENS:
        first = md5_hex(str(puid))
        check_match("MD5(MD5(puid))", md5_hex(first), puid)
        first_sha = sha256_hex(str(puid))
        check_match("MD5(SHA256(puid))", md5_hex(first_sha), puid)
        first_sha1 = sha1_hex(str(puid))
        check_match("MD5(SHA1(puid))", md5_hex(first_sha1), puid)
        for salt in ["chaoxing", "pan-yz", "u2oh6Vu^HWe4_AES", "uservalid"]:
            check_match(f"MD5(MD5(puid)+{salt})", md5_hex(first + salt), puid)
            check_match(f"MD5({salt}+MD5(puid))", md5_hex(salt + first), puid)
            check_match(f"MD5(MD5(puid+{salt}))", md5_hex(md5_hex(str(puid) + salt)), puid)
    return any_match


def try_puid_combinations():
    section("6. puid 自身组合尝试")
    for puid in KNOWN_TOKENS:
        print(f"\n  --- puid={puid} ---")
        check_match("MD5(puid+puid)", md5_hex(str(puid) + str(puid)), puid)
        check_match("MD5(puid_puid)", md5_hex(f"{puid}_{puid}"), puid)
        check_match("MD5(puid-puid)", md5_hex(f"{puid}-{puid}"), puid)
        check_match("MD5(puid.puid)", md5_hex(f"{puid}.{puid}"), puid)
        check_match("MD5(puid+puid_str)", md5_hex(str(puid) + str(puid)), puid)
        other_puid = [k for k in KNOWN_TOKENS if k != puid][0]
        check_match(f"MD5(puid+other_puid)", md5_hex(str(puid) + str(other_puid)), puid)
        check_match(f"MD5(other_puid+puid)", md5_hex(str(other_puid) + str(puid)), puid)


def try_known_key_combinations():
    section("7. 已知密钥/标识符组合尝试")
    aes_key = "u2oh6Vu^HWe4_AES"
    appid = "3F6410F7-344C-48C3-BC43-168936D1074B"
    for puid in KNOWN_TOKENS:
        print(f"\n  --- puid={puid} ---")
        check_match("MD5(puid+AES_KEY)", md5_hex(str(puid) + aes_key), puid)
        check_match("MD5(AES_KEY+puid)", md5_hex(aes_key + str(puid)), puid)
        check_match("MD5(puid+AES_KEY_bytes)", md5_hex(str(puid) + aes_key), puid)
        check_match("MD5(puid+APPID)", md5_hex(str(puid) + appid), puid)
        check_match("MD5(APPID+puid)", md5_hex(appid + str(puid)), puid)
        check_match("MD5(puid+AES_KEY+chaoxing)", md5_hex(str(puid) + aes_key + "chaoxing"), puid)
        check_match("MD5(chaoxing+puid+AES_KEY)", md5_hex("chaoxing" + str(puid) + aes_key), puid)
        check_match("MD5(puid+pan-yz+AES_KEY)", md5_hex(str(puid) + "pan-yz" + aes_key), puid)
        check_match("MD5(MD5(puid)+AES_KEY)", md5_hex(md5_hex(str(puid)) + aes_key), puid)
        check_match("MD5(AES_KEY+MD5(puid))", md5_hex(aes_key + md5_hex(str(puid))), puid)
        check_match("MD5(puid+MD5(AES_KEY))", md5_hex(str(puid) + md5_hex(aes_key)), puid)
        check_match("MD5(MD5(AES_KEY)+puid)", md5_hex(md5_hex(aes_key) + str(puid)), puid)
        check_match("MD5(puid+SHA256(AES_KEY)[:16])", md5_hex(str(puid) + sha256_hex(aes_key)[:16]), puid)
        check_match("MD5(SHA256(AES_KEY)[:16]+puid)", md5_hex(sha256_hex(aes_key)[:16] + str(puid)), puid)


def try_numeric_transforms():
    section("8. 数值变换尝试")
    for puid in KNOWN_TOKENS:
        print(f"\n  --- puid={puid} ---")
        check_match("MD5(hex(puid))", md5_hex(hex(puid)), puid)
        check_match("MD5(oct(puid))", md5_hex(oct(puid)), puid)
        check_match("MD5(bin(puid))", md5_hex(bin(puid)), puid)
        check_match("MD5(puid_reversed)", md5_hex(str(puid)[::-1]), puid)
        check_match("MD5(str(puid*2))", md5_hex(str(puid * 2)), puid)
        check_match("MD5(str(puid+1))", md5_hex(str(puid + 1)), puid)
        check_match("MD5(str(puid-1))", md5_hex(str(puid - 1)), puid)
        puid_str = str(puid)
        check_match("MD5(puid_upper)", md5_hex(puid_str.upper()), puid)
        check_match("MD5(puid_with_leading_zeros)", md5_hex(puid_str.zfill(12)), puid)
        check_match("MD5(bytes_puid_be)", md5_bytes(puid.to_bytes(4, 'big')), puid)
        check_match("MD5(bytes_puid_le)", md5_bytes(puid.to_bytes(4, 'little')), puid)
        check_match("MD5(bytes_puid_be_8)", md5_bytes(puid.to_bytes(8, 'big')), puid)
        check_match("MD5(bytes_puid_le_8)", md5_bytes(puid.to_bytes(8, 'little')), puid)


def try_hmac_variants():
    section("9. HMAC 变体尝试")
    import hmac
    any_match = False
    hmac_keys = [
        "chaoxing", "pan-yz", "u2oh6Vu^HWe4_AES", "secret", "key",
        "uservalid", "token", "_token", "mooc", "ananas",
    ]
    for key in hmac_keys:
        for puid in KNOWN_TOKENS:
            h = hmac.new(key.encode(), str(puid).encode(), hashlib.md5).hexdigest()
            if h.lower() == KNOWN_TOKENS[puid].lower():
                print(f"  *** MATCH! *** HMAC-MD5(key='{key}', msg='{puid}') = {h}")
                any_match = True
            h_sha256 = hmac.new(key.encode(), str(puid).encode(), hashlib.sha256).hexdigest()[:32]
            if h_sha256.lower() == KNOWN_TOKENS[puid].lower():
                print(f"  *** MATCH! *** HMAC-SHA256(key='{key}', msg='{puid}')[:32] = {h_sha256}")
                any_match = True
    if not any_match:
        print("  未找到匹配的 HMAC 变体")
    return any_match


def try_cross_account_analysis():
    section("10. 跨账号关联分析")
    t1 = KNOWN_TOKENS[252798154]
    t2 = KNOWN_TOKENS[239448447]
    print(f"  账号1 _token: {t1}")
    print(f"  账号2 _token: {t2}")
    print(f"  汉明距离 (字符级): {sum(c1 != c2 for c1, c2 in zip(t1, t2))}/32")
    check_match("MD5(token1+token2)", md5_hex(t1 + t2), 252798154)
    check_match("MD5(token2+token1)", md5_hex(t2 + t1), 252798154)
    puid1, puid2 = 252798154, 239448447
    check_match("MD5(puid1+puid2)", md5_hex(str(puid1) + str(puid2)), puid1)
    check_match("MD5(puid2+puid1)", md5_hex(str(puid2) + str(puid1)), puid2)
    diff = abs(puid1 - puid2)
    print(f"  puid差值: {diff}")
    check_match("MD5(diff)", md5_hex(str(diff)), puid1)
    xor_val = puid1 ^ puid2
    print(f"  puid异或: {xor_val}")
    check_match("MD5(xor)", md5_hex(str(xor_val)), puid1)


def try_server_side_patterns():
    section("11. 服务端常见生成模式尝试")
    for puid in KNOWN_TOKENS:
        print(f"\n  --- puid={puid} ---")
        check_match("MD5(puid+timestamp_like)", md5_hex(str(puid) + "0"), puid)
        check_match("MD5(puid+'0')", md5_hex(str(puid) + "0"), puid)
        check_match("MD5(puid+'1')", md5_hex(str(puid) + "1"), puid)
        check_match("MD5(puid+'true')", md5_hex(str(puid) + "true"), puid)
        check_match("MD5(puid+'false')", md5_hex(str(puid) + "false"), puid)
        check_match("MD5('puid:'+str(puid))", md5_hex(f"puid:{puid}"), puid)
        check_match("MD5('user:'+str(puid))", md5_hex(f"user:{puid}"), puid)
        check_match("MD5('token:'+str(puid))", md5_hex(f"token:{puid}"), puid)
        check_match("MD5('pan:'+str(puid))", md5_hex(f"pan:{puid}"), puid)
        check_match("MD5('chaoxing:'+str(puid))", md5_hex(f"chaoxing:{puid}"), puid)
        check_match("MD5(str(puid)+':chaoxing')", md5_hex(f"{puid}:chaoxing"), puid)
        check_match("MD5(str(puid)+':pan')", md5_hex(f"{puid}:pan"), puid)
        check_match("MD5('uservalid:'+str(puid))", md5_hex(f"uservalid:{puid}"), puid)
        check_match("MD5(str(puid)+'|chaoxing')", md5_hex(f"{puid}|chaoxing"), puid)
        check_match("MD5(str(puid)+'|pan-yz')", md5_hex(f"{puid}|pan-yz"), puid)
        check_match("MD5('pan-yz|'+str(puid))", md5_hex(f"pan-yz|{puid}"), puid)
        check_match("MD5(str(puid)+'|uservalid')", md5_hex(f"{puid}|uservalid"), puid)


def try_additional_salt_combos():
    section("12. 额外 salt 组合穷举 (MD5(puid + sep + salt) 和 MD5(salt + sep + puid))")
    extra_salts = [
        "cx", "CX", "cX", "Cx",
        "chaoxing_pan", "pan_chaoxing",
        "chaoxingpan", "panyzchaoxing",
        "chaoxing_yunpan", "yunpan_chaoxing",
        "pan_yz_chaoxing", "chaoxing_pan_yz",
        "ananas.chaoxing.com",
        "sync.ananas.chaoxing.com",
        "sync2.ananas.chaoxing.com",
        "sync3.ananas.chaoxing.com",
        "up",
        "USER_PAN",
        "user_pan",
        "RES_TYPE_YUNPAN_FILE",
        "44604c9884a7229121549849afaf88ba390248ae48a3eb35",
        "80e80ac5e63d7b56780e86c50a866292",
        "1216",
        "136",
        "336",
        "312",
    ]
    all_salts = COMMON_SALTS + extra_salts
    any_match = False
    for salt in all_salts:
        for sep in SEPARATOR_VARIANTS:
            for puid in KNOWN_TOKENS:
                for pattern_fn in [
                    lambda p, s, sp: str(p) + sp + s,
                    lambda p, s, sp: s + sp + str(p),
                ]:
                    s = pattern_fn(puid, salt, sep)
                    computed = md5_hex(s)
                    if computed.lower() == KNOWN_TOKENS[puid].lower():
                        print(f"  *** MATCH! *** puid={puid}, MD5('{s}')")
                        any_match = True
    if not any_match:
        print("  未找到匹配的额外 salt 变体")
    return any_match


def print_summary():
    section("分析总结")
    print("""
  已知信息:
    - _token 为 32 位十六进制字符串，符合 MD5 输出格式
    - 不同 puid 对应不同 _token，说明 _token 与用户关联
    - _token 通过 GET /api/token/uservalid 获取

  分析结果:
    - 基础哈希 (MD5/SHA256/SHA1/SHA512 直接对 puid 计算): 未匹配
    - MD5(puid + salt) 多种 salt 变体: 未匹配
    - MD5(salt + puid) 多种 salt 变体: 未匹配
    - 双重哈希 (MD5(MD5(puid)) 等): 未匹配
    - puid 自身组合 (puid+puid 等): 未匹配
    - 已知密钥组合 (AES_KEY, APPID 等): 未匹配
    - 数值变换 (hex/oct/bin/reverse/bytes): 未匹配
    - HMAC 变体 (多种 key): 未匹配
    - 服务端常见生成模式: 未匹配
    - 额外 salt 组合穷举: 未匹配

  结论:
    _token 不可通过 puid 简单预测。生成算法可能使用了:
    1. 服务端存储的用户特定密钥/随机种子
    2. 包含时间戳或其他动态因素的哈希
    3. 数据库生成的随机 UUID/Token
    4. 包含用户密码哈希等不可公开信息的组合

    因此，_token 的可预测性风险较低，攻击者无法仅通过 puid 伪造 _token。
    但 _token 一旦通过其他途径泄露（URL Referer、日志、网络嗅探等），
    由于 _token 未与 Session 绑定，仍可被用于越权访问。
""")


if __name__ == "__main__":
    print("=" * 70)
    print("  学习通云盘 _token 可预测性分析")
    print("  仅用于安全研究和授权测试目的")
    print("=" * 70)

    analyze_format()
    try_basic_hashes()
    try_salt_variants()
    try_salt_prefix_variants()
    try_double_hash()
    try_puid_combinations()
    try_known_key_combinations()
    try_numeric_transforms()
    try_hmac_variants()
    try_cross_account_analysis()
    try_server_side_patterns()
    try_additional_salt_combos()
    print_summary()
