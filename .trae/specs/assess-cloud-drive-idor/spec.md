# 学习通云盘越权访问安全评估 Spec

## Why
学习通App端云盘功能存在潜在的越权访问风险（IDOR - 不安全的直接对象引用），多个云盘API端点将`puid`（用户ID）作为URL参数直接传递，服务端可能未对请求者身份与资源归属进行严格校验，导致用户可通过篡改`puid`参数访问他人云盘内容。

## What Changes
- 对云盘功能进行系统性安全测试，验证IDOR越权访问漏洞是否存在
- 编写自动化安全测试脚本，覆盖云盘所有关键API端点
- 生成完整的安全评估报告，包含漏洞验证步骤、技术原因分析和修复建议

## Impact
- Affected specs: 学习通云盘API安全评估
- Affected code: api/xuexitong/XueXiTongFaceApi.go（云盘token获取）、学习通API端点技术报告.md（云盘API章节）

## ADDED Requirements

### Requirement: 云盘Token获取越权测试
系统 SHALL 验证云盘Token获取接口是否存在越权风险。

#### Scenario: 使用账号1获取Token后尝试访问账号2资源
- **WHEN** 使用账号1登录获取云盘Token
- **THEN** 验证该Token是否与puid绑定，是否能用于访问其他puid的资源

### Requirement: 云盘用户信息接口越权测试
系统 SHALL 验证获取用户信息接口是否存在IDOR漏洞。

#### Scenario: 使用账号1的认证信息查询账号2的用户信息
- **WHEN** 使用账号1的Cookie和Token，将puid参数替换为账号2的puid，请求`/api/info`接口
- **THEN** 验证是否能成功获取账号2的云盘用户信息

#### Scenario: 使用账号1的认证信息查询账号2的磁盘容量
- **WHEN** 使用账号1的Cookie和Token，将puid参数替换为账号2的puid，请求`/api/getUserDiskCapacity`接口
- **THEN** 验证是否能成功获取账号2的云盘磁盘容量信息

### Requirement: 云盘文件列表越权测试（核心风险点）
系统 SHALL 验证列出目录文件接口是否存在IDOR漏洞，这是最关键的越权风险点。

#### Scenario: 使用账号1的认证信息列出账号2的云盘文件
- **WHEN** 使用账号1的Cookie和Token，将puid参数替换为账号2的puid，请求`/api/getMyDirAndFiles`接口
- **THEN** 验证是否能成功列出账号2的云盘文件目录和文件列表

#### Scenario: 使用账号1的认证信息访问账号2的特定文件夹
- **WHEN** 使用账号1的认证信息，结合账号2的puid和fldid参数，请求`/api/getMyDirAndFiles`接口
- **THEN** 验证是否能成功浏览账号2的云盘子目录内容

### Requirement: 云盘文件删除越权测试
系统 SHALL 验证删除文件接口是否存在越权风险。

#### Scenario: 使用账号1的认证信息尝试删除账号2的文件
- **WHEN** 使用账号1的Cookie和Token，将puid参数替换为账号2的puid，请求`/api/delete`接口
- **THEN** 验证是否能成功删除账号2的云盘文件（仅测试不实际执行删除操作，通过分析响应判断）

### Requirement: 云盘文件上传越权测试
系统 SHALL 验证文件上传接口是否存在越权风险。

#### Scenario: 使用账号1的认证信息尝试向账号2的云盘上传文件
- **WHEN** 使用账号1的Cookie和Token，将puid参数替换为账号2的puid，请求`/opt/createfilenew`或`/upload`接口
- **THEN** 验证是否能成功向账号2的云盘上传文件（仅测试不实际上传，通过分析响应判断）

### Requirement: Token与puid绑定关系验证
系统 SHALL 验证云盘Token是否与特定puid绑定，还是全局通用。

#### Scenario: 使用账号1获取的Token配合账号2的puid请求
- **WHEN** 使用账号1登录获取的_token，配合账号2的puid参数请求云盘API
- **THEN** 验证服务端是否校验Token与puid的绑定关系

#### Scenario: 跨账号Token替换测试
- **WHEN** 使用账号2登录获取的_token，配合账号1的puid参数请求云盘API
- **THEN** 验证服务端是否拒绝不匹配的Token-puid组合

### Requirement: 安全评估报告生成
系统 SHALL 生成完整的安全评估报告。

#### Scenario: 报告内容完整性
- **WHEN** 所有安全测试完成后
- **THEN** 报告应包含：测试概述、测试环境、详细测试步骤、漏洞验证结果、技术原因分析、影响范围评估、修复建议

## MODIFIED Requirements

### Requirement: 现有云盘API实现
现有代码中云盘Token获取函数`GetFaceUpLoadToken()`仅用于人脸验证场景，需扩展为完整的云盘安全测试工具，覆盖所有云盘API端点的越权测试。

## REMOVED Requirements

无移除需求。

---

## 附录：待测试的云盘API端点清单

| 编号 | 端点 | 方法 | 越权风险参数 | 风险等级 |
|---|---|---|---|---|
| 10.1 | `/api/token/uservalid` | GET | 无（仅Cookie认证） | 低 |
| 10.2 | `/api/info?puid={puid}&_token={token}` | GET | puid | 高 |
| 10.3 | `/api/getUserDiskCapacity?puid={puid}&_token={token}` | GET | puid | 中 |
| 10.4 | `/api/getMyDirAndFiles?puid={puid}&fldid={fldid}&_token={token}` | GET | puid | 极高 |
| 10.5 | `/opt/createfilenew` | POST | puid | 高 |
| 10.7 | `/api/notification/rsyncsucss` | POST | puid | 高 |
| 10.8 | `/api/crcstatus?puid={puid}&crc={crc}&_token={token}` | GET | puid | 中 |
| 10.10 | `/api/delete` | POST | puid, resids | 极高 |
| 10.11 | `/upload` | POST | puid | 高 |

## 附录：测试账号信息

| 账号 | 手机号 | 用途 |
|---|---|---|
| 账号1 | 19312994130 | 主测试账号（攻击方模拟） |
| 账号2 | 15034188203 | 目标账号（被访问方模拟） |
