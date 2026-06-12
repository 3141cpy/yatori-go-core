# Tasks

- [ ] Task 1: 设计流量拦截方案并编写mitmproxy拦截脚本
  - [ ] 1.1 编写mitmproxy addon脚本，拦截所有发往*.chaoxing.com的请求
  - [ ] 1.2 脚本应记录：URL、HTTP方法、请求Header、请求参数、响应状态码、响应体
  - [ ] 1.3 特别关注签到相关API路径（pptSign/newsign/widget/sign/v2/apis/sign等）
  - [ ] 1.4 自动匹配已知API端点并标注

- [ ] Task 2: 编写签到状态实时监控脚本
  - [ ] 2.1 使用学生账号登录，轮询V2 signIn API获取当前签到状态
  - [ ] 2.2 记录每次查询的完整响应（含status、updatetime、teaUpdateFlag等）
  - [ ] 2.3 检测签到状态变化并记录精确时间戳
  - [ ] 2.4 使用教师账号同步验证签到状态

- [ ] Task 3: 编写账号活动日志分析脚本
  - [ ] 3.1 查询测试账号的签到历史记录
  - [ ] 3.2 分析签到记录中的teaUpdateFlag、updatetime等字段
  - [ ] 3.3 对比使用第三方网站前后的签到记录差异
  - [ ] 3.4 识别修改操作的来源（IP、UA、时间等）

- [ ] Task 4: 编写完整操作指南文档
  - [ ] 4.1 mitmproxy安装和配置步骤
  - [ ] 4.2 浏览器代理配置步骤
  - [ ] 4.3 HTTPS证书安装步骤
  - [ ] 4.4 第三方网站操作流程
  - [ ] 4.5 流量分析和漏洞定位步骤

- [ ] Task 5: 编写自动化差异分析脚本
  - [ ] 5.1 解析mitmproxy捕获的流量日志
  - [ ] 5.2 自动匹配已知100+域名的签到API端点
  - [ ] 5.3 生成差异报告：第三方网站调用了哪些API、使用了什么参数
  - [ ] 5.4 推断漏洞利用方法（CSRF/越权/教师账号/内部API等）

# Task Dependencies
- Task 1 和 Task 2 可并行执行
- Task 3 depends on Task 2（需要监控数据作为基线）
- Task 5 depends on Task 1 和 Task 3（需要流量数据和状态变化数据）
- Task 4 可与 Task 1-3 并行编写
