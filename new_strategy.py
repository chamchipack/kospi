import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide", page_title="주식 전략 분석기")
st.title("📈 주식 기술적 분석 및 매매 신호 스캐너")

# 1. 사이드바: 전략 설정 및 데이터 옵션
st.sidebar.header("⚙️ 분석 설정")
ticker = st.sidebar.text_input("종목 티커", "034020.KS")
period = st.sidebar.selectbox("데이터 기간", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
interval = st.sidebar.selectbox("봉 단위", ["1d", "60m", "15m", "5m"], index=0)

st.sidebar.header("🛡️ 전략 제어 스위치")
USE_TREND_FILTER = st.sidebar.checkbox("정배열 필터", False)
USE_MACD = st.sidebar.checkbox("MACD 골든크로스", True)
USE_BOLLINGER = st.sidebar.checkbox("볼린저 밴드 돌파", True)
USE_VOLUME_SPIKE = st.sidebar.checkbox("거래량 폭발 필터", True)
USE_RSI_FILTER = st.sidebar.checkbox("RSI 필터", False)
USE_ICHIMOKU_CLOUD = st.sidebar.checkbox("일목균형표 필터", False)

# 2. 데이터 가져오기
stock = yf.Ticker(ticker)
df = stock.history(period=period, interval=interval)

# 3. 지표 계산 (기존 로직 유지)
df["MA20"] = df["Close"].rolling(20).mean()
df["MA60"] = df["Close"].rolling(60).mean()
df["std20"] = df["Close"].rolling(20).std()
df["BB_Upper"] = df["MA20"] + (2 * df["std20"])
exp12, exp26 = df["Close"].ewm(span=12).mean(), df["Close"].ewm(span=26).mean()
df["MACD"] = exp12 - exp26
df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
df["Vol_MA5"] = df["Volume"].rolling(5).mean()
df["RSI"] = 100 - (100 / (1 + (df["Close"].diff().clip(lower=0).rolling(14).mean() / (-df["Close"].diff().clip(upper=0).rolling(14).mean() + 1e-9))))

# 일목균형표
df["tenkan_sen"] = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2
df["kijun_sen"] = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2

# 4. 신호 생성 로직 (매도 로직 포함)
df["signal"] = 0
# 매수/매도 조건 정의
cond_ma_gold = (df["MA20"] > df["MA60"]) & (df["MA20"].shift(1) <= df["MA60"].shift(1))
cond_ma_dead = (df["MA20"] < df["MA60"]) & (df["MA20"].shift(1) >= df["MA60"].shift(1))
cond_macd_gold = (df["MACD"] > df["MACD_Signal"]) & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1))
cond_macd_dead = (df["MACD"] < df["MACD_Signal"]) & (df["MACD"].shift(1) >= df["MACD_Signal"].shift(1))
cond_bb_breakout = (df["Close"] > df["BB_Upper"]) & (df["Close"].shift(1) <= df["BB_Upper"].shift(1))
cond_bb_breakdown = (df["Close"] < df["MA20"]) & (df["Close"].shift(1) >= df["MA20"].shift(1))
cond_volume_burst = df["Volume"] > (df["Vol_MA5"].shift(1) * 1.5)

# 매수 조건
buy_cond = (df["MA20"] > df["MA60"]) if USE_TREND_FILTER else pd.Series(True, index=df.index)
if USE_MACD: buy_cond &= cond_macd_gold
if USE_BOLLINGER: buy_cond &= cond_bb_breakout
if USE_VOLUME_SPIKE: buy_cond &= cond_volume_burst
df.loc[buy_cond, "signal"] = 1

# 매도 조건 (원래 코드의 매도 로직 복원)
sell_cond = cond_ma_dead
if USE_BOLLINGER: sell_cond |= cond_bb_breakdown
if USE_MACD: sell_cond |= cond_macd_dead
df.loc[sell_cond, "signal"] = -1

# 첫 신호 매도 제외
first_idx = df[df["signal"] != 0].index
if not first_idx.empty and df.loc[first_idx[0], "signal"] == -1: df.loc[first_idx[0], "signal"] = 0

# 5. 화면 출력 (한글화 완료)
rename_dict = {"Close": "종가", "tenkan_sen": "전환선", "Volume": "거래량", "Vol_MA5": "5일거래량", "RSI": "RSI", "signal": "신호"}
signals = df[df["signal"] != 0][["Close", "tenkan_sen", "Volume", "RSI", "signal"]].rename(columns=rename_dict)

st.subheader("📊 매매 신호 발생 내역")
st.dataframe(signals.tail(20), use_container_width=True)

st.subheader("📈 최근 지표 추이")
st.line_chart(df[["Close", "tenkan_sen"]].tail(50).rename(columns={"Close": "종가", "tenkan_sen": "전환선"}))
st.dataframe(df.tail(10)[["Close", "tenkan_sen", "Volume", "Vol_MA5", "RSI"]].rename(columns=rename_dict), use_container_width=True)
