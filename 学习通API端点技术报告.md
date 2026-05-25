# 学习通手机端API技术报告

## Why
学习通（超星）手机端App拥有大量未公开文档的API端点，仓库中已有部分逆向实现但不够全面（尤其缺少云盘相关API），需要系统梳理并补充联网收集的信息，形成完整的技术参考。

## What Changes
- 整理仓库中已有的学习通手机端API端点及实现细节
- 补充联网搜索获得的云盘API、数据分析API等端点信息
- 梳理手机端UA签名机制、加密机制、Cookie体系等核心技术细节
- 总结手机端与PC端的差异点

## Impact
- Affected specs: 学习通手机端API逆向分析
- Affected code: api/xuexitong/*, aggregation/xuexitong/*

## ADDED Requirements

### Requirement: 学习通手机端技术报告
系统 SHALL 提供一份完整的学习通手机端API技术报告，涵盖以下所有模块：

#### Scenario: 报告内容完整性
- **WHEN** 用户查阅技术报告
- **THEN** 报告应包含：认证体系、UA签名机制、课程API、章节API、视频学时API、作业API、考试API、讨论API、人脸验证API、验证码API、云盘API、数据分析API、直播API、阅读API、音频API、AI答题API等全部模块的端点信息

---

## 一、手机端核心认证与签名体系

### 1.1 登录认证

**端点**: `POST https://passport2.chaoxing.com/fanyalogin`

**请求参数**:
| 参数 | 值 | 说明 |
|---|---|---|
| fid | -1 | 固定值 |
| uname | AES加密(Base64) | 手机号，AES-CBC加密，KEY=`u2oh6Vu^HWe4_AES`，IV=KEY |
| password | AES加密(Base64) | 密码，同上加密方式 |
| refer | http%3A%2F%2Fi.mooc.chaoxing.com | 固定值 |
| t | true | 固定值 |
| forbidotherlogin | 0 | 固定值 |
| validate | (空) | 验证码相关 |
| doubleFactorLogin | 0 | 双因素登录 |
| independentId | 0 | 独立ID |
| independentNameId | 0 | 独立名称ID |

**加密细节**:
- AES-CBC模式，PKCS7填充
- KEY: `u2oh6Vu^HWe4_AES`（16字节）
- IV: 与KEY相同
- 加密后Base64编码

**返回Cookie关键字段**:
- `fid` - 学校ID
- `_uid` / `UID` - 用户ID
- `vc3` - 验证Cookie
- `uf` - 用户指纹
- `cx_p_token` - P Token
- `p_auth_token` - JWT认证Token
- `xxtenc` - 加密标识
- `DSSTASH_LOG` - 日志标识
- `route` / `jrose` / `k8s` - 负载均衡路由

### 1.2 手机端UA签名机制

**APP版本常量**:
```
APP_VERSION = "6.7.2"
BUILD = "10941_314"
DEVICE_VENDOR = "MI10"
ANDROID_VERSION = "Android 16"
```

**UA格式**（mobile类型）:
```
Mozilla/5.0 (Linux; {ANDROID_VERSION}; {DEVICE_VENDOR} Build/OPM1.171019.019; wv) 
AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 
(schild:{schild_sign}) 
(device:{DEVICE_VENDOR}) 
Language/zh_CN 
com.chaoxing.mobile/ChaoXingStudy_3_{APP_VERSION}_android_phone_{BUILD} 
(@Kalimdor)_{IMEI}
```

**schild签名算法**:
1. 拼接字符串: `(schild:ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu) (device:{model}) Language/{locale} com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build} (@Kalimdor)_{imei}`
2. 对拼接结果计算MD5
3. 返回小写hex字符串

**IMEI生成**: 使用 `TokenHex(16)` 生成32位随机hex字符串

**iPhone UA格式**:
```
Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1
```

### 1.3 移动端inf_enc签名机制

用于 `groupyd.chaoxing.com` 域名下的接口签名验证。

**算法**:
1. 按指定顺序拼接参数: `key1=value1&key2=value2&...`
2. 末尾追加 `&DESKey=Z(AfY@XS`
3. 对整个字符串计算MD5
4. 返回小写hex字符串

**DESKey**: `Z(AfY@XS`

**_c_0_参数**: UUID去掉连字符后的32位字符串

### 1.4 视频学时提交enc签名

**算法**:
```
MD5([clazzId][userId][jobId][objectId][playingTime*1000][d_yHJ!$pdA~5][duration*1000][clipTime])
```

**盐值**: `d_yHJ!$pdA~5`

### 1.5 考试提交签名（GetExamSignature）

**算法**:
1. 生成tokenHex(16) + 时间戳[4:] + 随机数r1 + 随机数r2 + qid
2. 对拼接字符串进行哈希: `temp = (temp << 5) - temp + char`
3. 生成salt: `r1 + r2 + (0x7fffffff & temp) % 10`
4. encVal = `uid_qid|salt`
5. 将encVal每个字符转为数字拼接
6. 取特定位置字符组成cStr，计算e值
7. 对pos字符串逐字符XOR加密

### 1.6 阅读任务enc签名

**算法**:
1. 按key排序拼接value
2. 末尾追加盐值 `NrRzLDpWB2JkeodIVAn4`
3. 计算MD5

---

## 二、域名体系

| 域名 | 用途 |
|---|---|
| passport2.chaoxing.com | 登录认证 |
| passport2-api.chaoxing.com | 认证API（人脸等） |
| mooc1-api.chaoxing.com | 主API（课程、章节、作业、考试等） |
| mooc1.chaoxing.com | MOOC服务（视频提交、文档、直播等） |
| mooc1-1.chaoxing.com | MOOC备用服务 |
| mooc2-ans.chaoxing.com | MOOC答题服务 |
| detect.chaoxing.com | 监控检测 |
| captcha.chaoxing.com | 验证码服务 |
| pan-yz.chaoxing.com | 云盘服务 |
| groupweb.chaoxing.com | 讨论区Web服务 |
| groupyd.chaoxing.com | 讨论区移动端API |
| zhibo.chaoxing.com | 直播服务 |
| stat2-ans.chaoxing.com | AI助手服务 |
| data-xxt.aichaoxing.com | 数据分析服务 |

---

## 三、课程与章节API

### 3.1 获取课程列表
- **端点**: `GET https://mooc1-api.chaoxing.com/mycourse/backclazzdata`
- **UA**: mobile
- **认证**: Cookie
- **返回**: JSON，包含channelList课程列表

### 3.2 获取课程完成状态
- **端点**: `GET https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu-job-info?clazzPersonStr={encodedStr}`
- **UA**: mobile（含完整schild签名）

### 3.3 拉取章节信息
- **端点**: `GET https://mooc1-api.chaoxing.com/gas/clazz?id={key}&personid={cpi}&fields={fields}&view=json`
- **fields参数**: `id,bbsid,classscore,isstart,allowdownload,chatid,name,state,isfiled,visiblescore,hideclazz,begindate,forbidintoclazz,coursesetting.fields(id,courseid,hiddencoursecover,coursefacecheck),course.fields(id,belongschoolid,name,infocontent,objectid,app,bulletformat,mappingcourseid,imageurl,teacherfactor,jobcount,knowledge.fields(id,name,indexOrder,parentnodeid,status,isReview,layer,label,jobcount,begintime,endtime,attachment.fields(id,type,objectid,extension).type(video)))`

### 3.4 获取章节任务点状态
- **端点**: `POST https://mooc1-api.chaoxing.com/job/myjobsnodesmap`
- **参数**: view, nodes, clazzid, time, userid, cpi, courseid

### 3.5 拉取章节卡片资源
- **端点**: `GET https://mooc1-api.chaoxing.com/gas/knowledge?id={nodeId}&courseid={courseId}&fields={fields}&view=json&token=4faa8662c59590c6f43ae9fe5b002b42`
- **固定token**: `4faa8662c59590c6f43ae9fe5b002b42`

### 3.6 章节卡片资源（接口2）
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/knowledge/cards?clazzid={clazzid}&courseid={courseid}&knowledgeid={knowledgeid}&num=0&ut=s&cpi={cpi}&v=2025-0424-1038-3&mooc2=1`

### 3.7 手机端章节任务卡片
- **端点**: `GET https://mooc1-api.chaoxing.com/knowledge/cards?clazzid={classId}&courseid={courseId}&knowledgeid={knowledgeId}&num={cardIndex}&isPhone=1&control=true&cpi={cpi}`
- **注意**: `isPhone=1` 为手机端特有参数

### 3.8 进入章节前调用
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudyAjax?courseId={courseId}&clazzid={clazzid}&chapterId={chapterId}&cpi={cpi}&verificationcode=&mooc2=1&toComputer=false&microTopicId=0`

---

## 四、视频学时提交API

### 4.1 PC端视频学时提交
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/multimedia/log/a/{cpi}/{dtoken}?clazzId=...&playingTime=...&duration=...&clipTime=...&objectId=...&otherInfo=...&courseId=...&jobid=...&userid=...&isdrag=...&view=pc&enc=...&rt=...&videoFaceCaptureEnc=...&dtype=Video&_t=...&attDuration=...&attDurationEnc=...`
- **isdrag值**: 0=正常播放, 2=暂停, 3=开始播放
- **view**: `pc`

### 4.2 手机端视频学时提交
- **端点**: 同上URL结构，但 `view=json`
- **Cookie过滤**: 仅发送 `fid,k8s,route,fanyamoocs,_uid,UID,vc3,uf,cx_p_token,p_auth_token,xxtenc,DSSTASH_LOG,jrose,thirdRegist,videojs_id`
- **附加Cookie**: `fanyamoocs=11401F839C536D9E`, `thirdRegist=0`, `videojs_id=1778753`

### 4.3 视频资源信息获取
- **端点**: `GET https://mooc1-api.chaoxing.com/ananas/status/{objectId}?k={fid}&flag=normal&_dc={timestamp}`
- **Referer**: `https://mooc1-api.chaoxing.com/ananas/modules/video/index_wap.html?v=372024-1121-1947`

---

## 五、作业API

### 5.1 作业列表
- **端点**: `GET https://mooc1-api.chaoxing.com/work/task-list?courseId={courseId}&classId={classId}&cpi={cpi}`
- **Header**: `X-Requested-With: com.chaoxing.mobile`

### 5.2 进入作业页面
- **端点**: `GET https://mooc1-api.chaoxing.com/android/mtaskmsgspecial?taskrefId=...&msgId=...&courseId=...&userId=...&clazzId=...&type=...&enc_task=...`
- **注意**: 会重定向，需跟踪最终URL

### 5.3 获取作业题目（接口1 - 手机端）
- **端点**: `GET https://mooc1-api.chaoxing.com/android/mworkspecial?courseid=...&workid=...&jobid=...&needRedirect=true&knowledgeid=...&userid=...&ut=s&clazzId=...&cpi=...&ktoken=...&enc=...`

### 5.4 获取作业题目（接口2 - 手机端）
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/work/phone/doHomeWork?keyboardDisplayRequiresUserAction=1&courseId=...&workAnswerId=...&workId=...&knowledgeId=...&classId=...&oldWorkId=...&jobId=&mooc=0&enc=...&cpi=...&originJobId=...`

### 5.5 获取作业题目（接口3 - 手机端）
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/work/phone/work?workId=...&courseId=...&clazzId=...&knowledgeId=...&jobId=&enc=...&cpi=...&originJobId=...`

### 5.6 拉取作业试卷
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/work/phone/doHomeWork?courseId=...&workId=...&cpi=...&workAnswerId=...&classId=...&oldWorkId&mooc=1&msgId=...&source=...&checkIntegrity=true&enc=...&keyboardDisplayRequiresUserAction=...`

### 5.7 提交作业答案（手机端）
- **端点**: `POST https://mooc1-api.chaoxing.com/mooc-ans/work/phone/doNormalHomeWorkSubmit?tempSave={bool}`
- **Content-Type**: `application/x-www-form-urlencoded; charset=UTF-8`
- **X-Requested-With**: `XMLHttpRequest`

### 5.8 新版作业提交
- **端点**: `POST https://mooc1.chaoxing.com/mooc-ans/work/addStudentWorkNew?_classId=...&courseid=...&token=...&totalQuestionNum=...&ua=pc&formType=post&saveStatus=1&version=1&tempsave=1`
- **Content-Type**: `multipart/form-data`

---

## 六、考试API

### 6.1 考试列表
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/exam/phone/task-list?courseId=...&classId=...&cpi=...`
- **UA**: 使用专门的考试UA（XXTEXAMUA）

### 6.2 进入考试页面
- **端点**: `GET https://mooc1-api.chaoxing.com/exam-ans/android/mtaskmsgspecial?taskrefId=...&msgId=...&courseId=...&userId=...&clazzId=...&type=...&enc_task=...`

### 6.3 拉取考试试卷
- **端点**: `GET https://mooc1-api.chaoxing.com/exam-ans/exam/phone/start?courseId=...&classId=...&examId=...&source=...&examAnswerId=...&cpi=...&keyboardDisplayRequiresUserAction=...&imei=...&faceDetectionResult&captchavalidate=...&jt=...&_v=0.3868294515418076&cxcid&cxtime&signt&_signcode=3&_signc=0&_signe=3-1&signk`
- **注意**: 需要先过滑块验证码获取captchavalidate参数

### 6.4 拉取考试题目
- **端点**: `GET https://mooc1-api.chaoxing.com/exam-ans/exam/test/reVersionTestStartNew?keyboardDisplayRequiresUserAction=1&courseId=...&classId=...&source=0&imei={IMEI}&tId=...&id=...&p=1&start={index}&cpi=...&isphone=true&monitorStatus=0&monitorOp=-1&remainTimeParam=...&relationAnswerLastUpdateTime=...&enc=...`

### 6.5 提交考试答案
- **端点**: `POST https://mooc1-api.chaoxing.com/exam-ans/exam/test/reVersionSubmitTestNew?classId=...&courseId=...&testPaperId=...&testUserRelationId=...&cpi=...&version=1&tempSave={bool}&pos={sig}&rd={rd}&value={value}&qid=...&_edt=...&_csign=1&_signcode=3&_signc=0&_signe=3-1&_signk&_cxcid&_cxtime&_signt`

### 6.6 重考接口
- **端点**: `GET https://mooc1-api.chaoxing.com/exam-ans/exam/phone/restartOp?examId=...&examAnswerId=...&courseId=...&classId=...&source=0&code=`

---

## 七、讨论（BBS）API

### 7.1 拉取讨论任务点链接
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/bbscircle/chapter?mtopicid=...&jobid=...&isPortal=...&knowledgeid=...&ut=...&clazzId=...&enc=...&utenc=...&courseid=...&isJob=...`

### 7.2 手机端讨论信息
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/bbscircle/chapter?mtopicid=...&jobid=...&isPortal=false&knowledgeid=...&ut=s&clazzId=...&enc&utenc=undefined&courseid=...&isJob=true&isMobile=true`
- **注意**: `isMobile=true` 为手机端特有参数

### 7.3 拉取讨论详情（手机端）
- **端点**: `POST https://groupyd.chaoxing.com/apis/topic/getTopic?_c_0_=...&token=4faa8662c59590c6f43ae9fe5b002b42&_time=...&inf_enc=...`
- **Body**: `puid=...&maxW=1080&topicId=...`
- **需要inf_enc签名**

### 7.4 回复讨论（PC端）
- **端点**: `POST https://groupweb.chaoxing.com/pc/invitation/{topicUUid}/addReplys`

### 7.5 回复讨论（手机端）
- **端点**: `POST https://groupyd.chaoxing.com/apis/invitation/addReply?token=4faa8662c59590c6f43ae9fe5b002b42&_time=...&_c_0_=...&puid=...&uuid=...&tag=classId{classId}&maxW=1080&topicUUID=...&anonymous=0&inf_enc=...`
- **Body**: `content={encoded_content}`
- **需要inf_enc签名**

### 7.6 获取utEnc参数
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudy?chapterId=...&courseId=...&clazzid=...&enc=...`
- **返回**: HTML页面中 `var utEnc="xxx";`

---

## 八、人脸验证API

### 8.1 获取云盘Token（用于人脸）
- **端点**: `GET https://pan-yz.chaoxing.com/api/token/uservalid`
- **返回**: JSON含 `_token` 字段

### 8.2 获取历史人脸图片
- **端点**: `GET https://passport2-api.chaoxing.com/api/getUserFaceid?enc={enc}&token=4faa8662c59590c6f43ae9fe5b002b42&_time={timestamp}`
- **enc计算**: `MD5(puid + "uWwjeEKsri")`

### 8.3 上传人脸图片
- **端点**: `POST https://pan-yz.chaoxing.com/upload`
- **参数**: uploadtype=face, _token, puid, file(JPG图片)
- **Content-Type**: multipart/form-data

### 8.4 获取人脸QrCode（进入课程时）
- **端点**: `GET https://mooc1.chaoxing.com/visit/stucoursemiddle?courseid=...&clazzid=...&cpi=...&ismooc2=1`
- **返回**: HTML中含uuid和qrcEnc

### 8.5 获取人脸QrCode（章节内）
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudyAjax?courseId=...&clazzid=...&chapterId=...&cpi=...&verificationcode=&mooc2=1&toComputer=false&microTopicId=0`

### 8.6 生成Qr码
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/qr/produce?uuid=...&enc=...&clazzid=...&videojobid=...&chaptervideoobjectid=...&videoCollectTime=0`

### 8.7 获取Qr码状态
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/qr/getqrstatus?uuid=...&enc=...&clazzid=...&courseid=...&cpi=...&collectionTime=0&mid=...&videoObjectId=...&videoRandomCollectTime=...&chapterId=...`

### 8.8 更新Qr码状态（PC端）
- **端点**: `POST https://mooc1-api.chaoxing.com/qr/updateqrstatus`
- **Body**: clazzId, courseId, uuid, qrcEnc, cpi, liveDetectionStatus, signt, signk, cxtime, cxcid, knowledgeid, objectId, videojobid, videoCollectTime, chaptervideoobjectid

### 8.9 手机端过人脸（新接口1）
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus?courseId=...&clazzId=...&cpi=...&chapterId=...&objectId=...&liveDetectionStatus=1&signt=&signk=&cxtime=&cxcid=&type=1`

### 8.10 手机端过人脸（新接口2 - POST）
- **端点**: `POST https://mooc1-api.chaoxing.com/mooc-ans/facephoto/clientfacecheckstatus?courseId2=...`
- **Body**: courseId, clazzId, cpi, liveDetectionStatus, objectId, signt, signk, cxtime, cxcid, type

### 8.11 手机端过人脸（老接口）
- **端点**: `POST https://mooc1-api.chaoxing.com/mooc-ans/knowledge/uploadInfo`
- **Body**: clazzId, courseId, knowledgeId, uuid, qrcEnc, objectId

### 8.12 开始人脸检测
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/knowledge/startface?clazzid=...&courseid=...&knowledgeid=...&cpi=...&type=1`

### 8.13 继续学习（人脸后）
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/facephoto/continuelearn?courseId=...&clazzId=...&cpi=...&objectId=...&errorLogId=...&type=1`

---

## 九、验证码API

### 9.1 获取图片验证码
- **端点**: `GET https://mooc1-api.chaoxing.com/processVerifyPng.ac?t={timestamp}`

### 9.2 获取章节验证码
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/kaptcha-img/code?{timestamp}`

### 9.3 提交验证码
- **端点**: `POST https://mooc1-api.chaoxing.com/html/processVerify.ac`
- **Body**: app=0, ucode={code}
- **成功标志**: HTTP 302重定向

### 9.4 提交章节验证码
- **端点**: `POST https://mooc1.chaoxing.com/mooc-ans/verifyCode/studychapter`
- **Body**: code={code}

### 9.5 获取滑块验证码配置
- **端点**: `GET https://captcha.chaoxing.com/captcha/get/conf?callback=cx_captcha_function&captchaId=...&_={timestamp}`

### 9.6 获取滑块验证码图片
- **端点**: `GET https://captcha.chaoxing.com/captcha/get/verification/image?callback=cx_captcha_function&captchaId=...&type=slide&version=1.1.20&captchaKey=...&token=...&referer=...`
- **token计算**: `MD5(serverTime + captchaId + "slide" + captchaKey) : serverTime+300000`

### 9.7 验证滑块
- **端点**: `GET https://captcha.chaoxing.com/captcha/check/verification/result?callback=cx_captcha_function&captchaId=...&type=slide&token=...&textClickArr=[{"x":{xPoint}}]&coordinate=[]&runEnv=10&version=1.1.20&t=a&iv=...`

---

## 十、云盘API（联网补充）

### 10.1 获取云盘Token
- **端点**: `GET https://pan-yz.chaoxing.com/api/token/uservalid`
- **认证**: Cookie（UID, uf）
- **返回**: JSON含 `result`, `_token`

### 10.2 获取用户信息
- **端点**: `GET https://pan-yz.chaoxing.com/api/info?puid={puid}&_token={token}`

### 10.3 获取磁盘容量
- **端点**: `GET https://pan-yz.chaoxing.com/api/getUserDiskCapacity?puid={puid}&_token={token}`

### 10.4 列出目录文件
- **端点**: `GET https://pan-yz.chaoxing.com/api/getMyDirAndFiles?puid={puid}&fldid={fldid}&orderby=d&order=desc&page=1&size=100&_token={token}&addrec=false&showCollect=1`

### 10.5 创建文件（秒传检测）
- **端点**: `POST https://pan-yz.chaoxing.com/opt/createfilenew`
- **参数**: size, fn(文件名), puid, fldid(文件夹ID)
- **文件**: file0(首512KB), file1(末1MB前的512KB)
- **返回**: 含crc(用于秒传检测), timemil(用于FTP上传)

### 10.6 FTP上传（大文件>200MB）
- **FTP服务器**: 从 `/api/info` 获取host
- **FTP用户**: `usertemp`
- **FTP密码**: `0GYF0hBAbsXVBZCUPaSOVS`
- **上传路径**: `/{froot}/{timemil}/{filename}`
- **被动模式**: 是

### 10.7 同步上传完成通知
- **端点**: `POST https://pan-yz.chaoxing.com/api/notification/rsyncsucss`
- **参数**: puid, rf(timemil), _token, pntid(可选)

### 10.8 CRC秒传状态查询
- **端点**: `GET https://pan-yz.chaoxing.com/api/crcstatus?puid={puid}&crc={crc}&_token={token}`

### 10.9 上传文件（通用入口）
- 小文件(<200MB): 直接FTP上传 + rsyncsucss
- 大文件(>200MB): createfilenew秒传检测 → FTP上传 → rsyncsucss → crcstatus

### 10.10 删除文件
- **端点**: `POST https://pan-yz.chaoxing.com/api/delete`
- **参数**: puid, resids(文件ID，逗号分隔), _token

### 10.11 上传人脸图片
- **端点**: `POST https://pan-yz.chaoxing.com/upload`
- **参数**: uploadtype=face, _token, puid, file
- **Content-Type**: multipart/form-data

---

## 十一、直播API

### 11.1 拉取直播信息
- **端点**: `GET https://mooc1.chaoxing.com/ananas/live/liveinfo?liveid=...&userid=...&clazzid=...&knowledgeid=...&courseid=...&jobid=...&ut=s`

### 11.2 直播关系建立
- **端点**: `GET https://mooc1.chaoxing.com/mooc-ans/live/relation?courseid=...&knowledgeid=...&ut=s&jobid=...&aid=...`

### 11.3 直播观看时刻上报
- **端点**: `GET https://zhibo.chaoxing.com/apis/live/put/watchMoment?liveId=...&streamName=...&vdoid=...&watchMoment=...&t=...&u=...`

### 11.4 直播学时提交
- **端点**: `GET https://zhibo.chaoxing.com/saveTimePc?streamName=...&vdoid=...&userId=...&isStart=1&t=...&courseId=...`

---

## 十二、文档与阅读API

### 12.1 文档任务点完成
- **端点**: `GET https://mooc1.chaoxing.com/ananas/job/document?jobid=...&knowledgeid=...&courseid=...&clazzid=...&jtoken=...&_dc=...`

### 12.2 文档完成（另一接口）
- **端点**: `GET https://mooc1.chaoxing.com/ananas/job?jobid=...&knowledgeid=...&courseid=...&clazzid=...&jtoken=...&_dc=...`

### 12.3 阅读任务点完成（PC端）
- **端点**: `GET https://mooc1-1.chaoxing.com/ananas/job/readv2?jobid=...&knowledgeid=...&courseid=...&clazzid=...&jtoken=...&checkMicroTopic=true&microTopicId=0&_dc=...`

### 12.4 阅读任务点完成（手机端）
- **端点**: `GET https://mooc1-api.chaoxing.com/ananas/job/readv2?jobid=...&knowledgeid=...&courseid=...&clazzid=...&jtoken=...&checkMicroTopic=true&microTopicId=0&_dc=...`

### 12.5 外链任务点完成
- **端点**: `GET https://mooc1.chaoxing.com/ananas/job/hyperlink?jobid=...&knowledgeid=...&courseid=...&clazzid=...&jtoken=...&checkMicroTopic=true&microTopicId=undefined&_dc=...`

### 12.6 阅读时间上报
- **端点**: `GET https://data-xxt.aichaoxing.com/analysis/ac_mark?f=readPoint&u={userId}&d={encoded_data}&t={timestamp}&enc={enc}`
- **enc盐值**: `NrRzLDpWB2JkeodIVAn4`

---

## 十三、音频API

### 13.1 手机端音频提交
- **端点**: `GET https://mooc1-api.chaoxing.com/mooc-ans/multimedia/log?objectId=...&clazzId=...&userid=...&jobid=...&duration=...&otherInfo=...&courseId=...&dtype=Audio&view=json&playingTime=...&isdrag=...&enc=...&_dc=...`
- **isdrag值**: 4=音频播放结束

---

## 十四、AI答题API

### 14.1 获取AI参数
- **端点**: `GET https://stat2-ans.chaoxing.com/bot/index?fromWorkbench=true&upload=true&clazzid=...&showToolbox=false&bgColorNone=true&app_id=1192651262850&courseid=...&cpi=...&bot_id=7438777570621653018&ut=s`
- **固定参数**: app_id=1192651262850, bot_id=7438777570621653018

### 14.2 AI对话（流式）
- **端点**: `POST https://stat2-ans.chaoxing.com/stat2/bot/talk-v1?cozeEnc=...&botId=7438777570621653018&userId=...&appId=1192651262850&courseid=...&clazzid=...&ut=s`
- **Body**: JSON数组，含role和content
- **返回**: 流式响应，以`$_$`分隔，type=coreAnswer的内容为答案

---

## 十五、数据分析API（联网补充）

### 15.1 课程Tab切换上报
- **端点**: `GET http://data.xxt.aichaoxing.com/analysis/course/tab?u={userId}&sign={sign}&description={desc}&enc={enc}&personid={personid}&classid={classid}&courseid={courseid}`
- **sign值**: task(任务), chapters(章节), more(更多)
- **enc**: MD5签名，逆向分析可得算法

### 15.2 监控检测
- **端点**: `GET https://detect.chaoxing.com/api/monitor?version=...&refer=...&from=&fid=...&jsoncallback=jsonp...&t=...`

---

## 十六、手机端与PC端差异总结

| 维度 | 手机端 | PC端 |
|---|---|---|
| UA | 含schild签名的移动端UA | 桌面浏览器UA |
| 作业获取 | `/android/mworkspecial` 或 `/work/phone/doHomeWork` | `/work/doHomeWork` |
| 作业提交 | `/work/phone/doNormalHomeWorkSubmit` | `/work/addStudentWorkNew` |
| 考试进入 | `/exam-ans/android/mtaskmsgspecial` | Web端路径 |
| 考试拉取 | `/exam-ans/exam/phone/start` | Web端路径 |
| 考试列表 | `/exam-ans/exam/phone/task-list` | Web端路径 |
| 讨论回复 | `groupyd.chaoxing.com/apis/invitation/addReply` | `groupweb.chaoxing.com/pc/invitation/addReplys` |
| 视频提交view参数 | `view=json` | `view=pc` |
| 人脸验证 | `clientfacecheckstatus` 或 `knowledge/uploadInfo` | `qr/updateqrstatus` |
| 阅读完成 | `mooc1-api.chaoxing.com/ananas/job/readv2` | `mooc1-1.chaoxing.com/ananas/job/readv2` |
| Cookie过滤 | 需过滤特定Cookie | 全量Cookie |
| 签名机制 | inf_enc签名（groupyd域名） | 无需 |
| X-Requested-With | `com.chaoxing.mobile` | `XMLHttpRequest` |
| isPhone参数 | `isPhone=1` | 无 |

---

## 十七、关键固定值汇总

| 名称 | 值 | 用途 |
|---|---|---|
| AES KEY | `u2oh6Vu^HWe4_AES` | 登录加密 |
| 视频enc盐值 | `d_yHJ!$pdA~5` | 视频学时提交签名 |
| DESKey | `Z(AfY@XS` | inf_enc签名 |
| 阅读enc盐值 | `NrRzLDpWB2JkeodIVAn4` | 阅读时间上报签名 |
| 人脸enc盐值 | `uWwjeEKsri` | 人脸图片获取签名 |
| 固定token | `4faa8662c59590c6f43ae9fe5b002b42` | 章节卡片/AI/人脸接口 |
| AI app_id | `1192651262850` | AI答题 |
| AI bot_id | `7438777570621653018` | AI答题 |
| schild密钥 | `ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu` | UA签名 |
| FTP密码 | `0GYF0hBAbsXVBZCUPaSOVS` | 云盘FTP上传 |
| FTP用户 | `usertemp` | 云盘FTP上传 |
| fanyamoocs | `11401F839C536D9E` | 视频提交Cookie |
