# 多人班级签到详情接口验证 Spec

## Why
之前在课程"exam"(classId=132821141)中测试签到详情接口时，班级只有1个学生，可能导致签到详情/统计接口返回异常（如`refeashSignList4Json2`对学生返回`false`可能是因为班级只有自己一人，没有"其他学生"的数据可展示）。用户建议切换到另一个课程"好好学习，天天向上"进行测试，该课程可能有更多学生，签到详情接口的行为可能不同。

## What Changes
- 查找学生账号18436633997的另一个课程"好好学习，天天向上"的courseId和classId
- 在多人班级中重新测试所有签到详情/统计接口
- 重点测试`refeashSignList4Json2`、`signedResult`、`signDetail`等接口
- 对比单人和多人班级的接口行为差异
- 如果发现学生可查看其他学生签到详情，深入挖掘相关修改漏洞

## Impact
- Affected APIs: `/pptSign/*`, `/newsign/*`, `/v2/apis/sign/*`, `/ppt/activeAPI/*`
- Test account: 学生 18436633997/3.1415926Cpy (puid=431407443)
- Course: "好好学习，天天向上" (courseId和classId待查找)

## ADDED Requirements

### Requirement: 多人班级签到详情接口验证
系统 SHALL 在多人班级中验证签到详情接口的行为。

#### Scenario: 查找多人课程
- **WHEN** 用学生账号获取课程列表
- **THEN** 应找到课程"好好学习，天天向上"的courseId和classId

#### Scenario: 多人班级签到详情接口测试
- **WHEN** 在多人班级中测试签到详情接口
- **THEN** 应验证接口是否返回其他学生的签到数据

#### Scenario: 对比单人和多人班级差异
- **WHEN** 对比两个班级的接口返回
- **THEN** 应识别行为差异并分析原因

#### Scenario: 多人班级修改漏洞挖掘
- **WHEN** 发现学生可查看其他学生签到详情
- **THEN** 应围绕该接口深入挖掘修改漏洞
