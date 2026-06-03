# 学生端签到状态修改漏洞深入探索（UA维度）Spec

## Why
用户确认学生端直接修改签到状态的漏洞确实存在，之前的验证方法可能存在问题。关键新线索：**某些签到PC端无法签到，需要尝试更改UA**。这意味着：
1. 之前用移动端UA测试`/newsign/updateSignStatus`返回"success"但数据未变化，可能是因为该API需要特定UA才真正生效
2. 不同UA（移动端App/移动端Web/PC端Web/平板端）可能导致不同的服务端行为
3. 之前仅用一种移动端UA测试，覆盖面不足
4. 验证状态的工作交给用户，我们只负责学生端探索

## What Changes
- 使用多种UA（移动端App、移动端Web、PC端Web、平板端、微信内嵌浏览器等）重新测试所有签到状态修改API
- 重点测试`/newsign/updateSignStatus`在不同UA下是否真正修改数据
- 探索学生端签到流程中可能遗漏的API端点
- 尝试不同的Content-Type、请求格式
- 不依赖教师端查询验证，只做学生端探索

## Impact
- Affected APIs: /newsign/*, /pptSign/*, /v2/apis/sign/*, /ppt/activeAPI/*
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141

## ADDED Requirements

### Requirement: 多UA维度测试签到状态修改API
系统 SHALL 使用多种User-Agent重新测试所有签到状态修改API，验证不同UA下服务端行为差异。

#### Scenario: 移动端App UA测试
- **WHEN** 使用学习通App移动端UA（含schild签名）调用签到状态修改API
- **THEN** 记录API响应和数据是否真正变化

#### Scenario: 移动端Web UA测试
- **WHEN** 使用移动端浏览器UA（无schild签名）调用签到状态修改API
- **THEN** 记录API响应和数据是否真正变化

#### Scenario: PC端Web UA测试
- **WHEN** 使用PC端浏览器UA调用签到状态修改API
- **THEN** 记录API响应和数据是否真正变化

#### Scenario: 微信内嵌浏览器UA测试
- **WHEN** 使用微信内嵌浏览器UA调用签到状态修改API
- **THEN** 记录API响应和数据是否真正变化

#### Scenario: 平板端UA测试
- **WHEN** 使用iPad/Android平板UA调用签到状态修改API
- **THEN** 记录API响应和数据是否真正变化

### Requirement: /newsign/updateSignStatus多UA深入验证
系统 SHALL 对`/newsign/updateSignStatus`进行多UA维度的深入验证，这是最有可能的漏洞路径。

#### Scenario: 不同UA下newsign/updateSignStatus数据变化验证
- **WHEN** 使用不同UA调用`/newsign/updateSignStatus`修改签到状态
- **THEN** 通过V2 signIn API查询确认数据是否真正变化

#### Scenario: 不同请求格式测试
- **WHEN** 使用不同的Content-Type和请求格式（form-data、json、multipart）调用API
- **THEN** 记录不同格式下的API行为差异

### Requirement: 学生端签到流程完整模拟
系统 SHALL 模拟学生端完整的签到流程，包括preSign、stuSignajax、updateqrstatus等，寻找状态修改的突破口。

#### Scenario: 模拟移动端App完整签到流程
- **WHEN** 使用移动端App UA模拟学生从进入签到页面到完成签到的完整流程
- **THEN** 记录每个步骤的API调用和响应

#### Scenario: 在签到流程中注入status参数
- **WHEN** 在学生签到流程的各个步骤中注入status参数
- **THEN** 验证是否有步骤接受status参数并修改签到状态

### Requirement: 探索其他可能被遗漏的API路径
系统 SHALL 探索可能被之前测试遗漏的API路径和参数组合。

#### Scenario: 不同域名+不同UA组合
- **WHEN** 在不同域名（mobilelearn/mooc1-api/learn等）下使用不同UA测试
- **THEN** 记录域名和UA的组合差异

#### Scenario: 参数名变体测试
- **WHEN** 测试不同的参数名变体（signStatus/resultStatus/type等）
- **THEN** 记录哪些参数名组合可能影响签到状态
