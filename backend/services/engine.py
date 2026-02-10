"""감사 독립성 분석의 핵심 비즈니스 로직.

- 단계 1: 시나리오 → 그래프(JSON)
- 단계 2: 그래프 → 법령 컨텍스트 문구
- 단계 3: 시나리오 + 그래프 + 법령 → 전문가 의견 JSON
- 단계 4: 그래프/분석 → Mermaid 기반 리스크 맵 이미지 URL
"""

import base64
import json
import re
import urllib.parse
from typing import Any, Dict, List

from openai import OpenAI

from common.config import OPENAI_MODEL_ANALYSIS, OPENAI_MODEL_GRAPH


# OpenAI 클라이언트 (환경변수 OPENAI_API_KEY 사용)
client = OpenAI()


# ---------------------------------------------------------------------------
# 공통 유틸리티
# ---------------------------------------------------------------------------
def get_dynamic_law_url(law_text: str) -> str:
    """
    법령 이름(예: '공인회계사법 제21조')으로 law.go.kr 링크를 동적으로 생성합니다.
    """
    base_url = "https://www.law.go.kr/법령/"
    match = re.search(r"([가-힣]+법)\s*(제?\d+조)?", law_text)
    if match:
        law_name = match.group(1)
        article = match.group(2) if match.group(2) else ""
        return base_url + urllib.parse.quote(f"{law_name}/{article}".strip("/"))
    return (
        "https://www.law.go.kr/DRF/lawSearch.do?target=law&query="
        + urllib.parse.quote(law_text)
    )


def safe_json_parse(content: str) -> Dict[str, Any]:
    """
    모델이 반환한 문자열에서 JSON 부분만 안전하게 추출/파싱합니다.
    - ```json ... ``` 형태로 감싸져 있어도 동작합니다.
    """
    try:
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, content, re.DOTALL)
        json_str = match.group(1) if match else content
        return json.loads(json_str)
    except Exception as e:
        return {"error": "JSON_PARSE_ERROR", "details": str(e)}


# ---------------------------------------------------------------------------
# 단계 1: 구조화 데이터 변환 (NLP -> Graph)
# ---------------------------------------------------------------------------
def stage1_nlp_to_graph(user_input: str) -> Dict[str, Any]:
    """
    자연어 시나리오에서 인물/회사/관계 등을 뽑아 그래프 구조(JSON)로 변환합니다.
    """
    system_prompt = """
    당신은 회계감사 관계 추출 전문가입니다. 입력된 시나리오에서 노드와 관계를 추출하여 JSON으로 반환하세요.
    - Nodes: id(p1, o1 등), label(Person, Organization, Asset), properties(name, firm_role, is_client, value 등)
    - Relationships: source_id, target_id, type(EMPLOYED_BY, OWNS, ISSUED_BY, FAMILY_OF 등)
    """
    response = client.chat.completions.create(
        model=OPENAI_MODEL_GRAPH,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return safe_json_parse(response.choices[0].message.content or "")


# ---------------------------------------------------------------------------
# 단계 2: 법령 컨텍스트 주입 (Context Injection)
# ---------------------------------------------------------------------------
def stage2_inject_law_context(graph_data: Dict[str, Any]) -> str:
    """
    그래프 내용(키워드)을 보고, 관련 법령 설명 문구를 자동으로 붙입니다.
    - 키워드 목록 (예: "주식", "대출")
    - 해당 키워드가 있을 때 붙일 설명 문구
    """
    context: List[str] = []
    data_str = str(graph_data)

    # 예시 1: 지분/주식 보유 관련
    if any(k in data_str for k in ["주식", "회원권", "지분", "OWNS"]):
        context.append(
            "[공인회계사법 제21조] 감사인 또는 그 배우자가 피감사회사의 주식, 사채, 회원권 등을 보유한 경우 감사업무 금지."
        )

    # 예시 2: 비감사서비스/자문 관련
    if any(k in data_str for k in ["계리", "자문", "Consulting"]):
        context.append(
            "[외부감사법 제9조] 비감사서비스(보험계리, 내부통제 구축 등) 제공 시 독립성 훼손으로 간주."
        )

    # 예시 3: 차입/대출 관련
    if any(k in data_str for k in ["카드", "할부", "대출", "차입"]):
        context.append(
            "[공인회계사법 시행령 제14조] 5천만원 이상의 채권/채무는 금지되나, 금융기관의 통상적 약관에 따른 거래는 예외."
        )

    # 예시 4: 가족관계 관련
    if any(k in data_str for k in ["배우자", "FAMILY_OF"]):
        context.append(
            "[윤리기준] 감사팀 소속원의 직계 가족이 피감사인의 임원인 경우 수임 제한."
        )

    return "\n".join(context) if context else "일반적 독립성 준수 원칙 적용"


# ---------------------------------------------------------------------------
# 단계 3: 전문가 분석 엔진 (Expert Analysis)
# ---------------------------------------------------------------------------
def stage3_expert_analysis(
    scenario: str, graph_data: Dict[str, Any], law_context: str
) -> Dict[str, Any]:
    """
    품질관리실 파트너 관점의 HTML 기반 의견서(JSON)를 생성합니다.

    status 판단 기준(모델 안내용 요약)
    ----------------------------------
    - "수임 불가"
      * 공인회계사법, 외부감사법, 윤리기준상 "절대적 금지" 또는 사실상 수임이 허용되지 않는 명백한 사유가 존재
      * 예: 감사인 또는 그 배우자가 피감사회사 지분을 실질적으로 보유, 고액 직접 대출/보증, 경영진 겸직 등

    - "안전장치 적용 시 수임 가능"
      * 독립성 위협이 존재하지만, 국제윤리기준위원회(IESBA) 윤리기준 상 적정한 안전장치(격리, 처분, 팀교체 등)를 통해
        수용 가능한 수준으로 낮출 수 있는 경우
      * 예: 타 본부 파트너의 과거 자문관계, 경미한 금액의 대출, 지분의 신속한 처분이 가능한 경우 등

    - "수임 가능"
      * 식별된 독립성 위협이 "중요하지 않은 수준"이며, 추가적인 안전장치가 없어도 수임에 문제가 없는 경우
      * 예: 피감사회사와의 통상적인 상거래, 실질적 이해관계가 없는 경우 등

    반환 JSON 예시
    -------------
    {
        "status": "수임 불가/안전장치 적용 시 수임 가능/수임 가능",
        "reason": "<b>...</b> 형태의 HTML 의견",
        "safeguards": ["조치 1", "조치 2"],
        "relevant_laws": ["공인회계사법 제21조"],
        "risky_node_ids": ["p1"],
        "risky_edge_indices": [0, 2]
    }
    """
    prompt = f"""
    당신은 대형 회계법인 품질관리실 파트너입니다. 한국 공인회계사 윤리기준과 외부감사법, 공인회계사법을 기준으로
    독립성 위협을 평가하여, 아래 세 가지 상태 중 하나로 신중하게 분류해야 합니다.

    - "수임 불가": 법령상 절대적 금지 또는 실질적으로 수임이 허용되지 않는 중대한 위반이 있는 경우에만 사용
    - "안전장치 적용 시 수임 가능": 위협이 있으나, 적절한 안전장치(격리, 처분, 팀교체 등)를 통해 수용 가능한 수준으로 낮출 수 있는 경우
    - "수임 가능": 독립성 위협이 중요하지 않은 수준이거나, 식별된 위협이 없고 법령·윤리기준에 위배되지 않는 경우

    [시나리오] {scenario}
    [데이터] {json.dumps(graph_data, ensure_ascii=False)}
    [법령 컨텍스트] {law_context}

    [작성 가이드라인]
    1. Opinion (구조화): 줄글을 지양하고 아래 섹션별로 HTML 태그(<b>, <li>, <br>)를 사용하여 요약하세요.
       - <b style='color:#64b5f6'>[핵심 위반 사항]</b>: 식별된 리스크 요약 (불렛포인트 사용)
       - <b style='color:#64b5f6'>[법적/규정 판단]</b>: 관련 법령 조항과 위반 사실의 1:1 매칭
       - <b style='color:#64b5f6'>[실무적 시사점]</b>: 독립채산제 등 법인의 특수성을 고려한 최종 경고

    2. Safeguards (구체성):
       - '수임 불가'인 경우: 정말로 법령상 절대적 금지 사유인지를 한번 더 점검한 뒤,
         "법령상 절대적 금지 사유로 인해 어떠한 안전장치로도 해결 불가능함"을 명시하고 그 이유를 구체적으로 쓰세요.
       - '안전장치 적용 시 수임 가능'인 경우: 즉시 실행 가능한 구체적 조치(격리, 처분, 팀 교체, 자문부서 분리 등)를 나열하세요.
       - '수임 가능'인 경우: 불필요한 공포를 주지 않도록, 왜 위협이 경미하다고 판단했는지 간단히 설명하고
         필요한 경우에만 경미한 수준의 주의사항을 제시하세요.

    [JSON 포맷]  ※ status 값은 다음 세 단어 중 하나만 사용하세요.
    - "수임 불가"
    - "안전장치 적용 시 수임 가능"
    - "수임 가능"

    {{
        "status": "수임 불가" 또는 "안전장치 적용 시 수임 가능" 또는 "수임 가능",
        "reason": "구조화된 HTML 전문가 의견서",
        "safeguards": ["조치 또는 불가 사유 1", "2"],
        "relevant_laws": ["공인회계사법 제21조" 등],
        "risky_node_ids": ["위험 노드 ID"],
        "risky_edge_indices": ["위험 관계 인덱스"]
    }}
    """
    response = client.chat.completions.create(
        model=OPENAI_MODEL_ANALYSIS,
        messages=[
            {"role": "system", "content": "Senior Audit Quality Control Partner"},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return safe_json_parse(response.choices[0].message.content or "")


# ---------------------------------------------------------------------------
# 단계 4: 그래프 이미지 URL 생성 (Mermaid -> PNG URL)
# ---------------------------------------------------------------------------
def build_graph_image_url(graph: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """
    그래프와 위험 노드/엣지 정보를 이용해 Mermaid 다이어그램을 만들고,
    이를 mermaid.ink의 PNG 이미지 URL로 변환합니다.
    """
    mm_code: List[str] = ["graph TD"]
    risky_nodes = analysis.get("risky_node_ids", [])

    for node in graph.get("nodes", []):
        nid = node.get("id")
        props = node.get("properties", {})
        name = props.get("name") or props.get("type") or nid
        role = props.get("firm_role", "") or props.get("position", "")
        if role:
            display_text = f"<b>{name}</b><br/>[{role}]"
        else:
            display_text = name
        mm_code.append(
            f'    {nid}["{"⚠️ " if nid in risky_nodes else ""}{display_text}"]:::{ "riskyNode" if nid in risky_nodes else "normalNode" }'
        )

    for idx, edge in enumerate(graph.get("relationships", [])):
        s = edge.get("source_id")
        e = edge.get("target_id")
        t = edge.get("type")
        # 관계 타입 문자열에서 언더스코어를 공백으로 바꾸고,
        # 너무 길 경우 첫 번째 공백에서 줄바꿈을 한 번 넣어 텍스트 겹침을 줄인다.
        label = t.replace("_", " ")
        if len(label) > 12 and " " in label:
            first_space = label.find(" ")
            label = label[:first_space] + "\\n" + label[first_space + 1 :]
        if idx in analysis.get("risky_edge_indices", []):
            mm_code.append(f'    {s} -. "⚠️ {label}" .-> {e}')
        else:
            mm_code.append(f'    {s} ---|"{label}"| {e}')

    mm_code.append(
        "    classDef normalNode fill:#ffffff,stroke:#333,stroke-width:1px;"
    )
    mm_code.append(
        "    classDef riskyNode fill:#fff5f5,stroke:#ff0000,stroke-width:2px,stroke-dasharray: 5 5;"
    )

    graph_url = (
        "https://mermaid.ink/img/"
        + base64.b64encode("\n".join(mm_code).encode("utf-8")).decode("ascii")
    )
    return graph_url

