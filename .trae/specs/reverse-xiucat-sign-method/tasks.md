# Tasks

- [ ] Task 1: 基线测试 — 教师修改本班学生签到状态
  - [ ] 1.1 使用19712720708(教师)登录，获取课程257485372的签到活动列表
  - [ ] 1.2 调用updateSignStatusByUidsV2修改uid=431407443在本课程的签到状态
  - [ ] 1.3 验证签到状态是否实际修改（通过V2 signIn接口确认）
  - [ ] 1.4 测试updateSignStatus2在mobilelearn.chaoxing.com上的行为
  - [ ] 1.5 测试newsign/updateSignStatus的行为

- [ ] Task 2: 水平越权测试 — 教师修改非本班学生签到状态（核心！）
  - [ ] 2.1 使用19712720708(教师)登录
  - [ ] 2.2 获取课程262934472("好好学习，天天向上")的签到活动列表
  - [ ] 2.3 尝试调用updateSignStatusByUidsV2修改uid=431407443在课程262934472的签到状态
  - [ ] 2.4 尝试调用updateSignStatus修改uid=431407443在课程262934472的签到状态
  - [ ] 2.5 尝试调用updateSignStatus2修改uid=431407443在课程262934472的签到状态
  - [ ] 2.6 尝试调用newsign/updateSignStatus修改uid=431407443在课程262934472的签到状态
  - [ ] 2.7 验证签到状态是否实际修改
  - [ ] 2.8 如果成功，测试是否可以修改任意uid的签到状态（随机uid）

- [ ] Task 3: 越权能力边界测试
  - [ ] 3.1 测试教师是否能获取非本课程的签到活动列表
  - [ ] 3.2 测试教师是否能获取非本课程的签到码(getSignCode/refreshQRCode)
  - [ ] 3.3 测试教师是否能查看非本课程的签到详情(refeashSignList4Json2)
  - [ ] 3.4 测试教师是否能重置非本课程的签到状态(resetUserSignStatus)
  - [ ] 3.5 测试不同域名(mobilelearn/mooc1-api)上的越权行为差异

- [ ] Task 4: 学生创建课程获取教师权限测试
  - [ ] 4.1 确认19712720708是否已有自己创建的课程
  - [ ] 4.2 如果没有，尝试通过API创建课程
  - [ ] 4.3 使用19712720708的session调用教师专属API
  - [ ] 4.4 测试是否能修改其他课程的签到状态

- [ ] Task 5: 签到码/enc获取与利用测试
  - [ ] 5.1 教师获取课程257485372的签到码(getSignCode)
  - [ ] 5.2 教师获取课程257485372的二维码enc(refreshQRCode)
  - [ ] 5.3 学生使用获取的signCode调用stuSignajax完成签到
  - [ ] 5.4 学生使用获取的enc调用stuSignajax完成签到
  - [ ] 5.5 测试教师是否能获取非本课程的签到码

- [ ] Task 6: xiucat.top行为对比与漏洞匹配分析
  - [ ] 6.1 汇总所有测试结果
  - [ ] 6.2 分析xiucat.top最可能利用的漏洞类型
  - [ ] 6.3 评估各假设的匹配度
  - [ ] 6.4 更新安全审计报告

# Task Dependencies
- Task 1 是基线测试，必须先完成
- Task 2 depends on Task 1（需要基线结果对比）
- Task 3 depends on Task 2（需要先确认越权是否存在）
- Task 4 和 Task 5 可与 Task 2-3 并行
- Task 6 depends on all previous tasks
