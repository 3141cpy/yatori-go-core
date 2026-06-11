# Tasks

- [ ] Task 1: 签到流程验证 — preSign→analysis→analysis2→stuSignajax完整链
  - [ ] 1.1 验证/newsign/preSign接口（POST，参数courseId/classId/activePrimaryId/uid/ext）
  - [ ] 1.2 验证/pptSign/analysis接口（GET，从返回HTML提取code）
  - [ ] 1.3 验证/pptSign/analysis2接口（GET，传入code）
  - [ ] 1.4 验证完整流程后stuSignajax是否可成功签到
  - [ ] 1.5 对比跳过preSign/analysis步骤直接调用stuSignajax的差异

- [ ] Task 2: V2 API信息泄露验证
  - [ ] 2.1 验证/v2/apis/active/student/activelist（获取活动列表）
  - [ ] 2.2 验证/v2/apis/active/getPPTActiveInfo（获取签到详情，含签到类型/验证码/人脸标记）
  - [ ] 2.3 检查返回数据中是否包含签到码/enc等敏感信息
  - [ ] 2.4 检查学生是否可获取其他学生的签到信息

- [ ] Task 3: 人脸识别绕过验证
  - [ ] 3.1 验证/pptSign/check-face-result接口
  - [ ] 3.2 验证signToken算法（MD5签名，从clientId解密获取cxcid和sc）
  - [ ] 3.3 验证LiveDetectionStatus=1和collectStatus=1硬编码绕过
  - [ ] 3.4 验证上传任意照片作为人脸图片的可行性

- [ ] Task 4: 二维码代签验证
  - [ ] 4.1 验证enc参数是否可跨用户复用
  - [ ] 4.2 验证同一enc为多个用户签到的可行性
  - [ ] 4.3 验证enc的有效期和限制

- [ ] Task 5: 拍照签到绕过验证
  - [ ] 5.1 验证pan-yz.chaoxing.com云盘token获取
  - [ ] 5.2 验证云盘图片上传（Multipart）
  - [ ] 5.3 验证objectId参数在stuSignajax中的使用
  - [ ] 5.4 验证从相册选图上传绕过实时拍照

- [ ] Task 6: 验证码系统安全评估
  - [ ] 6.1 验证captcha.chaoxing.com验证码配置获取
  - [ ] 6.2 验证滑块验证码图片获取
  - [ ] 6.3 评估验证码安全强度和自动化绕过可能性
  - [ ] 6.4 验证captchaId硬编码（Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU）

- [ ] Task 7: 手势/签到码暴力破解评估
  - [ ] 7.1 验证/widget/sign/pcStuSignController/checkSignCode接口
  - [ ] 7.2 评估签到码暴力破解可行性（返回result=1表示正确）
  - [ ] 7.3 评估手势编码暴力破解可行性

- [ ] Task 8: IM群聊签到获取验证
  - [ ] 8.1 验证im.chaoxing.com/webim/me获取IM配置
  - [ ] 8.2 验证IM群组列表获取
  - [ ] 8.3 验证从群聊消息中提取签到活动信息

- [ ] Task 9: 安全测试报告更新
  - [ ] 9.1 整理所有新发现漏洞
  - [ ] 9.2 更新/workspace/sign_vuln_report.md至v10.0

# Task Dependencies
- Task 1 是核心任务（签到流程验证），其他任务可并行
- Task 3 depends on Task 1（需要先完成签到流程）
- Task 4 depends on Task 1（需要先完成签到流程）
- Task 5 depends on Task 1（需要先完成签到流程）
- Task 9 depends on all previous tasks
