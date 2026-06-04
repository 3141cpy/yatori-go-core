# Tasks

- [x] Task 1: 签到模块CSRF深度验证（已有发现确认+扩展）
  - [x] 1.1 验证`/pptSign/updateSignStatusByUidsV2` GET/POST CSRF（无Referer、无Token、跨域Origin）
  - [x] 1.2 测试`/pptSign/stuSignajax`是否存在CSRF（学生签到伪造）
  - [x] 1.3 测试`/ppt/activeAPI/createActive`、`/ppt/activeAPI/endSign`、`/ppt/activeAPI/deleteActive`的CSRF
  - [x] 1.4 测试`/newsign/updateSignStatus`的CSRF

- [x] Task 2: 课程管理模块CSRF测试
  - [x] 2.1 测试`/mooc1-api.chaoxing.com/mooc-ans/mycourse/studentstudyAjax` CSRF
  - [x] 2.2 测试`/mooc1-api.chaoxing.com/job/myjobsnodesmap` CSRF
  - [x] 2.3 枚举并测试`/mooc1-api.chaoxing.com/mooc-ans/`下其他数据修改接口
  - [x] 2.4 枚举并测试`/mooc1.chaoxing.com/mooc-ans/`下数据修改接口

- [x] Task 3: 作业与考试模块CSRF测试
  - [x] 3.1 枚举作业提交相关接口（SubmitWorkAnswerApi等）
  - [x] 3.2 枚举考试提交相关接口（SubmitExamAnswerApi等）
  - [x] 3.3 测试作业/考试接口的CSRF防护状态
  - [x] 3.4 测试是否可通过CSRF替他人提交作业/考试

- [x] Task 4: 人脸识别模块CSRF测试
  - [x] 4.1 测试`/mooc1-api.chaoxing.com/qr/updateqrstatus` CSRF
  - [x] 4.2 测试`/mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus` CSRF
  - [x] 4.3 测试`/mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo` CSRF
  - [x] 4.4 测试`/mooc1-api.chaoxing.com/mooc-ans/facephoto/continuelearn` CSRF
  - [x] 4.5 评估人脸识别CSRF的影响（是否可绕过人脸验证）

- [x] Task 5: 云盘模块CSRF测试
  - [x] 5.1 测试`/pan-yz.chaoxing.com/upload` CSRF（文件上传）
  - [x] 5.2 测试`/groupweb.chaoxing.com/pc/resource/deleteResourceFile` CSRF（文件删除）
  - [x] 5.3 测试`/groupweb.chaoxing.com/pc/resource/addResource` CSRF（资源添加）
  - [x] 5.4 测试`/groupweb.chaoxing.com/pc/resource/moveResource` CSRF（资源移动）
  - [x] 5.5 评估云盘CSRF的影响（是否可删除/上传他人文件）

- [x] Task 6: 其他模块CSRF测试
  - [x] 6.1 测试AI模块`/stat2-ans.chaoxing.com/stat2/bot/talk-v1` CSRF
  - [x] 6.2 测试讨论模块接口CSRF
  - [x] 6.3 测试通知模块接口CSRF
  - [x] 6.4 测试个人信息修改接口CSRF

- [x] Task 7: CSRF PoC编写与验证
  - [x] 7.1 为每个高危CSRF漏洞编写HTML PoC
  - [x] 7.2 验证PoC是否可实际修改数据
  - [x] 7.3 评估攻击链（多步骤CSRF组合）

- [x] Task 8: 技术报告生成
  - [x] 8.1 汇总所有发现，按业务模块分类
  - [x] 8.2 为每个漏洞提供：接口路径、HTTP方法、参数、CSRF防护状态、PoC、影响范围、修复建议
  - [x] 8.3 生成完整技术报告文件 `/workspace/csrf_vuln_tech_report.md`

# Task Dependencies
- Task 7 depends on Tasks 1-6（需要先发现漏洞才能编写PoC）
- Task 8 depends on all previous tasks
- Tasks 1-6 are independent and can run in parallel
