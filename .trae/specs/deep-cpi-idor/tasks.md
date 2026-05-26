# Tasks

- [x] Task 1: 解决代理问题，获取完整Cookie
  - [x] SubTask 1.1: 登录后访问i.chaoxing.com/base获取额外Cookie（jrose、route等）— **成功获取20个Cookie**
  - [x] SubTask 1.2: 使用移动端UA（含schild签名）+完整Cookie验证API可访问性 — **API访问成功**
  - [x] SubTask 1.3: 对比有无i.chaoxing.com Cookie时API响应差异 — **i.chaoxing.com Cookie解决了404问题**

- [x] Task 2: 课程章节CPI越权测试（/gas/clazz）
  - [x] SubTask 2.1: 使用账号1的Cookie+账号1的cpi请求PullChapter — **基线成功**
  - [x] SubTask 2.2: 使用账号1的Cookie+账号2的cpi请求PullChapter — **🔴 越权成功！**
  - [x] SubTask 2.3: 分析返回的章节列表是否包含敏感信息 — **包含知识点列表+章节名称**

- [x] Task 3: 章节任务点状态CPI越权测试（/job/myjobsnodesmap）
  - [x] SubTask 3.1: 使用账号1的Cookie+账号1的cpi请求 — **失败（API可能需要特定参数）**
  - [x] SubTask 3.2: 使用账号1的Cookie+账号2的cpi+账号2的userid请求 — **被拒绝**
  - [x] SubTask 3.3: 使用账号1的Cookie+账号2的cpi+账号1的userid请求 — **被拒绝，cpi与userid绑定**

- [x] Task 4: 知识节点详情CPI越权测试（/gas/knowledge）
  - [x] SubTask 4.1: 使用K6 Token+账号1的courseId请求 — **成功，K6 Token不绑定用户身份**
  - [x] SubTask 4.2: 使用K6 Token+账号2的courseId请求 — **🔴 成功！K6 Token可访问任意课程知识节点**
  - [x] SubTask 4.3: 无Cookie仅使用K6 Token请求 — **🔴 成功！K6 Token=万能密钥**

- [x] Task 5: 知识卡片资源CPI越权测试（/mooc-ans/knowledge/cards）
  - [x] SubTask 5.1: 使用账号1的Cookie+账号1的cpi请求 — **失败（可能需要特定knowledgeid）**
  - [x] SubTask 5.2: 使用账号1的Cookie+账号2的cpi请求 — **被拒绝**

- [x] Task 6: 进入章节CPI越权测试（/mooc-ans/mycourse/studentstudyAjax）
  - [x] SubTask 6.1: 使用账号1的Cookie+账号1的cpi请求 — **成功**
  - [x] SubTask 6.2: 使用账号1的Cookie+账号2的cpi请求 — **🔴 越权成功！**

- [x] Task 7: 课程完成度CPI越权测试（/mooc2-ans/mycourse/stu-job-info）
  - [x] SubTask 7.1: 使用账号1的Cookie请求自己的课程完成度 — **成功**
  - [x] SubTask 7.2: 使用账号1的Cookie+账号2的clazzPersonStr请求 — **🔴 越权成功！**

- [x] Task 8: CPI获取方式评估
  - [x] SubTask 8.1: 分析cpi是否可通过课程列表API获取 — **是！课程列表API包含cpi字段**
  - [x] SubTask 8.2: 分析cpi是否可通过讨论区/小组等公开信息获取 — **小组API不包含cpi**
  - [x] SubTask 8.3: 评估cpi的保密性 — **cpi为半公开信息，任何已登录用户可通过课程列表获取**

- [x] Task 9: CPI越权完整攻击链评估与报告生成
  - [x] SubTask 9.1: 构建从cpi获取到数据泄露的完整攻击链
  - [x] SubTask 9.2: 评估cpi越权可泄露的数据范围
  - [x] SubTask 9.3: 生成课程CPI越权深入评估报告
  - [x] SubTask 9.4: 提出针对性修复建议

# Task Dependencies
- [Task 2-7] depends on [Task 1]
- [Task 2, 3, 4, 5, 6, 7] 可并行执行
- [Task 8] 可与Task 2-7并行
- [Task 9] depends on [Task 2-8]
