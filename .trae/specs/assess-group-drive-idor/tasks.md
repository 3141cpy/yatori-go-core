# Tasks

- [x] Task 1: 环境准备与账号登录
  - [x] SubTask 1.1: 使用账号1登录获取Cookie和puid → puid=252798154
  - [x] SubTask 1.2: 使用账号2登录获取Cookie和puid → puid=239448447
  - [x] SubTask 1.3: 使用两个账号分别获取/创建小组，记录bbsid → bbsid获取失败(groupweb需代理环境)

- [x] Task 2: 跨组文件列表越权测试（groupweb.chaoxing.com - /pc/resource/getResourceList）
  - [x] SubTask 2.1-2.5: 因groupweb.chaoxing.com需要代理环境(OnlyProxy:true)，从当前环境无法访问，测试跳过

- [x] Task 3: 跨组文件下载越权测试（noteyd.chaoxing.com）
  - [x] SubTask 3.1-3.3: 同样因代理限制，测试跳过

- [x] Task 4: 跨组文件上传越权测试
  - [x] SubTask 4.1-4.3: 同样因代理限制，测试跳过

- [x] Task 5: 跨组文件删除越权测试
  - [x] SubTask 5.1-5.3: 同样因代理限制，测试跳过

- [x] Task 6: 移动端API硬编码密钥安全测试（groupyd.chaoxing.com）
  - [x] SubTask 6.1: 使用硬编码Token和DES密钥构造inf_enc签名 → 签名被服务端接受
  - [x] SubTask 6.2: 使用账号1的puid请求getTopic → 成功获取话题数据(result=1)
  - [x] SubTask 6.3: 使用账号1的Cookie+账号2的puid请求getTopic → 被拒绝(code:433,Cookie-puid不匹配)
  - [x] SubTask 6.4: 使用账号1的Cookie+账号2的puid请求addReply → 被拒绝(code:433)
  - [x] 额外测试: 无Cookie仅硬编码Token请求 → 被拒绝(code:806001)
  - [x] 额外测试: 话题访问控制 → 任何已登录用户可遍历topicId访问任意话题(信息泄露)

- [x] Task 7: bbsid可枚举性与权限提升测试
  - [x] SubTask 7.1-7.3: 因bbsid未获取，测试跳过

- [x] Task 8: 安全评估报告生成
  - [x] SubTask 8.1: 汇总测试结果
  - [x] SubTask 8.2: 分析移动端硬编码密钥安全影响
  - [x] SubTask 8.3: 与个人云盘漏洞对比
  - [x] SubTask 8.4: 提出修复建议

# Task Dependencies
- [Task 2-5, 7] 因groupweb代理限制跳过
- [Task 6] 已完成，移动端API Cookie-puid校验生效，但硬编码密钥泄露
- [Task 8] 已完成

# 未完成项说明
groupweb.chaoxing.com / noteyd.chaoxing.com 的越权测试因以下原因未能执行：
1. 小组云盘标记为OnlyProxy:true，需要代理环境才能访问
2. 测试账号可能未创建任何小组
3. bbsid无法获取，导致所有基于bbsid的测试无法进行
建议：在配置代理的国内服务器环境中重新执行Task 2-5和7的测试
