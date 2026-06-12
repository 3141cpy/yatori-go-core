# 重新验证横向越权漏洞 Spec

## Why
之前的测试结论有误：19712720708是课程111(courseId=257485372)的创建者，所以在Course1上修改学生签到状态是正常权限操作，不是越权。Course2上修改失败才是正确的权限控制。因此横向越权漏洞并未被真正验证。需要重新设计测试方案，找到一个真正不在目标课程中的教师账号来验证越权。

## 核心问题
- 19712720708是Course1的创建者/教师 → Course1成功是正常行为
- 19712720708不在Course2中 → Course2失败是正常权限控制
- **结论：横向越权漏洞尚未被验证**

## 可能的探索方向

### 方向1：19712720708创建新课程后作为教师修改Course2学生
- 19712720708虽然是学生身份，但可以创建课程
- 创建课程后是否获得教师权限？
- 用这个"教师权限"能否修改其他课程(Course2)的学生签到？

### 方向2：xiucat.top的系统教师账号到底是什么
- xiucat.top的`system-teacher`是否是真正的教师账号？
- 还是某种特殊权限账号？
- 可能是超星内部账号或管理员账号

### 方向3：xiucat.top V2 API的签到功能是如何绕过限制的
- V2 API的签到端点(normal/qrcode/location)直接使用学生Cookie
- 但这些端点只能完成进行中的签到，不能修改已结束的签到
- 补签(patch-sign)功能才是核心 — 它是如何实现的？

### 方向4：探索updateSignStatus2的参数组合
- 之前测试中，mobilelearn.chaoxing.com的updateSignStatus2对学生返回"参数错误"而非"无权限"
- 是否存在某种参数组合可以绕过权限检查？
- denc参数是什么？如何获取？

### 方向5：学生创建课程获取教师身份后跨课程操作
- 19712720708创建课程后，是否可以在自己课程中获得教师身份？
- 获得教师身份后，能否跨课程修改签到？

## What Changes
- 重新验证横向越权：用真正不在目标课程中的教师账号测试
- 深入探索19712720708创建课程后的权限变化
- 探索xiucat.top补签功能的真实实现方式
- 测试updateSignStatus2的参数绕过可能性

## Impact
- Test accounts: 19712720708 (Course1创建者), 18436633997 (学生)
- Course 1: courseId=257485372, classId=132821141（19712720708是创建者）
- Course 2: courseId=262934472, classId=145110605（19712720708不在其中）

## ADDED Requirements

### Requirement: 正确验证横向越权
系统 SHALL 使用真正不在目标课程中的教师身份来验证横向越权。

#### Scenario: 19712720708创建新课程后修改Course2学生签到
- **WHEN** 19712720708创建新课程获得教师身份后，尝试修改Course2的学生签到状态
- **THEN** 应记录是否成功，分析权限检查逻辑

#### Scenario: 探索updateSignStatus2参数绕过
- **WHEN** 使用学生session调用updateSignStatus2，尝试不同的参数组合
- **THEN** 应记录是否存在参数组合可绕过权限检查

### Requirement: 深入分析xiucat.top补签实现
系统 SHALL 深入分析xiucat.top补签功能的真实实现方式。

#### Scenario: 分析xiucat.top补签流程
- **WHEN** 分析xiucat.top的VIP API补签流程
- **THEN** 应确定其使用的具体API和参数
