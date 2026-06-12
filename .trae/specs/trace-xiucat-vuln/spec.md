# 逆向追踪xiucat补签服务漏洞利用方法 Spec

## Why
用户发现第三方网站 `https://beta-a.xiucat.top` 可以修改学习通签到状态，需要逆向追踪该网站使用的学习通API漏洞。该网站采用前后端分离架构，前端不直接调用学习通API，而是通过后端服务代理操作，因此无法通过前端抓包直接获取其利用的漏洞方法。

## What Changes
- 通过xiucat API的实际调用，记录其对学习通后端的操作行为
- 使用测试学习通账号，对比xiucat操作前后学习通侧的数据变化
- 通过学习通侧的API日志/数据变化，逆向推断xiucat使用的具体API和漏洞
- 验证推断的漏洞利用方法是否可复现

## Impact
- Affected systems: xiucat第三方服务, 学习通签到系统
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141

## xiucat服务架构分析

### 核心工作流程
1. **用户注册/登录** → `POST /api/auth/login` 或 `POST /api/auth/xiucat-quick-login`（支持修猫账号/学习通手机号快捷登录）
2. **绑定超星账号** → `POST /api/chaoxing/accounts`（提交超星手机号+密码，服务端验证登录并存储凭证）
3. **获取课程/活动** → `GET /api/chaoxing/courses` → `GET /api/chaoxing/courses/{courseId}/classes/{classId}/actives`
4. **创建补签任务** → `POST /api/patch-sign/tasks`（指定 accountId, courseId, classId, activeId, targetStatus）
5. **异步执行补签** → 后端任务队列处理，状态流转: CREATED → QUEUED → RUNNING → SUCCESS/FAILED

### 关键发现

#### 1. 系统教师账号机制
- `PUT /api/chaoxing/accounts/system-teacher` — 配置"补签系统教师账号"
- **这暗示xiucat可能使用教师身份来修改签到状态**
- 教师账号的phone/password被存储在xiucat后端

#### 2. targetStatus枚举值
```
1  = 出勤（普通签到）
2  = 迟到
5  = 补签
7  = 二维码签到
8  = 位置签到
9  = 手势签到
10 = 签到码签到
11 = 拍照签到
12 = 快速签到
```
这些值与学习通的签到类型对应，说明xiucat对不同签到类型有针对性处理。

#### 3. 异步任务队列
补签以任务形式创建，支持取消/强制取消，说明后端有任务队列处理。这可能意味着：
- 补签操作可能需要重试
- 可能有并发限制
- 可能有时间窗口要求

#### 4. 账号绑定验证
`POST /api/chaoxing/accounts` 提交超星手机号+密码，服务端会"validate login"，说明xiucat后端会使用这些凭证登录学习通。

### 逆向追踪策略

由于无法直接拦截xiucat后端与学习通的通信，需要从学习通侧观察变化：

#### 策略A：学习通侧数据对比法
1. 记录操作前的签到状态（通过V2 signIn API获取完整记录）
2. 通过xiucat执行补签操作
3. 记录操作后的签到状态
4. 对比差异，特别是：
   - `teaUpdateFlag` 字段变化（如果变为1，说明是教师修改）
   - `updatetime` 变化
   - `status` 变化
   - `useragent` 字段（可能暴露xiucat后端的UA）
   - `clientip` 字段（可能暴露xiucat服务器IP）

#### 策略B：学习通侧API调用日志法
1. 在操作前通过学习通API获取签到详情
2. 通过xiucat执行补签
3. 在操作后立即通过学习通API获取签到详情
4. 分析变化字段推断使用的API

#### 策略C：教师账号验证法
1. 使用教师账号登录学习通
2. 通过xiucat执行补签
3. 检查教师账号的签到管理记录
4. 如果xiucat使用了教师API，教师端应该能看到操作记录

#### 策略D：网络流量分析法
1. 在测试学习通账号上开启所有可能的日志
2. 通过xiucat执行补签
3. 检查学习通侧是否有异常登录记录
4. 检查Cookie/Session变化

#### 策略E：xiucat API响应分析法
1. 调用xiucat的补签任务API
2. 分析任务状态和结果
3. 如果任务失败，错误信息可能暴露其使用的API
4. 如果任务成功，结果信息可能包含学习通API的响应

## ADDED Requirements

### Requirement: xiucat服务API探索
系统 SHALL 对xiucat服务的公开API进行全面探索，理解其工作流程和架构。

#### Scenario: API文档获取
- **WHEN** 访问 https://beta-a.xiucat.top/docs
- **THEN** 应获取完整的OpenAPI规范，识别所有签到相关端点

### Requirement: 学习通侧数据对比
系统 SHALL 通过学习通API记录xiucat操作前后的数据变化。

#### Scenario: 签到状态对比
- **WHEN** 通过xiucat执行补签操作
- **THEN** 应通过V2 signIn API记录操作前后的完整签到记录，对比所有字段变化

### Requirement: 教师API调用验证
系统 SHALL 验证xiucat是否使用教师身份API修改签到状态。

#### Scenario: 教师身份验证
- **WHEN** xiucat执行补签操作后
- **THEN** 应检查签到记录中teaUpdateFlag字段是否变为1，以及教师端是否可见操作记录

### Requirement: 漏洞利用方法复现
系统 SHALL 基于逆向追踪结果，复现xiucat使用的漏洞利用方法。

#### Scenario: 漏洞复现
- **WHEN** 确定xiucat使用的具体API和方法
- **THEN** 应使用测试账号独立复现该漏洞利用方法
