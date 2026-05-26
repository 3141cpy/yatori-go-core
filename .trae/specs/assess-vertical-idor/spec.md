# 课程垂直越权漏洞评估 Spec

## Why
前几轮评估已确认课程CPI水平越权漏洞，但尚未测试垂直越权——即学生账号是否可以访问或操作教师（课程创建者/管理者）专属的管理功能，如签到管理、活动管理、成绩管理、课程设置等。如果服务端仅依赖前端角色判断而未在API层校验用户角色权限，则存在严重的垂直越权风险。

## What Changes
- 分阶段进行：第一阶段调查教师管理API端点，第二阶段实际测试垂直越权
- 测试学生账号访问教师管理功能（签到管理、活动管理、成绩管理、课程设置等）
- 测试通过修改role参数绕过角色校验
- 测试通过修改cpi/uid参数冒充教师身份
- 评估垂直越权的完整影响范围

## Impact
- Affected specs: deep-cpi-idor, assess-platform-idor
- Affected APIs: mobilelearn.chaoxing.com, mooc1-api.chaoxing.com, mooc1.chaoxing.com
- Key code: CourseEntity.go (roletype字段), 硬编码Cookie (sso_role=3)

## ADDED Requirements

### Requirement: 第一阶段——教师管理API端点调查
系统 SHALL 先调查教师管理功能的API端点，再进行实际测试。

#### Scenario: 签到管理API调查
- **WHEN** 调查学习通签到管理相关的API端点
- **THEN** 应明确列出教师创建/管理签到的API端点、参数和认证方式

#### Scenario: 活动管理API调查
- **WHEN** 调查学习通活动管理相关的API端点
- **THEN** 应明确列出教师创建/管理活动的API端点

#### Scenario: 课程管理API调查
- **WHEN** 调查学习通课程管理相关的API端点
- **THEN** 应明确列出教师管理课程的API端点（成绩设置、成员管理等）

### Requirement: 第二阶段——签到系统垂直越权测试
系统 SHALL 使用学生账号测试签到管理功能的垂直越权。

#### Scenario: 学生获取课程活动列表
- **WHEN** 学生账号请求 /ppt/activeAPI/taskactivelist
- **THEN** 验证是否可获取教师创建的签到活动信息

#### Scenario: 学生创建签到活动
- **WHEN** 学生账号尝试调用教师创建签到的API
- **THEN** 验证是否可代替教师创建签到

#### Scenario: 学生管理签到结果
- **WHEN** 学生账号尝试查看/修改签到结果
- **THEN** 验证是否可访问教师专属的签到管理数据

### Requirement: 第二阶段——活动管理垂直越权测试
系统 SHALL 使用学生账号测试活动管理功能的垂直越权。

#### Scenario: 学生创建课堂活动
- **WHEN** 学生账号尝试调用创建活动API（投票/问卷/练习等）
- **THEN** 验证是否可代替教师创建活动

#### Scenario: 学生管理活动结果
- **WHEN** 学生账号尝试查看/修改活动结果
- **THEN** 验证是否可访问教师专属的活动管理数据

### Requirement: 第二阶段——课程管理垂直越权测试
系统 SHALL 使用学生账号测试课程管理功能的垂直越权。

#### Scenario: 学生访问课程管理页面
- **WHEN** 学生账号访问 /mycourse/teacherindex 或类似教师管理页面
- **THEN** 验证是否可获取教师管理界面数据

#### Scenario: 学生修改课程设置
- **WHEN** 学生账号尝试修改课程设置（成绩权重、成员管理等）
- **THEN** 验证是否可执行教师专属操作

#### Scenario: 学生查看班级统计
- **WHEN** 学生账号尝试查看班级学习统计
- **THEN** 验证是否可获取其他学生的学习数据

### Requirement: 第二阶段——角色参数篡改测试
系统 SHALL 测试通过修改角色相关参数绕过权限校验。

#### Scenario: 修改sso_role参数
- **WHEN** 将Cookie中的sso_role从3（学生）修改为1或2（教师/管理员）
- **THEN** 验证是否可绕过角色校验

#### Scenario: 修改role参数
- **WHEN** 在API请求中添加role=teacher或role=admin参数
- **THEN** 验证是否可绕过角色校验

#### Scenario: 修改roletype参数
- **WHEN** 修改请求中的roletype参数值
- **THEN** 验证是否可绕过角色校验

### Requirement: 课程垂直越权评估报告
系统 SHALL 生成课程垂直越权漏洞评估报告。

#### Scenario: 报告内容完整性
- **WHEN** 评估完成
- **THEN** 报告应包含：教师管理API端点清单、每个功能的垂直越权测试结果、角色校验机制分析、修复建议

---

## 附录：已发现的教师管理API端点

### 签到系统（来自联网搜索）

| API | URL | 方法 | 功能 | 认证 |
|---|---|---|---|---|
| 获取活动列表 | /ppt/activeAPI/taskactivelist | GET | 获取课程下的活动列表 | Cookie |
| 新版活动列表 | /v2/apis/active/student/activelist | GET | 新版学生活动列表 | Cookie |
| 学生签到 | /pptSign/stuSignajax | POST | 学生执行签到 | Cookie |
| 教师创建签到 | /ppt/activeAPI（推测） | POST | 教师创建签到活动 | Cookie+角色 |

### 课程管理（来自代码库分析）

| API | URL | 功能 | 关键参数 |
|---|---|---|---|
| 课程章节管理 | /gas/clazz | 课程章节列表 | id, personid(cpi) |
| 知识节点详情 | /gas/knowledge | 知识节点详情 | id, courseid, token=K6 |
| 进入章节 | /mooc-ans/mycourse/studentstudyAjax | 进入章节学习 | courseId, clazzid, cpi |
| 课程完成度 | /mooc2-ans/mycourse/stu-job-info | 课程完成度 | clazzPersonStr |

### 角色相关发现

- Cookie中 `sso_role=3` 可能代表学生角色
- `CourseEntity.go` 中有 `roletype` 字段
- 工学云模块使用 `roleKey`/`roleId` 进行角色判断
- 作业/考试Referer中有 `role=` 参数（当前为空）
