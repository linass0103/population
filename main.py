import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide"
)

st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.caption("전국 읍·면·동의 최신 인구 구조를 인구 피라미드 그래프와 지표로 확인해 보세요.")

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 및 전처리
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # GitHub raw 파일 주소
    url = "https://github.com/linass0103/population/raw/main/population_ts_yearly_gender.zip"
    
    # zip 파일 자동 압축 해제 후 로드
    df = pd.read_csv(url, compression='zip')
    
    # 가장 최신 연도만 추출
    latest_year = df['연도'].max()
    df_latest = df[df['연도'] == latest_year].copy()
    
    return df_latest, latest_year

with st.spinner("데이터를 불러오는 중입니다... 잠시만 기다려 주세요!"):
    df, latest_year = load_data()

st.sidebar.markdown(f"🗓️ **기준 연도:** {latest_year}년")

# -----------------------------------------------------------------------------
# 3. 드롭다운 메뉴 (시도 → 시군구 → 동 3단계 연동)
# -----------------------------------------------------------------------------
st.subheader("📍 지역 선택")

sido_list = sorted(df['시도'].dropna().unique())
selected_sido = st.selectbox("1. 시·도를 선택하세요", sido_list)

sigungu_df = df[df['시도'] == selected_sido]
sigungu_list = sorted(sigungu_df['시군구'].dropna().unique())
selected_sigungu = st.selectbox("2. 시·군·구를 선택하세요", sigungu_list)

dong_df = sigungu_df[sigungu_df['시군구'] == selected_sigungu]
dong_list = sorted(dong_df['동'].dropna().unique())
selected_dong = st.selectbox("3. 읍·면·동을 선택하세요", dong_list)

# 선택된 동네 데이터 1행 추출
target_data = dong_df[dong_df['동'] == selected_dong].iloc[0]

# -----------------------------------------------------------------------------
# 4. 나이 및 남/여 인구 데이터 추출 & 주요 지표 계산
# -----------------------------------------------------------------------------
age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_pop = []
female_pop = []

# 각 나이별 인구 수 수집 및 지표 계산용 데이터 가공
total_weighted_age_sum = 0  # (나이 * 인구수) 총합 (평균연령 계산용)
pop_under_15 = 0            # 0~14세 인구수 (유소년)
pop_65_and_over = 0         # 65세 이상 인구수 (고령)

for idx, age_str in enumerate(age_labels):
    # 100세 이상은 평균연령 계산 시 100세로 계산
    age_num = 100 if idx == 100 else idx
    
    male_col = f"남_{age_str}"
    female_col = f"여_{age_str}"
    
    m_val = target_data[male_col] if male_col in target_data else 0
    f_val = target_data[female_col] if female_col in target_data else 0
    
    # 음수/누락값 예외 처리
    m_val = max(0, int(m_val)) if pd.notnull(m_val) else 0
    f_val = max(0, int(f_val)) if pd.notnull(f_val) else 0
    
    age_total_pop = m_val + f_val
    
    male_pop.append(m_val)
    female_pop.append(f_val)
    
    # 평균연령 계산을 위한 (나이 x 인구수) 누적
    total_weighted_age_sum += age_num * age_total_pop
    
    # 연령대별 그룹 인구 수 누적
    if age_num < 15:
        pop_under_15 += age_total_pop
    if age_num >= 65:
        pop_65_and_over += age_total_pop

total_pop = sum(male_pop) + sum(female_pop)

# 지표 계산 (총인구가 0인 예외 상황 대처)
if total_pop > 0:
    avg_age = total_weighted_age_sum / total_pop
    aging_rate = (pop_65_and_over / total_pop) * 100
else:
    avg_age = 0.0
    aging_rate = 0.0

# -----------------------------------------------------------------------------
# 5. 그래프 상단 지표 카드 3개 표시
# -----------------------------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)

# 카드 1: 총인구
col1.metric("👥 총인구", f"{total_pop:,} 명")

# 카드 2: 평균연령
col2.metric("🎂 평균연령", f"{avg_age:.1f} 세")

# 카드 3: 고령화율 (20% 이상이면 주의 표시)
if aging_rate >= 20.0:
    col3.metric(
        label="👵 고령화율 (65세 이상)",
        value=f"{aging_rate:.1f} %",
        delta="🚨 초고령사회 (주의)",
        delta_color="inverse"
    )
else:
    col3.metric(
        label="👵 고령화율 (65세 이상)",
        value=f"{aging_rate:.1f} %"
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. Plotly 인구 피라미드 그래프 그리기
# -----------------------------------------------------------------------------
# 남성 인구수는 좌측 배치를 위해 음수(-) 변환
male_pop_neg = [-val for val in male_pop]

fig = go.Figure()

# 남성 (좌측 막대 - 따뜻한 네이비/코발트 톤)
fig.add_trace(go.Bar(
    y=age_labels,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    hoverinfo='text',
    hovertext=[f"남성 {age}: {abs(val):,}명" for age, val in zip(age_labels, male_pop)],
    marker=dict(color='#4A7BB0')
))

# 여성 (우측 막대 - 따뜻한 코랄/핑크 톤)
fig.add_trace(go.Bar(
    y=age_labels,
    x=female_pop,
    name='여성',
    orientation='h',
    hoverinfo='text',
    hovertext=[f"여성 {age}: {val:,}명" for age, val in zip(age_labels, female_pop)],
    marker=dict(color='#E88A8A')
))

# -----------------------------------------------------------------------------
# 7. 세로축(y축) 순서 고정 및 레이아웃 설정
# -----------------------------------------------------------------------------
# categoryarray를 사용해 0세가 맨 아래, 100세 이상이 맨 위로 고정되도록 합니다.
max_val = max(male_pop + female_pop) if (male_pop or female_pop) else 1

fig.update_layout(
    title=dict(
        text=f"<b>[{selected_sido} {selected_sigungu} {selected_dong}]</b> 인구 피라미드 ({latest_year}년)",
        font=dict(size=20)
    ),
    barmode='relative',
    bargap=0.1,
    xaxis=dict(
        title='인구수 (명)',
        tickvals=[-max_val, -max_val//2, 0, max_val//2, max_val],
        ticktext=[f"{abs(v):,}" for v in [-max_val, -max_val//2, 0, max_val//2, max_val]]
    ),
    yaxis=dict(
        title='연령 (세)',
        type='category',
        categoryorder='array',
        categoryarray=age_labels,  # 0세 -> 100세 이상 순서 고정
        dtick=10                  # 10세 단위 눈금 표시
    ),
    legend=dict(
        x=0.85,
        y=1.1,
        orientation='h'
    ),
    height=750,
    margin=dict(l=50, r=50, t=80, b=50)
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 8. 그래프 하단 자동 한 줄 설명 (아이 vs 어르신 비율 비교)
# -----------------------------------------------------------------------------
child_rate = (pop_under_15 / total_pop * 100) if total_pop > 0 else 0
senior_rate = (pop_65_and_over / total_pop * 100) if total_pop > 0 else 0

# 비율 비교에 따른 자동 안내 문구 생성
if child_rate > senior_rate:
    summary_text = (
        f"💡 **이 동네는 아이가 상대적으로 많은 편입니다!** "
        f"(15세 미만 아이 비율 **{child_rate:.1f}%** vs 65세 이상 어르신 비율 **{senior_rate:.1f}%**)"
    )
    st.info(summary_text)
elif senior_rate > child_rate:
    summary_text = (
        f"💡 **이 동네는 어르신이 상대적으로 많은 편입니다.** "
        f"(65세 이상 어르신 비율 **{senior_rate:.1f}%** vs 15세 미만 아이 비율 **{child_rate:.1f}%**)"
    )
    st.warning(summary_text)
else:
    summary_text = (
        f"💡 **이 동네는 아이와 어르신의 비율이 비슷한 편입니다.** "
        f"(각각 전체 인구의 약 **{child_rate:.1f}%** 차지)"
    )
    st.success(summary_text)
