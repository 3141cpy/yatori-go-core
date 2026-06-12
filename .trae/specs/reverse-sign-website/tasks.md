# Tasks

- [x] Task 0: 后端API结构探测（已完成：发现完整OpenAPI文档）
  - [x] 0.1 探测beta-a.xiucat.top基础结构
  - [x] 0.2 发现/openapi.json完整API文档
  - [x] 0.3 识别核心机制：系统教师账号代理修改

- [ ] Task 1: 编写签到状态监控脚本
  - [ ] 1.1 使用学生账号登录，轮询V2 signIn API获取当前签到状态
  - [ ] 1.2 记录每次查询的完整响应（含status、updatetime、teaUpdateFlag等）
  - [ ] 1.3 检测签到状态变化并记录精确时间戳
  - [ ] 1.4 使用教师账号同步验证签到状态变化

- [ ] Task 2: 验证教师账号代理修改机制
  - [ ] 2.1 在使用第三方网站前记录签到状态基线
  - [ ] 2.2 使用第三方网站修改签到状态
  - [ ] 2.3 检查签到记录中teaUpdateFlag是否变为1
  - [ ] 2.4 对比updatetime与补签任务完成时间
  - [ ] 2.5 分析clientip和useragent判断请求来源

- [ ] Task 3: 识别具体调用的学习通API端点
  - [ ] 3.1 分析OpenAPI文档中补签任务的参数结构
  - [ ] 3.2 对比targetStatus值与已知API的status参数映射
  - [ ] 3.3 测试已知教师端API（updateSignStatusByUidsV2/updateSignStatus2/newsign/updateSignStatus）
  - [ ] 3.4 通过参数匹配确定最可能的API端点

- [ ] Task 4: 编写完整验证报告
  - [ ] 4.1 记录漏洞利用方法（教师账号代理）
  - [ ] 4.2 记录具体API调用路径和参数
  - [ ] 4.3 记录影响范围和修复建议
  - [ ] 4.4 更新sign_vuln_report.md

# Task Dependencies
- Task 1 和 Task 3 可并行执行
- Task 2 depends on Task 1（需要监控脚本作为基线）
- Task 4 depends on Task 2 和 Task 3
