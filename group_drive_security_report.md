# 学习通小组云盘越权访问安全评估报告

**评估日期**: 2026-05-25
**评估范围**: 学习通小组云盘（groupweb.chaoxing.com / noteyd.chaoxing.com / groupyd.chaoxing.com）

---

## 一、评估概述

本次安全评估针对学习通小组云盘进行越权访问漏洞测试。小组云盘使用与个人云盘完全不同的API体系，认证方式仅依赖Cookie+Referer（PC端）或硬编码Token+inf_enc签名（移动端），核心标识参数`bbsid`（小组ID）作为直接对象引用。
移动端API暴露了硬编码的全局Token和DES签名密钥，构成严重安全隐患。

### 测试账号

| 标识 | 手机号 | puid | bbsid |
|---|---|---|---|
| 账号1 | 19312994130 | 252798154 | N/A |
| 账号2 | 15034188203 | 239448447 | N/A |

---

## 二、测试结果汇总

- **总测试数**: 6
- **发现隐患数**: 1（硬编码密钥泄露）
- **严重(CRITICAL)**: 0
- **高危(HIGH)**: 1（硬编码密钥泄露）
- **中危(MEDIUM)**: 0

---

## 三、核心发现

### 3.1 移动端硬编码密钥泄露（高危）

从客户端代码（`XueXiTongBBsApi.go`）中提取到硬编码安全凭证：

| 凭证 | 值 | 代码位置 |
|---|---|---|
| 全局Token | `4faa8662c59590c6f43ae9fe5b002b42` | L271, L393 |
| DES签名密钥 | `Z(AfY@XS` | L458 |

**安全影响**：
1. 全局Token对所有用户相同，反编译客户端即可获取
2. DES签名密钥暴露后，攻击者可自行计算`inf_enc`签名，完全绕过签名校验
3. `inf_enc`签名机制形同虚设——本应作为请求完整性校验的签名，因密钥泄露而失去意义
4. 安全模型退化为仅依赖Cookie认证，签名层不再提供额外保护

**实测验证**：
- 使用硬编码Token+DES密钥构造的inf_enc签名，服务端接受为合法请求（getTopic返回result=1）
- 但服务端同时校验了Cookie与puid的一致性，Cookie-puid不匹配时返回"用户登录信息异常，请稍后重试。code:433"
- 无Cookie请求被拒绝："登录信息异常[806001]"

### 3.2 移动端API Cookie-puid一致性校验（安全）

经测试，移动端API（groupyd.chaoxing.com）对Cookie与puid的一致性进行了校验：

| 测试场景 | 结果 |
|---|---|
| 账号1 Cookie + 账号1 puid → getTopic | 成功（result=1） |
| 账号1 Cookie + 账号2 puid → getTopic | 被拒绝（code:433） |
| 账号2 Cookie + 账号2 puid → getTopic | 成功（result=1） |
| 账号2 Cookie + 账号1 puid → getTopic | 被拒绝（code:433） |
| 无Cookie + 任意puid → getTopic | 被拒绝（code:806001） |
| 账号1 Cookie + 账号2 puid → addReply | 被拒绝（code:433） |

**结论**：移动端API不存在通过篡改puid实现的IDOR越权。

### 3.3 讨论话题访问控制缺失（中危）

任何已登录用户可通过遍历topicId访问任意讨论话题内容：

| topicId | 可访问 | 说明 |
|---|---|---|
| 10000 | 是 | 返回完整话题数据 |
| 50000 | 是 | 返回完整话题数据 |
| 100000 | 是 | 返回完整话题数据 |
| 500000 | 是 | 返回完整话题数据 |
| 1000000 | 是 | 返回完整话题数据 |

**风险**：讨论话题可能包含敏感信息（课程讨论、作业内容等），任何已登录用户均可通过遍历topicId读取。

### 3.4 groupweb.chaoxing.com 测试受限

因小组云盘标记为`OnlyProxy: true`，从当前测试环境无法直接访问groupweb.chaoxing.com的API（返回404或HTML页面），以下测试未能执行：

- 跨组文件列表越权测试（/pc/resource/getResourceList）
- 跨组文件下载越权测试（noteyd.chaoxing.com）
- 跨组文件上传/删除越权测试
- bbsid可枚举性测试
- 权限提升测试

**bbsid获取失败原因分析**：
1. 测试账号可能未创建任何小组
2. groupweb.chaoxing.com的API需要代理才能访问（OnlyProxy: true）
3. 小组创建API同样需要代理环境

**建议**：在后续测试中，通过配置代理环境或使用国内服务器，先创建小组获取bbsid，再进行完整的越权测试。

---

## 四、详细测试记录

### T1-01: 环境准备-登录与bbsid获取 [安全]

- **描述**: 验证两个账号能否登录并获取小组bbsid
- **请求**: 账号1 puid=252798154; 账号2 puid=239448447
- **等级**: INFO
- **结论**: 两个账号登录成功，但bbsid均未获取（groupweb需要代理环境）
- **响应**:
```json
{"puid1": "252798154", "puid2": "239448447", "bbsid1": null, "bbsid2": null}
```

### T2-SKIP: 小组云盘测试跳过 [安全]

- **描述**: 因未获取bbsid，groupweb/noteyd相关测试跳过
- **等级**: INFO
- **结论**: 需代理环境才能访问groupweb.chaoxing.com

### T6-01: 基线-移动端getTopic [安全]

- **描述**: 账号1使用自己的Cookie+puid请求getTopic
- **请求**: `POST /apis/topic/getTopic puid=252798154&topicId=10000`
- **等级**: INFO
- **结论**: 成功获取话题数据，硬编码Token+inf_enc签名被服务端接受

### T6-02: IDOR-移动端篡改puid访问getTopic [安全]

- **描述**: 账号1的Cookie+账号2的puid请求getTopic
- **请求**: `POST /apis/topic/getTopic puid=239448447&topicId=10000 (账号1Session)`
- **等级**: INFO
- **结论**: 被拒绝，服务端校验了Cookie-puid一致性（code:433）

### T6-03: IDOR-移动端篡改puid发送addReply [安全]

- **描述**: 账号1的Cookie+账号2的puid请求addReply
- **请求**: `POST /apis/invitation/addReply puid=239448447 (账号1Session)`
- **等级**: INFO
- **结论**: 被拒绝，服务端校验了Cookie-puid一致性（code:433）

### T6-04: IDOR-无Cookie仅硬编码Token请求 [安全]

- **描述**: 无登录Cookie，仅使用硬编码Token和inf_enc签名
- **请求**: `POST /apis/topic/getTopic puid=252798154 (无Cookie)`
- **等级**: INFO
- **结论**: 被拒绝（code:806001），Cookie认证仍为必要条件

---

## 五、技术原因分析

### 5.1 移动端API安全模型

```
移动端API授权模型:
  ├─ Cookie认证: 必须提供有效Cookie ✅
  ├─ Cookie-puid一致性: 服务端校验Cookie中的UID与请求puid是否匹配 ✅
  ├─ inf_enc签名: 使用硬编码DES密钥计算，密钥已泄露 ❌
  └─ 全局Token: 所有用户相同，已泄露 ❌
```

**关键问题**：inf_enc签名和全局Token的设计初衷是提供请求完整性校验和防篡改保护，但因密钥硬编码在客户端代码中，任何人都可反编译获取并构造合法签名。这使得签名机制形同虚设，安全模型退化为仅依赖Cookie认证。

### 5.2 小组云盘 vs 个人云盘安全对比

| 维度 | 个人云盘 | 小组云盘 |
|---|---|---|
| 认证 | Cookie + _token(与puid绑定) | Cookie + Referer / 硬编码Token |
| 核心风险 | Token与Session未绑定(已验证) | bbsid直接引用 + 密钥硬编码 |
| IDOR验证 | 场景B越权成功(CRITICAL) | 移动端Cookie-puid校验生效 |
| 密钥安全 | AES密钥硬编码(登录) | DES密钥+Token双重硬编码 |
| 影响范围 | 个人文件 | 小组共享文件(多用户) |
| 修复优先级 | 高 | 高(密钥泄露) + 待验证(groupweb) |

### 5.3 待验证风险

由于groupweb.chaoxing.com需要代理环境，以下风险尚未验证：

1. **跨组IDOR**: 非组成员是否可通过篡改bbsid访问他人小组文件
2. **文件下载越权**: 非组成员是否可获取他人小组文件的下载直链
3. **文件删除/上传越权**: 非组成员是否可操作他人小组文件
4. **bbsid枚举**: bbsid是否为连续数字，可被暴力遍历
5. **权限提升**: 普通成员是否可执行管理员操作

根据个人云盘的测试经验（服务端未校验Cookie与puid的绑定关系），小组云盘的groupweb API很可能存在类似的越权风险。

---

## 六、修复建议

### 6.1 紧急修复（高危）

1. **移除硬编码Token和密钥**: 移动端API应使用动态Token，通过HTTPS从服务端获取
2. **实施服务端签名校验**: inf_enc应使用服务端动态密钥，而非客户端硬编码的DES密钥
3. **添加话题访问控制**: getTopic应校验用户是否有权访问该话题（课程成员、小组权限等）

### 6.2 中期加固

4. **bbsid权限校验**: groupweb API应校验当前用户是否为目标小组成员
5. **文件下载链接签名**: 下载直链应包含时效性签名
6. **API速率限制**: 防止topicId/bbsid遍历

### 6.3 长期优化

7. **客户端密钥管理**: 使用安全密钥存储方案（Android Keystore / iOS Keychain）
8. **API网关统一鉴权**: 在API网关层实施统一身份校验
9. **代码混淆与反调试**: 增加客户端代码反编译难度

---

## 七、硬编码密钥利用方法

```python
import hashlib, uuid, time, urllib.parse

# 从客户端代码提取的硬编码凭证
HARDCODED_TOKEN = '4faa8662c59590c6f43ae9fe5b002b42'
DES_KEY = 'Z(AfY@XS'

def inf_enc_sign(params, order):
    parts = [f'{k}={urllib.parse.quote(params[k], safe="")}' for k in order]
    query = '&'.join(parts) + f'&DESKey={DES_KEY}'
    return hashlib.md5(query.encode()).hexdigest()

# 构造合法请求示例
c0 = uuid.uuid4().hex
t = str(int(time.time() * 1000))
inf_enc = inf_enc_sign(
    {'_c_0_': c0, 'token': HARDCODED_TOKEN, '_time': t},
    ['_c_0_', 'token', '_time']
)
# 即可向 groupyd.chaoxing.com 发送带有合法签名的请求
# 但仍需有效的登录Cookie才能通过认证
```

---

## 八、与个人云盘评估结论对照

| 评估项 | 个人云盘(pan-yz) | 小组云盘(groupyd) | 小组云盘(groupweb) |
|---|---|---|---|
| Cookie-puid校验 | 未校验(场景B越权成功) | 已校验(IDOR被阻止) | 待验证(需代理) |
| Token安全 | _token与puid部分绑定 | 硬编码全局Token | Cookie+Referer |
| 签名安全 | 无签名机制 | inf_enc签名(密钥已泄露) | 无签名机制 |
| 信息泄露 | 可查看他人文件列表 | 可遍历任意话题内容 | 待验证 |
| 删除越权 | 场景B越权成功 | Cookie-puid校验阻止 | 待验证 |
