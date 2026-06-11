# Tasks

- [x] Task 1: 第一梯队域名签到API探索（已完成：5个域全部可达但无签到API端点）
  - [x] 1.1 statisticyd.chaoxing.com — 可达但无签到API
  - [x] 1.2 k.chaoxing.com — POST返回405
  - [x] 1.3 study-api.chaoxing.com — 返回500
  - [x] 1.4 office.chaoxing.com — 404
  - [x] 1.5 task.chaoxing.com — 404

- [x] Task 2: 第二梯队域名替代API探索（已完成：仅mobilelearn.fy有签到功能）
  - [x] 2.1 mobile.fanya.chaoxing.com — 无签到API
  - [x] 2.2 mobilelearn.fy.chaoxing.com — 有签到功能但认证与主域一致
  - [x] 2.3 mooc2-ans.chaoxing.com — 无签到API
  - [x] 2.4 bigdata-api/bigdata-ans — 无签到API
  - [x] 2.5 fystat-ans/stat2-ans — 无签到API

- [x] Task 3: 第三梯队域名基础设施探索（已完成：全部无签到API）
  - [x] 3.1 passport2-api/uc/uc1-ans — 无签到API
  - [x] 3.2 structureyd/v1 — 无签到API
  - [x] 3.3 mobilewx/manage.learn/manage.yd — 无签到API

- [x] Task 4: 跨域名鉴权差异测试（已完成：FY域认证与主域一致）
  - [x] 4.1 mobilelearn.fy认证与主域一致
  - [x] 4.2 FY域仅HTTP可用，存在明文传输风险

- [x] Task 5: 第一轮新发现漏洞验证与报告更新（已完成：报告更新至v8.0）
  - [x] 5.1 验证mobilelearn.fy HTTP明文传输漏洞
  - [x] 5.2 更新sign_vuln_report.md至v8.0

- [x] Task 6: 第四梯队域名签到API探索（学习/教学核心域名）
  - [x] 6.1 learn.chaoxing.com — 无签到API（POST返回405）
  - [x] 6.2 mobilelearn.chaoxing.com — **完整签到API栈，V2 signIn信息泄露**
  - [x] 6.3 mooc1.chaoxing.com / mooc1-2 / mooc1-3 — 纯CDN/静态域名
  - [x] 6.4 mooc.chaoxing.com / i.mooc.chaoxing.com — 重定向/登录页
  - [x] 6.5 pc.chaoxing.com — 无签到API
  - [x] 6.6 m.chaoxing.com — 使用fxlogin独立认证体系

- [x] Task 7: 第五梯队域名签到API探索（群组/首页/特殊域名）
  - [x] 7.1 groupyd/groupweb/groupyd2 — 全部404/405
  - [x] 7.2 home-yd/home.yd/homewh — 全部404/405
  - [x] 7.3 special/special1.rhky/special2.rhky/special.rhky — SSO认证网关后404
  - [x] 7.4 specialpack.chaoxing.com — Access Denied

- [x] Task 8: 第六梯队域名签到API探索（应用/API/资源域名）
  - [x] 8.1 apps/apps.ananas/appswh — 无签到API
  - [x] 8.2 cs-api.chaoxing.com — SSL错误/502
  - [x] 8.3 resource.chaoxing.com — 纯静态资源
  - [x] 8.4 fe.chaoxing.com — **WAF完全封堵签到路径（403）**；mh.chaoxing.com — **Spring Cloud Gateway路由信息泄露**

- [x] Task 9: 第七梯队域名签到API探索（用户/通知/消息域名）
  - [x] 9.1 user.yd/useryd — 无签到API
  - [x] 9.2 notice/message — 无签到API
  - [x] 9.3 im/api.im/api1.im — api.im有API但403
  - [x] 9.4 contactsyd — 无签到API

- [x] Task 10: 第八梯队域名探索（代理/特殊路径 — 认证绕过重点）
  - [x] 10.1 noteyd.chaoxing.com — 基础域名返回400
  - [x] 10.2 noteyd.chaoxing.com/proxy — **非开放代理，POST统一405，认证绕过失败**
  - [x] 10.3 noteyd.chaoxing.com/comm/comp — 同上
  - [x] 10.4 appswh.chaoxing.com/epub/board/projectapp/hbqyg — POST统一405

- [x] Task 11: 第九至十一梯队域名批量探索（其他域名）
  - [x] 11.1 第九梯队：**contestyd.chaoxing.com CORS任意Origin反射**
  - [x] 11.2 第十梯队：x.chaoxing.com API路由存在但500
  - [x] 11.3 第十一梯队：**ss.zhizhen.com完整签到API（需独立认证）**

- [x] Task 12: 跨域认证深度测试
  - [x] 12.1 mobilelearn.chaoxing.com深度测试 — updateSignStatus2教师可修改任意学生签到；V2 signIn 40+字段泄露
  - [x] 12.2 fe.chaoxing.com WAF绕过测试 — 全部失败（tengine层全路径封堵）
  - [x] 12.3 mh.chaoxing.com网关测试 — 分号注入返回200；路由信息泄露
  - [x] 12.4 contestyd.chaoxing.com CORS测试 — **任意Origin反射+Allow-Credentials:true**
  - [x] 12.5 ss.zhizhen.com认证测试 — 独立认证体系，ChaoXing Cookie无效

- [x] Task 13: 新发现漏洞验证与报告更新
  - [x] 13.1 验证contestyd.chaoxing.com CORS漏洞（HIGH 7.2）
  - [x] 13.2 验证mobilelearn.chaoxing.com V2 signIn信息泄露（MEDIUM 5.0）
  - [x] 13.3 验证mh.chaoxing.com网关路由信息泄露（LOW 2.8）
  - [x] 13.4 更新 /workspace/sign_vuln_report.md 至v9.0

# Task Dependencies
- Task 6-11 可并行执行（不同域名独立探索）✅
- Task 12 depends on Task 6-11 ✅
- Task 13 depends on all previous tasks ✅
