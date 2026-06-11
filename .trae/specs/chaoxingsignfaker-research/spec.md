# 基于ChaoxingSignFaker开源仓库的签到漏洞深度验证 Spec

## Why
开源仓库 `aquamarine5/ChaoxingSignFaker`（随地大小签）揭示了学习通签到系统的完整攻击面，包括多个我们未发现的API端点和绕过技术。该仓库379次提交、90个标签，是一个成熟的学习通签到伪造工具，支持位置伪造、二维码代签、拍照伪造、人脸识别绕过、验证码自动处理等。我们需要验证这些发现并评估其安全影响。

## What Changes
- 验证ChaoxingSignFaker揭示的新API端点
- 验证签到流程中的preSign→analysis→analysis2→stuSignajax链
- 验证人脸识别绕过（LiveDetectionStatus硬编码）
- 验证验证码系统的完整流程
- 验证云盘图片上传绕过拍照签到
- 验证二维码签到enc参数复用（代签）
- 验证V2活动列表和签到详情API
- 更新安全测试报告

## Impact
- Affected APIs: /newsign/preSign, /pptSign/analysis, /pptSign/analysis2, /pptSign/check-face-result, /v2/apis/active/getPPTActiveInfo, /v2/apis/active/student/activelist, /widget/sign/pcStuSignController/checkSignCode, captcha.chaoxing.com/*
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141 / courseId=262934472, classId=145110605

## ChaoxingSignFaker揭示的关键发现

### 新发现的API端点（我们之前未知）
1. **`/newsign/preSign`** — 预签到接口（签到前必须调用）
2. **`/pptSign/analysis`** — 分析接口1（从返回HTML提取code）
3. **`/pptSign/analysis2`** — 分析接口2（传入code完成分析）
4. **`/pptSign/check-face-result`** — 人脸识别结果校验
5. **`/v2/apis/active/getPPTActiveInfo`** — 获取签到活动详情（V2 API）
6. **`/v2/apis/active/student/activelist`** — 获取活动列表（V2 API）
7. **`/widget/sign/pcStuSignController/checkSignCode`** — 校验手势/签到码
8. **`captcha.chaoxing.com/captcha/get/conf`** — 获取验证码配置
9. **`captcha.chaoxing.com/captcha/get/verification/image`** — 获取验证码图片
10. **`captcha.chaoxing.com/captcha/check/verification/result`** — 校验验证码结果
11. **`pan-yz.chaoxing.com/api/token/uservalid`** — 获取云盘token
12. **`pan-yz.chaoxing.com/upload`** — 上传图片到云盘
13. **`sso.chaoxing.com/apis/login/userLogin4Uname.do`** — 获取用户信息+上传设备信息
14. **`im.chaoxing.com/webim/me`** — 获取IM配置
15. **`im.chaoxing.com/webim/message/list/getMessageList`** — 获取IM群组列表

### 签到绕过技术
1. **位置签到**: 直接伪造经纬度和地址，无位置验证
2. **二维码签到**: enc参数可复用，一台设备扫码可为任意多用户签到
3. **拍照签到**: 从相册选图上传到云盘获取objectId，无需实时拍照
4. **人脸识别绕过**: LiveDetectionStatus=1和collectStatus=1硬编码，上传任意照片即可
5. **验证码**: 完整滑块验证码解决方案
6. **手势/签到码**: checkSignCode接口可暴力尝试

### 签到完整流程
```
1. preSign() → POST /newsign/preSign (检查签到状态)
2. postAnalysis() → GET /pptSign/analysis?aid={activeId} (提取code)
3. postAfterAnalysis() → GET /pptSign/analysis2?code={code} (完成分析)
4. stuSignajax → GET /pptSign/stuSignajax (正式签到)
```

### 人脸识别signToken算法
```
fields = {currentFaceId, LiveDetectionStatus=1, collectStatus=1, cxtime, cxcid}
signedFields = TreeMap(fields)
raw = 拼接所有key+value + sc
signToken = MD5(raw)
```

## ADDED Requirements

### Requirement: 签到流程验证
系统 SHALL 验证ChaoxingSignFaker揭示的完整签到流程。

#### Scenario: preSign→analysis→analysis2→stuSignajax链验证
- **WHEN** 学生按完整流程调用preSign→analysis→analysis2→stuSignajax
- **THEN** 应验证每个步骤的返回值和必要性

### Requirement: 人脸识别绕过验证
系统 SHALL 验证人脸识别签到的绕过方式。

#### Scenario: 人脸识别硬编码绕过
- **WHEN** 学生上传任意照片并设置LiveDetectionStatus=1和collectStatus=1
- **THEN** 应验证是否可绕过人脸识别完成签到

### Requirement: 二维码代签验证
系统 SHALL 验证二维码签到enc参数的复用性。

#### Scenario: enc参数代签
- **WHEN** 一台设备获取二维码enc值后为多个用户使用同一enc签到
- **THEN** 应验证enc参数是否可跨用户复用

### Requirement: V2 API信息泄露验证
系统 SHALL 验证V2活动列表和签到详情API的信息泄露。

#### Scenario: V2活动列表信息泄露
- **WHEN** 学生调用/v2/apis/active/student/activelist和getPPTActiveInfo
- **THEN** 应验证返回的敏感信息（签到码、enc等）

### Requirement: 验证码系统安全评估
系统 SHALL 评估验证码系统的安全性。

#### Scenario: 验证码绕过
- **WHEN** 分析captcha.chaoxing.com的验证码系统
- **THEN** 应评估验证码的安全强度和绕过可能性

### Requirement: 云盘图片上传绕过验证
系统 SHALL 验证通过云盘上传图片绕过拍照签到。

#### Scenario: 拍照签到绕过
- **WHEN** 学生从相册选择图片上传到云盘获取objectId
- **THEN** 应验证是否可绕过实时拍照要求

### Requirement: 安全测试报告更新
系统 SHALL 更新安全测试报告包含所有新发现。

#### Scenario: 报告更新
- **WHEN** 所有验证测试完成
- **THEN** 应更新sign_vuln_report.md至v10.0
