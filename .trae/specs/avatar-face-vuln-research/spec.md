# 学习通头像/人脸图片漏洞深入研究 Spec

## Why
通过分析代码库中的Go API文件，发现了学习通头像和人脸识别系统的多个潜在安全漏洞，包括：人脸图片获取接口的加密盐值硬编码（`md5(puid + "uWwjeEKsri")`）、云盘Token可被CSRF窃取用于上传伪造人脸、头像上传接口缺乏权限校验等。需要对这些漏洞进行深入验证和评估。

## What Changes
- 验证`getUserFaceid`接口的加密算法是否可被利用获取任意用户人脸图片
- 测试头像/人脸图片上传接口是否存在IDOR（使用他人puid和token上传）
- 测试头像URL是否可被遍历/预测
- 测试人脸识别绕过（使用他人人脸图片通过验证）
- 评估头像图片存储路径的安全性
- 生成技术报告

## Impact
- Affected APIs:
  - `https://passport2-api.chaoxing.com/api/getUserFaceid?enc={md5(puid+"uWwjeEKsri")}&token=4faa8662c59590c6f43ae9fe5b002b42`
  - `https://pan-yz.chaoxing.com/upload` (uploadtype=face)
  - `https://pan-yz.chaoxing.com/api/token/uservalid`
  - `https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus`
  - `https://mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo`
  - `https://mooc1-api.chaoxing.com/qr/updateqrstatus`
  - `https://mooc1-api.chaoxing.com/mooc-ans/facephoto/continuelearn`
- Test accounts: 教师 19712720708/3.1415926Cpy (puid=402644510), 学生 18436633997/3.1415926Cpy (puid=431407443)

## 已知关键信息

### getUserFaceid接口加密算法泄露
```go
hash := md5.Sum([]byte(puid + "uWwjeEKsri"))
enc := hex.EncodeToString(hash[:])
urlStr := "https://passport2-api.chaoxing.com/api/getUserFaceid?enc=" + enc + "&token=4faa8662c59590c6f43ae9fe5b002b42&_time=" + timestamp
```
- 盐值: `uWwjeEKsri`（硬编码）
- Token: `4faa8662c59590c6f43ae9fe5b002b42`（硬编码）
- 这意味着任何人都可以计算任意puid的enc，获取该用户的人脸图片URL

### 人脸上传流程
1. 获取云盘Token: `GET /api/token/uservalid` → 返回`_token`
2. 上传人脸图片: `POST /upload` with `uploadtype=face&_token={token}&puid={puid}` → 返回`objectId`
3. 使用objectId通过人脸验证: `GET /facephoto/clientfacecheckstatus?objectId={objectId}`

### 人脸验证绕过接口
- `/qr/updateqrstatus` — PC端过人脸
- `/facephoto/clientfacecheckstatus` — 手机端过人脸
- `/knowledge/uploadInfo` — 老接口过人脸

## ADDED Requirements

### Requirement: getUserFaceid接口IDOR验证
系统 SHALL 验证getUserFaceid接口是否存在IDOR漏洞。

#### Scenario: 使用计算出的enc获取他人人脸图片
- **WHEN** 使用学生账号，通过计算教师puid的enc值，调用getUserFaceid接口
- **THEN** 验证是否能获取教师的人脸图片URL

#### Scenario: 无需登录获取人脸图片
- **WHEN** 不使用任何Cookie，仅通过enc和token参数调用getUserFaceid
- **THEN** 验证是否可以在未认证状态下获取人脸图片

### Requirement: 人脸图片上传IDOR验证
系统 SHALL 验证人脸上传接口是否存在IDOR漏洞。

#### Scenario: 使用他人puid上传人脸图片
- **WHEN** 学生A获取云盘Token后，使用学生B的puid上传人脸图片
- **THEN** 验证是否能为他人设置人脸图片

#### Scenario: 使用他人Token上传
- **WHEN** 学生A使用学生B的Token上传人脸图片
- **THEN** 验证是否可以跨用户上传

### Requirement: 人脸识别绕过验证
系统 SHALL 验证是否可以使用他人的人脸图片绕过人脸识别。

#### Scenario: 使用他人objectId通过人脸验证
- **WHEN** 学生A上传自己的人脸图片获取objectId后，学生B使用该objectId调用人脸验证接口
- **THEN** 验证是否可以跨用户使用objectId

#### Scenario: 使用旧objectId重复通过验证
- **WHEN** 同一用户使用之前上传的objectId重复通过人脸验证
- **THEN** 验证objectId是否有有效期限制

### Requirement: 头像URL可预测性/遍历测试
系统 SHALL 测试头像图片URL是否可被预测或遍历。

#### Scenario: 头像URL模式分析
- **WHEN** 分析多个人脸图片URL的命名模式
- **THEN** 识别URL是否包含可预测的元素（如puid、时间戳、递增ID等）

#### Scenario: 头像图片未授权访问
- **WHEN** 直接访问头像图片URL，不携带Cookie
- **THEN** 验证图片是否可被未认证用户访问

### Requirement: 技术报告生成
系统 SHALL 生成完整的头像/人脸图片漏洞技术报告。

#### Scenario: 报告内容
- **WHEN** 所有测试完成
- **THEN** 报告应包含：漏洞位置、利用方法、影响范围、严重程度、修复建议
