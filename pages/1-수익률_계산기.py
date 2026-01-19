import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import datetime
import plotly.graph_objects as go
import time

# 페이지 설정
st.set_page_config(page_title="수익률 계산기", page_icon="💰", layout="wide")

st.title("💰 수익률 계산기")
st.markdown("### \"내가 그때 그 주식을 샀더라면...\" 🤔")

# --- 유틸리티 함수 (app.py와 동일) ---
def get_krx_company_list():
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        df = pd.read_html(url, header=0, flavor='bs4', encoding='EUC-KR')[0]
        df = df[['회사명', '종목코드']]
        df['종목코드'] = df['종목코드'].apply(lambda x: f'{x:06}')
        return df
    except:
        return pd.DataFrame()

def get_stock_code(company_name, df):
    codes = df[df['회사명'] == company_name]['종목코드'].values
    return codes[0] if len(codes) > 0 else None

# --- 입력 UI ---
col1, col2 = st.columns(2)

with col1:
    company_name = st.text_input("종목명 (예: 삼성전자)", "삼성전자")
    investment_amount = st.number_input("투자 금액 (원)", min_value=10000, value=1000000, step=10000)

with col2:
    # 날짜 제한: 오늘로부터 최소 하루 전
    max_date = datetime.date.today() - datetime.timedelta(days=1)
    buy_date = st.date_input("매수 날짜 선택", value=datetime.date(2020, 1, 2), max_value=max_date)

if st.button("계산해보기 🚀", use_container_width=True):
    df_krx = get_krx_company_list()
    code = get_stock_code(company_name, df_krx)
    
    if code:
        # 진행바 애니메이션 시작
        progress_text = "분석을 시작합니다..."
        my_bar = st.progress(0, text=progress_text)

        # 1단계: 서버 연결 (0~30%)
        for percent_complete in range(30):
            time.sleep(0.01) # 0.01초씩 멈춤
            my_bar.progress(percent_complete + 1, text="KRX 서버에 연결 중입니다...")

        # 2단계: 실제 데이터 수집
        start_str = buy_date.strftime("%Y%m%d")
        df = fdr.DataReader(code, start_str)
        df = df[df['Open'] > 0]
        
        # 3단계: 데이터 수신 완료 애니메이션 (30~80%)
        for percent_complete in range(30, 80):
            time.sleep(0.01)
            my_bar.progress(percent_complete + 1, text=f"{company_name}의 과거 주가 데이터를 가져오는 중...")
            
        if df.empty:
            my_bar.empty() # 진행바 삭제
            st.error("해당 기간의 데이터가 없습니다. 날짜를 다시 확인해주세요.")
        else:
            
            for percent_complete in range(80, 100):
                time.sleep(0.01)
                my_bar.progress(percent_complete + 1, text="복리 수익률과 배당금을 계산하고 있습니다...")
            
            # --- 실제 계산 로직 ---
            real_buy_date = df.index[0]
            buy_price = df['Open'].iloc[0]
            current_date = df.index[-1]
            current_price = df['Close'].iloc[-1]
            
            shares = int(investment_amount / buy_price)
            remainder = int(investment_amount % buy_price)
            current_value = (shares * current_price) + remainder
            profit = current_value - investment_amount
            return_rate = (profit / investment_amount) * 100
            
            # 5단계: 완료 -> 진행바 꽉 채우고 잠시 후 삭제
            my_bar.progress(100, text="분석 완료!")
            time.sleep(0.5)
            my_bar.empty() # 진행바 깔끔하게 지우기

            st.divider()
            st.subheader(f"결과 리포트 ({real_buy_date.strftime('%Y-%m-%d')} 매수 가정)")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("총 투자금", f"{investment_amount:,.0f}원")
            m2.metric("보유 주식 수", f"{shares}주", help=f"매수가: {buy_price:,.0f}원")
            m3.metric("현재 평가액", f"{current_value:,.0f}원")
            
            if profit > 0:
                m4.metric("수익률", f"{return_rate:.2f}%", f"+{profit:,.0f}원", delta_color="normal")
            else:
                m4.metric("수익률", f"{return_rate:.2f}%", f"{profit:,.0f}원", delta_color="normal")

            # 자산 변동 그래프
            df['AssetValue'] = (df['Close'] * shares) + remainder
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, y=df['AssetValue'],
                mode='lines',
                name='내 자산',
                line=dict(color='#ff4b4b', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 75, 75, 0.1)' 
            ))
            fig.add_hline(y=investment_amount, line_dash="dash", line_color="gray", annotation_text="원금")
            fig.update_layout(
                title=f"💰 {company_name} 투자 시 자산 변동 추이",
                xaxis_title="날짜",
                yaxis_title="평가 금액 (원)",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 추가 애니메이션
            if return_rate > 50:
                st.balloons()  # 풍선 효과
                st.success("대박이네요! 밥 한 끼 사세요! 🍖")
            elif return_rate > 0:
                st.info("은행 이자보다는 낫네요! 👍")
            elif return_rate > -20:
                st.snow() # 눈 내리는 효과 
                st.warning("존버는 승리합니다... 화이팅! 😭")
            else:
                st.snow()
                st.error("아이고... 눈물이 앞을 가립니다... 💦")

    else:
        st.error("종목을 찾을 수 없습니다. 정확한 회사명을 입력해주세요.")