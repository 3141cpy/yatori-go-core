# Tasks

- [x] Task 1: 越权攻击面分析与测试脚本编写
  - [x] SubTask 1.1: 基于已泄露密钥，梳理所有API端点的越权攻击面
  - [x] SubTask 1.2: 编写Python越权测试脚本，覆盖课程、作业、考试、人脸验证、视频学时、用户信息等模块
  - [x] SubTask 1.3: 在脚本中集成泄露密钥的签名计算（K3/K4/K5/K6/K7/K9）

- [x] Task 2: 课程信息越权测试
  - [x] SubTask 2.1: 使用账号1的Cookie访问账号2的课程列表（/mycourse/backclazzdata）
  - [x] SubTask 2.2: 使用泄露Token(K6)+DES密钥(K7)构造移动端请求访问他人课程
  - [x] SubTask 2.3: 修改cpi参数尝试访问他人课程详情 — **5/5课程越权成功**

- [x] Task 3: 作业系统越权测试
  - [x] SubTask 3.1: 修改workId/classId参数尝试查看他人作业列表（/work/task-list）
  - [x] SubTask 3.2: 使用泄露enc签名尝试访问他人作业详情
  - [x] SubTask 3.3: 尝试修改userId参数代替他人提交作业 — **被拒绝，防护有效**

- [x] Task 4: 考试系统越权测试
  - [x] SubTask 4.1: 修改examId/classId参数尝试查看他人考试列表
  - [x] SubTask 4.2: 使用泄露的考试签名算法(K9)构造请求尝试访问他人考试
  - [x] SubTask 4.3: 尝试修改testPaperId/testUserRelationId参数代替他人答题 — **被拒绝，防护有效**

- [x] Task 5: 人脸验证越权测试
  - [x] SubTask 5.1: 使用泄露的人脸盐值(K4)为目标用户构造enc签名
  - [x] SubTask 5.2: 修改cpi/objectId参数查看他人人脸验证状态
  - [x] SubTask 5.3: 尝试代替他人通过人脸验证 — **enc与Cookie绑定，跨用户被拒绝**

- [x] Task 6: 视频学时越权测试
  - [x] SubTask 6.1: 使用泄露的视频盐值(K3)为目标用户构造enc签名
  - [x] SubTask 6.2: 修改userid参数尝试为他人提交视频学时 — **被拒绝(405)**
  - [x] SubTask 6.3: 验证服务端是否校验Cookie中的uid与请求参数中的userid一致性 — **签名校验有效**

- [x] Task 7: 用户信息越权测试
  - [x] SubTask 7.1: 修改puid/uid参数尝试查看他人用户资料 — **被拒绝**
  - [x] SubTask 7.2: 使用泄露Token(K6)构造移动端请求访问他人信息 — **被拒绝**
  - [x] SubTask 7.3: 测试passport2-api.chaoxing.com的用户信息接口 — **"非法请求"**

- [x] Task 8: JWT令牌伪造越权测试
  - [x] SubTask 8.1: 从源码硬编码Cookie中提取JWT令牌，解码分析payload结构
  - [x] SubTask 8.2: 使用hashcat尝试暴力破解HS256签名密钥 — **19个候选密钥均不匹配**
  - [x] SubTask 8.3: 如果密钥被破解，伪造包含目标用户uid的JWT令牌并测试 — **密钥未破解**

- [x] Task 9: 越权漏洞安全评估报告生成
  - [x] SubTask 9.1: 汇总所有越权测试结果（35项测试，14项隐患）
  - [x] SubTask 9.2: 分析密钥泄露对越权漏洞的实际影响
  - [x] SubTask 9.3: 构建完整的越权攻击链（阅读任务+课程cpi+人脸验证）
  - [x] SubTask 9.4: 提出分层修复建议

# Task Dependencies
- [Task 2-8] depends on [Task 1]
- [Task 2, 3, 4, 5, 6, 7, 8] 可并行执行
- [Task 9] depends on [Task 2-8]
