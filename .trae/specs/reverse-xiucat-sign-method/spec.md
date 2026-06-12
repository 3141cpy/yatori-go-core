# 逆向分析xiucat.top签到修改方法 Spec

## Why
用户发现网站 beta-a.xiucat.top 可以修改学习通签到状态，经实际测试确认有效。经过深入探索，已完全理解该网站的架构和工作流程。该网站有两套后端系统：VIP Center API（补签功能）和修猫助手V2 API（签到功能）。核心问题是：**补签功能(patch-sign)是如何实现的？** 它很可能利用了教师权限的水平越权漏洞。

## 网站架构（已确认）

| 服务 | 基础URL | 框架 | 用途 |
|------|---------|------|------|
| **VIP Center API** | `https://beta-a.xiucat.top` | NestJS | VIP会员管理、补签任务、充值 |
| **修猫助手V2 API** | `https://api-test.xiucat.top/v2` | NestJS | 签到/打卡核心功能 |
| **前端应用** | `https://cx.xiucat.top` | UniApp | 用户界面 |

### 关键发现

1. **Swagger文档完全公开**: `/docs` 和 `/openapi.json` 暴露了89个API端点
2. **补签任务API**: `POST /api/patch-sign/tasks` — 创建补签任务，targetStatus: 1/2/5/7/8/9/10/11/12
3. **系统教师账号**: `GET /api/chaoxing/accounts/system-teacher` — 获取系统教师账号
4. **V2签到API使用学生身份**: 直接用超星手机号+密码登录，获取学生session
5. **邀请代签**: `/v2/student/sign/invite/create` 生成邀请链接允许他人代签

### 核心工作流程

**补签流程（VIP API）**:
1. 绑定超星账号 → `POST /api/chaoxing/accounts`
2. 获取课程 → `GET /api/chaoxing/courses`
3. 获取签到活动 → `GET /api/chaoxing/courses/{courseId}/classes/{classId}/actives`
4. 获取活动成员状态 → `GET /api/chaoxing/actives/{activeId}/members`
5. **创建补签任务** → `POST /api/patch-sign/tasks`（targetStatus: 1/2/5/7/8/9/10/11/12）
6. 系统使用**系统教师账号**执行补签

**签到流程（V2 API）**:
1. 登录 → `POST /v2/student/auth/login`（超星手机号+密码）
2. 获取课程 → `GET /v2/student/sign/courses`
3. 获取活动 → `POST /v2/student/sign/activities`
4. 执行签到 → 根据类型选择端点(normal/picture/qrcode/location/gesture-code)

## What Changes
- 验证补签功能的核心机制：系统教师账号 + updateSignStatusByUidsV2
- 验证系统教师账号的越权能力边界
- 验证邀请代签功能
- 对比V2签到API与学生直接签到的差异
- 确认xiucat.top利用的具体漏洞

## Impact
- Test accounts: 教师 19712720708 (puid=402644510), 学生 18436633997 (puid=431407443)
- Course 1: courseId=257485372, classId=132821141（课程exam，19712720708是教师）
- Course 2: courseId=262934472, classId=145110605（课程"好好学习，天天向上"，18436633997是学生）

## 核心假设（更新）

### 假设1：系统教师账号 + 水平越权（最高可能性）
- **原理**: xiucat.top维护了系统教师账号(`system-teacher`)，通过该账号调用updateSignStatusByUidsV2修改任意学生签到状态
- **证据**: 
  - API中有`GET /api/chaoxing/accounts/system-teacher`获取系统教师账号
  - API中有`PUT /api/chaoxing/accounts/system-teacher`配置系统教师账号
  - 补签任务的targetStatus包括1(出勤)/2(迟到)/5(补签)等教师才能设置的状态
- **验证方法**: 用19712720708(教师)调用updateSignStatusByUidsV2修改18436633997在课程262934472的签到状态

### 假设2：邀请代签（中等可能性）
- **原理**: V2 API的邀请签到功能允许一个学生创建邀请，另一个学生通过邀请链接代签
- **证据**: `/v2/student/sign/invite/create` 和 `/v2/student/sign/invite/verify` 端点存在
- **验证方法**: 测试邀请代签是否可以绕过签到类型限制

### 假设3：直接使用学生Cookie调用签到API（低可能性）
- **原理**: V2 API登录后获取学生Cookie，直接调用stuSignajax等接口
- **证据**: V2 API的签到端点(normal/qrcode/location等)直接使用学生身份
- **局限**: 这只能完成签到，不能修改已结束的签到状态

## ADDED Requirements

### Requirement: 系统教师账号越权验证
系统 SHALL 验证教师账号是否能修改非本课程学生的签到状态。

#### Scenario: 教师修改非本班学生签到
- **WHEN** 使用19712720708(教师)的session调用updateSignStatusByUidsV2，目标uid=431407443(学生)，activeId属于courseId=262934472
- **THEN** 应记录API是否返回success，签到状态是否实际被修改

#### Scenario: 教师修改本班学生签到（对照组）
- **WHEN** 使用19712720708(教师)的session调用updateSignStatusByUidsV2，目标uid=431407443(学生)，activeId属于courseId=257485372
- **THEN** 应确认签到状态成功修改（作为基线对照）

### Requirement: 越权能力边界测试
系统 SHALL 测试教师账号的越权能力边界。

#### Scenario: 跨课程修改
- **WHEN** 教师尝试修改非自己课程的学生签到状态
- **THEN** 应记录哪些接口允许跨课程操作

### Requirement: 邀请代签功能测试
系统 SHALL 验证邀请代签功能是否可被利用。

#### Scenario: 邀请代签
- **WHEN** 一个学生创建邀请签到链接
- **THEN** 另一个学生通过该链接是否可以完成签到

### Requirement: xiucat.top行为匹配分析
系统 SHALL 将测试结果与xiucat.top的行为进行对比。

#### Scenario: 行为匹配
- **WHEN** 完成所有漏洞验证后
- **THEN** 应分析xiucat.top最可能利用的漏洞类型
