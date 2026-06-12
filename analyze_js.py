#!/usr/bin/env python3
"""
分析 cx.xiucat.top 前端JS代码，找到签到API的参数名
"""

import requests, urllib3, re, json

urllib3.disable_warnings()

def main():
    print("=" * 70)
    print("  分析 cx.xiucat.top 前端JS代码")
    print("=" * 70)

    # 下载JS
    print("\n  下载 index-BOg_gJ90.js...")
    r = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
    js = r.text
    print(f"  JS长度: {len(js)}")

    # ===== 1. 搜索签到相关的API调用 =====
    print("\n" + "=" * 70)
    print("  1. 搜索签到相关API调用")
    print("=" * 70)

    # 搜索 /v2/ 开头的API路径
    v2_apis = re.findall(r'["\'](/v2/[^"\']+)["\']', js)
    print(f"  V2 API路径: {list(set(v2_apis))}")

    # 搜索 api-test.xiucat.top
    xiucat_apis = re.findall(r'api-test\.xiucat\.top([^"\'>\s]+)', js)
    print(f"  xiucat API: {list(set(xiucat_apis))}")

    # 搜索 sign 相关
    sign_apis = re.findall(r'["\']([^"\']*sign[^"\']*)["\']', js, re.IGNORECASE)
    sign_apis = [a for a in sign_apis if 'http' in a or '/v2/' in a or '/api/' in a]
    print(f"  签到API: {list(set(sign_apis))}")

    # ===== 2. 搜索 "是否验证" 相关代码 =====
    print("\n" + "=" * 70)
    print("  2. 搜索 '是否验证' 相关代码")
    print("=" * 70)

    # 搜索中文 "验证"
    for kw in ['验证', '是否', '补签', '签到']:
        indices = []
        idx = 0
        while True:
            idx = js.find(kw, idx)
            if idx == -1:
                break
            indices.append(idx)
            idx += len(kw)
        if indices:
            print(f"\n  关键词 '{kw}' 出现 {len(indices)} 次:")
            for i in indices[:10]:
                context = js[max(0, i-100):i+100]
                print(f"    ...{context}...")

    # ===== 3. 搜索签到函数 =====
    print("\n" + "=" * 70)
    print("  3. 搜索签到函数定义")
    print("=" * 70)

    # 搜索函数定义
    sign_functions = re.findall(r'(function\s+\w*[Ss]ign\w*|const\s+\w*[Ss]ign\w*\s*=|let\s+\w*[Ss]ign\w*\s*=|var\s+\w*[Ss]ign\w*\s*=)', js)
    print(f"  签到函数: {sign_functions[:20]}")

    # 搜索 POST 请求
    post_calls = re.findall(r'\.post\s*\(\s*["\']([^"\']+)["\']', js)
    print(f"  POST请求: {list(set(post_calls))}")

    # ===== 4. 搜索参数定义 =====
    print("\n" + "=" * 70)
    print("  4. 搜索签到参数定义")
    print("=" * 70)

    # 搜索 activeId 附近的代码
    idx = 0
    while True:
        idx = js.find('activeId', idx)
        if idx == -1:
            break
        context = js[max(0, idx-200):idx+200]
        print(f"\n  activeId 上下文 (位置 {idx}):")
        print(f"    ...{context}...")
        idx += len('activeId')
        if idx > 50000:  # 只搜索前面部分
            break

    # ===== 5. 搜索 normal 签到相关 =====
    print("\n" + "=" * 70)
    print("  5. 搜索 normal 签到相关")
    print("=" * 70)

    idx = 0
    count = 0
    while True:
        idx = js.find('normal', idx)
        if idx == -1:
            break
        context = js[max(0, idx-150):idx+150]
        if 'sign' in context.lower() or 'active' in context.lower():
            print(f"\n  normal 上下文 (位置 {idx}):")
            print(f"    ...{context}...")
            count += 1
        idx += len('normal')
        if count >= 5:
            break

    # ===== 6. 搜索所有参数名模式 =====
    print("\n" + "=" * 70)
    print("  6. 搜索对象字面量中的参数名")
    print("=" * 70)

    # 搜索包含 activeId 的对象定义
    obj_patterns = re.findall(r'\{[^}]*activeId[^}]*\}', js)
    for p in obj_patterns[:10]:
        print(f"  对象: {p[:300]}")

    # ===== 7. 搜索 locationText 相关 =====
    print("\n" + "=" * 70)
    print("  7. 搜索 locationText 相关")
    print("=" * 70)

    idx = 0
    count = 0
    while True:
        idx = js.find('locationText', idx)
        if idx == -1:
            break
        context = js[max(0, idx-200):idx+200]
        print(f"\n  locationText 上下文 (位置 {idx}):")
        print(f"    ...{context}...")
        idx += len('locationText')
        count += 1
        if count >= 5:
            break

    # ===== 8. 搜索 enc 相关 =====
    print("\n" + "=" * 70)
    print("  8. 搜索 enc 参数相关 (签到用)")
    print("=" * 70)

    # 搜索 enc 作为参数名
    enc_as_param = re.findall(r'["\']enc["\']\s*:', js)
    print(f"  enc作为参数: {len(enc_as_param)} 次")

    # 搜索 enc 在签到上下文中的使用
    for match in re.finditer(r'enc', js):
        idx = match.start()
        context = js[max(0, idx-100):idx+100]
        if any(kw in context.lower() for kw in ['sign', 'active', 'qrcode', 'course']):
            print(f"\n  enc 签到上下文 (位置 {idx}):")
            print(f"    ...{context}...")

    # ===== 9. 搜索 nickname 相关 =====
    print("\n" + "=" * 70)
    print("  9. 搜索 nickname 相关")
    print("=" * 70)

    idx = 0
    count = 0
    while True:
        idx = js.find('nickname', idx)
        if idx == -1:
            break
        context = js[max(0, idx-200):idx+200]
        print(f"\n  nickname 上下文 (位置 {idx}):")
        print(f"    ...{context}...")
        idx += len('nickname')
        count += 1
        if count >= 5:
            break

    # ===== 10. 搜索 courseName 相关 =====
    print("\n" + "=" * 70)
    print("  10. 搜索 courseName 相关")
    print("=" * 70)

    idx = 0
    count = 0
    while True:
        idx = js.find('courseName', idx)
        if idx == -1:
            break
        context = js[max(0, idx-200):idx+200]
        if 'sign' in context.lower() or 'active' in context.lower():
            print(f"\n  courseName 签到上下文 (位置 {idx}):")
            print(f"    ...{context}...")
            count += 1
        idx += len('courseName')
        if count >= 5:
            break

    # ===== 11. 搜索完整的签到请求构造 =====
    print("\n" + "=" * 70)
    print("  11. 搜索完整的签到请求构造")
    print("=" * 70)

    # 搜索包含多个签到参数的代码段
    sign_params_patterns = [
        r'activeId.*?courseId.*?classId',
        r'courseId.*?classId.*?activeId',
        r'nickname.*?courseName',
        r'courseName.*?nickname',
    ]
    for pattern in sign_params_patterns:
        matches = re.findall(pattern, js[:100000], re.DOTALL)
        if matches:
            print(f"  Pattern '{pattern}': {len(matches)} matches")
            for m in matches[:3]:
                print(f"    {m[:200]}")

    # ===== 12. 搜索特定代码段 =====
    print("\n" + "=" * 70)
    print("  12. 搜索 /v2/student/sign/ 附近的代码")
    print("=" * 70)

    for path in ['/v2/student/sign/normal', '/v2/student/sign/qrcode', '/v2/student/sign/location',
                 '/v2/student/sign/activities', '/v2/student/sign/courses']:
        idx = js.find(path)
        if idx != -1:
            context = js[max(0, idx-500):idx+500]
            print(f"\n  {path} 上下文:")
            print(f"    ...{context}...")
        else:
            print(f"\n  {path}: 未找到")

    # ===== 13. 搜索 validate/verify 相关的中文 =====
    print("\n" + "=" * 70)
    print("  13. 搜索验证相关中文")
    print("=" * 70)

    chinese_verify = re.findall(r'["\']([\u4e00-\u9fff]*验证[\u4e00-\u9fff]*)["\']', js)
    print(f"  中文验证: {list(set(chinese_verify))}")

    chinese_is = re.findall(r'["\']([\u4e00-\u9fff]*是否[\u4e00-\u9fff]*)["\']', js)
    print(f"  中文是否: {list(set(chinese_is))}")

    # 搜索错误消息
    error_msgs = re.findall(r'["\']([\u4e00-\u9fff]+必须是[\u4e00-\u9fff]+)["\']', js)
    print(f"  错误消息: {list(set(error_msgs))}")

    # 搜索字段验证
    field_validations = re.findall(r'["\']([\u4e00-\u9fff]+不能为空)["\']', js)
    print(f"  字段验证: {list(set(field_validations))}")


if __name__ == "__main__":
    main()
