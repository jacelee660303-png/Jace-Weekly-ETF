# -*- coding: utf-8 -*-
"""
KR 한국 ETF Weekly — 데이터 수집 스크립트
개념: N주 = 지난 5×N 영업일 (일봉 기준) · 매일 한국 장 마감 후 자동 업데이트
소스: 네이버 fchart (일봉)
출력: data.json
"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# (코드, 약칭, 정식명, 색상) — 한국 액티브 ETF 12종
ETFS = [
    ("0185L0", "휴머노이드",   "TIME 글로벌휴머노이드로봇액티브",      "#e11d48"),
    ("456600", "글로벌AI",     "TIME 글로벌AI인공지능액티브",          "#2563eb"),
    ("426030", "나스닥100",    "TIME 미국나스닥100액티브",             "#0891b2"),
    ("385720", "코스피",       "TIME 코스피액티브",                    "#16a34a"),
    ("463050", "K바이오",      "TIME K바이오액티브",                   "#14b8a6"),
    ("485810", "글로벌바이오", "TIME 글로벌바이오액티브",              "#84cc16"),
    ("478150", "우주·방산",    "TIME 글로벌우주테크&방산액티브",       "#7c3aed"),
    ("0043Y0", "차이나AI",     "TIME 차이나AI테크액티브",              "#db2777"),
    ("0174B0", "AI메모리",     "KoAct 글로벌AI메모리반도체액티브",     "#d97706"),
    ("482030", "반도체소재",   "KoAct 반도체&2차전지핵심소재액티브",   "#4f46e5"),
    ("487240", "AI전력설비",   "KODEX AI전력핵심설비",                 "#ea580c"),
    ("133690", "TIGER나스닥",  "TIGER 미국나스닥100",                  "#334155"),
]

PERIODS = [2, 4, 6, 8, 10]   # N주 = 5×N 영업일
TREND_DAYS = 51              # 추세 표시: 최근 51개 종가 (= 시작점 + 50영업일)
FETCH_COUNT = 80             # 여유분 포함 일봉 개수


def fetch_daily(code: str, count: int = FETCH_COUNT, retries: int = 2):
    """네이버 fchart 일봉 → [(date_str, close)] 오름차순"""
    url = (f"https://fchart.stock.naver.com/sise.nhn"
           f"?symbol={code}&timeframe=day&count={count}&requestType=0")
    last_err = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=20).read()
            text = raw.decode("euc-kr", errors="ignore")
            root = ET.fromstring(text)
            rows = []
            for it in root.iter("item"):
                f = it.attrib.get("data", "").split("|")
                if len(f) >= 5 and f[4]:
                    d = f[0]  # YYYYMMDD
                    rows.append((f"{d[:4]}-{d[4:6]}-{d[6:8]}", float(f[4])))
            rows.sort(key=lambda x: x[0])
            if rows:
                return rows
            last_err = "empty rows"
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"{code}: fchart 수집 실패 ({last_err})")


def pct(cur: float, prev: float):
    return round((cur / prev - 1) * 100, 1)


def build():
    etfs_out = []
    latest_date = None

    for code, short, name, color in ETFS:
        try:
            rows = fetch_daily(code)
        except RuntimeError as e:
            print(f"[WARN] {e} — 해당 종목 제외")
            continue

        closes = [c for _, c in rows]
        dates = [d for d, _ in rows]
        days = len(closes)
        cur = closes[-1]
        asof = dates[-1]
        if latest_date is None or asof > latest_date:
            latest_date = asof

        item = {
            "code": code, "short": short, "name": name, "color": color,
            "cur": cur, "asof": asof,
            "days": days, "weeks": days // 5,
            "new": days < 30,  # 자료 6주(30영업일) 미만 → NEW 표시
        }
        for n in PERIODS:
            k = 5 * n
            item[f"r{n}"] = pct(cur, closes[-1 - k]) if days > k else None

        # 추세: 최근 TREND_DAYS개 일별 종가, 표시 시작 = 100
        t = rows[-TREND_DAYS:]
        base = t[0][1]
        item["trend"] = [{"d": d, "idx": round(c / base * 100, 2)} for d, c in t]

        etfs_out.append(item)
        print(f"[OK] {code} {short}: {days}일, cur={cur:,.0f}, "
              f"r2={item['r2']}, r10={item['r10']}, asof={asof}")

    out = {
        "date": latest_date,
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "source": "Naver (fchart, daily)",
        "concept": "N주 = 지난 5×N 영업일",
        "currency": "KRW",
        "count": len(etfs_out),
        "etfs": etfs_out,
    }
    with open("kr-weekly-data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nkr-weekly-data.json 생성 완료: {len(etfs_out)}종, 기준일 {latest_date}")


if __name__ == "__main__":
    build()
