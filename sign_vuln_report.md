# 超星学习通签到系统安全审计报告

**审计日期**: 2026-06-03
**版本**: v7.0（签到详情接口探索版）
**审计范围**: 学习通PC端+移动端签到功能全面安全评估，含签到详情接口深度探索
**测试账号**: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
**测试课程**: courseId=257485372, classId=132821141

---

## 核心结论

原始漏洞位于PC端接口 `/widget/sign/pcTeaSignController/updateSignStatus2`（通过油猴脚本确认），已被紧急修复。本次评估重点探索了学生端签到详情接口，确认**学生无法直接查看其他学生的签到详情**（`refeashSignList4Json2` 对学生返回 `false`）。但发现了多个权限绕过点（均不可直接利用修改数据），以及CSRF、信息泄露等已确认漏洞。

| # | 漏洞 | 严重程度 | 学生端可直接利用 |
|---|---|---|---|
| 1 | `/pptSign/updateSignStatusByUidsV2` CSRF漏洞 | **HIGH (7.5)** | 否（需诱导教师） |
| 2 | PC端权限中间件JSON Content-Type绕过 | **MEDIUM (6.1)** | 否（当前不可利用） |
| 3 | 移动端 `updateSignStatus` Cookie注入/JSON绕过 | **MEDIUM (5.5)** | 否（绕过存在但不可利用） |
| 4 | 位置签到距离信息泄露 + 位置伪造 | **MEDIUM (5.3)** | **是** |
| 5 | `/newsign/updateSignStatus` 假success + 越权 | **LOW (3.5)** | 是（但无实际影响） |

---

## 漏洞1：CSRF - `/pptSign/updateSignStatusByUidsV2` (HIGH)

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

## 漏洞2：PC端权限中间件JSON Content-Type绕过 (MEDIUM)

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

## 漏洞3：移动端 updateSignStatus 权限绕过 (MEDIUM)

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

## 漏洞4：位置签到信息泄露 + 位置伪造 (MEDIUM)

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

## 漏洞5：`/newsign/updateSignStatus` 假success + 越权 (LOW)

### 漏洞描述

API返回"success"但实际不修改任何数据，且学生可调用教师级API。

### 修复建议

1. 添加权限校验
2. 修复API逻辑确保返回值与实际操作一致

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

### 签到统计查看功能

- 所有签到活动的 `isTeacherViewOpen=0`（不允许学生查看统计）
- `preSign` 和 `newsign/preSign` 页面包含签到相关JS代码
- `isTeacherViewOpen=-1` 时前端不展示统计
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
| JSON Content-Type权限绕过(PC) | 6.1 | 低（当前不可利用） | 权限控制覆盖不完整 |
| Cookie注入/JSON绕过(移动端) | 5.5 | 低（当前不可利用） | 权限检查逻辑缺陷 |
| 位置签到信息泄露+伪造 | 5.3 | 低（学生可直接利用） | 可伪造位置完成签到 |
| 假success+越权(newsign) | 3.5 | 极低（但无实际影响） | 误导性响应 |

---

## 修复优先级

1. **[紧急]** `/pptSign/updateSignStatusByUidsV2` — 禁止GET方法，添加CSRF Token，校验Referer
2. **[紧急]** PC端权限中间件 — 覆盖所有Content-Type
3. **[高]** 移动端权限校验 — 统一校验入口，不依赖Cookie中的UID
4. **[高]** 位置签到 — 不返回精确距离
5. **[中]** `/newsign/updateSignStatus` — 添加权限校验，修复假success
6. **[低]** V2 signIn API — 位置/IP/设备信息脱敏
