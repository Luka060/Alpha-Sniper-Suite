import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

# --- 頁面設定 ---
st.set_page_config(page_title="Alpha Sniper God Mode", layout="wide")
st.title("👁️ Alpha Sniper God Mode - 天眼操盤系統")
st.markdown("### 「不打沒把握的仗。只做勝率 > 80% 的狙擊。」")

# ==========================================
# 側邊欄：參數
# ==========================================
st.sidebar.header("⚙️ 戰情室參數")

# 1. 家人持股
st.sidebar.subheader("👨‍👩‍👧‍👦 家人持股")
default_family = "ZETA, NBIS"
family_input = st.sidebar.text_area("家人監控清單", default_family)
family_list = [x.strip().upper() for x in family_input.split(',')]

# 2. ETF
st.sidebar.subheader("🛡️ ETF 戰略指揮部")
default_etf = "VOO, QQQ, 0050.TW, 2563.T, 2558.T"
etf_input = st.sidebar.text_area("ETF 清單", default_etf)
etf_list = [x.strip().upper() for x in etf_input.split(',')]

# 3. 觀察名單
st.sidebar.subheader("⚡ 市場觀察名單")
default_watch = "NVDA, TSLA, AAPL, MSFT, PLTR, TSM, JPM"
watch_input = st.sidebar.text_area("觀察名單", default_watch)
watchlist = [x.strip().upper() for x in watch_input.split(',')]

st.sidebar.markdown("---")
with st.sidebar.expander("📖 天眼使用說明書 (必讀)", expanded=True):
    st.markdown("""
    ### 1. 🏆 勝率評分 (Score)
    - **90-100分:** 🌟 **天選之單** (重倉)
    - **80-90分:** 🚀 **優質交易** (標準)
    - **< 70分:** 🗑️ **垃圾時間** (觀望)
    
    ### 2. ⚡ SQZ 擠壓訊號
    - **紅色點:** 能量壓縮中 (暴漲前兆)
    - **灰色點:** 能量釋放中
    
    ### 3. 🛑 交易計畫 (ATR)
    - **止損 (Stop):** 跌破這裡一定要跑
    - **目標 (Target):** 漲到這裡分批止盈
    """)

# ==========================================
# 核心邏輯：天眼演算法
# ==========================================
def analyze_god_mode(ticker):
    if ticker == "FIG": return {"Error": "FIGMA 未上市"}
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y", interval="1d", auto_adjust=False)
        
        if df.empty or len(df) < 50: return {"Error": "資料不足"}

        # 幣別與名稱處理
        currency = "$"
        if ".T" in ticker or ".F" in ticker: currency = "¥"
        elif ".TW" in ticker: currency = "NT$"
        
        # 基金判斷
        is_fund = (df['High'].iloc[-1] == df['Low'].iloc[-1]) and ("0050" not in ticker)

        # --- 1. 計算高階指標 ---
        # 均線
        df['SMA_20'] = SMAIndicator(df['Close'], 20).sma_indicator()
        df['SMA_50'] = SMAIndicator(df['Close'], 50).sma_indicator()
        df['SMA_200'] = SMAIndicator(df['Close'], 200).sma_indicator()
        
        # RSI & MACD
        df['RSI'] = RSIIndicator(df['Close'], 14).rsi()
        macd = MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        
        # 波動率 (ATR & BB)
        df['ATR'] = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
        bb = BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_Up'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        df['BB_Width'] = (df['BB_Up'] - df['BB_Low']) / df['SMA_20']
        
        # 肯特納通道 (Keltner Channels) - 用於判斷擠壓
        df['KC_Up'] = df['SMA_20'] + (1.5 * df['ATR'])
        df['KC_Low'] = df['SMA_20'] - (1.5 * df['ATR'])
        
        # SQZ 擠壓訊號: 當布林帶跑進肯特納通道內，代表極度壓縮
        df['Squeeze_On'] = (df['BB_Up'] < df['KC_Up']) & (df['BB_Low'] > df['KC_Low'])

        # --- 2. 取得當前數據 ---
        curr = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        rsi = df['RSI'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        sma50 = df['SMA_50'].iloc[-1]
        sma200 = df['SMA_200'].iloc[-1]
        is_squeeze = df['Squeeze_On'].iloc[-1]

        # --- 3. AI 勝率評分系統 (0-100) ---
        score = 0
        reasons = []
        
        # A. 趨勢分數 (Trend) - 40分
        if curr > sma50: 
            score += 20
            if curr > sma200:
                score += 20
                reasons.append("✅ 多頭排列")
            else:
                reasons.append("⚠️ 站上季線但受壓年線")
        else:
            reasons.append("❌ 空頭趨勢 (季線下)")
            
        # B. 動能分數 (Momentum) - 30分
        if 50 <= rsi <= 70:
            score += 30
            reasons.append("✅ 動能強勁且健康")
        elif rsi < 30:
            score += 20
            reasons.append("💎 超賣反彈機會")
        elif rsi > 75:
            score -= 10
            reasons.append("⚠️ RSI 過熱風險")
            
        # C. 結構分數 (Structure) - 30分
        if is_squeeze:
            score += 20
            reasons.append("🔥 能量壓縮中 (準備噴出)")
        if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1]:
            score += 10
            reasons.append("✅ MACD 黃金交叉")

        # --- 4. 交易計畫 (ATR Based) ---
        # 止損設在 2倍 ATR 之外，止盈設在 3倍 ATR
        stop_loss = curr - (2 * atr)
        take_profit = curr + (3 * atr)
        risk_reward = (take_profit - curr) / (curr - stop_loss) # 應該恆等於 1.5

        # 狀態顯示顏色
        card_color = "gray"
        if score >= 80: card_color = "green"
        elif score <= 40: card_color = "red"
        elif score >= 60: card_color = "blue"

        return {
            "Ticker": ticker, "Price": round(curr, 2), "Symbol": currency,
            "Change%": round(((curr-prev)/prev)*100, 2),
            "Score": score, "Color": card_color, "Reasons": reasons,
            "Squeeze": is_squeeze,
            "RSI": round(rsi, 2),
            "Plan": {
                "Stop": round(stop_loss, 2),
                "Target": round(take_profit, 2),
                "RR": round(risk_reward, 1)
            },
            "Data": df, "IsFund": is_fund
        }
    except Exception as e: return {"Error": str(e)}

# --- 繪圖函式 (含 ATR 通道) ---
def draw_chart(item):
    df = item['Data'].tail(150)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # K線
    if item['IsFund']:
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='white'), name='Price'), row=1, col=1)
    else:
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_line_color='red', decreasing_line_color='green', name='Price'), row=1, col=1)

    # 均線
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='blue', width=1), name='50MA'), row=1, col=1)
    
    # ATR 止損線 (動態防守)
    atr_stop = df['Close'] - (2 * df['ATR'])
    fig.add_trace(go.Scatter(x=df.index, y=atr_stop, line=dict(color='cyan', width=1, dash='dot'), name='ATR 止損線'), row=1, col=1)

    # 擠壓訊號 (Squeeze Dots)
    # 在 MACD 柱狀圖中間畫點，紅色=擠壓，灰色=正常
    sqz_colors = ['red' if s else 'gray' for s in df['Squeeze_On']]
    fig.add_trace(go.Scatter(x=df.index, y=[0]*len(df), mode='markers', 
                             marker=dict(color=sqz_colors, size=6), name='SQZ 訊號'), row=2, col=1)
    
    # MACD
    colors = ['red' if v < 0 else 'green' for v in df['MACD'] - df['MACD_Signal']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD'] - df['MACD_Signal'], marker_color=colors, name='動能柱'), row=2, col=1)

    fig.update_layout(height=450, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="價格 & 止損", row=1, col=1)
    fig.update_yaxes(title_text="動能 & 擠壓", row=2, col=1)
    return fig

# ==========================================
# 主程式
# ==========================================
if st.button('🚀 啟動天眼掃描 (God Mode)'):
    
    # 共用顯示函式
    def show_card(ticker_list, title):
        st.markdown(f"## {title}")
        for t in ticker_list:
            if not t: continue
            item = analyze_god_mode(t)
            
            if not item or "Error" in item:
                st.warning(f"❌ {t}: 無法讀取")
                continue
                
            sym = item['Symbol']
            # 自動展開條件: 分數高 或 有擠壓訊號
            is_expanded = item['Score'] >= 80 or item['Squeeze']
            
            # 標題加上分數
            header = f"🏆 {item['Score']}分 | {item['Ticker']} | {sym}{item['Price']} ({item['Change%']}%)"
            
            with st.expander(header, expanded=is_expanded):
                c1, c2 = st.columns([1, 2])
                with c1:
                    # 1. 評分系統
                    st.metric("AI 勝率評分", f"{item['Score']} / 100", 
                              delta="天選之單" if item['Score']>=90 else "需謹慎", 
                              delta_color="normal" if item['Score']>=80 else "off")
                    
                    st.write("**📝 評分理由:**")
                    for r in item['Reasons']:
                        st.caption(f"{r}")
                    
                    st.divider()
                    
                    # 2. 交易計畫 (God Mode 核心)
                    st.markdown("### 🛑 操盤計畫")
                    st.metric("建議止損 (Stop)", f"{sym}{item['Plan']['Stop']}", help="跌破這裡代表趨勢改變，必須離場")
                    st.metric("獲利目標 (Target)", f"{sym}{item['Plan']['Target']}", help="預期可以漲到的位置")
                    
                    if item['Squeeze']:
                        st.error("🔥 波動擠壓中！即將變盤，密切注意！")
                    
                with c2:
                    st.plotly_chart(draw_chart(item), use_container_width=True)

    # 執行三個區塊
    show_card(etf_list, "🛡️ ETF 戰略指揮部")
    st.divider()
    show_card(family_list, "👨‍👩‍👧‍👦 家人持股衛士")
    st.divider()
    show_card(watchlist, "⚡ 市場觀察名單")

else:
    st.info("👋 Alpha Sniper God Mode 已就緒。點擊上方按鈕開啟天眼。")
