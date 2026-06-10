import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import requests
 
# ──────────────────────────────────────────
# 설정값
# ──────────────────────────────────────────
TIGER_TICKER = "133690.KS"
QQQ_TICKER   = "QQQ"
VWO_TICKER   = "VWO"
BND_TICKER   = "BND"
TIP_TICKER   = "TIP"
VIX_TICKER   = "^VIX"
OUTPUT_FILE  = "index.html"
 
# ──────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────
def get_price_data(ticker, period="400d"):
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return pd.Series(dtype=float), None
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna()
        # 마지막 데이터 날짜
        last_date = close.index[-1]
        if hasattr(last_date, 'strftime'):
            last_date_str = last_date.strftime("%Y-%m-%d")
        else:
            last_date_str = str(last_date)[:10]
        return close, last_date_str
    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return pd.Series(dtype=float), None
 
def safe_float(val):
    if val is None:
        return None
    if isinstance(val, (pd.Series, pd.DataFrame)):
        val = val.iloc[-1] if len(val) > 0 else None
    if val is None:
        return None
    try:
        return float(val)
    except:
        return None
 
def momentum_score(series):
    try:
        if len(series) < 252:
            return None
        p0   = safe_float(series.iloc[-1])
        p1m  = safe_float(series.iloc[-21])
        p3m  = safe_float(series.iloc[-63])
        p6m  = safe_float(series.iloc[-126])
        p12m = safe_float(series.iloc[-252])
        if None in [p0, p1m, p3m, p6m, p12m]:
            return None
        score = (p0/p1m-1)*12 + (p0/p3m-1)*4 + (p0/p6m-1)*2 + (p0/p12m-1)*1
        return round(score * 100, 1)
    except Exception as e:
        print(f"[momentum_score error] {e}")
        return None
 
def momentum_detail(series):
    """VAA 기간별 수익률 상세"""
    try:
        p0   = safe_float(series.iloc[-1])
        p1m  = safe_float(series.iloc[-21])
        p3m  = safe_float(series.iloc[-63])
        p6m  = safe_float(series.iloc[-126])
        p12m = safe_float(series.iloc[-252])
        return {
            "1M" : round((p0/p1m-1)*100, 1) if p1m else None,
            "3M" : round((p0/p3m-1)*100, 1) if p3m else None,
            "6M" : round((p0/p6m-1)*100, 1) if p6m else None,
            "12M": round((p0/p12m-1)*100, 1) if p12m else None,
        }
    except:
        return {}
 
def sma(series, window):
    try:
        if len(series) < window:
            return None
        val = series.rolling(window).mean().iloc[-1]
        return round(safe_float(val), 2)
    except:
        return None
 
def rsi(series, period=14):
    try:
        delta = series.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss
        r     = 100 - (100 / (1 + rs))
        return round(safe_float(r.iloc[-1]), 1)
    except:
        return None
 
def macd(series, fast=12, slow=26, signal=9):
    try:
        ema_fast    = series.ewm(span=fast, adjust=False).mean()
        ema_slow    = series.ewm(span=slow, adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram   = macd_line - signal_line
        return (
            round(safe_float(macd_line.iloc[-1]), 1),
            round(safe_float(signal_line.iloc[-1]), 1),
            round(safe_float(histogram.iloc[-1]), 1)
        )
    except:
        return (None, None, None)
 
def get_cnn_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        score  = data["fear_and_greed"]["score"]
        rating = data["fear_and_greed"]["rating"]
        return round(float(score), 1), rating
    except:
        return None, "N/A"
 
def recent_return(series, days):
    try:
        if len(series) < days + 1:
            return None
        p_now  = safe_float(series.iloc[-1])
        p_prev = safe_float(series.iloc[-days])
        return round((p_now / p_prev - 1) * 100, 2)
    except:
        return None
 
# ──────────────────────────────────────────
# 시그널 판정
# ──────────────────────────────────────────
def evaluate_signals(qqq, vwo, bnd, tip, qqq_date, vwo_date, bnd_date, tip_date):
    signals = {}
 
    qqq_price = safe_float(qqq.iloc[-1])
    qqq_200   = sma(qqq, 200)
    qqq_120   = sma(qqq, 120)
    qqq_50    = sma(qqq, 50)
    qqq_20    = sma(qqq, 20)
    trend_ok  = (qqq_price > qqq_200) if (qqq_price and qqq_200) else None
 
    # 이평선 대비 괴리율
    def gap_pct(price, ma):
        if price and ma:
            return round((price/ma - 1)*100, 1)
        return None
 
    signals["trend"] = {
        "price"   : round(qqq_price, 1) if qqq_price else None,
        "sma20"   : qqq_20,
        "sma50"   : qqq_50,
        "sma120"  : qqq_120,
        "sma200"  : qqq_200,
        "gap20"   : gap_pct(qqq_price, qqq_20),
        "gap50"   : gap_pct(qqq_price, qqq_50),
        "gap120"  : gap_pct(qqq_price, qqq_120),
        "gap200"  : gap_pct(qqq_price, qqq_200),
        "ok"      : trend_ok,
        "date"    : qqq_date,
        "label"   : "✅ 200일선 위 (안전)" if trend_ok else "🚨 200일선 이탈 (위험)"
    }
 
    vaa_score  = momentum_score(qqq)
    vaa_detail = momentum_detail(qqq)
    vaa_ok     = (vaa_score > 0) if vaa_score is not None else None
    signals["vaa"] = {
        "score" : vaa_score,
        "detail": vaa_detail,
        "ok"    : vaa_ok,
        "date"  : qqq_date,
        "label" : f"✅ 모멘텀 양호 ({vaa_score:+.1f})" if vaa_ok else f"🚨 모멘텀 약화 ({vaa_score:+.1f})" if vaa_score is not None else "⚠️ 데이터 부족"
    }
 
    vwo_ret  = recent_return(vwo, 21)
    bnd_ret  = recent_return(bnd, 21)
    daa_warn = (vwo_ret is not None and vwo_ret < 0) or (bnd_ret is not None and bnd_ret < 0)
    signals["daa"] = {
        "vwo_ret" : vwo_ret,
        "bnd_ret" : bnd_ret,
        "warn"    : daa_warn,
        "vwo_date": vwo_date,
        "bnd_date": bnd_date,
        "label"   : "🚨 카나리아 경고 (50% 현금화)" if daa_warn else "✅ 카나리아 정상"
    }
 
    tip_price  = safe_float(tip.iloc[-1])
    tip_sma12m = sma(tip, 252)
    haa_ok     = (tip_price > tip_sma12m) if (tip_price and tip_sma12m) else None
    signals["haa"] = {
        "price"  : round(tip_price, 2) if tip_price else None,
        "sma252" : tip_sma12m,
        "ok"     : haa_ok,
        "date"   : tip_date,
        "label"  : "✅ TIP 이평선 위 (안전)" if haa_ok else "🚨 TIP 이평선 이탈"
    }
 
    return signals
 
def cash_recommendation(signals):
    danger = 0
    if signals["trend"]["ok"] is False: danger += 2
    if signals["vaa"]["ok"]   is False: danger += 2
    if signals["daa"]["warn"]          : danger += 1
    if signals["haa"]["ok"]   is False: danger += 1
 
    if danger == 0:   return 0,   "● 완전 투자",          "green"
    elif danger <= 1: return 25,  "🟡 현금 25% 확보 권고", "gold"
    elif danger <= 2: return 50,  "🟠 현금 50% 확보 권고", "orange"
    elif danger <= 3: return 75,  "🔴 현금 75% 확보 권고", "red"
    else:             return 100, "🔴 전액 현금 전환 권고", "darkred"
 
# ──────────────────────────────────────────
# HTML 생성
# ──────────────────────────────────────────
def build_html(signals, tiger_rsi, tiger_macd, vix_price,
               fear_score, fear_rating,
               tiger_price, tiger_sma20, tiger_sma60,
               tiger_date, vix_date, generated_at, run_timestamp):
 
    cash_pct, cash_label, cash_color = cash_recommendation(signals)
    macd_line, macd_sig, macd_hist = tiger_macd
    macd_trend = "상승 ▲" if macd_hist and macd_hist > 0 else "하락 ▼"
 
    def fmt(v, suffix="", digits=1):
        if v is None: return "<span style='color:#555'>N/A</span>"
        return f"{v:,.{digits}f}{suffix}"
 
    def pct_span(v):
        if v is None: return "<span style='color:#555'>N/A</span>"
        color = "#2ecc71" if v > 0 else "#e74c3c"
        arrow = "▲" if v > 0 else "▼"
        return f"<span style='color:{color}'>{arrow}{abs(v):.1f}%</span>"
 
    def date_badge(d):
        if not d: return ""
        return f"<span style='font-size:0.75rem;color:#8b949e;margin-left:6px'>({d} 기준)</span>"
 
    rsi_width = min(tiger_rsi or 50, 100)
    rsi_color = '#e74c3c' if tiger_rsi and tiger_rsi > 70 else '#2ecc71' if tiger_rsi and tiger_rsi < 30 else '#f0a500'
    rsi_label = '⚠️ 과매수 (>70)' if tiger_rsi and tiger_rsi > 70 else '✅ 과매도 (<30)' if tiger_rsi and tiger_rsi < 30 else '중립 구간'
    vix_color = '#e74c3c' if vix_price and vix_price > 30 else '#f0a500' if vix_price and vix_price > 20 else '#2ecc71'
    vix_label = '🔴 극도의 공포 (>30)' if vix_price and vix_price > 30 else '🟠 공포 구간 (>20)' if vix_price and vix_price > 20 else '🟢 안정 구간'
    fear_color= '#e74c3c' if fear_score and fear_score < 25 else '#2ecc71' if fear_score and fear_score > 75 else '#f0a500'
 
    vaa_detail = signals["vaa"].get("detail", {})
    def vaa_row(period, wt):
        v = vaa_detail.get(period)
        contrib = round(v * wt, 1) if v is not None else None
        return f"""<tr>
          <td style='padding:5px 10px'>{period}</td>
          <td style='padding:5px 10px'>{pct_span(v)}</td>
          <td style='padding:5px 10px;color:#8b949e'>x{wt}</td>
          <td style='padding:5px 10px'>{pct_span(contrib)}</td>
        </tr>"""
 
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="3600">
<title>나스닥100 시그널 리포트</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif;font-size:14px;padding:16px;max-width:900px;margin:0 auto}}
  h1{{font-size:1.4rem;margin-bottom:4px}}
  h2{{font-size:1rem;color:#8b949e;margin:20px 0 8px;border-bottom:1px solid #21262d;padding-bottom:5px;display:flex;align-items:center;gap:8px}}
  .card{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px;margin-bottom:14px}}
  .cash-box{{background:{cash_color}18;border:2px solid {cash_color};border-radius:12px;padding:20px;text-align:center;margin-bottom:16px}}
  .cash-pct{{font-size:2.8rem;font-weight:800;color:{cash_color}}}
  .cash-label{{font-size:1.1rem;margin-top:4px;color:{cash_color}}}
  table{{width:100%;border-collapse:collapse}}
  td{{border-bottom:1px solid #21262d;vertical-align:middle}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  .metric{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px}}
  .metric-label{{color:#8b949e;font-size:0.8rem;margin-bottom:3px}}
  .metric-value{{font-size:1.2rem;font-weight:700}}
  .ts{{color:#8b949e;font-size:0.78rem;margin-top:3px}}
  .bar-bg{{background:#21262d;border-radius:4px;height:8px;margin-top:5px}}
  .bar{{background:{rsi_color};border-radius:4px;height:8px;width:{rsi_width}%}}
  .badge{{display:inline-block;background:#21262d;border-radius:4px;padding:1px 7px;font-size:0.75rem;color:#8b949e}}
  .ma-grid{{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}}
  .ma-chip{{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:4px 10px;font-size:0.8rem;text-align:center}}
  .refresh-btn{{background:#21262d;border:1px solid #30363d;color:#e6edf3;border-radius:6px;padding:4px 12px;cursor:pointer;font-size:0.8rem}}
  .refresh-btn:hover{{background:#30363d}}
  @media(max-width:600px){{.grid2{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
 
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div>
      <h1>📊 나스닥100 현금전환 시그널 리포트</h1>
      <p class="ts">스크립트 실행: {run_timestamp} &nbsp;|&nbsp; 데이터 기준: 직전 영업일 종가</p>
    </div>
    <button class="refresh-btn" onclick="location.reload()">🔄 새로고침</button>
  </div>
</div>
 
<div class="cash-box">
  <div style="font-size:0.9rem;color:#8b949e;margin-bottom:6px">▣ 권고 현금 비중</div>
  <div class="cash-pct">{cash_pct}%</div>
  <div class="cash-label">{cash_label}</div>
</div>
 
<!-- ① 4대 시그널 -->
<h2>① VAA / DAA / HAA 4대 카나리아 시그널</h2>
 
<!-- 추세 -->
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <strong>추세 (Trend)</strong>
    <span>{signals['trend']['label']}</span>
  </div>
  <div style="color:#ccc;margin-bottom:6px">
    QQQ 현재가 <strong style="color:#e6edf3">${fmt(signals['trend']['price'])}</strong>
    {date_badge(signals['trend']['date'])}
  </div>
  <div class="ma-grid">
    <div class="ma-chip">
      <div style="color:#8b949e">20일선</div>
      <div>${fmt(signals['trend']['sma20'])}</div>
      <div>{pct_span(signals['trend']['gap20'])}</div>
    </div>
    <div class="ma-chip">
      <div style="color:#8b949e">50일선</div>
      <div>${fmt(signals['trend']['sma50'])}</div>
      <div>{pct_span(signals['trend']['gap50'])}</div>
    </div>
    <div class="ma-chip">
      <div style="color:#8b949e">120일선</div>
      <div>${fmt(signals['trend']['sma120'])}</div>
      <div>{pct_span(signals['trend']['gap120'])}</div>
    </div>
    <div class="ma-chip" style="border-color:{'#2ecc71' if signals['trend']['ok'] else '#e74c3c'}">
      <div style="color:#8b949e">200일선 ★</div>
      <div>${fmt(signals['trend']['sma200'])}</div>
      <div>{pct_span(signals['trend']['gap200'])}</div>
    </div>
  </div>
</div>
 
<!-- VAA -->
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <strong>속도 (VAA)</strong>
    <span>{signals['vaa']['label']}</span>
  </div>
  <div style="color:#ccc;margin-bottom:8px">
    모멘텀 스코어 <strong style="color:{'#2ecc71' if signals['vaa']['ok'] else '#e74c3c'};font-size:1.1rem">{fmt(signals['vaa']['score'])}</strong>
    {date_badge(signals['vaa']['date'])}
    &nbsp;<span style="color:#8b949e;font-size:0.78rem">(공식: 12x1M + 4x3M + 2x6M + 1x12M)</span>
  </div>
  <table style="font-size:0.85rem">
    <tr style="color:#8b949e"><td style="padding:4px 10px">기간</td><td style="padding:4px 10px">수익률</td><td style="padding:4px 10px">가중치</td><td style="padding:4px 10px">기여도</td></tr>
    {vaa_row("1M", 12)}
    {vaa_row("3M", 4)}
    {vaa_row("6M", 2)}
    {vaa_row("12M", 1)}
  </table>
</div>
 
<!-- DAA -->
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <strong>심리 (DAA 카나리아)</strong>
    <span>{signals['daa']['label']}</span>
  </div>
  <table style="font-size:0.85rem">
    <tr>
      <td style="padding:6px 10px;color:#8b949e">VWO (신흥국)</td>
      <td style="padding:6px 10px">{pct_span(signals['daa']['vwo_ret'])} <span style="color:#555;font-size:0.75rem">(21일 수익률)</span></td>
      <td style="padding:6px 10px">{date_badge(signals['daa']['vwo_date'])}</td>
    </tr>
    <tr>
      <td style="padding:6px 10px;color:#8b949e">BND (채권)</td>
      <td style="padding:6px 10px">{pct_span(signals['daa']['bnd_ret'])} <span style="color:#555;font-size:0.75rem">(21일 수익률)</span></td>
      <td style="padding:6px 10px">{date_badge(signals['daa']['bnd_date'])}</td>
    </tr>
  </table>
</div>
 
<!-- HAA -->
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <strong>매크로 (HAA)</strong>
    <span>{signals['haa']['label']}</span>
  </div>
  <div style="color:#ccc;font-size:0.85rem">
    TIP 현재가 <strong>${fmt(signals['haa']['price'])}</strong> &nbsp;/&nbsp;
    12개월 이평 <strong>${fmt(signals['haa']['sma252'])}</strong>
    {date_badge(signals['haa']['date'])}
  </div>
</div>
 
<!-- ② TIGER ETF -->
<h2>② TIGER 미국나스닥100 (133690) 기술지표 {date_badge(tiger_date)}</h2>
<div class="grid2">
  <div class="metric">
    <div class="metric-label">현재가 (직전 영업일 종가)</div>
    <div class="metric-value">₩{fmt(tiger_price)}</div>
    <div class="ts">20일선 ₩{fmt(tiger_sma20)} &nbsp;/&nbsp; 60일선 ₩{fmt(tiger_sma60)}</div>
  </div>
  <div class="metric">
    <div class="metric-label">RSI (14일)</div>
    <div class="metric-value" style="color:{rsi_color}">{fmt(tiger_rsi)}</div>
    <div class="bar-bg"><div class="bar"></div></div>
    <div class="ts">{rsi_label} &nbsp;|&nbsp; 30↓과매도 / 70↑과매수</div>
  </div>
  <div class="metric">
    <div class="metric-label">MACD (12/26/9)</div>
    <div class="metric-value" style="color:{'#2ecc71' if macd_hist and macd_hist>0 else '#e74c3c'}">{fmt(macd_line)}</div>
    <div class="ts">Signal: {fmt(macd_sig)} &nbsp;/&nbsp; Histogram: {fmt(macd_hist)} → {macd_trend}</div>
  </div>
  <div class="metric">
    <div class="metric-label">VIX 공포지수 {date_badge(vix_date)}</div>
    <div class="metric-value" style="color:{vix_color}">{fmt(vix_price)}</div>
    <div class="ts">{vix_label}</div>
  </div>
</div>
 
<!-- ③ CNN -->
<h2>③ CNN 공포탐욕지수 <span style="font-size:0.8rem;color:#555">(실시간)</span></h2>
<div class="card" style="text-align:center">
  <div style="font-size:2.2rem;font-weight:800;color:{fear_color}">{fmt(fear_score)}</div>
  <div style="margin-top:4px;color:#8b949e;text-transform:uppercase">{fear_rating or 'N/A'}</div>
  <div style="margin:10px 0 4px;background:#21262d;border-radius:6px;height:10px;position:relative">
    <div style="background:linear-gradient(90deg,#e74c3c,#f0a500,#2ecc71);border-radius:6px;height:10px"></div>
    <div style="position:absolute;top:-4px;left:{min(fear_score or 50,100)}%;transform:translateX(-50%)">
      <div style="width:4px;height:18px;background:#fff;border-radius:2px;margin:0 auto"></div>
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;color:#555;font-size:0.75rem;margin-top:2px">
    <span>극도의 공포</span><span>중립</span><span>극도의 탐욕</span>
  </div>
</div>
 
<!-- ④ 운용 규칙 -->
<h2>④ 단계별 현금화 운용 규칙</h2>
<div class="card">
<table style="font-size:0.85rem">
  <tr style="background:#1a2a1a">
    <td style="padding:8px 12px;font-weight:600;color:#2ecc71;white-space:nowrap">복귀 조건</td>
    <td style="padding:8px 12px;color:#ccc">모든 시그널 플러스 전환 + QQQ 이평선 상향 안착 확인</td>
  </tr>
  <tr style="background:#2a2a1a">
    <td style="padding:8px 12px;font-weight:600;color:#f0a500;white-space:nowrap">1단계 (50% 현금)</td>
    <td style="padding:8px 12px;color:#ccc">DAA 카나리아 경고 또는 QQQ 50일선 이탈</td>
  </tr>
  <tr style="background:#2a1a1a">
    <td style="padding:8px 12px;font-weight:600;color:#e74c3c;white-space:nowrap">2단계 (100% 현금)</td>
    <td style="padding:8px 12px;color:#ccc">QQQ 200일선 이탈 또는 VAA 모멘텀 마이너스 전환</td>
  </tr>
</table>
</div>
 
<p style="color:#555;font-size:0.75rem;text-align:center;margin-top:16px;line-height:1.8">
  ※ Python 수집: {run_timestamp} &nbsp;|&nbsp; 데이터: Yahoo Finance (직전 영업일 종가), CNN<br>
  ※ 본 리포트는 투자 참고용이며 최종 투자 결정은 본인 책임입니다.
</p>
 
</body>
</html>"""
    return html
 
# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────
def main():
    print("📡 데이터 수집 시작...")
 
    qqq,   qqq_date   = get_price_data(QQQ_TICKER)
    vwo,   vwo_date   = get_price_data(VWO_TICKER)
    bnd,   bnd_date   = get_price_data(BND_TICKER)
    tip,   tip_date   = get_price_data(TIP_TICKER)
    tiger, tiger_date = get_price_data(TIGER_TICKER)
    vix,   vix_date   = get_price_data(VIX_TICKER, period="30d")
 
    print("📊 시그널 계산 중...")
    signals     = evaluate_signals(qqq, vwo, bnd, tip, qqq_date, vwo_date, bnd_date, tip_date)
    tiger_rsi   = rsi(tiger)
    tiger_macd  = macd(tiger)
    tiger_price = safe_float(tiger.iloc[-1]) if len(tiger) > 0 else None
    tiger_sma20 = sma(tiger, 20)
    tiger_sma60 = sma(tiger, 60)
    vix_price   = safe_float(vix.iloc[-1]) if len(vix) > 0 else None
    fear_score, fear_rating = get_cnn_fear_greed()
 
    now           = datetime.utcnow() + timedelta(hours=9)  # KST
    run_timestamp = now.strftime("%Y-%m-%d %H:%M KST")
    generated_at  = now.strftime("%Y년 %m월 %d일 %H:%M")
 
    print("🖊️ HTML 리포트 생성 중...")
    html = build_html(
        signals, tiger_rsi, tiger_macd,
        vix_price, fear_score, fear_rating,
        tiger_price, tiger_sma20, tiger_sma60,
        tiger_date, vix_date,
        generated_at, run_timestamp
    )
 
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 완료: {OUTPUT_FILE} | 실행시각: {run_timestamp}")
 
if __name__ == "__main__":
    main()
 
