# Tasks

- [x] Task 1: 图片马上传测试
  - [x] 1.1 创建正常JPG图片+PHP WebShell的图片马文件
  - [x] 1.2 创建正常JPG图片+HTML/JS恶意代码的图片马文件
  - [x] 1.3 通过pan-yz.chaoxing.com/upload上传图片马（uploadtype=face和normal两种）
  - [x] 1.4 检查上传后的文件URL，验证是否可被解析执行
  - [x] 1.5 测试图片马通过mooc1-api知识上传接口

- [x] Task 2: 存储型XSS测试
  - [x] 2.1 文件名XSS：上传文件名为`<img src=x onerror=alert(1)>.jpg`的图片
  - [x] 2.2 文件名XSS：上传文件名为`test"><script>alert(1)</script>.jpg`的图片
  - [x] 2.3 EXIF XSS：创建EXIF Comment中包含`<script>alert(1)</script>`的图片
  - [x] 2.4 SVG XSS：上传包含JS代码的SVG文件（伪装为.jpg扩展名）
  - [x] 2.5 SVG XSS：直接上传.svg文件
  - [x] 2.6 验证上传后文件名/EXIF是否被保留，是否在页面中渲染

- [x] Task 3: 文件类型绕过测试
  - [x] 3.1 Content-Type欺骗：上传.php文件但Content-Type设为image/jpeg
  - [x] 3.2 双扩展名：test.php.jpg, test.jpg.php, test.php.jpg.php
  - [x] 3.3 空字节：test.php%00.jpg
  - [x] 3.4 大小写：test.PhP, test.JSP, test.HtMl
  - [x] 3.5 特殊类型：.html, .htm, .svg, .xml, .json, .txt, .py, .sh
  - [x] 3.6 无扩展名文件
  - [x] 3.7 .htaccess文件上传

- [x] Task 4: CSRF头像上传测试
  - [x] 4.1 获取学生A的云盘Token
  - [x] 4.2 使用学生A的Token+教师puid上传头像（IDOR）
  - [x] 4.3 构造CSRF PoC替他人上传头像
  - [x] 4.4 验证是否成功修改他人头像

- [x] Task 5: 图片存储路径安全测试
  - [x] 5.1 路径遍历：文件名包含`../`
  - [x] 5.2 无Cookie访问上传的图片URL
  - [x] 5.3 分析图片URL的命名规律和可预测性
  - [x] 5.4 测试图片URL的CORS配置

- [x] Task 6: getUserFaceid接口安全测试（附加）
  - [x] 6.1 验证硬编码盐值"uWwjeEKsri"是否可获取任意用户人脸图片
  - [x] 6.2 无Cookie访问getUserFaceid
  - [x] 6.3 评估人脸图片泄露风险

- [x] Task 7: 技术报告生成
  - [x] 7.1 汇总所有发现，按漏洞类型分类
  - [x] 7.2 为每个漏洞提供：接口路径、攻击方法、PoC、影响范围、修复建议
  - [x] 7.3 生成完整技术报告文件 `/workspace/avatar_vuln_tech_report.md`

# Task Dependencies
- Task 2 depends on Task 1
- Task 4 depends on Task 1
- Task 5 depends on Task 1
- Task 7 depends on all previous tasks
