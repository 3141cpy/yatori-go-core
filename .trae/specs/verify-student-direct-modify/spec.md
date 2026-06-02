# 学生端直接修改签到状态漏洞验证 Spec（更新版）

## Why
知情人士确认学生端可直接在浏览器控制台修改签到状态，无需教师Cookie。前两轮测试中：
1. V3/V4/V5等更高版本API全部404不存在
2. `updateSignStatusByUids`（无V2后缀）存在但学生返回"无权限"
3. 所有参数绕过（roletype/role/cpi/operateSource等）均返回"无权限"
4. 学生Web登录+浏览器头+不同Content-Type均返回"无权限"

但知情人士坚持学生端可直接修改，说明我们可能遗漏了关键路径。需要从全新角度探索：
- 学生签到流程中是否有状态修改API
- 学生端App/Web使用的签到相关API端点
- 不同域名下的签到API
- 学生自己的签到记录修改接口

## What Changes
- 探索学生签到流程中的所有API端点（stuSignajax/preSign/signIn等）
- 探索不同域名下的签到状态修改API（mooc1-api/mooc1/fy等）
- 分析学生端JS源码中的API调用
- 测试学生签到接口是否接受status参数
- 探索学生修改自己签到记录的API

## Impact
- Affected APIs: /pptSign/*, /v2/apis/sign/*, 学生端签到相关API
- Test accounts: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
- Course: courseId=257485372, classId=132821141

## ADDED Requirements

### Requirement: 学生签到流程API全面探索
系统 SHALL 探索学生签到流程中的所有API端点，包括签到、补签、修改等操作。

#### Scenario: 发现学生可用的状态修改API
- **WHEN** 依次测试学生签到流程中的所有API端点
- **THEN** 应记录哪些端点学生可调用，哪些参数可修改签到状态

### Requirement: 多域名签到API探索
系统 SHALL 在不同域名下测试签到状态修改API。

#### Scenario: 发现其他域名下的可利用API
- **WHEN** 在mooc1-api/mooc1/fy等域名下测试签到API
- **THEN** 应记录不同域名的权限校验差异

### Requirement: 学生端JS源码分析
系统 SHALL 分析学生端签到页面的JavaScript源码，找出所有API调用。

#### Scenario: 从JS源码发现隐藏API
- **WHEN** 分析学生签到页面的JS文件
- **THEN** 应提取所有签到相关的API端点和调用方式

### Requirement: 更新安全测试报告
系统 SHALL 更新报告包含新发现。
