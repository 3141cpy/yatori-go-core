# 学习通单位云盘（小组云盘）API技术报告

## Why
之前的技术报告仅覆盖了个人云盘（pan-yz.chaoxing.com）的API，但学习通还存在一套完全不同的**单位/小组云盘**体系，使用不同的域名、API路径和认证方式。本报告补充调查此部分内容。

## What Changes
- 新增小组云盘（ChaoXingGroupDrive）完整API体系
- 新增小组云盘域名体系（groupweb.chaoxing.com / noteyd.chaoxing.com）
- 新增小组云盘与个人云盘的差异对比
- 补充学校云盘SSO入口信息

## Impact
- Affected specs: research-xuexitong-mobile-api（原报告第十章云盘部分需补充）
- Affected code: 仓库中暂无小组云盘相关代码实现

## ADDED Requirements

### Requirement: 单位云盘技术报告
系统 SHALL 提供一份完整的学习通单位/小组云盘API技术报告

#### Scenario: 报告内容完整性
- **WHEN** 用户查阅技术报告
- **THEN** 报告应包含：小组云盘概述、域名体系、认证方式、文件列表API、文件下载API、文件上传API、文件夹管理API、文件移动/删除API、权限体系、与个人云盘差异对比

---

## 一、小组云盘概述

### 1.1 什么是小组云盘

小组云盘（ChaoXingGroupDrive）是超星学习通中基于"小组"功能的共享云存储空间。与个人云盘不同，小组云盘依附于超星的"小组/圈子"体系，文件存储在小组的资源库中，所有小组成员可共享访问。

**关键特征**：
- 需要代理才能使用（OnlyProxy: true）
- 单文件大小限制2GB
- **没有总容量限制**
- 文件ID格式：`{recordId}${fileId}`（文件夹为纯数字ID）
- 手机端上传的文件与网页端上传的文件JSON结构有差异

### 1.2 如何获取bbsid

bbsid是小组云盘的核心标识参数，获取方式：
1. 登录超星后进入个人空间
2. 进入"小组"功能
3. 新建或进入一个小组
4. URL中即包含bbsid参数（如 `https://groupweb.chaoxing.com/group/{bbsid}`）

### 1.3 学校云盘SSO入口

部分高校通过SSO方式接入超星云盘，入口URL格式：
```
http://fysso.chaoxing.com/sso/to{schoolCode}?refer=http://pan-yz.chaoxing.com/pcuserpan/index
```

---

## 二、域名体系（小组云盘专用）

| 域名 | 用途 | 对应个人云盘域名 |
|---|---|---|
| groupweb.chaoxing.com | 小组云盘API（文件列表、文件夹管理、资源操作） | pan-yz.chaoxing.com |
| noteyd.chaoxing.com | 小组云盘下载API（文件状态、下载链接） | pan-yz.chaoxing.com |
| pan-yz.chaoxing.com | 文件上传（与个人云盘共用） | pan-yz.chaoxing.com |
| passport2.chaoxing.com | 登录认证（与个人云盘共用） | passport2.chaoxing.com |

---

## 三、认证方式

### 3.1 登录认证
与个人云盘完全相同：`POST https://passport2.chaoxing.com/fanyalogin`
- AES-CBC加密，KEY: `u2oh6Vu^HWe4_AES`
- 返回Cookie用于后续请求

### 3.2 请求认证
所有小组云盘API请求需要携带：
- **Cookie**: 登录后获取的完整Cookie字符串
- **Referer**: `https://chaoxing.com/`
- **Accept**: `application/json, text/plain, */*`

### 3.3 Cookie自动刷新
Cookie有效期约12小时，需定时刷新（AList实现为每12小时自动重新登录）

---

## 四、文件列表API

### 4.1 获取文件夹列表（recType=1）
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/getResourceList`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | folderId | {folderId} | 文件夹ID，根目录为-1 |
  | recType | 1 | 1=文件夹 |
- **认证**: Cookie + Referer
- **返回**: ListFileResp JSON

### 4.2 获取文件列表（recType=2）
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/getResourceList`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | folderId | {folderId} | 文件夹ID，根目录为-1 |
  | recType | 2 | 2=文件 |
- **认证**: Cookie + Referer
- **返回**: ListFileResp JSON

**注意**: 需要分别请求recType=1和recType=2来获取文件夹和文件，然后合并结果。

### 4.3 手机端文件特殊处理
手机端上传的文件没有`fileID`字段，但`ObjectID`与`fileID`相同，可代替：
```
if file.Content.FileID == "" {
    file.Content.FileID = file.Content.ObjectID
}
```

### 4.4 手机端与网页端JSON差异
- 网页端: `"puid": 54321, "size": 12345`（纯数字）
- 手机端: `"puid": "54321", "size": "12345"`（字符串数字）

解析时需要兼容两种格式。

---

## 五、文件下载API

### 5.1 获取文件下载链接
- **端点**: `POST https://noteyd.chaoxing.com/screen/note_note/files/status/{fileId}`
- **fileId提取**: 从文件ID `{recordId}${fileId}` 中取 `$` 后面的部分
- **Headers**:
  - Cookie: 登录Cookie
  - Referer: `https://chaoxing.com/`
  - User-Agent: 可自定义
- **返回**: DownResp JSON
  ```json
  {
    "msg": "",
    "duration": 0,
    "download": "https://...（下载直链）",
    "fileStatus": "",
    "url": "",
    "status": true
  }
  ```

### 5.2 下载请求
使用返回的`download`字段作为下载URL，需携带：
- Cookie: 登录Cookie
- Referer: `https://chaoxing.com/`
- User-Agent: 与获取下载链接时相同

支持多线程并发下载（Concurrency: 2, PartSize: 10MB）。

---

## 六、文件上传API

### 6.1 获取上传配置
- **端点**: `GET https://noteyd.chaoxing.com/pc/files/getUploadConfig`
- **认证**: Cookie
- **返回**: UploadDataRsp JSON
  ```json
  {
    "result": 1,
    "msg": {
      "puid": 12345,
      "token": "xxxxx"
    }
  }
  ```

### 6.2 上传文件到云盘
- **端点**: `POST https://pan-yz.chaoxing.com/upload`
- **Content-Type**: `multipart/form-data`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | file | {文件二进制} | 文件内容 |
  | _token | {token} | 从getUploadConfig获取 |
  | puid | {puid} | 从getUploadConfig获取 |
- **返回**: UploadFileDataRsp JSON
  ```json
  {
    "result": true,
    "msg": "success",
    "crc": "xxxxx",
    "objectId": "xxxxx",
    "resid": 12345,
    "puid": 12345,
    "data": { ... }
  }
  ```

### 6.3 将上传文件添加到小组资源
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/addResource`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | pid | {parentId} | 父文件夹ID |
  | type | yunpan | 固定值 |
  | params | [{...}] | URL编码的JSON数组 |
- **params结构**:
  ```json
  [{
    "key": "{objectId}",
    "cataid": "100000019",
    "param": { ... UploadFileDataRsp.data ... }
  }]
  ```
- **cataid固定值**: `100000019`

---

## 七、文件夹管理API

### 7.1 创建文件夹
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/addResourceFolder`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | name | {dirName} | 文件夹名称 |
  | pid | {parentId} | 父文件夹ID |
- **返回**: ListFileResp JSON（result=1表示成功）

### 7.2 重命名文件夹
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/updateResourceFolderName`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | folderId | {folderId} | 文件夹ID |
  | name | {newName} | 新名称 |
- **注意**: 不支持修改文件名（仅支持文件夹重命名）

---

## 八、文件移动与删除API

### 8.1 移动文件夹
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/moveResource`
- **参数（文件夹）**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | folderIds | {folderId} | 源文件夹ID |
  | targetId | {targetId} | 目标文件夹ID |

### 8.2 移动文件
- **端点**: 同上
- **参数（文件）**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | recIds | {recordId} | 文件recordId（ID中$前的部分） |
  | targetId | {targetId} | 目标文件夹ID |

### 8.3 删除文件夹
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/deleteResourceFolder`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | folderIds | {folderId} | 文件夹ID |

### 8.4 删除文件
- **端点**: `GET https://groupweb.chaoxing.com/pc/resource/deleteResourceFile`
- **参数**:
  | 参数 | 值 | 说明 |
  |---|---|---|
  | bbsid | {bbsid} | 小组ID |
  | recIds | {recordId} | 文件recordId（ID中$前的部分） |

---

## 九、权限体系（UserAuth）

小组云盘的API返回中包含完整的权限信息，结构如下：

### 9.1 小组权限（groupAuth）
| 权限字段 | 说明 |
|---|---|
| addData | 添加数据 |
| addDataFolder | 添加数据文件夹 |
| addLebel | 添加标签 |
| addManager | 添加管理员 |
| addMem | 添加成员 |
| addTopicFolder | 添加话题文件夹 |
| delData | 删除数据 |
| delDataFolder | 删除数据文件夹 |
| delMem | 删除成员 |
| dismiss | 解散小组 |
| examEnc | 考试加密 |
| isShowCircleCloudButton | 显示圈子云盘按钮 |
| isShowCompanyButton | 显示单位按钮 |
| modifyDataFolder | 修改数据文件夹 |
| modifyName | 修改名称 |
| showDataFolder | 显示数据文件夹 |
| showRecycleBin | 显示回收站 |
| showForward | 显示转发 |
| showGroupChat | 显示群聊 |

### 9.2 操作权限（operationAuth）
| 权限字段 | 说明 |
|---|---|
| add | 添加 |
| addTopicToFolder | 添加话题到文件夹 |
| delete | 删除 |
| reply | 回复 |
| update | 更新 |
| topSet | 置顶设置 |

---

## 十、数据结构定义

### 10.1 File结构
```json
{
  "cataid": 0,
  "cfid": 0,
  "content": {
    "cfid": 0,
    "pid": 0,
    "folderName": "",
    "shareType": 0,
    "preview": "",
    "filetype": "",
    "previewUrl": "",
    "isImg": false,
    "parentPath": "",
    "icon": "",
    "suffix": "",
    "duration": 0,
    "pantype": "",
    "puid": 0,
    "filepath": "",
    "crc": "",
    "isfile": false,
    "residstr": "",
    "objectId": "",
    "extinfo": "",
    "thumbnail": "",
    "creator": 0,
    "resTypeValue": 0,
    "uploadDateFormat": "",
    "disableOpt": false,
    "downPath": "",
    "sort": 0,
    "topsort": 0,
    "restype": "",
    "size": 0,
    "uploadDate": 0,
    "fileSize": "",
    "name": "",
    "fileId": ""
  },
  "creatorId": 0,
  "des_id": "",
  "id": 0,
  "inserttime": 0,
  "key": "",
  "norder": 0,
  "ownerId": 0,
  "ownerType": 0,
  "path": "",
  "rid": 0,
  "status": 0,
  "topsign": 0
}
```

### 10.2 文件ID编码规则
- **文件夹**: ID = `{file.id}`（纯数字）
- **文件**: ID = `{file.id}${file.content.fileId}`（数字$字符串）
- 判断是否为文件夹: `len(file.Content.FolderName) > 0`

---

## 十一、小组云盘 vs 个人云盘 完整对比

| 维度 | 个人云盘 | 小组云盘（单位云盘） |
|---|---|---|
| **API域名** | pan-yz.chaoxing.com | groupweb.chaoxing.com + noteyd.chaoxing.com |
| **核心标识** | puid（用户ID） | bbsid（小组ID） |
| **认证方式** | _token参数 | Cookie + Referer |
| **文件列表** | /api/getMyDirAndFiles | /pc/resource/getResourceList |
| **文件下载** | /api/download 或直链 | /screen/note_note/files/status/{fileId} |
| **文件上传** | FTP + /opt/createfilenew + /api/notification/rsyncsucss | /pc/files/getUploadConfig + /upload + /pc/resource/addResource |
| **创建文件夹** | /opt/createDir | /pc/resource/addResourceFolder |
| **删除文件** | /api/delete | /pc/resource/deleteResourceFile |
| **删除文件夹** | /api/delete | /pc/resource/deleteResourceFolder |
| **移动文件** | 无公开接口 | /pc/resource/moveResource |
| **重命名** | 无公开接口 | /pc/resource/updateResourceFolderName（仅文件夹） |
| **容量限制** | 100GB（默认） | 无总容量限制 |
| **单文件限制** | 2GB（网页端），无限制（FTP） | 2GB |
| **秒传支持** | 支持（CRC校验） | 不支持 |
| **FTP上传** | 支持 | 不支持（使用HTTP multipart） |
| **需要代理** | 否 | 是 |
| **权限体系** | 无（个人空间） | 完整权限体系（UserAuth） |
| **手机端兼容** | 原生支持 | 手机端文件JSON格式不同 |
| **文件ID格式** | resid（纯数字） | {recordId}${fileId} |
| **cataid** | 无 | 100000019（固定值） |
| **共享** | 个人独享 | 小组内共享 |

---

## 十二、关键发现与补充说明

### 12.1 超星云盘实际有三套体系
1. **个人云盘**（pan-yz.chaoxing.com）- 个人文件存储，100GB空间
2. **小组云盘**（groupweb.chaoxing.com + noteyd.chaoxing.com）- 小组共享存储，无容量限制
3. **课程资料盘**（通过学校SSO入口）- 教学资料存储，教职工100GB

### 12.2 小组云盘的特殊性
- 小组云盘是AList中唯一标记为`OnlyProxy: true`的超星驱动，说明其API可能存在地域限制或IP限制
- 上传流程为：获取上传配置 → 上传文件到pan-yz → 将文件关联到小组资源（三步走）
- 文件实际存储在pan-yz.chaoxing.com，但元数据管理在groupweb.chaoxing.com

### 12.3 手机端差异
- 手机端上传的文件`puid`和`size`字段为字符串类型，网页端为数字类型
- 手机端上传的文件缺少`fileId`字段，需用`objectId`替代
- 这些差异在解析API响应时需要特别处理
