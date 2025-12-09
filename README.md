# Docs Chatter

Confluence 문서 기반 RAG Slack 챗봇

## 개요

사내 Confluence 문서를 벡터 DB에 저장하고, Slack에서 자연어로 질문하면 관련 문서를 찾아 답변을 생성합니다.

### 주요 기능

- **배치 인덱싱**: Confluence 문서를 OpenSearch에 벡터 저장
- **Hybrid Search**: 키워드 검색 + 의미 검색 결합
- **RAG 파이프라인**: 검색 → 관련성 평가 → 답변 생성
- **Slack 연동**: 멘션 또는 DM으로 질문

### 아키텍처

```
+-------------+     +-------------+     +-------------+
|    Slack    |---->|  RAG Chain  |---->|   Claude    |
|   (질문)    |     |             |     |   (답변)    |
+-------------+     +------+------+     +-------------+
                          |
                   +------v------+
                   | OpenSearch  |<---- Batch Indexer <---- Confluence
                   |  (벡터 DB)  |
                   +-------------+
```

### RAG 파이프라인 (6단계)

1. **Retrieve**: Hybrid Search (Lexical + Neural)
2. **Merge**: 청크에서 Parent 문서 로드
3. **Score Filter**: 점수 기준 필터링
4. **Relevance**: LLM 기반 관련성 평가 (0~100점)
5. **Prompt**: 컨텍스트 + 시스템 프롬프트 조합
6. **Generate**: Claude로 답변 생성

## 필요 서비스

| 서비스 | 용도 | 비용 |
|--------|------|------|
| Confluence | 문서 소스 | 무료 (구독 내 포함) |
| OpenSearch | 벡터 DB | 로컬: 무료 / AWS: 유료 |
| Cohere | 임베딩 | 무료 티어 (월 1,000회) |
| Anthropic | LLM | 유료 (토큰당 과금) |
| Slack | 챗봇 인터페이스 | 무료 |

## 설치 및 실행

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일 편집:

```env
# Confluence
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-token
CONFLUENCE_SPACE_KEYS=SPACE1,SPACE2

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin

# Cohere (Embedding)
COHERE_API_KEY=your-cohere-key

# Anthropic (LLM)
ANTHROPIC_API_KEY=your-anthropic-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### 3. OpenSearch 실행 (로컬)

```bash
docker run -d --name opensearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=YourPassword123!" \
  opensearchproject/opensearch:latest
```

### 4. 문서 인덱싱

```bash
# 전체 인덱싱
python scripts/run_batch.py --mode full

# 증분 인덱싱 (어제 이후 변경분)
python scripts/run_batch.py --mode incremental

# 특정 날짜 이후 증분 인덱싱
python scripts/run_batch.py --mode incremental --since 2024-01-01
```

### 5. Slack 봇 실행

```bash
python main.py
```

## Slack App 설정

1. https://api.slack.com/apps 에서 새 앱 생성
2. **Socket Mode** 활성화 → App Token 발급 (`xapp-...`)
3. **OAuth & Permissions**에서 Bot Token Scopes 추가:
   - `app_mentions:read`
   - `chat:write`
   - `im:history`
   - `im:read`
   - `im:write`
4. **Event Subscriptions** 활성화 후 구독:
   - `app_mention`
   - `message.im`
5. 워크스페이스에 앱 설치 → Bot Token 발급 (`xoxb-...`)

## 프로젝트 구조

```
wise-chatter/
├── src/docs_chatter/
│   ├── config.py           # 환경변수 설정
│   ├── confluence/
│   │   ├── client.py       # Confluence API
│   │   └── converter.py    # HTML → Markdown/Text
│   ├── vectorstore/
│   │   ├── embeddings.py   # Cohere 임베딩
│   │   └── opensearch.py   # OpenSearch 클라이언트
│   ├── rag/
│   │   ├── chunker.py      # 문서 청킹
│   │   ├── retriever.py    # Hybrid Search
│   │   ├── relevance.py    # 관련성 평가
│   │   └── chain.py        # RAG 체인
│   ├── slack/
│   │   └── bot.py          # Slack 봇
│   └── batch/
│       └── indexer.py      # 배치 인덱싱
├── scripts/
│   └── run_batch.py        # 배치 실행 스크립트
├── docs/
│   └── REQUIREMENTS.md     # 상세 요구사항
├── main.py                 # 엔트리포인트
├── pyproject.toml
└── .env.example
```

## 사용 예시

Slack에서:

```
@wise-chatter 휴가 신청 어떻게 해?
```

응답:

```
휴가 신청은 HR 시스템에서 가능합니다.

1. HR 포털 접속
2. 휴가 신청 메뉴 클릭
3. 날짜 선택 후 제출

*참고 문서:*
- 휴가 신청 가이드
- HR 시스템 매뉴얼
```

## 예정 기능

- 슬랙 채팅도 저장해서 하나의 문서처럼 활용하도록 추가