# Tasks

- [x] Task 1: PC端接口路径系统性枚举与探测
  - [x] 1.1 枚举 `/widget/sign/pcTeaSignController/` 下所有端点（updateSignStatus, updateSignStatus2, getSignDetail, deleteSign, addSign, preSign, startSign, endSign, signList, stuList, exportSign等）
  - [x] 1.2 枚举 `/widget/sign/pcStuSignController/` 下所有端点（preSign, sign, doSign, qrSign等）
  - [x] 1.3 枚举 `/widget/sign/` 下其他Controller（pcSignController, signController, teaSignController, stuSignController, qrSignController等）
  - [x] 1.4 对每个发现的端点用学生和教师账号分别测试，记录权限差异
  - [x] 1.5 记录所有端点的HTTP方法、参数、返回值、鉴权状态

- [x] Task 2: 已修复漏洞绕过测试
  - [x] 2.1 学生直接调用 `/widget/sign/pcTeaSignController/updateSignStatus2`，验证鉴权是否阻止
  - [x] 2.2 参数篡改测试：篡改denc/duid/uid参数
  - [x] 2.3 HTTP方法变换测试：GET→POST/PUT/DELETE
  - [x] 2.4 路径变体测试：尾部斜杠、分号、.json/.html后缀、URL编码
  - [x] 2.5 请求头篡改测试：修改Referer/Origin/X-Requested-With/Content-Type
  - [x] 2.6 Cookie/Session篡改测试：替换学生Cookie为教师Cookie的部分字段
  - [x] 2.7 时序攻击测试：快速连续请求
  - [x] 2.8 **关键发现**: Content-Type: application/json 绕过权限中间件（返回500而非"您无权限修改"）

- [x] Task 3: 移动端与PC端鉴权差异对比
  - [x] 3.1 对比PC端updateSignStatus2与移动端updateSignStatusByUidsV2的鉴权机制
  - [x] 3.2 测试PC端接口是否接受移动端UA/Cookie
  - [x] 3.3 测试移动端接口是否接受PC端UA/Cookie
  - [x] 3.4 识别两端鉴权逻辑差异导致的绕过可能

- [x] Task 4: 签到系统全面权限控制评估
  - [x] 4.1 IDOR测试：学生修改其他学生签到状态
  - [x] 4.2 垂直越权测试：学生执行教师操作（创建/结束/删除签到活动）
  - [x] 4.3 批量操作测试：uids参数注入多个学生ID
  - [x] 4.4 签到活动信息泄露测试：学生能否获取签到详情、其他学生签到记录

- [x] Task 5: 修复方案完整性与有效性评估
  - [x] 5.1 分析updateSignStatus2当前返回结果，推断修复方式
  - [x] 5.2 检查同类接口（updateSignStatus V1、其他updateSignStatus变体）是否也修复
  - [x] 5.3 评估修复是否覆盖了所有攻击向量
  - [x] 5.4 提出修复改进建议

- [x] Task 6: 安全测试报告更新
  - [x] 6.1 汇总所有发现，按严重程度排序
  - [x] 6.2 为每个漏洞提供：位置、利用方法、影响范围、修复建议
  - [x] 6.3 更新 `/workspace/sign_vuln_report.md`

# Task Dependencies
- Task 2 depends on Task 1（需要先发现端点才能测试绕过）
- Task 3 depends on Task 1（需要先发现PC端端点才能对比）
- Task 4 depends on Task 1（需要先了解所有端点才能做全面评估）
- Task 5 depends on Task 2, Task 3（需要绕过测试结果才能评估修复方案）
- Task 6 depends on all previous tasks
