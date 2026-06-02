# Tasks

- [x] Task 1: 获取课程111最新活动列表，识别3个目标签到活动
  - [x] SubTask 1.1: 学生登录并获取活动列表 → 19个活动
  - [x] SubTask 1.2: 识别已结束未签的二维码签到 → aid=5000163776552 (qrcode=True, signout=False)
  - [x] SubTask 1.3: 识别进行中的二维码签到 → aid=5000163776548 (qrcode=True, signout=False, nameTwo=结束时间：06-03 01:49)
  - [x] SubTask 1.4: 识别已结束的签退活动 → aid=5000163776554 (qrcode=True, signout=True)
  - [x] SubTask 1.5: 记录每个活动的详细信息

- [x] Task 2: 测试已结束未签的二维码签到（活动1）
  - [x] SubTask 2.1: 查询当前签到状态 → status=None（未签到）
  - [x] SubTask 2.2: 学生调用 /newsign/updateSignStatus status=1 → "success"
  - [x] SubTask 2.3: 查询修改后签到状态 → 教师V2确认后status=1 🔴
  - [x] SubTask 2.4: 教师端确认签到状态变化 → status=1 🔴
  - [x] SubTask 2.5: 正常签到(stuSignajax) → "签到失败，请重新扫描"（需要扫码）

- [x] Task 3: 测试进行中的二维码签到（活动2）
  - [x] SubTask 3.1: 查询当前签到状态 → status=None
  - [x] SubTask 3.2: 学生调用 /newsign/updateSignStatus status=1 → "success"
  - [x] SubTask 3.3: 查询修改后签到状态 → 教师V2确认后status=1 🔴
  - [x] SubTask 3.4: 教师端确认签到状态变化 → status=1 🔴
  - [x] SubTask 3.5: 正常签到(stuSignajax) → "签到失败，请重新扫描"
  - [x] SubTask 3.6: 测试不同status值 → status=0~6全部API返回success，但查询均为1（首次修改后不变）

- [x] Task 4: 测试已结束的签退活动（活动3）
  - [x] SubTask 4.1: 查询当前签到状态 → status=None
  - [x] SubTask 4.2: 学生调用 /newsign/updateSignStatus status=1 → "success"
  - [x] SubTask 4.3: 查询修改后签到状态 → 教师V2确认后status=1 🔴
  - [x] SubTask 4.4: 教师端确认签到状态变化 → status=1 🔴
  - [x] SubTask 4.5: 签退活动也可被修改 🔴

- [x] Task 5: 汇总测试结果并更新文档
  - [x] SubTask 5.1: 汇总3种场景的测试结果
  - [x] SubTask 5.2: 更新 /workspace/newsign_vuln_exploit_guide.md → 新增第十节
  - [x] SubTask 5.3: 更新 /workspace/sign_vuln_report.md（已在之前版本更新）

# Task Dependencies
- [Task 1] 最先执行 ✅
- [Task 2, Task 3, Task 4] 依赖Task 1 ✅
- [Task 5] 依赖Task 2, 3, 4 ✅
