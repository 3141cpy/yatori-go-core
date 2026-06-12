# 逆向分析第三方签到修改网站漏洞利用方法 Spec

## Why
用户发现第三方网站(beta-a.xiucat.top)可以实际修改学习通签到状态，需要逆向分析该网站使用的漏洞利用方法。经初步探测，该网站后端暴露了完整OpenAPI文档，揭示了其核心机制：**使用系统教师账号代理修改学生签到状态**。

## What Changes
- 已完成：后端API结构探测，发现完整OpenAPI文档
- 需验证：确认该网站具体调用学习通的哪个API端点
- 需验证：确认教师账号修改签到的具体参数和流程
- 需编写：签到状态监控脚本，在使用网站前后捕获变化
- 需编写：验证脚本，通过teaUpdateFlag等字段确认修改来源

## Impact
- 第三方网站: https://beta-a.xiucat.top (VIP Center API, NestJS后端)
- Test accounts: 学生 18436633997/3.1415926Cpy, 教师 19712720708/3.1415926Cpy
- Course: courseId=257485372, classId=132821141

## 核心发现

### 第三方网站工作原理
1. 用户绑定学习通账号（提供手机号+密码）
2. 网站后端存储一个**系统教师账号**（`/api/chaoxing/accounts/system-teacher`）
3. 用户创建补签任务时，网站使用教师账号调用学习通教师端API修改学生签到状态
4. 补签任务状态：CREATED → QUEUED → RUNNING → SUCCESS/FAILED

### 关键API端点
- `POST /api/chaoxing/accounts` — 绑定学习通账号
- `GET /api/chaoxing/accounts/system-teacher` — 获取系统教师账号
- `PUT /api/chaoxing/accounts/system-teacher` — 配置系统教师账号
- `POST /api/patch-sign/tasks` — 创建补签任务（核心）
- `POST /api/patch-sign/tasks/bulk` — 批量补签
- `GET /api/chaoxing/actives/{activeId}/members` — 获取成员签到状态

### targetStatus值
1=正常签到, 2=迟到, 5=请假, 7=未签到, 8-12=其他状态

## ADDED Requirements

### Requirement: 验证教师账号代理修改机制
系统 SHALL 验证第三方网站是否通过教师账号调用学习通API修改签到状态。

#### Scenario: teaUpdateFlag验证
- **WHEN** 第三方网站修改了学生签到状态
- **THEN** 通过V2 signIn API查询签到记录，teaUpdateFlag应为1（教师修改标记）

#### Scenario: 修改时间验证
- **WHEN** 第三方网站修改了签到状态
- **THEN** updatetime应与补签任务完成时间一致

### Requirement: 识别具体调用的学习通API
系统 SHALL 识别第三方网站具体调用了学习通的哪个API端点。

#### Scenario: API端点识别
- **WHEN** 分析第三方网站的补签流程
- **THEN** 应确定是updateSignStatusByUidsV2、updateSignStatus2、还是其他端点

### Requirement: 编写签到状态监控脚本
系统 SHALL 提供签到状态监控脚本，在使用第三方网站前后持续监控。

#### Scenario: 实时监控
- **WHEN** 运行监控脚本
- **THEN** 应每5秒轮询一次签到状态，检测变化并记录时间戳

### Requirement: 编写完整验证报告
系统 SHALL 编写完整的验证报告，包含漏洞利用方法、影响范围和修复建议。

#### Scenario: 报告输出
- **WHEN** 所有验证完成
- **THEN** 应输出包含具体API调用路径、参数、认证方式的完整报告
