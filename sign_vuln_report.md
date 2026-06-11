# 超星学习通签到系统安全审计报告

**审计日期**: 2026-06-03 ~ 2026-06-11
**版本**: v10.0（ChaoxingSignFaker开源仓库启发版）
**审计范围**: 学习通签到系统全面安全评估，基于域名映射表探索100+域名 + ChaoxingSignFaker开源仓库逆向分析
**测试账号**: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
**测试课程**: courseId=257485372, classId=132821141 / courseId=262934472, classId=145110605

---

## 核心结论

基于开源仓库 `aquamarine5/ChaoxingSignFaker`（随地大小签）的逆向分析，发现了多个之前未知的关键API端点和攻击面。**最严重的发现是：V2 API泄露二维码enc生成时间戳(ewnCtime1)，SSO端点泄露IM密码明文，云盘上传无文件类型验证**。结合这些漏洞，学生可通过多种路径完成本不应能完成的签到。

| # | 漏洞 | 严重程度 | 学生端可直接利用 |
|---|---|---|---|
| 1 | `/pptSign/updateSignStatusByUidsV2` CSRF漏洞 | **HIGH (7.5)** | 否（需诱导教师） |
| 2 | **contestyd.chaoxing.com CORS任意Origin反射** | **HIGH (7.2)** | **是（跨域数据窃取）** |
| 3 | **V2 getPPTActiveInfo泄露ewnCtime1+签到安全配置** | **HIGH (7.0)** 🆕 | **是（可计算二维码enc）** |
| 4 | **SSO端点泄露IM密码明文** | **HIGH (6.8)** 🆕 | **是（可读取群聊签到码）** |
| 5 | PC端权限中间件JSON Content-Type绕过 | **MEDIUM (6.1)** | 否（当前不可利用） |
| 6 | 移动端 `updateSignStatus` Cookie注入/JSON绕过 | **MEDIUM (5.5)** | 否（绕过存在但不可利用） |
| 7 | 位置签到距离信息泄露 + 位置伪造 | **MEDIUM (5.3)** | **是** |
| 8 | **云盘上传无文件类型验证（绕过拍照签到）** | **MEDIUM (5.2)** 🆕 | **是** |
| 9 | **签到活动列表对学生完全可见** | **MEDIUM (5.0)** 🆕 | **是（可实时监控签到）** |
| 10 | mobilelearn.chaoxing.com V2 signIn信息泄露 | **MEDIUM (5.0)** | **是（40+内部字段泄露）** |
| 11 | **checkSignCode签到码暴力破解** | **MEDIUM (4.8)** 🆕 | **是（4位码仅10000组合）** |
| 12 | `/newsign/updateSignStatus` 假success + 越权 | **LOW (3.5)** | 是（但无实际影响） |
| 13 | mobilelearn.fy HTTP明文传输 | **LOW (3.1)** | 否（网络嗅探风险） |
| 14 | mh.chaoxing.com网关路由信息泄露 | **LOW (2.8)** | 否（信息泄露） |

---

## 漏洞3：V2 getPPTActiveInfo泄露ewnCtime1+签到安全配置 (HIGH 7.0) 🆕

### 漏洞描述

`/v2/apis/active/getPPTActiveInfo` 端点向学生返回签到活动的完整安全配置，包括二维码enc生成的时间戳参数 `ewnCtime1`。如果enc生成算法可逆（如 `MD5(activeId_ewnCtime1)`），学生可自行计算enc值完成二维码签到，无需扫描二维码。

### 验证证据

```
GET /v2/apis/active/getPPTActiveInfo?activeId=5000163891319

学生可见的敏感字段:
- ewnCtime1: 1781141212745     ← 二维码enc生成核心时间戳
- ewnCtime2: "2026-06-11 09:26:52"
- chartid: 296136586887169    ← 二维码chart ID
- ewmRefreshTime: 10          ← 二维码刷新间隔(秒)
- ifrefreshewm: 1             ← 是否启用二维码刷新
- openCheckFaceFlag: 1        ← 是否需要人脸识别
- openCheckWeChatFlag: 1      ← 是否需要微信验证
- openPreventCheatFlag: 1     ← 是否开启防作弊
- ifNeedVCode: 1              ← 是否需要验证码
- ifphoto: 1                  ← 是否需要拍照
- locationText: "郑州市金水区..." ← 签到地点描述
- locationRange: 500          ← 签到范围(米)
- attendNum: 1                ← 已签到人数
```

### 已正确过滤的字段

```
字段                    | 教师值                    | 学生值  | 状态
----------------------- | ------------------------- | ------- | ----
signCode                | "175509"                  | ""      | ✅ 已过滤
locationLongitude       | "113.6644556500963"       | ""      | ✅ 已过滤
locationLatitude        | "34.78994993072065"       | ""      | ✅ 已过滤
```

### 攻击场景

1. 学生调用 `getPPTActiveInfo` 获取 `ewnCtime1` 和 `chartid`
2. 如果enc算法为 `MD5(activeId + "_" + ewnCtime1)` 或类似变体
3. 学生自行计算enc值
4. 使用enc值调用 `stuSignajax` 完成二维码签到

### 修复建议

1. **[紧急]** 对学生隐藏 `ewnCtime1`、`ewnCtime2`、`chartid` 字段
2. **[紧急]** 对学生隐藏所有安全配置字段（openCheckFaceFlag等）
3. 评估enc生成算法是否可逆，如可逆则需更换算法
4. 减少返回给学生的字段至最小必要集合

---

## 漏洞4：SSO端点泄露IM密码明文 (HIGH 6.8) 🆕

### 漏洞描述

`sso.chaoxing.com/apis/login/userLogin4Uname.do` 端点在返回用户信息时，包含IM账户密码的**明文字段** `accountInfo.imAccount.password`。学生可利用此密码登录IM系统，读取群聊中教师发布的签到码。

### 验证证据

```
POST https://sso.chaoxing.com/apis/login/userLogin4Uname.do

返回数据包含:
- accountInfo.imAccount.password: "C8C5BBF3CD30A1A1" (学生IM密码)
- accountInfo.imAccount.password: "EEF607101FF2374F" (教师IM密码)
```

### 攻击场景

1. 学生登录后调用SSO端点获取IM密码
2. 使用IM密码登录IM系统
3. 读取群聊消息中教师发布的签到码/签到活动信息
4. 利用签到码完成签到码类型签到

### 额外发现

- SSO端点还返回 `switchInfo` 字段（256字符加密数据），可能包含人脸识别signToken所需的 `cxcid` 和 `sc`
- 如果 `switchInfo` 可解密，学生可构造人脸识别signToken绕过人脸验证

### 修复建议

1. **[紧急]** 不在API响应中返回IM密码明文
2. 评估 `switchInfo` 加密强度，确保无法解密获取 `cxcid`/`sc`
3. IM密码应使用OAuth token替代明文密码

---

## 漏洞8：云盘上传无文件类型验证 (MEDIUM 5.2) 🆕

### 漏洞描述

`pan-yz.chaoxing.com` 云盘上传接口无文件类型验证，学生可上传任意文件（包括非照片文件）获取objectId，用于绕过拍照签到的实时拍照要求。

### 验证证据

```
1. 获取云盘token: GET /api/token/uservalid → 成功
2. 上传PNG图片: POST /upload → objectId=14bbd09dc22b5f9fb30c644835ba5f53 ✅
3. 上传TXT文件: POST /upload → 同样成功 ✅
```

### 攻击场景

1. 学生从相册选择任意图片（非实时拍照）
2. 上传到云盘获取objectId
3. 使用objectId调用 `stuSignajax` 的objectId参数完成拍照签到

### 修复建议

1. 添加文件类型验证（仅允许JPEG/PNG）
2. 添加EXIF信息检查（验证是否为实时拍摄）
3. 添加上传时间与签到时间的关联验证

---

## 漏洞9：签到活动列表对学生完全可见 (MEDIUM 5.0) 🆕

### 漏洞描述

`/ppt/activeAPI/taskactivelist` 端点对学生返回完整的签到活动列表，包括所有签到活动的activeId、类型、状态。学生可轮询此接口实时监控新签到并自动响应。

### 验证证据

```
GET /ppt/activeAPI/taskactivelist → 返回30个签到活动

每个活动包含:
- activeId: 签到活动ID
- otherId: 签到类型(0=拍照,2=二维码,3=手势,4=位置,5=签到码)
- status: 活动状态
- name: 活动名称
```

### 修复建议

1. 评估是否需要对学生隐藏活动类型信息
2. 添加请求频率限制

---

## 漏洞11：checkSignCode签到码暴力破解 (MEDIUM 4.8) 🆕

### 漏洞描述

`/widget/sign/pcStuSignController/checkSignCode` 端点存在基于IP的速率限制，但4位数字签到码仅10000种组合，通过多IP/分布式方式仍可暴力破解。

### 验证证据

```
GET /widget/sign/pcStuSignController/checkSignCode?activeId=xxx&signCode=1234

- 正确签到码: result=1 (预期)
- 错误签到码: {"result":0,"errorMsg":"手势不正确"}
- 触发速率限制: "请勿频繁操作"
- 速率限制冷却时间: >120秒
- 教师账号不受同一IP速率限制影响
```

### 攻击场景

1. 学生获取签到活动ID
2. 使用多IP代理分布式尝试4位签到码（0000-9999）
3. 10000种组合在分布式环境下可在数分钟内穷举
4. 获取正确签到码后完成签到

### 修复建议

1. 增加签到码位数（至少6位）
2. 添加账号级别速率限制（非仅IP级别）
3. 错误次数过多后锁定签到码
4. 添加验证码保护

---

## ChaoxingSignFaker揭示的完整API端点清单

### 签到核心接口（mobilelearn.chaoxing.com）

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/pptSign/stuSignajax` | GET | 核心签到接口 | 学生可用 |
| `/newsign/preSign` | POST | 预签到 | 学生可用（返回签到状态信息） |
| `/pptSign/analysis` | GET | 分析链1 | 当前500 |
| `/pptSign/analysis2` | GET | 分析链2 | 当前500 |
| `/pptSign/check-face-result` | GET | 人脸校验 | 需人脸签到场景 |
| `/v2/apis/active/getPPTActiveInfo` | GET | 签到活动详情 | **学生可见敏感配置** |
| `/v2/apis/active/student/activelist` | GET | 活动列表 | 学生可用 |
| `/v2/apis/sign/signIn` | GET | 签到记录查询 | 学生可用 |
| `/widget/sign/pcStuSignController/checkSignCode` | GET | 签到码校验 | 学生可用（有速率限制） |
| `/ppt/activeAPI/taskactivelist` | GET | 活动列表(旧) | 学生可用 |

### 认证/用户接口

| 端点 | 方法 | 说明 | 风险 |
|------|------|------|------|
| `passport2.chaoxing.com/fanyalogin` | POST | 登录 | - |
| `sso.chaoxing.com/apis/login/userLogin4Uname.do` | POST | 用户信息+设备 | **泄露IM密码明文** |
| `im.chaoxing.com/webim/me` | GET | IM配置 | 返回tuid/token |
| `im.chaoxing.com/webim/message/list/getMessageList` | POST | IM消息列表 | 可获取群聊签到信息 |

### 验证码接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `captcha.chaoxing.com/captcha/get/conf` | GET | 验证码配置 |
| `captcha.chaoxing.com/captcha/get/verification/image` | GET | 验证码图片 |
| `captcha.chaoxing.com/captcha/check/verification/result` | GET | 验证码校验 |

### 云盘接口

| 端点 | 方法 | 说明 | 风险 |
|------|------|------|------|
| `pan-yz.chaoxing.com/api/token/uservalid` | GET | 云盘token | 学生可获取 |
| `pan-yz.chaoxing.com/upload` | POST | 图片上传 | **无文件类型验证** |

### 签到流程（ChaoxingSignFaker揭示）

```
1. preSign() → POST /newsign/preSign (检查签到状态)
2. postAnalysis() → GET /pptSign/analysis?aid={activeId} (提取code，当前500)
3. postAfterAnalysis() → GET /pptSign/analysis2?code={code} (完成分析，当前500)
4. stuSignajax → GET /pptSign/stuSignajax (正式签到)
```

**注意**: analysis/analysis2当前返回500，但stuSignajax仍可直接调用（analysis链不被强制执行）。

### 人脸识别绕过算法（ChaoxingSignFaker揭示）

```
1. 上传任意照片到云盘 → 获取objectId (currentFaceId)
2. 构造faceResult: {currentFaceId, LiveDetectionStatus=1, collectStatus=1}
3. 从clientId解密获取cxcid和sc
4. 计算signToken: MD5(拼接所有key+value + sc)
5. 调用 /pptSign/check-face-result → 获取faceEnc
6. 使用faceEnc完成签到
```

**关键**: `LiveDetectionStatus=1` 和 `collectStatus=1` 是硬编码的，不需要真正的人脸活体检测。

---

## 攻击链路总结

| 链路 | 难度 | 流程 | 关键漏洞点 |
|------|------|------|-----------|
| 二维码签到绕过 | 中 | getPPTActiveInfo获取ewnCtime1 → 计算enc → stuSignajax | ewnCtime1泄露 |
| 签到码获取 | 低-中 | SSO获取IM密码 → 读取群聊 → 获取签到码 → 签到 | IM密码明文泄露 |
| 拍照签到绕过 | 低 | 云盘上传任意图片 → 获取objectId → stuSignajax | 云盘无文件验证 |
| 位置签到绕过 | 极低 | 伪造经纬度 → stuSignajax | 无位置验证 |
| 签到码暴力破解 | 中 | checkSignCode尝试0000-9999 → 获取正确码 → 签到 | 4位码+弱速率限制 |
| 人脸识别绕过 | 中-高 | 上传照片 → 构造faceResult → 计算signToken → check-face-result | LiveDetectionStatus硬编码 |
| 普通签到自动化 | 极低 | 轮询taskactivelist → V2 API签到 | 仅需activeId |

---

## 修复优先级

1. **[紧急]** `/pptSign/updateSignStatusByUidsV2` — 禁止GET方法，添加CSRF Token
2. **[紧急]** `contestyd.chaoxing.com` CORS — 限制Origin白名单
3. **[紧急]** `getPPTActiveInfo` — 对学生隐藏ewnCtime1/ewnCtime2/chartid及安全配置字段
4. **[紧急]** SSO端点 — 不返回IM密码明文，评估switchInfo加密强度
5. **[高]** PC端权限中间件 — 覆盖所有Content-Type
6. **[高]** 云盘上传 — 添加文件类型验证和EXIF检查
7. **[高]** 移动端权限校验 — 统一校验入口
8. **[高]** 位置签到 — 不返回精确距离
9. **[高]** V2 signIn — 减少返回字段
10. **[中]** checkSignCode — 增加签到码位数，添加账号级速率限制
11. **[中]** taskactivelist — 添加请求频率限制
12. **[中]** `/newsign/updateSignStatus` — 添加权限校验
13. **[中]** `mh.chaoxing.com` 网关 — 统一错误响应
14. **[低]** `mobilelearn.fy` — 启用HTTPS
15. **[低]** `ss.zhizhen.com` — 评估CORS配置
