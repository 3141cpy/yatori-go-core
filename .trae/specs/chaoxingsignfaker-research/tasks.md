# Tasks

- [x] Task 1: V2 API信息泄露研究 — 签到码/enc获取
  - [x] 1.1 研究/v2/apis/active/getPPTActiveInfo — **发现ewnCtime1泄露（HIGH 7.0）**
  - [x] 1.2 研究/v2/apis/active/student/activelist — 参数组合均无效
  - [x] 1.3 分析返回数据 — signCode已过滤但ewnCtime1/chartid/安全配置未过滤

- [x] Task 2: preSign/checkSignCode/check-face-result权限研究
  - [x] 2.1 研究/newsign/preSign — 教师页面泄露签到码signCode=175509；学生页面返回signstatus
  - [x] 2.2 研究/widget/sign/pcStuSignController/checkSignCode — **可暴力破解（MEDIUM 4.8）**
  - [x] 2.3 研究/pptSign/check-face-result — 当前签到类型不适用，返回500

- [x] Task 3: analysis链与签到前置条件研究
  - [x] 3.1 研究/pptSign/analysis — 始终返回500
  - [x] 3.2 研究/pptSign/analysis2 — 始终返回500；analysis链不被强制执行

- [x] Task 4: 辅助端点安全研究
  - [x] 4.1 研究sso.chaoxing.com — **泄露IM密码明文（HIGH 6.8）**
  - [x] 4.2 研究im.chaoxing.com/webim/me — 返回HTML页面
  - [x] 4.3 研究captcha.chaoxing.com — captchaId硬编码，当前返回CALLBACK ERROR
  - [x] 4.4 研究pan-yz.chaoxing.com — **云盘上传无文件类型验证（MEDIUM 5.2）**

- [x] Task 5: 安全测试报告更新
  - [x] 5.1 整理所有新发现漏洞（5个新漏洞）
  - [x] 5.2 更新/workspace/sign_vuln_report.md至v10.0

# Task Dependencies
- Task 1-4 可并行执行 ✅
- Task 5 depends on all previous tasks ✅
