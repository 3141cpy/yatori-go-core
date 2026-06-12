# Xiucat API 全面分析报告

> 分析目标: https://beta-a.xiucat.top/docs-json
> 分析时间: 2026-06-12
> 原始规范已保存至: `/workspace/xiucat_openapi_spec.json`

## 1. API 基本信息

- **标题**: VIP Center API
- **版本**: 0.1.0
- **描述**: VIP service center API

## 2. 安全方案 (Security Schemes)

### bearer
- **类型**: http
- **方案**: bearer
- **Bearer 格式**: JWT

## 3. 端点统计

| 类别 | 数量 |
|------|------|
| 总端点数 | 107 |
| 签到相关端点 | 34 |
| 认证相关端点 | 9 |
| 超星交互端点 | 11 |
| 任务/异步端点 | 6 |
| WebSocket/SSE端点 | 0 |

## 4. 完整端点列表（按标签分组）

### admin-shop-recharge

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/shop-recharge/orders` | List shop recharge orders for administrators | AdminShopRechargeController_listOrders |
| POST | `/api/admin/shop-recharge/orders/{id}/refund` | Record external refund and claw back points | AdminShopRechargeController_refundOrder |

### agent-shop-recharge

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/agent/shop-recharge/packages` | List shop recharge packages for agents | AgentShopRechargeController_listPackages |
| POST | `/api/agent/shop-recharge/orders` | Create an agent shop recharge order and checkout redirect | AgentShopRechargeController_createOrder |
| GET | `/api/agent/shop-recharge/orders/{orderNo}` | Get an agent shop recharge order status | AgentShopRechargeController_getOrder |
| POST | `/api/agent/shop-recharge/orders/{orderNo}/cancel` | Cancel a pending agent shop recharge order | AgentShopRechargeController_cancelOrder |

### announcements

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/announcements` |  | AnnouncementController_listAdmin |
| POST | `/api/admin/announcements` |  | AnnouncementController_create |
| PATCH | `/api/admin/announcements/{id}` |  | AnnouncementController_update |
| POST | `/api/admin/announcements/{id}/publish` |  | AnnouncementController_publish |
| POST | `/api/admin/announcements/{id}/archive` |  | AnnouncementController_archive |
| GET | `/api/announcements/active` |  | AnnouncementController_listActive |
| POST | `/api/announcements/{id}/acknowledge` |  | AnnouncementController_acknowledge |

### applications

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/applications` |  | ApplicationController_list |
| POST | `/api/admin/applications/agent/{id}/approve` |  | ApplicationController_approveAgent |
| POST | `/api/admin/applications/agent/{id}/reject` |  | ApplicationController_rejectAgent |
| POST | `/api/admin/applications/student/{id}/approve` |  | ApplicationController_approveStudent |
| POST | `/api/admin/applications/student/{id}/reject` |  | ApplicationController_rejectStudent |

### audit-logs

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/audit-logs` |  | AuditController_list |

### auth

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| POST | `/api/auth/login` |  | AuthController_login |
| POST | `/api/auth/xiucat-quick-login` |  | AuthController_xiucatQuickLogin |
| POST | `/api/auth/refresh` |  | AuthController_refresh |
| POST | `/api/auth/logout` |  | AuthController_logout |
| POST | `/api/auth/change-password` |  | AuthController_changePassword |

### cards

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/cards/batches` |  | CardController_listBatches |
| POST | `/api/admin/cards/batches` |  | CardController_createBatch |
| GET | `/api/admin/cards` |  | CardController_listCards |
| POST | `/api/admin/cards/{code}/revoke` |  | CardController_revokeCard |
| POST | `/api/admin/cards/batches/{id}/revoke` |  | CardController_revokeBatch |
| PATCH | `/api/admin/cards/batches/{id}/expires` |  | CardController_updateBatchExpiry |
| POST | `/api/card/redeem` |  | CardController_redeem |

### chaoxing-accounts

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/chaoxing/accounts` | List visible Chaoxing accounts | ChaoxingAccountController_list |
| POST | `/api/chaoxing/accounts` | Bind one Chaoxing account and validate login | ChaoxingAccountController_bind |
| POST | `/api/chaoxing/accounts/bulk` | Bulk import Chaoxing accounts from CSV | ChaoxingAccountController_bulkImport |
| GET | `/api/chaoxing/accounts/bulk/{id}` | Get one Chaoxing account import batch | ChaoxingAccountController_getImportBatch |
| GET | `/api/chaoxing/accounts/system-teacher` | Get configured patch-sign system teacher account | ChaoxingAccountController_getSystemTeacher |
| PUT | `/api/chaoxing/accounts/system-teacher` | Configure patch-sign system teacher account | ChaoxingAccountController_configureSystemTeacher |
| DELETE | `/api/chaoxing/accounts/{id}` | Delete one visible Chaoxing account | ChaoxingAccountController_delete |

### chaoxing-courses

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/chaoxing/courses` | List Chaoxing courses for an account | CourseController_listCourses |
| GET | `/api/chaoxing/courses/{courseId}/classes/{classId}/actives` | List Chaoxing sign activities for a class | CourseController_listActives |
| GET | `/api/chaoxing/actives/{activeId}` | Get Chaoxing sign activity details | CourseController_getActivityInfo |
| GET | `/api/chaoxing/actives/{activeId}/members` | Get Chaoxing sign activity member statuses | CourseController_getMembers |

### discount-package-rules

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/discount-package-rules` | List discount package rules as admin | AdminDiscountPackageController_list |
| POST | `/api/admin/discount-package-rules` | Create a discount package rule | AdminDiscountPackageController_create |
| PATCH | `/api/admin/discount-package-rules/{id}` | Update a discount package rule | AdminDiscountPackageController_update |

### feishu-review

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| POST | `/api/feishu/review/events` |  | FeishuReviewController_handleEvent |

### health

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/health` |  | HealthController_health |

### invite-codes

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/invite-codes` |  | InviteController_list |
| POST | `/api/invite-codes` |  | InviteController_create |
| POST | `/api/invite-codes/{id}/disable` |  | InviteController_disable |

### ledger

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/ledger/accounts` |  | LedgerController_accounts |
| GET | `/api/admin/ledger/accounts/{ownerId}` |  | LedgerController_adminAccounts |
| GET | `/api/ledger/history` |  | LedgerController_history |
| GET | `/api/admin/ledger/history` |  | LedgerController_adminHistory |
| GET | `/api/agent/ledger` |  | LedgerController_agentHistory |
| POST | `/api/ledger/coin-to-point` |  | LedgerController_coinToPoint |

### notifications

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/notifications` |  | NotificationController_list |
| GET | `/api/notifications/summary` |  | NotificationController_summary |
| POST | `/api/notifications/{id}/read` |  | NotificationController_markRead |
| POST | `/api/notifications/read-all` |  | NotificationController_markAllRead |

### patch-sign-tasks

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/patch-sign/tasks` | List visible patch-sign tasks | PatchSignController_list |
| POST | `/api/patch-sign/tasks` | Create one patch-sign task | PatchSignController_create |
| POST | `/api/patch-sign/tasks/bulk` | Create patch-sign tasks in bulk | PatchSignController_createBulk |
| GET | `/api/patch-sign/tasks/{id}` | Get one visible patch-sign task | PatchSignController_get |
| DELETE | `/api/patch-sign/tasks/{id}` | Cancel a queued patch-sign task | PatchSignController_cancel |
| POST | `/api/admin/patch-sign/tasks/{id}/force-cancel` | Force-cancel a patch-sign task as admin | PatchSignController_forceCancel |

### profile

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/me` |  | ProfileController_me |
| GET | `/api/student/overview` |  | ProfileController_studentOverview |
| GET | `/api/agent/overview` |  | ProfileController_agentOverview |
| GET | `/api/admin/overview` |  | ProfileController_adminOverview |

### registration

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| POST | `/api/register/agent` |  | RegistrationController_registerAgent |
| POST | `/api/register/student` |  | RegistrationController_registerStudent |

### service-config

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/service-config` | List service configuration values | ServiceConfigController_list |
| PATCH | `/api/admin/service-config/{key}` | Update one service configuration value | ServiceConfigController_update |
| GET | `/api/service-config` | List public service configuration values | PublicServiceConfigController_list |

### shop-recharge-callback

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| POST | `/api/shop-recharge/callback` | Receive signed xiucat-shop recharge callback | ShopRechargeCallbackController_callback |

### student-discount-package

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/student/discount-package/rules` | List active discount package rules for students | StudentDiscountPackageController_listRules |
| GET | `/api/student/discount-package/current` | Get current active discount package purchase | StudentDiscountPackageController_current |
| POST | `/api/student/discount-package/purchases` | Purchase a discount package | StudentDiscountPackageController_purchase |
| POST | `/api/student/discount-package/shop-orders` | Create a discount package shop checkout order | StudentDiscountPackageController_createShopOrder |
| GET | `/api/student/discount-package/shop-orders/{orderNo}` | Get a discount package shop order status | StudentDiscountPackageController_getShopOrder |
| POST | `/api/student/discount-package/shop-orders/{orderNo}/cancel` | Cancel a pending discount package shop order | StudentDiscountPackageController_cancelShopOrder |

### student-shop-recharge

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/student/shop-recharge/packages` | List shop recharge packages for students | StudentShopRechargeController_listPackages |
| POST | `/api/student/shop-recharge/orders` | Create a shop recharge order and checkout redirect | StudentShopRechargeController_createOrder |
| GET | `/api/student/shop-recharge/orders/{orderNo}` | Get a shop recharge order status | StudentShopRechargeController_getOrder |
| POST | `/api/student/shop-recharge/orders/{orderNo}/cancel` | Cancel a pending shop recharge order | StudentShopRechargeController_cancelOrder |

### users

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/admin/users` |  | UserController_list |
| GET | `/api/admin/users/{id}` |  | UserController_detail |
| PATCH | `/api/admin/users/{id}/disable` |  | UserController_disable |
| PATCH | `/api/admin/users/{id}/restore` |  | UserController_restore |
| PATCH | `/api/admin/users/{id}/reassign` |  | UserController_reassign |
| PATCH | `/api/admin/users/{id}/promote-agent` |  | UserController_promoteAgent |
| PATCH | `/api/admin/users/{id}/commission` |  | UserController_updateCommission |
| POST | `/api/admin/agents/{id}/cleanup-students` |  | UserController_cleanupStudents |
| POST | `/api/admin/users/{id}/grant-points` |  | UserController_grantPoints |
| POST | `/api/admin/users/{id}/reset-password` |  | UserController_resetPassword |
| GET | `/api/agent/students` |  | UserController_agentStudents |
| GET | `/api/agent/students/{id}` |  | UserController_agentStudentDetail |
| PATCH | `/api/agent/students/{id}/disable` |  | UserController_disableAgentStudent |
| PATCH | `/api/agent/students/{id}/restore` |  | UserController_restoreAgentStudent |

### withdraw

| 方法 | 路径 | 摘要 | 操作ID |
|------|------|------|--------|
| GET | `/api/agent/withdraw` |  | WithdrawController_listMine |
| POST | `/api/agent/withdraw` |  | WithdrawController_create |
| POST | `/api/agent/withdraw/{id}/resubmit` |  | WithdrawController_resubmit |
| GET | `/api/admin/withdraw` |  | WithdrawController_listAll |
| POST | `/api/admin/withdraw/{id}/approve` |  | WithdrawController_approve |
| POST | `/api/admin/withdraw/{id}/mark-paid` |  | WithdrawController_markPaid |
| POST | `/api/admin/withdraw/{id}/reject` |  | WithdrawController_reject |

## 5. 签到相关端点详细分析

### POST `/api/auth/login`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_login
- **标签**: auth

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `loginName` *(必填)*: string 
  - `password` *(必填)*: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "loginName": {
      "type": "string"
    },
    "password": {
      "type": "string"
    }
  },
  "required": [
    "loginName",
    "password"
  ]
}
```
</details>

#### 响应

**状态码 200**: JWT access and refresh tokens
---

### POST `/api/auth/xiucat-quick-login`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_xiucatQuickLogin
- **标签**: auth

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `account` *(必填)*: string 修猫账号 / 学习通手机号
  - `password` *(必填)*: string 密码
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "description": "修猫账号 / 学习通手机号"
    },
    "password": {
      "type": "string",
      "description": "密码"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```
</details>

#### 响应

**状态码 200**: JWT access and refresh tokens for Xiucat quick login
---

### POST `/api/auth/refresh`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_refresh
- **标签**: auth

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `authorization` | header | 是 | {"type": "string"} |  |

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `refreshToken`: string Optional refresh token. Authorization bearer is preferred.
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "refreshToken": {
      "type": "string",
      "description": "Optional refresh token. Authorization bearer is preferred."
    }
  }
}
```
</details>

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/auth/logout`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_logout
- **标签**: auth

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `authorization` | header | 是 | {"type": "string"} |  |

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `all`: boolean 
  - `refreshToken`: string Optional refresh token. Authorization bearer is preferred.
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "all": {
      "type": "boolean"
    },
    "refreshToken": {
      "type": "string",
      "description": "Optional refresh token. Authorization bearer is preferred."
    }
  }
}
```
</details>

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/auth/change-password`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_changePassword
- **标签**: auth

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `currentPassword` *(必填)*: string 
  - `newPassword` *(必填)*: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "currentPassword": {
      "type": "string"
    },
    "newPassword": {
      "type": "string"
    }
  },
  "required": [
    "currentPassword",
    "newPassword"
  ]
}
```
</details>

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/announcements/active`
- **摘要**: 
- **描述**: 
- **操作ID**: AnnouncementController_listActive
- **标签**: announcements

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `displayMode` | query | 否 | {"enum": ["MODAL", "SILENT"], "type": "string"} |  |

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/admin/ledger/history`
- **摘要**: 
- **描述**: 
- **操作ID**: LedgerController_adminHistory
- **标签**: ledger

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `cursor` | query | 否 | {"type": "string"} |  |
| `limit` | query | 否 | {"minimum": 1, "maximum": 100, "type": "number"} |  |
| `page` | query | 否 | {"minimum": 1, "default": 1, "type": "number"} |  |
| `ownerId` | query | 否 | {"type": "string"} | Restrict results to a user id. |
| `reason` | query | 否 | {"enum": ["ADMIN_GRANT", "CARD_REDEEM", "SHOP_RECHARGE", "SHOP_RECHARGE_REFUND", "DISCOUNT_PACKAGE_P |  |
| `refId` | query | 否 | {"type": "string"} |  |
| `refType` | query | 否 | {"type": "string"} |  |
| `type` | query | 否 | {"enum": ["POINT", "COIN"], "type": "string"} |  |
| `ownerKeyword` | query | 否 | {"type": "string"} | Admin search keyword for user id, login name, nickname, or phone. |

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/admin/cards/batches`
- **摘要**: 
- **描述**: 
- **操作ID**: CardController_listBatches
- **标签**: cards

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `limit` | query | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/admin/cards/batches`
- **摘要**: 
- **描述**: 
- **操作ID**: CardController_createBatch
- **标签**: cards

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `faceValue` *(必填)*: number 
  - `count` *(必填)*: number 
  - `expiresAt` *(必填)*: string 
  - `note` *(必填)*: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "faceValue": {
      "type": "number",
      "minimum": 1
    },
    "count": {
      "type": "number",
      "maximum": 10000,
      "minimum": 1
    },
    "expiresAt": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  },
  "required": [
    "faceValue",
    "count"
  ]
}
```
</details>

#### 响应

**状态码 201**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/admin/cards`
- **摘要**: 
- **描述**: 
- **操作ID**: CardController_listCards
- **标签**: cards

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `batchId` | query | 否 | {"type": "string"} |  |
| `code` | query | 否 | {"type": "string"} |  |
| `status` | query | 否 | {"enum": ["UNUSED", "USED", "REVOKED", "EXPIRED"], "type": "string"} |  |
| `limit` | query | 否 | {"minimum": 1, "maximum": 100, "default": 20, "type": "number"} |  |

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/admin/cards/batches/{id}/revoke`
- **摘要**: 
- **描述**: 
- **操作ID**: CardController_revokeBatch
- **标签**: cards

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 201**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### PATCH `/api/admin/cards/batches/{id}/expires`
- **摘要**: 
- **描述**: 
- **操作ID**: CardController_updateBatchExpiry
- **标签**: cards

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `expiresAt`: object 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "expiresAt": {
      "type": "object",
      "nullable": true
    }
  }
}
```
</details>

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### PATCH `/api/admin/users/{id}/reassign`
- **摘要**: 
- **描述**: 
- **操作ID**: UserController_reassign
- **标签**: users

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `agentId`: object 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "agentId": {
      "type": "object",
      "nullable": true
    }
  }
}
```
</details>

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/admin/users/{id}/reset-password`
- **摘要**: 
- **描述**: 
- **操作ID**: UserController_resetPassword
- **标签**: users

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: 
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/student/discount-package/rules`
- **摘要**: List active discount package rules for students
- **描述**: 
- **操作ID**: StudentDiscountPackageController_listRules
- **标签**: student-discount-package

#### 响应

**状态码 200**: Discount package rules returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/student/discount-package/current`
- **摘要**: Get current active discount package purchase
- **描述**: 
- **操作ID**: StudentDiscountPackageController_current
- **标签**: student-discount-package

#### 响应

**状态码 200**: Current discount package returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/accounts`
- **摘要**: List visible Chaoxing accounts
- **描述**: 
- **操作ID**: ChaoxingAccountController_list
- **标签**: chaoxing-accounts

#### 响应

**状态码 200**: Visible Chaoxing accounts returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/chaoxing/accounts`
- **摘要**: Bind one Chaoxing account and validate login
- **描述**: 
- **操作ID**: ChaoxingAccountController_bind
- **标签**: chaoxing-accounts

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `account` *(必填)*: string 
  - `password` *(必填)*: string 
  - `note` *(必填)*: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "example": "13800138000"
    },
    "password": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```
</details>

#### 响应

**状态码 201**: Chaoxing account bound.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/chaoxing/accounts/bulk`
- **摘要**: Bulk import Chaoxing accounts from CSV
- **描述**: 
- **操作ID**: ChaoxingAccountController_bulkImport
- **标签**: chaoxing-accounts

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `multipart/form-data`

```
**object**:
  - `file` *(必填)*: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "properties": {
    "file": {
      "format": "binary",
      "type": "string"
    }
  },
  "required": [
    "file"
  ],
  "type": "object"
}
```
</details>

#### 响应

**状态码 201**: Import batch created.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/accounts/bulk/{id}`
- **摘要**: Get one Chaoxing account import batch
- **描述**: 
- **操作ID**: ChaoxingAccountController_getImportBatch
- **标签**: chaoxing-accounts

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Import batch returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/accounts/system-teacher`
- **摘要**: Get configured patch-sign system teacher account
- **描述**: 
- **操作ID**: ChaoxingAccountController_getSystemTeacher
- **标签**: chaoxing-accounts

#### 响应

**状态码 200**: System teacher account returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### PUT `/api/chaoxing/accounts/system-teacher`
- **摘要**: Configure patch-sign system teacher account
- **描述**: 
- **操作ID**: ChaoxingAccountController_configureSystemTeacher
- **标签**: chaoxing-accounts

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `account` *(必填)*: string 
  - `password` *(必填)*: string 
  - `note` *(必填)*: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "example": "13800138000"
    },
    "password": {
      "type": "string"
    },
    "note": {
      "type": "string",
      "example": "补签系统教师账号"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```
</details>

#### 响应

**状态码 200**: System teacher account configured.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### DELETE `/api/chaoxing/accounts/{id}`
- **摘要**: Delete one visible Chaoxing account
- **描述**: 
- **操作ID**: ChaoxingAccountController_delete
- **标签**: chaoxing-accounts

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Chaoxing account deleted.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/courses`
- **摘要**: List Chaoxing courses for an account
- **描述**: 
- **操作ID**: CourseController_listCourses
- **标签**: chaoxing-courses

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `accountId` | query | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Course list returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/courses/{courseId}/classes/{classId}/actives`
- **摘要**: List Chaoxing sign activities for a class
- **描述**: 
- **操作ID**: CourseController_listActives
- **标签**: chaoxing-courses

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `courseId` | path | 是 | {"type": "string"} |  |
| `classId` | path | 是 | {"type": "string"} |  |
| `accountId` | query | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Activity list returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/actives/{activeId}`
- **摘要**: Get Chaoxing sign activity details
- **描述**: 
- **操作ID**: CourseController_getActivityInfo
- **标签**: chaoxing-courses

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `activeId` | path | 是 | {"type": "string"} |  |
| `accountId` | query | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Activity details returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/chaoxing/actives/{activeId}/members`
- **摘要**: Get Chaoxing sign activity member statuses
- **描述**: 
- **操作ID**: CourseController_getMembers
- **标签**: chaoxing-courses

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `activeId` | path | 是 | {"type": "string"} |  |
| `accountId` | query | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Member status summary returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/patch-sign/tasks`
- **摘要**: List visible patch-sign tasks
- **描述**: 
- **操作ID**: PatchSignController_list
- **标签**: patch-sign-tasks

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `accountId` | query | 否 | {"type": "string"} |  |
| `courseId` | query | 否 | {"type": "string"} |  |
| `activeId` | query | 否 | {"type": "string"} |  |
| `createdFrom` | query | 否 | {"type": "string"} |  |
| `createdTo` | query | 否 | {"type": "string"} |  |
| `status` | query | 否 | {"enum": ["CREATED", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "SKIPPED", "CANCELED"], "type": "stri |  |
| `limit` | query | 否 | {"minimum": 1, "maximum": 100, "default": 20, "type": "number"} |  |
| `page` | query | 否 | {"minimum": 1, "default": 1, "type": "number"} |  |

#### 响应

**状态码 200**: Patch-sign task list returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/patch-sign/tasks`
- **摘要**: Create one patch-sign task
- **描述**: 
- **操作ID**: PatchSignController_create
- **标签**: patch-sign-tasks

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `accountId` *(必填)*: string 
  - `courseId` *(必填)*: string 
  - `classId` *(必填)*: string 
  - `activeId` *(必填)*: string 
  - `targetStatus` *(必填)*: number enum=[1, 2, 5, 7, 8, 9, 10, 11, 12] 
  - `acknowledgeSmallClass` *(必填)*: boolean default=False 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "accountId": {
      "type": "string"
    },
    "courseId": {
      "type": "string"
    },
    "classId": {
      "type": "string"
    },
    "activeId": {
      "type": "string"
    },
    "targetStatus": {
      "type": "number",
      "enum": [
        1,
        2,
        5,
        7,
        8,
        9,
        10,
        11,
        12
      ]
    },
    "acknowledgeSmallClass": {
      "type": "boolean",
      "default": false
    }
  },
  "required": [
    "accountId",
    "courseId",
    "classId",
    "activeId",
    "targetStatus",
    "acknowledgeSmallClass"
  ]
}
```
</details>

#### 响应

**状态码 201**: Patch-sign task created.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/patch-sign/tasks/bulk`
- **摘要**: Create patch-sign tasks in bulk
- **描述**: 
- **操作ID**: PatchSignController_createBulk
- **标签**: patch-sign-tasks

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `items` *(必填)*: array[object] 
    **object**:
      - `accountId` *(必填)*: string 
      - `courseId` *(必填)*: string 
      - `classId` *(必填)*: string 
      - `activeId` *(必填)*: string 
      - `targetStatus` *(必填)*: number enum=[1, 2, 5, 7, 8, 9, 10, 11, 12] 
      - `acknowledgeSmallClass` *(必填)*: boolean default=False 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "accountId": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "classId": {
            "type": "string"
          },
          "activeId": {
            "type": "string"
          },
          "targetStatus": {
            "type": "number",
            "enum": [
              1,
              2,
              5,
              7,
              8,
              9,
              10,
              11,
              12
            ]
          },
          "acknowledgeSmallClass": {
            "type": "boolean",
            "default": false
          }
        },
        "required": [
          "accountId",
          "courseId",
          "classId",
          "activeId",
          "targetStatus",
          "acknowledgeSmallClass"
        ]
      }
    }
  },
  "required": [
    "items"
  ]
}
```
</details>

#### 响应

**状态码 201**: Bulk creation results returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### GET `/api/patch-sign/tasks/{id}`
- **摘要**: Get one visible patch-sign task
- **描述**: 
- **操作ID**: PatchSignController_get
- **标签**: patch-sign-tasks

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Patch-sign task returned.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### DELETE `/api/patch-sign/tasks/{id}`
- **摘要**: Cancel a queued patch-sign task
- **描述**: 
- **操作ID**: PatchSignController_cancel
- **标签**: patch-sign-tasks

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Patch-sign task canceled.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/admin/patch-sign/tasks/{id}/force-cancel`
- **摘要**: Force-cancel a patch-sign task as admin
- **描述**: 
- **操作ID**: PatchSignController_forceCancel
- **标签**: patch-sign-tasks

#### 参数

| 名称 | 位置 | 必填 | 类型 | 描述 |
|------|------|------|------|------|
| `id` | path | 是 | {"type": "string"} |  |

#### 响应

**状态码 200**: Patch-sign task force-canceled.
#### 安全要求

```json
[
  {
    "bearer": []
  }
]
```

---

### POST `/api/shop-recharge/callback`
- **摘要**: Receive signed xiucat-shop recharge callback
- **描述**: 
- **操作ID**: ShopRechargeCallbackController_callback
- **标签**: shop-recharge-callback

#### 请求体

- **描述**: 
- **必填**: 是
- **Content-Type**: `application/json`

```
**object**:
  - `event` *(必填)*: string 
  - `order_id` *(必填)*: number 
  - `order_no` *(必填)*: string 
  - `downstream_order_no` *(必填)*: string 
  - `status` *(必填)*: string 
  - `timestamp` *(必填)*: number 
  - `amount` *(必填)*: string 
  - `currency` *(必填)*: string 
  - `fulfillment` *(必填)*: object
    **object**:
      - `amount`: string 
      - `currency`: string 
```

<details><summary>原始 Schema JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "event": {
      "type": "string"
    },
    "order_id": {
      "type": "number"
    },
    "order_no": {
      "type": "string"
    },
    "downstream_order_no": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "timestamp": {
      "type": "number"
    },
    "amount": {
      "type": "string"
    },
    "currency": {
      "type": "string"
    },
    "fulfillment": {
      "type": "object",
      "properties": {
        "amount": {
          "type": "string"
        },
        "currency": {
          "type": "string"
        }
      }
    }
  },
  "required": [
    "event",
    "order_id",
    "order_no",
    "downstream_order_no",
    "status",
    "timestamp"
  ]
}
```
</details>

#### 响应

**状态码 200**: Callback accepted.
---

## 6. 认证流程分析

### POST `/api/auth/login`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_login
- **标签**: auth
- **请求体**:
  - `application/json`:
```
**object**:
  - `loginName` *(必填)*: string 
  - `password` *(必填)*: string 
```
- **响应**:
  - 200: JWT access and refresh tokens

### POST `/api/auth/xiucat-quick-login`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_xiucatQuickLogin
- **标签**: auth
- **请求体**:
  - `application/json`:
```
**object**:
  - `account` *(必填)*: string 修猫账号 / 学习通手机号
  - `password` *(必填)*: string 密码
```
- **响应**:
  - 200: JWT access and refresh tokens for Xiucat quick login

### POST `/api/auth/refresh`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_refresh
- **标签**: auth
- **参数**:
  - `authorization` (header): 
- **请求体**:
  - `application/json`:
```
**object**:
  - `refreshToken`: string Optional refresh token. Authorization bearer is preferred.
```
- **响应**:
  - 200: 

### POST `/api/auth/logout`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_logout
- **标签**: auth
- **参数**:
  - `authorization` (header): 
- **请求体**:
  - `application/json`:
```
**object**:
  - `all`: boolean 
  - `refreshToken`: string Optional refresh token. Authorization bearer is preferred.
```
- **响应**:
  - 200: 

### POST `/api/auth/change-password`
- **摘要**: 
- **描述**: 
- **操作ID**: AuthController_changePassword
- **标签**: auth
- **请求体**:
  - `application/json`:
```
**object**:
  - `currentPassword` *(必填)*: string 
  - `newPassword` *(必填)*: string 
```
- **响应**:
  - 200: 

### POST `/api/register/agent`
- **摘要**: 
- **描述**: 
- **操作ID**: RegistrationController_registerAgent
- **标签**: registration
- **请求体**:
  - `application/json`:
```
**object**:
  - `loginName` *(必填)*: string 登录名需为至少 6 位数字、字母或下划线
  - `password` *(必填)*: string 
  - `nickname` *(必填)*: string 
  - `email` *(必填)*: string 
  - `phone` *(必填)*: string 
  - `inviteCode` *(必填)*: string 
  - `reason` *(必填)*: string 
  - `contactNote` *(必填)*: string 
```
- **响应**:
  - 201: 

### POST `/api/register/student`
- **摘要**: 
- **描述**: 
- **操作ID**: RegistrationController_registerStudent
- **标签**: registration
- **请求体**:
  - `application/json`:
```
**object**:
  - `loginName` *(必填)*: string 登录名需为至少 6 位数字、字母或下划线
  - `password` *(必填)*: string 
  - `nickname` *(必填)*: string 
  - `email` *(必填)*: string 
  - `phone` *(必填)*: string 
  - `inviteCode` *(必填)*: string 
  - `reason` *(必填)*: string 
  - `contactNote` *(必填)*: string 
```
- **响应**:
  - 201: 

### POST `/api/chaoxing/accounts`
- **摘要**: Bind one Chaoxing account and validate login
- **描述**: 
- **操作ID**: ChaoxingAccountController_bind
- **标签**: chaoxing-accounts
- **请求体**:
  - `application/json`:
```
**object**:
  - `account` *(必填)*: string 
  - `password` *(必填)*: string 
  - `note` *(必填)*: string 
```
- **响应**:
  - 201: Chaoxing account bound.

### POST `/api/shop-recharge/callback`
- **摘要**: Receive signed xiucat-shop recharge callback
- **描述**: 
- **操作ID**: ShopRechargeCallbackController_callback
- **标签**: shop-recharge-callback
- **请求体**:
  - `application/json`:
```
**object**:
  - `event` *(必填)*: string 
  - `order_id` *(必填)*: number 
  - `order_no` *(必填)*: string 
  - `downstream_order_no` *(必填)*: string 
  - `status` *(必填)*: string 
  - `timestamp` *(必填)*: number 
  - `amount` *(必填)*: string 
  - `currency` *(必填)*: string 
  - `fulfillment` *(必填)*: object
    **object**:
      - `amount`: string 
      - `currency`: string 
```
- **响应**:
  - 200: Callback accepted.

## 7. 超星(ChaoXing)交互端点分析

### GET `/api/chaoxing/accounts`
- **摘要**: List visible Chaoxing accounts
- **描述**: 
- **操作ID**: ChaoxingAccountController_list

### POST `/api/chaoxing/accounts`
- **摘要**: Bind one Chaoxing account and validate login
- **描述**: 
- **操作ID**: ChaoxingAccountController_bind
- **请求体**:
  - `application/json`:
```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "example": "13800138000"
    },
    "password": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```

### POST `/api/chaoxing/accounts/bulk`
- **摘要**: Bulk import Chaoxing accounts from CSV
- **描述**: 
- **操作ID**: ChaoxingAccountController_bulkImport
- **请求体**:
  - `multipart/form-data`:
```json
{
  "properties": {
    "file": {
      "format": "binary",
      "type": "string"
    }
  },
  "required": [
    "file"
  ],
  "type": "object"
}
```

### GET `/api/chaoxing/accounts/bulk/{id}`
- **摘要**: Get one Chaoxing account import batch
- **描述**: 
- **操作ID**: ChaoxingAccountController_getImportBatch

### GET `/api/chaoxing/accounts/system-teacher`
- **摘要**: Get configured patch-sign system teacher account
- **描述**: 
- **操作ID**: ChaoxingAccountController_getSystemTeacher

### PUT `/api/chaoxing/accounts/system-teacher`
- **摘要**: Configure patch-sign system teacher account
- **描述**: 
- **操作ID**: ChaoxingAccountController_configureSystemTeacher
- **请求体**:
  - `application/json`:
```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "example": "13800138000"
    },
    "password": {
      "type": "string"
    },
    "note": {
      "type": "string",
      "example": "补签系统教师账号"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```

### DELETE `/api/chaoxing/accounts/{id}`
- **摘要**: Delete one visible Chaoxing account
- **描述**: 
- **操作ID**: ChaoxingAccountController_delete

### GET `/api/chaoxing/courses`
- **摘要**: List Chaoxing courses for an account
- **描述**: 
- **操作ID**: CourseController_listCourses

### GET `/api/chaoxing/courses/{courseId}/classes/{classId}/actives`
- **摘要**: List Chaoxing sign activities for a class
- **描述**: 
- **操作ID**: CourseController_listActives

### GET `/api/chaoxing/actives/{activeId}`
- **摘要**: Get Chaoxing sign activity details
- **描述**: 
- **操作ID**: CourseController_getActivityInfo

### GET `/api/chaoxing/actives/{activeId}/members`
- **摘要**: Get Chaoxing sign activity member statuses
- **描述**: 
- **操作ID**: CourseController_getMembers

## 8. 任务/异步端点分析

### GET `/api/patch-sign/tasks`
- **摘要**: List visible patch-sign tasks
- **描述**: 
- **操作ID**: PatchSignController_list
- **参数**:
  - `accountId` (query): 
  - `courseId` (query): 
  - `activeId` (query): 
  - `createdFrom` (query): 
  - `createdTo` (query): 
  - `status` (query): 
  - `limit` (query): 
  - `page` (query): 
- **响应**:
  - 200: Patch-sign task list returned.

### POST `/api/patch-sign/tasks`
- **摘要**: Create one patch-sign task
- **描述**: 
- **操作ID**: PatchSignController_create
- **请求体**:
  - `application/json`:
```json
{
  "type": "object",
  "properties": {
    "accountId": {
      "type": "string"
    },
    "courseId": {
      "type": "string"
    },
    "classId": {
      "type": "string"
    },
    "activeId": {
      "type": "string"
    },
    "targetStatus": {
      "type": "number",
      "enum": [
        1,
        2,
        5,
        7,
        8,
        9,
        10,
        11,
        12
      ]
    },
    "acknowledgeSmallClass": {
      "type": "boolean",
      "default": false
    }
  },
  "required": [
    "accountId",
    "courseId",
    "classId",
    "activeId",
    "targetStatus",
    "acknowledgeSmallClass"
  ]
}
```
- **响应**:
  - 201: Patch-sign task created.

### POST `/api/patch-sign/tasks/bulk`
- **摘要**: Create patch-sign tasks in bulk
- **描述**: 
- **操作ID**: PatchSignController_createBulk
- **请求体**:
  - `application/json`:
```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "accountId": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "classId": {
            "type": "string"
          },
          "activeId": {
            "type": "string"
          },
          "targetStatus": {
            "type": "number",
            "enum": [
              1,
              2,
              5,
              7,
              8,
              9,
              10,
              11,
              12
            ]
          },
          "acknowledgeSmallClass": {
            "type": "boolean",
            "default": false
          }
        },
        "required": [
          "accountId",
          "courseId",
          "classId",
          "activeId",
          "targetStatus",
          "acknowledgeSmallClass"
        ]
      }
    }
  },
  "required": [
    "items"
  ]
}
```
- **响应**:
  - 201: Bulk creation results returned.

### GET `/api/patch-sign/tasks/{id}`
- **摘要**: Get one visible patch-sign task
- **描述**: 
- **操作ID**: PatchSignController_get
- **参数**:
  - `id` (path): 
- **响应**:
  - 200: Patch-sign task returned.

### DELETE `/api/patch-sign/tasks/{id}`
- **摘要**: Cancel a queued patch-sign task
- **描述**: 
- **操作ID**: PatchSignController_cancel
- **参数**:
  - `id` (path): 
- **响应**:
  - 200: Patch-sign task canceled.

### POST `/api/admin/patch-sign/tasks/{id}/force-cancel`
- **摘要**: Force-cancel a patch-sign task as admin
- **描述**: 
- **操作ID**: PatchSignController_forceCancel
- **参数**:
  - `id` (path): 
- **响应**:
  - 200: Patch-sign task force-canceled.

## 9. WebSocket/SSE 端点

未发现 WebSocket 或 SSE 端点。
## 10. 所有数据模型 (Schemas)

### BindChaoxingAccountDto

```
**object**:
  - `account` *(必填)*: string 
  - `password` *(必填)*: string 
  - `note` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "example": "13800138000"
    },
    "password": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```
</details>

### BulkPatchSignTaskItemDto

```
**object**:
  - `accountId` *(必填)*: string 
  - `courseId` *(必填)*: string 
  - `classId` *(必填)*: string 
  - `activeId` *(必填)*: string 
  - `targetStatus` *(必填)*: number enum=[1, 2, 5, 7, 8, 9, 10, 11, 12] 
  - `acknowledgeSmallClass` *(必填)*: boolean default=False 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "accountId": {
      "type": "string"
    },
    "courseId": {
      "type": "string"
    },
    "classId": {
      "type": "string"
    },
    "activeId": {
      "type": "string"
    },
    "targetStatus": {
      "type": "number",
      "enum": [
        1,
        2,
        5,
        7,
        8,
        9,
        10,
        11,
        12
      ]
    },
    "acknowledgeSmallClass": {
      "type": "boolean",
      "default": false
    }
  },
  "required": [
    "accountId",
    "courseId",
    "classId",
    "activeId",
    "targetStatus",
    "acknowledgeSmallClass"
  ]
}
```
</details>

### ChangePasswordDto

```
**object**:
  - `currentPassword` *(必填)*: string 
  - `newPassword` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "currentPassword": {
      "type": "string"
    },
    "newPassword": {
      "type": "string"
    }
  },
  "required": [
    "currentPassword",
    "newPassword"
  ]
}
```
</details>

### CleanupStudentsDto

```
**object**:
  - `action` *(必填)*: string enum=['null', 'transfer'] 
  - `transferToAgentId` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "null",
        "transfer"
      ]
    },
    "transferToAgentId": {
      "type": "string"
    }
  },
  "required": [
    "action"
  ]
}
```
</details>

### CoinToPointDto

```
**object**:
  - `amount` *(必填)*: number 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "amount": {
      "type": "number",
      "minimum": 1
    }
  },
  "required": [
    "amount"
  ]
}
```
</details>

### ConfigureSystemTeacherAccountDto

```
**object**:
  - `account` *(必填)*: string 
  - `password` *(必填)*: string 
  - `note` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "example": "13800138000"
    },
    "password": {
      "type": "string"
    },
    "note": {
      "type": "string",
      "example": "补签系统教师账号"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```
</details>

### CreateAnnouncementDto

```
**object**:
  - `body` *(必填)*: string 
  - `displayMode` *(必填)*: string enum=['MODAL', 'SILENT'] 
  - `level` *(必填)*: string enum=['INFO', 'WARN', 'ERROR'] 
  - `endsAt` *(必填)*: string 
  - `startsAt` *(必填)*: string 
  - `status` *(必填)*: string enum=['DRAFT', 'PUBLISHED', 'ARCHIVED'] 
  - `targetRole` *(必填)*: string enum=['AGENT', 'STUDENT'] 
  - `title` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "body": {
      "type": "string",
      "maxLength": 4000
    },
    "displayMode": {
      "type": "string",
      "enum": [
        "MODAL",
        "SILENT"
      ]
    },
    "level": {
      "type": "string",
      "enum": [
        "INFO",
        "WARN",
        "ERROR"
      ]
    },
    "endsAt": {
      "type": "string",
      "nullable": true
    },
    "startsAt": {
      "type": "string",
      "nullable": true
    },
    "status": {
      "type": "string",
      "enum": [
        "DRAFT",
        "PUBLISHED",
        "ARCHIVED"
      ]
    },
    "targetRole": {
      "type": "string",
      "enum": [
        "AGENT",
        "STUDENT"
      ]
    },
    "title": {
      "type": "string",
      "maxLength": 120
    }
  },
  "required": [
    "body",
    "displayMode",
    "targetRole",
    "title"
  ]
}
```
</details>

### CreateBulkPatchSignTaskDto

```
**object**:
  - `items` *(必填)*: array[object] 
    **object**:
      - `accountId` *(必填)*: string 
      - `courseId` *(必填)*: string 
      - `classId` *(必填)*: string 
      - `activeId` *(必填)*: string 
      - `targetStatus` *(必填)*: number enum=[1, 2, 5, 7, 8, 9, 10, 11, 12] 
      - `acknowledgeSmallClass` *(必填)*: boolean default=False 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "accountId": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "classId": {
            "type": "string"
          },
          "activeId": {
            "type": "string"
          },
          "targetStatus": {
            "type": "number",
            "enum": [
              1,
              2,
              5,
              7,
              8,
              9,
              10,
              11,
              12
            ]
          },
          "acknowledgeSmallClass": {
            "type": "boolean",
            "default": false
          }
        },
        "required": [
          "accountId",
          "courseId",
          "classId",
          "activeId",
          "targetStatus",
          "acknowledgeSmallClass"
        ]
      }
    }
  },
  "required": [
    "items"
  ]
}
```
</details>

### CreateCardBatchDto

```
**object**:
  - `faceValue` *(必填)*: number 
  - `count` *(必填)*: number 
  - `expiresAt` *(必填)*: string 
  - `note` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "faceValue": {
      "type": "number",
      "minimum": 1
    },
    "count": {
      "type": "number",
      "maximum": 10000,
      "minimum": 1
    },
    "expiresAt": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  },
  "required": [
    "faceValue",
    "count"
  ]
}
```
</details>

### CreateDiscountPackageRuleDto

```
**object**:
  - `name` *(必填)*: string 
  - `quantity` *(必填)*: number 
  - `unitPrice` *(必填)*: number 
  - `note` *(必填)*: string 
  - `sortOrder` *(必填)*: number default=0 
  - `shopSkuId` *(必填)*: number xiucat-shop SKU id for cash checkout
  - `cashAmount` *(必填)*: string Cash amount charged by xiucat-shop, e.g. 19.90
  - `currency` *(必填)*: string default=CNY 
  - `purchaseEnabled` *(必填)*: boolean default=True 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "example": "3次优惠包"
    },
    "quantity": {
      "type": "number",
      "minimum": 1
    },
    "unitPrice": {
      "type": "number",
      "minimum": 1
    },
    "note": {
      "type": "string"
    },
    "sortOrder": {
      "type": "number",
      "default": 0
    },
    "shopSkuId": {
      "type": "number",
      "description": "xiucat-shop SKU id for cash checkout"
    },
    "cashAmount": {
      "type": "string",
      "description": "Cash amount charged by xiucat-shop, e.g. 19.90"
    },
    "currency": {
      "type": "string",
      "default": "CNY"
    },
    "purchaseEnabled": {
      "type": "boolean",
      "default": true
    }
  },
  "required": [
    "name",
    "quantity",
    "unitPrice"
  ]
}
```
</details>

### CreateInviteCodeDto

```
**object**:
  - `issuerType`: string enum=['ADMIN', 'AGENT'] 
  - `maxUses`: number 
  - `expiresAt`: string 
  - `note`: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "issuerType": {
      "type": "string",
      "enum": [
        "ADMIN",
        "AGENT"
      ]
    },
    "maxUses": {
      "type": "number",
      "minimum": 1
    },
    "expiresAt": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  }
}
```
</details>

### CreatePatchSignTaskDto

```
**object**:
  - `accountId` *(必填)*: string 
  - `courseId` *(必填)*: string 
  - `classId` *(必填)*: string 
  - `activeId` *(必填)*: string 
  - `targetStatus` *(必填)*: number enum=[1, 2, 5, 7, 8, 9, 10, 11, 12] 
  - `acknowledgeSmallClass` *(必填)*: boolean default=False 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "accountId": {
      "type": "string"
    },
    "courseId": {
      "type": "string"
    },
    "classId": {
      "type": "string"
    },
    "activeId": {
      "type": "string"
    },
    "targetStatus": {
      "type": "number",
      "enum": [
        1,
        2,
        5,
        7,
        8,
        9,
        10,
        11,
        12
      ]
    },
    "acknowledgeSmallClass": {
      "type": "boolean",
      "default": false
    }
  },
  "required": [
    "accountId",
    "courseId",
    "classId",
    "activeId",
    "targetStatus",
    "acknowledgeSmallClass"
  ]
}
```
</details>

### CreateShopRechargeOrderDto

```
**object**:
  - `packageKey` *(必填)*: string Recharge package key from GET /student/shop-recharge/packages
  - `quantity` *(必填)*: number default=1 Number of package units to purchase
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "packageKey": {
      "type": "string",
      "description": "Recharge package key from GET /student/shop-recharge/packages"
    },
    "quantity": {
      "type": "number",
      "default": 1,
      "description": "Number of package units to purchase",
      "maximum": 99,
      "minimum": 1
    }
  },
  "required": [
    "packageKey"
  ]
}
```
</details>

### CreateWithdrawDto

```
**object**:
  - `amount` *(必填)*: number 
  - `payoutMethod` *(必填)*: string 
  - `payoutNote` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "amount": {
      "type": "number",
      "minimum": 1
    },
    "payoutMethod": {
      "type": "string"
    },
    "payoutNote": {
      "type": "string"
    }
  },
  "required": [
    "amount"
  ]
}
```
</details>

### DisableUserDto

```
**object**:
  - `reason` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "reason": {
      "type": "string",
      "maxLength": 200
    }
  },
  "required": [
    "reason"
  ]
}
```
</details>

### GrantPointsDto

```
**object**:
  - `delta` *(必填)*: number 
  - `note` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "delta": {
      "type": "number"
    },
    "note": {
      "type": "string",
      "maxLength": 200
    }
  },
  "required": [
    "delta",
    "note"
  ]
}
```
</details>

### LoginDto

```
**object**:
  - `loginName` *(必填)*: string 
  - `password` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "loginName": {
      "type": "string"
    },
    "password": {
      "type": "string"
    }
  },
  "required": [
    "loginName",
    "password"
  ]
}
```
</details>

### LogoutDto

```
**object**:
  - `all`: boolean 
  - `refreshToken`: string Optional refresh token. Authorization bearer is preferred.
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "all": {
      "type": "boolean"
    },
    "refreshToken": {
      "type": "string",
      "description": "Optional refresh token. Authorization bearer is preferred."
    }
  }
}
```
</details>

### PurchaseDiscountPackageDto

```
**object**:
  - `ruleId` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "ruleId": {
      "type": "string"
    }
  },
  "required": [
    "ruleId"
  ]
}
```
</details>

### ReassignUserDto

```
**object**:
  - `agentId`: object 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "agentId": {
      "type": "object",
      "nullable": true
    }
  }
}
```
</details>

### RedeemCardDto

```
**object**:
  - `code` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string"
    }
  },
  "required": [
    "code"
  ]
}
```
</details>

### RefreshDto

```
**object**:
  - `refreshToken`: string Optional refresh token. Authorization bearer is preferred.
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "refreshToken": {
      "type": "string",
      "description": "Optional refresh token. Authorization bearer is preferred."
    }
  }
}
```
</details>

### RefundShopRechargeOrderDto

```
**object**:
  - `reason` *(必填)*: string Admin-facing refund reason
  - `externalRef` *(必填)*: string External xiucat-shop refund record, payment-provider refund number, or manual refund evidence
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "reason": {
      "type": "string",
      "description": "Admin-facing refund reason",
      "maxLength": 500
    },
    "externalRef": {
      "type": "string",
      "description": "External xiucat-shop refund record, payment-provider refund number, or manual refund evidence",
      "maxLength": 200
    }
  },
  "required": [
    "reason",
    "externalRef"
  ]
}
```
</details>

### RegisterAgentDto

```
**object**:
  - `loginName` *(必填)*: string 登录名需为至少 6 位数字、字母或下划线
  - `password` *(必填)*: string 
  - `nickname` *(必填)*: string 
  - `email` *(必填)*: string 
  - `phone` *(必填)*: string 
  - `inviteCode` *(必填)*: string 
  - `reason` *(必填)*: string 
  - `contactNote` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "loginName": {
      "type": "string",
      "description": "登录名需为至少 6 位数字、字母或下划线",
      "minLength": 6,
      "pattern": "^[A-Za-z0-9_]{6,}$"
    },
    "password": {
      "type": "string"
    },
    "nickname": {
      "type": "string"
    },
    "email": {
      "type": "string"
    },
    "phone": {
      "type": "string"
    },
    "inviteCode": {
      "type": "string"
    },
    "reason": {
      "type": "string",
      "maxLength": 200
    },
    "contactNote": {
      "type": "string"
    }
  },
  "required": [
    "loginName",
    "password",
    "nickname",
    "email",
    "inviteCode",
    "reason"
  ]
}
```
</details>

### RegisterStudentDto

```
**object**:
  - `loginName` *(必填)*: string 登录名需为至少 6 位数字、字母或下划线
  - `password` *(必填)*: string 
  - `nickname` *(必填)*: string 
  - `email` *(必填)*: string 
  - `phone` *(必填)*: string 
  - `inviteCode` *(必填)*: string 
  - `reason` *(必填)*: string 
  - `contactNote` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "loginName": {
      "type": "string",
      "description": "登录名需为至少 6 位数字、字母或下划线",
      "minLength": 6,
      "pattern": "^[A-Za-z0-9_]{6,}$"
    },
    "password": {
      "type": "string"
    },
    "nickname": {
      "type": "string"
    },
    "email": {
      "type": "string"
    },
    "phone": {
      "type": "string"
    },
    "inviteCode": {
      "type": "string"
    },
    "reason": {
      "type": "string",
      "maxLength": 200
    },
    "contactNote": {
      "type": "string"
    }
  },
  "required": [
    "loginName",
    "password",
    "nickname",
    "email"
  ]
}
```
</details>

### RejectApplicationDto

```
**object**:
  - `reason` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "reason": {
      "type": "string",
      "maxLength": 200
    }
  },
  "required": [
    "reason"
  ]
}
```
</details>

### RejectWithdrawDto

```
**object**:
  - `reason` *(必填)*: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "reason": {
      "type": "string"
    }
  },
  "required": [
    "reason"
  ]
}
```
</details>

### ShopRechargeCallbackDto

```
**object**:
  - `event` *(必填)*: string 
  - `order_id` *(必填)*: number 
  - `order_no` *(必填)*: string 
  - `downstream_order_no` *(必填)*: string 
  - `status` *(必填)*: string 
  - `timestamp` *(必填)*: number 
  - `amount` *(必填)*: string 
  - `currency` *(必填)*: string 
  - `fulfillment` *(必填)*: object
    **object**:
      - `amount`: string 
      - `currency`: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "event": {
      "type": "string"
    },
    "order_id": {
      "type": "number"
    },
    "order_no": {
      "type": "string"
    },
    "downstream_order_no": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "timestamp": {
      "type": "number"
    },
    "amount": {
      "type": "string"
    },
    "currency": {
      "type": "string"
    },
    "fulfillment": {
      "type": "object",
      "properties": {
        "amount": {
          "type": "string"
        },
        "currency": {
          "type": "string"
        }
      }
    }
  },
  "required": [
    "event",
    "order_id",
    "order_no",
    "downstream_order_no",
    "status",
    "timestamp"
  ]
}
```
</details>

### ShopRechargeCallbackFulfillmentDto

```
**object**:
  - `amount`: string 
  - `currency`: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "amount": {
      "type": "string"
    },
    "currency": {
      "type": "string"
    }
  }
}
```
</details>

### UpdateAnnouncementDto

```
**object**:
  - `body`: string 
  - `displayMode`: string enum=['MODAL', 'SILENT'] 
  - `endsAt`: string 
  - `level`: string enum=['INFO', 'WARN', 'ERROR'] 
  - `startsAt`: string 
  - `targetRole`: string enum=['AGENT', 'STUDENT'] 
  - `title`: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "body": {
      "type": "string",
      "maxLength": 4000
    },
    "displayMode": {
      "type": "string",
      "enum": [
        "MODAL",
        "SILENT"
      ]
    },
    "endsAt": {
      "type": "string",
      "nullable": true
    },
    "level": {
      "type": "string",
      "enum": [
        "INFO",
        "WARN",
        "ERROR"
      ]
    },
    "startsAt": {
      "type": "string",
      "nullable": true
    },
    "targetRole": {
      "type": "string",
      "enum": [
        "AGENT",
        "STUDENT"
      ]
    },
    "title": {
      "type": "string",
      "maxLength": 120
    }
  }
}
```
</details>

### UpdateCardExpiryDto

```
**object**:
  - `expiresAt`: object 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "expiresAt": {
      "type": "object",
      "nullable": true
    }
  }
}
```
</details>

### UpdateCommissionDto

```
**object**:
  - `rate` *(必填)*: number 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "rate": {
      "type": "number",
      "maximum": 100,
      "minimum": 0
    }
  },
  "required": [
    "rate"
  ]
}
```
</details>

### UpdateDiscountPackageRuleDto

```
**object**:
  - `name`: string 
  - `quantity`: number 
  - `unitPrice`: number 
  - `status`: string enum=['ACTIVE', 'DISABLED'] 
  - `note`: object 
  - `sortOrder`: number 
  - `shopSkuId`: object xiucat-shop SKU id for cash checkout
  - `cashAmount`: object Cash amount charged by xiucat-shop, e.g. 19.90
  - `currency`: string default=CNY 
  - `purchaseEnabled`: boolean 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "example": "5次优惠包"
    },
    "quantity": {
      "type": "number",
      "minimum": 1
    },
    "unitPrice": {
      "type": "number",
      "minimum": 1
    },
    "status": {
      "type": "string",
      "enum": [
        "ACTIVE",
        "DISABLED"
      ]
    },
    "note": {
      "type": "object",
      "nullable": true
    },
    "sortOrder": {
      "type": "number"
    },
    "shopSkuId": {
      "type": "object",
      "description": "xiucat-shop SKU id for cash checkout",
      "nullable": true
    },
    "cashAmount": {
      "type": "object",
      "description": "Cash amount charged by xiucat-shop, e.g. 19.90",
      "nullable": true
    },
    "currency": {
      "type": "string",
      "default": "CNY"
    },
    "purchaseEnabled": {
      "type": "boolean"
    }
  }
}
```
</details>

### UpdateServiceConfigDto

```
**object**:
  - `valueInt`: number 
  - `valueStr`: string 
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "valueInt": {
      "type": "number",
      "example": 30
    },
    "valueStr": {
      "type": "string",
      "example": "enabled"
    }
  }
}
```
</details>

### XiucatQuickLoginDto

```
**object**:
  - `account` *(必填)*: string 修猫账号 / 学习通手机号
  - `password` *(必填)*: string 密码
```

<details><summary>原始 JSON</summary>

```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "description": "修猫账号 / 学习通手机号"
    },
    "password": {
      "type": "string",
      "description": "密码"
    }
  },
  "required": [
    "account",
    "password"
  ]
}
```
</details>

## 11. 服务架构推测分析

### 认证机制
发现 9 个认证相关端点:
- `POST /api/auth/login`
- `POST /api/auth/xiucat-quick-login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/change-password`
- `POST /api/register/agent`
- `POST /api/register/student`
- `POST /api/chaoxing/accounts`
- `POST /api/shop-recharge/callback`

推测认证流程:
1. 用户通过 `POST /api/auth/login` 进行登录
   - 需要提供字段: loginName, password
1. 用户通过 `POST /api/auth/xiucat-quick-login` 进行登录
   - 需要提供字段: account, password
1. 用户通过 `POST /api/chaoxing/accounts` 进行登录
   - 需要提供字段: account, password, note

### 签到操作流程
发现签到相关端点，推测签到流程:
- `POST /api/auth/login`: 无描述
- `POST /api/auth/xiucat-quick-login`: 无描述
- `POST /api/auth/refresh`: 无描述
- `POST /api/auth/logout`: 无描述
- `POST /api/auth/change-password`: 无描述
- `GET /api/announcements/active`: 无描述
- `GET /api/admin/ledger/history`: 无描述
- `GET /api/admin/cards/batches`: 无描述
- `POST /api/admin/cards/batches`: 无描述
- `GET /api/admin/cards`: 无描述
- `POST /api/admin/cards/batches/{id}/revoke`: 无描述
- `PATCH /api/admin/cards/batches/{id}/expires`: 无描述
- `PATCH /api/admin/users/{id}/reassign`: 无描述
- `POST /api/admin/users/{id}/reset-password`: 无描述
- `GET /api/student/discount-package/rules`: List active discount package rules for students
- `GET /api/student/discount-package/current`: Get current active discount package purchase
- `GET /api/chaoxing/accounts`: List visible Chaoxing accounts
- `POST /api/chaoxing/accounts`: Bind one Chaoxing account and validate login
- `POST /api/chaoxing/accounts/bulk`: Bulk import Chaoxing accounts from CSV
- `GET /api/chaoxing/accounts/bulk/{id}`: Get one Chaoxing account import batch
- `GET /api/chaoxing/accounts/system-teacher`: Get configured patch-sign system teacher account
- `PUT /api/chaoxing/accounts/system-teacher`: Configure patch-sign system teacher account
- `DELETE /api/chaoxing/accounts/{id}`: Delete one visible Chaoxing account
- `GET /api/chaoxing/courses`: List Chaoxing courses for an account
- `GET /api/chaoxing/courses/{courseId}/classes/{classId}/actives`: List Chaoxing sign activities for a class
- `GET /api/chaoxing/actives/{activeId}`: Get Chaoxing sign activity details
- `GET /api/chaoxing/actives/{activeId}/members`: Get Chaoxing sign activity member statuses
- `GET /api/patch-sign/tasks`: List visible patch-sign tasks
- `POST /api/patch-sign/tasks`: Create one patch-sign task
- `POST /api/patch-sign/tasks/bulk`: Create patch-sign tasks in bulk
- `GET /api/patch-sign/tasks/{id}`: Get one visible patch-sign task
- `DELETE /api/patch-sign/tasks/{id}`: Cancel a queued patch-sign task
- `POST /api/admin/patch-sign/tasks/{id}/force-cancel`: Force-cancel a patch-sign task as admin
- `POST /api/shop-recharge/callback`: Receive signed xiucat-shop recharge callback

### 与超星平台的交互方式
发现直接的超星交互端点:
- `GET /api/chaoxing/accounts`: List visible Chaoxing accounts
- `POST /api/chaoxing/accounts`: Bind one Chaoxing account and validate login
- `POST /api/chaoxing/accounts/bulk`: Bulk import Chaoxing accounts from CSV
- `GET /api/chaoxing/accounts/bulk/{id}`: Get one Chaoxing account import batch
- `GET /api/chaoxing/accounts/system-teacher`: Get configured patch-sign system teacher account
- `PUT /api/chaoxing/accounts/system-teacher`: Configure patch-sign system teacher account
- `DELETE /api/chaoxing/accounts/{id}`: Delete one visible Chaoxing account
- `GET /api/chaoxing/courses`: List Chaoxing courses for an account
- `GET /api/chaoxing/courses/{courseId}/classes/{classId}/actives`: List Chaoxing sign activities for a class
- `GET /api/chaoxing/actives/{activeId}`: Get Chaoxing sign activity details
- `GET /api/chaoxing/actives/{activeId}/members`: Get Chaoxing sign activity member statuses

### 异步任务处理
发现任务/异步端点:
- `GET /api/patch-sign/tasks`: List visible patch-sign tasks
- `POST /api/patch-sign/tasks`: Create one patch-sign task
- `POST /api/patch-sign/tasks/bulk`: Create patch-sign tasks in bulk
- `GET /api/patch-sign/tasks/{id}`: Get one visible patch-sign task
- `DELETE /api/patch-sign/tasks/{id}`: Cancel a queued patch-sign task
- `POST /api/admin/patch-sign/tasks/{id}/force-cancel`: Force-cancel a patch-sign task as admin

这表明服务可能使用异步任务队列处理签到操作，支持:
- 定时签到（监控课程活动）
- 批量签到
- 后台签到状态轮询

### 安全风险点
- 服务需要用户提交超星账号凭据（手机号/密码或Cookie）
- 用户的超星凭据存储在第三方服务器上
- 服务代替用户操作超星平台，存在账号风险
- 签到操作可能违反超星平台使用条款

## 12. 关键发现总结

- `POST /api/auth/login` 接受凭据字段: password
- `POST /api/auth/xiucat-quick-login` 接受凭据字段: password
- `POST /api/register/agent` 接受凭据字段: password, phone
- `POST /api/register/student` 接受凭据字段: password, phone
- `POST /api/chaoxing/accounts` 接受凭据字段: password
- `PUT /api/chaoxing/accounts/system-teacher` 接受凭据字段: password
- `GET /api/admin/cards/batches` 批量操作端点
- `POST /api/admin/cards/batches` 批量操作端点
- `POST /api/admin/cards/batches/{id}/revoke` 批量操作端点
- `PATCH /api/admin/cards/batches/{id}/expires` 批量操作端点
- `POST /api/chaoxing/accounts/bulk` 批量操作端点
- `GET /api/chaoxing/accounts/bulk/{id}` 批量操作端点
- `POST /api/patch-sign/tasks/bulk` 批量操作端点

---

*本报告由自动化分析脚本生成，仅供安全研究参考。*