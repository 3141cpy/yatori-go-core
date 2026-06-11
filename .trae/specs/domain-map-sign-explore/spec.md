# 基于域名映射表的签到漏洞全面探索 Spec (v2 - 深度版)

## Why
第一轮域名探索仅覆盖了约20个域名（5个第一梯队 + 15个第二三梯队），但用户提供的domainMap包含100+内部服务域名。剩余80+域名中可能存在：
- 签到状态修改的替代API端点
- 鉴权机制较弱的内部服务
- 代理/网关端点可绕过认证
- 未公开的签到详情查看接口
- 跨域会话传递漏洞

## What Changes
- 对domainMap中剩余80+未测试域名进行签到API探索
- 重点测试学习/教学/签到直接相关域名
- 测试代理路径(noteyd/proxy)和特殊路径(epub/board/projectapp)的认证绕过
- 测试跨域Cookie/Session传递
- 发现新的签到状态修改漏洞

## Impact
- Affected domains: domainMap中所有未测试域名
- Test accounts: 学生 18436633997/3.1415926Cpy (puid=431407443), 教师 19712720708/3.1415926Cpy (puid=402644510)
- Course: courseId=257485372, classId=132821141 / courseId=262934472, classId=145110605

## 已完成探索（第一轮结果）
- statisticyd.chaoxing.com — 可达但无签到API
- k.chaoxing.com — POST返回405
- study-api.chaoxing.com — 返回500
- office.chaoxing.com — 404
- task.chaoxing.com — 404
- mobile.fanya.chaoxing.com — 无签到API
- mobilelearn.fy.chaoxing.com — 有签到功能但认证与主域一致（仅HTTP）
- mooc2-ans.chaoxing.com — 无签到API
- bigdata-api/bigdata-ans — 无签到API
- fystat-ans/stat2-ans — 无签到API
- passport2-api/uc/uc1-ans/structureyd/v1/mobilewx/manage — 无签到API

## 新增探索域名

### 第四梯队：学习/教学核心域名（最高优先级）
1. **learn.chaoxing.com** (learnDomain/learnDomainHttps) — 学习域名，最可能托管签到功能
2. **mobilelearn.chaoxing.com** (mobilelearnDomain/mobilelearnDomainHttps) — 移动学习主域名
3. **mooc1.chaoxing.com** (mooc1Domain/mooc1DomainHttps) — MOOC1主域名
4. **mooc1-2.chaoxing.com** (mooc1_2Domain) — MOOC1-2变体
5. **mooc1-3.chaoxing.com** (mooc1_3Domain) — MOOC1-3变体
6. **mooc.chaoxing.com** (moocDomain/moocDomainHttps) — MOOC主域名
7. **i.mooc.chaoxing.com** (iMoocDomain) — iMooc域名
8. **pc.chaoxing.com** (pcDomain) — PC端域名
9. **m.chaoxing.com** (mDomain) — 移动端域名
10. **i.chaoxing.com** (iDomain) — i域名

### 第五梯队：群组/首页/特殊域名
11. **groupyd.chaoxing.com** (GroupDomain/GroupDomainHttps) — 群组域名
12. **groupweb.chaoxing.com** (GroupWebDomain/GroupWebDomainHttps) — 群组Web域名
13. **groupyd2.chaoxing.com** (groupweb2DomainHttps) — 群组2域名
14. **home-yd.chaoxing.com** (homeYdDomain) — 首页YD域名
15. **home.yd.chaoxing.com** (homeDomain) — 首页域名
16. **homewh.chaoxing.com** (homeWhDomainHttps) — 首页WH域名
17. **special.chaoxing.com** (specialDomain/specialDomainHttps) — 特殊域名
18. **special1.rhky.com** (special1DomainHttps) — 特殊1域名
19. **special2.rhky.com** (special2DomainHttps) — 特殊2域名
20. **special.rhky.com** (specialRhykDomainHttps) — 特殊RHKY域名
21. **specialpack.chaoxing.com** (SpecialPackDomain/SpecialPackDomainHttps) — 特殊包域名

### 第六梯队：应用/API/资源域名
22. **apps.chaoxing.com** (appsDomain) — 应用域名
23. **apps.ananas.chaoxing.com** (appsDomainHttps) — 应用Ananas域名
24. **appswh.chaoxing.com** (appsWhDomain/appsWhDomainHttps) — 应用WH域名
25. **cs-api.chaoxing.com** (csAPIDomain) — CS API域名
26. **resource.chaoxing.com** (resourceDomain/resourceDomainHttps) — 资源域名
27. **fe.chaoxing.com** (feDomain) — 前端域名
28. **mh.chaoxing.com** (menhuDomain) — 门户域名

### 第七梯队：用户/通知/消息域名
29. **user.yd.chaoxing.com** (UserDomain) — 用户YD域名
30. **useryd.chaoxing.com** (UserDomainHttps) — 用户YD HTTPS域名
31. **notice.chaoxing.com** (NoticeDomain/NoticeDomainHttps) — 通知域名
32. **message.chaoxing.com** (messageDomain/messageDomainHttps) — 消息域名
33. **im.chaoxing.com** (imDomain/imDomainHttps) — IM域名
34. **api.im.chaoxing.com** (apiImDomain) — IM API域名
35. **api1.im.chaoxing.com** (imApi1Domain) — IM API1域名
36. **contactsyd.chaoxing.com** (contactsDomainHttps) — 通讯录域名

### 第八梯队：代理/特殊路径域名（认证绕过重点）
37. **noteyd.chaoxing.com** (NoteDomain/NoteDomainHttps) — 笔记域名
38. **noteyd.chaoxing.com/proxy** (ProxyDomain/ProxyDomainHttps) — 代理路径（重点！可能绕过认证）
39. **noteyd.chaoxing.com/comm/** (commDomain) — 通信路径
40. **noteyd.chaoxing.com/comp/** (compDomain) — 组件路径
41. **appswh.chaoxing.com/epub** (EPubDomainHttps) — EPub路径
42. **appswh.chaoxing.com/board** (boardDomainHttps) — Board路径
43. **appswh.chaoxing.com/projectapp** (ProjectappDomainHttps) — ProjectApp路径
44. **appswh.chaoxing.com/hbqyg** (hbqygDomain) — HBQYG路径

### 第九梯队：其他可能相关域名
45. **exportyd.chaoxing.com** (exportDomain/exportDomainHttps) — 导出域名
46. **previewyd.chaoxing.com** (previewDomainHttps) — 预览域名
47. **wordyd.chaoxing.com** (wordDomainHttps) — Word域名
48. **convertservice.chaoxing.com** (convertHttps) — 转换服务
49. **transyd.chaoxing.com** (transydDomainHttps) — 传输域名
50. **merger.yd.chaoxing.com** (mergerDomain) — 合并域名
51. **commendyd.chaoxing.com** (commendDomainHttps) — 推荐域名
52. **cooperateyd.chaoxing.com** (cooperateDomainHttps) — 合作域名
53. **contestyd.chaoxing.com** (contestDomain) — 竞赛域名
54. **imageproxy.chaoxing.com** (imageproxyDomainHttps) — 图片代理
55. **x.chaoxing.com** (xDomainHttps) — X域名
56. **wx.chaoxing.com** (wechatDomain) — 微信域名
57. **passport2.chaoxing.com** (passport2Domain/passport2DomainHttps) — 认证域名（非API）
58. **sso.chaoxing.com** (ssoDomain) — SSO域名

### 第十梯队：AI/课堂/会议/直播域名
59. **ai.chaoxing.com** (aiDomainHttps) — AI域名
60. **airead.chaoxing.com** (aireadHttps) — AI阅读域名
61. **aivideo.chaoxing.com** (aivideoHttps) — AI视频域名
62. **kb.chaoxing.com** (kbDomainHttps) — KB域名
63. **meeting.chaoxing.com** (rkDomain/rkDomainHttps) — 会议域名
64. **live.chaoxing.com** (liveDomainHttps) — 直播域名
65. **live.superlib.com** (liveSuperlibDomainHttps) — 直播Superlib域名
66. **zhibo.chaoxing.com** (zhiboDomainHttps) — 直播域名
67. **intellectual-education-k8s.chaoxing.com** (intellectualDomain) — 智慧教育K8s
68. **ktlog.chaoxing.com** (ktLogDomain/ktLogDomainHttps) — 课堂日志域名
69. **wps.chaoxing.com** (wpsDomainHttps) — WPS域名
70. **jcuc.chaoxing.com** (jcucDomainHttps) — JCUC域名
71. **jcxygl.chaoxing.com** (AlmightyPrintHttps) — 教务管理域名

### 第十一梯队：泛亚/教育/其他域名
72. **paycenter.fanya.chaoxing.com** (paycenterDomain) — 支付中心
73. **fanya.zyk2.chaoxing.com** (fanYaZyk2Domain) — 泛亚ZYK2
74. **fanyalubodata.fanya.chaoxing.com** (fyLbDomainHttps) — 泛亚鲁班数据
75. **fystat1-1.fy.chaoxing.com** (fystat1_1FyDomain) — 泛亚统计1-1
76. **astats.fy.chaoxing.com** (astatsFyDomain) — AStats泛亚
77. **gdhydx.jxjy.chaoxing.com** (gdhydxDomainHttps) — 广东海洋大学继续教育
78. **cjkt.jxjy.chaoxing.com** (jjDomain) — 继续教育课堂
79. **hust.fanya.chaoxing.com** (hustFanya) — 华科泛亚
80. **mbti.basicedu.chaoxing.com** (mbtiDomainHttps) — MBTI基础教育
81. **ss.chaoxing.com** (ssDomain) — SS域名
82. **ss.zhizhen.com** (ssZhizhenDomain) — SS超星
83. **auth.zhizhen.com** (authZhizhenDomain) — 认证超星
84. **ketang-zhizhen.chaoxing.com** (ketangZhizhenDomain) — 课堂超星
85. **qikan.chaoxing.com** (qikanDomain) — 期刊域名
86. **16q.cn** (shortUrlDomain) — 短链域名
87. **sms.chaoxing.com** (smsDomain) — 短信域名
88. **swfilter.chaoxing.com** (swfilterDomain) — 过滤域名
89. **cv-p.chaoxing.com** (cvDomain) — CV域名
90. **vspace.chaoxing.com** (vspaceDomain) — VSpace域名
91. **ypdownload.chaoxing.com** (ypDomainHttps) — YP下载域名
92. **edas.chaoxing.com** (edasDomainHttps) — EDAS域名
93. **jwdatatb.chaoxing.com** (jwDomain) — 教务数据域名
94. **jwdatatb.fy.chaoxing.com** (jwFyDomain) — 教务数据泛亚域名
95. **specie.chaoxing.com** (specieDomainHttps) — Specie域名
96. **rec2.chaoxing.com** (rec2Domain) — Rec2域名
97. **recv1-tongxueshe.chaoxing.com** (tongxuesheDomainHttps) — 同学社域名
98. **robot.chaoxing.com** (RobotHttps) — 机器人域名
99. **robot-lc.chaoxing.com** (RobotLcHttps) — 机器人LC域名
100. **pan-yz.chaoxing.com** (panDomain/panDomainHttps) — 网盘域名
101. **d0.ananas.chaoxing.com** (d0Domain/d0DomainHttps) — D0 Ananas域名
102. **d0.cldisk.com** (d0NewDomain/d0NewDomainHttps) — D0新域名
103. **p2.ananas.chaoxing.com** (p2AnanasDomain) — P2 Ananas域名
104. **p.cldisk.com** (photoDomain/photoNewDomain/photoNewDomainHttps) — 图片域名
105. **photo.chaoxing.com** (avatarDomain) — 头像域名
106. **cs.ananas.chaoxing.com** (csDomain/csDomainHttps) — CS Ananas域名

## ADDED Requirements

### Requirement: 第四梯队域名签到API探索
系统 SHALL 对学习/教学核心域名(learn/mobilelearn/mooc1/mooc/pc/m/i等)进行签到API探索。

#### Scenario: 学习核心域名签到API探索
- **WHEN** 对learn.chaoxing.com、mobilelearn.chaoxing.com、mooc1.chaoxing.com等核心学习域名进行签到API探索
- **THEN** 应发现并记录所有签到相关端点，特别关注与主域不同的鉴权机制

### Requirement: 代理路径认证绕过测试
系统 SHALL 对noteyd.chaoxing.com/proxy等代理路径进行认证绕过测试。

#### Scenario: 代理路径认证绕过
- **WHEN** 通过noteyd.chaoxing.com/proxy路径访问签到API
- **THEN** 应验证代理是否转发认证信息，是否可绕过后端认证

### Requirement: 群组/首页域名签到功能测试
系统 SHALL 对群组域名(groupyd/groupweb)和首页域名(home/homewh)进行签到功能测试。

#### Scenario: 群组域名签到功能
- **WHEN** 对群组域名测试签到相关API
- **THEN** 应发现群组场景下是否存在不同的签到权限控制

### Requirement: 跨域Cookie/Session传递测试
系统 SHALL 测试不同域名间的Cookie和Session传递机制。

#### Scenario: 跨域认证传递
- **WHEN** 使用主域的Cookie访问其他域名的签到API
- **THEN** 应识别哪些域名共享认证，哪些域名有独立认证

### Requirement: 新发现漏洞验证与报告更新
系统 SHALL 验证所有新发现的漏洞并更新安全测试报告。

#### Scenario: 漏洞验证
- **WHEN** 在新域名上发现签到状态修改接口
- **THEN** 应验证学生是否能成功修改签到状态，并更新报告
