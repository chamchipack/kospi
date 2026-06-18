import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 웹 페이지 설정
st.set_page_config(layout="wide", page_title="주식 전략 분석기")
st.title("📈 주식 기술적 분석 및 매매 신호 스캐너")

# 1. 사이드바 제어 스위치
st.sidebar.header("⚙️ 전략 제어 스위치")
USE_TREND_FILTER = st.sidebar.checkbox("정배열 필터 (MA20 > MA60)", True)
USE_MACD = st.sidebar.checkbox("MACD 골든크로스", True)
USE_BOLLINGER = st.sidebar.checkbox("볼린저 밴드 상단 돌파", True)
USE_VOLUME_SPIKE = st.sidebar.checkbox("거래량 폭발 필터", True)
USE_ICHIMOKU_CLOUD = st.sidebar.checkbox("일목균형표 구름대 필터", False)

# 2. 종목 입력
ticker = st.text_input("종목 티커 입력 (예: 005930.KS, AAPL)", "004170.KS")
stock = yf.Ticker(ticker)
df = stock.history(period="1y")

# 3. 기술적 지표 계산 로직 (기존 로직과 동일)
df["MA20"] = df["Close"].rolling(window=20).mean()
df["MA60"] = df["Close"].rolling(window=60).mean()
df["std20"] = df["Close"].rolling(window=20).std()
df["BB_Upper"] = df["MA20"] + (2 * df["std20"])
exp12 = df["Close"].ewm(span=12, adjust=False).mean()
exp26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = exp12 - exp26
df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
df["Vol_MA5"] = df["Volume"].rolling(window=5).mean()
df["RSI"] = 100 - (100 / (1 + (df["Close"].diff().where(df["Close"].diff() > 0, 0).rolling(14).mean() / (-df["Close"].diff().where(df["Close"].diff() < 0, 0).rolling(14).mean() + 1e-9))))

# 일목균형표
nine_high = df["High"].rolling(window=9).max()
nine_low = df["Low"].rolling(window=9).min()
df["tenkan_sen"] = (nine_high + nine_low) / 2
df["kijun_sen"] = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2
df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)
df["senkou_span_b"] = ((df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2).shift(26)

# 4. 신호 생성 (매수/매도 로직)
df["signal"] = 0
cond_ma_gold = (df["MA20"] > df["MA60"]) & (df["MA20"].shift(1) <= df["MA60"].shift(1))
cond_macd_gold = (df["MACD"] > df["MACD_Signal"]) & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1))
cond_bb_breakout = (df["Close"] > df["BB_Upper"]) & (df["Close"].shift(1) <= df["BB_Upper"].shift(1))
cond_volume_burst = df["Volume"] > (df["Vol_MA5"].shift(1) * 1.5)

# 매수 조건
buy_cond = (df["MA20"] > df["MA60"] if USE_TREND_FILTER else True)
if USE_MACD: buy_cond &= cond_macd_gold
if USE_BOLLINGER: buy_cond &= cond_bb_breakout
if USE_VOLUME_SPIKE: buy_cond &= cond_volume_burst
df.loc[buy_cond, "signal"] = 1

# 5. 화면 출력
# st.subheader(f"{ticker} 분석 결과")
# signals = df[df["signal"] != 0][["Close", "tenkan_sen", "Volume", "RSI", "signal"]]
# st.dataframe(signals.tail(10))

# st.subheader("최근 10일 상세 지표")
# st.line_chart(df[["Close", "tenkan_sen"]].tail(30))
# st.dataframe(df.tail(10)[["Close", "tenkan_sen", "Volume", "Vol_MA5", "RSI"]])

# ===== 5. 화면 출력 부분 수정 =====
st.subheader(f"{ticker} 분석 결과")

# 한글 매핑 딕셔너리 생성
rename_dict = {
    "Close": "종가",
    "tenkan_sen": "전환선",
    "Volume": "거래량",
    "Vol_MA5": "5일거래량평균",
    "RSI": "RSI",
    "signal": "매매신호"
}

# 1. 매매 신호 표 한글화
signals = df[df["signal"] != 0][["Close", "tenkan_sen", "Volume", "RSI", "signal"]]
signals = signals.rename(columns=rename_dict)
st.dataframe(signals.tail(10))

# 2. 상세 지표 표 한글화
st.subheader("최근 10일 상세 지표")
df_recent = df.tail(10)[["Close", "tenkan_sen", "Volume", "Vol_MA5", "RSI"]]
df_recent = df_recent.rename(columns=rename_dict)
st.dataframe(df_recent)

# 3. 차트 컬럼명도 맞춰주기 (차트 상단 범례가 한글로 표시됨)
chart_df = df[["Close", "tenkan_sen"]].tail(30).rename(columns={"Close": "종가", "tenkan_sen": "전환선"})
st.line_chart(chart_df)