# Cookie UID篡改绕过一致性检查 - 安全评估报告

**评估日期**: 2026-05-25 09:51:37

**评估范围**: Cookie身份校验绕过测试（groupyd / pan-yz / groupweb）

---
## 一、评估概述

本次测试验证以下问题：

1. **puid与Cookie中的UID是否一致？**

2. **能否通过篡改Cookie中的UID及其他参数，使其与puid一致，从而绕过一致性检查？**

3. **`_d` Cookie在身份校验中的关键作用**


### 测试账号

| 标识 | 手机号 | puid | Cookie UID |
|---|---|---|---|

| 账号1 | 19312994130 | 252798154 | 252798154 |

| 账号2 | 15034188203 | 239448447 | 239448447 |

---
## 二、核心结论

### 2.1 puid与Cookie UID一致性

**结论: puid == Cookie UID = 是**


puid的值与Cookie中的`UID`字段完全一致。服务端通过Cookie中的UID来识别用户身份，
而puid是请求参数中传递的用户ID。两者在正常请求中必须匹配。


### 2.2 Cookie篡改能否绕过一致性检查

| 篡改方案 | groupyd结果 | 说明 |
|---|---|---|

| 仅替换UID | 被阻止(806001) | 服务端验证Cookie包完整性 |

| 替换7个身份Cookie(base7) | 被阻止(806001) | 缺少_d导致校验失败 |

| **base7 + _d** | **绕过成功!** | **_d是绕过的关键因素** |

| base7 + fid | 被阻止(806001) | fid不是关键因素 |

| base7 + DSSTASH_LOG | 被阻止(806001) | DSSTASH_LOG不是关键因素 |

| 完整Cookie替换 | 绕过成功 | 等同于使用另一个账号的Session |

| **伪造JWT(错误签名)+base7+_d** | **绕过成功!** | **JWT签名未被验证!严重漏洞** |


### 2.3 最小绕过集发现

通过逐步添加Cookie的测试，确定了绕过groupyd身份校验的**最小Cookie替换集**：

| 替换方案 | Cookie数量 | 结果 |
|---|---|---|
| UID + _d | 2 | 被阻止 |
| UID + _uid + _d | 3 | 被阻止 |
| UID + _uid + uf + _d | 4 | 被阻止 |
| **UID + _uid + uf + vc3 + _d** | **5** | **绕过成功!** |
| UID + _uid + uf + vc3 + xxtenc + _d | 6 | 绕过成功 |
| 7个身份Cookie + _d | 8 | 绕过成功 |

**最小绕过集 = 5个Cookie: `UID` + `_uid` + `uf` + `vc3` + `_d`**

不需要 `xxtenc`、`cx_p_token`、`p_auth_token` 即可绕过groupyd的身份校验！

### 2.4 JWT签名未验证（严重漏洞）

测试P3-10发现：修改JWT payload中的uid字段但保留原签名后，groupyd服务端**仍然接受了请求**。

这意味着：
- **groupyd不验证JWT签名**：服务端可能只检查JWT是否存在，或仅读取payload中的字段，但不验证签名
- **JWT形同虚设**：p_auth_token的HS256签名机制完全无效
- 攻击者可以随意修改JWT内容而不被检测

### 2.5 _d Cookie的关键作用

`_d` Cookie的值是毫秒级时间戳（如`1779702165920`），对应登录时间。


**关键发现**: 替换`_d` Cookie后，服务端接受了跨身份的请求。这表明：

- 服务端可能使用`_d`作为会话标识符的一部分

- `_d`与身份Cookie（特别是`p_auth_token` JWT）存在绑定关系

- 当`_d`与身份Cookie来自同一会话时，服务端认为Cookie包完整

- **缺少`_d`或`_d`与身份Cookie不匹配时，校验失败**


### 2.4 各API域名的校验差异

| API域名 | Cookie篡改绕过 | 额外校验 | 综合风险 |
|---|---|---|---|

| groupyd.chaoxing.com | base7+_d可绕过 | 无 | **高危** |

| pan-yz.chaoxing.com | Cookie替换不影响 | _token独立校验 | 中危(场景B仍有效) |

| groupweb.chaoxing.com | Cookie替换不影响 | 小组成员校验 | 低危 |


---
## 三、测试结果汇总

- **总测试数**: 28
- **绕过成功数**: 9


### 绕过成功的测试项
| ID | 名称 | 等级 | 结论 |
|---|---|---|---|

| P3-05 | 篡改-base7+_d | CRITICAL | base7+_d: 绕过成功! |

| P3-09 | 篡改-完整Cookie替换 | CRITICAL | 完整替换: 绕过成功! |

| P3-10 | 篡改-base7+_d+伪造JWT | CRITICAL | 伪造JWT: 绕过成功! |

| P4-02 | IDOR-账号1Cookie+账号2Token+账号2puid | CRITICAL | 场景B IDOR: 越权成功! |

| P4-03 | 完整Cookie替换+场景B IDOR | CRITICAL | 完整替换后场景B: 越权成功! |

| P5-05-d | 最小替换集-UID+_uid+uf+vc3+_d | CRITICAL | UID+_uid+uf+vc3+_d: 绕过成功! |

| P5-05-e | 最小替换集-UID+_uid+uf+vc3+xxtenc+_d | CRITICAL | UID+_uid+uf+vc3+xxtenc+_d: 绕过成功! |

| P5-05-f | 最小替换集-6身份+_d | CRITICAL | 6身份+_d: 绕过成功! |

| P5-05-g | 最小替换集-7身份+_d | CRITICAL | 7身份+_d: 绕过成功! |

---
## 四、详细测试记录


### P1-01: puid与Cookie UID一致性验证 [安全]

- **描述**: 
- **请求**: `puid1=252798154, UID1=252798154, puid2=239448447, UID2=239448447`
- **等级**: INFO
- **结论**: puid与Cookie中的UID值完全一致: puid1=252798154==UID1=252798154, puid2=239448447==UID2=239448447
- **响应**:
```json
{"match": true}
```


### P3-01: 基线-账号1正常请求groupyd [安全]

- **描述**: puid=252798154
- **请求**: `POST getTopic puid=252798154`
- **等级**: INFO
- **结论**: 基线: result=1, msg=sucess
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P3-02: IDOR-账号1Cookie+账号2puid(无篡改) [安全]

- **描述**: puid=239448447
- **请求**: `POST getTopic puid=239448447 (账号1Session)`
- **等级**: INFO
- **结论**: Cookie-puid不匹配: result=0, errorMsg=用户登录信息异常，请稍后重试。code:433
- **响应**:
```json
{"result": 0, "errorMsg": "用户登录信息异常，请稍后重试。code:433"}
```


### P3-03: 篡改-仅替换UID [安全]

- **描述**: UID=239448447
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: 仅替换UID: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P3-04: 篡改-base7(7个身份Cookie) [安全]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', 'cx_p_token', 'p_auth_token']
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: base7替换: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P3-05: 篡改-base7+_d [存在风险]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', 'cx_p_token', 'p_auth_token']+_d
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: base7+_d: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P3-06: 篡改-base7+fid [安全]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', 'cx_p_token', 'p_auth_token']+fid
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: base7+fid: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P3-07: 篡改-base7+DSSTASH_LOG [安全]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', 'cx_p_token', 'p_auth_token']+DSSTASH_LOG
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: base7+DSSTASH_LOG: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P3-08: 篡改-仅替换_d [安全]

- **描述**: _d=1779702694015
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: 仅替换_d: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P3-09: 篡改-完整Cookie替换 [存在风险]

- **描述**: 替换所有Cookie
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: 完整替换: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P3-10: 篡改-base7+_d+伪造JWT [存在风险]

- **描述**: 修改JWT中uid但保留原签名
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: 伪造JWT: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P4-01: 基线-账号1正常访问个人云盘 [安全]

- **描述**: puid=252798154
- **请求**: `GET /api/info?puid=252798154`
- **等级**: INFO
- **结论**: 基线: code=2, result=True
- **响应**:
```json
{"code": 2, "data": {"host": "sync.ananas.chaoxing.com", "hosts": ["sync2.ananas.chaoxing.com", "sync3.ananas.chaoxing.com"], "root": "up/1216/136/252798154", "froot": "1216/136/252798154", "p": "44604c9884a7229121549849afaf88ba390248ae48a3eb35", "u": "80e80ac5e63d7b56780e86c50a866292", "usedsize": 0, "disksize": 10737418240, "limitType": ["com", "apk", "deb", "ipa", "pxl", "dmg", "pkg", "0", "000", "001", "7z", "ace", "ain", "alz", "apz", "ar", "arc", "ari", "arj", "axx", "bh", "bhx", "boo", "bz", "bza", "bz2", "c00", "c01", "c02", "cab", "car", "cbr", "cbz", "cp9", "cpgz", "cpt", "dar", "dd"
```


### P4-02: IDOR-账号1Cookie+账号2Token+账号2puid [存在风险]

- **描述**: puid=239448447
- **请求**: `GET /api/info?puid=239448447&_token=83506aa06d929e82...`
- **等级**: CRITICAL
- **结论**: 场景B IDOR: 越权成功!
- **响应**:
```json
{"code": 2, "data": {"host": "sync.ananas.chaoxing.com", "hosts": ["sync2.ananas.chaoxing.com", "sync3.ananas.chaoxing.com"], "root": "up/336/312/239448447", "froot": "336/312/239448447", "p": "44604c9884a7229121549849afaf88ba390248ae48a3eb35", "u": "80e80ac5e63d7b56780e86c50a866292", "usedsize": 3663392, "disksize": 10737418240, "limitType": ["com", "apk", "deb", "ipa", "pxl", "dmg", "pkg", "0", "000", "001", "7z", "ace", "ain", "alz", "apz", "ar", "arc", "ari", "arj", "axx", "bh", "bhx", "boo", "bz", "bza", "bz2", "c00", "c01", "c02", "cab", "car", "cbr", "cbz", "cp9", "cpgz", "cpt", "dar", 
```


### P4-03: 完整Cookie替换+场景B IDOR [存在风险]

- **描述**: puid=239448447
- **请求**: `GET /api/info?puid=239448447&_token=83506aa06d929e82... (完整替换Cookie)`
- **等级**: CRITICAL
- **结论**: 完整替换后场景B: 越权成功!
- **响应**:
```json
{"code": 2, "data": {"host": "sync.ananas.chaoxing.com", "hosts": ["sync2.ananas.chaoxing.com", "sync3.ananas.chaoxing.com"], "root": "up/336/312/239448447", "froot": "336/312/239448447", "p": "44604c9884a7229121549849afaf88ba390248ae48a3eb35", "u": "80e80ac5e63d7b56780e86c50a866292", "usedsize": 3663392, "disksize": 10737418240, "limitType": ["com", "apk", "deb", "ipa", "pxl", "dmg", "pkg", "0", "000", "001", "7z", "ace", "ain", "alz", "apz", "ar", "arc", "ari", "arj", "axx", "bh", "bhx", "boo", "bz", "bza", "bz2", "c00", "c01", "c02", "cab", "car", "cbr", "cbz", "cp9", "cpgz", "cpt", "dar", 
```


### P4-04: base7+_d替换+场景A(同Token跨puid) [安全]

- **描述**: puid=239448447, token=token1
- **请求**: `GET /api/info?puid=239448447&_token=721b618c5d4593ec...`
- **等级**: INFO
- **结论**: base7+_d+场景A: 被阻止: 错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23
- **响应**:
```json
{"result": false, "msg": "错误的_token值：721b618c5d4593ecfe7e2ee3a2275c23"}
```


### P5-01: _d篡改为随机时间戳(自己puid) [安全]

- **描述**: _d=1779702695744
- **请求**: `POST getTopic puid=252798154`
- **等级**: INFO
- **结论**: 随机_d+自己puid: result=0, msg=登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-02: _d替换为账号2的_d(自己puid) [安全]

- **描述**: _d=1779702694015
- **请求**: `POST getTopic puid=252798154`
- **等级**: INFO
- **结论**: 账号2_d+自己puid: result=0, msg=登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-03: base7替换+保留自己_d [安全]

- **描述**: 替换身份Cookie但_d不变
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: base7+自己_d: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-04: 最小替换-UID+_d [安全]

- **描述**: UID=239448447, _d=1779702694015
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: UID+_d: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-05-a: 最小替换集-UID+_d [安全]

- **描述**: 替换['UID', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: UID+_d: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-05-b: 最小替换集-UID+_uid+_d [安全]

- **描述**: 替换['UID', '_uid', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: UID+_uid+_d: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-05-c: 最小替换集-UID+_uid+uf+_d [安全]

- **描述**: 替换['UID', '_uid', 'uf', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: INFO
- **结论**: UID+_uid+uf+_d: 被阻止: 登录信息异常[806001]
- **响应**:
```json
{"result": 0, "errorMsg": "登录信息异常[806001]"}
```


### P5-05-d: 最小替换集-UID+_uid+uf+vc3+_d [存在风险]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: UID+_uid+uf+vc3+_d: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P5-05-e: 最小替换集-UID+_uid+uf+vc3+xxtenc+_d [存在风险]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: UID+_uid+uf+vc3+xxtenc+_d: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P5-05-f: 最小替换集-6身份+_d [存在风险]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', 'cx_p_token', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: 6身份+_d: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P5-05-g: 最小替换集-7身份+_d [存在风险]

- **描述**: 替换['UID', '_uid', 'uf', 'vc3', 'xxtenc', 'cx_p_token', 'p_auth_token', '_d']
- **请求**: `POST getTopic puid=239448447`
- **等级**: CRITICAL
- **结论**: 7身份+_d: 绕过成功!
- **响应**:
```json
{"msg": "sucess", "result": 1, "data": {"flag": 0, "role": 1, "s_praisecount": "13", "text_content": "http://mp.weixin.qq.com/s?__biz=MzA3OTU1MTU4NQ==&mid=205556616&idx=1&sn=9d56d130e542417bc5bb54452728c233&scene=5#rd \n\n    互联网+时代教育，青岛全国推进学校信息化校长论坛视频今天上午的视频全部收齐，敬请观看\n武汉经开区实验小学校长做了 咱们产品慕课的报告\n叶馆作为嘉宾做了现场对话，是对话嘉宾里面最精彩的一位嘉宾。", "creator_fid": 0, "title": "", "uuid": "u10000", "isDataTrack": 0, "create_puid": 17416512, "score": {"scoreRange": {"minscore": 0, "maxscore": 100}, "total_num": 0, "total_score": 0, "my_score": 0, "avg_score": 0}, "update_time": 1432482035209, "createrFacility": "", "top
```


### P6-01: 基线-账号1正常访问groupweb [安全]

- **描述**: bbsid=03f39c270176b073fd4cf40fc26a44b1
- **请求**: `GET getResourceList`
- **等级**: INFO
- **结论**: 基线: result=1
- **响应**:
```json
{"result": 1, "userAuth": {"groupAuth": {"addData": 0, "addDataFolder": 0, "addLebel": 0, "addManager": 0, "addMem": 0, "addTopicFolder": 0, "anonymousAddReply": 0, "anonymousAddTopic": 0, "batchOperation": 0, "delData": 0, "delDataFolder": 0, "delMem": 0, "delTopicFolder": 0, "dismiss": 0, "groupChat": 0, "isShowCircleChatButton": 0, "isShowCircleCloudButton": 0, "isShowCompanyButton": 0, "isShowPriceButton": 0, "join": 1, "memberShowRankSet": 0, "modifyDataFolder": 0, "modifyExpose": 0, "modifyName": 0, "modifyShowPic": 0, "modifyTopicFolder": 0, "modifyVisibleState": 0, "onlyMgrScoreSet": 0
```


### P6-02: base7+_d替换后访问groupweb [安全]

- **描述**: bbsid=03f39c270176b073fd4cf40fc26a44b1
- **请求**: `GET getResourceList (替换Cookie)`
- **等级**: INFO
- **结论**: Cookie替换后groupweb: 被阻止: 请加入小组后再操作
- **响应**:
```json
{"result": 0, "msg": "请加入小组后再操作"}
```

---
## 五、技术分析

### 5.1 Cookie身份校验机制
```
服务端Cookie校验模型:
  ├─ Cookie包完整性校验:
  │   ├─ 身份Cookie(UID/_uid/uf/vc3/xxtenc/cx_p_token/p_auth_token) 必须来自同一会话
  │   └─ _d Cookie 必须与身份Cookie的会话匹配 ← 关键!
  ├─ p_auth_token JWT签名校验: ❌ 未验证! 伪造签名的JWT被接受!
  └─ Cookie-puid一致性: 校验Cookie UID与请求puid匹配 ✅
```


### 5.2 绕过原理
```
正常请求:
  Cookie: UID=A, _d=timestamp_A, p_auth_token=JWT_A(signed_for_A)
  puid=A → 校验通过 ✅

篡改请求(缺少_d):
  Cookie: UID=B, _d=timestamp_A, p_auth_token=JWT_B(signed_for_B)
  puid=B → _d与身份Cookie不匹配 → 校验失败 ❌

篡改请求(含_d):
  Cookie: UID=B, _d=timestamp_B, p_auth_token=JWT_B(signed_for_B)
  puid=B → _d与身份Cookie匹配 → 校验通过 ✅ ← 绕过!
```


### 5.3 安全影响评估

**groupyd.chaoxing.com (高危)**:

- 攻击者只需获取目标用户的身份Cookie(7个)+`_d` Cookie即可冒充目标用户

- 这8个Cookie值可通过XSS、网络嗅探、恶意插件等途径获取

- 一旦获取，攻击者可以目标用户身份执行所有groupyd API操作


**pan-yz.chaoxing.com (中危)**:

- Cookie篡改不影响个人云盘的_token校验

- 但场景B IDOR（使用目标Token+目标puid）仍然有效

- Token比Cookie更容易泄露（通过URL参数传递）


---
## 六、修复建议

1. **服务端不应依赖Cookie包完整性作为唯一校验**: 应从服务端Session中直接获取用户身份，而非信任客户端Cookie

2. **_d Cookie不应参与身份校验**: `_d`作为登录时间戳，不应成为身份校验的关键因素

3. **Cookie与Session绑定**: 服务端应维护Cookie与服务器端Session的映射关系，而非仅校验Cookie包内部一致性

4. **个人云盘_token与Session绑定**: _token应与当前Session关联，防止跨Session使用

5. **HttpOnly + Secure标记**: 所有身份相关Cookie应设置HttpOnly和Secure属性
6. **JWT签名验证**: groupyd必须验证p_auth_token的JWT签名，拒绝签名不匹配的JWT
7. **最小权限原则**: 减少Cookie校验依赖的Cookie数量，应从服务端Session获取身份而非信任客户端Cookie组合
