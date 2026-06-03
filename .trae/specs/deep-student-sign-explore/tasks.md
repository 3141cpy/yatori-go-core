# Tasks

- [ ] Task 1: /newsign/updateSignStatus 全面参数组合测试
  - [ ] SubTask 1.1: 测试不同DB_STRATEGY值（PRIMARY_KEY/COURSEID/CLASSID/ACTIVEID/NONE/空/RANDOM/SLAVE）
  - [ ] SubTask 1.2: 测试不同STRATEGY_PARA值（activeId/courseId/classId/uid）
  - [ ] SubTask 1.3: 测试不同HTTP方法（POST/GET/PUT）
  - [ ] SubTask 1.4: 测试不同Content-Type（urlencoded/multipart/json）
  - [ ] SubTask 1.5: 测试不同status值（0-6, -1, 99）
  - [ ] SubTask 1.6: 测试不同uids格式（单个uid/逗号分隔/JSON数组）
  - [ ] SubTask 1.7: 测试额外参数注入（operateSource/sourceType/roletype/role/cpi/token/signType）
  - [ ] SubTask 1.8: 测试不同签到活动类型（二维码/手势/位置/普通/签退）
  - [ ] SubTask 1.9: 测试不同活动状态（进行中 vs 已结束）
  - [ ] SubTask 1.10: 测试uid参数替换（用教师uid/其他学生uid/空uid）

- [ ] Task 2: /newsign/ 路径遗漏端点全面扫描
  - [ ] SubTask 2.1: 动词扫描（add/save/create/insert/submit/do/student/stu/sign/start/pre/quick/makeUp/resign/modify/change/delete/cancel/stop/end/close/lock/unlock/send/push/publish/confirm/check/verify/get/query/list/detail/info/count/stat/refresh/reset/retry/reopen）
  - [ ] SubTask 2.2: 名词组合（Sign/SignRecord/SignStatus/SignInfo/SignDetail/Active/Activity/Task/Record/Status/User/Student/Member）
  - [ ] SubTask 2.3: 对所有非404端点进行GET和POST测试

- [ ] Task 3: /pptSign/ 学生端可用端点深入测试
  - [ ] SubTask 3.1: stuSignajax完整参数测试（不同activeId/uid/latitude/longitude/address/enc/clientip/appType/fid组合）
  - [ ] SubTask 3.2: preSign深入测试（GET/POST，不同参数）
  - [ ] SubTask 3.3: updateqrstatus深入测试（不同enc值/空enc/无enc）
  - [ ] SubTask 3.4: 探索pptSign下更多端点（stuSignAjaxNew/stuSignNew/stuSignV2/signV2/signNew/signInV2/qrCodeSign/scanSign/locationSign/gestureSign/numberSign/signByCode/signByEnc等）
  - [ ] SubTask 3.5: 对所有非404端点记录响应

- [ ] Task 4: /v2/apis/ 签到相关端点探索
  - [ ] SubTask 4.1: /v2/apis/sign/ 下所有子路径（signIn/signUp/doSign/submit/modify/update/cancel/makeup/resign/quickSign/qrCodeSign/preSign）
  - [ ] SubTask 4.2: /v2/apis/active/ 下所有子路径（detail/student/activelist/teacher/activelist/startSign）
  - [ ] SubTask 4.3: GET和POST两种方法测试

- [ ] Task 5: 多域名API探索
  - [ ] SubTask 5.1: mooc1-api.chaoxing.com 域名下测试（/mooc-ans/sign/*, /mooc-ans/pptSign/*, /mooc-ans/newsign/*）
  - [ ] SubTask 5.2: learn.chaoxing.com 域名下测试（/apis/sign/*, /apis/pptSign/*）
  - [ ] SubTask 5.3: office.chaoxing.com 域名下测试
  - [ ] SubTask 5.4: 对比不同域名的权限校验差异

- [ ] Task 6: 位置签到伪造与三角定位
  - [ ] SubTask 6.1: 对所有位置签到活动收集距离信息
  - [ ] SubTask 6.2: 三角定位计算教师指定位置
  - [ ] SubTask 6.3: 用计算位置尝试签到
  - [ ] SubTask 6.4: 测试位置签到范围阈值

- [ ] Task 7: CSRF攻击路径验证
  - [ ] SubTask 7.1: 验证/pptSign/updateSignStatusByUidsV2 GET方式CSRF
  - [ ] SubTask 7.2: 验证无Referer检查
  - [ ] SubTask 7.3: 验证无自定义Header要求
  - [ ] SubTask 7.4: 生成CSRF PoC HTML

- [ ] Task 8: 输出完整测试报告
  - [ ] SubTask 8.1: 汇总所有端点测试结果
  - [ ] SubTask 8.2: 标记所有可利用的攻击路径
  - [ ] SubTask 8.3: 输出到/workspace/student_sign_vuln_deep_report.md

# Task Dependencies
- [Task 1, Task 2, Task 3, Task 4, Task 5] 可并行执行
- [Task 6] 依赖 Task 3 的结果（需要stuSignajax距离信息）
- [Task 7] 独立执行
- [Task 8] 依赖所有前序任务
