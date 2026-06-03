# Tasks

- [x] Task 1: 实现核心框架 - 登录与课程获取
  - [x] SubTask 1.1: 实现AES-CBC加密登录函数（移动端方式，含schild签名UA）
  - [x] SubTask 1.2: 实现获取课程列表函数（/mycourse/backclazzdata）
  - [x] SubTask 1.3: 实现获取活动列表函数（/ppt/activeAPI/taskactivelist）
  - [x] SubTask 1.4: 实现查询签到状态函数（/v2/apis/sign/signIn）

- [x] Task 2: 实现交互式菜单系统
  - [x] SubTask 2.1: 登录菜单 - 输入账号密码
  - [x] SubTask 2.2: 课程选择菜单 - 编号选择课程
  - [x] SubTask 2.3: 活动列表菜单 - 展示签到活动及当前状态（按未签到/已签到分组）
  - [x] SubTask 2.4: 活动多选菜单 - 支持逗号分隔、范围选择、all全选
  - [x] SubTask 2.5: 状态选择菜单 - 展示0-6状态选项

- [x] Task 3: 实现签到状态修改与验证
  - [x] SubTask 3.1: 实现修改签到状态函数（/newsign/updateSignStatus，含Referer和X-Requested-With头）
  - [x] SubTask 3.2: 实现修改后自动验证（查询实际状态对比）
  - [x] SubTask 3.3: 实现批量修改逻辑（遍历选中活动逐一修改并验证）
  - [x] SubTask 3.4: 实现修改结果汇总展示（含修补检测）

- [x] Task 4: 测试与优化
  - [x] SubTask 4.1: 使用测试账号端到端测试完整流程
  - [x] SubTask 4.2: 修复发现的bug（API域名修正、添加必要请求头、schild签名UA）
  - [x] SubTask 4.3: 优化输出格式和用户体验（分组显示、修补检测、all关键字）

# Task Dependencies
- [Task 2] depends on [Task 1] ✅
- [Task 3] depends on [Task 1] ✅
- [Task 4] depends on [Task 1, Task 2, Task 3] ✅

# 重要发现
测试过程中发现 `/newsign/updateSignStatus` API仍返回"success"但实际不再执行修改。
这表明该漏洞可能已被服务端修补（静默失效模式），脚本已加入修补检测逻辑。
