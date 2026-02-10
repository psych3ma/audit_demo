from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.engine import (
    build_graph_image_url,
    stage1_nlp_to_graph,
    stage2_inject_law_context,
    stage3_expert_analysis,
)


class AnalyzeRequest(BaseModel):
    """분석 API 입력 스키마."""

    scenario: str


class AnalyzeResponse(BaseModel):
    """분석 API 출력 스키마."""

    status: str
    reason_html: str
    safeguards: List[str]
    relevant_laws: List[str]
    graph: Dict[str, Any]
    law_context: str
    risky_node_ids: List[str]
    risky_edge_indices: List[int]
    graph_image_url: str


app = FastAPI(
    title="Audit Independence Scanner API",
    description="회계법인 감사 독립성 리스크 자동 분석 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    scenario = req.scenario

    # 1. 구조화
    graph_data = stage1_nlp_to_graph(scenario)

    # 2. 법령 주입
    law_context = stage2_inject_law_context(graph_data)

    # 3. 전문가 분석
    raw_analysis = stage3_expert_analysis(scenario, graph_data, law_context)

    # status 값이 프롬프트 설명 문구 등으로 잘못 나오는 경우를 방지하기 위한 후처리
    valid_statuses = ["수임 불가", "안전장치 적용 시 수임 가능", "수임 가능"]
    status = str(raw_analysis.get("status", "")).strip()
    if status not in valid_statuses:
        if "수임 불가" in status:
            status = "수임 불가"
        elif "안전장치" in status:
            status = "안전장치 적용 시 수임 가능"
        elif "수임 가능" in status:
            status = "수임 가능"
        else:
            status = "검토 중"

    analysis_result: Dict[str, Any] = {**raw_analysis, "status": status}

    # 4. 그래프 이미지 URL 생성
    graph_url = build_graph_image_url(graph_data, analysis_result)

    return AnalyzeResponse(
        status=status,
        reason_html=analysis_result.get("reason", ""),
        safeguards=analysis_result.get("safeguards", []),
        relevant_laws=analysis_result.get("relevant_laws", []),
        graph=graph_data,
        law_context=law_context,
        risky_node_ids=analysis_result.get("risky_node_ids", []),
        risky_edge_indices=analysis_result.get("risky_edge_indices", []),
        graph_image_url=graph_url,
    )


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

