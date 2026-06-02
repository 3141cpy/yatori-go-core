# 签到状态修改漏洞安全评估报告


**审计日期**: 2026-06-02 12:15:46


**教师账号**: puid=402644510


**学生账号**: puid=431407443


**目标课程**: 国际学院2025级4班


---

## 一、测试结果汇总


- **总测试数**: 18
- **发现隐患数**: 2

- **严重(CRITICAL)**: 0
- **高危(HIGH)**: 0

- **中危(MEDIUM)**: 0
- **低危(LOW)**: 2


---

## 二、签到API链路分析


### 2.1 签到完整流程


```
1. GET /mycourse/backclazzdata → 获取课程列表(courseId, classId, cpi)

2. GET /ppt/activeAPI/taskactivelist → 获取活动列表(activeId, activeType)

3. GET /newsign/preSign?activeId=X → 获取签到页面(含签到参数)

4. POST /pptSign/stuSignajax → 执行签到(activeId, uid, latitude, longitude, address)

5. GET /pptSign/signedResult → 查看签到结果
```


### 2.2 签到类型


| activeType | 签到类型 | 特殊参数 |
|---|---|---|

| 1 | 普通签到 | 无 |
| 2 | 位置签到 | latitude, longitude, address |
| 3 | 手势签到 | signCode |
| 4 | 签到码签到 | signCode |


---

## 三、各测试项详细结果


### T1-01: 教师获取课程和活动信息 [存在风险]


- **API端点**: `/mycourse/backclazzdata + /ppt/activeAPI/taskactivelist`

- **测试类型**: 调查

- **风险等级**: LOW

- **结论**: 教师端: 课程数=9, 活动数=17, 签到活动数=17


- **证据**: 目标课程: 国际学院2025级4班, courseId=260554328, classId=141377820


### T1-02: 学生获取课程和活动信息 [存在风险]


- **API端点**: `/mycourse/backclazzdata + /ppt/activeAPI/taskactivelist`

- **测试类型**: 调查

- **风险等级**: LOW

- **结论**: 学生端: 课程数=2, 活动数=0, 签到活动数=0


- **证据**: 学生puid=431407443, 教师puid=402644510


### T2-01: 学生请求签到前页面 [安全]


- **API端点**: `/newsign/preSign`

- **测试类型**: 信息获取

- **风险等级**: MEDIUM

- **结论**: 学生访问签到前页面: 失败，签到参数: {}


- **证据**: HTTP 500, 页面长度=224


### T3-1000161102850: 学生对位置签到签到执行签到操作 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 签到状态修改

- **风险等级**: LOW

- **结论**: 学生对已结束的位置签到签到(id=1000161102850)执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点617684.0米，不在可签到范围内。"}


### T3-1000160165622: 学生对位置签到签到执行签到操作 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 签到状态修改

- **风险等级**: LOW

- **结论**: 学生对已结束的位置签到签到(id=1000160165622)执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点617692.0米，不在可签到范围内。"}


### T3-1000159168580: 学生对位置签到签到执行签到操作 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 签到状态修改

- **风险等级**: LOW

- **结论**: 学生对已结束的位置签到签到(id=1000159168580)执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点617684.0米，不在可签到范围内。"}


### T3-1000158940384: 学生对位置签到签到执行签到操作 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 签到状态修改

- **风险等级**: LOW

- **结论**: 学生对已结束的位置签到签到(id=1000158940384)执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点617684.0米，不在可签到范围内。"}


### T3-1000158547913: 学生对位置签到签到执行签到操作 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 签到状态修改

- **风险等级**: LOW

- **结论**: 学生对已结束的位置签到签到(id=1000158547913)执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点617684.0米，不在可签到范围内。"}


### T4-01: 伪造uid为教师uid执行签到 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 参数篡改

- **风险等级**: CRITICAL

- **结论**: 使用教师uid(402644510)执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点1.2294171E7米，不在可签到范围内。"}


### T4-02: 修改appType参数执行签到 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 参数篡改

- **风险等级**: MEDIUM

- **结论**: 修改appType=1执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点1.2294171E7米，不在可签到范围内。"}


### T4-03: 伪造位置签到（含经纬度和地址） [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 参数篡改

- **风险等级**: HIGH

- **结论**: 伪造位置签到(上海): 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点827351.0米，不在可签到范围内。"}


### T4-04: 伪造deviceCode执行签到 [安全]


- **API端点**: `/pptSign/stuSignajax`

- **测试类型**: 参数篡改

- **风险等级**: MEDIUM

- **结论**: 伪造deviceCode执行签到: 被拒绝


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "距教师指定签到地点1.2294171E7米，不在可签到范围内。"}


### T5-01: 学生查看签到结果 [安全]


- **API端点**: `/pptSign/signedResult`

- **测试类型**: 信息获取

- **风险等级**: MEDIUM

- **结论**: 学生查看签到结果: 被拒绝


- **证据**: HTTP 500, 响应前500字: <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html>
<head><title>500 Internal Server Error</title></head>
<body>
<center><h1>500 Internal Server Error</h1></center>
<hr><center>tengine</center>
</body>
</html>



### T5-02: 学生调用教师补签API修改签到状态 [安全]


- **API端点**: `/pptSign/teacherSignForStu`

- **测试类型**: 垂直越权

- **风险等级**: CRITICAL

- **结论**: 学生调用教师补签API: 被拒绝


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T5-03: 学生查看其他学生签到状态 [安全]


- **API端点**: `/pptSign/stuSignResult`

- **测试类型**: 水平越权

- **风险等级**: HIGH

- **结论**: 学生查看其他学生签到状态: 被拒绝


- **证据**: HTTP 500, 响应前500字: <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html>
<head><title>500 Internal Server Error</title></head>
<body>
<center><h1>500 Internal Server Error</h1></center>
<hr><center>tengine</center>
</body>
</html>



### T6-01: 教师查看签到结果 [安全]


- **API端点**: `/pptSign/signedResult`

- **测试类型**: 基线

- **风险等级**: LOW

- **结论**: 教师查看签到结果: 失败


- **证据**: HTTP 500, 响应前500字: <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html>
<head><title>500 Internal Server Error</title></head>
<body>
<center><h1>500 Internal Server Error</h1></center>
<hr><center>tengine</center>
</body>
</html>



### T6-02: 教师修改学生签到状态 [安全]


- **API端点**: `/pptSign/teacherSignForStu`

- **测试类型**: 基线

- **风险等级**: LOW

- **结论**: 教师修改学生签到状态: 失败，此API为学生越权测试的基准


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T6-03: 教师查看签到活动详情 [安全]


- **API端点**: `/ppt/activeAPI/activeDetail`

- **测试类型**: 基线

- **风险等级**: LOW

- **结论**: 教师查看签到活动详情: 失败


- **证据**: HTTP 500, 响应前300字: <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html>
<head><title>500 Internal Server Error</title></head>
<body>
<center><h1>500 Internal Server Error</h1></center>
<hr><center>tengine</center>
</body>
</html>



---

## 四、漏洞利用条件分析


### 4.1 签到状态修改的利用条件


根据测试结果，签到状态修改的利用条件取决于以下因素：


1. **签到活动是否已结束**: 已结束的签到活动是否仍可执行签到操作

2. **签到类型**: 不同签到类型的参数校验严格程度不同

3. **位置校验**: 位置签到是否校验经纬度的真实性

4. **设备校验**: 是否校验deviceCode防止同设备重复签到

5. **时间校验**: 是否校验签到时间是否在活动有效期内


---

## 五、修复建议


### 5.1 紧急修复


1. **已结束签到禁止签到**: 服务端必须校验签到活动是否仍在有效期内

2. **位置校验增强**: 位置签到应校验经纬度是否在合理范围内

3. **教师补签API权限控制**: /pptSign/teacherSignForStu 必须校验请求者是否为课程教师


### 5.2 中期加固


4. **签到请求签名**: 签到请求应包含服务端验证的签名，防止参数篡改

5. **deviceCode绑定**: 设备码应与服务端记录绑定，防止伪造

6. **签到频率限制**: 防止签到请求重放攻击

7. **签到结果访问控制**: 学生只能查看自己的签到状态

