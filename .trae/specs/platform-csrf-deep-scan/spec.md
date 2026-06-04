# 学习通平台全业务CSRF漏洞深度探索 Spec

## Why
之前的安全评估仅覆盖签到模块，已确认`/pptSign/updateSignStatusByUidsV2`存在CSRF漏洞。但学习通平台包含签到、作业、考试、课程管理、云盘、人脸识别、讨论等多个业务模块，每个模块都有大量数据修改接口。需要系统性地探索所有业务模块的CSRF漏洞，评估平台整体安全状况。

## What Changes
- 对学习通平台所有业务模块的数据修改接口进行CSRF漏洞测试
- 重点测试教师端管理接口（课程管理、作业管理、考试管理、学生管理等）
- 测试学生端数据修改接口（作业提交、考试提交、讨论发帖等）
- 对已发现的CSRF漏洞编写PoC
- 生成完整的技术报告

## Impact
- Affected domains: mobilelearn.chaoxing.com, mooc1-api.chaoxing.com, mooc1.chaoxing.com, stat2-ans.chaoxing.com, pan-yz.chaoxing.com, groupweb.chaoxing.com, passport2-api.chaoxing.com
- Test accounts: 教师 19712720708/3.1415926Cpy (puid=402644510), 学生 18436633997/3.1415926Cpy (puid=431407443)
- Course: courseId=257485372, classId=132821141

## 已知业务模块与API

### 1. 签到模块（已测试）
- `/pptSign/updateSignStatusByUidsV2` — CSRF已确认
- `/pptSign/stuSignajax` — 学生签到
- `/newsign/updateSignStatus` — 假success
- `/widget/sign/pcTeaSignController/updateSignStatus2` — 已修复

### 2. 课程管理模块
- `/ppt/activeAPI/createActive` — 创建活动
- `/ppt/activeAPI/endSign` — 结束签到
- `/ppt/activeAPI/deleteActive` — 删除活动
- `/ppt/activeAPI/taskactivelist` — 活动列表
- `/mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata` — 课程列表
- `/mooc1-api.chaoxing.com/mooc-ans/mycourse/studentstudyAjax` — 进入章节学习

### 3. 作业模块
- 作业列表、进入作业、提交作业答案等接口
- 域名: mooc1.chaoxing.com, mooc1-api.chaoxing.com

### 4. 考试模块
- 考试列表、进入考试、提交考试答案等接口
- 域名: mooc1.chaoxing.com, mooc1-api.chaoxing.com

### 5. 人脸识别模块
- `/mooc1-api.chaoxing.com/qr/updateqrstatus` — 过人脸
- `/mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus` — 人脸检查
- `/mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo` — 上传人脸信息
- `/mooc1-api.chaoxing.com/mooc-ans/facephoto/continuelearn` — 继续学习
- `/passport2-api.chaoxing.com/api/getUserFaceid` — 获取人脸ID
- `/pan-yz.chaoxing.com/upload` — 上传人脸图片

### 6. 云盘模块
- `/pan-yz.chaoxing.com/api/token/uservalid` — 获取token
- `/pan-yz.chaoxing.com/upload` — 上传文件
- `/groupweb.chaoxing.com/pc/resource/addResource` — 添加小组资源
- `/groupweb.chaoxing.com/pc/resource/addResourceFolder` — 创建文件夹
- `/groupweb.chaoxing.com/pc/resource/deleteResourceFile` — 删除文件
- `/groupweb.chaoxing.com/pc/resource/deleteResourceFolder` — 删除文件夹
- `/groupweb.chaoxing.com/pc/resource/moveResource` — 移动资源
- `/groupweb.chaoxing.com/pc/resource/updateResourceFolderName` — 重命名

### 7. AI模块
- `/stat2-ans.chaoxing.com/stat2/bot/talk-v1` — AI对话

### 8. 章节学习模块
- `/mooc1-api.chaoxing.com/job/myjobsnodesmap` — 章节任务点状态
- `/mooc1-api.chaoxing.com/gas/clazz` — 拉取章节
- `/mooc1-api.chaoxing.com/gas/knowledge` — 拉取知识点
- `/mooc1.chaoxing.com/mooc-ans/knowledge/cards` — 知识点卡片

## ADDED Requirements

### Requirement: 全业务模块CSRF漏洞扫描
系统 SHALL 对学习通平台所有业务模块的数据修改接口进行CSRF漏洞测试。

#### Scenario: 教师端管理接口CSRF测试
- **WHEN** 使用教师session对教师端管理接口进行CSRF测试（无Referer、无CSRF Token、GET方式）
- **THEN** 记录每个接口的CSRF防护状态

#### Scenario: 学生端数据修改接口CSRF测试
- **WHEN** 使用学生session对学生端数据修改接口进行CSRF测试
- **THEN** 记录每个接口的CSRF防护状态

#### Scenario: 跨域接口CSRF测试
- **WHEN** 测试不同域名下的接口是否存在跨域CSRF
- **THEN** 识别跨域请求的CORS配置和CSRF防护

### Requirement: 高危接口深度测试
系统 SHALL 对发现的高危CSRF接口进行深度测试和PoC编写。

#### Scenario: 可修改成绩/状态的接口
- **WHEN** 发现可修改成绩、签到状态、作业状态等关键数据的CSRF漏洞
- **THEN** 编写完整的PoC并验证数据确实被修改

#### Scenario: 可删除数据的接口
- **WHEN** 发现可删除课程、作业、文件等数据的CSRF漏洞
- **THEN** 编写PoC并评估影响范围

### Requirement: 技术报告生成
系统 SHALL 生成完整的CSRF漏洞技术报告。

#### Scenario: 报告内容
- **WHEN** 所有测试完成
- **THEN** 报告应包含：每个业务模块的CSRF防护状态、漏洞详情、PoC、影响范围、修复建议
