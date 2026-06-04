# Tasks

- [ ] Task 1: getUserFaceid接口IDOR验证
  - [ ] 1.1 计算教师puid(402644510)的enc值: md5("402644510uWwjeEKsri")
  - [ ] 1.2 学生账号调用getUserFaceid获取教师人脸图片URL
  - [ ] 1.3 无Cookie调用getUserFaceid验证是否需要登录
  - [ ] 1.4 计算其他已知puid的enc值并批量测试
  - [ ] 1.5 分析返回的人脸图片URL结构和访问权限

- [ ] Task 2: 人脸图片上传IDOR验证
  - [ ] 2.1 学生A获取云盘Token
  - [ ] 2.2 学生A使用自己Token+教师puid上传人脸图片
  - [ ] 2.3 学生A使用教师Token+教师puid上传人脸图片（Token CSRF获取）
  - [ ] 2.4 验证上传后教师的objectId是否被替换
  - [ ] 2.5 测试uploadtype参数（face vs normal）的安全差异

- [ ] Task 3: 人脸识别绕过验证
  - [ ] 3.1 学生上传自己人脸获取objectId
  - [ ] 3.2 学生使用自己objectId调用clientfacecheckstatus
  - [ ] 3.3 学生使用他人objectId调用clientfacecheckstatus（IDOR）
  - [ ] 3.4 测试objectId有效期和重复使用
  - [ ] 3.5 测试/qr/updateqrstatus接口的参数篡改

- [ ] Task 4: 头像URL可预测性与未授权访问测试
  - [ ] 4.1 收集多个人脸图片URL，分析命名模式
  - [ ] 4.2 测试直接访问图片URL（无Cookie）
  - [ ] 4.3 测试URL遍历（修改objectId/puid等参数）
  - [ ] 4.4 测试头像图片CDN配置（CORS、缓存头等）

- [ ] Task 5: 技术报告生成
  - [ ] 5.1 汇总所有发现，按漏洞类型分类
  - [ ] 5.2 为每个漏洞提供：接口路径、参数、利用方法、影响范围、修复建议
  - [ ] 5.3 生成完整技术报告文件

# Task Dependencies
- Task 2 depends on Task 1（需要先验证Token获取和enc计算）
- Task 3 depends on Task 2（需要先上传人脸获取objectId）
- Task 5 depends on all previous tasks
