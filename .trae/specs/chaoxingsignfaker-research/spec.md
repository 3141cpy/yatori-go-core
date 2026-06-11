# 基于ChaoxingSignFaker的签到状态修改漏洞深挖 Spec

## Why
开源仓库 ChaoxingSignFaker 揭示了多个我们未知的API端点。用户的核心需求是：**寻找学生端可直接修改签到状态的漏洞**，而非验证正常签到流程。需要重点研究这些新端点是否存在权限绕过、越权修改签到状态的可能。

## What Changes
- 研究ChaoxingSignFaker揭示的新API端点中，哪些可能被学生利用来修改签到状态
- 重点测试V2 API（getPPTActiveInfo/activelist）是否泄露签到码/enc等可被利用的信息
- 重点测试preSign/checkSignCode/check-face-result等端点的权限控制
- 测试captcha/pan-yz/im等辅助端点是否可辅助签到状态修改
- 更新安全测试报告

## Impact
- 重点: 学生修改签到状态漏洞
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141 / courseId=262934472, classId=145110605

## ChaoxingSignFaker揭示的新端点（与签到状态修改相关）

### 高优先级 — 可能直接修改签到状态
1. **`/newsign/preSign`** — 预签到接口，可能包含签到状态修改逻辑
2. **`/v2/apis/active/getPPTActiveInfo`** — 签到活动详情，可能泄露签到码/enc
3. **`/v2/apis/active/student/activelist`** — 活动列表，可能泄露其他学生签到状态
4. **`/widget/sign/pcStuSignController/checkSignCode`** — 签到码校验，可能绕过签到码验证
5. **`/pptSign/check-face-result`** — 人脸校验，可能绕过人脸直接修改状态

### 中优先级 — 可能辅助签到状态修改
6. **`/pptSign/analysis` + `/pptSign/analysis2`** — 分析链，可能是签到前置条件
7. **`sso.chaoxing.com/apis/login/userLogin4Uname.do`** — 设备信息上传，可能影响认证
8. **`im.chaoxing.com/webim/me`** — IM配置，可能获取签到活动信息

### 低优先级 — 辅助功能
9. **`captcha.chaoxing.com/*`** — 验证码系统
10. **`pan-yz.chaoxing.com/*`** — 云盘上传
11. **`im.chaoxing.com/webim/message/list/getMessageList`** — IM群组列表

## ADDED Requirements

### Requirement: 新端点签到状态修改漏洞研究
系统 SHALL 研究ChaoxingSignFaker揭示的新API端点中，学生可修改签到状态的漏洞。

#### Scenario: 学生通过新端点修改签到状态
- **WHEN** 学生调用/newsign/preSign、/v2/apis/active/getPPTActiveInfo等新端点
- **THEN** 应识别哪些端点存在权限绕过可修改签到状态

### Requirement: V2 API信息泄露与签到码获取
系统 SHALL 研究V2 API是否泄露签到码/enc等可被学生利用修改签到状态的信息。

#### Scenario: V2 API签到码泄露
- **WHEN** 学生调用/v2/apis/active/getPPTActiveInfo获取签到详情
- **THEN** 应检查返回数据是否包含签到码/enc/二维码内容等敏感信息

### Requirement: checkSignCode暴力破解评估
系统 SHALL 评估checkSignCode接口是否可被暴力破解获取签到码。

#### Scenario: 签到码暴力破解
- **WHEN** 学生调用/widget/sign/pcStuSignController/checkSignCode尝试不同签到码
- **THEN** 应评估暴力破解的可行性和速率限制

### Requirement: 安全测试报告更新
系统 SHALL 更新安全测试报告包含所有新发现。

#### Scenario: 报告更新
- **WHEN** 所有研究完成
- **THEN** 应更新sign_vuln_report.md
