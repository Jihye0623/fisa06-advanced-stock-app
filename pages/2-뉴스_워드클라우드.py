import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os

# 페이지 설정
st.set_page_config(page_title="뉴스 워드클라우드", page_icon="📰", layout="wide")

st.title("📰 뉴스 & 워드클라우드 분석")
st.markdown("### \"지금 시장은 이 종목을 어떻게 말할까?\" 🗣️")

# --- 유틸리티: 한글 폰트 설정 (Streamlit Cloud용) ---
def get_font_path():
    # 현재 폴더에 폰트 파일이 없으면 다운로드 (나눔고딕)
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

# --- 유틸리티: 상장사 목록 (캐싱) ---
@st.cache_data
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

# --- 핵심: 네이버 금융 뉴스 크롤링 ---
def get_news_data(company_name):
    try:
        # 구글 뉴스 RSS 주소 (검색어 쿼리 방식)
        # hl=ko: 한국어, gl=KR: 한국 지역, ceid=KR:ko: 한국어 에디션
        url = f"https://news.google.com/rss/search?q={company_name}&hl=ko&gl=KR&ceid=KR:ko"
        
        resp = requests.get(url)
        
        # XML 형식의 데이터를 파싱합니다.
        soup = BeautifulSoup(resp.text, "xml")
        
        news_list = []
        items = soup.select("item") 
        
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date = item.pubDate.text
            
            news_list.append({'title': title, 'link': link})
            
        return news_list

    except Exception as e:
        st.error(f"구글 뉴스 가져오기 실패: {e}")
        return []

# --- UI 구성 ---
company_name = st.text_input("종목명 입력", "카카오")

if st.button("뉴스 분석하기 🔍", use_container_width=True):
    df_krx = get_krx_company_list()
    code = get_stock_code(company_name, df_krx)
    
    if code:
        with st.spinner(f"{company_name}의 최신 뉴스를 수집하고 있습니다..."):
            news_data = get_news_data(company_name)
            
            if not news_data:
                st.warning("최신 뉴스가 없거나 가져올 수 없습니다.")
            else:
                st.success(f"총 {len(news_data)}개의 최신 뉴스를 가져왔습니다!")
                
                # 레이아웃 분할 (왼쪽: 워드클라우드, 오른쪽: 뉴스 리스트)
                col1, col2 = st.columns([1.2, 1])
                
                with col1:
                    st.subheader("☁️ 뉴스 키워드 클라우드")
                    
                    # 1. 모든 제목을 하나의 문자열로 합치기
                    all_text = " ".join([item['title'] for item in news_data])
                    
                    # 2. 워드클라우드 생성
                    font_path = get_font_path()
                    
                    # 불용어(제외할 단어) 설정 
                    stopwords = {'속보', '특징주', '종목', '분기', '실적', '발표', '공시'}
                    
                    wc = WordCloud(
                        font_path=font_path,
                        width=800, height=600,
                        background_color='white',
                        stopwords=stopwords
                    ).generate(all_text)
                    
                    # 3. 그림 그리기
                    fig = plt.figure(figsize=(10, 8))
                    plt.imshow(wc, interpolation='bilinear')
                    plt.axis('off') # 축 제거
                    st.pyplot(fig)
                    
                with col2:
                    st.subheader("📰 최신 뉴스 헤드라인")
                    # 뉴스 리스트 출력
                    for idx, news in enumerate(news_data):
                        # 링크를 클릭할 수 있게 마크다운으로 표시
                        st.markdown(f"{idx+1}. [{news['title']}]({news['link']})")
                        if idx >= 9: # 10개까지만 보여줌
                            break
                            
    else:
        st.error("정확한 종목명을 입력해주세요.")