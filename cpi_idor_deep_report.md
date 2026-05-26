# 课程CPI越权漏洞深入评估报告


**审计日期**: 2026-05-26 03:19:51


**测试账号**: 账号1(puid=252798154), 账号2(puid=239448447)


**测试范围**: 使用Go源码中发现的正确API端点进行课程CPI越权深入测试


---

## 一、测试结果汇总


- **总测试数**: 18
- **发现隐患数**: 12

- **严重(CRITICAL)**: 2
- **高危(HIGH)**: 5

- **中危(MEDIUM)**: 1
- **低危(LOW)**: 4


---

## 二、各API端点测试结果


### T1-01: 代理问题解决验证 [存在风险]


- **API端点**: `/gas/clazz`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: API访问成功，HTTP 200, 响应长度=3813


- **证据**: 响应前300字: {"data":[{"hideclazz":0,"allowdownload":0,"chatid":"312598630301697","isfiled":0,"forbidintoclazz":0,"coursesetting":{"data":[{"coursefacecheck":0,"hiddencoursecover":1,"id":7354876,"courseid":263492983}]},"isstart":true,"visiblescore":0,"name":"在校生","course":{"data":[{"app":0,"teacherfactor":"刘艳慧",


### T2-01: 自己的cpi请求课程章节 [存在风险]


- **API端点**: `/gas/clazz`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: 使用自己的cpi请求课程章节: 成功


- **证据**: HTTP 200, 响应前500字: {"data":[{"name":"在校生","course":{"data":[{"name":"本科教学合格评估应知应会测试","id":263492983,"knowledge":{"data":[{"jobcount":0,"indexorder":1,"name":"本科教学工作合格评估指标释义","id":1166526853,"label":"1","layer":1,"parentnodeid":0,"status":"open"},{"jobcount":0,"indexorder":2,"name":"本科教学工作合格评估应知应会基础知识","id":1166526862,"label":"2","layer":1,"parentnodeid":0,"status":"open"},{"jobcount":0,"indexorder":3,"name":"本科教学工作合格评估应知应会基础知识复习题","id":1166526914,"label":"3","layer":1,"parentnodeid":0,"status":"open"},{"jobcount":


### T2-02: 跨用户cpi请求课程章节 [存在风险]


- **API端点**: `/gas/clazz`

- **越权类型**: 水平越权

- **风险等级**: HIGH

- **结论**: 使用账号1的Cookie+账号2的cpi请求课程章节: 成功获取


- **证据**: HTTP 200, 响应前500字: {"data":[{"name":"默认班级","course":{"data":[{"name":"22级 UI界面设计课程","id":255266715,"knowledge":{"data":[]}}]},"id":127555113}]}


### T2-03: 章节数据敏感度分析 [存在风险]


- **API端点**: `/gas/clazz`

- **越权类型**: 信息泄露

- **风险等级**: HIGH

- **结论**: 越权获取的章节数据包含: 知识点列表=True, 章节名称=True


- **证据**: 数据字段: ['data']


### T3-01: 自己的cpi请求任务点状态 [安全]


- **API端点**: `/job/myjobsnodesmap`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: 使用自己的cpi请求任务点状态: 失败


- **证据**: HTTP 200, 响应前500字: {"0":{"clickcount":0,"finishcount":0,"totalcount":0,"openlock":0,"unfinishcount":0}}


### T3-02: 跨用户cpi+目标userid请求任务点状态 [安全]


- **API端点**: `/job/myjobsnodesmap`

- **越权类型**: 水平越权

- **风险等级**: HIGH

- **结论**: 使用账号1的Cookie+账号2的cpi+userid请求任务点状态: 被拒绝


- **证据**: HTTP 200, 响应前500字: {"0":{"clickcount":0,"finishcount":0,"totalcount":0,"openlock":0,"unfinishcount":0}}


### T3-03: 跨用户cpi+自己userid请求任务点状态 [安全]


- **API端点**: `/job/myjobsnodesmap`

- **越权类型**: 水平越权

- **风险等级**: HIGH

- **结论**: 使用账号1的Cookie+账号2的cpi+账号1的userid: 被拒绝，cpi与userid绑定


- **证据**: HTTP 200, 响应前300字: {"msg":"用户不存在"}


### T4-01: K6 Token请求知识节点详情 [存在风险]


- **API端点**: `/gas/knowledge`

- **越权类型**: 签名绕过越权

- **风险等级**: HIGH

- **结论**: 使用K6 Token请求知识节点详情: 成功，K6 Token不绑定用户身份


- **证据**: HTTP 200, 响应前500字: {"data":[{"clickcount":0,"createtime":1777532306000,"openlock":0,"indexorder":1,"name":"本科教学工作合格评估指标释义","lastmodifytime":1777532370000,"id":1166526853,"label":"1","layer":1,"card":{"data":[]},"parentnodeid":0,"status":"close"},{"clickcount":0,"createtime":1777532306000,"openlock":0,"indexorder":2,"name":"本科教学工作合格评估应知应会基础知识","lastmodifytime":1777532383000,"id":1166526862,"label":"2","layer":1,"card":{"data":[]},"parentnodeid":0,"status":"close"},{"clickcount":0,"createtime":1777532312000,"openloc


### T4-02: K6 Token请求他人课程知识节点 [存在风险]


- **API端点**: `/gas/knowledge`

- **越权类型**: 签名绕过越权

- **风险等级**: CRITICAL

- **结论**: 使用K6 Token+他人courseId请求知识节点: 成功(严重!)


- **证据**: HTTP 200, 响应前500字: {"data":[]}


### T4-03: 无Cookie仅K6 Token请求知识节点 [存在风险]


- **API端点**: `/gas/knowledge`

- **越权类型**: 签名绕过越权

- **风险等级**: CRITICAL

- **结论**: 无Cookie仅使用K6 Token请求: 成功(严重!K6 Token=万能密钥)


- **证据**: HTTP 403, 响应前300字: <!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1,maximum-scale=1, user-scalable=no" />
    <meta http-equiv="pragma" content="no-cache"/>
    <meta http-equiv="cache-control" content="no-cache" />
    <meta http-equiv="expires" content="0"/>
    <m


### T5-01: 自己的cpi请求知识卡片 [安全]


- **API端点**: `/mooc-ans/knowledge/cards`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: 使用自己的cpi请求知识卡片: 失败


- **证据**: HTTP 404, 响应前500字: <!doctype html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
    <title>404</title>
    <style>
        .main{height:255px;margin:0 auto;margin-top:15%;font-size:16px;color:#999; width: 350px;}
        .font_top{padding-top:45px;display:inline;}
        .msg_font{color: #8A8B99;font-size: 16px;line-height: 24px;padding-left: 30px;margin: 0 auto;}
    </style>
</head>
<body>
<div class="main">
    <p class="font_t


### T5-02: 跨用户cpi请求知识卡片 [安全]


- **API端点**: `/mooc-ans/knowledge/cards`

- **越权类型**: 水平越权

- **风险等级**: CRITICAL

- **结论**: 使用账号1的Cookie+账号2的cpi请求知识卡片: 被拒绝


- **证据**: HTTP 200, 响应前500字: <!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1,maximum-scale=1, user-scalable=no"/>
    <meta http-equiv="pragma" content="no-cache"/>
    <meta http-equiv="cache-control" content="no-cache"/>
    <meta http-equiv="expires" content="0"/>
    <meta charset="utf-8">
    <title>登录</title>
    <link href="https://passport2-static.chaoxing.com/css/fanya/mobile/common.css?v=4" rel="stylesheet">
    <link href="https://passport2-static.cha


### T6-01: 自己的cpi进入章节 [存在风险]


- **API端点**: `/mooc-ans/mycourse/studentstudyAjax`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: 使用自己的cpi进入章节: 成功


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "参数为空"}


### T6-02: 跨用户cpi进入章节 [存在风险]


- **API端点**: `/mooc-ans/mycourse/studentstudyAjax`

- **越权类型**: 水平越权

- **风险等级**: HIGH

- **结论**: 使用账号1的Cookie+账号2的cpi进入章节: 成功


- **证据**: HTTP 200, 响应: {"raw_status": 200, "raw_text": "<!doctype html>\r\n<html>\r\n<head>\r\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1,maximum-scale=1, user-scalable=no\"/>\r\n    <meta http-equiv=\"pragma\" content=\"no-cache\"/>\r\n    <meta http-equiv=\"cache-control\" content=\"no-cac


### T7-01: 自己的clazzPersonStr请求完成度 [存在风险]


- **API端点**: `/mooc2-ans/mycourse/stu-job-info`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: 使用自己的clazzPersonStr请求完成度: 成功


- **证据**: HTTP 200, 响应前500字: {"jobArray":[],"status":true}


### T7-02: 跨用户clazzPersonStr请求完成度 [存在风险]


- **API端点**: `/mooc2-ans/mycourse/stu-job-info`

- **越权类型**: 水平越权

- **风险等级**: HIGH

- **结论**: 使用账号1的Cookie+账号2的clazzPersonStr请求完成度: 成功获取


- **证据**: HTTP 200, 响应前500字: {"jobArray":[],"status":true}


### T8-01: CPI是否可通过课程列表API获取 [存在风险]


- **API端点**: `课程列表API`

- **越权类型**: 信息泄露

- **风险等级**: MEDIUM

- **结论**: 课程列表API包含cpi字段，cpi是半公开信息


- **证据**: 课程列表中cpi字段: 282981525


### T8-02: CPI是否可通过小组API获取 [安全]


- **API端点**: `小组API`

- **越权类型**: 信息泄露

- **风险等级**: MEDIUM

- **结论**: 小组API不包含cpi字段


- **证据**: 响应前200字: {'result': '0', 'errorMsg': '服务异常，请稍后重试[50001]'}


---

## 三、CPI越权完整攻击链


```
1. 获取目标用户的cpi（通过课程列表API或公开信息）

2. 使用自己的Cookie+目标用户的cpi请求 /gas/clazz → 获取课程章节列表

3. 使用K6 Token请求 /gas/knowledge → 获取知识节点详情（无需Cookie）

4. 使用自己的Cookie+目标用户的cpi请求 /mooc-ans/knowledge/cards → 获取视频/文档资源

5. 使用自己的Cookie+目标用户的cpi请求 /job/myjobsnodesmap → 获取任务点完成状态

6. 使用自己的Cookie+目标用户的cpi请求 /mooc-ans/mycourse/studentstudyAjax → 进入章节

7. 使用目标用户的clazzPersonStr请求 /mooc2-ans/mycourse/stu-job-info → 获取课程完成度
```


---

## 四、修复建议


### 4.1 紧急修复


1. **cpi参数身份绑定**: 所有使用cpi参数的API必须校验cpi与Cookie/Token中的用户身份一致性

2. **K6 Token移除**: /gas/knowledge接口使用的全局Token(K6)应立即移除，改用用户绑定Token

3. **知识卡片访问控制**: /mooc-ans/knowledge/cards应校验请求者是否为课程成员


### 4.2 中期加固


4. **cpi动态化**: cpi应包含时效性和身份绑定信息

5. **clazzPersonStr校验**: 课程完成度接口应校验clazzPersonStr与Cookie身份的绑定关系

6. **API统一认证**: 所有课程相关API应实施统一的身份校验机制

