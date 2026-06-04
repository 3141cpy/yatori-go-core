# 学习通头像图片安全漏洞研究 Spec

## Why
学习通的头像/图片上传功能可能存在多种安全漏洞，包括但不限于：图片马（将WebShell代码嵌入图片文件绕过上传检测）、存储型XSS（通过文件名/EXIF/Metadata注入恶意脚本）、CSRF（替他人上传头像）、任意文件上传（绕过文件类型检测）、SSRF（通过图片URL触发服务端请求）等。需要针对这些攻击面进行深入研究。

## What Changes
- 测试头像/图片上传接口是否可上传图片马（WebShell嵌入图片）
- 测试文件名XSS（特殊字符文件名是否被正确过滤）
- 测试EXIF/Metadata XSS（图片元数据中的恶意脚本是否被保留和渲染）
- 测试Content-Type欺骗（修改MIME类型绕过检测）
- 测试文件扩展名绕过（双扩展名、空字节、大小写等）
- 测试CSRF替他人上传头像
- 测试图片存储路径是否可遍历
- 测试SVG/XSS（上传SVG文件执行脚本）
- 生成技术报告

## Impact
- Affected APIs:
  - `https://pan-yz.chaoxing.com/upload` (uploadtype=face/normal)
  - `https://pan-yz.chaoxing.com/api/token/uservalid`
  - `https://passport2-api.chaoxing.com/api/getUserFaceid`
  - `https://mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo`
  - `https://groupweb.chaoxing.com/pc/resource/addResource`
- Test accounts: 教师 19712720708/3.1415926Cpy (puid=402644510), 学生 18436633997/3.1415926Cpy (puid=431407443)

## ADDED Requirements

### Requirement: 图片马上传测试
系统 SHALL 测试头像上传接口是否可上传包含WebShell代码的图片文件。

#### Scenario: 图片+PHP WebShell
- **WHEN** 上传一个正常图片文件，末尾追加PHP WebShell代码（`<?php eval($_POST['cmd']); ?>`）
- **THEN** 验证文件是否被接受，以及上传后的文件是否可被解析为PHP

#### Scenario: 图片+JSP WebShell
- **WHEN** 上传一个正常图片文件，末尾追加JSP WebShell代码
- **THEN** 验证文件是否被接受

#### Scenario: 图片+HTML/JS代码
- **WHEN** 上传一个正常图片文件，末尾追加HTML/JS恶意代码
- **THEN** 验证文件是否被接受，以及访问时是否执行JS

### Requirement: 存储型XSS测试
系统 SHALL 测试头像上传接口是否存在存储型XSS漏洞。

#### Scenario: 文件名XSS
- **WHEN** 上传文件名为`<img src=x onerror=alert(1)>.jpg`或`test"><script>alert(1)</script>.jpg`的图片
- **THEN** 验证文件名是否被正确过滤，在页面渲染时是否触发XSS

#### Scenario: EXIF Metadata XSS
- **WHEN** 上传EXIF信息中包含`<script>alert(1)</script>`的图片
- **THEN** 验证EXIF信息是否被保留，是否在展示时触发XSS

#### Scenario: SVG XSS
- **WHEN** 上传包含`<script>alert(document.cookie)</script>`的SVG文件（伪装为.jpg）
- **THEN** 验证SVG是否被接受，访问时是否执行脚本

### Requirement: 文件类型绕过测试
系统 SHALL 测试头像上传接口的文件类型检测是否可被绕过。

#### Scenario: Content-Type欺骗
- **WHEN** 上传非图片文件但设置Content-Type为image/jpeg
- **THEN** 验证是否仅依赖Content-Type判断文件类型

#### Scenario: 双扩展名绕过
- **WHEN** 上传文件名为`test.php.jpg`或`test.jpg.php`的文件
- **THEN** 验证扩展名解析逻辑

#### Scenario: 空字节绕过
- **WHEN** 上传文件名为`test.php%00.jpg`的文件
- **THEN** 验证空字节是否被正确处理

#### Scenario: 大小写绕过
- **WHEN** 上传文件名为`test.PhP`或`test.JSP`的文件
- **THEN** 验证扩展名检测是否区分大小写

#### Scenario: 特殊文件类型
- **WHEN** 上传.html、.htm、.svg、.xml、.json文件
- **THEN** 验证是否可以上传非图片类型文件

### Requirement: CSRF头像上传测试
系统 SHALL 测试头像上传接口是否存在CSRF漏洞。

#### Scenario: 替他人上传头像
- **WHEN** 通过CSRF构造请求，使用他人puid上传头像
- **THEN** 验证是否可以替他人修改头像

### Requirement: 图片存储路径安全测试
系统 SHALL 测试上传图片的存储路径和访问方式的安全性。

#### Scenario: 图片URL直接访问
- **WHEN** 不携带Cookie直接访问上传的图片URL
- **THEN** 验证图片是否需要认证才能访问

#### Scenario: 路径遍历
- **WHEN** 在文件名中包含`../`等路径遍历字符
- **THEN** 验证是否可以上传到非预期目录

### Requirement: 技术报告生成
系统 SHALL 生成完整的头像图片安全漏洞技术报告。
