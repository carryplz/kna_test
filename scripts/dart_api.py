"""DART OpenAPI 도우미 — .env의 DART_API_KEY를 읽어 호출한다 (키는 출력하지 않음).

사용 예 (프로젝트 루트에서):
  python scripts/dart_api.py check                 # 키 등록 여부 확인
  python scripts/dart_api.py corp 풀무원            # 고유번호(corp_code) 찾기
  python scripts/dart_api.py list 풀무원 A 20260101 # 정기공시(A) 목록
  python scripts/dart_api.py doc 20260323001547    # 공시 원문 zip 저장 (research/data/raw/)
"""
import io, json, os, sys, urllib.parse, urllib.request, zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://opendart.fss.or.kr/api/"


def load_key():
    key = os.environ.get("DART_API_KEY", "")
    path = os.path.join(ROOT, ".env")
    if not key and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("DART_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if len(key) != 40:
        sys.exit("DART_API_KEY가 .env에 없거나 40자리가 아니에요. .env.example을 참고하세요.")
    return key


def get(endpoint, **params):
    params["crtfc_key"] = load_key()
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def corp_codes():
    """corpCode.xml(zip) → [(corp_code, corp_name, stock_code)]. 캐시: research/data/raw/corpCode.xml"""
    cache = os.path.join(ROOT, "research", "data", "raw", "corpCode.xml")
    if not os.path.exists(cache):
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        z = zipfile.ZipFile(io.BytesIO(get("corpCode.xml")))
        open(cache, "wb").write(z.read(z.namelist()[0]))
    root = ET.parse(cache).getroot()
    return [(e.findtext("corp_code"), e.findtext("corp_name"), (e.findtext("stock_code") or "").strip())
            for e in root.iter("list")]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        load_key(); print("DART_API_KEY 확인됨 (값은 표시하지 않음)")
    elif cmd == "corp":
        name = sys.argv[2]
        for c in corp_codes():
            if c[1] == name or (name in c[1] and c[2]):
                print(*c, sep="\t")
    elif cmd == "list":
        name, ty, bgn = sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "A"), (sys.argv[4] if len(sys.argv) > 4 else "20250101")
        code = next(c[0] for c in corp_codes() if c[1] == name)
        d = json.loads(get("list.json", corp_code=code, pblntf_ty=ty, bgn_de=bgn, page_count=100))
        if d.get("status") != "000":
            sys.exit(f"오류 {d.get('status')}: {d.get('message')}")
        for x in d["list"]:
            print(x["rcept_dt"], x["rcept_no"], x["report_nm"], sep="\t")
    elif cmd == "doc":
        rcp = sys.argv[2]
        out = os.path.join(ROOT, "research", "data", "raw", f"dart_{rcp}.zip")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(get("document.xml", rcept_no=rcp))
        print("저장:", os.path.relpath(out, ROOT))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
