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

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    USE_TREND_FILTER = st.checkbox("정배열 필터", False)
    st.caption("MA20(20일 평균가)이 MA60(60일 평균가) 위에 있을 때만 매수 허용. "
               "단기 추세가 장기 추세보다 강할 때만 진입하므로, 하락장에서의 섣부른 매수를 줄여줘요. "
               "켜면 신호가 줄어드는 대신 추세 역행 매매를 막아줘요.")
with col_s2:
    USE_MACD = st.checkbox("MACD 골든크로스", True)
    st.caption("단기 추세선이 장기 추세선을 위로 돌파하는 순간(모멘텀 전환)을 포착해요. "
               "매수: 골든크로스 발생 시 진입 검토. 매도: 반대로 데드크로스 시 청산 검토. "
               "추세 전환 초입을 잡는 데 강하지만, 횡보장에서는 가짜 신호(휩소)가 잦아요.")
with col_s3:
    USE_BOLLINGER = st.checkbox("볼린저 밴드 돌파", False)
    st.caption("주가가 평소 변동 범위(상단밴드)를 강하게 뚫고 올라갈 때 포착해요. "
               "매수: 상단 돌파 시 추세 가속 기대. 매도: 종가가 다시 MA20 아래로 내려오면 청산. "
               "변동성이 커지는 구간에서 효과적이에요.")

col_s4, col_s5, col_s6 = st.columns(3)
with col_s4:
    USE_VOLUME_SPIKE = st.checkbox("거래량 폭발 필터", False)
    st.caption("평소(5일 평균) 대비 거래량이 1.5배 이상 터졌을 때만 매수를 인정해요. "
               "거래량 없는 가격 움직임은 힘이 약해 되돌림 가능성이 높으므로, "
               "이 필터를 켜면 '진짜 힘 있는' 신호만 골라낼 수 있어요.")
with col_s5:
    USE_RSI_FILTER = st.checkbox("RSI 필터", False)
    st.caption("RSI 35 이하(과매도) 구간에서의 반등 매수를 보완하고, "
               "RSI 75 이상(과매수) 구간에서는 조기 청산을 유도해요. "
               "매수: 과매도+장기추세 유지 시 저점 매수 기회. 매도: 과매수 구간 진입 시 차익실현 검토.")
with col_s6:
    USE_ICHIMOKU_CLOUD = st.checkbox("일목구름대 필터", False)
    st.caption("주가가 구름대(저항/지지 영역) 위에 있을 때만 매수를 허용하는 대세 하락장 방어 필터예요. "
               "매수: 구름 위 안착 시에만 진입. 매도: 구름 아래로 이탈하면 대세 하락 신호로 보고 무조건 청산.")

col_s7, col_s8 = st.columns(2)
with col_s7:
    USE_ATR_STOP = st.checkbox("ATR 변동성 기반 손절선 표시", True)
    st.caption("그 종목이 평소(14일) 하루에 평균적으로 얼마나 움직이는지(ATR)를 기준으로 "
               "손절가를 계산해요. 변동성이 큰 종목은 손절선을 넓게, 작은 종목은 좁게 잡아 "
               "'정상적인 출렁임'에 불필요하게 손절당하는 걸 막아줘요. "
               "매매 원칙: 진입가에서 ATR×2 만큼 하락하면 기계적으로 손절하는 걸 권장해요.")
with col_s8:
    USE_RELATIVE_STRENGTH = st.checkbox("시장 대비 상대강도 필터", False)
    st.caption("KOSPI 지수 대비 이 종목이 더 잘 가고 있는지(상대강도)를 비교해요. "
               "매수: 상대강도가 우상향 중일 때 = 시장이 빠져도 버티거나 시장보다 더 오르는 '진짜 힘 있는' 종목. "
               "매도: 상대강도가 꺾이면 = 시장 따라 출렁이기만 하는 종목일 수 있어 신뢰도 하락.")

st.markdown("---")

# 데이터 매핑
period_map = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y"}
interval_map = {"일봉": "1d", "60분봉": "60m", "15분봉": "15m"}

# 2. 데이터 가져오기
# [핵심] 인덱스를 문자열로 바꾸지 않음 -> rolling/shift 계산이 시간 순서 기준으로 정확히 동작
try:
    stock = yf.Ticker(ticker_input)
    company_name = stock.info.get('longName', '알 수 없는 종목')
    st.subheader(f"📊 {company_name} ({ticker_input})")

    df = stock.history(period=period_map[period_kr], interval=interval_map[interval_kr])
    df.index = df.index.tz_convert('Asia/Seoul')
    pd.options.display.float_format = '{:.2f}'.format

    # 시장 대비 상대강도 필터를 위한 KOSPI 지수 데이터 (필요할 때만 호출)
    if USE_RELATIVE_STRENGTH:
        kospi = yf.Ticker("^KS11")
        df_kospi = kospi.history(period=period_map[period_kr], interval=interval_map[interval_kr])
        df_kospi.index = df_kospi.index.tz_convert('Asia/Seoul')
except Exception as e:
    st.error("티커를 확인해주세요.")
    st.stop()

# ===== 1. 기존 기술적 지표 계산 =====
df["MA20"] = df["Close"].rolling(window=20).mean()
df["MA60"] = df["Close"].rolling(window=60).mean()

df["std20"] = df["Close"].rolling(window=20).std()
df["BB_Upper"] = df["MA20"] + (2 * df["std20"])
df["BB_Lower"] = df["MA20"] - (2 * df["std20"])

exp12 = df["Close"].ewm(span=12, adjust=False).mean()
exp26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = exp12 - exp26
df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

# ===== 2. 거래량 및 RSI 계산 =====
df["Vol_MA5"] = df["Volume"].rolling(window=5).mean()

delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / (loss + 1e-9)
df["RSI"] = 100 - (100 / (1 + rs))

# ===== 3. 일목균형표 구름대 계산 =====
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

# ===== 💡 4. [신규] ATR (Average True Range) - 변동성 기반 손절선 =====
# True Range: 당일 변동폭 중 가장 큰 값 (전일 종가 갭까지 고려)
prev_close = df["Close"].shift(1)
tr1 = df["High"] - df["Low"]
tr2 = (df["High"] - prev_close).abs()
tr3 = (df["Low"] - prev_close).abs()
df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df["ATR"] = df["TR"].rolling(window=14).mean()

# 손절가 = 종가 - (ATR × 2) : 평소 변동폭의 2배만큼 빠지면 손절 기준선으로 봄
df["Stop_Loss"] = df["Close"] - (df["ATR"] * 2)

# ===== 💡 5. [신규] 볼린저 밴드 스퀴즈 (변동성 축소 → 확대 포착) =====
# 밴드 폭 = (상단 - 하단) / 중심선(MA20) -> 비율로 표현해 변동성 수축/확장을 비교 가능하게 함
df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["MA20"]
# 최근 60일 중 밴드 폭이 하위 20% 수준까지 좁아졌다가, 다시 넓어지기 시작하는 시점을 '스퀴즈 이후 확장'으로 정의
df["BB_Width_Percentile"] = df["BB_Width"].rolling(window=60).rank(pct=True)
cond_squeeze_release = (df["BB_Width_Percentile"].shift(1) <= 0.2) & (df["BB_Width"] > df["BB_Width"].shift(1))

# ===== 💡 6. [신규] 시장 대비 상대강도 =====
if USE_RELATIVE_STRENGTH:
    # 종목 수익률 누적 - 코스피 수익률 누적 = 상대강도 (양수면 시장보다 잘 가는 중)
    df_kospi_aligned = df_kospi["Close"].reindex(df.index, method="ffill")
    stock_return = df["Close"] / df["Close"].iloc[0] - 1
    market_return = df_kospi_aligned / df_kospi_aligned.iloc[0] - 1
    df["Relative_Strength"] = (stock_return - market_return) * 100  # %p 단위
    df["RS_MA5"] = df["Relative_Strength"].rolling(window=5).mean()
    cond_rs_rising = df["Relative_Strength"] > df["RS_MA5"]  # 상대강도가 자기 평균보다 위 = 강세 지속
else:
    cond_rs_rising = pd.Series(True, index=df.index)  # 필터 꺼져있으면 항상 통과

# ===== 7. 매매 신호(Signal) 계산 =====
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

# ----- [A] 매수 조건 조립 -----
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

if USE_RELATIVE_STRENGTH:
    final_buy_condition = final_buy_condition & cond_rs_rising

df.loc[final_buy_condition, "signal"] = 1

# ----- [B] 매도 조건 조립 -----
final_sell_condition = cond_ma_dead

if USE_BOLLINGER:    final_sell_condition = final_sell_condition | cond_bb_breakdown
if USE_MACD:         final_sell_condition = final_sell_condition | cond_macd_dead
if USE_TREND_FILTER: final_sell_condition = final_sell_condition | (df["MA20"] < df["MA60"])
if USE_RSI_FILTER:   final_sell_condition = final_sell_condition | (df["RSI"] >= 75)

if USE_ICHIMOKU_CLOUD:
    cond_below_cloud = df["Close"] < df["Cloud_Bottom"]
    final_sell_condition = final_sell_condition | cond_below_cloud

if USE_RELATIVE_STRENGTH:
    final_sell_condition = final_sell_condition | (~cond_rs_rising & (df["RSI"] >= 60))  # 상대강도 꺾이고 과열권이면 청산 가중

df.loc[final_sell_condition, "signal"] = -1

# ===== 8. 첫 신호가 '매도(-1)'인 경우 제외 처리 =====
first_signal_idx = df[df["signal"] != 0].index
if not first_signal_idx.empty and df.loc[first_signal_idx[0], "signal"] == -1:
    df.loc[first_signal_idx[0], "signal"] = 0

df["신호"] = df["signal"].map({1: "매수", -1: "매도", 0: "-"})
df["스퀴즈해제"] = cond_squeeze_release.map({True: "💥", False: ""})

# ===== 9. 화면 표시용 인덱스 포맷 (계산이 다 끝난 뒤에만 문자열로 변환) =====
if interval_map[interval_kr] == "1d":
    display_index = df.index.strftime('%Y-%m-%d')
else:
    display_index = df.index.strftime('%Y-%m-%d %H:%M')
df_display = df.copy()
df_display.index = display_index

# ===== 화면 출력 =====
st.markdown("##### 📊 매매 신호 발생 내역")

active_modes = []
if USE_TREND_FILTER:    active_modes.append("정배열")
if USE_BOLLINGER:        active_modes.append("볼린저")
if USE_MACD:              active_modes.append("MACD")
if USE_VOLUME_SPIKE:     active_modes.append("거래량")
if USE_RSI_FILTER:       active_modes.append("RSI")
if USE_ICHIMOKU_CLOUD:   active_modes.append("일목구름대")
if USE_RELATIVE_STRENGTH: active_modes.append("상대강도")
st.caption(f"적용 필터: {' + '.join(active_modes) if active_modes else '없음 (기본 MA 골든크로스)'}")

rename_signal_dict = {
    "Close": "종가",
    "tenkan_sen": "전환선",
    "Volume": "거래량",
    "Vol_MA5": "5일거래량",
    "RSI": "RSI",
    "Stop_Loss": "ATR손절가",
    "신호": "신호",
    "스퀴즈해제": "변동성확장",
}

cols_to_show = ["종가", "전환선", "거래량", "5일거래량", "RSI", "ATR손절가", "신호", "변동성확장"]
st.dataframe(
    df_display.rename(columns=rename_signal_dict)[df_display["signal"] != 0][cols_to_show].tail(10),
    use_container_width=True
)

# ===== 현재 상태 요약 카드 =====
st.markdown("##### 🧭 현재 상태 요약")
latest = df.iloc[-1]
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("현재가", f"{latest['Close']:,.0f}")
with m2:
    st.metric("ATR (평균 일일 변동폭)", f"{latest['ATR']:,.0f}")
with m3:
    st.metric("ATR 기준 손절가 (×2)", f"{latest['Stop_Loss']:,.0f}",
               delta=f"{(latest['Stop_Loss'] - latest['Close']):,.0f}")
with m4:
    if USE_RELATIVE_STRENGTH:
        st.metric("시장 대비 상대강도", f"{latest['Relative_Strength']:+.2f}%p")
    else:
        st.metric("시장 대비 상대강도", "필터 꺼짐")

st.markdown("##### 📈 시세 및 거래량 차트")
st.bar_chart(df_display["Volume"].tail(50))

df_chart = df_display.dropna(subset=['Open', 'High', 'Low', 'Close'])
fig = go.Figure(data=[go.Candlestick(
    x=df_chart.tail(50).index, open=df_chart.tail(50)['Open'], high=df_chart.tail(50)['High'],
    low=df_chart.tail(50)['Low'], close=df_chart.tail(50)['Close'],
    increasing_line_color='red', decreasing_line_color='blue'
)])
fig.add_trace(go.Scatter(x=df_chart.tail(50).index, y=df_chart.tail(50)['tenkan_sen'], mode='lines', name='전환선', line=dict(color='orange', width=2)))
fig.add_trace(go.Scatter(x=df_chart.tail(50).index, y=df_chart.tail(50)['Stop_Loss'], mode='lines', name='ATR손절선', line=dict(color='purple', width=1, dash='dash')))
if USE_ICHIMOKU_CLOUD:
    fig.add_trace(go.Scatter(x=df_chart.tail(50).index, y=df_chart.tail(50)['Cloud_Top'], mode='lines', name='구름상단', line=dict(color='gray', width=1, dash='dot')))
fig.update_layout(xaxis_rangeslider_visible=False, height=400)
st.plotly_chart(fig, use_container_width=True)

# ===== 시장 대비 상대강도 차트 (필터 켰을 때만 표시) =====
if USE_RELATIVE_STRENGTH:
    st.markdown("##### 🆚 시장(KOSPI) 대비 상대강도 추이")
    st.caption("0보다 위에 있으면 시장보다 더 잘 가고 있다는 뜻, 우상향이면 점점 더 강해지고 있다는 뜻이에요.")
    fig_rs = go.Figure()
    fig_rs.add_trace(go.Scatter(x=df_chart.tail(60).index, y=df_chart.tail(60)['Relative_Strength'], mode='lines', name='상대강도', line=dict(color='green', width=2)))
    fig_rs.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_rs.update_layout(height=250)
    st.plotly_chart(fig_rs, use_container_width=True)

# ===== 볼린저 밴드 폭(스퀴즈) 차트 =====
st.markdown("##### 🌀 변동성 수축/확장 (볼린저 밴드 폭)")
st.caption("밴드 폭이 좁아졌다가(스퀴즈) 다시 넓어지기 시작하는 지점(💥)은 큰 움직임이 시작될 수 있는 신호예요.")
fig_bb = go.Figure()
fig_bb.add_trace(go.Scatter(x=df_chart.tail(60).index, y=df_chart.tail(60)['BB_Width'], mode='lines', name='밴드폭', line=dict(color='teal', width=2)))
squeeze_points = df_chart.tail(60)[df_chart.tail(60)['스퀴즈해제'] == "💥"]
if not squeeze_points.empty:
    fig_bb.add_trace(go.Scatter(x=squeeze_points.index, y=squeeze_points['BB_Width'], mode='markers', name='스퀴즈 해제', marker=dict(color='red', size=10, symbol='star')))
fig_bb.update_layout(height=250)
st.plotly_chart(fig_bb, use_container_width=True)

# ===== 최근 10일 상세 데이터 =====
st.markdown("##### 📋 최근 10일 상세 지표 및 매매 신호")
recent_df = df_display.tail(10).copy()
recent_df['상태'] = recent_df.apply(lambda row: '▲ 양봉' if row['Close'] > row['Open'] else ('▼ 음봉' if row['Close'] < row['Open'] else '— 보합'), axis=1)
display_df = recent_df.rename(columns={"Open": "시가", "Close": "종가", "tenkan_sen": "전환선", "Volume": "거래량", "RSI": "RSI", "Stop_Loss": "ATR손절가"})
show_cols = ["시가", "종가", "거래량", "RSI", "ATR손절가", "상태", "신호"]
st.dataframe(display_df[show_cols], use_container_width=True)


# ============================================================
# 💡 [추가] 섹터 로테이션 — 지금 어느 업종에 돈이 몰리고 있는지
# ============================================================
# 개념: 같은 기간 동안 주요 섹터 ETF들의 수익률을 비교해서,
#       상대적으로 강한 섹터/약한 섹터를 한눈에 보는 도구예요.
#       개별 종목 신호가 좋아도, 그 종목이 속한 섹터 자체가 약하면
#       전체적인 순풍을 못 받고 있을 수 있어요.
#
# 참고: 한국 개별 업종 ETF(반도체, 2차전지 등)는 yfinance에서
#       데이터가 부실한 경우가 많아, 정보가 안정적인 미국 섹터 ETF
#       (S&P500 11개 섹터 대표 ETF) 기준으로 구성했어요.
#       미국 시장 기준이지만, 글로벌 자금 흐름의 큰 그림을 보는 데
#       참고할 수 있어요.

st.markdown("---")
st.markdown("##### 🔄 섹터 로테이션 (최근 자금이 몰리는 업종)")
st.caption("S&P500 11개 섹터 대표 ETF의 최근 수익률을 비교해요. 상대강도가 강한 섹터는 "
           "지금 시장의 관심이 몰려있다는 뜻이고, 약한 섹터는 자금이 빠져나가고 있다는 뜻이에요. "
           "내가 보는 종목의 섹터가 상위권이면 순풍, 하위권이면 역풍을 맞고 있다고 해석할 수 있어요.")

sector_period = st.selectbox("섹터 비교 기간", ["1개월", "3개월", "6개월"], index=0, key="sector_period")
sector_period_map = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo"}

sector_etfs = {
    "XLK 기술": "XLK",
    "XLF 금융": "XLF",
    "XLV 헬스케어": "XLV",
    "XLE 에너지": "XLE",
    "XLY 임의소비재": "XLY",
    "XLP 필수소비재": "XLP",
    "XLI 산업재": "XLI",
    "XLB 소재": "XLB",
    "XLU 유틸리티": "XLU",
    "XLRE 부동산": "XLRE",
    "XLC 커뮤니케이션": "XLC",
}

@st.cache_data(ttl=3600)  # 1시간 캐시 - 매번 11개 ETF를 다시 받지 않도록
def get_sector_returns(period):
    results = []
    for name, ticker in sector_etfs.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if hist.empty:
                continue
            ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
            results.append({"섹터": name, "티커": ticker, "수익률(%)": round(ret, 2)})
        except Exception:
            continue
    return pd.DataFrame(results).sort_values("수익률(%)", ascending=False)

with st.spinner("섹터별 데이터 수집 중..."):
    df_sector = get_sector_returns(sector_period_map[sector_period])

if not df_sector.empty:
    # 막대그래프로 시각화 - 강한 섹터(양수)는 빨강, 약한 섹터(음수)는 파랑
    colors = ["#d62728" if v >= 0 else "#1f77b4" for v in df_sector["수익률(%)"]]
    fig_sector = go.Figure(data=[go.Bar(
        x=df_sector["섹터"],
        y=df_sector["수익률(%)"],
        marker_color=colors,
        text=df_sector["수익률(%)"].astype(str) + "%",
        textposition="outside"
    )])
    fig_sector.update_layout(
        height=350,
        xaxis_title="",
        yaxis_title=f"{sector_period} 수익률(%)",
        showlegend=False
    )
    st.plotly_chart(fig_sector, use_container_width=True)

    col_top, col_bottom = st.columns(2)
    with col_top:
        st.markdown("**🔥 강세 섹터 TOP 3**")
        st.dataframe(df_sector.head(3)[["섹터", "수익률(%)"]], use_container_width=True, hide_index=True)
    with col_bottom:
        st.markdown("**🧊 약세 섹터 TOP 3**")
        st.dataframe(df_sector.tail(3)[["섹터", "수익률(%)"]].sort_values("수익률(%)"), use_container_width=True, hide_index=True)
else:
    st.warning("섹터 데이터를 가져오지 못했어요. 잠시 후 다시 시도해주세요.")