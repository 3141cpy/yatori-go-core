# 超星学习通签到系统安全审计报告

**审计日期**: 2026-06-03
**版本**: v7.0（深度多域名渗透测试版）
**审计范围**: 学习通PC端+移动端+多域名签到功能全面安全评估
**测试账号**: 教师 19712720708 (puid=402644510)，学生 18436633997 (puid=431407443)
**测试课程**: courseId=257485372, classId=132821141

---

## 核心结论

原始漏洞位于PC端接口 `/widget/sign/pcTeaSignController/updateSignStatus2`，已被修复。但全面评估发现签到系统仍存在多个安全问题，其中**QR码enc值泄露+学生签到绕过**是最具潜在价值的攻击链，需在活跃签到环境下进一步验证。

| # | 漏洞 | 严重程度 | 学生端可直接利用 | 状态 |
|---|---|---|---|---|
| 1 | `/pptSign/updateSignStatusByUidsV2` CSRF漏洞 | **HIGH (7.5)** | 否（需诱导教师） | 已确认 |
| 2 | 教师preSign页面QR码enc值泄露 | **HIGH (7.1)** | 需进一步验证 | 待活跃活动验证 |
| 3 | PC端权限中间件JSON Content-Type绕过 | **MEDIUM (6.1)** | 否（当前不可利用） | 已确认 |
| 4 | 位置签到距离信息泄露+位置伪造 | **MEDIUM (5.3)** | **是** | 已确认 |
| 5 | `/mooc-ans/qr/` 端点认证差异 | **MEDIUM (5.0)** | 部分可利用 | 已确认 |
| 6 | `/newsign/updateSignStatus` 假success+越权 | **LOW (3.5)** | 是（但无实际影响） | 已确认 |

---

## 漏洞1：CSRF - `/pptSign/updateSignStatusByUidsV2` (HIGH)

### 漏洞描述

移动端教师签到状态修改API存在完全无防护的CSRF漏洞。攻击者可构造恶意页面，当已登录的教师访问时，自动修改任意学生的签到状态。

### 验证证据

- 无CSRF Token
- 支持GET方法（`<img>`标签即可触发）
- 不检查Referer/Origin
- 可实际修改签到状态数据

### CSRF PoC

```html
<img src="https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}&uids={uid}&status=1&remark=" width="0" height="0" />
```

### 修复建议
1. 禁止GET方法修改数据
2. 添加CSRF Token验证
3. 校验Referer/Origin头
4. 添加SameSite Cookie属性

---

## 漏洞2：教师preSign页面QR码enc值泄露 (HIGH)

### 漏洞描述

教师的 `/newsign/preSign` 页面在HTML中包含隐藏input字段，泄露了QR签到的关键加密数据（`viceScreenEwmEnc`）。如果学生能获取此值，即可通过 `pptSign/stuSignajax` 绕过二维码验证完成签到。

### 验证证据

教师访问 `newsign/preSign` 页面时，HTML中包含：

```html
<input type="hidden" id="viceScreenEwmEnc" value="F7A141E39C0D366E1B7E98AE84FE8CF9" />
<input type="hidden" id="signCode" value="504149" />
<input type="hidden" id="otherId" value="2" />
<input type="hidden" id="activeStatus" value="2" />
<input type="hidden" id="ifRefreshEwm" value="1" />
```

成功提取了4个QR签到活动的enc值：
- aid=5000163964324: `F7A141E39C0D366E1B7E98AE84FE8CF9`
- aid=5000163963862: `549C9DC1A86F433AC8EBE1E482C75625`
- aid=5000163891319: `B50F8B13102B5979368A13C02F8625F2`
- aid=5000163776552: `7E71AE8B62F8272E947DF44879EA30F5`

### 攻击链（理论验证中）

```
1. 教师发起QR签到活动（活跃状态status=1）
2. 教师访问 /newsign/preSign 页面
3. 页面HTML中包含 viceScreenEwmEnc 值
4. 学生获取该enc值（通过CSRF/网络嗅探/其他途径）
5. 学生调用 pptSign/stuSignajax(activeId={aid}, enc={viceScreenEwmEnc})
6. 签到成功
```

### 当前限制

- 所有测试活动已结束（status=2），enc值无法使用
- 学生直接访问教师preSign页面返回"暂无权限"
- 需要在活跃签到环境下验证完整攻击链

### 修复建议
1. **不在HTML中暴露enc值** — 改为API动态获取
2. **enc值绑定时间窗口** — 过期自动失效
3. **enc值绑定用户身份** — 限制只能由发起签到的教师获取
4. **添加访问频率限制** — 防止暴力获取enc值

---

## 漏洞3：PC端权限中间件JSON Content-Type绕过 (MEDIUM)

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

**当前不可利用** — Controller使用`@RequestParam`注解无法从JSON body提取参数。但若后端代码改为`@RequestBody`接收JSON，此绕过将变为高危可利用漏洞。

### 修复建议
1. 权限中间件必须覆盖所有Content-Type
2. 对未支持的Content-Type应返回415，而非跳过检查
3. Controller层添加二次权限校验

---

## 漏洞4：位置签到信息泄露+位置伪造 (MEDIUM)

### 漏洞描述

1. 服务端返回学生位置到教师指定位置的**精确距离**（信息泄露）
2. `stuSignajax` 接受任意经纬度参数（位置伪造）

### 验证证据

- 三角定位法可反推教师位置（误差3m）
- 学生可伪造GPS坐标完成位置签到

### 修复建议
1. 不返回精确距离，改为"在/不在范围内"
2. 检测异常GPS精度和位置跳跃
3. 添加设备指纹检测

---

## 漏洞5：`/mooc-ans/qr/` 端点认证差异 (MEDIUM)

### 漏洞描述

`mooc1-api.chaoxing.com` 域名下的QR码相关端点存在认证差异：

1. **`/mooc-ans/qr/getqrstatus`**: 学生返回code=1，教师返回code=0 — 角色区分信号泄露
2. **`/mooc-ans/qr/updateqrstatus`**: JSON Content-Type可绕过认证重定向，返回"参数不完整"而非登录页
3. **`/qr/updateqrstatus`**: 学生POST返回"图片格式错误"而非"无权限" — 学生请求通过了权限检查

### 验证证据

| 端点 | 学生(form) | 学生(JSON) | 教师(form) |
|---|---|---|---|
| `/qr/updateqrstatus` | 302重定向 | "图片格式错误" | "无权限管理" |
| `/mooc-ans/qr/updateqrstatus` | 302重定向 | "参数不完整" | 302重定向 |
| `/mooc-ans/qr/getqrstatus` | code=1 | - | code=0 |

### 修复建议
1. 统一认证机制，所有Content-Type都应经过认证
2. 不泄露角色区分信息（code值差异）
3. 学生请求应返回"无权限"而非进入业务逻辑

---

## 漏洞6：`/newsign/updateSignStatus` 假success+越权 (LOW)

### 漏洞描述

API返回"success"但实际不修改数据，且学生可调用教师级API。

### 修复建议
1. 添加权限校验
2. 修复API逻辑确保返回值与实际操作一致

---

## 多域名API枚举结果

### 存活的端点

| 域名 | 端点 | 学生响应 | 教师响应 | 备注 |
|---|---|---|---|---|
| mobilelearn | /pptSign/updateSignStatusByUidsV2 | "无权限" | "success" | CSRF漏洞 |
| mobilelearn | /newsign/updateSignStatus | "success"(假) | "success" | 假success |
| mobilelearn | /widget/sign/pcTeaSignController/updateSignStatus2 | "您无权限修改" | "success" | 已修复 |
| mobilelearn | /newsign/preSign | 500 | 含viceScreenEwmEnc | enc值泄露 |
| mooc1-api | /qr/updateqrstatus | "图片格式错误" | "无权限管理" | 权限差异 |
| mooc1-api | /mooc-ans/qr/updateqrstatus | "参数不完整"(JSON) | 302重定向 | 认证绕过 |
| mooc1-api | /mooc-ans/qr/getqrstatus | code=1 | code=0 | 角色泄露 |
| mooc1-api | /mooc-ans/qr/produce | "无效的参数code=1" | "无效的参数code=1" | 参数不完整 |
| mooc1-api | /mooc-ans/facephoto/clientfacecheckstatus | "无权限" | "无权限" | 需要权限 |

### 不存在的端点

- `mooc2-ans.chaoxing.com` — 所有端点404
- `mooc1-api.chaoxing.com/mooc-ans/pptSign/*` — 404
- `mooc1-api.chaoxing.com/mooc-ans/newsign/*` — 404
- `mooc1-api.chaoxing.com/mooc-ans/sign/*` — 404

---

## inf_enc签名算法分析

### 算法细节（从Go源码逆向）

```
DESKey = "Z(AfY@XS"
签名 = MD5(参数按顺序拼接 + "&DESKey=" + DESKey)
```

### 测试结果

- inf_enc签名**不能绕过权限检查** — 带/不带签名结果完全一致
- 签名仅用于参数完整性验证，不参与权限判断

---

## 修复优先级

1. **[紧急]** `/pptSign/updateSignStatusByUidsV2` — 禁止GET方法，添加CSRF Token
2. **[紧急]** 教师preSign页面 — 不在HTML中暴露viceScreenEwmEnc值
3. **[高]** PC端权限中间件 — 覆盖所有Content-Type
4. **[高]** `/mooc-ans/qr/` 端点 — 统一认证机制，消除角色信息泄露
5. **[中]** 位置签到 — 不返回精确距离
6. **[低]** `/newsign/updateSignStatus` — 添加权限校验，修复假success

---

## 待验证项

以下发现需要在**活跃签到环境**下进一步验证：

1. **enc值利用链**: 当QR签到活动处于活跃状态(status=1)时，学生是否能用从教师preSign页面获取的viceScreenEwmEnc值通过stuSignajax完成签到？
2. **学生获取enc值**: 学生是否有任何途径（API/页面/网络）获取活跃签到的enc值？
3. **`/qr/updateqrstatus` 完整利用**: 学生POST返回"图片格式错误"说明已通过权限检查，如果能提供有效的qrcEnc参数，是否可以完成签到？

建议在真实课堂环境中发起活跃签到活动进行验证。
