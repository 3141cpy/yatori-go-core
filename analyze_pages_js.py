#!/usr/bin/env python3
"""
下载并分析 xiucat 签到详情页JS - 找到签到参数
"""

import requests, urllib3, re, json

urllib3.disable_warnings()

def main():
    # 下载签到详情页JS
    print("下载 pages-checkin-detail.DEc-Ee2u.js...")
    r = requests.get("https://cx.xiucat.top/assets/pages-checkin-detail.DEc-Ee2u.js",
                     verify=False, timeout=30)
    js = r.text
    print(f"JS长度: {len(js)}")

    # 打印完整内容 (如果不太长)
    if len(js) < 50000:
        print(f"\n完整JS内容:\n{js}")
    else:
        print(f"\nJS前10000字符:\n{js[:10000]}")

    # 搜索关键参数
    print("\n" + "=" * 70)
    print("  搜索签到参数")
    print("=" * 70)

    # 搜索 mode1 调用
    for kw in ['mode1', 'mode2', 'mode3', 'mode4', 'LN(', 'RN(', 'NN(', 'BN(',
               'activeId', 'signType', 'address', 'location', 'enc',
               'courseName', 'nickname', 'fid', 'locationText', 'name',
               'otherJson', 'facePunch', 'seq']:
        idx = 0
        count = 0
        while True:
            idx = js.find(kw, idx)
            if idx == -1:
                break
            context = js[max(0, idx-150):idx+150]
            print(f"\n  '{kw}' 位置 {idx}:")
            print(f"  {context[:300]}")
            idx += 1
            count += 1
            if count >= 5:
                break

    # 下载签到列表页JS
    print("\n\n" + "=" * 70)
    print("  下载 pages-checkin-list.BFJFWtJt.js")
    print("=" * 70)

    r = requests.get("https://cx.xiucat.top/assets/pages-checkin-list.BFJFWtJt.js",
                     verify=False, timeout=30)
    js2 = r.text
    print(f"JS长度: {len(js2)}")

    if len(js2) < 50000:
        print(f"\n完整JS内容:\n{js2}")
    else:
        print(f"\nJS前10000字符:\n{js2[:10000]}")

    # 搜索关键参数
    for kw in ['mode1', 'activeId', 'signType', 'courseName', 'nickname',
               'otherJson', 'fid', 'address', 'location']:
        idx = 0
        count = 0
        while True:
            idx = js2.find(kw, idx)
            if idx == -1:
                break
            context = js2[max(0, idx-150):idx+150]
            if 'sign' in context.lower() or 'clockin' in context.lower() or 'active' in context.lower():
                print(f"\n  '{kw}' 位置 {idx}:")
                print(f"  {context[:300]}")
            idx += 1
            count += 1
            if count >= 5:
                break

    # 下载扫码签到页JS
    print("\n\n" + "=" * 70)
    print("  下载 pages-checkin-qrscan.CXi6tRm7.js")
    print("=" * 70)

    r = requests.get("https://cx.xiucat.top/assets/pages-checkin-qrscan.CXi6tRm7.js",
                     verify=False, timeout=30)
    js3 = r.text
    print(f"JS长度: {len(js3)}")

    if len(js3) < 50000:
        print(f"\n完整JS内容:\n{js3}")
    else:
        # 搜索签到参数
        for kw in ['mode1', 'mode2', 'LN(', 'RN(', 'activeId', 'signType',
                   'enc', 'address', 'location', 'courseName', 'nickname']:
            idx = 0
            count = 0
            while True:
                idx = js3.find(kw, idx)
                if idx == -1:
                    break
                context = js3[max(0, idx-200):idx+200]
                print(f"\n  '{kw}' 位置 {idx}:")
                print(f"  {context[:400]}")
                idx += 1
                count += 1
                if count >= 3:
                    break


if __name__ == "__main__":
    main()
