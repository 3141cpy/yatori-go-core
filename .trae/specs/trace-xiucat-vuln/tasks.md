# Tasks

- [ ] Task 1: xiucat服务API注册与认证
  - [ ] 1.1 调用 `POST /api/auth/xiucat-quick-login` 使用学习通测试账号登录xiucat
  - [ ] 1.2 如果快捷登录失败，尝试 `POST /api/auth/login` 注册/登录
  - [ ] 1.3 获取JWT Token并验证有效性
  - [ ] 1.4 调用 `GET /api/me` 获取用户信息

- [ ] Task 2: 绑定学习通测试账号到xiucat
  - [ ] 2.1 调用 `POST /api/chaoxing/accounts` 绑定学生账号(18436633997/3.1415926Cpy)
  - [ ] 2.2 记录返回的accountId
  - [ ] 2.3 调用 `GET /api/chaoxing/accounts` 验证绑定成功
  - [ ] 2.4 检查 `GET /api/chaoxing/accounts/system-teacher` 是否有系统教师账号配置

- [ ] Task 3: 获取课程和签到活动信息
  - [ ] 3.1 调用 `GET /api/chaoxing/courses?accountId=xxx` 获取课程列表
  - [ ] 3.2 调用 `GET /api/chaoxing/courses/{courseId}/classes/{classId}/actives?accountId=xxx` 获取签到活动
  - [ ] 3.3 调用 `GET /api/chaoxing/actives/{activeId}?accountId=xxx` 获取签到详情
  - [ ] 3.4 调用 `GET /api/chaoxing/actives/{activeId}/members?accountId=xxx` 获取成员状态
  - [ ] 3.5 对比xiucat返回的数据与学习通直接API返回的数据差异

- [ ] Task 4: 学习通侧操作前数据快照
  - [ ] 4.1 通过学习通V2 signIn API获取当前签到记录的完整数据（所有字段）
  - [ ] 4.2 记录关键字段: status, teaUpdateFlag, updatetime, useragent, clientip, deviceCode
  - [ ] 4.3 通过教师账号获取签到管理视图的数据

- [ ] Task 5: 通过xiucat执行补签操作
  - [ ] 5.1 调用 `POST /api/patch-sign/tasks` 创建补签任务（targetStatus=1）
  - [ ] 5.2 轮询 `GET /api/patch-sign/tasks/{id}` 等待任务完成
  - [ ] 5.3 记录任务的完整状态变化和结果
  - [ ] 5.4 如果任务失败，分析错误信息

- [ ] Task 6: 学习通侧操作后数据对比
  - [ ] 6.1 通过学习通V2 signIn API获取操作后的签到记录
  - [ ] 6.2 对比操作前后的所有字段变化
  - [ ] 6.3 重点关注: teaUpdateFlag变化、useragent变化、clientip变化、updatetime变化
  - [ ] 6.4 通过教师账号检查是否有新的签到管理操作记录
  - [ ] 6.5 检查签到记录的tag字段是否包含teaUpdateFlag=1

- [ ] Task 7: 逆向推断漏洞利用方法
  - [ ] 7.1 基于数据对比结果，推断xiucat使用的API（教师API vs 学生API）
  - [ ] 7.2 如果teaUpdateFlag=1，说明使用了教师身份API（updateSignStatus2或updateSignStatusByUidsV2）
  - [ ] 7.3 如果clientip变化，记录xiucat服务器IP
  - [ ] 7.4 如果useragent变化，记录xiucat后端的UA特征
  - [ ] 7.5 分析xiucat的system-teacher机制是否是关键

- [ ] Task 8: 漏洞利用方法复现
  - [ ] 8.1 基于推断的方法，使用测试账号独立复现
  - [ ] 8.2 如果是教师API，验证学生是否也能调用
  - [ ] 8.3 记录完整的漏洞利用链
  - [ ] 8.4 更新安全测试报告

# Task Dependencies
- Task 2 depends on Task 1（需要JWT Token）
- Task 3 depends on Task 2（需要accountId）
- Task 5 depends on Task 3 + Task 4（需要activeId和操作前快照）
- Task 6 depends on Task 5（需要操作后对比）
- Task 7 depends on Task 6（需要对比结果）
- Task 8 depends on Task 7（需要推断的方法）
