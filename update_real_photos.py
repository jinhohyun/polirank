"""
PoliRank - 32인 국회의원 진짜 공식 사진 교체 및 DB 업데이트 스크립트
"""
import re
import os

path = os.path.join(os.path.dirname(__file__), "seed_data.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

real_photos = {
    "박찬대": "https://upload.wikimedia.org/wikipedia/commons/e/eb/Park_Chan-dae%27s_Portrait_%282026.7%29.jpg",
    "추경호": "https://upload.wikimedia.org/wikipedia/commons/f/f6/Choo_Kyung-ho%27s_Portrait_%282024.5%29.png",
    "정청래": "https://www.assembly.go.kr/static/portal/img/openassm/2385336L.jpg",
    "나경원": "https://www.assembly.go.kr/static/portal/img/openassm/SLW27496.jpg",
    "조국": "https://upload.wikimedia.org/wikipedia/commons/c/c3/Cho_Kuk%27s_Portrait_%282024.3%29.png",
    "이준석": "https://www.assembly.go.kr/static/portal/img/openassm/QWL7778X.jpg",
    "용혜인": "https://www.assembly.go.kr/static/portal/img/openassm/GE71932C.jpg",
    "안철수": "https://www.assembly.go.kr/static/portal/img/openassm/YOG1280B.jpg",
    "이재명": "https://upload.wikimedia.org/wikipedia/commons/5/59/President_Lee_Jae_Myung_20260306.jpg",
    "김용태": "https://www.assembly.go.kr/static/portal/img/openassm/EPI69383.jpg",
    "전용기": "https://www.assembly.go.kr/static/portal/img/openassm/TJW93720.jpg",
    "김재섭": "https://www.assembly.go.kr/static/portal/img/openassm/57B28032.jpg",
    "모경종": "https://www.assembly.go.kr/static/portal/img/openassm/J1G57517.jpg",
    "우원식": "https://www.assembly.go.kr/static/portal/img/openassm/XBT9550Q.jpg",
    "신장식": "https://www.assembly.go.kr/static/portal/img/openassm/NPD75153.jpg",
    "천하람": "https://www.assembly.go.kr/static/portal/img/openassm/YGB8604T.jpg",
    "윤상현": "https://www.assembly.go.kr/static/portal/img/openassm/MSY7784L.jpg",
    "서영교": "https://www.assembly.go.kr/static/portal/img/openassm/TKJ4800F.jpg",
    "배현진": "https://www.assembly.go.kr/static/portal/img/openassm/4X525582.jpg",
    "고민정": "https://www.assembly.go.kr/static/portal/img/openassm/WCD5518S.jpg",
    "박은정": "https://www.assembly.go.kr/static/portal/img/openassm/1A82234K.jpg",
    "윤건영": "https://www.assembly.go.kr/static/portal/img/openassm/GP07421U.jpg",
    "이철규": "https://www.assembly.go.kr/static/portal/img/openassm/TZP9391O.jpg",
    "박지원": "https://www.assembly.go.kr/static/portal/img/openassm/8BF5855P.jpg",
    "엄태영": "https://www.assembly.go.kr/static/portal/img/openassm/8348421R.jpg",
    "위성곤": "https://upload.wikimedia.org/wikipedia/commons/d/d3/%EC%9C%84%EC%84%B1%EA%B3%A4_%EA%B5%AD%ED%9A%8C%EC%9D%98%EC%9B%90.jpg",
    "임이자": "https://www.assembly.go.kr/static/portal/img/openassm/EH27538E.jpg",
    "신정훈": "https://www.assembly.go.kr/static/portal/img/openassm/M7O7878U.jpg",
    "성일종": "https://www.assembly.go.kr/static/portal/img/openassm/7XY7109I.jpg",
    "윤종오": "https://www.assembly.go.kr/static/portal/img/openassm/3TP65086.jpg",
    "한창민": "https://www.assembly.go.kr/static/portal/img/openassm/T4I4862D.jpg",
    "이소영": "https://www.assembly.go.kr/static/portal/img/openassm/WTR5885Y.jpg"
}

success_count = 0
for name, photo in real_photos.items():
    # MEMBER_FUN_AND_EXTRA_DATA 내의 각 의원 블록에서 official_photo 치환
    pattern = rf'("{name}":\s*\{{[^}}]*?"official_photo":\s*")[^"]+(")'
    content, count = re.subn(pattern, rf'\g<1>{photo}\g<2>', content, flags=re.DOTALL)
    if count > 0:
        success_count += count
    else:
        print(f"Warning: Failed to replace for {name}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully replaced {success_count} / {len(real_photos)} official photos in seed_data.py!")

