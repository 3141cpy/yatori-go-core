# 再次验证未签二维码签到漏洞 Spec

## Why
用户已有一个新的未签二维码签到活动，需要再次验证`/newsign/updateSignStatus`漏洞是否可行。

## What Changes
- 获取最新活动列表，找到未签的二维码签到活动
- 学生调用漏洞API修改签到状态
- 验证修改是否生效

## Impact
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141

## ADDED Requirements

### Requirement: 验证新二维码签到活动漏洞
系统 SHALL 对新的未签二维码签到活动验证漏洞可行性。

#### Scenario: 学生修改未签二维码签到状态
- **WHEN** 学生调用 /newsign/updateSignStatus 修改未签的二维码签到状态为出勤
- **THEN** 通过V2 signIn API查询确认status已变为1
