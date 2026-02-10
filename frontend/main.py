"""Streamlit 웹 대시보드 진입점."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가 (Streamlit Cloud 배포용)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import List
import time
import concurrent.futures

import requests
import streamlit as st

from common.config import BACKEND_URL
from backend.services.engine import get_dynamic_law_url


def render_law_badges(relevant_laws: List[str]) -> str:
    badges = []
    for law in relevant_laws:
        url = get_dynamic_law_url(law)
        badges.append(
            f"""
            <a href="{url}" target="_blank"
               style="display:inline-block; background:white; padding:6px 12px;
                      border-radius:8px; margin:4px; text-decoration:none;
                      font-size:0.9em; border:1px solid #90caf9; color:#0d47a1;
                      font-weight:600; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                📜 {law} ↗️
            </a>
            """
        )
    return "".join(badges)


def main() -> None:
    st.set_page_config(
        page_title="AI Independence Scanner",
        page_icon="🧭",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .status-pill {
            display:inline-block;
            padding:6px 14px;
            border-radius:999px;
            font-size:0.9em;
            font-weight:600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("AI 기반 감사 독립성 스캐너")
    st.caption("대형 회계법인 품질관리실 수준의 독립성 리스크 자동 판정 엔진")

    col1, col2 = st.columns([1.1, 1])

    with col1:
        st.subheader("1️⃣ 시나리오 입력")
        with st.expander("이렇게 작성하시면 됩니다 (펼쳐보기)", expanded=False):
            st.markdown(
                """
                **이렇게 작성하시면 됩니다.**
                - 누가 감사 대상인지 (예: C㈜, 건설·분양사업 등)
                - 우리 회계법인/부서가 어떤 역할인지 (감사본부, 세무본부 등)
                - 이해관계나 금전 거래가 어떻게 얽혀 있는지 (차입, 주식 보유 등)
                - 금액·관계의 크기를 대략적으로 적어주세요 (예: 7천만원 차입)

                아래 예시는 **실제 입력 예시**입니다.  
                👉 그대로 두고 바로 분석해도 되고, 상황에 맞게 일부만 수정하셔도 됩니다.
                """,
                unsafe_allow_html=False,
            )
        default_scenario = (
            "B 회계법인의 사원인 김한국 회계사는 ㈜대한그룹의 재무제표감사를 수행하고 있다. "
            "㈜대한그룹으로부터 받은 감사보수 총액이 B 회계법인의 연간 전체 매출액의 30%에 달한다."
        )
        scenario = st.text_area(
            "감사 독립성 관련 상황(시나리오)을 자연어로 입력하세요.",
            value=default_scenario,
            height=240,
        )

        run = st.button("🚀 독립성 분석 실행", type="primary")

    if run:
        if not scenario.strip():
            st.warning("시나리오를 입력해주세요.")
            return

        # 엔진 분석 진행률(대략적인 진행 상황) 표시용 프로그레스 바
        progress_bar = st.progress(0, text="엔진 분석 준비 중 (0/3 단계)")

        def call_backend():
            return requests.post(
                f"{BACKEND_URL}/analyze",
                json={"scenario": scenario},
                timeout=120,
            )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_backend)
                step = 0
                while not future.done():
                    step = min(step + 5, 95)
                    if step < 35:
                        label = "엔진 분석 중 (1/3) 시나리오 구조화..."
                    elif step < 70:
                        label = "엔진 분석 중 (2/3) 법령 컨텍스트 적용..."
                    else:
                        label = "엔진 분석 중 (3/3) 전문가 의견 생성..."
                    progress_bar.progress(step, text=label)
                    time.sleep(0.2)

                resp = future.result()

        except Exception as e:
            progress_bar.empty()
            st.error(f"백엔드 호출 중 오류가 발생했습니다: {e}")
            return

        if resp.status_code != 200:
            progress_bar.empty()
            st.error(
                f"분석 API 호출 실패 (status={resp.status_code})\n\n{resp.text}"
            )
            return

        # 성공적으로 응답을 받은 경우, 100%로 마무리하고 결과를 세션에 저장
        progress_bar.progress(100, text="엔진 분석 완료 (3/3 단계)")
        data = resp.json()

        # status 문자열이 설명 문구 등을 포함하는 경우를 방지하기 위한 추가 정규화
        valid_statuses = ["수임 불가", "안전장치 적용 시 수임 가능", "수임 가능"]
        raw_status = str(data.get("status", "")).strip()
        if raw_status not in valid_statuses:
            if "수임 불가" in raw_status:
                norm_status = "수임 불가"
            elif "안전장치" in raw_status:
                norm_status = "안전장치 적용 시 수임 가능"
            elif "수임 가능" in raw_status:
                norm_status = "수임 가능"
            else:
                norm_status = "검토 중"
            data["status"] = norm_status

        st.session_state["analysis_result"] = data

    # --- 여기부터는 최근 분석 결과가 있을 때 언제나 우측 패널에 표시 ---
    data = st.session_state.get("analysis_result")
    if data:
        status = data.get("status", "검토 중")
        status_color = {
            "수임 불가": "#d32f2f",
            "안전장치 적용 시 수임 가능": "#ed6c02",
            "수임 가능": "#2e7d32",
        }.get(status, "#455a64")

        with col2:
            st.subheader("2️⃣ 엔진 판정 결과")
            st.markdown(
                f'<span class="status-pill" style="background:{status_color}22; color:{status_color}; border:1px solid {status_color}55;">'
                f"{status}</span>",
                unsafe_allow_html=True,
            )
            st.caption("※ 본 리포트는 전문가의 최종 판단을 보조하기 위한 참고 자료입니다.")

            graph_url = data.get("graph_image_url")
            if graph_url:
                st.markdown(
                    f"""
                    <div style="max-width:100%; overflow-x:auto; padding-bottom:8px;">
                        <img src="{graph_url}" alt="Risk Map (Mermaid 기반)"
                             style="max-width:100%; height:auto; display:block; margin:0 auto;" />
                    </div>
                    <div style="font-size:0.85rem; color:#777; text-align:center; margin-top:-4px;">
                        Risk Map (Mermaid 기반)
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.subheader("📋 AI 리스크 진단 보고서")
        st.markdown(
            data.get("reason_html", "분석 결과를 불러오는 중입니다."),
            unsafe_allow_html=True,
        )

        st.subheader("🛡️ Safeguards / 조치 사항")
        safeguards = data.get("safeguards") or []
        if safeguards:
            for i, s in enumerate(safeguards, start=1):
                st.markdown(f"- {i}. {s}")
        else:
            st.write("추가로 제안된 안전장치(safeguards)가 없습니다.")

        st.subheader("🔗 관련 법령 링크")
        laws = data.get("relevant_laws") or []
        if laws:
            st.markdown(render_law_badges(laws), unsafe_allow_html=True)
        else:
            st.write("모델이 특정 법령 조항을 명시적으로 식별하지 않았습니다.")


if __name__ == "__main__":
    main()

