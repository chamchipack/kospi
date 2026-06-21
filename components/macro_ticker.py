"""
macro_ticker.py
오늘의 시장 환경(거시지표) 컴포넌트
- app.py에서 import해서 사용
"""

import streamlit as st
import yfinance as yf


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
        "MSCI한국": "EWY",
    }
    results = []
    for name, ticker in macro_tickers.items():
        try:
            # period를 10일로 넉넉하게 받아서, 최근 1~2일 데이터가 비어도 직전 유효값을 쓸 수 있게 함
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


def render_macro_ticker():
    """오늘의 시장 환경 섹션을 화면에 그려주는 함수. app.py에서 이 함수 하나만 호출하면 됨."""
    macro_data = get_macro_data()
    macro_data_valid = [d for d in macro_data if d["value"] is not None]
    macro_data_failed = [d["name"] for d in macro_data if d["value"] is None]

    st.markdown("---")
    st.markdown("##### 🌍 오늘의 시장 환경")

    display_mode = st.radio(
        "표시 방식", ["흘러가는 티커", "고정 카드"],
        horizontal=True, label_visibility="collapsed"
    )

    if display_mode == "흘러가는 티커":
        ticker_items_html = ""
        for item in macro_data_valid:
            color = "#d62728" if item["change_pct"] >= 0 else "#1f77b4"
            arrow = "▲" if item["change_pct"] >= 0 else "▼"
            ticker_items_html += f"""
            <span style="margin-right: 40px; white-space: nowrap;">
                <b>{item['name']}</b>
                <span style="margin-left:6px;">{item['value']:,.2f}</span>
                <span style="color:{color}; margin-left:6px;">{arrow} {abs(item['change_pct']):.2f}%</span>
            </span>
            """
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