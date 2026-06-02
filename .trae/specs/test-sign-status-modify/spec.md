# 签到状态修改漏洞安全测试 Spec

## Why
有消息称学习通平台存在允许学生修改签到状态的漏洞。本次测试针对"111"课程的签到功能，使用教师账号和学生账号进行系统性安全测试，验证学生是否可以通过常规或非常规手段修改已提交的签到状态。

## What Changes
- 使用教师账号创建签到活动，学生账号执行签到/缺勤
- 测试学生修改已提交签到状态的各种攻击向量
- 测试伪造位置签到、重复签到、签到状态回改等场景
- 分析签到API的请求参数和校验逻辑
- 生成详细的安全测试报告

## Impact
- Affected APIs: mobilelearn.chaoxing.com/pptSign/stuSignajax, /ppt/activeAPI/taskactivelist, /pptSign/signedResult
- Affected specs: assess-vertical-idor（扩展签到系统测试）
- Test accounts: 教师 19712720708, 学生 18436633997, 课程 "111"

## ADDED Requirements

### Requirement: 第一阶段——签到系统API调查与基线测试
系统 SHALL 先调查签到API端点并建立基线，再进行漏洞测试。

#### Scenario: 教师创建签到活动
- **WHEN** 使用教师账号在"111"课程中创建签到活动
- **THEN** 应成功创建签到活动并获取activeId

#### Scenario: 学生查看签到活动列表
- **WHEN** 学生账号请求活动列表API
- **THEN** 应能看到教师创建的签到活动

#### Scenario: 学生正常签到
- **WHEN** 学生账号通过正常流程完成签到
- **THEN** 应成功签到，状态变为"已签"

#### Scenario: 学生查看自己的签到状态
- **WHEN** 学生账号查看签到结果
- **THEN** 应能看到自己的签到状态

### Requirement: 第二阶段——签到状态修改漏洞测试
系统 SHALL 测试学生修改已提交签到状态的各种攻击向量。

#### Scenario: 学生重复签到（已签到后再次签到）
- **WHEN** 学生账号在已签到状态下再次调用签到API
- **THEN** 验证服务端是否拒绝重复签到，以及是否有时间窗口允许重复操作

#### Scenario: 学生修改签到类型参数
- **WHEN** 学生账号在签到请求中修改activeType等参数
- **THEN** 验证是否可改变签到类型（如从普通签到改为位置签到）

#### Scenario: 学生伪造位置信息签到
- **WHEN** 学生账号在位置签到中提交伪造的经纬度
- **THEN** 验证服务端是否校验位置信息的合理性

#### Scenario: 学生修改签到时间参数
- **WHEN** 学生账号在签到请求中修改时间相关参数
- **THEN** 验证是否可在签到截止后补签

#### Scenario: 学生篡改签到结果API
- **WHEN** 学生账号调用签到结果修改API（如教师端的修改签到状态接口）
- **THEN** 验证是否可自行修改签到状态（缺勤→已签）

#### Scenario: 学生利用localStorage绕过设备限制
- **WHEN** 清除localStorage中的签到记录后再次签到
- **THEN** 验证是否可绕过"同一设备不允许重复签到"的限制

### Requirement: 第三阶段——签到API参数篡改深度测试
系统 SHALL 对签到API的每个参数进行篡改测试。

#### Scenario: 修改activeId参数
- **WHEN** 学生账号修改签到请求中的activeId为其他签到活动的ID
- **THEN** 验证是否可完成其他签到活动的签到

#### Scenario: 修改uid参数
- **WHEN** 学生账号修改签到请求中的uid为其他用户的ID
- **THEN** 验证是否可代替他人签到

#### Scenario: 修改fid参数
- **WHEN** 学生账号修改签到请求中的fid参数
- **THEN** 验证是否可绕过学校/机构校验

#### Scenario: 修改deviceCode参数
- **WHEN** 学生账号修改签到请求中的deviceCode
- **THEN** 验证是否可绕过设备唯一性校验

### Requirement: 签到状态修改漏洞安全测试报告
系统 SHALL 生成详细的安全测试报告。

#### Scenario: 报告内容完整性
- **WHEN** 测试完成
- **THEN** 报告应包含：漏洞验证过程、技术原理分析、漏洞利用条件、影响范围、严重程度、修复建议

---

## 附录：签到系统API端点（来自联网搜索和代码库分析）

### 核心API

| API | URL | 方法 | 功能 | 关键参数 |
|---|---|---|---|---|
| 获取活动列表 | /ppt/activeAPI/taskactivelist | GET | 获取课程活动列表 | courseId, classId, uid |
| 创建签到 | /ppt/activeAPI/createActive | POST | 教师创建签到 | courseId, classId, activeType, title |
| 学生签到 | /pptSign/stuSignajax | POST | 学生执行签到 | activeId, uid, fid, latitude, longitude, address, name, clientip, appType, ifTiJiao, validate, deviceCode |
| 签到结果 | /pptSign/signedResult | GET | 查看签到结果 | activeId, classId, courseId, uid |
| 删除活动 | /ppt/activeAPI/deleteActive | POST | 删除活动 | activeId, courseId, classId |

### 签到类型（activeType）

| activeType | 类型 | 说明 |
|---|---|---|
| 2 | 普通签到 | 学生直接点击签到 |
| 2+手势 | 手势签到 | 学生需画出指定手势 |
| 2+位置 | 位置签到 | 需要GPS定位，校验经纬度 |
| 2+二维码 | 二维码签到 | 需要扫描二维码 |

### 签到API安全机制（来自公开信息）

1. **重复签到防护**: 前端使用`chongfu`变量和`localStorage`防止重复签到
2. **设备唯一性**: 使用`deviceCode`参数校验设备唯一性
3. **位置校验**: 位置签到时服务端校验经纬度是否在签到范围内
4. **前端校验问题**: 位置信息通过`$("#latitude").val()`获取，可被JS篡改
5. **localStorage可清除**: 设备签到记录存储在localStorage中，可被清除后绕过
