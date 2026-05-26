# Tasks

## 第一阶段：调查

- [x] Task 1: 教师管理API端点调查
  - [x] SubTask 1.1: 联网搜索教师创建签到的API端点 — `/ppt/activeAPI/createActive`
  - [x] SubTask 1.2: 联网搜索教师管理活动的API端点 — `/ppt/activeAPI/deleteActive`
  - [x] SubTask 1.3: 联网搜索教师课程管理的API端点 — `/mycourse/teacherindex`, `/clazz/update`
  - [x] SubTask 1.4: 分析代码库中的角色判断逻辑 — `roletype`字段（0/1/3）
  - [x] SubTask 1.5: 整理所有教师管理API端点清单

- [x] Task 2: 角色校验机制调查
  - [x] SubTask 2.1: 分析Cookie中sso_role字段 — **不存在sso_role Cookie**
  - [x] SubTask 2.2: 分析API请求中role参数的作用 — **服务端不依赖role参数**
  - [x] SubTask 2.3: 分析cpi与角色的关系 — **roletype=3为学生，roletype=1为教师**
  - [x] SubTask 2.4: 确定哪些API端点依赖角色校验 — **创建/删除活动、课程设置等均校验角色**

## 第二阶段：实际测试

- [x] Task 3: 签到系统垂直越权测试
  - [x] SubTask 3.1: 使用学生账号获取课程活动列表 — **成功（正常功能）**
  - [x] SubTask 3.2: 使用学生账号尝试创建签到活动 — **被拒绝，防护有效**
  - [x] SubTask 3.3: 使用学生账号尝试创建投票/问卷/随堂练习 — **被拒绝，防护有效**
  - [x] SubTask 3.4: 使用学生账号尝试删除活动 — **未测试（无活动ID）**
  - [x] SubTask 3.5: 使用学生账号查看签到结果 — **未测试（无活动ID）**

- [x] Task 4: 活动管理垂直越权测试
  - [x] SubTask 4.1: 使用学生账号尝试创建投票/问卷活动 — **被拒绝**
  - [x] SubTask 4.2: 使用学生账号尝试创建随堂练习 — **被拒绝**
  - [x] SubTask 4.3: 使用学生账号尝试管理活动结果 — **被拒绝**

- [x] Task 5: 课程管理垂直越权测试
  - [x] SubTask 5.1: 使用学生账号访问课程管理页面 — **404，被拒绝**
  - [x] SubTask 5.2: 使用学生账号尝试修改课程设置 — **被拒绝**
  - [x] SubTask 5.3: 使用学生账号尝试查看班级学习统计 — **被拒绝**
  - [x] SubTask 5.4: 使用学生账号尝试管理课程成员 — **被拒绝**

- [x] Task 6: 角色参数篡改测试
  - [x] SubTask 6.1: 修改Cookie中sso_role参数（3→1） — **无法绕过，服务端不依赖Cookie中的sso_role**
  - [x] SubTask 6.2: 在API请求中添加role=1参数 — **无法绕过**
  - [x] SubTask 6.3: 修改roletype参数值 — **未测试（roletype由服务端返回）**
  - [x] SubTask 6.4: 使用教师cpi访问教师管理API — **未测试（无教师账号）**

- [x] Task 7: 垂直越权评估报告生成
  - [x] SubTask 7.1: 汇总所有垂直越权测试结果
  - [x] SubTask 7.2: 分析角色校验机制的安全性
  - [x] SubTask 7.3: 构建垂直越权攻击链
  - [x] SubTask 7.4: 提出针对性修复建议

# Task Dependencies
- [Task 3-6] depends on [Task 1-2]
- [Task 3, 4, 5, 6] 可并行执行
- [Task 7] depends on [Task 3-6]
