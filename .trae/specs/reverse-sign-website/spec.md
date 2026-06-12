# 逆向分析第三方签到修改网站漏洞利用方法 Spec

## Why
用户发现了一个第三方网站可以实际修改学习通签到状态，需要逆向分析该网站使用的漏洞利用方法，以便定位和修复底层漏洞。这是一个典型的"已知可利用→反推漏洞"的安全审计场景。

## What Changes
- 设计并实现一套完整的流量捕获与API调用分析方案
- 编写自动化脚本监控测试账号签到状态变化
- 编写自动化脚本对比使用网站前后的API调用差异
- 编写流量拦截代理脚本记录第三方网站的所有HTTP请求
- 基于已知的100+域名和签到API端点，自动匹配第三方网站调用的目标

## Impact
- Affected code: 新建流量分析脚本、签到状态监控脚本
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141

## 已知信息
- 我们已完整映射了100+域名的签到API端点
- 已知可修改签到状态的API:
  - `/pptSign/updateSignStatusByUidsV2` (教师端, CSRF漏洞)
  - `/widget/sign/pcTeaSignController/updateSignStatus2` (PC端教师)
  - `/newsign/updateSignStatus` (教师端)
  - `/pptSign/updateSignStatus` (教师端)
  - `/pptSign/resetUserSignStatus` (教师端)
- 学生端无法直接修改签到状态（已验证）
- 第三方网站确实能修改签到状态（用户已验证）

## ADDED Requirements

### Requirement: 流量拦截方案设计
系统 SHALL 提供一套完整的流量拦截方案，用于捕获第三方网站与学习通服务器之间的所有HTTP/HTTPS通信。

#### Scenario: mitmproxy代理拦截
- **WHEN** 用户通过mitmproxy代理访问第三方网站并执行签到修改操作
- **THEN** 应记录所有发往*.chaoxing.com域名的请求，包括URL、方法、Header、参数、响应

#### Scenario: 浏览器DevTools捕获
- **WHEN** 用户在浏览器DevTools Network面板中操作第三方网站
- **THEN** 应能识别所有XHR/Fetch请求到学习通域名

### Requirement: 签到状态实时监控
系统 SHALL 提供签到状态实时监控脚本，在使用第三方网站前后持续轮询签到状态。

#### Scenario: 签到状态变化检测
- **WHEN** 第三方网站成功修改了签到状态
- **THEN** 监控脚本应立即检测到变化，并记录精确时间戳

### Requirement: API调用差异对比
系统 SHALL 提供API调用差异对比工具，将第三方网站的调用与已知API端点进行匹配。

#### Scenario: 端点匹配
- **WHEN** 捕获到第三方网站的API调用
- **THEN** 应自动匹配到已知的签到API端点，并标注调用方式

### Requirement: 账号活动日志分析
系统 SHALL 通过学习通API查询测试账号的近期活动日志，识别第三方网站的操作痕迹。

#### Scenario: 操作日志查询
- **WHEN** 第三方网站修改了签到状态
- **THEN** 应能通过V2 signIn API查询到修改记录（含teaUpdateFlag、updatetime等）

### Requirement: 多维度验证方案
系统 SHALL 提供多维度验证方案，从不同角度确认第三方网站的漏洞利用方法。

#### Scenario: 教师端验证
- **WHEN** 第三方网站修改了学生签到状态
- **THEN** 应通过教师端API验证修改是否真实生效

#### Scenario: Cookie/Session分析
- **WHEN** 第三方网站要求用户提供认证信息
- **THEN** 应分析网站获取的认证信息类型（Cookie/Token/密码）及其使用方式
