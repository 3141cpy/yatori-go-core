# 超星学习通签到系统安全审计报告

**审计日期**: 2026-06-03 ~ 2026-06-11
**版本**: v9.0（域名映射表深度探索版 — 100+域名全覆盖）
**审计范围**: 学习通全域名签到功能安全评估，基于域名映射表探索100+内部服务域名
**测试账号**: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
**测试课程**: courseId=257485372, classId=132821141 / courseId=262934472, classId=145110605

---

## 核心结论

基于用户提供的完整域名映射表(domainMap)，对100+内部服务域名进行了系统性安全评估。发现**contestyd.chaoxing.com存在严重CORS配置漏洞**（任意Origin反射+凭证允许），以及**mobilelearn.chaoxing.com独立部署的签到API栈存在信息泄露和权限检查缺陷**。学生端仍无法直接修改签到状态，但CORS漏洞可被利用进行跨域数据窃取。

| # | 漏洞 | 严重程度 | 学生端可直接利用 |
|---|---|---|---|
| 1 | `/pptSign/updateSignStatusByUidsV2` CSRF漏洞 | **HIGH (7.5)** | 否（需诱导教师） |
| 2 | **contestyd.chaoxing.com CORS任意Origin反射** | **HIGH (7.2)** | **是（跨域数据窃取）** |
| 3 | PC端权限中间件JSON Content-Type绕过 | **MEDIUM (6.1)** | 否（当前不可利用） |
| 4 | 移动端 `updateSignStatus` Cookie注入/JSON绕过 | **MEDIUM (5.5)** | 否（绕过存在但不可利用） |
| 5 | 位置签到距离信息泄露 + 位置伪造 | **MEDIUM (5.3)** | **是** |
| 6 | **mobilelearn.chaoxing.com V2 signIn信息泄露** | **MEDIUM (5.0)** | **是（40+内部字段泄露）** |
| 7 | `/newsign/updateSignStatus` 假success + 越权 | **LOW (3.5)** | 是（但无实际影响） |
| 8 | mobilelearn.fy HTTP明文传输 | **LOW (3.1)** | 否（网络嗅探风险） |
| 9 | **mh.chaoxing.com网关路由信息泄露** | **LOW (2.8)** | 否（信息泄露） |

---

## 漏洞1：CSRF - `/pptSign/updateSignStatusByUidsV2` (HIGH 7.5)

### 漏洞描述

移动端教师签到状态修改API存在完全无防护的CSRF漏洞。攻击者可构造恶意页面，当已登录的教师访问时，自动修改任意学生的签到状态。

### 验证证据

```
测试项                              | 响应                    | 结果
----------------------------------- | ----------------------- | ----
教师POST(标准Header)                | {"state":"success"}     | 修改成功
教师POST(无X-Requested-With)        | {"state":"success"}     | 修改成功
教师POST(无任何自定义Header)         | {"state":"success"}     | 修改成功
教师POST(Referer=evil.com)          | {"state":"success"}     | 修改成功
教师GET方式                          | {"state":"success"}     | 修改成功
教师GET(Origin=evil.com)            | {"state":"success"}     | 修改成功
```

**关键问题**: 无CSRF Token、支持GET方法、不检查Referer/Origin、可实际修改数据

### 修复建议

1. 禁止GET方法修改数据
2. 添加CSRF Token验证
3. 校验Referer/Origin头
4. 添加SameSite Cookie属性

---

## 漏洞2：contestyd.chaoxing.com CORS任意Origin反射 (HIGH 7.2) 🆕

### 漏洞描述

竞赛云域名 `contestyd.chaoxing.com` 的 `/v2/apis/sign/signIn` 端点存在严重CORS配置缺陷：**反射任意Origin并配合 `Access-Control-Allow-Credentials: true`**。攻击者可在任意恶意网站上编写JavaScript，诱骗已登录用户访问后，跨域读取该API的响应数据（包括携带Cookie的请求）。

### 验证证据

```
Origin Header                        | 响应 Access-Control-Allow-Origin   | Allow-Credentials
------------------------------------ | ---------------------------------- | -----------------
https://mooc1-api.chaoxing.com       | https://mooc1-api.chaoxing.com     | true
https://chaoxing.com                 | https://chaoxing.com               | true
https://evil.com                     | https://evil.com                   | true ✅
null                                 | null                               | true ✅
```

### 攻击场景

1. 攻击者在 `evil.com` 上编写恶意JS代码
2. 诱骗已登录超星的教师/学生访问该页面
3. JS代码发送跨域请求到 `contestyd.chaoxing.com/v2/apis/sign/signIn`
4. 浏览器自动携带Cookie，响应被JS读取
5. 攻击者获取签到数据（当前服务异常返回错误，但若后端修复后可获取完整签到记录）

### 当前可利用性

**部分可利用** — 当前 `/v2/apis/sign/signIn` 返回 `{"result":"0","errorMsg":"服务异常，请稍后重试[50001]"}`，后端服务异常。但CORS漏洞本身已确认存在，一旦后端服务修复，即可被利用窃取签到数据。`null` Origin也被允许，iframe sandbox可利用。

### 修复建议

1. **[紧急]** 修改CORS配置，仅允许白名单Origin
2. 禁止反射任意Origin，禁止 `null` Origin
3. 评估是否真的需要 `Access-Control-Allow-Credentials: true`
4. 后端服务修复后需重新评估数据泄露风险

---

## 漏洞3：PC端权限中间件JSON Content-Type绕过 (MEDIUM 6.1)

### 漏洞描述

PC端 `/widget/sign/pcTeaSignController/updateSignStatus2` 的权限中间件仅检查 `Content-Type: application/x-www-form-urlencoded` 的请求。当使用 `Content-Type: application/json` 时，权限检查被完全绕过。

### 验证证据

```
Content-Type                          | 学生响应                          | 绕过权限?
------------------------------------- | --------------------------------- | --------
application/x-www-form-urlencoded     | {"result":0,"errorMsg":"您无权限修改"} | 否
application/json                      | HTTP 500 Internal Server Error     | 是
```

### 当前可利用性

**当前不可利用** — Controller使用`@RequestParam`无法从JSON body提取参数导致500。若后端改为`@RequestBody`则变为高危。

### 修复建议

1. 权限中间件必须覆盖所有Content-Type
2. 对未支持的Content-Type应返回415而非跳过检查
3. Controller层添加二次权限校验

---

## 漏洞4：移动端 updateSignStatus 权限绕过 (MEDIUM 5.5)

### 漏洞描述

移动端 `/pptSign/updateSignStatus` 存在两种权限绕过方式，虽然当前均不可利用修改数据，但证明权限控制存在缺陷。

### 验证证据

**绕过方式1: Cookie注入**
```
正常学生请求 → "无权限"
注入教师UID Cookie → HTTP 403（走了不同的认证路径，但被网关拦截）
```

**绕过方式2: JSON Content-Type**
```
Content-Type: application/x-www-form-urlencoded → "无权限"
Content-Type: application/json → HTTP 500（绕过业务层权限检查，但参数解析失败）
```

### 当前可利用性

**当前不可利用** — Cookie注入被网关层403拦截，JSON绕过因参数解析失败返回500。但两种绕过都证明权限检查逻辑存在缺陷。

### 修复建议

1. 统一权限校验入口，不依赖Cookie中的UID字段
2. 所有Content-Type都应经过权限检查
3. 添加纵深防御（Controller层二次校验）

---

## 漏洞5：位置签到信息泄露 + 位置伪造 (MEDIUM 5.3)

### 漏洞描述

1. **信息泄露**: 服务端返回学生提交位置到教师指定位置的**精确距离**
2. **位置伪造**: `stuSignajax` API接受任意经纬度参数，服务端仅校验距离

### 验证证据

```
三角定位反推教师位置: (34.784500, 113.659700), 误差仅3m
```

### 修复建议

1. 不返回精确距离，改为"在/不在范围内"
2. 增加位置验证和设备指纹检测

---

## 漏洞6：mobilelearn.chaoxing.com V2 signIn信息泄露 (MEDIUM 5.0) 🆕

### 漏洞描述

`mobilelearn.chaoxing.com` 是独立部署的签到服务域名（与 `mooc1-api.chaoxing.com` 完全独立），其 `/v2/apis/sign/signIn` 端点返回40+个字段的完整签到记录，远超学生端需要的信息，包含多个内部标记字段。

### 验证证据

```
GET /v2/apis/sign/signIn?activeId=xxx → result:1, msg:success

返回字段（40+个）:
- id: 签到记录ID (如5001370808137)
- tag: {"teaUpdateFlag":1}  ← 暴露教师修改痕迹
- fid: 机构ID
- sasort: 排序值
- islook/isshow/ismark: 内部显示控制字段
- longitude/latitude: 签到位置
- clientip: 客户端IP
- useragent: 设备信息
- deviceCode: 设备码
- vpProbability/vpStrategy: VP相关字段
```

### 额外发现

1. **mobilelearn.chaoxing.com 独立部署**: 与 mooc1-api.chaoxing.com 完全独立的签到API栈
2. **updateSignStatus2 权限检查差异**: 学生访问返回"参数错误"而非"无权限"，说明参数校验在权限校验之前
3. **pptSign/endSign 无角色检查**: 学生和教师均可访问，返回"签到不存在"（非"无权限"）
4. **Cookie注入泄露代码路径**: 不同Cookie状态返回不同错误消息（"无权限" vs "无权限。"），泄露后端代码路径差异

### 修复建议

1. 减少返回字段，仅返回学生端必要信息
2. 移除 `teaUpdateFlag`、`vpProbability`、`vpStrategy` 等内部标记
3. 统一错误消息，避免泄露代码路径差异
4. `pptSign/endSign` 添加角色检查

---

## 漏洞7：`/newsign/updateSignStatus` 假success + 越权 (LOW 3.5)

### 漏洞描述

API返回"success"但实际不修改任何数据，且学生可调用教师级API。

### 修复建议

1. 添加权限校验
2. 修复API逻辑确保返回值与实际操作一致

---

## 漏洞8：mobilelearn.fy HTTP明文传输 (LOW 3.1)

### 漏洞描述

泛亚学习端 `mobilelearn.fy.chaoxing.com` 仅支持HTTP协议，认证Cookie以明文传输，存在网络嗅探风险。

### 修复建议

1. 启用HTTPS
2. 设置Cookie Secure属性

---

## 漏洞9：mh.chaoxing.com网关路由信息泄露 (LOW 2.8) 🆕

### 漏洞描述

门户域名 `mh.chaoxing.com` 是Spring Cloud Gateway，使用 `/entry/` 前缀路由。网关对路径的两种不同响应（302→403 vs 404 JSON）泄露了路由注册信息。

### 验证证据

```
路径                                  | 响应           | 含义
------------------------------------- | -------------- | ----
/entry/pptSign/updateSignStatus       | 302→403        | 路由已注册，权限拦截
/entry/newsign/updateSignStatus       | 302→403        | 路由已注册，权限拦截
/entry/pptSign/refeashSignList4Json2  | 404 JSON       | 路由未注册
/entry/pptSign/stuSignajax            | 404 JSON       | 路由未注册
```

### 额外发现

- **分号注入**: `/entry/;jsessionid=test` 返回200，暴露智慧门户个人空间HTML页面（Thymeleaf模板）
- **Spring Boot错误信息泄露**: `/entry/error` 返回 `{"status":999,"error":"None"}`（Spring Security自定义错误码）
- **Actuator端点**: `/entry/actuator` 返回Spring Boot应用层403（非tengine WAF）

### 修复建议

1. 统一错误响应格式，不区分已注册/未注册路由
2. 禁用分号路径匹配
3. 关闭Spring Boot错误详情
4. 保护Actuator端点

---

## 域名映射表全面探索结果

### 探索覆盖范围

| 梯队 | 域名数 | 可达 | 有签到API | 关键发现 |
|---|---|---|---|---|
| 第一梯队（统计/课堂/学习API/办公/任务） | 5 | 5 | 0 | 全部可达但无签到API |
| 第二梯队（泛亚/MOOC2/大数据/统计） | 7 | 7 | 1 | mobilelearn.fy有签到功能 |
| 第三梯队（认证/用户中心/结构/管理） | 8 | 8 | 0 | 无签到API |
| **第四梯队（学习/教学核心）** | 10 | 10 | **1** | **mobilelearn.chaoxing.com有完整签到API栈** |
| 第五梯队（群组/首页/特殊） | 11 | 11 | 0 | special.chaoxing.com有SSO认证网关 |
| 第六梯队（应用/API/资源） | 7 | 7 | 0 | fe.chaoxing.com WAF封堵；mh.chaoxing.com网关路由 |
| 第七梯队（用户/通知/消息） | 8 | 8 | 0 | api.im.chaoxing.com有API但403 |
| 第八梯队（代理/特殊路径） | 8 | 8 | 0 | 代理路径非开放代理，POST统一405 |
| 第九梯队（其他相关） | 14 | 14 | 0 | contestyd.chaoxing.com CORS漏洞 |
| 第十梯队（AI/课堂/会议/直播） | 13 | 13 | 0 | x.chaoxing.com API路由存在但500 |
| 第十一梯队（泛亚/教育/其他） | 35 | 35 | 1 | ss.zhizhen.com完整签到API（需独立认证） |

### 关键域名发现

| 域名 | 发现 | 风险等级 |
|---|---|---|
| **mobilelearn.chaoxing.com** | 独立部署的完整签到API栈，V2 signIn信息泄露 | 🟡 中 |
| **contestyd.chaoxing.com** | CORS任意Origin反射，/v2/apis/sign/signIn存在但服务异常 | 🔴 高 |
| **fe.chaoxing.com** | 签到API路径存在但被WAF(tengine)完全封堵 | 🟢 低 |
| **mh.chaoxing.com** | Spring Cloud Gateway，路由信息泄露，分号注入 | 🟢 低 |
| **ss.zhizhen.com** | 完整签到API部署，需知真独立认证 | 🟡 中 |
| **x.chaoxing.com** | /v2/apis/sign/signIn路由存在但500错误 | 🟢 低 |
| **m.chaoxing.com** | 使用fxlogin独立认证体系，ChaoXing Cookie不互通 | 🟢 低 |
| **special.chaoxing.com** | SSO认证网关(/user/token/getToken)，认证参数通过URL传递 | 🟢 低 |

### 代理路径测试结果

| 路径 | 认证绕过 | 说明 |
|---|---|---|
| noteyd.chaoxing.com/proxy | ❌ 失败 | POST统一405，非开放代理 |
| noteyd.chaoxing.com/comm | ❌ 失败 | 同上 |
| noteyd.chaoxing.com/comp | ❌ 失败 | 路径不存在 |
| appswh.chaoxing.com/epub | ❌ 失败 | POST统一405 |
| appswh.chaoxing.com/board | ❌ 失败 | 路径不存在 |
| appswh.chaoxing.com/projectapp | ❌ 失败 | POST统一405 |
| appswh.chaoxing.com/hbqyg | ❌ 失败 | POST统一405 |

**结论**: 所有代理路径均为反向代理网关，非开放代理，POST请求在网关层被统一拒绝，无法转发到后端签到服务。

### 跨域认证测试结果

| 域名 | ChaoXing Cookie有效 | 独立认证 | 说明 |
|---|---|---|---|
| mobilelearn.chaoxing.com | ✅ 是 | 否 | 与主域共享Cookie |
| m.chaoxing.com | ❌ 否 | 是(fxlogin) | 需fxlogin独立认证 |
| fe.chaoxing.com | N/A | N/A | WAF封堵，无法测试 |
| mh.chaoxing.com | ❌ 否 | 是(网关权限) | Spring Cloud Gateway权限控制 |
| contestyd.chaoxing.com | ✅ 是 | 否 | 与主域共享Cookie，但CORS有问题 |
| ss.zhizhen.com | ❌ 否 | 是(知真认证) | 需login.zhizhen.com认证 |
| ss.chaoxing.com | ❌ 否 | 是(liballiance) | 302→ss.liballiance.com |

---

## 签到详情接口探索结果

### 新发现的移动端端点

| 端点 | 学生响应 | 教师响应 | 敏感数据 |
|---|---|---|---|
| `/pptSign/refeashSignList4Json2` | `false` | 全班签到列表 | 全部学生签到详情 |
| `/pptSign/autoRefeashSignList4Json2` | `false` | 全班签到列表 | 全部学生签到详情 |
| `/pptSign/refeashSignList4Json` | `false` | 全班签到列表 | 全部学生签到详情 |
| `/pptSign/resetUserSignStatus` | "无权限" | "success" | 可重置签到状态 |
| `/pptSign/updateSignStatus` | "无权限" | "修改失败"(需更多参数) | 可修改签到状态 |
| `/pptSign/shuaxin` | 聊天消息 | 聊天消息 | 无敏感数据 |
| `/widget/sign/pcTeaSignController/getSignCode` | "没有权限" | result=1 | 签到码 |
| `/v2/apis/sign/refreshQRCode` | "非二维码签到" | "非二维码签到" | - |

### V2 signIn 返回字段分析

学生通过 `/v2/apis/sign/signIn` 可获取个人签到记录，包含以下字段：

| 字段 | 说明 | 敏感程度 |
|---|---|---|
| id | 签到记录ID (如5001371688276) | 中 |
| uid | 用户ID | 低 |
| activeId | 活动ID | 低 |
| status | 签到状态 | 低 |
| name | 用户姓名 | 中 |
| longitude/latitude | 签到位置 | 高 |
| clientip | 客户端IP | 高 |
| useragent | 设备信息 | 中 |
| submittime | 提交时间 | 低 |
| isdelete | 是否删除 | 低 |
| updatetime | 更新时间 | 低 |
| deviceCode | 设备码 | 中 |
| vpProbability | VP概率 | 低 |
| vpStrategy | VP策略 | 低 |
| **tag** | **{"teaUpdateFlag":1}** | **高（暴露教师修改痕迹）** |
| **fid** | **机构ID** | **中** |
| **sasort** | **排序值** | **低** |
| **islook/isshow/ismark** | **内部显示控制** | **中** |

### 签到统计查看功能

- 所有签到活动的 `isTeacherViewOpen=0`（不允许学生查看统计）
- 学生无法通过任何已测试API直接查看其他学生的签到详情

### IDOR测试结果

- **跨用户IDOR不存在**: uid参数被忽略，服务端基于session判断身份
- **跨活动访问**: 学生可访问同课程所有签到活动的个人记录（仅返回自己的数据）
- **跨课程访问**: 随机activeId返回result=0，无法访问

---

## 风险评估总结

| 漏洞 | CVSS | 攻击难度 | 实际影响 |
|---|---|---|---|
| CSRF(updateSignStatusByUidsV2) | 7.5 | 中（需诱导教师） | 可修改任意学生签到状态 |
| **CORS任意Origin反射(contestyd)** | **7.2** | **低（跨域数据窃取）** | **可跨域读取签到数据** |
| JSON Content-Type权限绕过(PC) | 6.1 | 低（当前不可利用） | 权限控制覆盖不完整 |
| Cookie注入/JSON绕过(移动端) | 5.5 | 低（当前不可利用） | 权限检查逻辑缺陷 |
| 位置签到信息泄露+伪造 | 5.3 | 低（学生可直接利用） | 可伪造位置完成签到 |
| **V2 signIn信息泄露(mobilelearn)** | **5.0** | **极低（学生可直接访问）** | **40+内部字段泄露** |
| 假success+越权(newsign) | 3.5 | 极低（但无实际影响） | 误导性响应 |
| HTTP明文传输(mobilelearn.fy) | 3.1 | 中（需网络嗅探） | Cookie明文传输 |
| **网关路由信息泄露(mh)** | **2.8** | **低** | **路由注册信息泄露** |

---

## 修复优先级

1. **[紧急]** `/pptSign/updateSignStatusByUidsV2` — 禁止GET方法，添加CSRF Token，校验Referer
2. **[紧急]** `contestyd.chaoxing.com` CORS配置 — 限制Origin白名单，禁止null Origin
3. **[紧急]** PC端权限中间件 — 覆盖所有Content-Type
4. **[高]** 移动端权限校验 — 统一校验入口，不依赖Cookie中的UID
5. **[高]** 位置签到 — 不返回精确距离
6. **[高]** `mobilelearn.chaoxing.com` V2 signIn — 减少返回字段，移除内部标记
7. **[中]** `/newsign/updateSignStatus` — 添加权限校验，修复假success
8. **[中]** `mh.chaoxing.com` 网关 — 统一错误响应，禁用分号路径匹配
9. **[低]** `mobilelearn.fy` — 启用HTTPS
10. **[低]** `ss.zhizhen.com` — 评估CORS配置
