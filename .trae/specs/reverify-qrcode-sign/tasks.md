# Tasks

- [x] Task 1: 获取最新活动列表，找到未签的二维码签到活动 → aid=5000163891319（结束时间06-03 13:40，未签到）
- [x] Task 2: 学生调用 /newsign/updateSignStatus 修改签到状态为出勤 → 返回"success"
- [x] Task 3: 验证修改是否生效（学生端+教师端查询确认）→ 教师V2确认后status=1，签到记录已创建(id=5001370808137)

# Task Dependencies
- [Task 2] depends on [Task 1] ✅
- [Task 3] depends on [Task 2] ✅
