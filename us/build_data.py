# -*- coding: utf-8 -*-
"""
미국 ETF (Weekly) — 영업일 롤링 1~7주 수익률 데이터 생성
- 매일 미국 장 마감 후 실행 (GitHub Actions)
- N주 수익률 = 최신 종가 vs 5×N 영업일 전 종가 (1주=5영업일 ... 7주=35영업일)
- trend = 최근 35영업일 일별 지수 (시작=100)
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

ETFS = [
    ("QQQ",  "Nasdaq 100",          "#1e40af"),
    ("SOXX", "Semiconductor",       "#7c3aed"),
    ("DRAM", "Memory (Roundhill)",  "#be185d"),
    ("EWY",  "Korea (MSCI)",        "#dc2626"),
    ("GLD",  "Gold",                "#ca8a04"),
    ("IEF",  "7-10Y Treasury",      "#0e7490"),
    ("MSTR", "MicroStrategy",       "#f7931a"),
]

WEEKS = range(1, 8)      # 1~7주 (N주 = 5*N 영업일 전 대비)
TREND_DAYS = 35          # 추세 차트: 최근 35영업일 (= 7주)


def main():
    tickers = [t for t, _, _ in ETFS]
    raw = yf.download(
        tickers, period="90d", interval="1d",
        auto_adjust=True, progress=False,
    )["Close"]

    etfs_out, latest_dates = [], []

    for tk, name, color in ETFS:
        s = raw[tk].dropna()
        if len(s) < 6:
            print(f"[WARN] {tk}: 데이터 부족({len(s)}행) — 건너뜀")
            continue

        closes = [float(v) for v in s.values]
        dates = [d.date().isoformat() for d in s.index]
        cur = closes[-1]
        n = len(closes)

        # N주 수익률 = 5N 영업일 전 종가 대비 (데이터 부족 시 None)
        rets = {}
        for w in WEEKS:
            back = 5 * w
            if n - 1 - back >= 0:
                rets[f"r{w}"] = round((cur / closes[-1 - back] - 1) * 100, 1)
            else:
                rets[f"r{w}"] = None

        # 추세: 최근 35영업일 일별 지수화 (시작=100)
        tp = closes[-(TREND_DAYS + 1):]
        td = dates[-(TREND_DAYS + 1):]
        base = tp[0]
        trend = [{"d": d, "idx": round(c / base * 100, 1)} for d, c in zip(td, tp)]

        etfs_out.append({
            "ticker": tk, "name": name, "color": color,
            "cur": round(cur, 2), **rets, "trend": trend,
        })
        latest_dates.append(dates[-1])
        print(f"OK {tk}: 1주={rets['r1']} 7주={rets['r7']}")

    if not etfs_out:
        raise SystemExit("[ERROR] 수집 종목 없음")

    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    out = {
        "date": max(latest_dates),
        "generated_at": now_kst.strftime("%Y-%m-%d %H:%M KST"),
        "etfs": etfs_out,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"완료: {len(etfs_out)}종 · 기준일 {out['date']} · 생성 {out['generated_at']}")


if __name__ == "__main__":
    main()
