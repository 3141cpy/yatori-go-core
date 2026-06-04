# 深度签到状态修改漏洞探索 Spec

## Why
知情人士透露签到状态修改漏洞依旧存在。之前测试集中在 `mobilelearn.chaoxing.com` 域名的 `/pptSign/` 和 `/newsign/` 路径，但Go源码揭示了多个未测试的API域名和端点（`mooc1-api.chaoxing.com/qr/updateqrstatus`、`mooc-ans/facephoto/`、`mooc-ans/qr/`等），且PC端 `/widget/sign/pcTeaSignController/` 的JSON Content-Type绕过虽然当前不可利用，但可能存在其他绕过方式。需要全面探索所有可能修改签到状态的接口。

## What Changes
- 探索Go源码中发现的新API域名和端点
- 对 `/qr/updateqrstatus`（mooc1-api域名）进行专项安全测试
- 对 `/mooc-ans/` 路径下的签到相关端点进行枚举和测试
- 重新测试 `/newsign/updateSignStatus` 在不同域名下的行为
- 测试 `inf_enc` 签名参数对API权限的影响
- 探索 `mooc2-ans.chaoxing.com` 域名下的签到接口
- 测试PC端接口在 `mooc1.chaoxing.com` 域名下的行为
- 对所有发现的端点进行学生端越权测试

## Impact
- Affected APIs:
  - 新发现: `mooc1-api.chaoxing.com/qr/updateqrstatus`
  - 新发现: `mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus`
  - 新发现: `mooc1.chaoxing.com/mooc-ans/qr/produce`
  - 新发现: `mooc1.chaoxing.com/mooc-ans/qr/getqrstatus`
  - 新发现: `mooc2-ans.chaoxing.com` 域名下可能存在的签到接口
  - 已知: `mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2`
  - 已知: `mobilelearn.chaoxing.com/newsign/updateSignStatus`
  - 已知: `mobilelearn.chaoxing.com/widget/sign/pcTeaSignController/updateSignStatus2`
- Test accounts: 教师 19712720708/3.1415926Cpy (puid=402644510), 学生 18436633997/3.1415926Cpy (puid=431407443)
- Course: courseId=257485372, classId=132821141

## 已知但未充分测试的攻击面

### 1. mooc1-api域名下的签到接口
Go源码中发现 `mooc1-api.chaoxing.com/qr/updateqrstatus`，这是二维码签到的核心接口。
- 参数: uuid, clazzId, courseId, qrcEnc, cpi, objectId, liveDetectionStatus, signt, signk, cxtime, cxcid
- 问题: 学生能否伪造qrcEnc参数完成签到？

### 2. mooc-ans路径
`mooc1-api.chaoxing.com/mooc-ans/` 路径下可能存在更多签到相关端点。
- `/mooc-ans/facephoto/clientfacecheckstatus` — 人脸签到
- `/mooc-ans/qr/produce` — 二维码生成
- `/mooc-ans/qr/getqrstatus` — 二维码状态

### 3. inf_enc签名参数
Go源码中 `InfEncSign` 函数为移动端API参数添加签名。某些API可能需要此签名才能调用。
- 如果签名算法可逆向，学生可能伪造签名调用教师接口

### 4. mooc2-ans域名
`mooc2-ans.chaoxing.com` 域名下可能存在未测试的签到接口。

### 5. PC端JSON绕过的进一步利用
之前发现 `Content-Type: application/json` 绕过了PC端权限中间件，但因参数解析问题不可利用。
- 如果能找到正确的JSON参数格式，可能真正修改数据

## ADDED Requirements

### Requirement: 多域名签到接口全面枚举
系统 SHALL 对所有已发现的域名下的签到相关接口进行系统性枚举和测试。

#### Scenario: mooc1-api域名签到接口测试
- **WHEN** 对 `mooc1-api.chaoxing.com` 域名下的签到接口进行测试
- **THEN** 应发现并记录所有可用端点及其权限要求

#### Scenario: mooc-ans路径端点枚举
- **WHEN** 对 `/mooc-ans/` 路径下的签到相关端点进行枚举
- **THEN** 应发现并记录所有可用端点

#### Scenario: mooc2-ans域名端点枚举
- **WHEN** 对 `mooc2-ans.chaoxing.com` 域名下的签到接口进行测试
- **THEN** 应发现并记录所有可用端点

### Requirement: /qr/updateqrstatus 专项安全测试
系统 SHALL 对 `/qr/updateqrstatus` 接口进行专项安全测试。

#### Scenario: 学生直接调用updateqrstatus
- **WHEN** 学生尝试直接调用 `/qr/updateqrstatus` 修改签到状态
- **THEN** 验证是否需要qrcEnc参数以及该参数是否可伪造

#### Scenario: qrcEnc参数伪造
- **WHEN** 学生尝试伪造qrcEnc参数
- **THEN** 验证qrcEnc的生成算法是否可逆向

#### Scenario: 签到状态直接修改
- **WHEN** 学生通过updateqrstatus接口提交签到
- **THEN** 验证是否可以绕过二维码验证直接完成签到

### Requirement: inf_enc签名算法逆向
系统 SHALL 分析inf_enc签名算法是否可被学生伪造。

#### Scenario: 签名算法分析
- **WHEN** 分析Go源码中的InfEncSign函数
- **THEN** 确定签名算法的输入参数和生成逻辑

#### Scenario: 签名伪造测试
- **WHEN** 学生使用伪造的inf_enc签名调用教师接口
- **THEN** 验证签名是否通过验证

### Requirement: PC端JSON绕过深度利用
系统 SHALL 继续尝试利用PC端JSON Content-Type绕过。

#### Scenario: JSON参数格式探索
- **WHEN** 尝试不同的JSON参数格式（嵌套、数组、下划线命名等）
- **THEN** 验证是否存在Controller可以正确解析的JSON格式

#### Scenario: 多域名PC端接口测试
- **WHEN** 在mooc1-api域名下测试PC端接口
- **THEN** 验证不同域名下的权限中间件是否存在差异

### Requirement: 签到状态修改漏洞全面验证
系统 SHALL 对所有发现的可能修改签到状态的路径进行实际验证。

#### Scenario: 修改前后状态对比
- **WHEN** 学生尝试通过任何路径修改签到状态
- **THEN** 必须通过V2 API查询验证修改是否真正生效

#### Scenario: 多场景覆盖
- **WHEN** 在不同签到类型（二维码、位置、手势、签到码、普通）下测试
- **THEN** 验证漏洞是否在所有签到类型下都存在
