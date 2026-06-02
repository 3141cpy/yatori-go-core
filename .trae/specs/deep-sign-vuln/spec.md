# 签到状态修改漏洞深入验证 Spec

## Why
知情人士已确认学习通平台存在允许学生修改签到状态的漏洞，描述为"那个接口里只能改状态，然后什么信息都带不了，位置信息啊，二维码信息"。上一轮测试（sign-status-vuln）仅测试了已结束的签到活动且未找到"111"课程，测试范围不够深入。需要基于此线索，对教师端和学生端的签到API端点进行全面深入探索，定位可修改签到状态的具体接口。

## What Changes
- 基于知情人士线索"只能改状态，带不了位置/二维码信息"，重点探索仅接受status参数的API端点
- 全面枚举教师端和学生端签到相关API端点（包括已知和未知的）
- 使用教师账号创建一个进行中的签到活动，以测试进行中签到的状态修改
- 重新定位"111"课程（courseId/classId/cpi）
- 对每个发现的API端点进行状态修改测试
- 生成更新版安全测试报告

## Impact
- Affected specs: sign-status-vuln（上一轮签到测试，已发现1项MEDIUM但未确认核心漏洞）
- Affected APIs: mobilelearn.chaoxing.com 签到相关全部API端点
- Test accounts: 教师 19712720708/3.1415926Cpy, 学生 18436633997/3.1415926Cpy
- 关键线索: "只能改状态，带不了位置信息、二维码信息"——暗示存在一个仅修改status字段的API，绕过了签到类型的验证逻辑

## ADDED Requirements

### Requirement: 阶段1——签到API端点全面枚举
系统 SHALL 全面枚举学习通签到系统的所有API端点。

#### Scenario: 教师端API端点枚举
- **WHEN** 使用教师账号访问签到管理页面并抓取所有API请求
- **THEN** 应记录所有教师端签到API端点的URL、方法、参数、响应格式

#### Scenario: 学生端API端点枚举
- **WHEN** 使用学生账号访问签到页面并抓取所有API请求
- **THEN** 应记录所有学生端签到API端点的URL、方法、参数、响应格式

#### Scenario: 联网搜索未知API端点
- **WHEN** 搜索学习通签到API的公开信息（GitHub、技术博客、API文档等）
- **THEN** 应发现并记录所有公开已知的签到API端点

### Requirement: 阶段2——"111"课程定位与进行中签到创建
系统 SHALL 定位"111"课程并创建进行中的签到活动。

#### Scenario: 定位"111"课程
- **WHEN** 使用教师账号和学生账号分别获取课程列表
- **THEN** 应找到名为"111"的课程及其courseId/classId/cpi

#### Scenario: 创建进行中的签到活动
- **WHEN** 使用教师账号在"111"课程中创建一个普通签到活动（保持进行中状态，不手动结束）
- **THEN** 应记录新签到活动的activeId，确认学生端可见且未签到

### Requirement: 阶段3——基于线索的API端点定向测试
系统 SHALL 基于知情人士线索"只能改状态，带不了位置/二维码信息"进行定向测试。

#### Scenario: 测试仅修改status参数的API端点
- **WHEN** 学生账号尝试调用可能存在的状态修改API（如/pptSign/updateSignStatus、/pptSign/changeStatus、/pptSign/modifySign等）
- **THEN** 验证是否存在仅接受status参数而不验证签到类型的API端点

#### Scenario: 测试教师端签到管理API的学生可访问性
- **WHEN** 学生账号尝试调用教师端签到管理API（如修改签到结果、补签、修改状态等）
- **THEN** 验证学生是否可绕过角色校验直接修改签到状态

#### Scenario: 测试签到结果API的状态修改能力
- **WHEN** 学生账号尝试通过签到结果API修改自己的签到状态（从缺勤改为已签到）
- **THEN** 验证签到结果API是否接受status参数修改

#### Scenario: 测试不同签到类型的状态修改
- **WHEN** 对普通签到、手势签到、位置签到、二维码签到分别尝试仅修改status
- **THEN** 验证是否存在某种签到类型的状态可被直接修改而不需携带类型验证信息

### Requirement: 阶段4——preSign页面与前端逻辑深入分析
系统 SHALL 深入分析preSign页面的前端逻辑。

#### Scenario: 分析preSign页面的JavaScript代码
- **WHEN** 获取preSign页面的完整HTML和JS代码
- **THEN** 应分析其中包含的API调用、签到提交逻辑、状态修改逻辑

#### Scenario: 分析preSign页面中发现的API端点
- **WHEN** 从preSign页面的JS代码中提取API端点
- **THEN** 应逐一测试这些端点是否允许修改签到状态

### Requirement: 阶段5——漏洞验证与报告更新
系统 SHALL 验证发现的漏洞并更新安全测试报告。

#### Scenario: 漏洞验证
- **WHEN** 发现可能的状态修改漏洞
- **THEN** 应通过教师端确认签到状态是否确实被修改

#### Scenario: 报告更新
- **WHEN** 所有测试完成
- **THEN** 应更新安全测试报告，包含新发现的漏洞、利用条件、影响范围及修复建议

## MODIFIED Requirements

### Requirement: 签到状态修改漏洞评估（原sign-status-vuln）
上一轮测试结论"签到状态修改漏洞未确认"需基于新线索重新评估。核心线索："只能改状态，带不了位置/二维码信息"暗示存在一个绕过签到类型验证的状态修改接口。
