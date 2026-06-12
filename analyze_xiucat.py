#!/usr/bin/env python3
"""
Xiucat API OpenAPI Specification Fetcher & Analyzer
Security Research - ChaoXing Sign-in Service Analysis
"""

import json
import sys
import urllib.request
import urllib.error
from collections import defaultdict

URL = "https://beta-a.xiucat.top/docs-json"
RAW_OUTPUT = "/workspace/xiucat_openapi_spec.json"
ANALYSIS_OUTPUT = "/workspace/xiucat_api_analysis.md"

# Keywords for sign-in related endpoints
SIGN_KEYWORDS = [
    "sign", "签到", "chaoxing", "course", "active", "attendance",
    "task", "job", "xuexitong", "超星", "学习通", "login", "auth",
    "cookie", "token", "phone", "password", "credential", "checkin",
    "check-in", "punch", "location", "qr", "qrcode", "photo",
    "preSign", "presign", "monitor", "watch", "auto", "batch"
]


def fetch_spec(url):
    """Fetch OpenAPI spec from URL."""
    print(f"[*] Fetching OpenAPI spec from {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"[+] Successfully fetched spec ({len(json.dumps(data))} bytes)")
        return data
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP Error: {e.code} {e.reason}")
        # Try reading error body
        try:
            body = e.read().decode("utf-8")
            print(f"    Response body: {body[:500]}")
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error fetching spec: {e}")
        sys.exit(1)


def resolve_ref(spec, ref_str):
    """Resolve a $ref reference like '#/components/schemas/Xxx'."""
    if not ref_str.startswith("#/"):
        return {"$ref": ref_str, "_note": "External or unresolved ref"}
    parts = ref_str[2:].split("/")
    obj = spec
    for part in parts:
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return {"$ref": ref_str, "_note": "Broken ref"}
    return obj


def resolve_schema(spec, schema, depth=0, max_depth=10):
    """Recursively resolve all $ref in a schema."""
    if depth > max_depth:
        return {"_note": "Max depth exceeded", "_schema": str(schema)[:200]}

    if isinstance(schema, dict):
        if "$ref" in schema:
            resolved = resolve_ref(spec, schema["$ref"])
            return resolve_schema(spec, resolved, depth + 1, max_depth)
        result = {}
        for k, v in schema.items():
            result[k] = resolve_schema(spec, v, depth + 1, max_depth)
        return result
    elif isinstance(schema, list):
        return [resolve_schema(spec, item, depth + 1, max_depth) for item in schema]
    else:
        return schema


def extract_params(params_list):
    """Extract parameter details."""
    if not params_list:
        return []
    result = []
    for p in params_list:
        info = {
            "name": p.get("name"),
            "in": p.get("in"),
            "required": p.get("required", False),
            "description": p.get("description", ""),
            "schema": p.get("schema", {}),
        }
        result.append(info)
    return result


def extract_request_body(spec, body_obj):
    """Extract and resolve request body schema."""
    if not body_obj:
        return None
    content = body_obj.get("content", {})
    result = {}
    for media_type, media_info in content.items():
        schema = media_info.get("schema", {})
        result[media_type] = resolve_schema(spec, schema)
    return {
        "description": body_obj.get("description", ""),
        "required": body_obj.get("required", False),
        "content": result,
    }


def extract_responses(spec, responses_obj):
    """Extract and resolve response schemas."""
    if not responses_obj:
        return {}
    result = {}
    for code, resp_info in responses_obj.items():
        content = resp_info.get("content", {})
        resolved_content = {}
        for media_type, media_info in content.items():
            schema = media_info.get("schema", {})
            resolved_content[media_type] = resolve_schema(spec, schema)
        result[code] = {
            "description": resp_info.get("description", ""),
            "content": resolved_content,
        }
    return result


def is_sign_related(path, method, operation):
    """Check if an endpoint is related to sign-in operations."""
    search_text = (path + " " + method + " ").lower()
    # Add operation metadata
    search_text += (operation.get("summary", "") + " ").lower()
    search_text += (operation.get("description", "") + " ").lower()
    search_text += (operation.get("operationId", "") + " ").lower()
    # Add tag names
    for tag in operation.get("tags", []):
        search_text += (tag + " ").lower()
    # Add parameter names and descriptions
    for p in operation.get("parameters", []):
        search_text += (p.get("name", "") + " ").lower()
        search_text += (p.get("description", "") + " ").lower()
    # Add request body description
    rb = operation.get("requestBody", {})
    if rb:
        search_text += (rb.get("description", "") + " ").lower()

    for kw in SIGN_KEYWORDS:
        if kw.lower() in search_text:
            return True
    return False


def analyze_spec(spec):
    """Perform comprehensive analysis of the OpenAPI spec."""
    paths = spec.get("paths", {})
    components = spec.get("components", {})
    schemas = components.get("schemas", {})
    security_schemes = components.get("securitySchemes", {})

    # Collect all endpoints
    all_endpoints = []
    sign_endpoints = []
    endpoints_by_tag = defaultdict(list)
    auth_endpoints = []
    chaoxing_endpoints = []
    task_job_endpoints = []
    websocket_endpoints = []

    for path, path_item in paths.items():
        # Check for WebSocket/SSE at path level
        for key in path_item:
            if key.lower() in ("ws", "wss", "websocket", "sse", "eventstream"):
                websocket_endpoints.append({"path": path, "type": key, "details": path_item[key]})

        for method in ["get", "post", "put", "patch", "delete", "options", "head", "trace"]:
            if method not in path_item:
                continue
            operation = path_item[method]
            tags = operation.get("tags", ["未分类"])
            summary = operation.get("summary", "")
            description = operation.get("description", "")
            operation_id = operation.get("operationId", "")
            params = extract_params(operation.get("parameters", []))
            request_body = extract_request_body(spec, operation.get("requestBody"))
            responses = extract_responses(spec, operation.get("responses", {}))
            security = operation.get("security", None)
            deprecated = operation.get("deprecated", False)

            endpoint_info = {
                "path": path,
                "method": method.upper(),
                "summary": summary,
                "description": description,
                "operationId": operation_id,
                "tags": tags,
                "parameters": params,
                "requestBody": request_body,
                "responses": responses,
                "security": security,
                "deprecated": deprecated,
            }

            all_endpoints.append(endpoint_info)

            for tag in tags:
                endpoints_by_tag[tag].append(endpoint_info)

            # Check sign-in related
            if is_sign_related(path, method, operation):
                sign_endpoints.append(endpoint_info)

            # Check auth-related
            auth_kw = ["login", "auth", "token", "session", "cookie", "credential", "register", "signup", "quick-login", "xiucat"]
            auth_text = (path + " " + summary + " " + description + " " + operation_id).lower()
            if any(kw in auth_text for kw in auth_kw):
                auth_endpoints.append(endpoint_info)

            # Check ChaoXing interaction
            cx_kw = ["chaoxing", "xuexitong", "超星", "学习通", "cx", "fx", "mooc1", "mooc1-1", "mooc1-2", "chaoxing.com"]
            cx_text = (path + " " + summary + " " + description + " " + operation_id).lower()
            # Also check in request body and params
            for p in params:
                cx_text += " " + (p.get("name", "") + " " + p.get("description", "")).lower()
            if request_body and request_body.get("description"):
                cx_text += " " + request_body["description"].lower()
            if any(kw in cx_text for kw in cx_kw):
                chaoxing_endpoints.append(endpoint_info)

            # Check task/job endpoints
            task_kw = ["task", "job", "queue", "async", "schedule", "cron", "worker"]
            task_text = (path + " " + summary + " " + description + " " + operation_id).lower()
            if any(kw in task_text for kw in task_kw):
                task_job_endpoints.append(endpoint_info)

    return {
        "all_endpoints": all_endpoints,
        "sign_endpoints": sign_endpoints,
        "auth_endpoints": auth_endpoints,
        "chaoxing_endpoints": chaoxing_endpoints,
        "task_job_endpoints": task_job_endpoints,
        "websocket_endpoints": websocket_endpoints,
        "endpoints_by_tag": dict(endpoints_by_tag),
        "schemas": schemas,
        "security_schemes": security_schemes,
        "info": spec.get("info", {}),
        "servers": spec.get("servers", []),
    }


def schema_to_markdown(schema, indent=0):
    """Convert a resolved schema to readable markdown."""
    if not schema:
        return "无"
    prefix = "  " * indent
    lines = []

    if isinstance(schema, dict):
        if "type" in schema:
            type_str = schema["type"]
            if type_str == "object" and "properties" in schema:
                lines.append(f"{prefix}**object**:")
                for prop_name, prop_schema in schema["properties"].items():
                    required = prop_name in schema.get("required", []) or schema.get("required", False)
                    req_mark = " *(必填)*" if required else ""
                    prop_type = prop_schema.get("type", "unknown") if isinstance(prop_schema, dict) else "unknown"
                    desc = prop_schema.get("description", "") if isinstance(prop_schema, dict) else ""
                    if prop_type == "object" and "properties" in prop_schema:
                        lines.append(f"{prefix}  - `{prop_name}`{req_mark}: object")
                        lines.append(schema_to_markdown(prop_schema, indent + 2))
                    elif prop_type == "array" and isinstance(prop_schema, dict) and "items" in prop_schema:
                        items = prop_schema["items"]
                        item_type = items.get("type", "object") if isinstance(items, dict) else "object"
                        lines.append(f"{prefix}  - `{prop_name}`{req_mark}: array[{item_type}] {desc}")
                        if isinstance(items, dict) and "properties" in items:
                            lines.append(schema_to_markdown(items, indent + 2))
                    else:
                        enum_str = ""
                        if isinstance(prop_schema, dict) and "enum" in prop_schema:
                            enum_str = f" enum={prop_schema['enum']}"
                        default_str = ""
                        if isinstance(prop_schema, dict) and "default" in prop_schema:
                            default_str = f" default={prop_schema['default']}"
                        lines.append(f"{prefix}  - `{prop_name}`{req_mark}: {prop_type}{enum_str}{default_str} {desc}")
            elif type_str == "array" and "items" in schema:
                items = schema["items"]
                lines.append(f"{prefix}**array**:")
                lines.append(schema_to_markdown(items, indent + 1))
            else:
                enum_str = f" enum={schema['enum']}" if "enum" in schema else ""
                default_str = f" default={schema['default']}" if "default" in schema else ""
                lines.append(f"{prefix}{type_str}{enum_str}{default_str}")
        elif "oneOf" in schema:
            lines.append(f"{prefix}**oneOf**:")
            for i, sub in enumerate(schema["oneOf"]):
                lines.append(f"{prefix}  选项{i+1}:")
                lines.append(schema_to_markdown(sub, indent + 2))
        elif "allOf" in schema:
            lines.append(f"{prefix}**allOf**:")
            for sub in schema["allOf"]:
                lines.append(schema_to_markdown(sub, indent + 1))
        elif "anyOf" in schema:
            lines.append(f"{prefix}**anyOf**:")
            for sub in schema["anyOf"]:
                lines.append(schema_to_markdown(sub, indent + 1))
        else:
            # Just dump key info
            for k, v in schema.items():
                if k not in ("properties", "required", "type"):
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}: {json.dumps(v, ensure_ascii=False)[:200]}")
                    else:
                        lines.append(f"{prefix}{k}: {v}")

    return "\n".join(lines)


def write_analysis(analysis, spec):
    """Write comprehensive analysis to markdown."""
    lines = []

    lines.append("# Xiucat API 全面分析报告")
    lines.append("")
    lines.append(f"> 分析目标: https://beta-a.xiucat.top/docs-json")
    lines.append(f"> 分析时间: 2026-06-12")
    lines.append(f"> 原始规范已保存至: `/workspace/xiucat_openapi_spec.json`")
    lines.append("")

    # API Info
    info = analysis["info"]
    lines.append("## 1. API 基本信息")
    lines.append("")
    lines.append(f"- **标题**: {info.get('title', 'N/A')}")
    lines.append(f"- **版本**: {info.get('version', 'N/A')}")
    lines.append(f"- **描述**: {info.get('description', 'N/A')}")
    lines.append("")

    # Servers
    servers = analysis["servers"]
    if servers:
        lines.append("### 服务器列表")
        lines.append("")
        for s in servers:
            lines.append(f"- `{s.get('url', 'N/A')}` - {s.get('description', '')}")
        lines.append("")

    # Security Schemes
    sec_schemes = analysis["security_schemes"]
    if sec_schemes:
        lines.append("## 2. 安全方案 (Security Schemes)")
        lines.append("")
        for name, scheme in sec_schemes.items():
            lines.append(f"### {name}")
            lines.append(f"- **类型**: {scheme.get('type', 'N/A')}")
            lines.append(f"- **方案**: {scheme.get('scheme', 'N/A')}")
            lines.append(f"- **Bearer 格式**: {scheme.get('bearerFormat', 'N/A')}")
            if scheme.get("description"):
                lines.append(f"- **描述**: {scheme['description']}")
            if scheme.get("flows"):
                lines.append(f"- **OAuth 流程**: {json.dumps(scheme['flows'], ensure_ascii=False, indent=2)}")
            if scheme.get("openIdConnectUrl"):
                lines.append(f"- **OpenID Connect URL**: {scheme['openIdConnectUrl']}")
            lines.append("")
    else:
        lines.append("## 2. 安全方案 (Security Schemes)")
        lines.append("")
        lines.append("未在 components 中定义安全方案（可能在操作级别定义）")
        lines.append("")

    # Statistics
    total = len(analysis["all_endpoints"])
    sign_count = len(analysis["sign_endpoints"])
    auth_count = len(analysis["auth_endpoints"])
    cx_count = len(analysis["chaoxing_endpoints"])
    task_count = len(analysis["task_job_endpoints"])
    ws_count = len(analysis["websocket_endpoints"])

    lines.append("## 3. 端点统计")
    lines.append("")
    lines.append(f"| 类别 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总端点数 | {total} |")
    lines.append(f"| 签到相关端点 | {sign_count} |")
    lines.append(f"| 认证相关端点 | {auth_count} |")
    lines.append(f"| 超星交互端点 | {cx_count} |")
    lines.append(f"| 任务/异步端点 | {task_count} |")
    lines.append(f"| WebSocket/SSE端点 | {ws_count} |")
    lines.append("")

    # Complete endpoint list by tag
    lines.append("## 4. 完整端点列表（按标签分组）")
    lines.append("")
    for tag, endpoints in sorted(analysis["endpoints_by_tag"].items()):
        lines.append(f"### {tag}")
        lines.append("")
        lines.append("| 方法 | 路径 | 摘要 | 操作ID |")
        lines.append("|------|------|------|--------|")
        for ep in endpoints:
            dep_mark = " ⚠️已弃用" if ep["deprecated"] else ""
            lines.append(f"| {ep['method']} | `{ep['path']}` | {ep['summary']}{dep_mark} | {ep['operationId']} |")
        lines.append("")

    # Sign-in related endpoints
    lines.append("## 5. 签到相关端点详细分析")
    lines.append("")
    if not analysis["sign_endpoints"]:
        lines.append("未发现签到相关端点。")
        lines.append("")
    else:
        for ep in analysis["sign_endpoints"]:
            lines.append(f"### {ep['method']} `{ep['path']}`")
            lines.append(f"- **摘要**: {ep['summary']}")
            lines.append(f"- **描述**: {ep['description']}")
            lines.append(f"- **操作ID**: {ep['operationId']}")
            lines.append(f"- **标签**: {', '.join(ep['tags'])}")
            if ep["deprecated"]:
                lines.append(f"- ⚠️ **已弃用**")
            lines.append("")

            # Parameters
            if ep["parameters"]:
                lines.append("#### 参数")
                lines.append("")
                lines.append("| 名称 | 位置 | 必填 | 类型 | 描述 |")
                lines.append("|------|------|------|------|------|")
                for p in ep["parameters"]:
                    ptype = json.dumps(p.get("schema", {}), ensure_ascii=False)[:100]
                    lines.append(f"| `{p['name']}` | {p['in']} | {'是' if p['required'] else '否'} | {ptype} | {p['description']} |")
                lines.append("")

            # Request Body
            if ep["requestBody"]:
                lines.append("#### 请求体")
                lines.append("")
                lines.append(f"- **描述**: {ep['requestBody']['description']}")
                lines.append(f"- **必填**: {'是' if ep['requestBody']['required'] else '否'}")
                for media_type, schema in ep["requestBody"]["content"].items():
                    lines.append(f"- **Content-Type**: `{media_type}`")
                    lines.append("")
                    lines.append("```")
                    lines.append(schema_to_markdown(schema))
                    lines.append("```")
                    lines.append("")
                    # Also dump raw JSON for clarity
                    lines.append("<details><summary>原始 Schema JSON</summary>")
                    lines.append("")
                    lines.append("```json")
                    lines.append(json.dumps(schema, ensure_ascii=False, indent=2)[:3000])
                    lines.append("```")
                    lines.append("</details>")
                    lines.append("")

            # Responses
            if ep["responses"]:
                lines.append("#### 响应")
                lines.append("")
                for code, resp in ep["responses"].items():
                    lines.append(f"**状态码 {code}**: {resp['description']}")
                    for media_type, schema in resp["content"].items():
                        lines.append(f"- Content-Type: `{media_type}`")
                        lines.append("")
                        lines.append("```")
                        lines.append(schema_to_markdown(schema))
                        lines.append("```")
                        lines.append("")
                        lines.append("<details><summary>原始 Schema JSON</summary>")
                        lines.append("")
                        lines.append("```json")
                        lines.append(json.dumps(schema, ensure_ascii=False, indent=2)[:3000])
                        lines.append("```")
                        lines.append("</details>")
                        lines.append("")

            # Security
            if ep["security"] is not None:
                lines.append("#### 安全要求")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(ep["security"], ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Authentication flow analysis
    lines.append("## 6. 认证流程分析")
    lines.append("")
    if not analysis["auth_endpoints"]:
        lines.append("未发现认证相关端点。")
    else:
        for ep in analysis["auth_endpoints"]:
            lines.append(f"### {ep['method']} `{ep['path']}`")
            lines.append(f"- **摘要**: {ep['summary']}")
            lines.append(f"- **描述**: {ep['description']}")
            lines.append(f"- **操作ID**: {ep['operationId']}")
            lines.append(f"- **标签**: {', '.join(ep['tags'])}")
            if ep["parameters"]:
                lines.append("- **参数**:")
                for p in ep["parameters"]:
                    lines.append(f"  - `{p['name']}` ({p['in']}): {p['description']}")
            if ep["requestBody"]:
                lines.append("- **请求体**:")
                for media_type, schema in ep["requestBody"]["content"].items():
                    lines.append(f"  - `{media_type}`:")
                    lines.append("```")
                    lines.append(schema_to_markdown(schema))
                    lines.append("```")
            if ep["responses"]:
                lines.append("- **响应**:")
                for code, resp in ep["responses"].items():
                    lines.append(f"  - {code}: {resp['description']}")
                    for mt, schema in resp["content"].items():
                        lines.append(f"    - `{mt}`:")
                        lines.append("```")
                        lines.append(schema_to_markdown(schema)[:1500])
                        lines.append("```")
            lines.append("")

    # ChaoXing interaction analysis
    lines.append("## 7. 超星(ChaoXing)交互端点分析")
    lines.append("")
    if not analysis["chaoxing_endpoints"]:
        lines.append("未发现直接的超星交互端点。可能在内部服务层处理。")
    else:
        for ep in analysis["chaoxing_endpoints"]:
            lines.append(f"### {ep['method']} `{ep['path']}`")
            lines.append(f"- **摘要**: {ep['summary']}")
            lines.append(f"- **描述**: {ep['description']}")
            lines.append(f"- **操作ID**: {ep['operationId']}")
            if ep["requestBody"]:
                lines.append("- **请求体**:")
                for media_type, schema in ep["requestBody"]["content"].items():
                    lines.append(f"  - `{media_type}`:")
                    lines.append("```json")
                    lines.append(json.dumps(schema, ensure_ascii=False, indent=2)[:2000])
                    lines.append("```")
            lines.append("")

    # Task/Job endpoints
    lines.append("## 8. 任务/异步端点分析")
    lines.append("")
    if not analysis["task_job_endpoints"]:
        lines.append("未发现任务/异步端点。")
    else:
        for ep in analysis["task_job_endpoints"]:
            lines.append(f"### {ep['method']} `{ep['path']}`")
            lines.append(f"- **摘要**: {ep['summary']}")
            lines.append(f"- **描述**: {ep['description']}")
            lines.append(f"- **操作ID**: {ep['operationId']}")
            if ep["parameters"]:
                lines.append("- **参数**:")
                for p in ep["parameters"]:
                    lines.append(f"  - `{p['name']}` ({p['in']}): {p['description']}")
            if ep["requestBody"]:
                lines.append("- **请求体**:")
                for media_type, schema in ep["requestBody"]["content"].items():
                    lines.append(f"  - `{media_type}`:")
                    lines.append("```json")
                    lines.append(json.dumps(schema, ensure_ascii=False, indent=2)[:2000])
                    lines.append("```")
            if ep["responses"]:
                lines.append("- **响应**:")
                for code, resp in ep["responses"].items():
                    lines.append(f"  - {code}: {resp['description']}")
                    for mt, schema in resp["content"].items():
                        lines.append(f"    - `{mt}`:")
                        lines.append("```json")
                        lines.append(json.dumps(schema, ensure_ascii=False, indent=2)[:2000])
                        lines.append("```")
            lines.append("")

    # WebSocket/SSE
    lines.append("## 9. WebSocket/SSE 端点")
    lines.append("")
    if not analysis["websocket_endpoints"]:
        lines.append("未发现 WebSocket 或 SSE 端点。")
    else:
        for ws in analysis["websocket_endpoints"]:
            lines.append(f"- **路径**: `{ws['path']}`")
            lines.append(f"- **类型**: {ws['type']}")
            lines.append(f"- **详情**: {json.dumps(ws['details'], ensure_ascii=False, indent=2)[:1000]}")
            lines.append("")

    # All schemas
    lines.append("## 10. 所有数据模型 (Schemas)")
    lines.append("")
    schemas = analysis["schemas"]
    if not schemas:
        lines.append("未定义 schemas。")
    else:
        for name, schema_def in sorted(schemas.items()):
            resolved = resolve_schema(spec, schema_def)
            lines.append(f"### {name}")
            lines.append("")
            lines.append("```")
            lines.append(schema_to_markdown(resolved))
            lines.append("```")
            lines.append("")
            lines.append("<details><summary>原始 JSON</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(resolved, ensure_ascii=False, indent=2)[:3000])
            lines.append("```")
            lines.append("</details>")
            lines.append("")

    # Architecture analysis
    lines.append("## 11. 服务架构推测分析")
    lines.append("")

    # Analyze based on what we found
    has_auth = len(analysis["auth_endpoints"]) > 0
    has_sign = len(analysis["sign_endpoints"]) > 0
    has_task = len(analysis["task_job_endpoints"]) > 0
    has_cx = len(analysis["chaoxing_endpoints"]) > 0

    lines.append("### 认证机制")
    if has_auth:
        auth_paths = [f"{ep['method']} {ep['path']}" for ep in analysis["auth_endpoints"]]
        lines.append(f"发现 {len(auth_paths)} 个认证相关端点:")
        for p in auth_paths:
            lines.append(f"- `{p}`")
        lines.append("")
        lines.append("推测认证流程:")
        for ep in analysis["auth_endpoints"]:
            if "login" in ep["path"].lower() or "login" in (ep["summary"] or "").lower():
                lines.append(f"1. 用户通过 `{ep['method']} {ep['path']}` 进行登录")
                if ep["requestBody"] and ep["requestBody"]["content"]:
                    for mt, schema in ep["requestBody"]["content"].items():
                        if isinstance(schema, dict) and "properties" in schema:
                            props = list(schema["properties"].keys())
                            lines.append(f"   - 需要提供字段: {', '.join(props)}")
    else:
        lines.append("未发现明确的认证端点，可能使用外部认证或API Key方式。")

    lines.append("")
    lines.append("### 签到操作流程")
    if has_sign:
        lines.append("发现签到相关端点，推测签到流程:")
        for ep in analysis["sign_endpoints"]:
            lines.append(f"- `{ep['method']} {ep['path']}`: {ep['summary'] or ep['description'] or '无描述'}")
    else:
        lines.append("需要进一步分析端点以确定签到操作流程。")

    lines.append("")
    lines.append("### 与超星平台的交互方式")
    if has_cx:
        lines.append("发现直接的超星交互端点:")
        for ep in analysis["chaoxing_endpoints"]:
            lines.append(f"- `{ep['method']} {ep['path']}`: {ep['summary'] or '无描述'}")
    else:
        lines.append("API层面未发现直接的超星交互端点。服务可能在后端内部通过HTTP客户端与超星API通信。")
        lines.append("推测交互方式:")
        lines.append("- 服务端存储用户的超星Cookie/Token")
        lines.append("- 后端模拟超星客户端发起签到请求")
        lines.append("- 可能使用超星移动端API或Web端API")

    lines.append("")
    lines.append("### 异步任务处理")
    if has_task:
        lines.append("发现任务/异步端点:")
        for ep in analysis["task_job_endpoints"]:
            lines.append(f"- `{ep['method']} {ep['path']}`: {ep['summary'] or '无描述'}")
        lines.append("")
        lines.append("这表明服务可能使用异步任务队列处理签到操作，支持:")
        lines.append("- 定时签到（监控课程活动）")
        lines.append("- 批量签到")
        lines.append("- 后台签到状态轮询")
    else:
        lines.append("未发现明确的异步任务端点。签到操作可能为同步处理。")

    lines.append("")
    lines.append("### 安全风险点")
    lines.append("- 服务需要用户提交超星账号凭据（手机号/密码或Cookie）")
    lines.append("- 用户的超星凭据存储在第三方服务器上")
    lines.append("- 服务代替用户操作超星平台，存在账号风险")
    lines.append("- 签到操作可能违反超星平台使用条款")

    lines.append("")
    lines.append("## 12. 关键发现总结")
    lines.append("")

    # Collect interesting findings
    findings = []

    # Check for credential-accepting endpoints
    for ep in analysis["all_endpoints"]:
        if ep["requestBody"] and ep["requestBody"]["content"]:
            for mt, schema in ep["requestBody"]["content"].items():
                if isinstance(schema, dict) and "properties" in schema:
                    props = schema["properties"]
                    cred_fields = [k for k in props if k.lower() in
                                   ["password", "phone", "cookie", "token", "uid", "fid", "cookies"]]
                    if cred_fields:
                        findings.append(f"- `{ep['method']} {ep['path']}` 接受凭据字段: {', '.join(cred_fields)}")

    # Check for monitoring/polling patterns
    for ep in analysis["all_endpoints"]:
        path_lower = ep["path"].lower()
        if any(kw in path_lower for kw in ["monitor", "watch", "poll", "subscribe", "listen"]):
            findings.append(f"- `{ep['method']} {ep['path']}` 可能是监控/轮询端点")

    # Check for batch operations
    for ep in analysis["all_endpoints"]:
        path_lower = ep["path"].lower()
        summary_lower = (ep["summary"] or "").lower()
        if "batch" in path_lower or "batch" in summary_lower or "bulk" in path_lower:
            findings.append(f"- `{ep['method']} {ep['path']}` 批量操作端点")

    if findings:
        for f in findings:
            lines.append(f)
    else:
        lines.append("无特殊发现。")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本报告由自动化分析脚本生成，仅供安全研究参考。*")

    return "\n".join(lines)


def main():
    # Fetch spec
    spec = fetch_spec(URL)

    # Save raw spec
    with open(RAW_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print(f"[+] Raw spec saved to {RAW_OUTPUT}")

    # Analyze
    print("[*] Analyzing spec...")
    analysis = analyze_spec(spec)

    print(f"[+] Total endpoints: {len(analysis['all_endpoints'])}")
    print(f"[+] Sign-in related: {len(analysis['sign_endpoints'])}")
    print(f"[+] Auth related: {len(analysis['auth_endpoints'])}")
    print(f"[+] ChaoXing related: {len(analysis['chaoxing_endpoints'])}")
    print(f"[+] Task/Job related: {len(analysis['task_job_endpoints'])}")
    print(f"[+] WebSocket/SSE: {len(analysis['websocket_endpoints'])}")
    print(f"[+] Tags: {list(analysis['endpoints_by_tag'].keys())}")
    print(f"[+] Schemas: {list(analysis['schemas'].keys())}")

    # Write analysis
    print("[*] Writing analysis report...")
    md = write_analysis(analysis, spec)
    with open(ANALYSIS_OUTPUT, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[+] Analysis report saved to {ANALYSIS_OUTPUT}")

    # Print sign-in endpoint summary
    if analysis["sign_endpoints"]:
        print("\n[*] Sign-in related endpoints found:")
        for ep in analysis["sign_endpoints"]:
            print(f"  - {ep['method']} {ep['path']}: {ep['summary']}")

    if analysis["auth_endpoints"]:
        print("\n[*] Auth related endpoints found:")
        for ep in analysis["auth_endpoints"]:
            print(f"  - {ep['method']} {ep['path']}: {ep['summary']}")

    if analysis["task_job_endpoints"]:
        print("\n[*] Task/Job endpoints found:")
        for ep in analysis["task_job_endpoints"]:
            print(f"  - {ep['method']} {ep['path']}: {ep['summary']}")

    print("\n[+] Done!")


if __name__ == "__main__":
    main()
