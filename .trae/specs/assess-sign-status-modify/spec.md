# 签到状态修改漏洞安全评估 Spec

## Why
有消息称学习通平台存在允许学生修改签到状态的漏洞。前一轮垂直越权测试确认学生无法创建/删除签到（防护有效），但未测试"学生修改已提交签到状态"这一核心场景。本次评估使用专用的教师/学生测试账号，针对"111"课程的签到功能进行系统性安全测试，验证签到状态是否可被非授权修改。

## What Changes
- 使用专用教师账号（19712720708）和学生账号（18436633997）进行测试
- 分两阶段进行：第一阶段调查签到API端点和流程，第二阶段实际测试签到状态修改
- 重点测试：学生修改已提交的签到状态（从缺勤改为已签等）
- 测试非常规手段：修改网络请求参数、伪造签到请求、重放签到请求、篡改activeId等
- 不创建新签到活动（使用教师已创建的签到）

## Impact
- Affected specs: assess-vertical-idor（扩展签到系统测试）
- Affected APIs: mobilelearn.chaoxing.com（签到核心API）
- Key findings from research: 签到API链路已完整公开（获取活动列表→签到→查看结果）

## ADDED Requirements

### Requirement: 第一阶段——签到API端点与流程调查
系统 SHALL 先调查签到系统的完整API链路和已知漏洞。

#### Scenario: 签到API链路调查
- **WHEN** 调查学习通签到系统的API端点
- **THEN** 应明确列出签到完整流程的API端点、参数和认证方式

#### Scenario: 已知漏洞调查
- **WHEN** 调查已公开的签到漏洞信息
- **THEN** 应明确列出已知的签到绕过/伪造方法

### Requirement: 第二阶段——签到状态修改测试
系统 SHALL 使用学生账号测试签到状态修改漏洞。

#### Scenario: 学生获取已结束签到活动列表
- **WHEN** 学生账号请求 /ppt/activeAPI/taskactivelist 获取"111"课程的活动列表
- **THEN** 验证是否可获取教师创建的签到活动信息（含已结束的签到）

#### Scenario: 学生对已结束签到执行签到操作
- **WHEN** 学生账号对已结束的签到活动调用 /pptSign/stuSignajax
- **THEN** 验证是否可将缺勤状态修改为已签

#### Scenario: 学生重放/伪造签到请求
- **WHEN** 学生账号构造签到请求（修改activeId、uid等参数）
- **THEN** 验证是否可对任意签到活动执行签到

#### Scenario: 学生修改签到类型参数
- **WHEN** 学生账号修改签到请求中的activeType、signType等参数
- **THEN** 验证是否可绕过签到类型限制（如普通签到→手势签到）

#### Scenario: 学生使用位置伪造签到
- **WHEN** 学生账号构造包含伪造经纬度的签到请求
- **THEN** 验证是否可绕过位置签到限制

#### Scenario: 学生查看/修改签到结果
- **WHEN** 学生账号尝试访问签到结果管理API
- **THEN** 验证是否可查看其他学生的签到状态或修改自己的签到状态

### Requirement: 第三阶段——教师端签到管理测试
系统 SHALL 使用教师账号验证签到管理功能的安全边界。

#### Scenario: 教师查看签到结果
- **WHEN** 教师账号查看签到活动的学生签到状态
- **THEN** 记录签到状态数据结构和API端点

#### Scenario: 教师修改学生签到状态
- **WHEN** 教师账号修改学生的签到状态（缺勤→已签）
- **THEN** 记录修改签到状态的API端点和参数，为学生端越权测试提供基准

### Requirement: 签到状态修改漏洞评估报告
系统 SHALL 生成签到状态修改漏洞的安全评估报告。

#### Scenario: 报告内容完整性
- **WHEN** 评估完成
- **THEN** 报告应包含：签到API链路分析、签到状态修改测试结果、漏洞利用条件、影响范围、严重程度、修复建议

---

## 附录：调查发现的签到API端点

### 签到完整流程API链路

| 步骤 | API | 方法 | 功能 | 关键参数 |
|---|---|---|---|---|
| 1.获取课程列表 | /mycourse/backclazzdata | GET | 获取课程列表 | view=json, m=0 |
| 2.获取活动列表 | /ppt/activeAPI/taskactivelist | GET | 获取课程活动列表 | courseId, classId, uid |
| 3.签到前页面 | /newsign/preSign | GET | 签到页面（含签到参数） | activeId |
| 4.执行签到 | /pptSign/stuSignajax | POST | 执行签到 | activeId, uid, fid, latitude, longitude, address, appType, ifTiJiao, validate, deviceCode |
| 5.签到结果 | /pptSign/signedResult | GET | 查看签到结果 | activeId, classId, courseId |
| 6.新版活动列表 | /v2/apis/active/student/activelist | GET | 新版活动列表 | courseId, classId |

### 已知漏洞（来自公开渠道）

1. **位置伪造签到**: 签到页面中经纬度从DOM元素获取（`$("#latitude").val()`），可通过JS修改DOM值伪造位置
2. **localStorage防重复签到绕过**: 签到前端使用localStorage防止同设备重复签到，清除localStorage即可绕过
3. **deviceCode伪造**: 设备码可伪造，绕过同设备限制
4. **签到接口直接调用**: /pptSign/stuSignajax 可通过HTTP直接调用，无需通过App内WebView

### 签到类型（activeType）

| activeType | 签到类型 | 特殊参数 |
|---|---|---|
| 1 | 普通签到 | 无 |
| 2 | 位置签到 | latitude, longitude, address |
| 3 | 手势签到 | signCode（手势码） |
| 4 | 签到码签到 | signCode（签到码） |

### 签到状态（status）

| status | 含义 |
|---|---|
| 1 | 未签到（进行中） |
| 2 | 已签到 |
| 其他 | 已结束 |
