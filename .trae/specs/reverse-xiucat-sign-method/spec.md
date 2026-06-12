# 逆向分析xiucat.top签到修改方法 Spec

## Why
用户发现网站 beta-a.xiucat.top 可以修改学习通签到状态，经实际测试确认有效。由于该网站通过后端代理操作（前端无法直接看到调用逻辑），需要设计一套方案来捕获和逆向分析该网站所利用的漏洞。根据已有安全审计知识，最可能的利用方式是：**使用教师账号通过 updateSignStatusByUidsV2 等接口实现水平越权修改任意学生签到状态**。

## What Changes
- 设计并实现"蜜罐"测试方案：使用已知账号(19712720708)尝试修改另一账号(18436633997)所在课程的签到状态
- 验证水平越权假设：教师账号是否能修改非自己班级学生的签到状态
- 深入探索 updateSignStatusByUidsV2 的越权能力边界
- 探索其他可能的签到修改方法（如直接调用教师API、Cookie复用等）
- 对比该网站行为与已知漏洞的匹配度

## Impact
- Affected code: 新建测试脚本
- Test accounts: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
- Course 1: courseId=257485372, classId=132821141（课程exam，19712720708是教师）
- Course 2: courseId=262934472, classId=145110605（课程"好好学习，天天向上"，18436633997是学生）

## 核心假设分析

### 假设1：水平越权 — 教师修改非本班学生签到状态
- **可能性**: 高
- **原理**: updateSignStatusByUidsV2 接口仅检查请求者是否为教师，可能不检查教师与目标学生是否在同一课程/班级
- **验证方法**: 用19712720708(教师)调用updateSignStatusByUidsV2修改18436633997在courseId=262934472的签到状态

### 假设2：学生创建课程后获得教师权限
- **可能性**: 中
- **原理**: 19712720708虽然是学生身份，但可以创建课程成为自己课程的教师，可能利用此身份调用教师API
- **验证方法**: 用19712720708在自己创建的课程中获取教师权限，然后尝试修改其他课程的签到

### 假设3：利用已知的CSRF漏洞
- **可能性**: 低（需要诱导真实教师）
- **原理**: updateSignStatusByUidsV2 无CSRF防护，但需要教师主动触发

### 假设4：利用mobilelearn.chaoxing.com的updateSignStatus2权限缺陷
- **可能性**: 中
- **原理**: mobilelearn.chaoxing.com上updateSignStatus2对学生返回"参数错误"而非"无权限"，可能存在参数组合可绕过

### 假设5：获取签到码/enc后直接签到
- **可能性**: 中
- **原理**: 通过教师API获取signCode/enc，然后用学生身份完成签到

## ADDED Requirements

### Requirement: 水平越权验证
系统 SHALL 验证教师账号是否能修改非本课程学生的签到状态。

#### Scenario: 教师修改非本班学生签到
- **WHEN** 使用19712720708(教师)的session调用updateSignStatusByUidsV2，目标uid=431407443(学生)，activeId属于courseId=262934472
- **THEN** 应记录API是否返回success，签到状态是否实际被修改

#### Scenario: 教师修改本班学生签到（对照组）
- **WHEN** 使用19712720708(教师)的session调用updateSignStatusByUidsV2，目标uid=431407443(学生)，activeId属于courseId=257485372
- **THEN** 应确认签到状态成功修改（作为基线对照）

### Requirement: 越权能力边界测试
系统 SHALL 测试教师账号的越权能力边界。

#### Scenario: 跨课程修改
- **WHEN** 教师尝试修改非自己课程的学生签到状态
- **THEN** 应记录哪些接口允许跨课程操作，哪些不允许

#### Scenario: 跨班级修改
- **WHEN** 教师尝试修改同课程不同班级的学生签到状态
- **THEN** 应记录是否受班级限制

### Requirement: 学生创建课程获取教师权限测试
系统 SHALL 验证学生创建课程后是否能获得教师API调用权限。

#### Scenario: 学生创建课程后调用教师API
- **WHEN** 19712720708创建课程后，使用该session调用updateSignStatusByUidsV2
- **THEN** 应验证是否能成功修改签到状态

### Requirement: 签到码/enc获取与利用测试
系统 SHALL 验证通过教师API获取签到码后学生是否能完成签到。

#### Scenario: 教师获取签到码后学生签到
- **WHEN** 教师通过getSignCode/refreshQRCode获取signCode/enc
- **THEN** 学生使用该signCode/enc调用stuSignajax完成签到

### Requirement: xiucat.top行为对比分析
系统 SHALL 将测试结果与xiucat.top的行为进行对比。

#### Scenario: 行为匹配
- **WHEN** 完成所有漏洞验证后
- **THEN** 应分析xiucat.top最可能利用的漏洞类型，并给出匹配度评估
