# 표준 라이브러리
import datetime
from io import BytesIO

# 서드파티 라이브러리
import datetime
from io import BytesIO
import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import koreanize_matplotlib
import os
from dotenv import load_dotenv
load_dotenv() # .env에 있는 환경 변수를 읽어옴 

st.set_page_config(layout="wide")

my_name = os.getenv("MY_NAME")

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("📊 주식 분석 대시보드")
    my_name = os.getenv("MY_NAME", "Guest") # 환경변수 없으면 Guest
    st.write(f"환영합니다, **{my_name}**님!")
    
    company_name = st.text_input('조회할 회사를 입력하세요')

    today = datetime.date.today()
    last_year = today - datetime.timedelta(days=365)
    selected_dates = st.date_input(
        '날짜를 입력하세요 (시작일 - 종료일)',
        value=[last_year, today]  
    )
    
    confirm_btn = st.button(label='조회하기')

def get_krx_company_list() -> pd.DataFrame:
    try:
        # 파이썬 및 인터넷 기본 문자열 인코딩 방식 : UTF-8
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        
        df_listing = pd.read_html(url, header=0, flavor='bs4', encoding='EUC-KR')[0]
        
        # 필요한 컬럼만 추출 및 종목코드 6자리 포맷 맞추기
        df_listing = df_listing[['회사명', '종목코드']].copy()
        df_listing['종목코드'] = df_listing['종목코드'].apply(lambda x: f'{x:06}')
        return df_listing
    except Exception as e:
        st.error(f"상장사 명단을 불러오는 데 실패했습니다: {e}")
        return pd.DataFrame(columns=['회사명', '종목코드'])

def get_stock_code_by_company(company_name: str) -> str:
    # 만약 입력값이 숫자 6자리라면 그대로 반환
    if company_name.isdigit() and len(company_name) == 6:
        return company_name
    
    company_df = get_krx_company_list()
    codes = company_df[company_df['회사명'] == company_name]['종목코드'].values
    if len(codes) > 0:
        return codes[0]
    else:
        raise ValueError(f"'{company_name}'을 찾을 수 없습니다. 종목코드 6자리를 직접 입력해보세요.")


# --- 메인 로직 ---
if confirm_btn:
    if not company_name:
        st.warning("조회할 회사 이름을 입력하세요.")
    elif len(selected_dates) != 2:
        st.warning("시작 날짜와 종료 날짜를 모두 선택해주세요.")
    else:
        try:
            with st.spinner('데이터를 수집하는 중...'):
                stock_code = get_stock_code_by_company(company_name)
                start_date = selected_dates[0].strftime("%Y%m%d")
                end_date = selected_dates[1].strftime("%Y%m%d")
                
                price_df = fdr.DataReader(stock_code, start_date, end_date)
                
            if price_df.empty:
                st.info("해당 기간의 주가 데이터가 없습니다.")
            else:
                # 1. 이동평균선 계산 (Feature Engineering)
                price_df['MA5'] = price_df['Close'].rolling(window=5).mean()
                price_df['MA20'] = price_df['Close'].rolling(window=20).mean()

                # 2. 주요 지표 표시 (Metric)
                st.title(f"📈 {company_name} ({stock_code})")
                
                last_close = price_df['Close'].iloc[-1]
                start_close = price_df['Close'].iloc[0]
                change = last_close - start_close
                pct_change = (change / start_close) * 100
                max_price = price_df['High'].max()
                min_price = price_df['Low'].min()

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("현재 주가 (종가)", f"{last_close:,.0f}원", f"{pct_change:.2f}%")
                col2.metric("기간 내 변동", f"{change:,.0f}원")
                col3.metric("최고가", f"{max_price:,.0f}원")
                col4.metric("최저가", f"{min_price:,.0f}원")

                st.divider() # 구분선

                # 3. 탭 구성
                tab1, tab2 = st.tabs(["📈 차트 분석", "📋 데이터 원본"])

                with tab1:
                    # --- Plotly 차트 그리기 ---
                    # 캔들스틱(위) + 거래량(아래) 구조 잡기
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.05, 
                                        row_heights=[0.7, 0.3],
                                        subplot_titles=('주가 추이 & 이동평균선', '거래량'))

                    # (1) 캔들스틱 차트
                    fig.add_trace(go.Candlestick(x=price_df.index,
                                    open=price_df['Open'], high=price_df['High'],
                                    low=price_df['Low'], close=price_df['Close'],
                                    name='주가'), row=1, col=1)

                    # (2) 이동평균선 추가
                    fig.add_trace(go.Scatter(x=price_df.index, y=price_df['MA5'], 
                                             opacity=0.7, line=dict(color='blue', width=1), name='5일 이동평균'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=price_df.index, y=price_df['MA20'], 
                                             opacity=0.7, line=dict(color='orange', width=1), name='20일 이동평균'), row=1, col=1)

                    # (3) 거래량 바 차트
                    colors = ['red' if row['Open'] - row['Close'] >= 0 else 'blue' for index, row in price_df.iterrows()]
                    fig.add_trace(go.Bar(x=price_df.index, y=price_df['Volume'], 
                                         marker_color=colors, name='거래량'), row=2, col=1)

                    # 레이아웃 다듬기
                    fig.update_layout(title=f'{company_name} 주가 분석', xaxis_rangeslider_visible=False, height=600)
                    
                    # Streamlit에 표시
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.dataframe(price_df.sort_index(ascending=False), use_container_width=True)
                    
                    # 엑셀 다운로드
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        price_df.to_excel(writer, index=True, sheet_name='Sheet1')
                    
                    st.download_button(
                        label="📥 엑셀 파일 다운로드",
                        data=output.getvalue(),
                        file_name=f"{company_name}_{today}.xlsx",
                        mime="application/vnd.ms-excel"
                    )

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")