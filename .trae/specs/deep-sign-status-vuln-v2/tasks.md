# Tasks

- [x] Task 1: 多域名签到接口全面枚举
  - [x] 1.1 枚举 `mooc1-api.chaoxing.com/qr/` 下所有端点
  - [x] 1.2 枚举 `mooc1-api.chaoxing.com/mooc-ans/` 下签到相关端点
  - [x] 1.3 枚举 `mooc1.chaoxing.com/mooc-ans/` 下签到相关端点
  - [x] 1.4 枚举 `mooc2-ans.chaoxing.com` 下签到相关端点
  - [x] 1.5 枚举 `mooc1-api.chaoxing.com/mooc-ans/pptSign/` 和 `/newsign/` 路径
  - [x] 1.6 对每个发现的端点用学生和教师账号分别测试

- [x] Task 2: /qr/updateqrstatus 专项安全测试
  - [x] 2.1 学生直接调用测试权限 — 学生POST返回"图片格式错误"而非"无权限"
  - [x] 2.2 测试不同参数组合
  - [x] 2.3 分析qrcEnc参数 — 教师preSign页面泄露viceScreenEwmEnc值
  - [x] 2.4 测试空qrcEnc、伪造qrcEnc
  - [x] 2.5 验证签到状态 — 已结束活动无法验证，需要活跃活动

- [x] Task 3: inf_enc签名算法逆向与伪造
  - [x] 3.1 分析Go源码中的InfEncSign函数 — DESKey=Z(AfY@XS, MD5签名
  - [x] 3.2 用Python复现签名算法
  - [x] 3.3 测试带inf_enc签名的请求 — 无法绕过权限
  - [x] 3.4 对比有无inf_enc签名的API响应 — 完全一致

- [x] Task 4: PC端JSON绕过深度利用
  - [x] 4.1 尝试不同JSON参数格式 — 全部404
  - [x] 4.2 在mooc1-api域名下测试 — 端点不存在
  - [x] 4.3 测试multipart/form-data — 404
  - [x] 4.4 尝试将参数同时放在URL和JSON body中 — 404

- [x] Task 5: mooc-ans路径下的签到状态修改接口探索
  - [x] 5.1 测试 `/mooc-ans/pptSign/updateSignStatusByUidsV2` — 404
  - [x] 5.2 测试 `/mooc-ans/newsign/updateSignStatus` — 404
  - [x] 5.3 测试 `/mooc-ans/sign/` 路径 — 404
  - [x] 5.4 测试 `/mooc-ans/qr/` 路径 — 有响应（参数不完整/无效参数）

- [x] Task 6: 签到状态修改漏洞全面验证
  - [x] 6.1 对所有发现的可能路径进行实际修改测试
  - [x] 6.2 修改前后通过V2 API查询验证
  - [x] 6.3 覆盖不同签到类型
  - [x] 6.4 结论：需要活跃签到活动才能验证enc值利用链

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 独立
- Task 5 depends on Task 1
- Task 6 depends on all previous tasks
