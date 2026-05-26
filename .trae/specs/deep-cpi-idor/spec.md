# 课程CPI越权漏洞深入研究 Spec

## Why
前一轮评估中确认了课程cpi越权访问漏洞（Web页面级别5/5课程可访问），但API级别的深入测试返回404，原因是使用了错误的API路径。通过分析Go源码，发现了正确的API端点（/gas/clazz、/job/myjobsnodesmap、/gas/knowledge、/mooc-ans/knowledge/cards、/mooc-ans/mycourse/studentstudyAjax等），需要使用这些正确端点进行深入越权测试，评估cpi越权可访问的完整范围。

## What Changes
- 使用Go源码中的正确API端点进行cpi越权测试
- 解决代理问题（通过i.chaoxing.com获取完整Cookie、使用移动端UA+Cookie方式）
- 测试课程章节、任务点、知识卡片、学习进度等子功能的cpi越权
- 评估cpi越权的完整攻击面（从课程列表到具体内容）
- 编写自动化测试脚本验证所有cpi越权场景

## Impact
- Affected specs: assess-platform-idor（扩展课程信息越权测试）
- Affected APIs: mooc1-api.chaoxing.com, mooc1.chaoxing.com, mooc2-ans.chaoxing.com
- Key code: XueXiTongChapterApi.go, XueXiTongCourseApi.go

## ADDED Requirements

### Requirement: 正确API端点的CPI越权测试
系统 SHALL 使用Go源码中发现的正确API端点进行cpi越权测试。

#### Scenario: 使用正确端点访问课程章节
- **WHEN** 使用账号1的Cookie+账号2的cpi请求 /gas/clazz?id=classId&personid=cpi
- **THEN** 验证是否可获取账号2的课程章节列表

#### Scenario: 使用正确端点访问章节任务点状态
- **WHEN** 使用账号1的Cookie+账号2的cpi请求 /job/myjobsnodesmap
- **THEN** 验证是否可获取账号2的章节任务点完成状态

#### Scenario: 使用正确端点访问知识卡片
- **WHEN** 使用账号1的Cookie+账号2的cpi请求 /mooc-ans/knowledge/cards
- **THEN** 验证是否可获取账号2的知识卡片内容（含视频、文档等资源）

#### Scenario: 使用正确端点进入章节
- **WHEN** 使用账号1的Cookie+账号2的cpi请求 /mooc-ans/mycourse/studentstudyAjax
- **THEN** 验证是否可代替账号2进入章节学习

#### Scenario: 使用正确端点获取知识节点详情
- **WHEN** 使用泄露Token(K6)请求 /gas/knowledge?id=nodeId&courseid=courseId&token=K6
- **THEN** 验证是否可获取知识节点详情（该接口使用K6 Token而非Cookie认证）

### Requirement: 代理问题解决
系统 SHALL 解决mooc1-api.chaoxing.com的API访问问题。

#### Scenario: 通过i.chaoxing.com获取完整Cookie
- **WHEN** 登录后访问i.chaoxing.com/base获取额外Cookie
- **THEN** 验证是否可解决API返回404/登录页的问题

#### Scenario: 使用移动端UA+Cookie方式访问
- **WHEN** 使用移动端UA（含schild签名）+完整Cookie访问API
- **THEN** 验证是否可正常获取API数据

### Requirement: CPI越权完整攻击面评估
系统 SHALL 评估cpi越权漏洞的完整攻击面。

#### Scenario: 从课程列表到具体内容的完整越权链
- **WHEN** 攻击者拥有目标用户的cpi
- **THEN** 验证攻击者可访问的目标用户数据范围（课程列表→章节→任务点→知识卡片→资源）

#### Scenario: CPI获取方式评估
- **WHEN** 分析cpi的获取途径
- **THEN** 评估cpi是否可通过公开信息推断或获取

### Requirement: 课程CPI越权深入评估报告
系统 SHALL 生成课程cpi越权漏洞的深入评估报告。

#### Scenario: 报告内容完整性
- **WHEN** 评估完成
- **THEN** 报告应包含：正确API端点测试结果、cpi越权完整攻击面、数据泄露范围评估、修复建议

---

## 附录：Go源码中发现的关键API端点

| API | URL | 关键参数 | 认证方式 | 功能 |
|---|---|---|---|---|
| PullChapter | /gas/clazz | id(classKey), personid(cpi), fields, view=json | Cookie | 课程章节列表 |
| FetchChapterPointStatus | /job/myjobsnodesmap | nodes, clazzid, userid, cpi, courseid | Cookie | 章节任务点状态 |
| FetchChapterCords | /gas/knowledge | id(nodeId), courseid, token=K6, _time | Cookie+K6 Token | 知识节点详情 |
| FetchChapterCords2 | /mooc-ans/knowledge/cards | clazzid, courseid, knowledgeid, cpi | Cookie | 知识卡片资源 |
| EnterChapterForwardCallApi | /mooc-ans/mycourse/studentstudyAjax | courseId, clazzid, chapterId, cpi | Cookie | 进入章节 |
| CourseCompleteStatusApi | /mooc2-ans/mycourse/stu-job-info | clazzPersonStr | Cookie | 课程完成度 |
| CourseListApi | /mycourse/backclazzdata | view=json, m=0 | Cookie | 课程列表 |

### 关键发现：/gas/knowledge 使用K6 Token认证
FetchChapterCords接口使用`token=4faa8662c59590c6f43ae9fe5b002b42`（K6全局Token）作为参数，而非Cookie认证。这意味着该接口可能不受Cookie身份校验限制，仅凭K6 Token即可访问知识节点详情。
