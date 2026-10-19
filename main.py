import json
import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="전국 고령화 단계구분도", layout="wide")
st.title("📊 전국 시군구별 고령화율 단계구분도 (2026년 기준)")


@st.cache_data
def load_data():
    # 1. GeoJSON 데이터 가져오기 (Raw URL)
    geojson_url = "https://raw.githubusercontent.com/linass0103/population/main/sigungu_kr.geojson.txt"
    geojson_res = requests.get(geojson_url)
    geojson_data = geojson_res.json()

    # 2. 인구 CSV 데이터 읽기 (Raw URL / Zip 압축)
    # GitHub Blob URL -> Raw URL 변환
    pop_url = "https://raw.githubusercontent.com/linass0103/population/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url, compression="zip")

    # '연도' 열이 존재할 경우 2026년 데이터만 추출 (숫자 또는 문자열 처리)
    if "연도" in df.columns:
        df = df[df["연도"].astype(str) == "2026"]

    # 코드 열 5자리 시군구 코드로 변환 (문자열 보장 및 빈자리 0 채움)
    df["sigungu_code"] = (
        df["코드"].astype(str).str.split(".").str[0].str.zfill(8).str[:5]
    )

    # 계_로 시작하는 열들 탐색
    total_age_cols = [c for c in df.columns if c.startswith("계_")]

    # 65세 이상 열 탐색 (계_65세 ~ 계_100세 이상)
    over_65_cols = []
    for col in total_age_cols:
        match = re.search(r"계_(\d+)세", col)
        if match:
            age = int(match.group(1))
            if age >= 65:
                over_65_cols.append(col)
        elif "100세 이상" in col:
            over_65_cols.append(col)

    # 시군구 코드별로 인구 합산
    group_cols = total_age_cols
    agg_df = df.groupby("sigungu_code")[group_cols].sum().reset_index()

    # 전체 인구 및 65세 이상 인구 계산
    agg_df["total_pop"] = agg_df[total_age_cols].sum(axis=1)
    agg_df["over_65_pop"] = agg_df[over_65_cols].sum(axis=1)

    # 고령화율(%) 계산
    agg_df["elderly_ratio"] = (
        agg_df["over_65_pop"] / agg_df["total_pop"]
    ) * 100
    agg_df["elderly_ratio"] = agg_df["elderly_ratio"].round(2)

    # GeoJSON의 시군구 이름 매핑 생성 (툴팁 표시용)
    code_to_name = {}
    for feature in geojson_data["features"]:
        props = feature["properties"]
        code = str(props.get("코드", ""))
        name = f"{props.get('시도', '')} {props.get('시군구', '')}".strip()
        code_to_name[code] = name

    agg_df["시군구명"] = agg_df["sigungu_code"].map(code_to_name)

    return geojson_data, agg_df


# 데이터 로드
with st.spinner("데이터를 불러오는 중입니다..."):
    geojson_data, df_ratio = load_data()

# Plotly Choropleth 생성
fig = px.choropleth(
    df_ratio,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="elderly_ratio",
    color_continuous_scale="Reds",
    hover_data={"sigungu_code": False, "시군구명": True, "elderly_ratio": True},
    labels={"elderly_ratio": "고령화율 (%)", "시군구명": "지역명"},
)

# 배경 타일 및 지도 스타일 설정 (타일 없이 경계만 표시)
fig.update_geos(
    visible=False,
    fitbounds="locations",
)

fig.update_layout(
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
    coloraxis_colorbar=dict(title="고령화율 (%)"),
)

# 스트림릿 화면에 출력
st.plotly_chart(fig, use_container_width=True)
