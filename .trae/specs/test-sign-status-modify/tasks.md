# Tasks

## 第一阶段：签到系统API调查与基线测试

- [ ] Task 1: 教师账号登录并创建签到活动
  - [ ] SubTask 1.1: 使用教师账号(19712720708)登录学习通
  - [ ] SubTask 1.2: 获取"111"课程的courseId和classId
  - [ ] SubTask 1.3: 教师创建普通签到活动
  - [ ] SubTask 1.4: 教师创建位置签到活动
  - [ ] SubTask 1.5: 记录创建的签到活动activeId

- [ ] Task 2: 学生账号基线测试
  - [ ] SubTask 2.1: 使用学生账号(18436633997)登录学习通
  - [ ] SubTask 2.2: 学生获取"111"课程的活动列表
  - [ ] SubTask 2.3: 学生正常完成一次签到
  - [ ] SubTask 2.4: 学生查看自己的签到状态

## 第二阶段：签到状态修改漏洞测试

- [ ] Task 3: 重复签到测试
  - [ ] SubTask 3.1: 学生在已签到状态下再次调用签到API
  - [ ] SubTask 3.2: 清除localStorage后再次签到
  - [ ] SubTask 3.3: 修改deviceCode后再次签到
  - [ ] SubTask 3.4: 使用不同Cookie/Session重复签到

- [ ] Task 4: 签到参数篡改测试
  - [ ] SubTask 4.1: 修改activeId参数尝试完成其他签到
  - [ ] SubTask 4.2: 修改uid参数尝试代替他人签到
  - [ ] SubTask 4.3: 修改签到时间参数尝试补签
  - [ ] SubTask 4.4: 修改activeType参数尝试改变签到类型

- [ ] Task 5: 位置签到伪造测试
  - [ ] SubTask 5.1: 使用伪造经纬度提交位置签到
  - [ ] SubTask 5.2: 使用极端经纬度值测试服务端校验
  - [ ] SubTask 5.3: 不带位置参数提交位置签到

- [ ] Task 6: 签到状态回改测试
  - [ ] SubTask 6.1: 学生调用教师端修改签到状态API
  - [ ] SubTask 6.2: 学生尝试将缺勤状态改为已签
  - [ ] SubTask 6.3: 学生尝试修改签到结果中的状态字段

## 第三阶段：深度测试与报告

- [ ] Task 7: 签到API完整参数分析
  - [ ] SubTask 7.1: 分析stuSignajax所有参数的作用和校验逻辑
  - [ ] SubTask 7.2: 分析签到状态在服务端的存储和校验机制
  - [ ] SubTask 7.3: 分析前端校验与服务端校验的差异

- [ ] Task 8: 签到状态修改漏洞安全测试报告
  - [ ] SubTask 8.1: 汇总所有测试结果
  - [ ] SubTask 8.2: 分析漏洞利用条件和影响范围
  - [ ] SubTask 8.3: 确定漏洞严重程度
  - [ ] SubTask 8.4: 提出针对性修复建议

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3-6] depends on [Task 2]
- [Task 3, 4, 5, 6] 可并行执行
- [Task 7] depends on [Task 3-6]
- [Task 8] depends on [Task 7]
