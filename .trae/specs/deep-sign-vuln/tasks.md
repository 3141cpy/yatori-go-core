# Tasks

## 阶段1：签到API端点全面枚举

- [ ] Task 1: 联网搜索学习通签到API端点
  - [ ] SubTask 1.1: 搜索GitHub上学习通签到相关开源项目，提取API端点列表
  - [ ] SubTask 1.2: 搜索技术博客/论坛中学习通签到API的分析文章
  - [ ] SubTask 1.3: 搜索学习通签到API的参数格式和响应格式
  - [ ] SubTask 1.4: 整理所有发现的API端点，按教师端/学生端分类

- [ ] Task 2: 教师端签到API端点枚举
  - [ ] SubTask 2.1: 使用教师账号登录，获取完整Cookie
  - [ ] SubTask 2.2: 访问教师端签到管理页面，提取页面中的API调用
  - [ ] SubTask 2.3: 测试教师端签到管理API（/ppt/activeAPI/*系列端点）
  - [ ] SubTask 2.4: 测试教师端签到结果管理API（/pptSign/*系列端点）
  - [ ] SubTask 2.5: 记录所有教师端API的URL、方法、参数、响应格式

- [ ] Task 3: 学生端签到API端点枚举
  - [ ] SubTask 3.1: 使用学生账号登录，获取完整Cookie
  - [ ] SubTask 3.2: 访问学生端签到页面，提取页面中的API调用
  - [ ] SubTask 3.3: 分析preSign页面的完整HTML和JavaScript代码，提取API端点
  - [ ] SubTask 3.4: 测试学生端签到API（/pptSign/stuSignajax及其变体）
  - [ ] SubTask 3.5: 记录所有学生端API的URL、方法、参数、响应格式

## 阶段2："111"课程定位与进行中签到创建

- [ ] Task 4: 定位"111"课程
  - [ ] SubTask 4.1: 使用教师账号获取课程列表，搜索"111"课程
  - [ ] SubTask 4.2: 使用学生账号获取课程列表，搜索"111"课程
  - [ ] SubTask 4.3: 如果未找到"111"课程，搜索所有课程名称中包含"1"的课程
  - [ ] SubTask 4.4: 记录"111"课程的courseId/classId/cpi/roletype

- [ ] Task 5: 创建进行中的签到活动
  - [ ] SubTask 5.1: 使用教师账号在"111"课程中创建一个普通签到活动
  - [ ] SubTask 5.2: 确认签到活动创建成功，记录activeId
  - [ ] SubTask 5.3: 使用学生账号确认签到活动可见且为进行中状态
  - [ ] SubTask 5.4: 确认学生当前未签到该活动

## 阶段3：基于线索的API端点定向测试

- [ ] Task 6: 测试"仅改状态"的API端点
  - [ ] SubTask 6.1: 测试/pptSign/updateSignStatus端点（仅传activeId+status参数）
  - [ ] SubTask 6.2: 测试/pptSign/changeStatus端点（仅传activeId+status参数）
  - [ ] SubTask 6.3: 测试/pptSign/modifySign端点（仅传activeId+status参数）
  - [ ] SubTask 6.4: 测试/pptSign/sign端点（仅传activeId参数，不传位置/二维码/手势信息）
  - [ ] SubTask 6.5: 测试/pptSign/saveSign端点
  - [ ] SubTask 6.6: 测试/pptSign/stuSign端点（非stuSignajax）
  - [ ] SubTask 6.7: 测试/pptSign/doSign端点
  - [ ] SubTask 6.8: 测试/ppt/activeAPI/updateActive端点

- [ ] Task 7: 教师端签到管理API的学生可访问性测试
  - [ ] SubTask 7.1: 学生账号调用/ppt/activeAPI/startSign（发起签到）
  - [ ] SubTask 7.2: 学生账号调用/ppt/activeAPI/endActive（结束签到）
  - [ ] SubTask 7.3: 学生账号调用/ppt/activeAPI/modifyActive（修改签到活动）
  - [ ] SubTask 7.4: 学生账号调用/pptSign/teacherSign（教师签到管理）
  - [ ] SubTask 7.5: 学生账号调用/pptSign/signedResult（签到结果，含POST修改）
  - [ ] SubTask 7.6: 学生账号调用/pptSign/updateSign（更新签到）
  - [ ] SubTask 7.7: 学生账号调用/pptSign/signDetail（签到详情）
  - [ ] SubTask 7.8: 学生账号调用/pptSign/reSign（重新签到/补签）

- [ ] Task 8: 签到结果API的状态修改能力测试
  - [ ] SubTask 8.1: 学生账号GET /pptSign/signedResult获取签到结果格式
  - [ ] SubTask 8.2: 学生账号POST /pptSign/signedResult修改签到状态
  - [ ] SubTask 8.3: 学生账号PUT /pptSign/signedResult修改签到状态
  - [ ] SubTask 8.4: 学生账号POST /pptSign/signedResult添加status=1参数
  - [ ] SubTask 8.5: 学生账号POST /pptSign/signedResult添加signStatus=1参数

- [ ] Task 9: 不同签到类型的状态修改测试
  - [ ] SubTask 9.1: 对进行中的普通签到，尝试仅传activeId签到（不传任何类型验证信息）
  - [ ] SubTask 9.2: 对进行中的普通签到，尝试传activeId+activeType=2签到
  - [ ] SubTask 9.3: 创建手势签到，学生尝试仅传activeId+signCode参数签到
  - [ ] SubTask 9.4: 创建位置签到，学生尝试仅传activeId签到（不传位置信息）
  - [ ] SubTask 9.5: 创建二维码签到，学生尝试仅传activeId签到（不传enc参数）
  - [ ] SubTask 9.6: 对每种签到类型，尝试通过/pptSign/stuSignajax仅传activeId参数

## 阶段4：preSign页面与前端逻辑深入分析

- [ ] Task 10: preSign页面深入分析
  - [ ] SubTask 10.1: 获取进行中签到的preSign页面完整HTML
  - [ ] SubTask 10.2: 提取preSign页面中引用的所有JavaScript文件URL
  - [ ] SubTask 10.3: 下载并分析每个JS文件中的签到相关API调用
  - [ ] SubTask 10.4: 分析preSign页面中的签到提交逻辑和状态修改逻辑
  - [ ] SubTask 10.5: 测试从JS代码中发现的API端点

## 阶段5：漏洞验证与报告更新

- [ ] Task 11: 漏洞验证
  - [ ] SubTask 11.1: 对每个发现的可修改状态的API，使用教师端确认签到状态是否确实改变
  - [ ] SubTask 11.2: 分析漏洞利用的前提条件（需要什么参数、什么签到状态、什么角色）
  - [ ] SubTask 11.3: 评估漏洞影响范围（哪些签到类型受影响、影响多少用户）
  - [ ] SubTask 11.4: 构建完整的签到状态修改攻击链

- [ ] Task 12: 更新安全测试报告
  - [ ] SubTask 12.1: 更新/sign_vuln_report.md，添加新发现的漏洞
  - [ ] SubTask 12.2: 记录所有测试步骤、操作方法、系统响应及结果
  - [ ] SubTask 12.3: 分析漏洞技术原理（为什么"只能改状态，带不了位置/二维码信息"）
  - [ ] SubTask 12.4: 确定漏洞利用条件、影响范围及严重程度
  - [ ] SubTask 12.5: 提出修复建议

# Task Dependencies
- [Task 2] depends on [Task 1]（联网搜索结果指导教师端API枚举方向）
- [Task 3] depends on [Task 1]（联网搜索结果指导学生端API枚举方向）
- [Task 4] depends on [Task 2, Task 3]（需要先登录获取Cookie）
- [Task 5] depends on [Task 4]（需要先定位课程）
- [Task 6, 7, 8] depends on [Task 5]（需要进行中的签到活动）
- [Task 9] depends on [Task 5]（需要不同类型的进行中签到活动）
- [Task 10] depends on [Task 5]（需要preSign页面可访问）
- [Task 6, 7, 8, 9, 10] 可并行执行
- [Task 11] depends on [Task 6-10]
- [Task 12] depends on [Task 11]
