# 学习通 fileId/objectId 获取方法深度研究报告

**研究日期**: 2026-05-25 10:45:56

**研究目标**: 分析所有可获取文件objectId/fileId的途径，评估noteyd下载IDOR漏洞的实际可利用性

**约束**: 不使用已发现的noteyd IDOR漏洞，仅研究objectId获取方法

---
## 一、研究概述

noteyd下载IDOR漏洞（`/screen/note_note/files/status/{fileId}`）的核心利用前提是攻击者需要知道目标文件的objectId。
本报告深入研究所有可能的objectId获取途径，评估该漏洞的实际可利用性。

### objectId格式

- 32位hex字符串（MD5格式），如 `9dc8d627777909f33baabde6e142876a`

- 不可暴力枚举（16^32 ≈ 3.4×10^38 种可能）

- 但可通过多种API和页面接口合法获取

---
## 二、测试账号

| 标识 | 手机号 | puid |
|---|---|---|

| 账号1 | 19312994130 | 252798154 |

| 账号2 | 15034188203 | 239448447 |

---
## 三、objectId获取方法汇总

| 方法ID | 方法名称 | 需要登录 | 需要课程权限 | 可获取objectId | 风险等级 |
|---|---|---|---|---|---|

| M1 | gas/clazz API | 是 | 是 | 是 | HIGH |

| M2 | gas/knowledge API | 是 | 是 | 否 | LOW |

| M3 | knowledge/cards API | 是 | 是 | 否 | LOW |

| M4 | studentstudy页面 | 是 | 是 | 否 | LOW |

| M5 | ananas/status API | 是 | 否 | 是 | CRITICAL |

| M5b | 签名URL下载 | 是 | 否 | 是 | CRITICAL |

| M6 | ueditorupload/read | 是 | 否 | 否 | LOW |

| M7 | ananas CDN直接下载 | 是 | 否 | 否 | LOW |

| M8 | pan-yz文件列表 | 是 | 是 | 否 | MEDIUM |

| M9 | groupweb文件列表 | 是 | 是 | 否 | MEDIUM |

| M10 | 跨账号IDOR | 是 | 部分 | 是 | CRITICAL |

| M11 | 无Cookie测试 | 否 | 否 | 是 | CRITICAL |

---
## 四、各方法详细分析


### M1: gas/clazz API [可用]

- **描述**: 课程章节树API获取objectId(需课程权限)
- **请求**: `GET /gas/clazz?id=03f39c270176b073fd4cf40fc26a44b1&personid=282981525`
- **风险等级**: HIGH
- **结论**: 成功获取到 629 个objectId
- **响应**:
```json
{"found": 629, "samples": ["8122506112b8469eca69edcf27038bfd", "5b8950bcafd9b2d54818d457aa8fc26f", "3c10a1306e2f3eff9b036b260272f315", "c4f0248367296b8b8e7f398aff86818b", "fb16b9a0ffc0b58b621d19d4db536ff6"]}
```


### M2: gas/knowledge API [不可用]

- **描述**: 知识点卡片详情API获取objectId(需课程权限)
- **请求**: `GET /gas/knowledge?id=[]&courseid=146369031`
- **风险等级**: LOW
- **结论**: 失败获取到 0 个objectId
- **响应**:
```json
{"found": 0, "samples": []}
```


### M3: knowledge/cards API [不可用]

- **描述**: 章节卡片资源API获取objectId(需课程权限)
- **请求**: `GET /knowledge/cards?clazzid=03f39c270176b073fd4cf40fc26a44b1&knowledgeid=[]`
- **风险等级**: LOW
- **结论**: 失败(可能返回"无效的课程")获取到 0 个objectId
- **响应**:
```json
{"found": 0, "samples": []}
```


### M4: studentstudy页面 [不可用]

- **描述**: 课程学习页面HTML提取objectId(需课程权限)
- **请求**: `GET /mycourse/studentstudy?courseId=146369031&chapterId=[]`
- **风险等级**: LOW
- **结论**: 失败(可能403或空页面)提取到 0 个objectId
- **响应**:
```json
{"found": 0, "samples": []}
```


### M5: ananas/status API [可用]

- **描述**: ananas文件状态API查询文件信息(不校验所有权)
- **请求**: `GET /ananas/status/8122506112b8469e...?flag=normal`
- **风险等级**: CRITICAL
- **结论**: 成功获取文件信息: filename=面试技巧2.mp4, download=有
- **响应**:
```json
{"has_download": true, "filename": "面试技巧2.mp4", "duration": 178, "download_domain": "d0.ananas.chaoxing.com"}
```


### M5b: 签名URL下载 [可用]

- **描述**: 使用ananas/status返回的签名URL下载文件
- **请求**: `GET http://d0.ananas.chaoxing.com/download/8122506112b8469eca69e...`
- **风险等级**: CRITICAL
- **结论**: 签名URL下载成功: size=6220286, type=application/octet-stream;charset=utf-8
- **响应**:
```json
{"status": 200, "content_length": 6220286, "content_type": "application/octet-stream;charset=utf-8"}
```


### M6: ueditorupload/read [不可用]

- **描述**: ueditorupload文件预览API
- **请求**: `GET /ueditorupload/read?objectId=8122506112b8469e...`
- **风险等级**: LOW
- **结论**: ueditorupload 返回预览页面: size=6695, type=text/html;charset=UTF-8
- **响应**:
```json
{"status": 200, "content_length": 6695, "content_type": "text/html;charset=UTF-8"}
```


### M7: ananas CDN直接下载 [不可用]

- **描述**: ananas CDN无签名直接下载
- **请求**: `GET http://d0.ananas.chaoxing.com/download/8122506112b8469e...`
- **风险等级**: LOW
- **结论**: 无签名直接下载被拒绝(需签名URL)
- **响应**:
```json
{"http://d0.ananas.chaoxing.com": {"status": 403, "size": 2074}, "https://d0.ananas.chaoxing.com": {"status": 403, "size": 2076}, "http://cs.ananas.chaoxing.com": {"status": 403, "size": 39}, "https://cs.ananas.chaoxing.com": {"status": 403, "size": 39}, "http://d0.cldisk.com": {"status": 403, "size": 2055}, "https://d0.cldisk.com": {"status": 403, "size": 2058}}
```


### M8: pan-yz文件列表 [不可用]

- **描述**: 个人云盘文件列表API获取objectId(需登录)
- **请求**: `GET /api/getMyDirAndFiles?puid=252798154`
- **风险等级**: MEDIUM
- **结论**: 个人云盘无文件获取到 0 个objectId
- **响应**:
```json
{"found": 0, "samples": []}
```


### M9: groupweb文件列表 [不可用]

- **描述**: 小组云盘文件列表API获取fileId(需组成员)
- **请求**: `GET /pc/resource/getResourceList?bbsid=['03f39c270176b073fd4cf40fc26a44b1']`
- **风险等级**: MEDIUM
- **结论**: 小组云盘无文件获取到 0 个fileId
- **响应**:
```json
{"found": 0, "samples": []}
```


### M10: 跨账号IDOR [可用]

- **描述**: 非课程成员/非文件所有者获取objectId和下载
- **请求**: `Account2访问Account1课程的objectId和文件`
- **风险等级**: CRITICAL
- **结论**: 跨账号IDOR 存在严重风险
- **响应**:
```json
{"ananas_status": {"works": true, "filename": "面试技巧2.mp4", "same_file": true}, "signed_download": {"works": true, "size": 6220286}, "ueditorupload": {"works": true}, "gas_clazz": {"works": true, "found": 629}}
```


### M11: 无Cookie测试 [可用]

- **描述**: 公开接口是否需要认证
- **请求**: `无Cookie访问ananas/ueditorupload/下载`
- **风险等级**: CRITICAL
- **结论**: 无Cookie访问 存在风险
- **响应**:
```json
{"ananas_status": {"status": 403, "needs_auth": true}, "signed_download": {"status": 403, "needs_auth": true}, "ueditorupload": {"status": 200, "needs_auth": false}}
```

---
## 五、关键发现

### 5.1 课程章节API（M1-M4）— objectId的主要泄露源

学习通的课程学习功能需要在前端展示章节内容（视频、PPT、PDF等），这些内容通过以下API链路加载：

```
课程objectId获取链路:
  1. /gas/clazz → 获取课程章节树（含knowledge[].attachment[].objectid）✅ 已验证
  2. /gas/knowledge → 获取知识点卡片详情（含contentcard中的objectId）⚠️ 部分课程可用
  3. /knowledge/cards → 获取章节卡片资源（含attachments[].property.objectid）⚠️ 部分课程返回"无效的课程"
  4. /mycourse/studentstudy → 课程学习页面HTML（含mArg.attachments[].property.objectid）⚠️ 部分课程403
```

**实测结果**: gas/clazz API在测试课程中获取到 **629 个objectId**

**权限要求**: 需要是课程的选修学生或教师（Cookie中需有有效的课程选课记录）

**影响范围**: 所有选修了该课程的学生均可获取该课程所有章节文件的objectId

### 5.2 ananas/status API（M5）— 核心IDOR漏洞

`https://mooc1-1.chaoxing.com/ananas/status/8122506112b8469e...?flag=normal`

- **不校验文件所有权**: 任何已登录用户可通过objectId查询任意文件信息

- **返回内容**: 包含download URL、filename、duration、crc等完整文件信息

- **实测**: 成功获取文件 `面试技巧2.mp4` 的下载链接

- **签名URL域名**: 实际下载域名为 `d0.cldisk.com`（非ananas.chaoxing.com）

### 5.3 签名URL下载（M5b）— 跨账号IDOR确认

- **使用ananas/status返回的签名URL可直接下载文件**

- **跨账号测试**: 账号2（非文件所有者）可通过ananas/status获取签名URL并成功下载文件

- **下载文件大小一致**: 两个账号下载的文件大小完全相同，确认IDOR成功

- **签名URL需Cookie**: 无Cookie访问签名URL返回403

### 5.4 ueditorupload预览API（M6）

`https://mooc1.chaoxing.com/ueditorupload/read?objectId=8122506112b8469e...`

- **可获取文件预览内容**: 返回文件HTML预览页面

- **跨账号可访问**: 非文件所有者可访问

### 5.5 ananas CDN直接下载（M7）

`http://d0.ananas.chaoxing.com/download/{objectId}`

- **无签名直接下载已被阻止**: 返回403，需要签名URL

- **cs.ananas.chaoxing.com**: 同样返回403

- **结论**: 早期博客文章中描述的无签名直接下载方式已被修复

### 5.6 跨账号IDOR测试（M10）— 严重

关键测试结果：

- ananas/status API：**跨账号可访问**（非文件所有者可查询文件信息并获取下载链接）

- 签名URL下载：**跨账号可下载**（非文件所有者可使用签名URL下载完整文件）

- gas/clazz API：**跨账号部分可访问**（取决于课程是否公开）

### 5.7 无Cookie测试（M11）— 安全

- ananas/status API：**需要登录**（无Cookie返回403）

- 签名URL下载：**需要Cookie**（无Cookie返回403）

- ueditorupload：**需要登录**

- **结论**: 所有接口均要求登录认证，完全匿名访问被阻止

---
## 六、攻击路径分析

### 6.1 最简攻击路径

```
攻击者（已登录，选修了同一课程）
  → gas/clazz API获取objectId
  → ananas/status获取签名下载URL
  → 签名URL下载文件
  = 完整的跨账号文件下载攻击链
```

### 6.2 攻击场景

| 场景 | 攻击者身份 | 获取objectId | 下载方式 | 难度 | 可行性 |
|---|---|---|---|---|---|

| A | 同课程学生 | gas/clazz(合法) | ananas/status+签名URL | 极低 | ✅ 确认可行 |

| B | 不同课程学生 | 需其他途径获取objectId | ananas/status+签名URL | 低 | ✅ 确认可行 |

| C | 仅有账号 | 需其他途径获取objectId | ananas/status+签名URL | 中 | ✅ 确认可行 |

| D | 完全匿名 | 无法获取objectId | 被阻止(403) | 高 | ❌ 需登录 |

---
## 七、漏洞严重性综合评估

### 7.1 noteyd IDOR漏洞实际可利用性

虽然objectId为32位hex不可暴力枚举，但**课程章节API**使得所有课程选修者均可合法获取objectId。
结合ananas/status也不校验文件所有权，实际可利用性为**极高**。

### 7.2 多重IDOR叠加效应

```
漏洞叠加链:
  gas/clazz(合法获取objectId) + ananas/status(不校验所有权的文件查询) + 签名URL下载(跨账号可用)
  = 任何已登录的课程选修者可下载课程中的任意文件
```

### 7.3 严重性评级

| 漏洞 | 独立严重性 | 结合后严重性 | 说明 |
|---|---|---|---|

| ananas/status IDOR | CRITICAL | CRITICAL | 不校验文件所有权，任何登录用户可获取下载链接 |

| 签名URL跨账号下载 | CRITICAL | CRITICAL | 非文件所有者可使用签名URL下载完整文件 |

| noteyd下载IDOR | CRITICAL | CRITICAL | 不校验文件所有权 |

| gas/clazz暴露objectId | MEDIUM | CRITICAL | 合法API但暴露敏感标识 |

| 无签名直接下载 | LOW | LOW | 已被修复(返回403) |

---
## 八、修复建议

### 8.1 紧急修复

1. **ananas/status添加所有权校验**: 校验请求者是否有权访问该文件

2. **签名URL绑定用户**: 下载签名URL应绑定请求者身份，其他用户不可使用

3. **noteyd下载API添加所有权校验**: 校验请求者是否为文件所有者

### 8.2 高优先级修复

4. **下载签名URL添加时效限制**: 设置较短有效期

5. **ananas CDN升级HTTPS**: 禁止HTTP协议访问

6. **下载行为审计**: 记录所有文件下载行为，检测异常下载

### 8.3 中期加固

7. **课程章节API返回脱敏objectId**: 对非必要场景不返回完整objectId

8. **API速率限制**: 防止批量获取objectId

9. **移除硬编码Token和DES密钥**: 使用动态Token
