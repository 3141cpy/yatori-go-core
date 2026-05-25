# Tasks

- [ ] Task 1: 环境准备与账号登录验证
  - [ ] SubTask 1.1: 使用账号1（19312994130）调用登录API获取Cookie和puid
  - [ ] SubTask 1.2: 使用账号2（15034188203）调用登录API获取Cookie和puid
  - [ ] SubTask 1.3: 记录两个账号的puid、Cookie关键字段（UID、uf等）

- [ ] Task 2: 云盘Token获取与绑定关系测试
  - [ ] SubTask 2.1: 使用账号1的Cookie请求`/api/token/uservalid`获取Token1
  - [ ] SubTask 2.2: 使用账号2的Cookie请求`/api/token/uservalid`获取Token2
  - [ ] SubTask 2.3: 分析Token1和Token2的结构，判断是否包含puid绑定信息

- [ ] Task 3: 云盘用户信息接口越权测试（IDOR - /api/info）
  - [ ] SubTask 3.1: 使用账号1的Cookie+Token1+账号1的puid请求`/api/info`，记录正常响应（基线）
  - [ ] SubTask 3.2: 使用账号1的Cookie+Token1+账号2的puid请求`/api/info`，验证是否返回账号2的信息
  - [ ] SubTask 3.3: 使用账号1的Cookie+Token2+账号2的puid请求`/api/info`，验证跨Token组合是否被允许

- [ ] Task 4: 云盘磁盘容量接口越权测试（IDOR - /api/getUserDiskCapacity）
  - [ ] SubTask 4.1: 使用账号1的Cookie+Token1+账号1的puid请求`/api/getUserDiskCapacity`，记录正常响应（基线）
  - [ ] SubTask 4.2: 使用账号1的Cookie+Token1+账号2的puid请求`/api/getUserDiskCapacity`，验证是否返回账号2的容量信息

- [ ] Task 5: 云盘文件列表越权测试（核心风险 - /api/getMyDirAndFiles）
  - [ ] SubTask 5.1: 使用账号1的Cookie+Token1+账号1的puid请求`/api/getMyDirAndFiles`，记录账号1的文件列表（基线）
  - [ ] SubTask 5.2: 使用账号2的Cookie+Token2+账号2的puid请求`/api/getMyDirAndFiles`，记录账号2的文件列表（基线）
  - [ ] SubTask 5.3: 使用账号1的Cookie+Token1+账号2的puid请求`/api/getMyDirAndFiles`，验证是否能列出账号2的文件
  - [ ] SubTask 5.4: 如5.3成功，尝试使用账号2的fldid参数进一步浏览账号2的子目录
  - [ ] SubTask 5.5: 使用账号1的Cookie+Token2+账号2的puid请求，验证跨Token组合的影响

- [ ] Task 6: 云盘文件删除接口越权测试（/api/delete）
  - [ ] SubTask 6.1: 使用账号1的Cookie+Token1+账号2的puid构造删除请求，分析响应判断是否被允许（不实际执行删除）
  - [ ] SubTask 6.2: 对比使用账号1的puid和账号2的puid时服务端的响应差异

- [ ] Task 7: 云盘文件上传接口越权测试（/opt/createfilenew 和 /upload）
  - [ ] SubTask 7.1: 使用账号1的Cookie+Token1+账号2的puid构造上传请求，分析响应判断是否被允许（不实际上传）
  - [ ] SubTask 7.2: 对比使用账号1的puid和账号2的puid时服务端的响应差异

- [ ] Task 8: 安全评估报告生成
  - [ ] SubTask 8.1: 汇总所有测试结果，标注确认存在越权风险的端点
  - [ ] SubTask 8.2: 分析越权漏洞的技术原因（服务端未校验puid与认证身份的绑定关系）
  - [ ] SubTask 8.3: 评估影响范围（所有使用puid作为直接对象引用的云盘API端点）
  - [ ] SubTask 8.4: 提出修复建议（服务端应基于认证Cookie/Token解析用户身份，而非信任客户端传递的puid参数）

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2]
- [Task 5] depends on [Task 2]
- [Task 6] depends on [Task 2]
- [Task 7] depends on [Task 2]
- [Task 8] depends on [Task 3, Task 4, Task 5, Task 6, Task 7]
- [Task 3, Task 4, Task 5, Task 6, Task 7] 可并行执行
