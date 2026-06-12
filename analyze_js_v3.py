#!/usr/bin/env python3
"""
深入分析 cx.xiucat.top JS代码 - 找到签到表单参数构造
"""

import requests, urllib3, re, json

urllib3.disable_warnings()

def main():
    print("下载JS...")
    r = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
    js = r.text
    print(f"JS长度: {len(js)}")

    # ===== 1. 找到签到详情页面的代码 =====
    print("\n" + "=" * 70)
    print("  1. 搜索签到详情页面代码")
    print("=" * 70)

    # 搜索 checkin/detail 相关的路由和组件
    # 在uni-app中，页面组件通常在路由定义附近
    checkin_routes = []
    idx = 0
    while True:
        idx = js.find('checkin', idx)
        if idx == -1:
            break
        context = js[max(0, idx-100):idx+200]
        if 'path' in context or 'page' in context or 'component' in context:
            checkin_routes.append((idx, context))
        idx += 1

    print(f"  找到 {len(checkin_routes)} 个checkin相关路由")
    for pos, ctx in checkin_routes[:10]:
        print(f"  位置 {pos}: {ctx[:200]}")

    # ===== 2. 搜索签到提交函数 =====
    print("\n" + "=" * 70)
    print("  2. 搜索签到提交函数")
    print("=" * 70)

    # 搜索 LN (mode1) 的调用
    # LN(e) 意味着参数 e 被传入
    # 需要找到 e 是怎么构造的

    # 搜索所有函数调用模式
    # 在minified JS中，函数调用通常是 LN(someVar)
    # 我们需要找到 someVar 的构造位置

    # 搜索 "LN(" 的所有位置
    ln_positions = []
    idx = 0
    while True:
        idx = js.find('LN(', idx)
        if idx == -1:
            break
        ln_positions.append(idx)
        idx += 1

    print(f"  LN(mode1) 调用位置: {ln_positions}")

    # 对于每个调用位置，向上搜索参数构造
    for pos in ln_positions:
        # 获取更大范围的上下文
        context = js[max(0, pos-3000):pos+500]

        # 搜索对象构造 {...}
        # 在minified JS中，参数通常是内联构造的
        # 例如: LN({activeId:t.value,address:e.value,...})

        # 搜索包含 activeId 的代码段
        active_idx = context.rfind('activeId')
        if active_idx != -1:
            param_context = context[max(0, active_idx-200):active_idx+500]
            print(f"\n  LN调用中的activeId上下文:")
            print(f"  {param_context[:600]}")

    # ===== 3. 搜索 signType 的使用 =====
    print("\n" + "=" * 70)
    print("  3. 搜索 signType 的使用")
    print("=" * 70)

    idx = 0
    count = 0
    while True:
        idx = js.find('signType', idx)
        if idx == -1:
            break
        context = js[max(0, idx-200):idx+200]
        print(f"\n  signType 位置 {idx}:")
        print(f"  {context[:300]}")
        idx += 1
        count += 1
        if count >= 10:
            break

    # ===== 4. 搜索 "是否验证" 相关代码 =====
    print("\n" + "=" * 70)
    print("  4. 搜索 '是否验证' 相关代码")
    print("=" * 70)

    # 搜索中文
    for kw in ['是否验证', '验证', '是否', '补签', '签到码', '签入']:
        idx = 0
        while True:
            idx = js.find(kw, idx)
            if idx == -1:
                break
            context = js[max(0, idx-100):idx+100]
            print(f"  '{kw}' 位置 {idx}: {context[:200]}")
            idx += 1

    # ===== 5. 搜索 DTO/验证装饰器 =====
    print("\n" + "=" * 70)
    print("  5. 搜索验证相关字段 (从错误消息推断)")
    print("=" * 70)

    # "是否验证必须是数字" 这个错误消息来自服务端
    # 在NestJS中，这通常来自 class-validator 的 @IsNumber() 装饰器
    # 对应的DTO字段名可能是 isVerify, needVerify 等
    # 但错误消息可能是自定义的

    # 让我搜索JS中所有发送到 /student/sign/normal 的请求构造
    # 搜索 "student/sign" 附近的代码
    idx = 0
    while True:
        idx = js.find('student/sign', idx)
        if idx == -1:
            break
        context = js[max(0, idx-500):idx+500]
        print(f"\n  student/sign 位置 {idx}:")
        print(f"  {context[:800]}")
        idx += 1

    # ===== 6. 搜索表单数据构造 =====
    print("\n" + "=" * 70)
    print("  6. 搜索表单数据构造")
    print("=" * 70)

    # 搜索包含多个签到相关字段的对象
    # 在minified JS中，对象构造通常是 {key1:val1,key2:val2,...}
    patterns = [
        r'\{[^}]*activeId[^}]*signType[^}]*\}',
        r'\{[^}]*signType[^}]*activeId[^}]*\}',
        r'\{[^}]*activeId[^}]*address[^}]*\}',
        r'\{[^}]*address[^}]*activeId[^}]*\}',
        r'\{[^}]*activeId[^}]*location[^}]*\}',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, js[:300000])
        if matches:
            print(f"\n  Pattern '{pattern[:30]}...':")
            for m in matches[:3]:
                print(f"  {m[:300]}")

    # ===== 7. 搜索签到页面组件的setup函数 =====
    print("\n" + "=" * 70)
    print("  7. 搜索签到页面组件")
    print("=" * 70)

    # 在uni-app中，页面组件通常有 setup() 函数
    # 搜索 checkin/detail 页面的setup函数

    # 找到 checkin/detail 的路由定义
    detail_idx = js.find('"checkin/detail"')
    if detail_idx == -1:
        detail_idx = js.find("'checkin/detail'")

    if detail_idx != -1:
        # 获取后面的代码
        after_detail = js[detail_idx:detail_idx+10000]
        print(f"  checkin/detail 后的代码 (前2000字符):")
        print(f"  {after_detail[:2000]}")

    # ===== 8. 搜索所有包含 "mode1" 或 "mode2" 的代码 =====
    print("\n" + "=" * 70)
    print("  8. 搜索 mode1/mode2 调用上下文")
    print("=" * 70)

    for mode in ['mode1', 'mode2', 'mode3', 'mode4']:
        idx = js.find(f'{mode}')
        while idx != -1:
            context = js[max(0, idx-500):idx+500]
            if 'clockin' in context or 'sign' in context.lower():
                print(f"\n  {mode} 位置 {idx}:")
                print(f"  {context[:600]}")
                break
            idx = js.find(f'{mode}', idx + 1)

    # ===== 9. 搜索 "otherJson" 字段 =====
    print("\n" + "=" * 70)
    print("  9. 搜索 otherJson 字段")
    print("=" * 70)

    idx = 0
    count = 0
    while True:
        idx = js.find('otherJson', idx)
        if idx == -1:
            break
        context = js[max(0, idx-200):idx+200]
        print(f"  otherJson 位置 {idx}: {context[:300]}")
        idx += 1
        count += 1
        if count >= 5:
            break

    # ===== 10. 搜索 "punchOn" 和 "punchOff" =====
    print("\n" + "=" * 70)
    print("  10. 搜索 punch 相关字段")
    print("=" * 70)

    for kw in ['punchOn', 'punchOff', 'punchConfig', 'punchSetting', 'punchOrder',
               'clockIn', 'clockOn', 'clockOff']:
        idx = js.find(kw, 0)
        if idx != -1:
            context = js[max(0, idx-100):idx+200]
            print(f"  {kw} 位置 {idx}: {context[:200]}")


if __name__ == "__main__":
    main()
