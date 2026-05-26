# 学习通移动端暴露密钥与签名算法安全审计 Spec

## Why
学习通移动端客户端代码中硬编码了大量加密密钥、签名盐值、全局Token和签名算法，这些信息可通过APK反编译轻易获取，严重削弱了服务端安全机制的有效性。需系统性审计所有暴露的密钥和签名算法，评估每个泄露点的安全影响。

## What Changes
- 系统性审计代码库中所有学习通相关的硬编码密钥、Token、签名盐值
- 对每个泄露点进行安全影响评估
- 验证泄露密钥是否可被实际利用（通过构造请求测试）
- 生成完整的安全审计报告

## Impact
- Affected specs: assess-cloud-drive-idor, assess-group-drive-idor（已有评估发现部分密钥泄露）
- Affected code: api/xuexitong/ 目录下所有文件

## ADDED Requirements

### Requirement: 硬编码密钥全面盘点
系统 SHALL 对代码库中所有学习通相关的硬编码安全凭证进行全面盘点。

#### Scenario: 密钥清单完整性
- **WHEN** 审计完成
- **THEN** 报告应包含所有硬编码密钥的名称、值、所在文件和行号、用途、风险等级

### Requirement: AES登录加密密钥安全评估
系统 SHALL 评估AES-CBC加密密钥`u2oh6Vu^HWe4_AES`泄露的安全影响。

#### Scenario: 密钥用于登录加密
- **WHEN** 攻击者获取该密钥
- **THEN** 可构造合法的登录请求，实现自动化批量登录

### Requirement: schild签名算法安全评估
系统 SHALL 评估schild签名算法泄露的安全影响。

#### Scenario: 签名算法被逆向
- **WHEN** 攻击者获取schild签名算法（含硬编码盐值`ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu`）
- **THEN** 可伪造任意设备的合法User-Agent签名，绕过设备指纹校验

### Requirement: 视频学时提交签名盐值安全评估
系统 SHALL 评估视频/音频学时提交签名盐值`d_yHJ!$pdA~5`泄露的安全影响。

#### Scenario: 盐值用于学时提交签名
- **WHEN** 攻击者获取该盐值
- **THEN** 可伪造视频观看记录，实现刷课

### Requirement: 人脸验证签名盐值安全评估
系统 SHALL 评估人脸验证签名盐值`uWwjeEKsri`泄露的安全影响。

#### Scenario: 盐值用于人脸验证请求签名
- **WHEN** 攻击者获取该盐值（`md5(puid + "uWwjeEKsri")`）
- **THEN** 可伪造人脸验证请求，绕过人脸识别校验

### Requirement: 阅读任务签名盐值安全评估
系统 SHALL 评估阅读任务签名盐值`NrRzLDpWB2JkeodIVAn4`泄露的安全影响。

#### Scenario: 盐值用于阅读任务签名
- **WHEN** 攻击者获取该盐值
- **THEN** 可伪造阅读任务完成记录

### Requirement: 移动端全局Token安全评估
系统 SHALL 评估全局Token`4faa8662c59590c6f43ae9fe5b002b42`泄露的安全影响。

#### Scenario: Token用于移动端API认证
- **WHEN** 攻击者获取该Token
- **THEN** 可构造合法的移动端API请求（需配合inf_enc签名）

### Requirement: DES签名密钥安全评估
系统 SHALL 评估DES签名密钥`Z(AfY@XS`泄露的安全影响。

#### Scenario: 密钥用于inf_enc签名计算
- **WHEN** 攻击者获取该密钥
- **THEN** 可自行计算inf_enc签名，使签名机制完全失效

### Requirement: 验证码系统IV泄露安全评估
系统 SHALL 评估验证码系统固定IV`cdd9bfb9e7805d0d2d5f1ad4498f70e1`泄露的安全影响。

#### Scenario: IV用于验证码校验
- **WHEN** 攻击者获取该IV
- **THEN** 可能影响验证码校验的安全性

### Requirement: 考试签名算法安全评估
系统 SHALL 评估考试签名算法`GetExamSignature`泄露的安全影响。

#### Scenario: 算法用于考试防作弊签名
- **WHEN** 攻击者获取该算法
- **THEN** 可伪造考试操作签名，绕过防作弊机制

### Requirement: 各泄露密钥实际可利用性验证
系统 SHALL 对每个泄露密钥进行实际利用性验证测试。

#### Scenario: 构造请求验证密钥有效性
- **WHEN** 使用泄露的密钥构造请求
- **THEN** 验证服务端是否接受该请求，确认密钥是否仍为有效值

### Requirement: 安全审计报告生成
系统 SHALL 生成完整的密钥泄露安全审计报告。

#### Scenario: 报告内容完整性
- **WHEN** 审计完成
- **THEN** 报告应包含：密钥清单、每个密钥的安全影响分析、实际可利用性验证结果、综合风险评估、修复建议

## MODIFIED Requirements

### Requirement: 现有安全评估范围扩展
在已完成个人云盘和小组云盘安全评估的基础上，将评估范围扩展至移动端密钥泄露审计。

## REMOVED Requirements

无移除需求。

---

## 附录：已发现的硬编码安全凭证清单

| 编号 | 凭证名称 | 值 | 文件位置 | 用途 |
|---|---|---|---|---|
| K1 | AES登录加密密钥 | `u2oh6Vu^HWe4_AES` | XueXiTongLoginApi.go | 登录请求AES-CBC加密 |
| K2 | schild签名盐值 | `ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu` | XueXiTongLoginApi.go L93 | 移动端UA签名 |
| K3 | 视频学时签名盐值 | `d_yHJ!$pdA~5` | XueXiTongCardApi.go L177, XueXiTongAudioApi.go L21 | 视频/音频学时提交enc签名 |
| K4 | 人脸验证签名盐值 | `uWwjeEKsri` | XueXiTongFaceApi.go L93 | 人脸验证enc签名(md5(puid+salt)) |
| K5 | 阅读任务签名盐值 | `NrRzLDpWB2JkeodIVAn4` | XueXiTongReadApi.go L112 | 阅读任务签名(加盐MD5) |
| K6 | 移动端全局Token | `4faa8662c59590c6f43ae9fe5b002b42` | XueXiTongFaceApi.go L95, XueXiTongBBsApi.go L271/L393 | 移动端API认证 |
| K7 | DES签名密钥 | `Z(AfY@XS` | XueXiTongBBsApi.go L458 | inf_enc签名计算 |
| K8 | 验证码固定IV | `cdd9bfb9e7805d0d2d5f1ad4498f70e1` | XueXiTongVerCodeApi.go L450 | 验证码校验参数 |
| K9 | 考试签名算法 | GetExamSignature | XueXiTongExamApi.go L695 | 考试防作弊签名 |
| K10 | schild签名算法 | MobileUASign | XueXiTongLoginApi.go L90 | UA签名计算(含K2盐值) |
| K11 | 多个硬编码schild值 | `5e5510ce86e012a7f489e7c488fc17b4`等 | 多文件注释中 | 预计算的UA签名值 |

## 附录：签名算法详情

### A1. schild签名算法 (MobileUASign)
```
输入: model, locale, version, build, imei
拼接: "(schild:ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu)" + "(device:{model})" + "Language/{locale}" + "com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}" + "(@Kalimdor)_{imei}"
输出: md5(拼接字符串)
```

### A2. 视频学时enc签名
```
输入: classId, userId, jobId, objectId, playingTime*1000, duration*1000, clipTime
拼接: "[{classId}][{userId}][{jobId}][{objectId}][{playingTime}][d_yHJ!$pdA~5][{duration}][{clipTime}]"
输出: md5(拼接字符串)
```

### A3. 人脸验证enc签名
```
输入: puid
拼接: puid + "uWwjeEKsri"
输出: md5(拼接字符串)
```

### A4. 阅读任务签名
```
输入: 请求参数JSON
步骤: 1. 按key排序拼接值 2. 末尾加盐 "NrRzLDpWB2JkeodIVAn4" 3. MD5
输出: md5(排序拼接值 + "NrRzLDpWB2JkeodIVAn4")
```

### A5. inf_enc签名算法
```
输入: 请求参数 + DESKey
步骤: 1. 按指定顺序拼接参数 2. 末尾追加 "&DESKey=Z(AfY@XS" 3. MD5
输出: md5(参数排序拼接 + "&DESKey=Z(AfY@XS")
```
