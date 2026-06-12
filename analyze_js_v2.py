#!/usr/bin/env python3
"""
找到 xiucat 前端的 API base URL 和签到参数
"""

import requests, urllib3, re, json

urllib3.disable_warnings()

def main():
    # 下载JS
    print("下载JS...")
    r = requests.get("https://cx.xiucat.top/assets/index-BOg_gJ90.js", verify=False, timeout=30)
    js = r.text
    print(f"JS长度: {len(js)}")

    # ===== 1. 搜索 baseURL 配置 =====
    print("\n" + "=" * 70)
    print("  1. 搜索 baseURL / API 配置")
    print("=" * 70)

    # 搜索 baseURL
    for pattern in [r'baseURL\s*[:=]\s*["\']([^"\']+)["\']',
                    r'BASE_URL\s*[:=]\s*["\']([^"\']+)["\']',
                    r'apiBase\s*[:=]\s*["\']([^"\']+)["\']',
                    r'apiUrl\s*[:=]\s*["\']([^"\']+)["\']',
                    r'serverUrl\s*[:=]\s*["\']([^"\']+)["\']',
                    r'apiPrefix\s*[:=]\s*["\']([^"\']+)["\']']:
        matches = re.findall(pattern, js)
        if matches:
            print(f"  Pattern '{pattern}': {matches}")

    # 搜索 xiucat.top 域名
    xiucat_domains = re.findall(r'(https?://[a-zA-Z0-9.-]*xiucat\.top[^"\'>\s]*)', js)
    print(f"\n  xiucat.top URLs: {list(set(xiucat_domains))}")

    # 搜索 https:// URL
    https_urls = re.findall(r'["\'](https?://[^"\'>\s]{10,})["\']', js)
    relevant_urls = [u for u in https_urls if 'xiucat' in u or 'chaoxing' in u or 'api' in u]
    print(f"\n  相关URLs: {list(set(relevant_urls))}")

    # 搜索 VITE_ 环境变量
    vite_vars = re.findall(r'(VITE_[A-Z_]+)\s*[:=]', js)
    print(f"\n  VITE变量: {list(set(vite_vars))}")

    # ===== 2. 搜索 Ae 对象定义 (HTTP客户端) =====
    print("\n" + "=" * 70)
    print("  2. 搜索 HTTP 客户端配置")
    print("=" * 70)

    # 搜索 axios 创建
    axios_patterns = re.findall(r'(axios\.create\([^)]{0,500}\))', js)
    for p in axios_patterns[:5]:
        print(f"  axios.create: {p[:300]}")

    # 搜索 Ae 变量定义
    ae_patterns = re.findall(r'(Ae\s*=\s*[^;]{0,300})', js)
    for p in ae_patterns[:5]:
        print(f"  Ae定义: {p[:300]}")

    # ===== 3. 搜索请求拦截器/配置 =====
    print("\n" + "=" * 70)
    print("  3. 搜索请求拦截器")
    print("=" * 70)

    interceptor_patterns = re.findall(r'(interceptors?\.(request|response)\s*\.\s*use\s*\([^)]{0,500}\))', js)
    for p in interceptor_patterns[:5]:
        print(f"  拦截器: {p[0][:300]}")

    # ===== 4. 搜索 mode1~4 的调用位置 =====
    print("\n" + "=" * 70)
    print("  4. 搜索 mode1~4 的调用位置和参数")
    print("=" * 70)

    # 搜索 LN, RN, NN, BN 函数的调用
    for func_name, api_name in [('LN', 'mode1'), ('RN', 'mode2'), ('NN', 'mode3'), ('BN', 'mode4')]:
        # 找到函数调用
        pattern = rf'{func_name}\s*\(\s*([^)]{{0,500}})\s*\)'
        matches = re.findall(pattern, js)
        if matches:
            print(f"\n  {func_name} ({api_name}) 调用:")
            for m in matches[:5]:
                print(f"    {m[:300]}")

    # ===== 5. 搜索签到页面组件代码 =====
    print("\n" + "=" * 70)
    print("  5. 搜索签到页面组件代码")
    print("=" * 70)

    # 搜索 checkin/detail 页面
    for page_name in ['checkin/detail', 'checkin/list', 'checkin/qrscan']:
        idx = js.find(f'"{page_name}"')
        if idx != -1:
            context = js[max(0, idx-500):idx+2000]
            # 搜索签到相关函数调用
            sign_calls = re.findall(r'(mode\d|whichMode|faceScore|clockin)\s*\([^)]{0,200}\)', context)
            if sign_calls:
                print(f"\n  {page_name} 签到调用:")
                for sc in sign_calls[:10]:
                    print(f"    {sc[:200]}")

    # ===== 6. 搜索完整的签到流程代码 =====
    print("\n" + "=" * 70)
    print("  6. 搜索签到流程代码 (更大范围)")
    print("=" * 70)

    # 搜索包含 activeId 和 mode 的代码段
    # 找到签到提交的核心逻辑
    for keyword in ['handleSign', 'doSign', 'submitSign', 'startSign', 'onSign',
                    'signSubmit', 'clockinSubmit', 'handleClockin', 'doClockin']:
        idx = js.find(keyword)
        if idx != -1:
            context = js[max(0, idx-200):idx+500]
            print(f"\n  {keyword} 上下文:")
            print(f"    {context[:500]}")

    # ===== 7. 搜索环境配置 =====
    print("\n" + "=" * 70)
    print("  7. 搜索环境配置")
    print("=" * 70)

    # 搜索 import.meta.env
    env_patterns = re.findall(r'import\.meta\.env\.([A-Z_]+)', js)
    print(f"  环境变量引用: {list(set(env_patterns))}")

    # 搜索配置对象
    config_patterns = re.findall(r'config\s*[:=]\s*\{[^}]{0,500}\}', js)
    for p in config_patterns[:5]:
        if 'url' in p.lower() or 'api' in p.lower() or 'base' in p.lower():
            print(f"  配置: {p[:300]}")

    # ===== 8. 直接搜索 api-test 或 api.xiucat =====
    print("\n" + "=" * 70)
    print("  8. 搜索 API 域名配置")
    print("=" * 70)

    # 搜索所有URL
    all_urls = re.findall(r'["\'](https?://[^"\'>\s]+)["\']', js)
    api_urls = [u for u in all_urls if 'api' in u.lower() or 'xiucat' in u.lower()]
    print(f"  API URLs: {list(set(api_urls))}")

    # 搜索域名
    domains = re.findall(r'["\']([a-zA-Z0-9.-]+\.xiucat\.top)["\']', js)
    print(f"  xiucat域名: {list(set(domains))}")

    # ===== 9. 搜索 /v2/ 前缀 =====
    print("\n" + "=" * 70)
    print("  9. 搜索 /v2/ 前缀配置")
    print("=" * 70)

    v2_prefix = re.findall(r'["\'](/v2/[^"\']+)["\']', js)
    print(f"  /v2/ 路径: {list(set(v2_prefix))}")

    # 搜索 prefix 配置
    prefix_patterns = re.findall(r'prefix\s*[:=]\s*["\']([^"\']+)["\']', js)
    print(f"  prefix: {list(set(prefix_patterns))}")

    # ===== 10. 尝试不同的 API base URL =====
    print("\n" + "=" * 70)
    print("  10. 尝试不同的 API base URL")
    print("=" * 70)

    # 登录获取token
    r = requests.post("https://api-test.xiucat.top/v2/student/auth/login",
                      json={"phone": "18436633997", "password": "3.1415926Cpy"},
                      verify=False, timeout=20)
    token = r.json()["data"]["tInfo"]["accessToken"]
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 尝试不同的base URL + /clockin/mode1
    base_urls = [
        "https://api-test.xiucat.top",
        "https://api-test.xiucat.top/v2",
        "https://cx.xiucat.top",
        "https://cx.xiucat.top/api",
        "https://sign.xiucat.top",
        "https://app.xiucat.top",
    ]

    for base in base_urls:
        for path in ['/clockin/whichMode', '/v2/clockin/whichMode', '/clockin/mode1', '/v2/clockin/mode1']:
            url = base + path
            try:
                r = requests.post(url,
                                  headers=auth_headers,
                                  json={"activeId": "1000155099942"},
                                  verify=False, timeout=10)
                if r.status_code != 0 and "Cannot POST" not in r.text and "404" not in r.text:
                    print(f"  ★ {url}: Status={r.status_code}, Body={r.text[:200]}")
                elif "Cannot POST" not in r.text:
                    print(f"  {url}: Status={r.status_code}, Body={r.text[:100]}")
            except requests.exceptions.SSLError:
                pass
            except requests.exceptions.ConnectTimeout:
                pass
            except Exception as e:
                err_type = type(e).__name__
                if err_type not in ['SSLError', 'ConnectTimeout', 'ConnectionError']:
                    print(f"  {url}: {err_type}")

    # ===== 11. 分析 Ae 对象的完整定义 =====
    print("\n" + "=" * 70)
    print("  11. 分析 Ae (HTTP客户端) 的完整定义")
    print("=" * 70)

    # 找到 Ae 的定义位置
    # Ae.post("/clockin/mode1", e, void 0, void 0, co)
    # 这意味着 Ae 是一个封装了 axios 的对象
    # 搜索 Ae 的创建

    # 搜索 "Ae=" 或 "const Ae" 或 "var Ae" 或 "let Ae"
    for pattern in [r'Ae\s*=\s*\w+\([^)]{0,200}\)',
                    r'const\s+Ae\s*=\s*[^;]{0,300}',
                    r'var\s+Ae\s*=\s*[^;]{0,300}',
                    r'let\s+Ae\s*=\s*[^;]{0,300}']:
        matches = re.findall(pattern, js)
        if matches:
            print(f"  Pattern '{pattern[:30]}...':")
            for m in matches[:3]:
                print(f"    {m[:300]}")

    # 搜索 createRequest 或 createHttp
    for pattern in [r'createRequest\s*\([^)]{0,500}\)',
                    r'createHttp\s*\([^)]{0,500}\)',
                    r'createAxios\s*\([^)]{0,500}\)',
                    r'createInstance\s*\([^)]{0,500}\)']:
        matches = re.findall(pattern, js)
        if matches:
            print(f"\n  创建函数:")
            for m in matches[:3]:
                print(f"    {m[:300]}")

    # 搜索 uni.request (因为这是uni-app)
    uni_request = re.findall(r'uni\.request\s*\([^)]{0,500}\)', js)
    print(f"\n  uni.request 调用数: {len(uni_request)}")

    # 搜索请求配置
    request_config = re.findall(r'(request\s*[:=]\s*\{[^}]{0,500}\})', js)
    for rc in request_config[:3]:
        if 'url' in rc or 'base' in rc:
            print(f"  请求配置: {rc[:300]}")


if __name__ == "__main__":
    main()
