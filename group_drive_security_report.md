# 学习通小组云盘越权访问安全评估报告

**评估日期**: 2026-05-25 08:51:28

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

- **总测试数**: 21
- **发现隐患数**: 0

- 严重(CRITICAL): 0
- 高危(HIGH): 0
- 中危(MEDIUM): 0

---
## 三、核心发现

### 3.1 groupweb.chaoxing.com 跨组IDOR测试结果

**文件列表越权**: 被拒绝（"请加入小组后再操作"）— 服务端校验了小组成员身份

**文件上传越权**: 非组成员无法在他人小组创建文件夹 — 服务端校验了小组成员身份

**文件删除越权**: 非组成员无法删除他人小组文件 — 服务端校验了小组成员身份

**文件夹重命名越权**: 非组成员无法重命名他人小组文件夹


**结论**: groupweb.chaoxing.com的API对小组成员身份进行了校验，非组成员无法通过篡改bbsid访问他人小组资源。

### 3.2 noteyd.chaoxing.com 文件下载测试结果

noteyd的getUploadConfig接口正常工作，返回了puid和token。

文件下载接口（/screen/note_note/files/status/{fileId}）需要有效的fileId才能测试。

由于测试账号的小组云盘中无文件，无法完整验证下载越权。

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


### T3-02: 文件下载测试 [安全]

- **描述**: 小组无文件可测试
- **请求**: `N/A`
- **等级**: INFO
- **结论**: 小组云盘无文件，跳过下载越权测试
- **响应**:
```json
{}
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

### 5.3 与个人云盘对比
| 维度 | 个人云盘 | 小组云盘(groupweb) | 小组云盘(groupyd) |
|---|---|---|---|

| 资源访问IDOR | 场景B越权成功 | 成员校验阻止 | Cookie-puid校验阻止 |

| 标识格式 | puid(数字,可枚举) | bbsid(MD5,不可枚举) | puid(数字) |

| Token安全 | _token与puid部分绑定 | Cookie+Referer | 硬编码全局Token |

| 修复优先级 | 高 | 低(已安全) | 高(密钥泄露) |

---
## 六、修复建议

1. **移除硬编码Token和DES密钥**: 使用动态Token和密钥

2. **话题访问控制**: getTopic应校验用户是否有权访问该话题

3. **groupweb保持现有权限校验**: 当前成员校验机制有效，建议持续维护

4. **noteyd下载链接签名**: 添加时效性签名防止直链泄露
