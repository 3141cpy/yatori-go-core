# Tasks

- [x] Task 1: 教师账号调用updateSignStatusByUidsV2 API验证
  - [x] SubTask 1.1: 教师账号登录，获取Cookie
  - [x] SubTask 1.2: 使用multipart/form-data格式调用updateSignStatusByUidsV2（activeId=5000163767353, uids=431407443, status=2）
  - [x] SubTask 1.3: 使用application/x-www-form-urlencoded格式调用同一API
  - [x] SubTask 1.4: 测试不同status值（0/1/2/3/4/5/6）
  - [x] SubTask 1.5: 测试不同DB_STRATEGY参数（PRIMARY_KEY/NONE等）
  - [x] SubTask 1.6: 测试批量uids参数（多个uid逗号分隔）

- [x] Task 2: 学生账号越权调用updateSignStatusByUidsV2 API
  - [x] SubTask 2.1: 学生账号登录，获取Cookie
  - [x] SubTask 2.2: 学生使用multipart/form-data格式调用updateSignStatusByUidsV2
  - [x] SubTask 2.3: 学生使用application/x-www-form-urlencoded格式调用
  - [x] SubTask 2.4: 学生尝试修改自己的签到状态（uids=自己的puid）
  - [x] SubTask 2.5: 学生尝试修改其他学生的签到状态
  - [x] SubTask 2.6: 学生使用教师Cookie调用此API

- [x] Task 3: updateSignStatusByUidsV2 API参数篡改测试
  - [x] SubTask 3.1: 修改activeId参数指向其他签到活动
  - [x] SubTask 3.2: 修改uids参数（添加不存在uid、其他课程uid等）
  - [x] SubTask 3.3: 添加额外参数（latitude/longitude/enc/signCode等）
  - [x] SubTask 3.4: 删除DB_STRATEGY参数测试
  - [x] SubTask 3.5: 使用GET方法调用

- [x] Task 4: 签到状态修改持久化验证
  - [x] SubTask 4.1: 调用updateSignStatusByUidsV2后，使用V2 signIn API查询签到状态
  - [x] SubTask 4.2: 使用教师账号查看签到结果页面
  - [x] SubTask 4.3: 验证签到状态是否确实改变

- [x] Task 5: 更新安全测试报告
  - [x] SubTask 5.1: 记录所有测试步骤和结果
  - [x] SubTask 5.2: 分析updateSignStatusByUidsV2与updateSignStatus的差异
  - [x] SubTask 5.3: 确定漏洞利用条件、影响范围及严重程度
  - [x] SubTask 5.4: 更新 /workspace/sign_vuln_report.md

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 2, Task 3] 可并行执行
- [Task 4] depends on [Task 1, Task 2, Task 3]
- [Task 5] depends on [Task 4]
