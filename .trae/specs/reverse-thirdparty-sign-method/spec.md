# 逆向分析第三方网站签到修改方法 Spec

## Why
用户发现一个第三方网站可以实际修改学习通签到状态，需要通过技术手段捕获该网站使用的具体API调用和漏洞利用方法，以便识别和修复对应的安全漏洞。

## What Changes
- 设计并实现一套完整的流量捕获与逆向分析方案
- 编写自动化脚本记录签到状态变更前后的差异
- 通过代理拦截、API对比、时间关联等方式定位漏洞利用路径
- 编写分析工具自动对比已知API端点与捕获的请求

## Impact
- Affected specs: domain-map-sign-explore（可能发现新的未记录API端点）
- Affected code: sign_vuln_report.md（需更新新发现的漏洞）
- 测试账号: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)

## 核心挑战

第三方网站可能采用以下架构之一：
1. **纯前端模式**：浏览器直接向学习通API发请求（可在DevTools/代理中捕获）
2. **后端代理模式**：用户提交凭证→第三方服务器→学习通API（浏览器中不可见）
3. **混合模式**：部分前端+部分后端

## ADDED Requirements

### Requirement: 流量捕获方案
系统 SHALL 提供多种流量捕获方法，覆盖前端和后端代理两种场景。

#### Scenario: 前端直接请求捕获
- **WHEN** 第三方网站在浏览器中直接调用学习通API
- **THEN** 应通过浏览器DevTools或代理工具完整记录请求URL、方法、Header、Body

#### Scenario: 后端代理请求推断
- **WHEN** 第三方网站通过后端服务器代理请求
- **THEN** 应通过签到状态变更前后的差异分析推断使用的API

### Requirement: 签到状态快照对比
系统 SHALL 在使用第三方网站前后分别记录签到状态的完整快照。

#### Scenario: 签到状态快照
- **WHEN** 使用第三方网站修改签到状态
- **THEN** 应记录修改前后的完整签到记录（包括所有40+字段），通过差异定位关键变更

### Requirement: API调用推断
系统 SHALL 基于签到状态变更的特征推断第三方网站使用的API。

#### Scenario: 基于tag字段推断
- **WHEN** 签到记录的tag字段包含teaUpdateFlag
- **THEN** 推断使用了教师端API（updateSignStatus2或updateSignStatusByUidsV2）

#### Scenario: 基于clientip推断
- **WHEN** 签到记录的clientip不是用户自己的IP
- **THEN** 推断第三方网站使用了自己的服务器代理请求

#### Scenario: 基于updatetime推断
- **WHEN** 签到记录的updatetime与使用第三方网站的时间吻合
- **THEN** 确认变更确实由第三方网站触发

### Requirement: 已知漏洞匹配
系统 SHALL 将推断的API调用与已知漏洞进行匹配。

#### Scenario: 漏洞匹配
- **WHEN** 推断出第三方网站使用了updateSignStatusByUidsV2
- **THEN** 匹配到CSRF漏洞（漏洞1）
- **WHEN** 推断出第三方网站使用了updateSignStatus2
- **THEN** 匹配到PC端教师接口漏洞
- **WHEN** 推断出第三方网站使用了未知API
- **THEN** 标记为新发现漏洞，需进一步研究

### Requirement: 自动化分析工具
系统 SHALL 提供自动化脚本执行完整的捕获-对比-推断流程。

#### Scenario: 一键分析
- **WHEN** 运行分析脚本
- **THEN** 自动执行：快照→使用网站→快照→对比→推断→报告
