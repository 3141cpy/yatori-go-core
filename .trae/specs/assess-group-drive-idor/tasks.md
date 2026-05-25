# Tasks

- [x] Task 1: 环境准备与账号登录
  - [x] SubTask 1.1: 使用账号1登录获取Cookie和puid → puid=252798154
  - [x] SubTask 1.2: 使用账号2登录获取Cookie和puid → puid=239448447
  - [x] SubTask 1.3: 通过mycourse/backclazzdata API获取bbsid → 账号1:43个小组, 账号2:54个小组

- [x] Task 2: 跨组文件列表越权测试（groupweb.chaoxing.com - /pc/resource/getResourceList）
  - [x] SubTask 2.1: [基线] 账号1列出自己小组的文件 → result=1, files=0
  - [x] SubTask 2.2: [基线] 账号2列出自己小组的文件 → result=1, files=0
  - [x] SubTask 2.3: [越权] 账号1使用账号2小组的bbsid列出文件 → 被拒绝："请加入小组后再操作"
  - [x] SubTask 2.4: [越权] 账号2使用账号1小组的bbsid列出文件 → 被拒绝："请加入小组后再操作"
  - [x] SubTask 2.5: 无子目录可测试（根目录无文件）

- [x] Task 3: 跨组文件下载越权测试（noteyd.chaoxing.com）
  - [x] SubTask 3.1: 获取上传配置 → 成功（puid+token）
  - [x] SubTask 3.2: 小组云盘无文件，跳过下载越权测试
  - [x] SubTask 3.3: noteyd接口对无效fileId返回"没有对应下载地址"

- [x] Task 4: 跨组文件上传越权测试
  - [x] SubTask 4.1: 账号1在账号2小组创建文件夹 → 被拒绝
  - [x] SubTask 4.2: 账号2在账号1小组创建文件夹 → 被拒绝

- [x] Task 5: 跨组文件删除越权测试
  - [x] SubTask 5.1: 账号1删除账号2小组文件 → 被拒绝
  - [x] SubTask 5.2: 账号1删除账号2小组文件夹 → 被拒绝
  - [x] SubTask 5.3: 账号1重命名账号2小组文件夹 → 被拒绝

- [x] Task 6: 移动端API硬编码密钥安全测试（groupyd.chaoxing.com）
  - [x] SubTask 6.1: 使用硬编码Token和DES密钥构造inf_enc签名 → 签名被服务端接受
  - [x] SubTask 6.2: 使用账号1的puid请求getTopic → 成功(result=1, has_data=True)
  - [x] SubTask 6.3: 使用账号1的Cookie+账号2的puid请求getTopic → 被拒绝(code:433)
  - [x] SubTask 6.4: 使用账号1的Cookie+账号2的puid请求addReply → 被拒绝(code:433)
  - [x] 额外测试: 无Cookie仅硬编码Token请求 → 被拒绝(code:806001)

- [x] Task 7: bbsid可枚举性与权限提升测试
  - [x] SubTask 7.1: bbsid格式分析 → 32位hex(MD5格式)，不可暴力枚举
  - [x] SubTask 7.2: bbsid随机碰撞测试 → 5次随机测试均未命中
  - [x] SubTask 7.3: 权限体系分析 → addData=0, delData=0, addManager=0
  - [x] SubTask 7.4: 权限提升测试(addManager/delMem) → 均被拒绝

- [x] Task 8: 安全评估报告生成
  - [x] SubTask 8.1: 汇总所有测试结果
  - [x] SubTask 8.2: 分析移动端硬编码密钥安全影响
  - [x] SubTask 8.3: 与个人云盘漏洞对比
  - [x] SubTask 8.4: 提出修复建议

# Task Dependencies
- All tasks completed
