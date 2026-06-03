# Tasks

- [x] Task 1: 构建多UA签到状态修改测试脚本
  - [x] SubTask 1.1: 定义10种UA（移动端App含schild x4版本、移动端Web、PC端Chrome/Edge、微信内嵌、iPad、iPhone Web）
  - [x] SubTask 1.2: 对每种UA测试`/newsign/updateSignStatus`，修改status后用V2 signIn查询验证
  - [x] SubTask 1.3: 对每种UA测试`/pptSign/updateSignStatus`、`/pptSign/updateSignStatusByUidsV2`等
  - [x] SubTask 1.4: 对每种UA测试`/pptSign/stuSignajax`带status参数

- [x] Task 2: 不同Content-Type和请求格式测试
  - [x] SubTask 2.1: 测试application/json格式POST
  - [x] SubTask 2.2: 测试multipart/form-data格式
  - [x] SubTask 2.3: 测试application/x-www-form-urlencoded格式
  - [x] SubTask 2.4: 测试PUT/GET方法

- [x] Task 3: 学生端完整签到流程模拟（移动端App UA）
  - [x] SubTask 3.1: 模拟preSign获取签到信息（发现JS逆向关键参数）
  - [x] SubTask 3.2: 模拟stuSignajax签到（GET/POST，带ifTiJiao/validate/deviceCode参数）
  - [x] SubTask 3.3: 模拟updateqrstatus二维码签到
  - [x] SubTask 3.4: 在每个步骤中注入status参数测试

- [x] Task 4: 其他域名+UA组合探索
  - [x] SubTask 4.1: 在mooc1-api域名下用不同UA测试
  - [x] SubTask 4.2: 在learn.chaoxing.com/office.chaoxing.com域名下测试
  - [x] SubTask 4.3: 探索/api/、/front/、/mooc-ans/等路径前缀

- [x] Task 5: 参数名变体和特殊参数测试
  - [x] SubTask 5.1: 测试signStatus/resultStatus/type/operateType等参数名
  - [x] SubTask 5.2: 测试clientType/appType/sourceType等来源参数
  - [x] SubTask 5.3: 测试不同UA下参数名变体的行为差异

- [x] Task 6: 输出测试结果供用户验证
  - [x] SubTask 6.1: 汇总所有测试结果到JSON文件
  - [x] SubTask 6.2: 标记所有返回"success"或非错误响应的测试项
  - [x] SubTask 6.3: 生成用户可自行验证的curl命令列表

# Task Dependencies
- Task 2 depends on Task 1 (需要先确定哪些UA有差异)
- Task 3 depends on Task 1 (需要先确定UA维度)
- Task 4 depends on Task 1 (需要先确定UA维度)
- Task 5 depends on Task 1 (需要先确定UA维度)
- Task 6 depends on Task 1-5 (汇总所有结果)
