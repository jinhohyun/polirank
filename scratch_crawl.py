import urllib.request
import json

url = "https://open.assembly.go.kr/portal/openapi/nwvrqwxyaytdsfvhu?Type=json&pIndex=1&pSize=300"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
    rows = data["nwvrqwxyaytdsfvhu"][1]["row"]
    print(f"Total assembly members from open API: {len(rows)}")
    member_img_map = {}
    for r in rows:
        name = r.get("HG_NM")
        link = r.get("BTH_DATE") # or other fields
        # print keys of first row
        member_img_map[name] = r
    print("Sample row keys:", list(rows[0].keys()))
    print("HG_NM sample:", rows[0].get("HG_NM"), "IMG:", rows[0].get("LINK_URL") or rows[0].get("ASSEM_ADDR"))
    
    # Check 32 members
    target_names = ['박찬대', '추경호', '정청래', '나경원', '조국', '이준석', '용혜인', '안철수', '이재명', '김용태', '전용기', '김재섭', '모경종', '우원식', '신장식', '천하람', '윤상현', '서영교', '배현진', '고민정', '박은정', '윤건영', '이철규', '박지원', '엄태영', '위성곤', '임이자', '신정훈', '성일종', '윤종오', '한창민', '이소영']
    for t in target_names:
        found = any(r.get("HG_NM") == t for r in rows)
        matching = [r for r in rows if r.get("HG_NM") == t]
        if matching:
            print(f"{t}: found, keys: {[k for k, v in matching[0].items() if 'jpg' in str(v).lower() or 'http' in str(v).lower()]}")
            for k, v in matching[0].items():
                if 'jpg' in str(v).lower() or 'http' in str(v).lower() or 'img' in str(k).lower() or 'pic' in str(k).lower():
                    print(f"   {k} -> {v}")
except Exception as e:
    print("API Error:", e)
