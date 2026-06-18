import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(layout="wide", page_title="주식 전략 분석기")
st.title("📈 주식 기술적 분석 및 매매 신호 스캐너")

# 1. 사이드바 설정
st.sidebar.header("⚙️ 분석 설정")
ticker_input = st.sidebar.text_input("종목 티커 (예: 005930.KS)", "034020.KS")

period_map = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y"}
interval_map = {"일봉": "1d", "60분봉": "60m", "15분봉": "15m"}

period_kr = st.sidebar.selectbox("데이터 기간", list(period_map.keys()))
interval_kr = st.sidebar.selectbox("봉 단위", list(interval_map.keys()))

st.sidebar.header("🛡️ 전략 제어 스위치")
USE_TREND_FILTER = st.sidebar.checkbox("정배열 필터", False)
USE_MACD = st.sidebar.checkbox("MACD 골든크로스", True)
USE_BOLLINGER = st.sidebar.checkbox("볼린저 밴드 돌파", True)
USE_VOLUME_SPIKE = st.sidebar.checkbox("거래량 폭발 필터", True)

# 2. 데이터 가져오기
try:
    stock = yf.Ticker(ticker_input)
    info = stock.info
    company_name = info.get('longName', '알 수 없는 종목')
    st.subheader(f"종목: {company_name} ({ticker_input})")
    
    df = stock.history(period=period_map[period_kr], interval=interval_map[interval_kr])
    
    # 시간대 변환 및 포맷팅
    df.index = df.index.tz_convert('Asia/Seoul')
    if interval_map[interval_kr] == "1d":
        df.index = df.index.strftime('%Y-%m-%d')
    else:
        df.index = df.index.strftime('%Y-%m-%d %H:%M')
except Exception as e:
    st.error("티커를 확인해주세요.")
    st.stop()

# 3. 지표 계산
df["MA20"] = df["Close"].rolling(20).mean()
df["MA60"] = df["Close"].rolling(60).mean()
df["std20"] = df["Close"].rolling(20).std()
df["BB_Upper"] = df["MA20"] + (2 * df["std20"])
exp12, exp26 = df["Close"].ewm(span=12).mean(), df["Close"].ewm(span=26).mean()
df["MACD"] = exp12 - exp26
df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
df["Vol_MA5"] = df["Volume"].rolling(5).mean()
df["RSI"] = 100 - (100 / (1 + (df["Close"].diff().clip(lower=0).rolling(14).mean() / (-df["Close"].diff().clip(upper=0).rolling(14).mean() + 1e-9))))
df["tenkan_sen"] = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2

# 4. 신호 생성
df["signal"] = 0
cond_macd_gold = (df["MACD"] > df["MACD_Signal"]) & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1))
cond_bb_breakout = (df["Close"] > df["BB_Upper"]) & (df["Close"].shift(1) <= df["BB_Upper"].shift(1))
cond_volume_burst = df["Volume"] > (df["Vol_MA5"].shift(1) * 1.5)

buy_cond = pd.Series(True, index=df.index)
if USE_MACD: buy_cond &= cond_macd_gold
if USE_BOLLINGER: buy_cond &= cond_bb_breakout
if USE_VOLUME_SPIKE: buy_cond &= cond_volume_burst
if USE_TREND_FILTER: buy_cond &= (df["MA20"] > df["MA60"])

df.loc[buy_cond, "signal"] = 1
df.loc[df["Close"] < df["MA20"], "signal"] = -1
df["신호"] = df["signal"].map({1: "매수", -1: "매도", 0: "대기"})

# 5. 화면 출력
rename_dict = {
    "Close": "종가", "tenkan_sen": "전환선", "Volume": "거래량", 
    "Vol_MA5": "5일거래량평균", "RSI": "RSI"
}

st.subheader("📊 매매 신호 발생 내역")
st.dataframe(df.rename(columns=rename_dict)[df["signal"] != 0][["종가", "거래량", "신호"]].tail(10), use_container_width=True)

st.subheader("📈 시세 및 거래량 차트")

# 거래량 막대
st.bar_chart(df["Volume"].tail(50))

# 캔들 차트 그리기 바로 윗줄에 추가하세요
# 1. 색상 결정 컬럼 생성 (True면 상승, False면 하락)
df['is_increasing'] = df['Close'] >= df['Open']

# 1. 비어있는 값 제거 (가장 중요)
df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

# 2. 시가/종가 강제 재정렬
# 혹시라도 데이터가 꼬였을 수 있으니 시가와 종가가 확실히 비교되도록 합니다.

# 2. 색상 리스트 생성
colors = ['red' if x else 'blue' for x in df['is_increasing'].tail(50)]

# 3. 캔들스틱 생성 시 line_color 사용
fig = go.Figure(data=[go.Candlestick(
    x=df.tail(50).index,
    open=df.tail(50)['Open'],
    high=df.tail(50)['High'],
    low=df.tail(50)['Low'],
    close=df.tail(50)['Close'],
    # 🔴 상승일 땐 빨간색, 하락일 땐 파란색으로 개별 지정
    increasing_line_color='red',
    decreasing_line_color='blue',
    name='시세'
)])
# 전환선 추가 (add_trace 사용)
fig.add_trace(go.Scatter(
    x=df.tail(50).index, 
    y=df.tail(50)['tenkan_sen'], 
    mode='lines', 
    name='전환선', 
    line=dict(color='orange', width=2)
))

# 레이아웃 설정
fig.update_layout(xaxis_rangeslider_visible=False, height=500)
st.plotly_chart(fig, use_container_width=True)

# [신규 추가] 최근 10일 상세 지표 출력
st.subheader("📋 최근 10일 상세 데이터")
recent_df = df.tail(10).rename(columns=rename_dict)
st.dataframe(recent_df[["종가", "전환선", "거래량", "5일거래량평균", "RSI"]], use_container_width=True)
