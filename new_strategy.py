import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(layout="wide", page_title="주식 전략 분석기")


@st.cache_data(ttl=300)  # 5분 캐시 - 너무 자주 다시 받지 않도록
def get_macro_data():
    macro_tickers = {
        "원/달러": "KRW=X",
        "엔/달러": "JPY=X",
        "美 10년물": "^TNX",
        "WTI유": "CL=F",
        "VIX": "^VIX",
        "S&P500": "^GSPC",
        "S&P500 선물": "ES=F",
        "나스닥": "^IXIC",
        "나스닥 선물": "NQ=F",
        "필라델피아 반도체": "^SOX",
        "MSCI한국": "EWY"
    }
    results = []
    for name, ticker in macro_tickers.items():
        try:
            # period를 10일로 넉넉하게 받아서, 최근 1~2일 데이터가 비어도 직전 유효값을 쓸 수 있게 함
            hist = yf.Ticker(ticker).history(period="10d")
            # 종가(Close)가 실제로 존재하는 행만 남기기 (NaN 행 제거)
            hist = hist.dropna(subset=["Close"])
            if hist.empty or len(hist) < 2:
                results.append({"name": name, "value": None, "change_pct": None})
                continue
            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            change_pct = (current - prev) / prev * 100
            results.append({"name": name, "value": current, "change_pct": change_pct})
        except Exception:
            results.append({"name": name, "value": None, "change_pct": None})
    return results
 
macro_data = get_macro_data()
# 데이터가 없는 항목은 화면에 표시하지 않고 따로 안내
macro_data_valid = [d for d in macro_data if d["value"] is not None]
macro_data_failed = [d["name"] for d in macro_data if d["value"] is None]
 
st.markdown("---")
st.markdown("##### 🌍 오늘의 시장 환경")
 
display_mode = st.radio("표시 방식", ["흘러가는 티커", "고정 카드"], horizontal=True, label_visibility="collapsed")
 
if display_mode == "흘러가는 티커":
    # ----- 주식 전광판 스타일 스크롤링 티커 (HTML/CSS 직접 삽입) -----
    ticker_items_html = ""
    for item in macro_data_valid:
        color = "#d62728" if item["change_pct"] >= 0 else "#1f77b4"  # 상승 빨강, 하락 파랑
        arrow = "▲" if item["change_pct"] >= 0 else "▼"
        ticker_items_html += f"""
        <span style="margin-right: 40px; white-space: nowrap;">
            <b>{item['name']}</b>
            <span style="margin-left:6px;">{item['value']:,.2f}</span>
            <span style="color:{color}; margin-left:6px;">{arrow} {abs(item['change_pct']):.2f}%</span>
        </span>
        """
    # 끊김 없이 보이도록 동일 내용 2번 반복
    full_content = ticker_items_html * 2
 
    scrolling_html = f"""
    <style>
    .ticker-wrap {{
        width: 100%;
        overflow: hidden;
        background-color: #0e1117;
        padding: 10px 0;
        border-radius: 6px;
        box-sizing: border-box;
    }}
    .ticker-move {{
        display: inline-block;
        white-space: nowrap;
        animation: scroll-left 35s linear infinite;
        font-size: 14px;
        color: #fafafa;
        font-family: -apple-system, sans-serif;
    }}
    @keyframes scroll-left {{
        0%   {{ transform: translateX(0%); }}
        100% {{ transform: translateX(-50%); }}
    }}
    </style>
    <div class="ticker-wrap">
        <div class="ticker-move">{full_content}</div>
    </div>
    """
    st.components.v1.html(scrolling_html, height=50)
    st.caption("💡 흘러가는 화면이 끊기거나 너무 빠르면 위에서 '고정 카드'를 선택하세요.")
 
else:
    # ----- 고정 카드 버전 (작은 글씨, 화면 상단에 깔끔하게) -----
    cols = st.columns(5)
    for idx, item in enumerate(macro_data_valid):
        card_color = "#d62728" if item["change_pct"] >= 0 else "#1f77b4"
        card_arrow = "▲" if item["change_pct"] >= 0 else "▼"
        with cols[idx % 5]:
            st.markdown(
                f"<div style='font-size:12px; color:gray;'>{item['name']}</div>"
                f"<div style='font-size:15px; font-weight:bold;'>{item['value']:,.2f} "
                f"<span style='font-size:12px; color:{card_color};'>"
                f"{card_arrow}{abs(item['change_pct']):.2f}%</span></div>",
                unsafe_allow_html=True
            )
 
if macro_data_failed:
    st.caption(f"⚠️ 일시적으로 데이터를 못 가져온 항목: {', '.join(macro_data_failed)} (잠시 후 새로고침하면 복구될 수 있어요)")
 
# ============================================================
# 💡 [추가] 신용 스프레드 — 시장이 진짜로 불안한지 보는 지표
# ============================================================
st.markdown("---")
st.markdown("##### 💳 신용 스프레드 (위험자산 회피 심리)")
st.caption(
    "VIX는 '주가 변동성'만 보지만, 이 지표는 채권시장이 느끼는 불안까지 같이 봐요. "
    "**HYG**(고위험 회사채 ETF)가 빠지는데 **TLT**(미국 장기국채 ETF)가 오르면, "
    "투자자들이 위험자산을 버리고 안전자산으로 도망가는 중이라는 뜻이에요. "
    "이런 날은 개별 종목의 매수 신호가 떠도 한 박자 신중하게 접근하는 걸 권장해요. "
    "반대로 둘 다 같이 오르내리면 특별한 위험 회피 신호는 아니에요."
)
 
@st.cache_data(ttl=300)
def get_credit_spread_data():
    tickers = {"HYG (하이일드 회사채)": "HYG", "TLT (미국 장기국채)": "TLT"}
    results = []
    for name, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period="10d")
            hist = hist.dropna(subset=["Close"])
            if hist.empty or len(hist) < 2:
                results.append({"name": name, "value": None, "change_pct": None})
                continue
            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            change_pct = (current - prev) / prev * 100
            results.append({"name": name, "value": current, "change_pct": change_pct})
        except Exception:
            results.append({"name": name, "value": None, "change_pct": None})
    return results
 
credit_data = get_credit_spread_data()
credit_data_valid = [d for d in credit_data if d["value"] is not None]
 
if len(credit_data_valid) == 2:
    c1, c2 = st.columns(2)
    for col, item in zip([c1, c2], credit_data_valid):
        with col:
            st.metric(item["name"], f"${item['value']:,.2f}", delta=f"{item['change_pct']:+.2f}%")
 
    hyg_change = credit_data_valid[0]["change_pct"]
    tlt_change = credit_data_valid[1]["change_pct"]
    if hyg_change < 0 and tlt_change > 0:
        st.warning("⚠️ 위험자산 회피 신호: 회사채(HYG) 약세 + 국채(TLT) 강세 — 시장이 안전자산을 선호하는 중이에요.")
    elif hyg_change > 0 and tlt_change < 0:
        st.success("✅ 위험자산 선호 신호: 회사채(HYG) 강세 + 국채(TLT) 약세 — 시장이 위험을 감수하려는 분위기예요.")
    else:
        st.info("ℹ️ 특별한 쏠림 없이 같이 움직이는 중이에요.")
else:
    st.warning("신용 스프레드 데이터를 일시적으로 가져오지 못했어요. 잠시 후 새로고침해보세요.")
st.subheader("📈 주식 기술적 분석 및 매매 신호 스캐너")

st.markdown("##### 📌 즐겨찾기 종목")
c_fav1, c_fav2, c_fav3, _ = st.columns([1.5, 1.5, 1.5, 2])  # 버튼 크기에 맞게 조절

# 세션 상태(Session State)를 활용해 버튼 클릭 시 티커 입력창 값 제어
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "009150.KS"  # 기본값 (삼성전기)

with c_fav1:
    if st.button("⚡ LS ELECTRIC", use_container_width=True):
        st.session_state.selected_ticker = "010120.KS"
        st.rerun()
with c_fav2:
    if st.button("🏦 삼성생명", use_container_width=True):
        st.session_state.selected_ticker = "032830.KS"
        st.rerun()
with c_fav3:
    if st.button("💎 삼성전자우", use_container_width=True):
        st.session_state.selected_ticker = "005935.KS"
        st.rerun()
        
# 1. 상단 제어 영역
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    ticker_input = st.text_input("종목 티커 입력 (예: 005930.KS)", "009150.KS")
with col2:
    period_kr = st.selectbox("데이터 기간", ["1개월", "3개월", "6개월", "1년"], index=3)
with col3:
    interval_kr = st.selectbox("봉 단위", ["일봉", "60분봉", "15분봉"])

# ============================================================
# 💡 [추가] 추천 필터 조합 — 모달로 한번에 적용
# ============================================================
# 개념: 8개 필터를 매번 일일이 켜고 끄는 대신, 상황별로 검증된
#       조합을 버튼 하나로 적용할 수 있게 함. 모달(팝업)에서
#       조합을 고르면 체크박스 상태가 한번에 세팅됨.

# 조합 프리셋 정의
FILTER_PRESETS = {
    "추세 추종 (기본형)": {
        "trend": True, "macd": True, "bollinger": False,
        "volume": True, "rsi": False, "ichimoku": False,
        "atr": True, "relative_strength": False,
        "gap": False, "atr_surge": False, "mtf": True,
        "설명": "큰 흐름이 상승 중인 종목만 거른 뒤(정배열), MACD 골든크로스로 진입 타이밍을 잡아요. "
                "거래량으로 가짜 신호를 줄이고 ATR로 손절 기준을 같이 봐요. "
                "여기에 멀티 타임프레임 확인을 더해 60분봉 흐름까지 같은 방향인지 한 번 더 검증해요. "
                "신호는 적지만 신뢰도가 높은 가장 안전한 조합이에요. 추세가 뚜렷한 장에 적합해요."
    },
    "변동성 돌파 (모멘텀 추격형)": {
        "trend": False, "macd": False, "bollinger": True,
        "volume": True, "rsi": False, "ichimoku": False,
        "atr": True, "relative_strength": False,
        "gap": True, "atr_surge": True, "mtf": False,
        "설명": "볼린저 상단을 강하게 뚫는 순간을 거래량으로 검증해서 빠르게 잡는 조합이에요. "
                "갭상승 유지와 ATR 급변까지 더해, '진짜 돈이 몰려서 터지는 중'인지 다각도로 확인해요. "
                "정배열은 일부러 빼는데, 추세 초입엔 장기 이동평균이 못 따라온 경우가 많아서예요. "
                "막 터지기 시작하는 종목을 추격할 때 적합하고, 추격매수라 ATR 손절은 필수예요."
    },
    "저점 매수 (반등 확인형)": {
        "trend": False, "macd": True, "bollinger": False,
        "volume": False, "rsi": True, "ichimoku": False,
        "atr": True, "relative_strength": True,
        "gap": False, "atr_surge": False, "mtf": True,
        "설명": "RSI 과매도 구간에서의 반등을 노리되, 시장보다 덜 빠지거나 더 빨리 회복하는 "
                "'진짜 강한 종목'인지 상대강도로 검증해요. 여기에 MACD 골든크로스와 멀티 타임프레임 확인을 더해 "
                "'그냥 많이 빠진 것'과 '바닥을 찍고 모멘텀이 꺾여 60분봉에서도 살아나는 것'을 구분해요. "
                "심리적으로 어려운 조합이라 익숙해진 뒤 시도하는 걸 권해요."
    },
    "갭 추격 (단기 강세형)": {
        "trend": False, "macd": False, "bollinger": False,
        "volume": True, "rsi": False, "ichimoku": False,
        "atr": True, "relative_strength": False,
        "gap": True, "atr_surge": True, "mtf": False,
        "설명": "전일 종가보다 갭상승으로 출발했는데 장중에 그 갭을 안 메우고 버티는 종목을 잡아요. "
                "거래량 폭발과 ATR 급변까지 같이 확인해서, 단순 호가 공백이 아니라 "
                "진짜 매수세가 몰려서 생긴 갭인지 검증해요. 신호가 뜬 당일 단기 대응에 적합하고, "
                "변동성이 크니 ATR 손절은 반드시 같이 봐야 해요."
    },
}

if "preset_to_apply" not in st.session_state:
    st.session_state.preset_to_apply = None

period_map = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y"}
interval_map = {"일봉": "1d", "60분봉": "60m", "15분봉": "15m"}

st.markdown("##### 🛡️ 필터 설정")

@st.dialog("추천 필터 조합 선택")
def show_preset_modal():
    st.caption("상황에 맞는 조합을 고르면 아래 8개 필터가 한번에 세팅돼요.")
    for preset_name, preset_values in FILTER_PRESETS.items():
        with st.container(border=True):
            st.markdown(f"**{preset_name}**")
            st.caption(preset_values["설명"])
            if st.button("이 조합 적용하기", key=f"apply_{preset_name}", use_container_width=True):
                st.session_state.preset_to_apply = preset_name
                st.rerun()

if st.button("📋 추천 조합 보기", use_container_width=False):
    show_preset_modal()

# 모달에서 선택된 프리셋을 체크박스 기본값에 반영
applied_preset = FILTER_PRESETS.get(st.session_state.preset_to_apply, {})
if st.session_state.preset_to_apply:
    st.success(f"✅ '{st.session_state.preset_to_apply}' 조합이 적용됐어요. 아래에서 개별 조정도 가능해요.")


col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    USE_TREND_FILTER = st.checkbox("정배열 필터", applied_preset.get("trend", False))
    st.caption("MA20(20일 평균가)이 MA60(60일 평균가) 위에 있을 때만 매수 허용. "
               "단기 추세가 장기 추세보다 강할 때만 진입하므로, 하락장에서의 섣부른 매수를 줄여줘요. "
               "켜면 신호가 줄어드는 대신 추세 역행 매매를 막아줘요.")
with col_s2:
    USE_MACD = st.checkbox("MACD 골든크로스", applied_preset.get("macd", True))
    st.caption("단기 추세선이 장기 추세선을 위로 돌파하는 순간(모멘텀 전환)을 포착해요. "
               "매수: 골든크로스 발생 시 진입 검토. 매도: 반대로 데드크로스 시 청산 검토. "
               "추세 전환 초입을 잡는 데 강하지만, 횡보장에서는 가짜 신호(휩소)가 잦아요.")
with col_s3:
    USE_BOLLINGER = st.checkbox("볼린저 밴드 돌파", applied_preset.get("bollinger", False))
    st.caption("주가가 평소 변동 범위(상단밴드)를 강하게 뚫고 올라갈 때 포착해요. "
               "매수: 상단 돌파 시 추세 가속 기대. 매도: 종가가 다시 MA20 아래로 내려오면 청산. "
               "변동성이 커지는 구간에서 효과적이에요.")

col_s4, col_s5, col_s6 = st.columns(3)
with col_s4:
    USE_VOLUME_SPIKE = st.checkbox("거래량 폭발 필터", applied_preset.get("volume", False))
    st.caption("평소(5일 평균) 대비 거래량이 1.5배 이상 터졌을 때만 매수를 인정해요. "
               "거래량 없는 가격 움직임은 힘이 약해 되돌림 가능성이 높으므로, "
               "이 필터를 켜면 '진짜 힘 있는' 신호만 골라낼 수 있어요.")
with col_s5:
    USE_RSI_FILTER = st.checkbox("RSI 필터", applied_preset.get("rsi", False))
    st.caption("RSI 35 이하(과매도) 구간에서의 반등 매수를 보완하고, "
               "RSI 75 이상(과매수) 구간에서는 조기 청산을 유도해요. "
               "매수: 과매도+장기추세 유지 시 저점 매수 기회. 매도: 과매수 구간 진입 시 차익실현 검토.")
with col_s6:
    USE_ICHIMOKU_CLOUD = st.checkbox("일목구름대 필터", applied_preset.get("ichimoku", False))
    st.caption("주가가 구름대(저항/지지 영역) 위에 있을 때만 매수를 허용하는 대세 하락장 방어 필터예요. "
               "매수: 구름 위 안착 시에만 진입. 매도: 구름 아래로 이탈하면 대세 하락 신호로 보고 무조건 청산.")

col_s7, col_s8, col_s9 = st.columns(3)
with col_s7:
    USE_ATR_STOP = st.checkbox("ATR 변동성 기반 손절선 표시", applied_preset.get("atr", True))
    st.caption("그 종목이 평소(14일) 하루에 평균적으로 얼마나 움직이는지(ATR)를 기준으로 "
               "손절가를 계산해요. 변동성이 큰 종목은 손절선을 넓게, 작은 종목은 좁게 잡아 "
               "'정상적인 출렁임'에 불필요하게 손절당하는 걸 막아줘요. "
               "매매 원칙: 진입가에서 ATR×2 만큼 하락하면 기계적으로 손절하는 걸 권장해요.")
with col_s8:
    USE_RELATIVE_STRENGTH = st.checkbox("시장 대비 상대강도 필터", applied_preset.get("relative_strength", False))
    st.caption("KOSPI 지수 대비 이 종목이 더 잘 가고 있는지(상대강도)를 비교해요. "
               "매수: 상대강도가 우상향 중일 때 = 시장이 빠져도 버티거나 시장보다 더 오르는 '진짜 힘 있는' 종목. "
               "매도: 상대강도가 꺾이면 = 시장 따라 출렁이기만 하는 종목일 수 있어 신뢰도 하락.")
with col_s9:
    USE_GAP_FILTER = st.checkbox("갭상승 유지 필터", applied_preset.get("gap", False))
    st.caption("어제 종가보다 1% 이상 높게 출발(갭상승)했는데 장중에도 그 갭을 안 메우고 버티면 "
            "신규 매수세가 강하다는 뜻이에요. 매수: 갭 유지 시 진입 검토. "
                "매도 참고: 갭이 장중에 메워지면(전일 종가 아래로 떨어지면) 가짜 신호로 보고 보류해요.")

col_s10, col_s11, col_s12 = st.columns(3)
with col_s10:
    USE_ATR_SURGE = st.checkbox("ATR 급변 필터", applied_preset.get("atr_surge", False))
    st.caption("평소(최근 5일 평균) 대비 오늘 변동성(ATR)이 30% 이상 갑자기 커지면 포착해요. "
           "변동성이 급격히 커지는 시점은 큰 자금이 들어오기 시작하는 타이밍과 자주 겹쳐요. "
           "매수: 다른 매수 신호와 같이 뜰 때 신뢰도를 높이는 보조 용도로 활용하세요.")
with col_s11:
    if interval_map[interval_kr] == "1d":
        USE_MTF_FILTER = st.checkbox("멀티 타임프레임 확인", applied_preset.get("mtf", False))
        st.caption("일봉에서 매수 신호가 떠도, 더 짧은 시간 단위(60분봉)의 최근 흐름도 같은 방향인지 "
                   "같이 확인해요. 일봉은 좋은데 60분봉에서 막 꺾이는 중이면 타이밍이 안 좋을 수 있어요. "
                   "매수: 일봉 신호 + 60분봉 흐름이 같은 방향일 때 신뢰도가 더 높아요.")
    else:
        USE_MTF_FILTER = False
        st.caption("💡 멀티 타임프레임 확인은 '일봉' 선택 시에만 사용할 수 있어요.")

st.markdown("---")

# 데이터 매핑


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
    mtf_bullish = None
    if interval_map[interval_kr] == "1d" and USE_MTF_FILTER:
        df_60m = stock.history(period="5d", interval="60m")
        if not df_60m.empty:
            df_60m.index = df_60m.index.tz_convert('Asia/Seoul')
            df_60m["MA20_60m"] = df_60m["Close"].rolling(window=20).mean()
            if len(df_60m) >= 20:
                mtf_bullish = df_60m["Close"].iloc[-1] > df_60m["MA20_60m"].iloc[-1]

    if USE_RELATIVE_STRENGTH:
        kospi = yf.Ticker("^KS11")
        df_kospi = kospi.history(period=period_map[period_kr], interval=interval_map[interval_kr])
        df_kospi.index = df_kospi.index.tz_convert('Asia/Seoul')
except Exception as e:
    st.error("티커를 확인해주세요.")
    st.stop()

if interval_map[interval_kr] == "1d" and USE_MTF_FILTER:
    if mtf_bullish is None:
        st.warning("60분봉 데이터가 부족해 멀티 타임프레임 확인이 어려워요.")
    else:
        st.caption(f"현재 60분봉 기준 흐름: {'🟢 상승 추세' if mtf_bullish else '🔴 하락/횡보 추세'}")

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

# ===== 💡 [신규] ATR 급변 (변동성이 갑자기 커지기 시작하는 시점) =====
# 오늘 ATR이 최근 5일 평균 ATR보다 30% 이상 커지면 "변동성 급등"으로 판단
df["ATR_MA5"] = df["ATR"].rolling(window=5).mean()
df["ATR_Surge_Pct"] = (df["ATR"] - df["ATR_MA5"]) / df["ATR_MA5"] * 100
cond_atr_surge = df["ATR_Surge_Pct"] >= 30  # 평소보다 변동성이 30% 이상 커진 날

# ===== 💡 [신규] 갭(Gap) 분석 =====
# 어제 종가 대비 오늘 시가가 1% 이상 위에서 출발(갭상승)했는데,
# 장중 저가가 어제 종가 아래로 안 떨어지면(갭 유지) 신규 매수세가 강하다는 뜻
prev_close_for_gap = df["Close"].shift(1)
df["Gap_Pct"] = (df["Open"] - prev_close_for_gap) / prev_close_for_gap * 100
df["Is_Gap_Up"] = df["Gap_Pct"] >= 1.0
df["Gap_Held"] = df["Low"] > prev_close_for_gap
cond_gap_buy = df["Is_Gap_Up"] & df["Gap_Held"]

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

buy_triggers = []

if USE_MACD:
    buy_triggers.append(cond_macd_gold)       # MACD 골든크로스 시점
if USE_BOLLINGER:
    buy_triggers.append(cond_bb_breakout)     # 볼린저밴드 상단 돌파 시점
if USE_RSI_FILTER:
    buy_triggers.append(cond_rsi_oversold)     # RSI 과매도 바닥 구간 진입 시점

# 사용자가 체크박스를 하나도 안 켰다면, 기본 시스템으로 '이동평균선 골든크로스'를 씁니다.
if not buy_triggers:
    final_buy_trigger = cond_ma_gold
else:
    # 켜진 트리거들 중 하나라도 만족(True)하면 신호 발생
    final_buy_trigger = pd.concat(buy_triggers, axis=1).any(axis=1)


# 2. 필터(안전장치 자격요건) 모음집 - 켜놓은 조건은 무조건 '동시에' 만족해야 함 (AND 연산)
buy_filters = []

if USE_TREND_FILTER:
    buy_filters.append(df["MA20"] > df["MA60"])       # 정배열 상태인가?
if USE_VOLUME_SPIKE:
    buy_filters.append(cond_volume_burst)             # 거래량이 터진 상태인가?
if USE_ICHIMOKU_CLOUD:
    buy_filters.append(df["Close"] > df["Cloud_Top"]) # 주가가 일목구름 위에 있는가?
if USE_RELATIVE_STRENGTH:
    buy_filters.append(cond_rs_rising)                # 시장 대비 상대강도가 우상향인가?

# 켜진 필터가 없다면 항상 통과(True), 있다면 모든 필터를 만족해야 통과
if buy_filters:
    final_buy_filter = pd.concat(buy_filters, axis=1).all(axis=1)
else:
    final_buy_filter = pd.Series(True, index=df.index)


# 3. 최종 결합: 신호등(트리거)이 켜졌고, 자격요건(필터)을 모두 통과했을 때만 최종 매수!
final_buy_condition = final_buy_trigger & final_buy_filter

if USE_GAP_FILTER:
    final_buy_condition = final_buy_condition & cond_gap_buy

if USE_ATR_SURGE:
    final_buy_condition = final_buy_condition & cond_atr_surge

if USE_MTF_FILTER and mtf_bullish is not None:
    final_buy_condition = final_buy_condition & mtf_bullish
# ---------------------------------------------------
# (아래 줄은 기존 코드와 연결되는 부분입니다)
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

st.markdown("##### 📈 거래량")
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

st.markdown("##### 📈 시세")
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
st.caption("• 밴드 폭이 1 이상이면 변동성이 커지며 시장보다 강한 탄력을 받고 있다는 신호입니다.")
st.caption("• 밴드 폭이 1 이하이면 에너지가 응축되는 횡보 구간으로, 시장의 움직임이 둔화된 상태입니다.")

fig_bb = go.Figure()
fig_bb.add_trace(go.Scatter(x=df_chart.tail(60).index, y=df_chart.tail(60)['BB_Width'], mode='lines', name='밴드폭', line=dict(color='teal', width=2)))
squeeze_points = df_chart.tail(60)[df_chart.tail(60)['스퀴즈해제'] == "💥"]
if not squeeze_points.empty:
    fig_bb.add_trace(go.Scatter(x=squeeze_points.index, y=squeeze_points['BB_Width'], mode='markers', name='스퀴즈 해제', marker=dict(color='red', size=10, symbol='star')))
fig_bb.update_layout(height=250)
st.plotly_chart(fig_bb, use_container_width=True)

st.caption("• 스퀴즈 해제는 방향이 결정된 것이 아니라, 💥응축되었던 변동성이 위든 아래든 터지기 시작하는 초기 신호입니다.")
st.caption("• 밴드 상단을 강하게 돌파하며 벌어지면 상승 추세로, 하단을 강하게 이탈하며 벌어지면 하락 추세로 판단합니다.")
st.caption("• 따라서 스퀴즈 해제 표시가 떴을 때는, 가격이 어느 쪽 밴드를 먼저 뚫고 나가는지 확인하는 것이 가장 중요합니다.")

# ===== 최근 10일 상세 데이터 =====
st.markdown("##### 📋 최근 10일 상세 지표 및 매매 신호")
recent_df = df_display.tail(10).copy()
recent_df['상태'] = recent_df.apply(lambda row: '▲ 양봉' if row['Close'] > row['Open'] else ('▼ 음봉' if row['Close'] < row['Open'] else '— 보합'), axis=1)
display_df = recent_df.rename(columns={"Open": "시가", "Close": "종가", "tenkan_sen": "전환선", "Volume": "거래량", "RSI": "RSI", "Stop_Loss": "ATR손절가"})
show_cols = ["시가", "종가", "거래량", "RSI", "ATR손절가", "상태", "신호"]
st.dataframe(display_df[show_cols], use_container_width=True)

