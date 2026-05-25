# 学习通云盘 Token 与 PUID 关系研究 Spec

## Why
访问学习通（超星）云盘需要理解其认证体系中 token 和 puid 的关系以及 token 的生成算法，以便正确构造 API 请求完成文件操作。目前缺乏对这套认证机制的系统性研究文档。

## What Changes
- 梳理学习通云盘认证体系中的关键凭据类型及其关系
- 分析旧版云盘 API（pan-yz.chaoxing.com）的 `_token` + `puid` 机制
- 分析新版云盘 API（noteyd.chaoxing.com）的 `_token` + `puid` 机制
- 研究登录加密算法（AES-CBC）及密钥
- 研究 `p_auth_token`（JWT）的结构与生成
- 研究各 Cookie 字段（UID、uf、vc 等）的作用
- 形成完整的认证流程图和 token 生成算法说明

## Impact
- Affected specs: 学习通云盘访问认证
- Affected code: 任何需要调用学习通云盘 API 的客户端程序

---

## ADDED Requirements

### Requirement: 学习通云盘认证体系全景梳理

系统 SHALL 提供学习通云盘访问过程中涉及的所有认证凭据的完整梳理，包括但不限于：

1. **Cookie 类凭据**：`UID`、`uf`、`vc`、`vc2`、`vc3`、`xxtenc`、`fid`、`_d`、`tl`、`jrose`、`DSSTASH_LOG`、`source`、`spaceFidEnc`、`spaceFid`、`spaceRoleId`
2. **Token 类凭据**：`_token`（旧版云盘 API）、`_token`（新版云盘 API）、`cx_p_token`、`p_auth_token`（JWT）
3. **用户标识**：`puid`（即 UID，用户唯一 ID）

#### Scenario: 用户通过 Cookie 登录后访问旧版云盘 API
- **WHEN** 用户携带 `UID` 和 `uf` Cookie 访问 `https://pan-yz.chaoxing.com/api/token/uservalid`
- **THEN** 服务端验证 Cookie 有效性，返回 `{ "result": true, "_token": "xxx" }`
- **AND** 后续所有旧版云盘 API 请求需携带 `puid=<UID>&_token=<返回的_token>`

#### Scenario: 用户通过 Cookie 登录后访问新版云盘 API
- **WHEN** 用户携带完整 Cookie 访问 `https://noteyd.chaoxing.com/pc/files/getUploadConfig`
- **THEN** 服务端返回 `{ "result": 1, "msg": { "puid": 12345, "token": "xxx" } }`
- **AND** 上传文件时需携带 `_token` 和 `puid` 参数

### Requirement: 旧版云盘 API（pan-yz.chaoxing.com）的 _token 与 puid 机制

系统 SHALL 详细说明旧版云盘 API 中 `_token` 和 `puid` 的关系：

1. **puid 的来源**：`puid` 就是用户的 `UID`（从 Cookie 中获取），是用户的唯一数字标识
2. **_token 的获取**：通过 `GET https://pan-yz.chaoxing.com/api/token/uservalid` 接口获取，该接口依赖 Cookie 中的 `UID` 和 `uf` 进行身份验证
3. **_token 的性质**：服务端生成的有状态 token（opaque token），存储在服务端缓存/数据库中，与 puid 绑定
4. **_token 的有效期**：与 Cookie 会话绑定，会话过期则 _token 失效
5. **使用方式**：所有旧版 API 请求均需携带 `puid` 和 `_token` 作为查询参数，例如：
   - `GET /api/info?puid={puid}&_token={_token}`
   - `GET /api/getMyDirAndFiles?puid={puid}&fldid={fldid}&_token={_token}`
   - `POST /api/delete` body: `puid={puid}&resids={id}&_token={_token}`
   - `POST /api/notification/rsyncsucss` body: `puid={puid}&rf={timemil}&_token={_token}`

#### Scenario: _token 验证失败
- **WHEN** 用户使用过期或无效的 `_token` 请求旧版云盘 API
- **THEN** 服务端返回 `{ "result": false }` 表示验证失败

### Requirement: 新版云盘 API（noteyd.chaoxing.com）的 _token 与 puid 机制

系统 SHALL 详细说明新版云盘 API 中 `_token` 和 `puid` 的关系：

1. **puid 的来源**：通过 `GET https://noteyd.chaoxing.com/pc/files/getUploadConfig` 接口返回，值与用户 UID 相同
2. **_token 的获取**：同一接口返回，与 puid 配对出现
3. **使用场景**：主要用于文件上传 `POST https://pan-yz.chaoxing.com/upload`，需在 form-data 中携带 `_token` 和 `puid`
4. **新版 API 认证方式**：新版 API（noteyd.chaoxing.com）主要通过 Cookie 进行认证，而非查询参数中的 `_token`

#### Scenario: 获取上传配置
- **WHEN** 用户携带有效 Cookie 请求 `getUploadConfig`
- **THEN** 返回 `{ "result": 1, "msg": { "puid": 12345, "token": "abc123" } }`

### Requirement: 登录加密算法研究

系统 SHALL 详细说明学习通登录过程中的加密算法：

1. **登录接口**：`POST https://passport2.chaoxing.com/fanyalogin`
2. **加密方式**：AES-CBC 加密
3. **加密密钥**：`u2oh6Vu^HWe4_AES`（硬编码在前端 JS 中）
4. **IV 向量**：取密钥的前 16 字节，即 `u2oh6Vu^HWe4_AES` 的前 16 字节
5. **填充方式**：PKCS7 填充
6. **加密对象**：用户名（uname）和密码（password）分别独立加密
7. **编码方式**：加密后的密文进行 Base64 编码后传输
8. **传输格式**：multipart/form-data，字段包括 `uname`（加密后）、`password`（加密后）、`t`（固定为 "true"）

#### Scenario: AES 加密用户名
- **WHEN** 用户名为 "testuser"
- **THEN** 使用 AES-CBC 算法，密钥 `u2oh6Vu^HWe4_AES`，IV 为密钥前 16 字节，PKCS7 填充，对 "testuser" 加密后 Base64 编码

#### Scenario: 登录成功
- **WHEN** 使用正确的加密后用户名和密码请求 `fanyalogin`
- **THEN** 服务端返回 Set-Cookie 头，包含 `UID`、`uf`、`vc`、`cx_p_token`、`p_auth_token` 等 Cookie

### Requirement: p_auth_token（JWT）结构分析

系统 SHALL 详细说明 `p_auth_token` 的 JWT 结构：

1. **格式**：标准 JWT 三段式 `Header.Payload.Signature`
2. **Header**：`{ "alg": "HS256", "typ": "JWT" }`
3. **Payload** 包含以下字段：
   - `uid`：用户唯一标识（字符串形式，如 "205386953"）
   - `loginTime`：登录时间戳（毫秒级，如 1736931383256）
   - `exp`：过期时间戳（秒级 Unix 时间戳）
4. **签名算法**：HMAC-SHA256，密钥为服务端持有
5. **有效期**：约 18.5 天（从 loginTime 到 exp 的间隔）
6. **作用**：用于主站 i.chaoxing.com 的身份认证

#### Scenario: 解码 p_auth_token
- **WHEN** 对 `p_auth_token` 进行 Base64URL 解码
- **THEN** Payload 中可看到 `uid`、`loginTime`、`exp` 字段
- **AND** `uid` 与 Cookie 中的 `UID` 值相同

### Requirement: cx_p_token 分析

系统 SHALL 说明 `cx_p_token` 的特征：

1. **格式**：32 位十六进制字符串（如 "af599aebfd327529886ea6989d7e000e"）
2. **性质**：服务端生成的 opaque token（有状态），类似 MD5 哈希格式
3. **作用**：用于超星平台内部的身份验证，与 Cookie 中的其他字段配合使用
4. **有效期**：与 Cookie 会话绑定

### Requirement: Cookie 字段作用梳理

系统 SHALL 详细说明各 Cookie 字段的作用：

| Cookie 字段 | 作用说明 |
|---|---|
| `UID` | 用户唯一数字 ID，即 puid |
| `uf` | 用户指纹（user fingerprint），用于身份验证的关键 Cookie |
| `vc` / `vc2` / `vc3` | 验证码/校验值，不同版本的会话验证凭据 |
| `xxtenc` | 加密的会话标识 |
| `fid` | 用户所属学校/机构 ID |
| `_d` | 设备标识时间戳 |
| `tl` | 登录类型标识 |
| `jrose` | 服务端路由标识（格式：`HASH.ans`） |
| `DSSTASH_LOG` | 日志追踪标识（格式：`C_{fid}-UN_{?}-US_{uid}-T_{timestamp}`） |
| `cx_p_token` | 超星平台认证 token |
| `p_auth_token` | JWT 格式的认证 token |
| `spaceFid` / `spaceFidEnc` | 用户云盘空间 ID 及其加密形式 |
| `spaceRoleId` | 用户在云盘空间中的角色 ID |

### Requirement: 完整认证流程图

系统 SHALL 提供从登录到访问云盘的完整认证流程：

```
1. 登录阶段
   ├─ 前端：使用 AES-CBC（密钥 u2oh6Vu^HWe4_AES）加密用户名和密码
   ├─ 请求：POST https://passport2.chaoxing.com/fanyalogin
   │         Content-Type: multipart/form-data
   │         Body: uname={AES加密}, password={AES加密}, t=true
   └─ 响应：Set-Cookie 返回 UID, uf, vc, cx_p_token, p_auth_token 等

2. 获取旧版云盘 Token
   ├─ 请求：GET https://pan-yz.chaoxing.com/api/token/uservalid
   │         Cookie: UID=xxx; uf=xxx
   └─ 响应：{ "result": true, "_token": "xxx" }
             _token 与 puid(=UID) 绑定，后续旧版 API 请求需携带

3. 获取新版云盘 Token
   ├─ 请求：GET https://noteyd.chaoxing.com/pc/files/getUploadConfig
   │         Cookie: 完整 Cookie 字符串
   └─ 响应：{ "result": 1, "msg": { "puid": 12345, "token": "xxx" } }
             用于文件上传时的身份验证

4. 访问云盘资源
   ├─ 旧版 API：URL 查询参数携带 puid + _token
   │   例：GET /api/getMyDirAndFiles?puid={UID}&_token={_token}&...
   ├─ 新版 API：Cookie 认证
   │   例：GET /pc/resource/getResourceList?bbsid={bbsid}&folderId={id}
   └─ 下载：Cookie + Referer + User-Agent 验证
       例：POST /screen/note_note/files/status/{fileId}
```

### Requirement: Token 与 PUID 的核心关系总结

系统 SHALL 明确 token 与 puid 的核心关系：

1. **puid 就是 UID**：puid（Pan User ID）本质上就是用户的 UID，即 Cookie 中的 `UID` 字段值
2. **_token 是 puid 的服务端凭证**：_token 由服务端根据 puid 和会话状态生成，是 puid 在云盘系统中的"通行证"
3. **_token 与 puid 必须配对使用**：旧版 API 中，_token 和 puid 必须同时携带且匹配，缺一不可
4. **_token 的生成是服务端行为**：客户端无法自行生成 _token，只能通过 API 接口获取
5. **不同 API 体系的 _token 不同**：旧版云盘 API（pan-yz）和新版云盘 API（noteyd）的 _token 是独立生成的，互不通用
6. **puid 在文件元数据中也有体现**：云盘文件的 `content.puid` 字段标识文件所属用户

## MODIFIED Requirements

### Requirement: _token 可预测性分析（关联 security_report.md 攻击路径2）

基于 security_report.md 中"攻击路径2 (Token可预测场景)"的未完成研究，系统 SHALL 对旧版云盘 API 的 `_token` 进行可预测性分析：

1. **_token 格式特征**：
   - 长度：32 位十六进制字符串
   - 示例：`721b618c5d4593ecfe7e2ee3a2275c23`（账号1）、`83506aa06d929e82bc9a613314ef9890`（账号2）
   - 格式符合 MD5 哈希输出特征（128 bit / 32 hex chars）

2. **_token 生成算法推测**：
   - **最可能算法**：`_token = MD5(puid + salt)` 或 `_token = MD5(puid + session_key + salt)`
   - **依据**：
     - 32 位 hex 格式与 MD5 输出完全一致
     - Token 与 puid 绑定（不同 puid 产生不同 Token）
     - Token 与 Session 也有一定关联（同一用户不同时间获取可能不同）
   - **其他可能性**：服务端随机生成后存储在缓存中与 puid 关联

3. **可预测性评估**：
   - **若 _token = MD5(puid + 固定salt)**：高度可预测，攻击者只需知道 puid 即可伪造 Token
   - **若 _token = MD5(puid + session_key + salt)**：中等可预测，需同时获取 session_key
   - **若 _token 为服务端随机生成**：不可预测，但可通过 `/api/token/uservalid` 接口获取任意用户的 Token（只要有该用户的 Cookie）

4. **关键安全发现**（来自 security_report.md）：
   - 服务端仅校验 `_token` 与 `puid` 的匹配关系
   - **完全忽略 Cookie/Session 中的用户身份校验**
   - 即使 _token 不可预测，只要获取到目标用户的 _token，即可使用任意 Session 越权访问

5. **绕过方案分析**：
   - **方案1（已验证可行）**：获取目标用户 Cookie → 调用 `/api/token/uservalid` 获取 _token → 使用自身 Session + 目标 _token + 目标 puid 越权访问
   - **方案2（待验证）**：若 _token 生成算法可逆向 → 直接根据 puid 伪造 _token → 无需目标用户 Cookie 即可越权
   - **方案3（待验证）**：利用 _token 不与 Session 绑定的缺陷 → 一次性获取 _token 后长期使用

#### Scenario: _token 可预测性测试
- **WHEN** 对同一用户在不同时间多次调用 `/api/token/uservalid`
- **THEN** 观察返回的 _token 是否相同
- **AND** 若相同，说明 _token 仅与 puid 相关（可能为 `MD5(puid + salt)`），可预测性高
- **AND** 若不同，说明 _token 包含时间/会话因子，可预测性较低

#### Scenario: _token 算法逆向尝试
- **WHEN** 已知多个 puid 与对应 _token 的映射关系
- **THEN** 尝试常见哈希算法（MD5、SHA1 截断等）对 puid 进行哈希
- **AND** 若匹配成功，则 _token 生成算法已被逆向
- **AND** 若均不匹配，则 _token 可能包含未知 salt 或为随机生成

## REMOVED Requirements

无
