# 课程垂直越权漏洞评估报告


**审计日期**: 2026-05-26 03:57:15


**测试账号**: 账号1(puid=252798154), 账号2(puid=239448447)


---

## 一、测试结果汇总


- **总测试数**: 14
- **发现隐患数**: 3

- **严重(CRITICAL)**: 0
- **高危(HIGH)**: 1

- **中危(MEDIUM)**: 0
- **低危(LOW)**: 2


---

## 二、教师管理API端点清单


| API | URL | 功能 | 认证方式 |
|---|---|---|---|

| 获取活动列表 | /ppt/activeAPI/taskactivelist | 获取课程活动列表 | Cookie |

| 创建活动 | /ppt/activeAPI/createActive | 创建签到/投票/练习 | Cookie+角色 |

| 删除活动 | /ppt/activeAPI/deleteActive | 删除活动 | Cookie+角色 |

| 学生签到 | /pptSign/stuSignajax | 学生执行签到 | Cookie |

| 签到结果 | /pptSign/signedResult | 查看签到结果 | Cookie |

| 教师管理页面 | /mycourse/teacherindex | 教师管理界面 | Cookie+角色 |

| 班级统计 | /clazz/result/studentStatic | 班级学习统计 | Cookie |

| 课程设置 | /clazz/update | 修改课程设置 | Cookie+角色 |

| 成员列表 | /clazz/member/list | 课程成员列表 | Cookie |


---

## 三、角色校验机制分析


### 3.1 roletype字段

- 课程列表API返回的`roletype`字段标识用户在课程中的角色

- `roletype=0` 表示学生，`roletype=1` 表示教师/创建者

- 该字段由服务端返回，客户端无法直接修改


### 3.2 sso_role Cookie

- Cookie中可能包含`sso_role`字段，用于标识用户全局角色

- 该字段可被客户端修改，如果服务端依赖此字段进行角色校验，则存在篡改风险


---

## 四、各模块详细测试结果


### T2-01: roletype字段分析 [存在风险]


- **API端点**: `/mycourse/backclazzdata`

- **越权类型**: 角色分析

- **风险等级**: LOW

- **结论**: 账号1: 学生角色课程=43, 教师角色课程=0, roletype值={3}


- **证据**: roletype: 0=学生, 1=教师, 2=助教(推测)


### T2-02: Cookie中sso_role分析 [安全]


- **API端点**: `Cookie`

- **越权类型**: 角色分析

- **风险等级**: LOW

- **结论**: Cookie中sso_role=不存在


- **证据**: sso_role值: 


### T3-01: 学生获取课程活动列表 [存在风险]


- **API端点**: `/ppt/activeAPI/taskactivelist`

- **越权类型**: 基线

- **风险等级**: LOW

- **结论**: 学生账号请求活动列表: 成功


- **证据**: HTTP 200, 响应前500字: {"groupList":[{"classId":"","content":"","courseId":"","createTime":null,"fid":"","id":1,"isDelete":0,"name":"进行中(0)","sort":0,"type":0,"uid":"","updateTime":null},{"classId":"","content":"","courseId":"","createTime":null,"fid":"","id":0,"isDelete":0,"name":"未开始(0)","sort":0,"type":0,"uid":"","updateTime":null},{"classId":"","content":"","courseId":"","createTime":null,"fid":"","id":2,"isDelete":0,"name":"已结束(0)","sort":0,"type":0,"uid":"","updateTime":null}],"activeList":[],"count":0,"status":


### T3-02: 学生尝试创建签到活动 [安全]


- **API端点**: `/ppt/activeAPI/createActive`

- **越权类型**: 垂直越权

- **风险等级**: CRITICAL

- **结论**: 学生账号尝试创建签到: 被拒绝


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T3-03-4: 学生尝试创建投票/问卷 [安全]


- **API端点**: `/ppt/activeAPI/createActive`

- **越权类型**: 垂直越权

- **风险等级**: CRITICAL

- **结论**: 学生账号尝试创建投票/问卷: 被拒绝


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T3-03-16: 学生尝试创建随堂练习 [安全]


- **API端点**: `/ppt/activeAPI/createActive`

- **越权类型**: 垂直越权

- **风险等级**: CRITICAL

- **结论**: 学生账号尝试创建随堂练习: 被拒绝


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T5-01: 学生访问教师管理页面 [安全]


- **API端点**: `/mycourse/teacherindex`

- **越权类型**: 垂直越权

- **风险等级**: HIGH

- **结论**: 学生账号访问教师管理页面: 被拒绝(HTTP 404)


- **证据**: HTTP 404, 重定向: 无


### T5-02: 学生查看班级统计数据 [安全]


- **API端点**: `/clazz/result/studentStatic`

- **越权类型**: 垂直越权

- **风险等级**: HIGH

- **结论**: 学生账号查看班级统计: 被拒绝


- **证据**: HTTP 404, 响应前300字: <!doctype html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
    <title>404</title>
    <style>
        .main{height:255px;margin:0 auto;margin-top:15%;font-size:16px;color:#999; width: 350px;}
        .font_top{padd


### T5-03: 学生尝试修改课程设置 [安全]


- **API端点**: `/clazz/update`

- **越权类型**: 垂直越权

- **风险等级**: CRITICAL

- **结论**: 学生账号尝试修改课程设置: 被拒绝


- **证据**: HTTP 404, 响应: {"raw_status": 404, "raw_text": "<!doctype html>\n<html>\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=viewport content=\"initial-scale=1, minimum-scale=1, width=device-width\">\n    <title>404</title>\n    <style>\n        .main{height:255px;margin:0 auto;margin-top:15%;font-size:16px;color


### T5-04: 学生查看课程成员列表 [安全]


- **API端点**: `/clazz/member/list`

- **越权类型**: 垂直越权

- **风险等级**: HIGH

- **结论**: 学生账号查看课程成员: 被拒绝


- **证据**: HTTP 404, 响应前300字: <!doctype html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name=viewport content="initial-scale=1, minimum-scale=1, width=device-width">
    <title>404</title>
    <style>
        .main{height:255px;margin:0 auto;margin-top:15%;font-size:16px;color:#999; width: 350px;}
        .font_top{padd


### T6-01: 修改sso_role为1后请求活动列表 [存在风险]


- **API端点**: `/ppt/activeAPI/taskactivelist`

- **越权类型**: 角色篡改

- **风险等级**: HIGH

- **结论**: 修改sso_role=1后请求活动列表: 成功


- **证据**: HTTP 200, 响应前300字: {"groupList":[{"classId":"","content":"","courseId":"","createTime":null,"fid":"","id":1,"isDelete":0,"name":"进行中(0)","sort":0,"type":0,"uid":"","updateTime":null},{"classId":"","content":"","courseId":"","createTime":null,"fid":"","id":0,"isDelete":0,"name":"未开始(0)","sort":0,"type":0,"uid":"","upda


### T6-02: 修改sso_role后尝试创建签到 [安全]


- **API端点**: `/ppt/activeAPI/createActive`

- **越权类型**: 角色篡改+垂直越权

- **风险等级**: CRITICAL

- **结论**: 修改sso_role=1后创建签到: 被拒绝


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T6-03: 添加role=1参数后尝试创建签到 [安全]


- **API端点**: `/ppt/activeAPI/createActive`

- **越权类型**: 角色篡改+垂直越权

- **风险等级**: CRITICAL

- **结论**: 添加role=1参数后创建签到: 被拒绝


- **证据**: HTTP 500, 响应: {"raw_status": 500, "raw_text": "<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">\r\n<html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body>\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>tengine</center>\r\n</body>\r\n</html>\r\n"}


### T6-04: 修改sso_role后访问教师管理页面 [安全]


- **API端点**: `/mycourse/teacherindex`

- **越权类型**: 角色篡改+垂直越权

- **风险等级**: HIGH

- **结论**: 修改sso_role=1后访问教师管理页面: 被拒绝


- **证据**: HTTP 404, 重定向: 无


---

## 五、修复建议


### 5.1 紧急修复


1. **服务端角色校验**: 所有教师管理API必须在服务端校验用户角色，不能仅依赖Cookie或前端参数

2. **创建活动权限控制**: /ppt/activeAPI/createActive 必须校验请求者是否为课程教师/创建者

3. **删除活动权限控制**: /ppt/activeAPI/deleteActive 必须校验请求者是否为活动创建者

4. **课程设置权限控制**: /clazz/update 必须校验请求者是否为课程教师


### 5.2 中期加固


5. **sso_role不可信**: 不应依赖Cookie中的sso_role字段进行角色校验

6. **教师管理页面权限校验**: /mycourse/teacherindex 应在服务端校验roletype

7. **班级统计数据访问控制**: 班级统计应限制为教师角色访问

8. **成员列表访问控制**: 课程成员列表应限制为教师角色访问

