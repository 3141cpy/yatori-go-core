# 学生端签到详情接口探索与漏洞挖掘 Spec

## Why
知情人士透露学习通存在学生端即可查看签到活动详情的接口（包括班级其他学生的签到状态、签到位置、签到设备等信息）。该接口可能是签到系统中权限控制最薄弱的环节——如果学生能查看签到详情，那么围绕该接口的修改/删除操作可能同样存在鉴权缺陷，这可能是找到真正可修改签到状态漏洞的关键突破口。

## What Changes
- 系统性探索学生端可访问的签到详情/统计接口
- 分析签到详情接口返回的数据结构（其他学生信息、位置、设备等）
- 围绕签到详情接口测试相关修改/删除接口的权限控制
- 验证签到详情接口是否可被利用来修改签到状态

## Impact
- Affected APIs: `/pptSign/*`, `/newsign/*`, `/ppt/activeAPI/*`, `/v2/apis/sign/*`, `/widget/sign/*`, mooc1-api域名
- Test accounts: 教师 19712720708/3.1415926Cpy (puid=402644510), 学生 18436633997/3.1415926Cpy (puid=431407443)
- Course: courseId=257485372, classId=132821141

## 已知线索

### 关键线索1: 签到统计结果查看
- 官方文档提到"签到支持设置是否允许学生查看统计结果"
- 这意味着存在一个学生可查看签到统计的接口/页面
- 如果教师设置了"允许学生查看统计结果"，学生端应该有对应的API获取这些数据

### 关键线索2: 已知但未深入测试的接口
- `/pptSign/signedResult` — 签到结果页面（之前测试学生返回500或空内容）
- `/pptSign/signDetail` — 签到详情（之前测试未深入）
- `/v2/apis/sign/signIn` — V2签到查询（返回个人签到记录）

### 关键线索3: 可能存在的接口路径
- `/pptSign/getSignStuInfo` — 获取签到学生信息
- `/pptSign/getStuSignList` — 获取学生签到列表
- `/pptSign/signStuList` — 签到学生列表
- `/pptSign/getSignResult` — 获取签到结果
- `/newsign/getSignDetail` — 获取签到详情
- `/newsign/signStuList` — 签到学生列表
- `/v2/apis/sign/signDetail` — V2签到详情
- `/v2/apis/sign/signResult` — V2签到结果
- `/v2/apis/sign/stuList` — V2学生列表
- `/ppt/activeAPI/getActiveDetail` — 活动详情
- `/ppt/activeAPI/signStuList` — 签到学生列表

## ADDED Requirements

### Requirement: 阶段1——签到详情/统计接口全面探索
系统 SHALL 对所有可能的学生端签到详情接口进行系统性枚举和测试。

#### Scenario: 枚举签到详情相关接口
- **WHEN** 用学生账号对签到详情相关的所有可能API路径进行测试
- **THEN** 应发现并记录所有返回有效数据的接口

#### Scenario: 测试签到统计结果查看功能
- **WHEN** 教师设置"允许学生查看统计结果"后，学生尝试访问签到统计
- **THEN** 应识别学生端获取统计数据的API路径和数据结构

### Requirement: 阶段2——签到详情接口数据结构分析
系统 SHALL 分析签到详情接口返回的完整数据结构。

#### Scenario: 分析返回数据中的敏感信息
- **WHEN** 学生成功获取签到详情数据
- **THEN** 应识别数据中是否包含其他学生的签到状态、位置、设备信息

#### Scenario: 分析返回数据中的可操作字段
- **WHEN** 分析签到详情接口返回的数据结构
- **THEN** 应识别是否存在可被修改的字段（如status、remark等）

### Requirement: 阶段3——围绕签到详情接口的修改漏洞挖掘
系统 SHALL 围绕签到详情接口测试相关的修改/删除操作。

#### Scenario: 测试签到详情页面中的修改操作
- **WHEN** 分析签到详情页面/接口中暴露的修改操作
- **THEN** 应测试学生是否能调用这些修改操作

#### Scenario: 测试签到详情接口的关联修改接口
- **WHEN** 从签到详情接口的参数和URL模式推断关联的修改接口
- **THEN** 应测试这些修改接口的权限控制

### Requirement: 阶段4——签到详情接口的IDOR测试
系统 SHALL 测试签到详情接口是否存在IDOR漏洞。

#### Scenario: 跨活动访问测试
- **WHEN** 学生尝试访问其他课程/班级的签到详情
- **THEN** 应验证是否存在水平越权

#### Scenario: 跨用户数据访问测试
- **WHEN** 学生尝试通过修改参数访问其他学生的签到详情
- **THEN** 应验证是否存在IDOR漏洞

### Requirement: 阶段5——签到状态修改漏洞深度挖掘
系统 SHALL 基于签到详情接口的发现，深度挖掘签到状态修改漏洞。

#### Scenario: 基于详情接口参数构造修改请求
- **WHEN** 从签到详情接口获取到的参数（如签到记录ID、activeId等）构造修改请求
- **THEN** 应测试学生是否能成功修改签到状态

#### Scenario: 测试签到记录的直接修改
- **WHEN** 学生尝试通过签到记录ID直接修改签到状态
- **THEN** 应验证是否存在基于记录ID的修改漏洞
