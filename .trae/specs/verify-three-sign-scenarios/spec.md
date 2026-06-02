# 三种签到活动定向漏洞验证 Spec

## Why
用户确认课程"111"现有3个需要测试的签到活动：已结束未签的二维码签到、进行中的二维码签到、已结束的签退活动。需要针对这3种不同场景验证`/newsign/updateSignStatus`漏洞是否可行，特别是二维码签到和签退活动是否有额外的校验机制。

## What Changes
- 获取课程111的最新活动列表，识别3个目标签到活动
- 对已结束未签的二维码签到测试漏洞利用
- 对进行中的二维码签到测试漏洞利用
- 对已结束的签退活动测试漏洞利用
- 记录每种场景的详细测试结果

## Impact
- Affected APIs: /newsign/updateSignStatus, /v2/apis/sign/signIn, /pptSign/stuSignajax
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141

## ADDED Requirements

### Requirement: 三种签到场景漏洞验证
系统 SHALL 对3种不同签到场景分别验证漏洞可行性。

#### Scenario: 已结束未签的二维码签到
- **WHEN** 学生调用 /newsign/updateSignStatus 修改已结束的二维码签到状态
- **THEN** 记录API响应和实际签到状态变化

#### Scenario: 进行中的二维码签到
- **WHEN** 学生调用 /newsign/updateSignStatus 修改进行中的二维码签到状态
- **THEN** 记录API响应和实际签到状态变化

#### Scenario: 已结束的签退活动
- **WHEN** 学生调用 /newsign/updateSignStatus 修改签退活动状态
- **THEN** 记录API响应和实际签到状态变化
