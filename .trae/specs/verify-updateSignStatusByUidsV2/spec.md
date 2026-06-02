# updateSignStatusByUidsV2 API漏洞验证 Spec

## Why
用户提供了学习通签到状态修改的V2 API端点 `updateSignStatusByUidsV2`，这是之前测试中从未发现的关键API。该API使用multipart/form-data格式、支持批量uids参数、带有DB_STRATEGY路由参数，可能是知情人士描述的"只能改状态"漏洞的实际利用路径。需立即验证此API的权限校验机制和学生越权可能性。

## What Changes
- 测试 `updateSignStatusByUidsV2` API的教师端调用行为
- 测试学生账号越权调用此API
- 验证此API是否"只能改状态"（不需要位置/二维码/手势信息）
- 测试不同status值、不同uids组合
- 测试DB_STRATEGY参数的影响
- 更新安全测试报告

## Impact
- Affected APIs: `POST /pptSign/updateSignStatusByUidsV2`
- Test accounts: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
- Course: courseId=257485372, classId=132821141（课程名exam，班级名111）
- ActiveId: 5000163767353（测试签到活动）

## ADDED Requirements

### Requirement: 验证updateSignStatusByUidsV2 API
系统 SHALL 验证updateSignStatusByUidsV2 API的权限校验和越权可能性。

#### Scenario: 教师端调用updateSignStatusByUidsV2
- **WHEN** 教师账号使用multipart/form-data格式调用updateSignStatusByUidsV2
- **THEN** 应记录API响应，确认是否可修改签到状态

#### Scenario: 学生越权调用updateSignStatusByUidsV2
- **WHEN** 学生账号尝试调用updateSignStatusByUidsV2
- **THEN** 验证是否可越权修改签到状态

#### Scenario: "只能改状态"特征验证
- **WHEN** 调用updateSignStatusByUidsV2时仅提供uids和status参数
- **THEN** 验证是否无需位置/二维码/手势信息即可修改签到状态

### Requirement: 更新安全测试报告
系统 SHALL 更新安全测试报告，包含updateSignStatusByUidsV2的测试结果。

#### Scenario: 报告更新
- **WHEN** 测试完成
- **THEN** 报告应包含新API的漏洞验证过程、权限校验分析及修复建议
