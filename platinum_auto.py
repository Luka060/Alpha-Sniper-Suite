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
st.markdown("### 「流動性是獲利的氧氣，只做大人在玩的股票。」")

# ==========================================
# 側邊欄：參數
# ==========================================
st.sidebar.header("⚙️ 戰情室參數")

# 1. 掃描設定
st.sidebar.subheader("💎 神股掃描設定")
min_volume = st.sidebar.number_input("最小成交量 (萬股)", value=100, step=50, help="低於此成交量的冷門股會被過濾掉") * 10000

# 2. 家人持股
st.sidebar.subheader("👨‍👩‍👧‍👦 家人持股")
default_family = "ZETA, NBIS"
family_input = st.sidebar.text_area("家人監控清單", default_family)
family_list = [x.strip().upper() for x in family_input.split(',')]

# 3. ETF
st.sidebar.subheader("🛡️ ETF 戰略指揮部")
default_etf = "VOO, QQQ, 0050.TW, 2563.T, 2558.T"
etf_input = st.sidebar.text_area("ETF 清單", default_etf)
etf_list = [x.strip().upper() for x in etf_input.split(',')]

# 4. 觀察名單
st.sidebar.subheader("⚡ 市場觀察名單")
default_watch = "NVDA, TSLA, AAPL, MSFT, PLTR, TSM, JPM, AMD, AMZN, META, GOOGL"
watch_input = st.sidebar.text_area("觀察名單", default_watch)
watchlist = [x.strip().upper() for x in watch_input.split(',')]

st.sidebar.markdown("---")
with st.sidebar.expander("📖 評分與篩選說明", expanded=True):
    st.markdown("""
    ### 🏆 90分神股條件
    1. **趨勢:** 股價 > 50MA > 200MA (絕對多頭)
    2. **動能:** RSI 在 50-75 之間 (強勢但不失控)
    3. **籌碼:** 成交量 > 設定門檻 (拒絕冷門股)
    
    ### 🛑 交易計畫
    - **Stop (止損):** 2倍 ATR
    - **Target (目標):** 3倍 ATR
    """)

# ==========================================
# 核心邏輯
# ==========================================
def analyze_god_mode(ticker):
    if ticker == "FIG": return {"Error": "FIGMA 未上市"}
    
    try:
        stock = yf.Ticker(ticker)
        # 抓多一點資料算均線
        df = stock.history(period="2y", interval="1d", auto_adjust=False)
        
        if df.empty or len(df) < 50: return {"Error": "資料不足"}

        # --- 0. 流動性過濾 (Liquidity Check) ---
        # 計算過去 5 天的平均成交量
        avg_volume = df['Volume'].tail(5).mean()
        if avg_volume < min_volume:
            return {"Error": f"成交量不足 ({int(avg_volume/10000)}萬股)", "LowVol": True}

        # 幣別處理
        currency = "$"
        if ".T" in ticker or ".F" in ticker: currency = "¥"
        elif ".TW" in ticker: currency = "NT$"
        
        # 基金判斷
        is_fund = (df['High'].iloc[-1] == df['Low'].iloc[-1]) and ("0050" not in ticker)

        # --- 1. 指標計算 ---
        df['SMA_20'] = SMAIndicator(df['Close'], 20).sma_indicator()
        df['SMA_50'] = SMAIndicator(df['Close'], 50).sma_indicator()
        df['SMA_200'] = SMAIndicator(df['Close'], 200).sma_indicator()
        
        df['RSI'] = RSIIndicator(df['Close'], 14).rsi()
        macd = MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        
        df['ATR'] = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
        bb = BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_Up'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        
        # 肯特納通道 (Squeeze)
        df['KC_Up'] = df['SMA_20'] + (1.5 * df['ATR'])
        df['KC_Low'] = df['SMA_20'] - (1.5 * df['ATR'])
        df['Squeeze_On'] = (df['BB_Up'] < df['KC_Up']) & (df['BB_Low'] > df['KC_Low'])

        # --- 2. 當前數據 ---
        curr = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        rsi = df['RSI'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        sma50 = df['SMA_50'].iloc[-1]
        sma200 = df['SMA_200'].iloc[-1]
        is_squeeze = df['Squeeze_On'].iloc[-1]

        # --- 3. AI 評分系統 (0-100) ---
        score = 0
        reasons = []
        
        # A. 趨勢 (Trend)
        if curr > sma50: 
            score += 20
            if sma200 > 0 and curr > sma200:
                score += 20
                if sma50 > sma200: # 均線多頭排列
                    score += 10
                    reasons.append("✅ 均線完美多頭排列")
                else:
                    reasons.append("✅ 站上年線與季線")
            else:
                reasons.append("⚠️ 站上季線但受壓年線")
        else:
            reasons.append("❌ 趨勢偏空 (季線下)")
            
        # B. 動能 (Momentum)
        if 50 <= rsi <= 75:
            score += 30
            reasons.append("✅ RSI 動能強勁")
        elif rsi < 30:
            score += 20
            reasons.append("💎 超賣反彈機會")
        elif rsi > 80:
            score -= 10
            reasons.append("⚠️ RSI 過熱風險")
            
        # C. 結構 (Structure)
        if is_squeeze:
            score += 10
            reasons.append("🔥 能量壓縮中")
        if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1]:
            score += 10
            reasons.append("✅ MACD 黃金交叉")

        # 確保分數上限 100
        score = min(score, 100)

        # 交易計畫
        stop_loss = curr - (2 * atr)
        take_profit = curr + (3 * atr)
        risk_reward = (take_profit - curr) / (curr - stop_loss)

        card_color = "gray"
        if score >= 90: card_color = "green" # 神股
        elif score <= 50: card_color = "red"
        elif score >= 70: card_color = "blue"

        return {
            "Ticker": ticker, "Price": round(curr, 2), "Symbol": currency,
            "Change%": round(((curr-prev)/prev)*100, 2),
            "Score": score, "Color": card_color, "Reasons": reasons,
            "Squeeze": is_squeeze, "RSI": round(rsi, 2),
            "Volume": int(avg_volume),
            "Plan": {"Stop": round(stop_loss, 2), "Target": round(take_profit, 2)},
            "Data": df, "IsFund": is_fund
        }
    except Exception as e: return {"Error": str(e)}

# --- 繪圖函式 ---
def draw_chart(item):
    df = item['Data'].tail(150)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    if item['IsFund']:
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='white'), name='Price'), row=1, col=1)
    else:
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_line_color='red', decreasing_line_color='green', name='Price'), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='blue', width=1), name='50MA'), row=1, col=1)
    atr_stop = df['Close'] - (2 * df['ATR'])
    fig.add_trace(go.Scatter(x=df.index, y=atr_stop, line=dict(color='cyan', width=1, dash='dot'), name='ATR 止損'), row=1, col=1)

    sqz_colors = ['red' if s else 'gray' for s in df['Squeeze_On']]
    fig.add_trace(go.Scatter(x=df.index, y=[0]*len(df), mode='markers', marker=dict(color=sqz_colors, size=6), name='SQZ'), row=2, col=1)
    colors = ['red' if v < 0 else 'green' for v in df['MACD'] - df['MACD_Signal']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD'] - df['MACD_Signal'], marker_color=colors, name='動能'), row=2, col=1)

    fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    return fig

# ==========================================
# 主程式
# ==========================================
if st.button('🚀 啟動 90分神股掃描 (God Mode)'):
    
    # 建立掃描池 (包含用戶清單 + 內建熱門股)
    # 我們加入一些美股大型權值股，確保掃描池夠大
    market_pool = [
        "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD", "AVGO", "COST", 
        "JPM", "NFLX", "PLTR", "MSTR", "COIN", "SMCI", "ARM", "INTC", "TSM", "V", "MA",
        "LLY", "UNH", "XOM", "CVX", "HD", "PG", "KO", "PEP", "MRK"
    ]
    # 合併清單並去重
    full_scan_list = list(set(family_list + etf_list + watchlist + market_pool))
    
    st.markdown("## 💎 90分神股掃描結果")
    st.info(f"正在掃描 {len(full_scan_list)} 檔標的，篩選條件：成交量 > {int(min_volume/10000)}萬股 且 評分 >= 90...")
    
    found_gems = []
    
    # 進度條
    prog = st.progress(0)
    
    for i, t in enumerate(full_scan_list):
        if not t: continue
        item = analyze_god_mode(t)
        prog.progress((i+1)/len(full_scan_list))
        
        # 篩選邏輯：只要分數 >= 90 且沒有錯誤
        if item and "Error" not in item:
            if item['Score'] >= 90:
                found_gems.append(item)
    
    # 顯示結果
    if not found_gems:
        st.warning("⚠️ 目前市場上沒有符合「90分 + 高流動性」的完美標的。建議觀望或降低標準。")
    else:
        st.success(f"🎉 恭喜！發現 {len(found_gems)} 檔神級股票！")
        # 依分數排序
        found_gems.sort(key=lambda x: x['Score'], reverse=True)
        
        for item in found_gems:
            sym = item['Symbol']
            header = f"🌟 {item['Ticker']} | {item['Score']}分 | {sym}{item['Price']} ({item['Change%']}%)"
            
            with st.expander(header, expanded=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("AI 評分", f"{item['Score']} / 100")
                    st.write(f"**成交量:** {int(item['Volume']/10000)} 萬股")
                    st.write("**🔥 入選理由:**")
                    for r in item['Reasons']:
                        st.caption(r)
                    
                    st.divider()
                    st.markdown("### 🛑 交易計畫")
                    st.metric("止損 (Stop)", f"{sym}{item['Plan']['Stop']}")
                    st.metric("目標 (Target)", f"{sym}{item['Plan']['Target']}")
                
                with c2:
                    st.plotly_chart(draw_chart(item), use_container_width=True)
    
    st.divider()
    
    # 下方顯示原本的清單 (只顯示簡單版，避免太長)
    st.markdown("### ⚡ 您的觀察名單 (快速檢視)")
    cols = st.columns(4)
    for i, t in enumerate(watchlist):
        item = analyze_god_mode(t)
        if item and "Error" not in item:
            color = item['Color']
            emoji = "🟢" if color == "green" else "🔴" if color == "red" else "⚪"
            cols[i % 4].metric(f"{emoji} {t}", f"{item['Score']}分", f"{item['Change%']}%")

else:
    st.info("👋 點擊按鈕，開始從全市場挖掘 90 分以上的獲利機會。")
