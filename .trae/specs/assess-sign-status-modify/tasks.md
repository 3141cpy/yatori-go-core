# Tasks

## 第一阶段：调查

- [ ] Task 1: 签到API端点与流程调查
  - [ ] SubTask 1.1: 使用教师账号登录，获取"111"课程信息（courseId, classId, cpi）
  - [ ] SubTask 1.2: 使用教师账号获取活动列表，记录已有签到活动的activeId和状态
  - [ ] SubTask 1.3: 使用学生账号登录，获取"111"课程信息
  - [ ] SubTask 1.4: 使用学生账号获取活动列表，对比教师端与学生端的数据差异

## 第二阶段：签到状态修改测试

- [ ] Task 2: 学生获取已结束签到活动信息
  - [ ] SubTask 2.1: 学生账号请求活动列表，获取教师创建的签到活动activeId
  - [ ] SubTask 2.2: 学生账号请求签到前页面(/newsign/preSign)，获取签到参数
  - [ ] SubTask 2.3: 分析签到页面的HTML/JS代码，提取签到相关参数和逻辑

- [ ] Task 3: 学生对已结束签到执行签到操作
  - [ ] SubTask 3.1: 学生账号对已结束的普通签到调用stuSignajax
  - [ ] SubTask 3.2: 学生账号对已结束的位置签到调用stuSignajax（含伪造经纬度）
  - [ ] SubTask 3.3: 学生账号对已结束的手势签到/签到码签到调用stuSignajax
  - [ ] SubTask 3.4: 记录每个签到请求的响应，判断是否成功修改签到状态

- [ ] Task 4: 学生伪造/重放签到请求
  - [ ] SubTask 4.1: 构造签到请求（修改activeId为其他签到活动的ID）
  - [ ] SubTask 4.2: 构造签到请求（修改uid为其他学生的uid）
  - [ ] SubTask 4.3: 构造签到请求（修改appType参数）
  - [ ] SubTask 4.4: 构造签到请求（修改deviceCode参数绕过设备限制）
  - [ ] SubTask 4.5: 重放之前成功的签到请求

- [ ] Task 5: 学生查看/修改签到结果
  - [ ] SubTask 5.1: 学生账号请求签到结果API(/pptSign/signedResult)
  - [ ] SubTask 5.2: 学生账号尝试修改签到状态（调用教师端修改API）
  - [ ] SubTask 5.3: 学生账号尝试查看其他学生的签到状态

## 第三阶段：教师端验证

- [ ] Task 6: 教师端签到管理验证
  - [ ] SubTask 6.1: 教师账号查看签到结果，记录API端点和参数
  - [ ] SubTask 6.2: 教师账号修改学生签到状态（缺勤→已签），记录API端点
  - [ ] SubTask 6.3: 对比学生端修改前后教师端看到的签到状态变化

- [ ] Task 7: 签到状态修改漏洞评估报告生成
  - [ ] SubTask 7.1: 汇总所有签到状态修改测试结果
  - [ ] SubTask 7.2: 分析签到状态修改的漏洞利用条件和影响范围
  - [ ] SubTask 7.3: 确定漏洞严重程度
  - [ ] SubTask 7.4: 提出针对性修复建议
  - [ ] SubTask 7.5: 生成详细的安全测试报告

# Task Dependencies
- [Task 2-5] depends on [Task 1]
- [Task 6] depends on [Task 3]
- [Task 7] depends on [Task 2-6]
