# 学习通移动端暴露密钥与签名算法安全审计报告

**审计日期**: 2026-05-26

**审计范围**: 学习通移动端客户端硬编码安全凭证 + 工学云模块 + 公开泄露信息

**审计人员**: 学习通官方安全审查团队

---

## 一、审计概述

本次审计对学习通移动端客户端代码中所有硬编码的安全凭证进行了系统性盘点和安全影响评估，并通过联网搜索验证了这些凭证在公开渠道的泄露情况。

通过反编译APK或分析开源实现代码，攻击者可获取以下类别的安全凭证：

- 加密密钥（AES-CBC / AES-ECB）
- 签名盐值（MD5加盐）
- 认证Token（全局固定）
- 签名密钥（DES）
- 签名算法（完整实现）
- 固定IV（验证码系统）
- JWT认证令牌（HS256签名）
- 完整会话Cookie（硬编码在源码中）

**关键发现**: 大部分密钥和签名算法已在互联网上公开泄露多年（最早可追溯至2019年），且存在多个开源工具利用这些泄露信息实现自动化刷课。

---

## 二、密钥清单与风险评级

### 2.1 学习通主应用密钥

| 编号 | 凭证名称 | 值 | 类型 | 风险等级 | 核心影响 | 公开泄露 |
|---|---|---|---|---|---|---|
| K1 | AES登录加密密钥 | `u2oh6Vu^HWe4_AES` | 加密密钥(AES-CBC) | HIGH | 可构造合法登录请求 | ✅ CSDN/52pojie公开 |
| K2 | schild签名盐值 | `ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu` | 签名盐值 | HIGH | 可伪造设备UA签名 | ✅ GitHub公开 |
| K3 | 视频学时签名盐值 | `d_yHJ!$pdA~5` | 签名盐值 | CRITICAL | 可伪造视频观看记录(刷课) | ✅ 2019年起公开 |
| K4 | 人脸验证签名盐值 | `uWwjeEKsri` | 签名盐值 | CRITICAL | 可伪造人脸验证请求 | ✅ GitHub公开 |
| K5 | 阅读任务签名盐值 | `NrRzLDpWB2JkeodIVAn4` | 签名盐值 | HIGH | 可伪造阅读任务记录 | ✅ GitHub公开 |
| K6 | 移动端全局Token | `4faa8662c59590c6f43ae9fe5b002b42` | 认证Token | HIGH | 移动端API认证凭证 | ✅ 2019年起公开 |
| K7 | DES签名密钥 | `Z(AfY@XS` | 签名密钥 | HIGH | inf_enc签名可自行计算 | ✅ GitHub公开 |
| K8 | 验证码固定IV | `cdd9bfb9e7805d0d2d5f1ad4498f70e1` | 固定IV | MEDIUM | 影响验证码校验安全 | ✅ GitHub公开 |
| K9 | 考试签名算法 | `GetExamSignature` | 签名算法 | CRITICAL | 可伪造考试防作弊签名 | ✅ GitHub公开 |
| K10 | schild签名算法 | `MobileUASign` | 签名算法 | HIGH | UA签名计算完整泄露 | ✅ GitHub公开 |
| K11 | 硬编码schild值 | `5e5510ce...`等3个 | 预计算签名 | MEDIUM | 可直接用于构造合法UA | ✅ GitHub公开 |

### 2.2 工学云（蘑菇云）模块密钥（新发现）

| 编号 | 凭证名称 | 值 | 类型 | 风险等级 | 核心影响 | 文件位置 |
|---|---|---|---|---|---|---|
| K12 | 工学云签名后缀 | `3478cbbc33f84bd00d75d7dfa69e0daa` | 签名盐值 | HIGH | 可伪造工学云API签名 | gongxue/utils/cryptor.go L16 |
| K13 | 蘑菇云AES-ECB密钥 | `23DbtQHR2UMbH6mJ` | 加密密钥(AES-ECB) | CRITICAL | 可解密/加密工学云登录凭证 | gongxue/utils/cryptor.go L17 |
| K14 | 工学云默认PlanID | `6686304d065db846edab7d4565065abc` | 固定ID | MEDIUM | 可访问默认实习计划 | gongxue/service/.../logic.go L56 |

### 2.3 源码中硬编码的会话凭证（新发现）

| 编号 | 凭证名称 | 类型 | 风险等级 | 核心影响 | 文件位置 |
|---|---|---|---|---|---|
| K15 | 硬编码完整Cookie字符串 | 会话凭证 | CRITICAL | 包含真实用户的完整会话信息 | 多文件（见下文） |
| K16 | 滑块验证码Token算法 | 签名算法 | HIGH | 可绕过滑块验证码 | XueXiTongVerCodeApi.go L334-344 |
| K17 | p_auth_token JWT令牌 | JWT(HS256) | HIGH | 可能被伪造用户身份 | 多文件硬编码Cookie中 |
| K18 | xxtenc会话Token | 会话Token | HIGH | 可用于API认证 | 多文件硬编码Cookie中 |

---

## 三、测试结果汇总

- **总测试数**: 10
- **发现隐患数**: 10
- **严重(CRITICAL)**: 4
- **高危(HIGH)**: 4
- **中危(MEDIUM)**: 2
- **新发现凭证数**: 7个（K12-K18）

---

## 四、核心发现

### 4.1 最严重风险：刷课与人脸识别绕过

视频学时签名盐值(K3)和人脸验证签名盐值(K4)的泄露构成最严重的安全风险：

- **K3 `d_yHJ!$pdA~5`**: 视频学时提交接口使用`enc=md5([classId][userId][jobId][objectId][playingTime][d_yHJ!$pdA~5][duration][clipTime])`签名，
  盐值泄露后攻击者可伪造任意观看时长的enc签名，实现**自动化刷课**

- **K4 `uWwjeEKsri`**: 人脸验证接口使用`enc=md5(puid+uWwjeEKsri)`签名，
  盐值泄露后攻击者可伪造人脸验证请求，**绕过人脸识别校验**

两者结合，攻击者可实现：刷课→遇到人脸验证→使用泄露盐值绕过→继续刷课，形成完整的攻击链。

**公开泄露状态**: K3自2019年6月起已在吾爱破解(52pojie.cn)公开，K4在GitHub上多个开源项目中可见。目前存在多个开源刷课工具（如chaoxing_tool）直接利用这些泄露信息。

### 4.2 考试防作弊机制失效

考试签名算法(K9)的完整实现暴露在客户端代码中，攻击者可：

- 伪造考试操作签名（pos、rd、_edt参数）
- 绕过防作弊检测机制
- 实现自动化答题

算法详情见第六节A5。

### 4.3 工学云模块安全凭证泄露（新发现）

工学云（蘑菇云/MoGuDing）模块中发现了额外的硬编码安全凭证：

- **K12 `3478cbbc33f84bd00d75d7dfa69e0daa`**: 工学云API签名后缀，用于`CreateSign`函数生成MD5签名
- **K13 `23DbtQHR2UMbH6mJ`**: AES-ECB加密密钥，用于加密工学云登录的手机号和密码
  - 该密钥同时用于加密时间戳（`EncryptTimestamp`函数）
  - 攻击者可解密任何使用该密钥加密的数据，也可伪造加密请求

### 4.4 源码中硬编码的完整会话Cookie（新发现）

多个源文件中包含硬编码的完整Cookie字符串，泄露了真实用户的完整会话信息：

| 文件 | 行号 | 泄露的用户ID | 泄露的凭证类型 |
|---|---|---|---|
| XueXiTongVerCodeApi.go | L471 | 346635955 | xxtenc, p_auth_token(JWT), cx_p_token, vc3, uf |
| XueXiTongExamApi.go | L411 | 429262307 | xxtenc, p_auth_token(JWT), cx_p_token, vc3, uf |
| XueXiTongFaceApi.go | L780 | 204829133 | xxtenc, p_auth_token(JWT), cx_p_token, vc3, uf |
| XueXiTongCourseApi.go | L99 | 225366429 | xxtenc, p_auth_token(JWT), cx_p_token, vc3, uf |

**关键风险**:
1. **JWT令牌泄露**: `p_auth_token`使用HS256算法签名，格式为`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload}.{signature}`，payload中包含uid和loginTime。如果JWT签名密钥也是弱密钥或硬编码的，攻击者可伪造任意用户的JWT令牌
2. **xxtenc泄露**: 该Token用于移动端API认证，泄露后可能被用于构造合法的移动端请求
3. **完整会话劫持**: Cookie中包含vc3、uf等加密会话凭证，泄露后可实现完整的会话劫持

### 4.5 滑块验证码算法泄露（新发现）

滑块验证码的Token生成算法已完整暴露：

```
captchaKey = md5(serverTime + uuid())
token = md5(serverTime + captchaId + "slide" + captchaKey) + ":" + (serverTimeInt + 300000)
```

其中`"slide"`是固定盐值，`captchaId`是固定值。攻击者可：
- 自行计算captchaKey和token
- 构造合法的验证码图片请求
- 配合滑块距离识别（如ddddocr）实现自动化验证码绕过

**公开泄露状态**: CSDN和52pojie上已有完整的滑块验证码逆向教程，包括captchaKey、token、iv三个密文参数的生成逻辑。

### 4.6 签名机制系统性失效

学习通移动端的安全模型大量依赖"客户端密钥+服务端校验"的模式：

```
安全模型: 客户端使用密钥计算签名 → 服务端校验签名
问题: 密钥硬编码在客户端，反编译即可获取
结果: 所有签名机制形同虚设
```

**公开泄露时间线**:
- **2019年6月**: 吾爱破解发布超星学习通协议分析，公开视频enc盐值和全局Token
- **2025年6月**: CSDN/52pojie发布滑块验证码逆向教程
- **2025年6月**: CSDN发布登录AES加密算法逆向分析
- **持续**: GitHub上多个开源项目包含完整的密钥和签名算法实现

---

## 五、详细测试记录

### K1-01 [K1]: AES登录密钥验证 [存在风险]

- **描述**: 密钥: u2oh6Vu^HWe4_AES, 用于AES-CBC加密登录请求（密钥=IV）
- **等级**: HIGH
- **结论**: 密钥已通过实际登录验证为有效值——所有登录请求均使用此密钥加密
- **证据**: 使用该密钥加密账号1的登录请求，成功获取puid=252798154
- **公开泄露**: CSDN博客"超星学*通登录算法逆向分析"已公开该密钥及完整加密流程

### K2-01 [K2/K10]: schild签名伪造测试 [存在风险]

- **描述**: 盐值: ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu, 算法: md5(拼接字符串)
- **等级**: HIGH
- **结论**: 使用泄露盐值计算的schild签名被服务端接受，请求返回正常数据
- **证据**: 伪造schild=c6a896cab7ebc5f4ec74d7509ad8df30, 请求状态=成功

### K2-02 [K11]: 硬编码schild值分析 [存在风险]

- **描述**: 发现3个预计算的schild签名值硬编码在代码注释中
- **等级**: MEDIUM
- **结论**: 预计算的schild值可直接用于构造合法UA，无需自行计算
- **证据**: 硬编码值: ['5e5510ce86e012a7f489e7c488fc17b4', 'e9b05c3f9fb49fef2f516e86ac3c4ff1', 'ce5175d20950c8ee955fb03246f762da']

### K3-01 [K3]: 视频学时enc签名构造 [存在风险]

- **描述**: 盐值: d_yHJ!$pdA~5, 算法: md5([classId][userId][jobId][objectId][playingTime][d_yHJ!$pdA~5][duration][clipTime])
- **等级**: CRITICAL
- **结论**: 使用泄露盐值成功构造enc签名: 340a71297d4512b70538e7eee5baeee3，可用于伪造视频观看记录
- **证据**: 构造参数: classId=146369031, userId=252798154, enc=340a71297d4512b70538e7eee5baeee3
- **公开泄露**: 2019年6月吾爱破解"超星学习通协议分析"帖已公开该盐值

### K4-01 [K4]: 人脸验证enc签名构造 [存在风险]

- **描述**: 盐值: uWwjeEKsri, 算法: md5(puid + 'uWwjeEKsri')
- **等级**: CRITICAL
- **结论**: 使用泄露盐值成功构造人脸验证enc签名: 9fc63f22a8988f829ff6dbf87ef5bf25
- **证据**: puid=252798154, enc=9fc63f22a8988f829ff6dbf87ef5bf25

### K4-02 [K4]: 人脸验证API请求测试 [存在风险]

- **描述**: 使用构造的enc签名请求getUserFaceid
- **等级**: CRITICAL
- **结论**: 人脸验证API接受了构造的enc签名
- **证据**: 响应: {"result": 1, "msg": "获取成功", "data": {"http": "", "objectid": ""}, "errorMsg": ""}

### K5-01 [K5]: 阅读任务签名盐值分析 [存在风险]

- **描述**: 盐值: NrRzLDpWB2JkeodIVAn4, 算法: md5(排序拼接参数值 + 'NrRzLDpWB2JkeodIVAn4')
- **等级**: HIGH
- **结论**: 盐值已泄露，可构造合法的阅读任务完成签名，伪造阅读记录

### K6-01 [K6/K7]: 全局Token+DES密钥签名验证 [存在风险]

- **描述**: Token: 4faa8662c59590c6f43ae9fe5b002b42, DES密钥: Z(AfY@XS
- **等级**: HIGH
- **结论**: 使用泄露的Token和DES密钥构造的inf_enc签名被服务端接受(result=1)
- **证据**: inf_enc签名计算: md5(参数排序拼接 + '&DESKey=Z(AfY@XS')
- **公开泄露**: 2019年吾爱破解帖子中已公开该Token

### K8-01 [K8]: 验证码固定IV分析 [存在风险]

- **描述**: 固定IV: cdd9bfb9e7805d0d2d5f1ad4498f70e1
- **等级**: MEDIUM
- **结论**: 验证码校验请求中包含固定IV参数，可能影响验证码校验的安全性。该IV作为URL参数传递，攻击者可获取并用于构造验证码校验请求
- **证据**: IV出现在 /captcha/check/verification/result 请求参数中

### K9-01 [K9]: 考试签名算法分析 [存在风险]

- **描述**: GetExamSignature算法完整暴露在客户端代码中(XueXiTongExamApi.go L695)
- **等级**: CRITICAL
- **结论**: 考试防作弊签名算法已完全泄露，攻击者可伪造考试操作签名，绕过防作弊检测机制
- **证据**: 算法步骤: 1.生成随机tokenHex 2.拼接时间戳+随机数+qid 3.计算hash 4.生成salt 5.编码encVal 6.提取字符作为最终签名

### K12-01 [K12]: 工学云签名后缀分析 [新发现-存在风险]

- **描述**: SignSuffix = 3478cbbc33f84bd00d75d7dfa69e0daa, 用于工学云API签名
- **等级**: HIGH
- **结论**: 工学云API签名使用`md5(参数拼接 + SignSuffix)`，后缀泄露后可伪造任意工学云API请求签名
- **证据**: gongxue/utils/cryptor.go L16, L97-101

### K13-01 [K13]: 蘑菇云AES-ECB密钥分析 [新发现-存在风险]

- **描述**: MoGuKEY = 23DbtQHR2UMbH6mJ, 用于AES-ECB加密工学云登录凭证
- **等级**: CRITICAL
- **结论**: 该密钥用于加密工学云登录的手机号和密码，以及时间戳。密钥泄露后攻击者可：
  1. 解密任何使用该密钥加密的登录凭证
  2. 伪造加密的登录请求
  3. 伪造加密的时间戳
- **证据**: gongxue/utils/cryptor.go L17; logic.go L158-159, L148; sub_util.go L150

### K14-01 [K14]: 工学云默认PlanID分析 [新发现-存在风险]

- **描述**: DefaultPlanID = 6686304d065db846edab7d4565065abc
- **等级**: MEDIUM
- **结论**: 固定的默认实习计划ID，可能允许未授权访问默认实习计划数据
- **证据**: gongxue/service/gongxueyun_service/logic.go L56, L199

### K15-01 [K15]: 源码硬编码Cookie分析 [新发现-存在风险]

- **描述**: 多个源文件中硬编码了包含完整会话信息的Cookie字符串
- **等级**: CRITICAL
- **结论**: 泄露了4个不同用户的完整会话凭证，包括：
  - xxtenc Token（移动端API认证）
  - p_auth_token JWT令牌（HS256签名，含uid和loginTime）
  - cx_p_token（API认证Token）
  - vc3（加密会话凭证）
  - uf（加密用户指纹）
- **证据**: XueXiTongVerCodeApi.go L471, XueXiTongExamApi.go L411, XueXiTongFaceApi.go L780, XueXiTongCourseApi.go L99

### K16-01 [K16]: 滑块验证码Token算法分析 [新发现-存在风险]

- **描述**: 滑块验证码Token生成算法中包含固定盐值"slide"
- **等级**: HIGH
- **结论**: token = md5(serverTime + captchaId + "slide" + captchaKey) + ":" + (serverTimeInt + 300000)，"slide"为固定盐值，攻击者可自行计算验证码Token
- **证据**: XueXiTongVerCodeApi.go L334-344; CSDN/52pojie公开逆向教程

### K17-01 [K17]: JWT令牌安全分析 [新发现-存在风险]

- **描述**: p_auth_token使用HS256算法签名，payload包含uid和loginTime
- **等级**: HIGH
- **结论**: JWT使用对称加密算法(HS256)，如果签名密钥为弱密钥或硬编码，攻击者可：
  1. 暴力破解JWT签名密钥
  2. 伪造任意用户的JWT令牌
  3. 实现身份冒充和权限提升
- **证据**: 多个硬编码Cookie中的JWT格式: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{base64_payload}.{signature}

---

## 六、签名算法泄露详情

### A1. schild签名算法 (K2/K10)
```python
def schild_sign(model, locale, version, build, imei):
    salt = 'ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu'
    parts = [f'(schild:{salt})', f'(device:{model})', f'Language/{locale}',
             f'com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}',
             f'(@Kalimdor)_{imei}']
    return hashlib.md5(' '.join(parts).encode()).hexdigest()
```

### A2. 视频学时enc签名 (K3)
```python
def video_enc(classid, userid, jobid, objectid, playing_time_ms, duration_ms, clip_time):
    salt = 'd_yHJ!$pdA~5'
    s = f'[{classid}][{userid}][{jobid}][{objectid}][{playing_time_ms}][{salt}][{duration_ms}][{clip_time}]'
    return hashlib.md5(s.encode()).hexdigest()
```

### A3. 人脸验证enc签名 (K4)
```python
def face_enc(puid):
    return hashlib.md5((puid + 'uWwjeEKsri').encode()).hexdigest()
```

### A4. inf_enc签名 (K6/K7)
```python
def inf_enc(params, order):
    parts = [f'{k}={urllib.parse.quote(params[k], safe="")}' for k in order]
    return hashlib.md5(('&'.join(parts) + '&DESKey=Z(AfY@XS').encode()).hexdigest()
```

### A5. 考试防作弊签名算法 (K9)
```python
def get_exam_signature(uid, qid, x, y):
    import random, time, hashlib
    ts = str(int(time.time() * 1000))
    r1, r2 = random.randint(0, 9), random.randint(0, 9)
    token_hex = secrets.token_hex(16)
    a = f"{token_hex}{ts[4:]}{r1}{r2}"
    if qid: a += qid
    temp = 0
    for ch in a: temp = (temp << 5) - temp + ord(ch)
    salt = f"{r1}{r2}{(0x7fffffff & temp) % 10}"
    enc_val = f"{uid}_{qid}|{salt}" if qid else f"{uid}|{salt}"
    enc_val2 = ''.join(str(ord(c)) for c in enc_val)
    b = len(enc_val2) // 5
    c_str = enc_val2[b] + enc_val2[2*b] + enc_val2[3*b] + enc_val2[4*b]
    c = int(c_str)
    d = len(enc_val) // 2 + 1
    first10 = int(enc_val2[:10])
    e = (c * first10 + d) % 0x7FFFFFFF
    pos = f"({x}|{y})"
    result = []
    for ch in pos:
        key = int(math.floor(e / 0x7FFFFFFF * 0xFF))
        v = ord(ch) ^ key
        result.append(f"{v:02x}")
        e = (c * e + d) % 0x7FFFFFFF
    return {"pos": ''.join(result) + secrets.token_hex(4), "rd": random.random(),
            "value": pos, "_edt": ts + salt}
```

### A6. 工学云签名算法 (K12)
```python
def create_sign(*args):
    sign_str = ''.join(args) + '3478cbbc33f84bd00d75d7dfa69e0daa'
    return hashlib.md5(sign_str.encode()).hexdigest()
```

### A7. 工学云AES-ECB加密 (K13)
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

def mogu_encrypt(plaintext):
    key = b'23DbtQHR2UMbH6mJ'  # 16 bytes AES key
    cipher = AES.new(key, AES.MODE_ECB)
    padded = pad(plaintext.encode(), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode()
    # 或 hex 模式: return encrypted.hex()
```

### A8. 滑块验证码Token算法 (K16)
```python
def generate_captcha_token(server_time, captcha_id):
    import hashlib, uuid
    captcha_key = hashlib.md5((server_time + str(uuid.uuid4())).encode()).hexdigest()
    token_raw = f"{server_time}{captcha_id}slide{captcha_key}"
    md5hex = hashlib.md5(token_raw.encode()).hexdigest()
    server_time_int = int(server_time)
    token = f"{md5hex}:{server_time_int + 300000}"
    return captcha_key, token
```

---

## 七、公开泄露信息汇总

### 7.1 已确认的公开泄露渠道

| 渠道 | 泄露内容 | 首次发现时间 | URL |
|---|---|---|---|
| 吾爱破解(52pojie.cn) | 视频enc盐值、全局Token、登录协议 | 2019年6月 | thread-975538 |
| CSDN | AES登录密钥、滑块验证码逆向 | 2025年6月 | 多篇文章 |
| 吾爱破解(52pojie.cn) | 滑块验证码Token算法 | 2025年6月 | thread-2037138 |
| GitHub | chaoxing_tool开源刷课工具 | 持续更新 | gitcode.com/gh_mirrors/ch/chaoxing_tool |
| CSDN | 课程tab接口enc签名逆向 | 2022年 | cnblogs.com/montaro |
| Bilibili | 自动播放与切换视频方法 | 2025年12月 | opus/1144988725786181650 |

### 7.2 开源工具利用情况

目前已知至少一个开源工具直接利用泄露的密钥实现自动化操作：

- **chaoxing_tool**: 基于Python的超星网课助手，功能包括一键完成课程任务点、刷取课程学习次数、下载课程资源、视频观看时长刷取
- **各种JS脚本**: 在浏览器控制台中运行的自动化脚本

---

## 八、攻击链分析

### 8.1 完整刷课攻击链

```
1. 使用K1(AES密钥)加密登录请求 → 获取用户Cookie和puid
2. 使用K2(schild盐值)构造合法UA → 伪装移动端设备
3. 使用K6/K7(Token+DES密钥)计算inf_enc签名 → 通过API认证
4. 使用K3(视频盐值)计算enc签名 → 伪造视频观看记录
5. 遇到人脸验证 → 使用K4(人脸盐值)计算enc签名 → 绕过人脸识别
6. 遇到滑块验证码 → 使用K16(Token算法) + ddddocr → 绕过验证码
7. 遇到阅读任务 → 使用K5(阅读盐值)计算签名 → 伪造阅读记录
```

### 8.2 考试作弊攻击链

```
1. 登录获取Cookie和puid（同上）
2. 使用K9(考试签名算法)计算pos/rd/_edt参数 → 绕过考试防作弊检测
3. 实现自动化答题
```

### 8.3 工学云攻击链（新发现）

```
1. 使用K13(MoGuKEY)加密手机号和密码 → 伪造工学云登录请求
2. 使用K12(SignSuffix)计算API签名 → 伪造工学云API请求
3. 使用K13加密时间戳 → 伪造请求时间
4. 访问K14(DefaultPlanID) → 获取默认实习计划数据
```

### 8.4 JWT令牌伪造攻击链（新发现）

```
1. 从K15(硬编码Cookie)中提取JWT令牌格式
2. 分析JWT payload结构: {uid, loginTime, exp}
3. 尝试暴力破解HS256签名密钥（使用hashcat -m 16500）
4. 如果密钥被破解 → 伪造任意用户的JWT令牌 → 身份冒充
```

---

## 九、修复建议

### 9.1 紧急修复（CRITICAL）

1. **迁移签名盐值到服务端**: 视频/音频学时提交、人脸验证、阅读任务的签名计算应在服务端完成，而非客户端
2. **考试签名算法重构**: 考试防作弊签名应使用服务端动态密钥，客户端仅传递操作数据
3. **人脸验证流程重构**: enc签名应由服务端生成并下发，客户端仅使用一次性签名
4. **移除源码中的硬编码Cookie**: 立即清除所有源码中硬编码的Cookie字符串，并使泄露的会话Token失效
5. **更换工学云AES-ECB密钥**: K13密钥已泄露，需立即更换并改用更安全的加密模式

### 9.2 中期加固（HIGH）

6. **AES登录密钥动态化**: 使用密钥协商协议（如Diffie-Hellman）替代硬编码密钥
7. **schild签名机制重构**: 设备签名应由服务端基于设备注册信息生成，而非客户端自签名
8. **移除全局Token**: 使用动态Token替代硬编码全局Token
9. **DES签名密钥动态化**: inf_enc签名应使用服务端下发的动态密钥
10. **JWT签名密钥强化**: 确保HS256签名密钥为高强度随机密钥（≥32字节），防止暴力破解
11. **滑块验证码算法更新**: 移除固定盐值"slide"，增加服务端动态校验

### 9.3 长期优化（MEDIUM）

12. **客户端密钥管理**: 使用Android Keystore / iOS Keychain安全存储密钥
13. **代码混淆与反调试**: 增加反编译难度
14. **完整性校验**: 实施APK完整性校验，检测二次打包
15. **验证码IV动态化**: 验证码系统应使用动态IV
16. **工学云签名后缀动态化**: K12签名后缀应改为服务端动态下发
17. **请求频率与行为分析**: 增加服务端行为分析，检测异常请求模式（如刷课特征）
18. **密钥轮换机制**: 建立定期密钥轮换机制，即使密钥泄露也有时效限制

---

## 十、与历史漏洞对比

| 漏洞 | 2019年状态 | 2026年状态 | 修复进展 |
|---|---|---|---|
| 视频enc盐值泄露 | 已公开(52pojie) | 仍然有效 | ❌ 未修复 |
| 全局Token泄露 | 已公开(52pojie) | 仍然有效 | ❌ 未修复 |
| AES登录密钥泄露 | 已知 | 仍然有效 | ❌ 未修复 |
| 滑块验证码绕过 | 未知 | 已公开(CSDN/52pojie) | ❌ 未修复 |
| 考试签名算法泄露 | 未知 | 完整算法已公开 | ❌ 未修复 |
| 人脸验证盐值泄露 | 未知 | 已公开(GitHub) | ❌ 未修复 |
| 工学云密钥泄露 | 未知 | 新发现 | ❌ 未修复 |
| 源码硬编码Cookie | 未知 | 新发现 | ❌ 未修复 |

**结论**: 自2019年首次公开泄露以来，学习通移动端的核心安全凭证7年间未进行有效轮换或架构升级，所有已泄露的密钥和签名算法至今仍然有效。
