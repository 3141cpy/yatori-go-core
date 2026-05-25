# Tasks

- [x] Task 1: 梳理学习通云盘认证体系中的关键凭据类型
  - [x] SubTask 1.1: 整理所有 Cookie 字段（UID、uf、vc/vc2/vc3、xxtenc、fid、cx_p_token、p_auth_token 等）及其作用
  - [x] SubTask 1.2: 整理所有 Token 类型（_token 旧版、_token 新版、cx_p_token、p_auth_token）及其获取方式
  - [x] SubTask 1.3: 明确 puid 与 UID 的等价关系

- [x] Task 2: 分析旧版云盘 API（pan-yz.chaoxing.com）的 _token + puid 机制
  - [x] SubTask 2.1: 研究 /api/token/uservalid 接口的请求与响应格式
  - [x] SubTask 2.2: 分析 _token 在旧版 API 中的使用方式（查询参数配对 puid + _token）
  - [x] SubTask 2.3: 确认 _token 的性质（有状态 opaque token，服务端生成与存储）

- [x] Task 3: 分析新版云盘 API（noteyd.chaoxing.com）的 _token + puid 机制
  - [x] SubTask 3.1: 研究 /pc/files/getUploadConfig 接口的请求与响应格式
  - [x] SubTask 3.2: 分析新版 API 中 _token 和 puid 在文件上传中的使用方式
  - [x] SubTask 3.3: 对比新旧 API 认证方式的差异

- [x] Task 4: 研究登录加密算法
  - [x] SubTask 4.1: 分析 AES-CBC 加密算法的实现细节（密钥、IV、填充方式）
  - [x] SubTask 4.2: 验证加密密钥 `u2oh6Vu^HWe4_AES` 的来源（前端 JS 硬编码）
  - [x] SubTask 4.3: 编写加密算法的伪代码/代码示例

- [x] Task 5: 分析 p_auth_token（JWT）结构
  - [x] SubTask 5.1: 解码 JWT 的 Header 和 Payload 结构
  - [x] SubTask 5.2: 确认 Payload 中的 uid、loginTime、exp 字段含义
  - [x] SubTask 5.3: 分析 JWT 的签名算法和有效期

- [x] Task 6: 绘制完整认证流程图
  - [x] SubTask 6.1: 从登录到获取 Cookie 的流程
  - [x] SubTask 6.2: 从 Cookie 到获取云盘 _token 的流程
  - [x] SubTask 6.3: 使用 _token + puid 访问云盘资源的流程

- [x] Task 7: 总结 token 与 puid 的核心关系
  - [x] SubTask 7.1: 明确 puid = UID 的等价关系
  - [x] SubTask 7.2: 说明 _token 是 puid 的服务端凭证
  - [x] SubTask 7.3: 说明新旧 API 的 _token 独立性

- [x] Task 8: _token 可预测性分析（关联 security_report.md 攻击路径2）
  - [x] SubTask 8.1: 分析 _token 的格式特征（32位hex，疑似MD5）
  - [x] SubTask 8.2: 推测 _token 的可能生成算法（MD5(puid+salt) / MD5(puid+session+salt) / 随机生成）
  - [x] SubTask 8.3: 评估 _token 的可预测性等级 — 结论：不可预测
  - [x] SubTask 8.4: 分析绕过方案（方案1已验证可行，方案2不可行，方案3待验证）

- [x] Task 9: 验证 security_report.md 中未完成的绕过方案
  - [x] SubTask 9.1: 编写 token_predictability_analysis.py — 200+种哈希逆向尝试均未匹配
  - [x] SubTask 9.2: 编写 token_bypass_verify.py — 包含稳定性/长期有效性/Session绑定三项测试
  - [x] SubTask 9.3: 综合评估攻击路径2的可行性 — 结论：Token不可预测，攻击路径2不可行
  - [x] SubTask 9.4: 更新 security_report.md — 已补充5.3.1和5.3.2章节

# Task Dependencies
- Task 8 depends on Task 1, Task 2
- Task 9 depends on Task 8
