# Tasks

- [x] Task 1: 硬编码密钥全面盘点与分类
  - [x] SubTask 1.1: 扫描api/xuexitong/目录下所有Go文件，提取所有硬编码密钥/盐值/Token
  - [x] SubTask 1.2: 对每个密钥进行分类（加密密钥/签名盐值/认证Token/固定IV）
  - [x] SubTask 1.3: 记录每个密钥的文件位置、行号、用途、关联的签名算法
  - [x] SubTask 1.4: 扫描api/gongxue/目录，发现工学云模块额外密钥(K12-K14)
  - [x] SubTask 1.5: 发现源码中硬编码的完整Cookie字符串(K15-K18)

- [x] Task 2: AES登录加密密钥(K1)可利用性验证
  - [x] SubTask 2.1: 使用密钥`u2oh6Vu^HWe4_AES`构造登录请求，验证是否成功登录
  - [x] SubTask 2.2: 评估批量登录可行性（自动化脚本构造登录请求）

- [x] Task 3: schild签名算法(K2/K10/K11)可利用性验证
  - [x] SubTask 3.1: 使用泄露的盐值`ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu`计算schild签名
  - [x] SubTask 3.2: 使用伪造的schild签名构造请求，验证服务端是否接受
  - [x] SubTask 3.3: 评估schild签名是否用于服务端设备校验

- [x] Task 4: 视频学时签名盐值(K3)可利用性验证
  - [x] SubTask 4.1: 使用盐值`d_yHJ!$pdA~5`构造视频学时提交enc签名
  - [x] SubTask 4.2: 使用伪造的enc签名构造学时提交请求，验证服务端是否接受
  - [x] SubTask 4.3: 评估刷课风险（伪造观看时长、跳过观看等）

- [x] Task 5: 人脸验证签名盐值(K4)可利用性验证
  - [x] SubTask 5.1: 使用盐值`uWwjeEKsri`计算人脸验证enc签名
  - [x] SubTask 5.2: 使用伪造的enc签名构造人脸验证请求，验证服务端是否接受
  - [x] SubTask 5.3: 评估绕过人脸识别的风险

- [x] Task 6: 阅读任务签名盐值(K5)可利用性验证
  - [x] SubTask 6.1: 使用盐值`NrRzLDpWB2JkeodIVAn4`构造阅读任务签名
  - [x] SubTask 6.2: 使用伪造的签名构造阅读任务完成请求，验证服务端是否接受

- [x] Task 7: 全局Token(K6)和DES签名密钥(K7)可利用性验证
  - [x] SubTask 7.1: 使用Token`4faa8662c59590c6f43ae9fe5b002b42`+DES密钥`Z(AfY@XS`构造移动端API请求
  - [x] SubTask 7.2: 验证签名是否被服务端接受（已在小组云盘评估中部分验证，需补充更多端点）

- [x] Task 8: 验证码IV(K8)和考试签名(K9)安全评估
  - [x] SubTask 8.1: 分析验证码固定IV`cdd9bfb9e7805d0d2d5f1ad4498f70e1`的安全影响
  - [x] SubTask 8.2: 分析考试签名算法`GetExamSignature`的安全影响
  - [x] SubTask 8.3: 评估考试防作弊签名是否可被伪造

- [x] Task 9: 安全审计报告生成
  - [x] SubTask 9.1: 汇总所有密钥清单和可利用性验证结果
  - [x] SubTask 9.2: 对每个密钥进行风险评级（CVSS或自定义评级）
  - [x] SubTask 9.3: 提出分层修复建议（紧急/中期/长期）
  - [x] SubTask 9.4: 与公开已知的学习通安全漏洞进行对比
  - [x] SubTask 9.5: 整合新发现的工学云模块密钥(K12-K14)
  - [x] SubTask 9.6: 整合新发现的硬编码Cookie和JWT令牌(K15-K18)
  - [x] SubTask 9.7: 整合联网搜索的公开泄露信息
  - [x] SubTask 9.8: 完成攻击链分析

# Task Dependencies
- [Task 2-8] depends on [Task 1]
- [Task 2, 3, 4, 5, 6, 7, 8] 可并行执行
- [Task 9] depends on [Task 2-8]
