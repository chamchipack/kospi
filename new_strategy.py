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
    ticker_input = st.text_input("종목 티커 입력 (예: 005930.KS)", "009150.KS")
with col2:
    period_kr = st.selectbox("데이터 기간", ["1개월", "3개월", "6개월", "1년"], index=3)
with col3:
    interval_kr = st.selectbox("봉 단위", ["일봉", "60분봉", "15분봉"])

st.markdown("##### 🛡️ 필터 설정")
col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns(6)
with col_s1: USE_TREND_FILTER = st.checkbox("정배열 필터", False)
with col_s2: USE_MACD = st.checkbox("MACD 골든크로스", True)
with col_s3: USE_BOLLINGER = st.checkbox("볼린저 밴드 돌파", False)
with col_s4: USE_VOLUME_SPIKE = st.checkbox("거래량 폭발 필터", False)
with col_s5: USE_RSI_FILTER = st.checkbox("RSI 필터", False)
with col_s6: USE_ICHIMOKU_CLOUD = st.checkbox("일목구름대 필터", False)
st.markdown("---")

# 데이터 매핑
period_map = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y"}
interval_map = {"일봉": "1d", "60분봉": "60m", "15분봉": "15m"}

# 2. 데이터 가져오기
# [원본 로직 유지] 인덱스를 문자열로 바꾸지 않음 -> rolling/shift 계산이 시간 순서 기준으로 정확히 동작
try:
    stock = yf.Ticker(ticker_input)
    company_name = stock.info.get('longName', '알 수 없는 종목')
    st.subheader(f"📊 {company_name} ({ticker_input})")

    df = stock.history(period=period_map[period_kr], interval=interval_map[interval_kr])
    df.index = df.index.tz_convert('Asia/Seoul')  # 시간대만 변환, 문자열 변환은 화면 표시 시점에만 적용
    pd.options.display.float_format = '{:.2f}'.format
except Exception as e:
    st.error("티커를 확인해주세요.")
    st.stop()

# ===== 1. 기존 기술적 지표 계산 (원본과 동일) =====
df["MA20"] = df["Close"].rolling(window=20).mean()
df["MA60"] = df["Close"].rolling(window=60).mean()

df["std20"] = df["Close"].rolling(window=20).std()
df["BB_Upper"] = df["MA20"] + (2 * df["std20"])

exp12 = df["Close"].ewm(span=12, adjust=False).mean()
exp26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = exp12 - exp26
df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

# ===== 2. 거래량 및 RSI 계산 (원본과 동일) =====
df["Vol_MA5"] = df["Volume"].rolling(window=5).mean()

delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / (loss + 1e-9)
df["RSI"] = 100 - (100 / (1 + rs))

# ===== 3. 일목균형표 구름대 계산 (원본과 동일) =====
nine_high = df["High"].rolling(window=9).max()
nine_low = df["Low"].rolling(window=9).min()
df["tenkan_sen"] = (nine_high + nine_low) / 2

twentysix_high = df["High"].rolling(window=26).max()
twentysix_low = df["Low"].rolling(window=26).min()
df["kijun_sen"] = (twentysix_high + twentysix_low) / 2

df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)

fiftytwo_high = df["High"].rolling(window=52).max()
fiftytwo_low = df["Low"].rolling(window=52).min()
df["senkou_span_b"] = ((fiftytwo_high + fiftytwo_low) / 2).shift(26)

df["Cloud_Top"] = np.where(df["senkou_span_a"] > df["senkou_span_b"], df["senkou_span_a"], df["senkou_span_b"])
df["Cloud_Bottom"] = np.where(df["senkou_span_a"] < df["senkou_span_b"], df["senkou_span_a"], df["senkou_span_b"])

# ===== 4. 매매 신호(Signal) 계산 (원본과 동일) =====
df["signal"] = 0

cond_ma_gold   = (df["MA20"] > df["MA60"]) & (df["MA20"].shift(1) <= df["MA60"].shift(1))
cond_ma_dead   = (df["MA20"] < df["MA60"]) & (df["MA20"].shift(1) >= df["MA60"].shift(1))

cond_macd_gold = (df["MACD"] > df["MACD_Signal"]) & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1))
cond_macd_dead = (df["MACD"] < df["MACD_Signal"]) & (df["MACD"].shift(1) >= df["MACD_Signal"].shift(1))

cond_bb_breakout = (df["Close"] > df["BB_Upper"]) & (df["Close"].shift(1) <= df["BB_Upper"].shift(1))
cond_bb_breakdown = (df["Close"] < df["MA20"]) & (df["Close"].shift(1) >= df["MA20"].shift(1))

cond_volume_burst = df["Volume"] > (df["Vol_MA5"].shift(1) * 1.5)
cond_rsi_overbought = df["RSI"] >= 70
cond_rsi_oversold   = df["RSI"] <= 35

# ----- [A] 매수 조건 조립 (트리거/필터 분리 로직 그대로 이식) -----
if USE_TREND_FILTER:
    final_buy_condition = df["MA20"] > df["MA60"]
else:
    final_buy_condition = pd.Series(True, index=df.index)

if USE_MACD and USE_BOLLINGER:
    trigger = cond_macd_gold | cond_bb_breakout
    filter_cond = (df["MACD"] > df["MACD_Signal"]) & (df["Close"] >= df["MA20"])
    final_buy_condition = final_buy_condition & trigger & filter_cond
elif USE_MACD:
    final_buy_condition = final_buy_condition & cond_macd_gold
elif USE_BOLLINGER:
    final_buy_condition = final_buy_condition & cond_bb_breakout
else:
    final_buy_condition = cond_ma_gold

if USE_VOLUME_SPIKE:
    final_buy_condition = final_buy_condition & cond_volume_burst

if USE_RSI_FILTER:
    final_buy_condition = final_buy_condition | (cond_rsi_oversold & (df["Close"] >= df["MA60"]))

if USE_ICHIMOKU_CLOUD:
    cond_above_cloud = df["Close"] > df["Cloud_Top"]
    final_buy_condition = final_buy_condition & cond_above_cloud

df.loc[final_buy_condition, "signal"] = 1

# ----- [B] 매도 조건 조립 (원본과 동일) -----
final_sell_condition = cond_ma_dead

if USE_BOLLINGER:    final_sell_condition = final_sell_condition | cond_bb_breakdown
if USE_MACD:         final_sell_condition = final_sell_condition | cond_macd_dead
if USE_TREND_FILTER: final_sell_condition = final_sell_condition | (df["MA20"] < df["MA60"])
if USE_RSI_FILTER:   final_sell_condition = final_sell_condition | (df["RSI"] >= 75)

if USE_ICHIMOKU_CLOUD:
    cond_below_cloud = df["Close"] < df["Cloud_Bottom"]
    final_sell_condition = final_sell_condition | cond_below_cloud

df.loc[final_sell_condition, "signal"] = -1

# ===== 5. 첫 신호가 '매도(-1)'인 경우 제외 처리 (원본과 동일, Streamlit 버전에 누락됐던 부분) =====
first_signal_idx = df[df["signal"] != 0].index
if not first_signal_idx.empty and df.loc[first_signal_idx[0], "signal"] == -1:
    df.loc[first_signal_idx[0], "signal"] = 0

df["신호"] = df["signal"].map({1: "매수", -1: "매도", 0: "-"})

# ===== 6. 화면 표시용 인덱스 포맷 (계산이 다 끝난 뒤에만 문자열로 변환) =====
if interval_map[interval_kr] == "1d":
    display_index = df.index.strftime('%Y-%m-%d')
else:
    display_index = df.index.strftime('%Y-%m-%d %H:%M')
df_display = df.copy()
df_display.index = display_index

# 5. 화면 출력
st.markdown("##### 📊 매매 신호 발생 내역")

active_modes = []
if USE_TREND_FILTER:    active_modes.append("정배열")
if USE_BOLLINGER:       active_modes.append("볼린저")
if USE_MACD:             active_modes.append("MACD")
if USE_VOLUME_SPIKE:    active_modes.append("거래량")
if USE_RSI_FILTER:      active_modes.append("RSI")
if USE_ICHIMOKU_CLOUD:  active_modes.append("일목구름대")
st.caption(f"적용 필터: {' + '.join(active_modes) if active_modes else '없음 (기본 MA 골든크로스)'}")

rename_signal_dict = {
    "Close": "종가",
    "tenkan_sen": "전환선",
    "Volume": "거래량",
    "Vol_MA5": "5일거래량",
    "RSI": "RSI",
    "신호": "신호"
}

cols_to_show = ["종가", "전환선", "거래량", "5일거래량", "RSI", "신호"]
st.dataframe(
    df_display.rename(columns=rename_signal_dict)[df_display["signal"] != 0][cols_to_show].tail(10),
    use_container_width=True
)

st.markdown("##### 📈 시세 및 거래량 차트")
st.bar_chart(df_display["Volume"].tail(50))

df_chart = df_display.dropna(subset=['Open', 'High', 'Low', 'Close'])
fig = go.Figure(data=[go.Candlestick(
    x=df_chart.tail(50).index, open=df_chart.tail(50)['Open'], high=df_chart.tail(50)['High'],
    low=df_chart.tail(50)['Low'], close=df_chart.tail(50)['Close'],
    increasing_line_color='red', decreasing_line_color='blue'
)])
fig.add_trace(go.Scatter(x=df_chart.tail(50).index, y=df_chart.tail(50)['tenkan_sen'], mode='lines', name='전환선', line=dict(color='orange', width=2)))
if USE_ICHIMOKU_CLOUD:
    fig.add_trace(go.Scatter(x=df_chart.tail(50).index, y=df_chart.tail(50)['Cloud_Top'], mode='lines', name='구름상단', line=dict(color='gray', width=1, dash='dot')))
fig.update_layout(xaxis_rangeslider_visible=False, height=400)
st.plotly_chart(fig, use_container_width=True)

# 6. 최근 10일 상세 데이터
st.markdown("##### 📋 최근 10일 상세 지표 및 매매 신호")
recent_df = df_display.tail(10).copy()
recent_df['상태'] = recent_df.apply(lambda row: '▲ 양봉' if row['Close'] > row['Open'] else ('▼ 음봉' if row['Close'] < row['Open'] else '— 보합'), axis=1)
display_df = recent_df.rename(columns={"Open": "시가", "Close": "종가", "tenkan_sen": "전환선", "Volume": "거래량", "RSI": "RSI"})
st.dataframe(display_df[["시가", "종가", "거래량", "RSI", "상태", "신호"]], use_container_width=True)