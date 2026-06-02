# Tasks

## 阶段1：教师端签到管理API端点发现

- [x] Task 1: 联网搜索学习通教师端签到管理API端点
  - [x] SubTask 1.1: 搜索学习通签到管理API、教师补签接口、修改签到状态接口等相关信息
  - [x] SubTask 1.2: 搜索GitHub上学习通相关项目中签到API的使用示例
  - [x] SubTask 1.3: 整理所有发现的教师端签到管理API端点清单

- [x] Task 2: 使用教师账号探测签到管理API端点
  - [x] SubTask 2.1: 教师账号登录，获取"111"班级（classId=132821141）的签到活动列表
  - [x] SubTask 2.2: 探测教师端签到管理API（/pptSign/updateSignStatus等）
  - [x] SubTask 2.3: 探测教师端补签API
  - [x] SubTask 2.4: 探测签到结果修改API
  - [x] SubTask 2.5: 记录所有教师端可用API端点及其请求参数、响应格式

## 阶段2：学生越权调用教师端签到状态修改接口

- [x] Task 3: 学生账号越权调用教师端签到状态修改接口
  - [x] SubTask 3.1: 学生账号登录，获取"111"班级的签到活动列表
  - [x] SubTask 3.2: 学生尝试调用教师端修改签到状态API（updateSignStatus等）
  - [x] SubTask 3.3: 学生尝试修改自己的签到状态（缺勤→已签到）
  - [x] SubTask 3.4: 学生尝试修改其他学生的签到状态
  - [x] SubTask 3.5: 重点测试"只能改状态"的接口——updateSignStatus

- [x] Task 4: 签到状态修改接口参数篡改测试
  - [x] SubTask 4.1: 在教师端API中修改activeId参数
  - [x] SubTask 4.2: 在教师端API中修改uid/studentId参数
  - [x] SubTask 4.3: 在教师端API中修改status/signStatus参数
  - [x] SubTask 4.4: 在教师端API中添加/删除位置信息参数
  - [x] SubTask 4.5: 使用不同HTTP方法调用教师端API

## 阶段3：签到状态修改漏洞深度利用

- [x] Task 5: 签到状态修改漏洞深度利用与验证
  - [x] SubTask 5.1: 对已确认可修改状态的接口，验证修改是否持久化
  - [x] SubTask 5.2: 验证教师端是否可见学生的状态修改
  - [x] SubTask 5.3: 测试修改不同类型签到的状态
  - [x] SubTask 5.4: 测试修改已结束签到的状态
  - [x] SubTask 5.5: 构建完整的签到状态修改攻击链

## 阶段4：更新安全测试报告

- [x] Task 6: 更新安全测试报告
  - [x] SubTask 6.1: 记录所有新测试步骤、操作方法、系统响应及结果
  - [x] SubTask 6.2: 分析漏洞技术原理
  - [x] SubTask 6.3: 确定漏洞利用条件、影响范围及严重程度
  - [x] SubTask 6.4: 提出修复建议
  - [x] SubTask 6.5: 更新 /workspace/sign_vuln_report.md

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2]
- [Task 3, Task 4] 可并行执行
- [Task 5] depends on [Task 3, Task 4]
- [Task 6] depends on [Task 5]
