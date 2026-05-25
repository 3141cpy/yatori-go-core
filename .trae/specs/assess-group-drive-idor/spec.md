# 学习通小组云盘越权访问安全评估 Spec

## Why
学习通小组云盘（ChaoXingGroupDrive）使用与个人云盘完全不同的API体系（groupweb.chaoxing.com / noteyd.chaoxing.com / groupyd.chaoxing.com），其认证方式仅依赖Cookie+Referer（PC端）或硬编码Token+inf_enc签名（移动端），核心标识参数`bbsid`（小组ID）作为直接对象引用，且移动端API暴露了硬编码的DES签名密钥`Z(AfY@XS`和全局Token`4faa8662c59590c6f43ae9fe5b002b42`，存在严重的越权访问风险。

## What Changes
- 对小组云盘三个API域名（groupweb / noteyd / groupyd）进行系统性越权安全测试
- 验证跨组访问（非组成员访问他人小组云盘）的IDOR漏洞
- 验证移动端硬编码Token和签名密钥带来的安全风险
- 验证文件下载接口是否存在无权限校验的直链访问
- 生成完整的安全评估报告

## Impact
- Affected specs: assess-cloud-drive-idor（个人云盘评估已完成，本评估为扩展范围）
- Affected code: api/xuexitong/XueXiTongBBsApi.go（暴露硬编码密钥和Token）
- Affected APIs: groupweb.chaoxing.com, noteyd.chaoxing.com, groupyd.chaoxing.com

## ADDED Requirements

### Requirement: 小组云盘环境准备与bbsid获取
系统 SHALL 验证测试账号能否正常访问小组云盘功能并获取有效的bbsid。

#### Scenario: 账号登录并获取小组列表
- **WHEN** 使用两个测试账号登录并访问小组功能
- **THEN** 获取各账号所属小组的bbsid，记录小组成员关系

#### Scenario: 创建测试用小组
- **WHEN** 使用测试账号创建新的测试小组
- **THEN** 获得可用于越权测试的bbsid，确保一个账号是成员而另一个不是

### Requirement: 跨组文件列表越权测试（groupweb.chaoxing.com）
系统 SHALL 验证文件列表API是否存在跨组IDOR漏洞。

#### Scenario: 非组成员列出小组文件
- **WHEN** 使用非组成员的Cookie+Referer，配合目标小组的bbsid，请求`/pc/resource/getResourceList`
- **THEN** 验证是否能列出目标小组的文件和文件夹

#### Scenario: 非组成员列出小组文件夹内容
- **WHEN** 使用非组成员的认证信息，配合目标小组的bbsid和folderId，请求`/pc/resource/getResourceList`
- **THEN** 验证是否能浏览目标小组的子目录内容

### Requirement: 跨组文件下载越权测试（noteyd.chaoxing.com）
系统 SHALL 验证文件下载API是否存在无权限校验的直链访问漏洞。

#### Scenario: 非组成员获取文件下载链接
- **WHEN** 使用非组成员的Cookie，请求`/screen/note_note/files/status/{fileId}`
- **THEN** 验证是否能获取目标小组文件的下载直链

#### Scenario: 直接访问下载直链
- **WHEN** 使用非组成员的Cookie访问下载直链
- **THEN** 验证是否能成功下载目标小组的文件

### Requirement: 跨组文件上传越权测试
系统 SHALL 验证文件上传流程是否存在跨组越权风险。

#### Scenario: 非组成员获取上传配置
- **WHEN** 使用非组成员的Cookie请求`/pc/files/getUploadConfig`
- **THEN** 验证是否能获取上传Token和puid

#### Scenario: 非组成员向他人小组上传文件
- **WHEN** 使用非组成员的认证信息，配合目标小组的bbsid，请求`/pc/resource/addResource`
- **THEN** 验证是否能向目标小组添加文件资源

### Requirement: 跨组文件删除越权测试
系统 SHALL 验证文件删除API是否存在跨组IDOR漏洞。

#### Scenario: 非组成员删除他人小组文件
- **WHEN** 使用非组成员的Cookie，配合目标小组的bbsid和recIds，请求`/pc/resource/deleteResourceFile`
- **THEN** 验证是否能删除目标小组的文件（探测性测试，不实际执行）

#### Scenario: 非组成员删除他人小组文件夹
- **WHEN** 使用非组成员的Cookie，配合目标小组的bbsid和folderIds，请求`/pc/resource/deleteResourceFolder`
- **THEN** 验证是否能删除目标小组的文件夹（探测性测试）

### Requirement: 跨组文件夹管理越权测试
系统 SHALL 验证文件夹管理API是否存在跨组越权风险。

#### Scenario: 非组成员在他人小组创建文件夹
- **WHEN** 使用非组成员的Cookie，配合目标小组的bbsid，请求`/pc/resource/addResourceFolder`
- **THEN** 验证是否能在目标小组创建文件夹

#### Scenario: 非组成员重命名他人小组文件夹
- **WHEN** 使用非组成员的Cookie，配合目标小组的bbsid和folderId，请求`/pc/resource/updateResourceFolderName`
- **THEN** 验证是否能修改目标小组的文件夹名称

### Requirement: 移动端API硬编码密钥安全测试（groupyd.chaoxing.com）
系统 SHALL 验证移动端API因硬编码Token和签名密钥带来的安全风险。

#### Scenario: 使用硬编码Token和签名密钥伪造请求
- **WHEN** 使用从客户端代码提取的硬编码Token`4faa8662c59590c6f43ae9fe5b002b42`和DES密钥`Z(AfY@XS`，构造inf_enc签名，请求`groupyd.chaoxing.com/apis/topic/getTopic`
- **THEN** 验证是否能成功访问其他用户的讨论数据

#### Scenario: 篡改puid参数访问他人数据
- **WHEN** 使用硬编码Token和签名密钥，将puid参数替换为其他用户的puid
- **THEN** 验证是否能访问其他用户的讨论数据

### Requirement: bbsid可枚举性测试
系统 SHALL 评估bbsid的可预测性和枚举风险。

#### Scenario: bbsid格式分析
- **WHEN** 分析已获取的bbsid格式
- **THEN** 判断bbsid是否为连续数字、是否可被暴力枚举

#### Scenario: bbsid遍历测试
- **WHEN** 对bbsid进行递增/递减遍历请求
- **THEN** 验证是否能访问到非预期的小组资源

### Requirement: 权限提升测试
系统 SHALL 验证小组云盘的权限体系是否可被绕过。

#### Scenario: 普通成员执行管理员操作
- **WHEN** 使用普通成员的认证信息，尝试执行需要管理员权限的操作（如addManager、dismiss等）
- **THEN** 验证权限校验是否生效

### Requirement: 安全评估报告生成
系统 SHALL 生成完整的小组云盘安全评估报告。

#### Scenario: 报告内容完整性
- **WHEN** 所有安全测试完成后
- **THEN** 报告应包含：测试概述、三个API域名的测试结果、移动端硬编码密钥风险分析、与个人云盘漏洞对比、技术原因分析、影响范围评估、修复建议

## MODIFIED Requirements

### Requirement: 现有安全评估范围扩展
在已完成个人云盘安全评估的基础上，将评估范围扩展至小组云盘体系。个人云盘评估结论保持不变。

## REMOVED Requirements

无移除需求。

---

## 附录：小组云盘 vs 个人云盘安全架构对比

| 维度 | 个人云盘 | 小组云盘 |
|---|---|---|
| **认证方式** | Cookie + _token参数 | Cookie + Referer（PC端）/ 硬编码Token + inf_enc签名（移动端） |
| **核心标识** | puid（用户ID） | bbsid（小组ID） |
| **Token安全** | _token与puid绑定（部分校验） | 移动端Token硬编码（全局固定） |
| **签名密钥** | 无 | DES密钥硬编码在客户端 |
| **文件列表API** | /api/getMyDirAndFiles | /pc/resource/getResourceList |
| **文件下载API** | /api/download | /screen/note_note/files/status/{fileId} |
| **文件删除API** | /api/delete | /pc/resource/deleteResourceFile |
| **权限体系** | 无（个人空间） | UserAuth权限体系（但可能未强制校验） |

## 附录：待测试的API端点清单

### A. groupweb.chaoxing.com（PC端API）
| 编号 | 端点 | 方法 | 越权风险参数 | 风险等级 |
|---|---|---|---|---|
| A1 | /pc/resource/getResourceList | GET | bbsid, folderId | 极高 |
| A2 | /pc/resource/addResource | GET | bbsid, pid, params | 高 |
| A3 | /pc/resource/addResourceFolder | GET | bbsid, name, pid | 高 |
| A4 | /pc/resource/updateResourceFolderName | GET | bbsid, folderId, name | 中 |
| A5 | /pc/resource/moveResource | GET | bbsid, folderIds/recIds, targetId | 高 |
| A6 | /pc/resource/deleteResourceFile | GET | bbsid, recIds | 极高 |
| A7 | /pc/resource/deleteResourceFolder | GET | bbsid, folderIds | 极高 |

### B. noteyd.chaoxing.com（下载API）
| 编号 | 端点 | 方法 | 越权风险参数 | 风险等级 |
|---|---|---|---|---|
| B1 | /screen/note_note/files/status/{fileId} | POST | fileId | 极高 |
| B2 | /pc/files/getUploadConfig | GET | 无（仅Cookie） | 中 |

### C. groupyd.chaoxing.com（移动端API）
| 编号 | 端点 | 方法 | 越权风险参数 | 风险等级 |
|---|---|---|---|---|
| C1 | /apis/topic/getTopic | POST | puid, topicId, token(硬编码) | 极高 |
| C2 | /apis/invitation/addReply | POST | puid, topicUUID, token(硬编码) | 高 |

## 附录：硬编码安全凭证

| 凭证 | 值 | 来源 |
|---|---|---|
| 移动端Token | 4faa8662c59590c6f43ae9fe5b002b42 | XueXiTongBBsApi.go L271, L393 |
| DES签名密钥 | Z(AfY@XS | XueXiTongBBsApi.go L458 |
