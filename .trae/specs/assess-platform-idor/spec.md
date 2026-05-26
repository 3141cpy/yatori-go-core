# 学习通越权漏洞全面评估 Spec

## Why
基于前三个阶段的安全评估（个人云盘IDOR、小组云盘IDOR、密钥泄露审计），已发现学习通存在系统性的安全凭证泄露问题。这些泄露的密钥和签名算法大幅降低了攻击者利用越权漏洞的门槛——攻击者可以伪造合法的移动端签名绕过API认证，进而对课程、作业、考试、人脸验证等核心功能进行越权测试。需要系统性地评估泄露密钥对越权漏洞的实际影响，并在云盘之外的功能模块中寻找和验证越权漏洞。

## What Changes
- 基于已泄露密钥，系统性分析学习通各功能模块的越权攻击面
- 对课程信息、作业、考试、人脸验证、视频学时、用户信息等模块进行越权测试
- 验证泄露的签名算法和Token是否可用于绕过越权防护
- 编写自动化测试脚本验证发现的越权漏洞
- 生成越权漏洞安全评估报告

## Impact
- Affected specs: assess-cloud-drive-idor, assess-group-drive-idor, audit-exposed-secrets
- Affected code: api/xuexitong/ 目录下所有API文件
- Affected APIs: mooc1-api.chaoxing.com, mooc1.chaoxing.com, exam-ans.chaoxing.com, passport2-api.chaoxing.com

## ADDED Requirements

### Requirement: 越权攻击面分析
系统 SHALL 基于已泄露的密钥和签名算法，分析学习通各功能模块可能存在的越权漏洞。

#### Scenario: 密钥泄露对越权漏洞的影响分析
- **WHEN** 攻击者拥有所有泄露的密钥和签名算法
- **THEN** 应明确列出哪些API端点的越权防护可能被绕过，以及攻击者可利用的具体方式

### Requirement: 课程信息越权测试
系统 SHALL 验证课程相关API是否存在越权访问漏洞。

#### Scenario: 跨用户访问课程信息
- **WHEN** 使用账号1的Cookie访问账号2的课程列表或课程详情
- **THEN** 验证服务端是否校验请求者与课程归属关系

#### Scenario: 使用泄露Token访问他人课程
- **WHEN** 使用泄露的全局Token(K6)和DES密钥(K7)构造移动端请求访问他人课程
- **THEN** 验证是否可绕过Cookie身份校验

### Requirement: 作业系统越权测试
系统 SHALL 验证作业相关API是否存在越权访问漏洞。

#### Scenario: 查看他人作业
- **WHEN** 修改workId/classId/courseId参数尝试访问他人作业
- **THEN** 验证是否可查看或提交他人作业

#### Scenario: 代替他人提交作业
- **WHEN** 使用泄露的enc签名构造作业提交请求，修改userId为目标用户
- **THEN** 验证是否可代替他人提交作业

### Requirement: 考试系统越权测试
系统 SHALL 验证考试相关API是否存在越权访问漏洞。

#### Scenario: 查看他人考试信息
- **WHEN** 修改examId/classId/courseId参数尝试访问他人考试
- **THEN** 验证是否可查看他人考试题目或成绩

#### Scenario: 代替他人答题
- **WHEN** 使用泄露的考试签名算法(K9)构造答题请求
- **THEN** 验证是否可代替他人提交考试答案

### Requirement: 人脸验证越权测试
系统 SHALL 验证人脸验证系统是否存在越权漏洞。

#### Scenario: 绕过他人人脸验证
- **WHEN** 使用泄露的人脸验证盐值(K4)为目标用户构造enc签名
- **THEN** 验证是否可代替他人通过人脸验证

#### Scenario: 查看他人人脸验证状态
- **WHEN** 修改cpi/objectId参数查看他人的人脸验证状态
- **THEN** 验证是否可获取他人人脸验证信息

### Requirement: 视频学时越权测试
系统 SHALL 验证视频学时提交系统是否存在越权漏洞。

#### Scenario: 为他人刷视频学时
- **WHEN** 使用泄露的视频盐值(K3)为目标用户构造enc签名提交学时
- **THEN** 验证是否可为他人伪造视频观看记录

### Requirement: 用户信息越权测试
系统 SHALL 验证用户信息相关API是否存在越权访问漏洞。

#### Scenario: 查看他人用户信息
- **WHEN** 修改puid/uid参数尝试访问他人用户资料
- **THEN** 验证是否可获取他人手机号、姓名等敏感信息

### Requirement: JWT令牌伪造越权测试
系统 SHALL 验证JWT令牌(p_auth_token)是否可被伪造用于越权。

#### Scenario: 暴力破解JWT签名密钥
- **WHEN** 使用hashcat对从源码中提取的JWT令牌进行暴力破解
- **THEN** 验证HS256签名密钥是否为弱密钥

#### Scenario: 伪造JWT令牌访问他人资源
- **WHEN** 如果JWT密钥被破解，伪造包含目标用户uid的JWT令牌
- **THEN** 验证是否可冒充目标用户访问API

### Requirement: 越权漏洞安全评估报告
系统 SHALL 生成完整的越权漏洞安全评估报告。

#### Scenario: 报告内容完整性
- **WHEN** 评估完成
- **THEN** 报告应包含：越权攻击面分析、每个模块的测试结果、密钥泄露对越权漏洞的影响分析、攻击链分析、修复建议

## MODIFIED Requirements

### Requirement: 现有安全评估范围扩展
在已完成个人云盘、小组云盘和密钥泄露评估的基础上，将评估范围扩展至越权漏洞对全平台功能的影响。

## REMOVED Requirements

无移除需求。

---

## 附录：越权漏洞潜在攻击面

### 基于密钥泄露的越权攻击面分析

| 功能模块 | 关键API | 关键ID参数 | 泄露密钥影响 | 潜在越权类型 |
|---|---|---|---|---|
| 课程信息 | /mycourse/backclazzdata, /mycourse/stu-job-info | courseId, classId, cpi | K6/K7可构造移动端请求 | 水平越权 |
| 作业系统 | /work/task-list, /work/phone/doHomeWork | workId, courseId, classId, userId, enc | K5阅读盐值可伪造enc | 水平越权+写入 |
| 考试系统 | /exam/phone/task-list, /exam/test/reVersionTestStartNew, /exam/test/reVersionSubmitTestNew | examId, courseId, classId, cpi, testPaperId | K9考试签名可伪造 | 水平越权+写入 |
| 人脸验证 | /facephoto/clientfacecheckstatus, /mycourse/studentstudyAjax | courseId, clazzId, cpi, objectId | K4人脸盐值可伪造enc | 水平越权+绕过 |
| 视频学时 | /multimedia/log/a/{cpi}/{dtoken} | clazzId, courseId, objectId, userid, enc | K3视频盐值可伪造enc | 水平越权+写入 |
| 阅读任务 | /ananas/job/readv2 | jobid, knowledgeid, courseid, clazzid, jtoken | K5阅读盐值可伪造签名 | 水平越权+写入 |
| 用户信息 | /visit/stucoursemiddle, passport2-api | puid, uid | K6全局Token可绕认证 | 水平越权 |
| JWT认证 | p_auth_token | uid (in payload) | K17 JWT可能被伪造 | 垂直越权+身份冒充 |

### 越权测试方法论

1. **水平越权（IDOR）**: 使用账号1的凭证，修改ID参数为账号2的ID，验证是否能访问账号2的资源
2. **签名绕过越权**: 使用泄露的密钥构造合法签名，修改userId等参数为目标用户，验证服务端是否仅校验签名而未校验身份
3. **Token替换越权**: 使用泄露的全局Token(K6)替换动态Token，验证是否可绕过身份校验
4. **JWT伪造越权**: 如果JWT签名密钥可被破解，伪造包含目标用户uid的JWT令牌
