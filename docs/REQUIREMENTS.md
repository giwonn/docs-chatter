# Docs Chatter - Confluence RAG 챗봇

## 1. 프로젝트 개요

사내 Confluence 문서를 기반으로 질문에 답변하는 Slack 챗봇 시스템

### 핵심 목표
- Confluence 문서를 벡터 DB에 저장하여 의미 기반 검색
- Slack을 통해 자연어로 사내 문서 검색 및 질의응답
- 매일 새벽 배치로 문서 동기화

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docs Chatter                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                               │
│  │   Slack Bot  │ ◄── 사용자 질문                                 │
│  │  (slack-bolt)│                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              ChatBot Server (RAG Pipeline)                │  │
│  │  ┌─────────┐    ┌─────────┐   ┌─────────┐    ┌─────────┐  │  │
│  │  │Retrieve │ ─▶ │  Merge │ ─▶│Relevance│ ─▶ │Generate │ │  │
│  │  │(검색)    │    │ (병합)  │   │ (평가)   │    │  (LLM)  │  │  │
│  │  └─────────┘    └─────────┘   └─────────┘    └─────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│         │                               │                       │
│         ▼                               ▼                       │
│  ┌──────────────┐              ┌──────────────┐                 │
│  │  OpenSearch  │              │   Anthropic  │                 │
│  │ (Vector DB)  │              │   Claude     │                 │
│  └──────┬───────┘              └──────────────┘                 │
│         │                                                       │
│  ┌──────┴───────┐                                               │
│  │    Batch     │ ◄── 새벽 동기화 (Cron)                          │
│  │  (Indexer)   │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │  Confluence  │                                               │
│  │     API      │                                               │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| Language | Python 3.14+ | |
| Framework | LangChain | RAG 파이프라인 |
| LLM | Anthropic Claude | 답변 생성 |
| Embedding | Cohere | 텍스트 임베딩 |
| Vector DB | OpenSearch | Hybrid Search (Lexical + Neural) |
| Slack | slack-bolt | 이벤트 기반 봇 |
| Confluence | atlassian-python-api | 문서 크롤링 |
| HTML 파싱 | BeautifulSoup4 | HTML → Markdown/Plain Text |
| 설정 관리 | pydantic-settings | 환경변수 관리 |

## 4. 배치 파이프라인 (ETL)

스푼랩스 참고: **Converting → Chunking** 순서로 진행

### 4.1 Content 변환 (Converting)

**3종 문서 준비:**

| 형식 | 용도 |
|------|------|
| HTML 원문 | Confluence API 호출 부담 줄이기 위해 저장 (선택) |
| Markdown | LLM 참조용 Parent 문서 (문맥 유지) |
| Plain Text | Text Embedding용 (의미 밀도 중요) |

**왜 Markdown인가?**
- LLM은 Markdown 포맷을 가장 잘 처리
- 명확한 계층구조 (#, -, >, 1.)
- 의미 전달이 가능 (가독성 좋음)

**왜 Plain Text도 필요한가?**
- Text Embedding은 구조보다 의미 밀도가 중요
- Markdown 마크업이 오히려 노이즈가 될 수 있음

### 4.2 Chunking

**왜 Chunking이 필요한가?**

1. **Token Limit**: Cohere embed-multilingual-v3.0은 512 token 제한
2. **문맥 손실 방지**: 중요 정보가 chunk 경계에서 잘리는 것 방지

**Chunking 전략:**

| 방식 | 설명 |
|------|------|
| Recursive Character Splitter | 문장을 자연스럽게 끊기지 않게 분할 |
| Sliding Window (Overlap) | 앞뒤 내용 겹쳐서 문맥 유지 |

**권장 설정:**
- Chunk Size: 500~1000 토큰
- Overlap: 100 토큰

```
┌─────────────────────────────────────────┐
│           Indexing Pipeline             │
├─────────────────────────────────────────┤
│                                         │
│  Confluence API                         │
│       │                                 │
│       ▼                                 │
│  ┌─────────────┐                        │
│  │ HTML 문서   │                        │
│  └─────┬───────┘                        │
│        │                                │
│        ├──────────────┐                 │
│        ▼              ▼                 │
│  ┌──────────┐   ┌──────────┐            │
│  │ Markdown │   │Plain Text│            │
│  │ (Parent) │   │(Embedding)│           │
│  └──────────┘   └────┬─────┘            │
│                      │                  │
│                      ▼                  │
│               ┌──────────┐              │
│               │ Chunking │              │
│               └────┬─────┘              │
│                    │                    │
│                    ▼                    │
│               ┌──────────┐              │
│               │Embedding │ ← Cohere     │
│               └────┬─────┘              │
│                    │                    │
│                    ▼                    │
│               ┌──────────┐              │
│               │OpenSearch│              │
│               └──────────┘              │
│                                         │
└─────────────────────────────────────────┘
```

## 5. RAG 파이프라인 (6단계)

### 5.1 Retrieve (검색)

**Hybrid Search** = Lexical + Neural 동시 수행

```
Hybrid Search
├── Lexical (multi_match)
│   ├── 형태소 분석 (korean_analyzer)
│   ├── minimum_should_match: 80%
│   └── operator: or (관련 문서 최대한 수집)
│
└── Neural (KNN)
    ├── Cohere Embedding
    └── k: 30 (상위 30개)
```

### 5.2 Merge (병합)

- Chunk만으로는 문맥 부족
- 검색된 Chunk가 속한 **Parent 문서(Markdown)** 를 가져옴
- LLM이 더 풍부한 문맥 이해 가능

### 5.3 Score Filter

**문제**: Hybrid Search에서는 `min_score`가 작동 안 함
- Lexical: BM25 기반 점수
- Neural: 유클리드 거리 기반 점수
- 단위가 달라서 단순 비교 불가

**해결**: Application 레벨에서 `_score` 기준 필터링
- 예: `score > 0.3` 이상만 통과

### 5.4 Relevance (관련성 평가)

**목적**: 점수는 높지만 실제로 관련 없는 문서 걸러내기

**방법**: LLM에게 직접 관련성 점수(0~100) 요청

```
System Prompt:
당신은 주어진 질의(Query)와 문서(Document)의 관련성을 평가하는 AI입니다.
관련성 점수를 0(관련 없음)에서 100(매우 관련 있음) 사이로 평가하세요.

응답 형식:
Relevance: <score>
```

**기준:**
- 60점 초과 → 포함
- 60점 이하 → 제외
- 최종 10개 이하 chunk만 사용

### 5.5 Prompt

- 프롬프트 하나로 결과가 달라짐
- 페르소나 설정 중요
- 프롬프트 검토/첨삭 권장

### 5.6 Generate (LLM)

**파라미터:**
- `temperature`: 0.0 (정확한 답변) ~ 1.0 (창의적)
- `max_tokens`: 응답 최대 길이

**응답 방식:**
- `call()`: 전체 응답 한 번에
- `stream()`: 스트리밍 (체감 속도 향상)

```
┌─────────────────────────────────────────┐
│           RAG Pipeline (6단계)          │
├─────────────────────────────────────────┤
│                                         │
│  사용자 질문                             │
│       │                                 │
│       ▼                                 │
│  ┌─────────────┐                        │
│  │ 1. Retrieve │ ← Hybrid Search        │
│  └─────┬───────┘   (Lexical + Neural)   │
│        │                                │
│        ▼                                │
│  ┌─────────────┐                        │
│  │  2. Merge   │ ← Parent 문서 로드      │
│  └─────┬───────┘                        │
│        │                                │
│        ▼                                │
│  ┌─────────────┐                        │
│  │3.Score Filter│ ← _score > 0.3        │
│  └─────┬───────┘                        │
│        │                                │
│        ▼                                │
│  ┌─────────────┐                        │
│  │4. Relevance │ ← LLM 관련성 평가       │
│  └─────┬───────┘   (60점 이상만)         │
│        │                                │
│        ▼                                │
│  ┌─────────────┐                        │
│  │  5. Prompt  │ ← 시스템 프롬프트 조합   │
│  └─────┬───────┘                        │
│        │                                │
│        ▼                                │
│  ┌─────────────┐                        │
│  │ 6. Generate │ ← Claude LLM           │
│  └─────┬───────┘                        │
│        │                                │
│        ▼                                │
│  최종 응답 (+ 출처 링크)                  │
│                                         │
└─────────────────────────────────────────┘
```

## 6. 환경 변수

```env
# Confluence
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-api-token
CONFLUENCE_SPACE_KEYS=SPACE1,SPACE2

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin
OPENSEARCH_INDEX=docs-chatter

# Cohere (Embedding)
COHERE_API_KEY=your-cohere-api-key

# Anthropic (LLM)
ANTHROPIC_API_KEY=your-anthropic-api-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
```

## 7. 프로젝트 구조

```
docs-chatter/
├── src/
│   └── docs_chatter/
│       ├── __init__.py
│       ├── config.py              # 설정 관리 (pydantic-settings)
│       ├── confluence/
│       │   ├── __init__.py
│       │   ├── client.py          # Confluence API 클라이언트
│       │   └── converter.py       # HTML → Markdown/Plain Text
│       ├── vectorstore/
│       │   ├── __init__.py
│       │   ├── opensearch.py      # OpenSearch 클라이언트
│       │   └── embeddings.py      # Cohere 임베딩
│       ├── rag/
│       │   ├── __init__.py
│       │   ├── chunker.py         # 문서 청킹
│       │   ├── retriever.py       # Hybrid Search
│       │   ├── relevance.py       # 관련성 평가
│       │   └── chain.py           # RAG 체인
│       ├── slack/
│       │   ├── __init__.py
│       │   └── bot.py             # Slack 봇 핸들러
│       └── batch/
│           ├── __init__.py
│           └── indexer.py         # 배치 인덱싱
├── scripts/
│   └── run_batch.py               # 배치 실행 스크립트
├── docs/
│   └── REQUIREMENTS.md
├── main.py                        # Slack 봇 엔트리포인트
├── pyproject.toml
└── .env.example
```

## 8. 구현 우선순위

### Phase 1: 기반 구축
- [ ] 프로젝트 구조 생성
- [ ] 설정 관리 (config.py)
- [ ] Confluence 클라이언트

### Phase 2: 인덱싱 파이프라인
- [ ] HTML → Markdown/Plain Text 변환
- [ ] 문서 청킹 (Recursive + Overlap)
- [ ] OpenSearch 연동
- [ ] Cohere 임베딩
- [ ] 배치 스크립트

### Phase 3: RAG 파이프라인
- [ ] Hybrid Search (Retrieve)
- [ ] Parent 문서 Merge
- [ ] Score Filter
- [ ] Relevance 평가
- [ ] RAG Chain + Prompt

### Phase 4: Slack 봇
- [ ] 봇 이벤트 핸들러 (멘션/DM)
- [ ] 응답 포맷 (답변 + 출처)
- [ ] 스트리밍 응답

### Phase 5: 운영
- [ ] 로깅
- [ ] 배치 스케줄링 (cron)

## 9. 주요 고려사항

### 성능
- Chunk Size: 500~1000 토큰
- Overlap: 100 토큰
- 검색 결과: Top-K = 30, 최종 사용 10개 이하
- 비동기 처리로 Relevance 평가 병렬화

### 품질
- Hybrid Search로 키워드 + 의미 검색 결합
- Parent 문서로 문맥 보존
- Relevance 평가로 관련 없는 문서 필터링
- 프롬프트 튜닝 중요

### 비용
- Cohere Embedding: 사용량 기반
- Anthropic Claude: 토큰 기반
- Relevance 평가도 LLM 호출 (문서당 1회)
