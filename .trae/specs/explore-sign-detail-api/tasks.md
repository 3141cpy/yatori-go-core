# Tasks

- [x] Task 1: 签到详情/统计接口全面探索
  - [x] 1.1 枚举 `/pptSign/` 下所有签到详情相关端点
  - [x] 1.2 枚举 `/newsign/` 下所有签到详情相关端点
  - [x] 1.3 枚举 `/v2/apis/sign/` 下所有端点
  - [x] 1.4 枚举 `/ppt/activeAPI/` 下所有端点
  - [x] 1.5 枚举 mooc1-api 域名下的等价端点
  - [x] 1.6 对每个端点用学生和教师账号分别测试GET和POST
  - [x] 1.7 特别测试：带不同参数组合（activeId, courseId, classId, uid, cpi等）

- [x] Task 2: 签到统计结果查看功能测试
  - [x] 2.1 用教师账号检查签到活动是否设置了"允许学生查看统计结果"
  - [x] 2.2 尝试通过教师API修改该设置
  - [x] 2.3 用学生账号测试在"允许查看"设置下的签到统计接口
  - [x] 2.4 分析学生端APP的签到详情页面URL和API调用

- [x] Task 3: 签到详情接口数据结构分析
  - [x] 3.1 对所有返回有效数据的接口，完整记录返回的JSON结构
  - [x] 3.2 识别返回数据中的敏感信息（其他学生姓名、uid、签到位置、设备信息）
  - [x] 3.3 识别返回数据中的可操作字段（status, remark, signId, recordId等）
  - [x] 3.4 对比学生和教师看到的数据差异

- [x] Task 4: 围绕签到详情接口的修改漏洞挖掘
  - [x] 4.1 从签到详情接口的URL模式推断修改接口路径
  - [x] 4.2 测试签到详情接口返回的记录ID是否可用于直接修改
  - [x] 4.3 测试签到详情页面中嵌入的修改操作（如updateSignStatus等）
  - [x] 4.4 测试newsign路径下的修改接口（基于详情接口发现的参数）
  - [x] 4.5 测试v2路径下的修改接口

- [x] Task 5: 签到详情接口IDOR测试
  - [x] 5.1 学生访问其他课程/班级的签到详情
  - [x] 5.2 学生通过修改uid参数访问其他学生的签到记录
  - [x] 5.3 学生通过修改activeId参数访问其他活动的签到详情
  - [x] 5.4 学生尝试访问教师端签到管理页面

- [x] Task 6: 签到状态修改漏洞深度挖掘
  - [x] 6.1 基于详情接口发现的参数构造修改请求
  - [x] 6.2 测试签到记录ID直接修改（如果有signId/recordId字段）
  - [x] 6.3 测试不同API路径的修改接口（newsign, pptSign, v2, widget）
  - [x] 6.4 测试参数组合（带/不带denc, duid, cpi等）
  - [x] 6.5 验证修改是否真正生效（查询前后对比）
  - [x] 6.6 发现uids参数绕过、Cookie注入绕过、JSON Content-Type绕过（均不可利用）

- [x] Task 7: 安全测试报告更新
  - [x] 7.1 汇总所有发现
  - [x] 7.2 更新 `/workspace/sign_vuln_report.md`

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 3
- Task 5 depends on Task 1
- Task 6 depends on Task 3, Task 4
- Task 7 depends on all previous tasks
