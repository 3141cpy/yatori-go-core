# Tasks

## 阶段1：测试环境确认与教师端API发现

- [ ] Task 1: 重新确认测试环境
  - [ ] SubTask 1.1: 使用教师账号(19712720708)登录，获取课程列表，确认课程名和班级名"111"/"exam"的对应关系
  - [ ] SubTask 1.2: 使用学生账号(18436633997)登录，确认同一课程/班级信息
  - [ ] SubTask 1.3: 获取签到活动列表，确认哪些签到活动中学生为缺勤/未签状态

- [ ] Task 2: 教师端签到管理API发现
  - [ ] SubTask 2.1: 使用教师账号访问签到活动详情API（/ppt/activeAPI/getPPTActiveInfo等），记录响应
  - [ ] SubTask 2.2: 使用教师账号访问签到结果/统计API（/pptSign/signedResult等），记录响应
  - [ ] SubTask 2.3: 探索教师端签到管理页面，发现修改学生签到状态的API端点
  - [ ] SubTask 2.4: 枚举所有可能的签到管理API路径（/ppt/activeAPI/*、/pptSign/*等）

## 阶段2：教师端签到状态修改API测试

- [ ] Task 3: 教师端签到状态修改API功能测试
  - [ ] SubTask 3.1: 使用教师账号调用修改签到状态API，将学生状态从缺勤改为已签到，记录完整请求和响应
  - [ ] SubTask 3.2: 记录修改签到状态API的完整参数列表（activeId、studentId、status等）
  - [ ] SubTask 3.3: 测试不同签到类型（普通/手势/位置/二维码/签到码）的状态修改是否使用同一API
  - [ ] SubTask 3.4: 确认"只能改状态"的接口——不需要位置/二维码/手势等验证数据的接口

## 阶段3：学生越权调用教师端API

- [ ] Task 4: 学生直接调用教师端签到管理API
  - [ ] SubTask 4.1: 学生账号直接调用修改签到状态API（使用从教师端发现的API端点和参数）
  - [ ] SubTask 4.2: 学生账号调用签到结果/统计API
  - [ ] SubTask 4.3: 学生账号调用签到活动详情API
  - [ ] SubTask 4.4: 学生账号使用移动端UA（含schild签名）调用教师端API

- [ ] Task 5: 学生使用参数篡改绕过角色校验
  - [ ] SubTask 5.1: 在学生请求中添加roletype=1参数模拟教师角色
  - [ ] SubTask 5.2: 使用教师的cpi参数构造请求
  - [ ] SubTask 5.3: 使用K6 Token+DES密钥构造移动端教师请求
  - [ ] SubTask 5.4: 修改Cookie中的角色相关字段

## 阶段4："只能改状态"接口深入测试

- [ ] Task 6: 查找并测试"只能改状态"的API
  - [ ] SubTask 6.1: 枚举所有可能的签到状态修改API路径（/pptSign/updateSignStatus、/ppt/activeAPI/updateSignStatus、/pptSign/updateSign等）
  - [ ] SubTask 6.2: 测试每个发现的API端点，确认哪些只需要activeId+status即可修改状态
  - [ ] SubTask 6.3: 学生账号尝试调用"只能改状态"的API修改自己的签到状态
  - [ ] SubTask 6.4: 学生账号尝试修改其他学生的签到状态（跨用户IDOR）

- [ ] Task 7: 签到状态值枚举与篡改
  - [ ] SubTask 7.1: 枚举签到状态值（0=缺勤、1=已签到、2=迟到、3=请假等）
  - [ ] SubTask 7.2: 学生账号尝试通过修改status参数将缺勤改为已签到
  - [ ] SubTask 7.3: 学生账号尝试通过修改signResult参数改变签到结果
  - [ ] SubTask 7.4: 测试已结束签到活动的状态修改（status=2的活动）

## 阶段5：漏洞验证与报告更新

- [ ] Task 8: 漏洞验证
  - [ ] SubTask 8.1: 如果发现漏洞，完整记录漏洞利用过程
  - [ ] SubTask 8.2: 分析漏洞利用的前提条件和技术要求
  - [ ] SubTask 8.3: 评估漏洞影响范围和严重程度
  - [ ] SubTask 8.4: 构建完整的攻击链

- [ ] Task 9: 更新安全测试报告
  - [ ] SubTask 9.1: 更新/workspace/sign_vuln_report.md，添加新发现的漏洞
  - [ ] SubTask 9.2: 分析漏洞技术原理
  - [ ] SubTask 9.3: 确定漏洞利用条件、影响范围及严重程度
  - [ ] SubTask 9.4: 提出修复建议

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4, 5] depends on [Task 3]
- [Task 6, 7] depends on [Task 3]
- [Task 4, 5, 6, 7] 可并行执行
- [Task 8] depends on [Task 4-7]
- [Task 9] depends on [Task 8]
