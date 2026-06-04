# PC端签到状态修改漏洞全面安全评估 Spec

## Why
已确认原始漏洞位于PC端Web接口 `/widget/sign/pcTeaSignController/updateSignStatus2`（通过油猴脚本 `/workspace/超星签到.user.js` 确认），该漏洞已被紧急修复。但修复可能不完整——同一路径下可能存在其他未授权接口，移动端可能存在功能等价的替代接口，且现有修复方案可能可被绕过。需进行全面的安全评估与深度渗透测试。

## What Changes
- 对已修复的PC端接口路径 `/widget/sign/pcTeaSignController/` 进行系统性端点枚举与测试
- 对PC端学生路径 `/widget/sign/pcStuSignController/` 进行安全测试
- 对 `/widget/sign/` 路径下所有可能的Controller进行枚举
- 验证修复方案的有效性——测试学生能否绕过鉴权调用updateSignStatus2
- 测试移动端API与PC端API的鉴权差异
- 评估参数篡改、路径遍历、请求伪造等绕过手段
- 对整个签到系统进行全面梳理，识别其他权限控制缺陷
- 更新安全测试报告

## Impact
- Affected APIs:
  - PC端: `/widget/sign/pcTeaSignController/*`, `/widget/sign/pcStuSignController/*`
  - 移动端: `/pptSign/*`, `/newsign/*`, `/ppt/activeAPI/*`
  - V2 API: `/v2/apis/sign/*`
- Test accounts: 教师 19712720708/3.1415926Cpy (puid=402644510), 学生 18436633997/3.1415926Cpy (puid=431407443)
- Course: courseId=257485372, classId=132821141（课程名exam，班级名111）

## 已知关键信息

### 原始漏洞接口（已修复）
- **路径**: `/widget/sign/pcTeaSignController/updateSignStatus2`
- **方法**: GET
- **参数**: uid, activeId, status, denc, duid
- **返回**: `{result: 1}` 表示成功，`{result: 0, errorMsg: "..."}` 表示失败
- **鉴权参数**: denc（加密参数）, duid（设备用户ID）
- **修复状态**: 已被紧急修复

### PC端学生签到接口
- **路径**: `/widget/sign/pcStuSignController/preSign`
- **参数**: activeId, courseId, classId
- **功能**: 学生签到预处理

### 移动端已知接口
- `/pptSign/stuSignajax` - 学生签到（需二维码/位置验证）
- `/pptSign/updateSignStatusByUidsV2` - 教师修改签到状态（CSRF漏洞已确认）
- `/newsign/updateSignStatus` - 假success（不修改数据）
- `/ppt/activeAPI/taskactivelist` - 活动列表
- `/v2/apis/sign/signIn` - 签到记录查询

## ADDED Requirements

### Requirement: 阶段1——PC端接口路径系统性枚举
系统 SHALL 对 `/widget/sign/` 路径下所有可能的Controller和端点进行系统性枚举和测试。

#### Scenario: 枚举pcTeaSignController下的所有端点
- **WHEN** 对 `/widget/sign/pcTeaSignController/` 路径进行端点枚举
- **THEN** 应发现并记录所有可用端点及其功能

#### Scenario: 枚举pcStuSignController下的所有端点
- **WHEN** 对 `/widget/sign/pcStuSignController/` 路径进行端点枚举
- **THEN** 应发现并记录所有可用端点及其功能

#### Scenario: 枚举/widget/sign/下其他Controller
- **WHEN** 对 `/widget/sign/` 路径下其他可能的Controller进行枚举
- **THEN** 应发现并记录所有可用Controller及其端点

### Requirement: 阶段2——已修复漏洞绕过测试
系统 SHALL 验证已修复的updateSignStatus2接口是否可被绕过。

#### Scenario: 学生直接调用updateSignStatus2
- **WHEN** 学生账号尝试直接调用 `/widget/sign/pcTeaSignController/updateSignStatus2`
- **THEN** 验证鉴权是否真正阻止了学生调用

#### Scenario: 参数篡改绕过
- **WHEN** 通过篡改denc/duid/uid参数尝试绕过鉴权
- **THEN** 验证是否存在参数级别的鉴权绕过

#### Scenario: 请求方法变换绕过
- **WHEN** 将GET请求改为POST/PUT/DELETE尝试绕过
- **THEN** 验证是否存在HTTP方法级别的鉴权绕过

#### Scenario: 路径变体绕过
- **WHEN** 尝试 `/widget/sign/pcTeaSignController/updateSignStatus2/`、`/widget/sign/pcTeaSignController/updateSignStatus2;`、`/widget/sign/pcTeaSignController/updateSignStatus2.json` 等路径变体
- **THEN** 验证是否存在路径级别的鉴权绕过

### Requirement: 阶段3——移动端与PC端鉴权差异对比
系统 SHALL 对比移动端和PC端API的鉴权机制差异。

#### Scenario: 同功能接口的鉴权对比
- **WHEN** 对比PC端 `/widget/sign/pcTeaSignController/updateSignStatus2` 和移动端 `/pptSign/updateSignStatusByUidsV2` 的鉴权
- **THEN** 识别两端鉴权机制的差异和潜在绕过点

#### Scenario: 学生端接口越权测试
- **WHEN** 学生调用PC端教师接口和移动端教师接口
- **THEN** 对比两端的权限校验结果

### Requirement: 阶段4——签到系统全面权限控制评估
系统 SHALL 对整个签到系统进行全面的权限控制评估。

#### Scenario: IDOR测试——跨用户操作
- **WHEN** 学生尝试修改其他学生的签到状态
- **THEN** 验证是否存在水平越权漏洞

#### Scenario: 垂直越权测试
- **WHEN** 学生尝试执行教师级操作（创建签到、结束签到、删除活动等）
- **THEN** 验证是否存在垂直越权漏洞

#### Scenario: 批量操作测试
- **WHEN** 学生尝试批量修改签到状态
- **THEN** 验证是否存在批量操作漏洞

### Requirement: 阶段5——修复方案完整性与有效性评估
系统 SHALL 评估现有漏洞修复方案的完整性与有效性。

#### Scenario: 修复方案分析
- **WHEN** 分析updateSignStatus2接口的修复方案
- **THEN** 识别修复是否真正解决了根本问题（权限校验 vs 参数校验 vs 接口下线）

#### Scenario: 同类接口一致性检查
- **WHEN** 检查其他功能相似的接口是否也进行了相同的修复
- **THEN** 验证修复是否覆盖了所有同类接口

### Requirement: 阶段6——安全测试报告更新
系统 SHALL 更新安全测试报告，包含所有新发现。

#### Scenario: 报告更新
- **WHEN** 全面安全评估完成
- **THEN** 报告应包含：漏洞位置、利用方法、影响范围、严重程度、修复建议、修复有效性评估
