# Tasks

## 阶段1：信息收集与签到状态确认

- [x] Task 1: 教师账号登录并获取"111"课程签到活动列表
  - [x] SubTask 1.1: 使用教师账号(19712720708/3.1415926Cpy)登录学习通
  - [x] SubTask 1.2: 获取教师账号的课程列表，找到"111"课程的courseId/classId/cpi（未找到"111"课程，使用"exam"课程替代）
  - [x] SubTask 1.3: 获取"exam"课程的活动列表（/ppt/activeAPI/taskactivelist），记录所有签到活动的activeId、activeType、status、时间
  - [x] SubTask 1.4: 获取每个签到活动的详细信息（签到结果、已签/未签学生列表）

- [x] Task 2: 学生账号登录并获取签到状态
  - [x] SubTask 2.1: 使用学生账号(18436633997/3.1415926Cpy)登录学习通
  - [x] SubTask 2.2: 获取学生账号的课程列表，找到"exam"课程的courseId/classId/cpi
  - [x] SubTask 2.3: 获取学生在"exam"课程的活动列表，确认哪些签到已签/未签/缺勤
  - [x] SubTask 2.4: 记录学生未签到的签到活动ID（作为后续测试目标）

## 阶段2：常规签到操作测试

- [x] Task 3: 学生常规签到操作测试
  - [x] SubTask 3.1: 对未签到的签到活动执行正常签到（/pptSign/stuSignajax），记录请求和响应
  - [x] SubTask 3.2: 对已签到的活动重复签到，验证系统是否拒绝
  - [x] SubTask 3.3: 使用教师账号确认学生签到状态是否确实改变

## 阶段3：非常规手段修改签到状态

- [x] Task 4: 修改签到请求参数测试
  - [x] SubTask 4.1: 修改签到请求中的activeId参数（指向其他签到活动）
  - [x] SubTask 4.2: 修改签到请求中的status参数（改为已签到状态）
  - [x] SubTask 4.3: 修改签到请求中的uid参数（冒充其他学生签到）
  - [x] SubTask 4.4: 添加额外的参数（如signStatus=1、isSigned=true等）

- [x] Task 5: 修改签到API的HTTP方法测试
  - [x] SubTask 5.1: 使用PUT方法访问签到API
  - [x] SubTask 5.2: 使用PATCH方法访问签到API
  - [x] SubTask 5.3: 使用DELETE方法访问签到API
  - [x] SubTask 5.4: 尝试访问签到结果修改API（/pptSign/updateSign、/pptSign/signedResult等）

- [x] Task 6: 利用泄露密钥构造签到请求
  - [x] SubTask 6.1: 使用K6 Token+DES密钥构造移动端签到请求
  - [x] SubTask 6.2: 使用schild签名构造移动端UA
  - [x] SubTask 6.3: 构造包含修改参数的移动端签到请求

- [x] Task 7: 签到结果API直接访问测试
  - [x] SubTask 7.1: 学生账号直接访问签到结果API（/pptSign/signedResult）
  - [x] SubTask 7.2: 学生账号尝试修改签到结果（POST /pptSign/signedResult）
  - [x] SubTask 7.3: 学生账号尝试访问签到管理API（/ppt/activeAPI/startSign等）
  - [x] SubTask 7.4: 学生账号尝试调用签到统计API获取其他学生签到数据

- [x] Task 8: 签到类型篡改测试
  - [x] SubTask 8.1: 修改签到类型参数（普通签到→手势签到→位置签到→二维码签到）
  - [x] SubTask 8.2: 尝试绕过手势签到的手势验证
  - [x] SubTask 8.3: 尝试绕过位置签到的位置验证
  - [x] SubTask 8.4: 尝试绕过二维码签到的二维码验证

## 阶段4：漏洞分析与影响评估

- [x] Task 9: 漏洞分析与影响评估
  - [x] SubTask 9.1: 汇总所有测试结果，确认哪些方法可修改签到状态
  - [x] SubTask 9.2: 分析漏洞利用的前提条件和技术要求
  - [x] SubTask 9.3: 评估漏洞影响范围和严重程度
  - [x] SubTask 9.4: 构建签到状态修改攻击链

## 阶段5：安全测试报告

- [x] Task 10: 生成安全测试报告
  - [x] SubTask 10.1: 记录所有测试步骤、操作方法、系统响应及结果
  - [x] SubTask 10.2: 分析漏洞技术原理
  - [x] SubTask 10.3: 确定漏洞利用条件、影响范围及严重程度
  - [x] SubTask 10.4: 提出修复建议

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4-8] depends on [Task 3]
- [Task 4, 5, 6, 7, 8] 可并行执行
- [Task 9] depends on [Task 4-8]
- [Task 10] depends on [Task 9]
