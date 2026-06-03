# 自动化交互式签到记录修改脚本 Spec

## Why
基于已确认的 `/newsign/updateSignStatus` 权限校验缺失漏洞（CRITICAL），需要开发一个用户友好的自动化交互式脚本，让安全审计人员只需输入账号密码即可完成签到状态的查询和修改，无需手动拼接API请求。

## What Changes
- 创建交互式Python脚本，实现自动登录、课程选择、活动浏览、状态修改、结果验证的完整流程
- 支持多选和批量修改
- 支持多种签到状态切换（出勤/迟到/事假/病假/补签/缺勤/旷课）

## Impact
- Affected APIs: /newsign/updateSignStatus, /ppt/activeAPI/taskactivelist, /v2/apis/sign/signIn
- 依赖已有漏洞发现成果
- 新增脚本文件: /workspace/sign_status_modifier.py

## ADDED Requirements

### Requirement: 自动登录
系统 SHALL 提供账号密码输入，自动完成学习通登录（移动端AES-CBC加密方式），获取UID和Cookie。

#### Scenario: 用户输入账号密码登录
- **WHEN** 用户输入手机号和密码
- **THEN** 系统自动加密并登录，显示登录状态和用户名/UID

### Requirement: 课程列表展示与选择
系统 SHALL 自动获取用户的所有课程列表，以编号形式展示供用户选择。

#### Scenario: 登录后展示课程列表
- **WHEN** 登录成功后
- **THEN** 显示所有课程的编号、课程名、班级名，用户输入编号选择课程

### Requirement: 签到活动列表展示
系统 SHALL 获取所选课程的所有签到活动，展示活动ID、名称、状态（进行中/已结束）及当前签到状态。

#### Scenario: 选择课程后展示签到活动
- **WHEN** 用户选择某课程后
- **THEN** 显示该课程所有签到活动的编号、活动ID、名称、时间、当前签到状态（未签到/出勤/迟到/事假/病假/补签/缺勤/旷课）

### Requirement: 签到状态修改
系统 SHALL 允许用户选择目标活动和目标状态，调用 `/newsign/updateSignStatus` API修改签到状态。

#### Scenario: 用户选择活动并修改状态
- **WHEN** 用户选择一个或多个签到活动，并选择目标状态
- **THEN** 系统调用漏洞API修改签到状态，显示修改结果

### Requirement: 修改结果验证
系统 SHALL 在修改后自动查询签到状态，核实修改是否真正生效。

#### Scenario: 修改后自动验证
- **WHEN** 签到状态修改API返回"success"
- **THEN** 系统通过V2 signIn API查询实际签到状态，对比修改前后确认是否生效

### Requirement: 多选与批量修改
系统 SHALL 支持用户一次选择多个签到活动进行批量修改。

#### Scenario: 批量修改多个活动
- **WHEN** 用户输入多个活动编号（如"1,3,5"或"1-5"）
- **THEN** 系统依次修改所有选中活动的签到状态，并逐一显示结果

### Requirement: 状态值对照
系统 SHALL 提供清晰的状态选项菜单，包含所有可用的签到状态。

#### Scenario: 展示状态选项
- **WHEN** 用户选择活动后需要选择目标状态
- **THEN** 显示: 0-缺勤, 1-出勤, 2-迟到, 3-事假, 4-病假, 5-补签, 6-旷课
