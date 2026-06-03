import base64, hashlib, json, uuid, requests, urllib3, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

urllib3.disable_warnings()
AES_KEY = b"u2oh6Vu^HWe4_AES"
SCHILD_SALT = "ipL$TkeiEmfy1gTXb2XHrdLN0a@7c^vu"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"
COURSE_ID = "257485372"
CLASS_ID = "132821141"

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
    return s, puid

def safe_json(r):
    try: return r.json()
    except: return {"_raw_status": r.status_code, "_raw_text": r.text[:500]}

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
base = "https://mobilelearn.chaoxing.com"

print("=" * 80)
print("关键验证：/newsign/updateSignStatus 是否真正修改了服务端数据？")
print("=" * 80)

# 找一个未签到的签到活动
r = s_s.get(f"{base}/ppt/activeAPI/taskactivelist",
            params={"courseId": COURSE_ID, "classId": CLASS_ID, "uid": puid_s}, timeout=20)
d = safe_json(r)
active_list = d.get("activeList", [])

# 找未签到的签到活动
target_aid = None
for act in active_list:
    aid = str(act.get("id", ""))
    atype = act.get("activeType", -1)
    if atype not in (2, 74):
        continue
    r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    # 只看V2 signIn能查到的活动
    if isinstance(d, dict) and d.get("result") == 1 and d.get("data"):
        status = d["data"].get("status")
        if status is None:
            target_aid = aid
            print(f"找到未签到活动: aid={aid}")
            break

if not target_aid:
    # 如果没有V2 signIn能查到的未签到活动，找所有签到活动
    print("没有V2 signIn可查的未签到活动，使用活动列表中的签到活动...")
    for act in active_list[:5]:
        aid = str(act.get("id", ""))
        atype = act.get("activeType", -1)
        if atype == 2:
            target_aid = aid
            print(f"使用活动: aid={aid}")
            break

if not target_aid:
    print("未找到任何签到活动！")
    exit()

aid = target_aid

# ========== 关键测试 ==========
print(f"\n{'=' * 80}")
print(f"测试1: 学生修改后，不调用教师V2，直接用教师端查询")
print(f"{'=' * 80}")

# 先查看教师端当前状态
print(f"\n--- 修改前：教师端查询 ---")
r = s_t.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
print(f"  教师V2 signIn查询: {json.dumps(d, ensure_ascii=False)[:300]}")

# 教师端signedResult页面查询
r = s_t.get(f"{base}/pptSign/signedResult",
            params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID},
            timeout=20, allow_redirects=True)
print(f"  教师signedResult页面: HTTP {r.status_code}, len={len(r.text)}")
# 提取学生签到状态
import re
status_in_page = re.findall(r'431407443[^}]*?status["\s:=]+(\d)', r.text)
student_in_page = re.findall(r'3141cpy[^<]*?<', r.text, re.I)
print(f"  页面中status值: {status_in_page[:5]}")
print(f"  页面中学生记录: {student_in_page[:3]}")

# 学生修改
print(f"\n--- 学生调用 /newsign/updateSignStatus ---")
r = s_s.post(f"{base}/newsign/updateSignStatus",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid},
             data={"uids": puid_s, "status": "1", "remark": "",
                   "activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
             headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/x-www-form-urlencoded"},
             timeout=20)
print(f"  API返回: {r.text}")

time.sleep(3)

# 修改后：教师端查询（不调用教师V2 API）
print(f"\n--- 修改后：教师端查询（不调用教师V2修改API）---")
r = s_t.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
teacher_status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  教师V2 signIn查询: status={teacher_status}, {json.dumps(d, ensure_ascii=False)[:300]}")

# 教师端signedResult页面查询
r = s_t.get(f"{base}/pptSign/signedResult",
            params={"activeId": aid, "classId": CLASS_ID, "courseId": COURSE_ID},
            timeout=20, allow_redirects=True)
status_in_page_after = re.findall(r'431407443[^}]*?status["\s:=]+(\d)', r.text)
print(f"  教师signedResult页面: HTTP {r.status_code}, len={len(r.text)}")
print(f"  页面中status值: {status_in_page_after[:5]}")

# 学生端查询
r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
student_status = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
print(f"  学生V2 signIn查询: status={student_status}, {json.dumps(d, ensure_ascii=False)[:200]}")

print(f"\n{'=' * 80}")
print(f"测试2: 对比 - 不调用/newsign/，仅调用教师V2修改")
print(f"{'=' * 80}")

# 找另一个未签到活动
target_aid2 = None
for act in active_list:
    aid2 = str(act.get("id", ""))
    atype = act.get("activeType", -1)
    if atype not in (2, 74) or aid2 == aid:
        continue
    r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid2, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and d.get("result") == 1 and d.get("data"):
        status = d["data"].get("status")
        if status is None:
            target_aid2 = aid2
            print(f"找到第二个未签到活动: aid={aid2}")
            break

if target_aid2:
    aid2 = target_aid2
    print(f"\n--- 仅教师V2修改（不调用/newsign/）---")
    r = s_t.post(f"{base}/pptSign/updateSignStatusByUidsV2",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid2},
                 data={"uids": puid_s, "status": "1", "remark": ""},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  教师V2: {r.text[:200]}")

    time.sleep(2)

    r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid2, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    status2 = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
    print(f"  修改后查询: status={status2}, {json.dumps(d, ensure_ascii=False)[:200]}")
else:
    print("  没有找到第二个未签到活动，跳过对比测试")

print(f"\n{'=' * 80}")
print(f"测试3: 学生修改后，等待更长时间再查询")
print(f"{'=' * 80}")

# 找第三个未签到活动
target_aid3 = None
for act in active_list:
    aid3 = str(act.get("id", ""))
    atype = act.get("activeType", -1)
    if atype not in (2, 74) or aid3 in (aid, target_aid2 or ""):
        continue
    r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid3, "uid": puid_s}, timeout=20)
    d = safe_json(r)
    if isinstance(d, dict) and d.get("result") == 1 and d.get("data"):
        status = d["data"].get("status")
        if status is None:
            target_aid3 = aid3
            print(f"找到第三个未签到活动: aid={aid3}")
            break

if target_aid3:
    aid3 = target_aid3
    print(f"\n--- 学生修改后等待10秒 ---")
    r = s_s.post(f"{base}/newsign/updateSignStatus",
                 params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": aid3},
                 data={"uids": puid_s, "status": "1", "remark": "",
                       "activeId": aid3, "classId": CLASS_ID, "courseId": COURSE_ID, "uid": puid_s},
                 headers={"Referer": f"{base}/", "X-Requested-With": "XMLHttpRequest",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 timeout=20)
    print(f"  API返回: {r.text}")

    for i in range(5):
        time.sleep(3)
        r = s_s.get(f"{base}/v2/apis/sign/signIn", params={"activeId": aid3, "uid": puid_s}, timeout=20)
        d = safe_json(r)
        status3 = d.get("data", {}).get("status") if isinstance(d.get("data"), dict) else None
        print(f"  {(i+1)*3}秒后查询: status={status3}")
        if status3 is not None:
            print(f"  🔴 数据已生效！无需教师V2触发！")
            break
else:
    print("  没有找到第三个未签到活动，跳过")

print(f"\n{'=' * 80}")
print(f"结论")
print(f"{'=' * 80}")
print(f"  测试1: 学生修改后教师端直接查询 → status={teacher_status}")
print(f"  测试2: 仅教师V2修改 → 对比")
print(f"  测试3: 学生修改后等待 → 观察是否自动生效")
