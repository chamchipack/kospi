import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(layout="wide", page_title="주식 전략 분석기")
st.subheader("📈 주식 기술적 분석 및 매매 신호 스캐너")

# 1. 상단 제어 영역
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    ticker_input = st.text_input("종목 티커 입력 (예: 005930.KS)", "034020.KS")
with col2:
    period_kr = st.selectbox("데이터 기간", ["1개월", "3개월", "6개월", "1년"])
with col3:
    interval_kr = st.selectbox("봉 단위", ["일봉", "60분봉", "15분봉"])

st.markdown("##### 🛡️ 필터 설정")
col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
with col_s1: USE_TREND_FILTER = st.checkbox("정배열 필터", False)
with col_s2: USE_MACD = st.checkbox("MACD 골든크로스", True)
with col_s3: USE_BOLLINGER = st.checkbox("볼린저 밴드 돌파", True)
with col_s4: USE_VOLUME_SPIKE = st.checkbox("거래량 폭발 필터", True)
with col_s5: USE_ICHIMOKU_CLOUD = st.checkbox("일목구름대 필터", False) # ☁️ 추가
st.markdown("---")

# 데이터 매핑
period_map = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y"}
interval_map = {"일봉": "1d", "60분봉": "60m", "15분봉": "15m"}

# 2. 데이터 가져오기
try:
    stock = yf.Ticker(ticker_input)
    company_name = stock.info.get('longName', '알 수 없는 종목')
    st.subheader(f"📊 {company_name} ({ticker_input})")

    df = stock.history(period=period_map[period_kr], interval=interval_map[interval_kr])
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

# 일목균형표 계산
df["tenkan_sen"] = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2
kijun_sen = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2
df["senkou_span_a"] = ((df["tenkan_sen"] + kijun_sen) / 2).shift(26)
df["senkou_span_b"] = ((df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2).shift(26)
df["Cloud_Top"] = df[["senkou_span_a", "senkou_span_b"]].max(axis=1)
df["Cloud_Bottom"] = df[["senkou_span_a", "senkou_span_b"]].min(axis=1)

# 4. 신호 생성
df["signal"] = 0
cond_macd_gold = (df["MACD"] > df["MACD_Signal"]) & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1))
cond_bb_breakout = (df["Close"] > df["BB_Upper"]) & (df["Close"].shift(1) <= df["BB_Upper"].shift(1))
cond_volume_burst = df["Volume"] > (df["Vol_MA5"].shift(1) * 1.5)
cond_above_cloud = df["Close"] > df["Cloud_Top"] # 구름대 상단 돌파

buy_cond = pd.Series(True, index=df.index)
if USE_MACD: buy_cond &= cond_macd_gold
if USE_BOLLINGER: buy_cond &= cond_bb_breakout
if USE_VOLUME_SPIKE: buy_cond &= cond_volume_burst
if USE_TREND_FILTER: buy_cond &= (df["MA20"] > df["MA60"])
if USE_ICHIMOKU_CLOUD: buy_cond &= cond_above_cloud # 구름대 필터 적용

df.loc[buy_cond, "signal"] = 1
# 매도 조건: 이동평균선 데드크로스 또는 구름대 하향 이탈
sell_cond = (df["Close"] < df["MA20"])
if USE_ICHIMOKU_CLOUD: sell_cond |= (df["Close"] < df["Cloud_Bottom"])
df.loc[sell_cond, "signal"] = -1

df["신호"] = df["signal"].map({1: "매수", -1: "매도", 0: "-"})

# 5. 화면 출력
st.markdown("##### 📊 매매 신호 발생 내역")
st.dataframe(df.rename(columns={"Close":"종가"})[df["signal"] != 0][["종가", "신호"]].tail(10), use_container_width=True)

st.markdown("##### 📈 시세 및 거래량 차트")
st.bar_chart(df["Volume"].tail(50))
df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
fig = go.Figure(data=[go.Candlestick(x=df.tail(50).index, open=df.tail(50)['Open'], high=df.tail(50)['High'], low=df.tail(50)['Low'], close=df.tail(50)['Close'], increasing_line_color='red', decreasing_line_color='blue')])
fig.add_trace(go.Scatter(x=df.tail(50).index, y=df.tail(50)['tenkan_sen'], mode='lines', name='전환선', line=dict(color='orange', width=2)))
fig.add_trace(go.Scatter(x=df.tail(50).index, y=df.tail(50)['Cloud_Top'], mode='lines', name='구름상단', line=dict(color='gray', width=1, dash='dot'))) # ☁️ 추가
fig.update_layout(xaxis_rangeslider_visible=False, height=400)
st.plotly_chart(fig, use_container_width=True)

# 6. 최근 10일 상세 데이터
st.markdown("##### 📋 최근 10일 상세 지표 및 매매 신호")
recent_df = df.tail(10).copy()
recent_df['상태'] = recent_df.apply(lambda row: '▲ 양봉' if row['Close'] > row['Open'] else ('▼ 음봉' if row['Close'] < row['Open'] else '— 보합'), axis=1)
display_df = recent_df.rename(columns={"Open":"시가", "Close":"종가", "tenkan_sen":"전환선", "Volume":"거래량", "RSI":"RSI"})
st.dataframe(display_df[["시가", "종가", "거래량", "RSI", "상태", "신호"]], use_container_width=True)