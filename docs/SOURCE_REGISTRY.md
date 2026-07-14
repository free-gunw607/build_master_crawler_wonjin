# Source Registry

신규 공고 소스는 먼저 `config/source_registry.json`에 등록하고, parser·회귀 smoke·Sheets dedup·Telegram 결과를 확인한 뒤 활성화한다.

## 운영 원칙

- `enabled: true`인 소스만 production 수집 대상으로 본다.
- 현재 V1 운영 소스는 `LH`, `i-SH`, `GH` 세 개다.
- 신규 소스는 기본적으로 `enabled: false`다.
- 서울 i-SH 후보와 경기 GH 후보는 기존 소스와 중복 여부를 먼저 판정한다.
- `source_id`는 Sheets dedup의 `source` 값이 되므로, 운영 투입 후 임의로 변경하지 않는다.
- 모든 entry는 `production_approved: true|false`를 명시해야 하며, 값이 없으면 runtime registry validation이 실패한다.
- 키워드는 필터 힌트이며, 실제 포함 조건은 소스별 parser smoke에서 확정한다.

## 추가 순서

1. 현재 V1 운영 기준선과 watchdog 검증
2. registry 전체 목록의 URL·게시판 범위 조사
3. 서로 다른 구조의 소스 2~3개를 파일럿 구현
4. 공통 `Notice` 계약과 parser family 정리
5. 지역 단위로 나머지 소스를 순차 활성화

## 현재 분류 상태

- `active_v1`: 기존 production adapter가 있는 소스
- `active_v2`: 신규 adapter가 production Sheets/Telegram 경로까지 검증된 소스
- `candidate`: 기존 소스와 게시판 범위 중복 확인이 필요한 소스
- `planned`: URL만 등록했고 parser 조사는 시작하지 않은 소스

## 1차 조사 결과

2026-07-14 기준 실제 목록 응답을 확인했다. 확인된 소스들은 대체로 서버 렌더링 목록을 제공하지만 detail 식별자 방식은 서로 다르다.

- `ish_custom_variant`: 기존 i-SH와 같은 `getDetailView(seq)` 계열
- `server_board_href`: table 행의 일반 detail href에 식별자가 포함된 계열
- `server_board_onclick`: `dataId` 또는 유사 식별자가 onclick/detail URL에 포함된 계열
- `server_query_board`: query string의 `board_idx` 등으로 detail을 여는 계열
- `legacy_php_board`, `legacy_zboard`: 오래된 PHP/zboard 계열

첫 파일럿은 다음 2개로 확정한다.

1. `BMC`: 일반 detail href 기반 서버 게시판
2. `UMCA`: onclick/dataId 기반 서버 게시판

서울 i-SH 후보는 기존 i-SH와 raw ID가 59/59 겹쳐 `i-SH`에 병합했다. 별도 source identity나 Sheets tab을 만들지 않는다.

두 파일럿은 parser/detail/dedup/schema/Telegram smoke를 통과해 `active_v2`로 승격했고, 실제 운영 workflow에서 Sheets tab 생성과 write path까지 검증했다. 증거 workflow는 `29280240103`이며 BMC·UMCA가 enabled source로 실행되어 `overall`/runlog/Telegram 경로를 예외 없이 완료했다.

- `BMC`: 85건
- `UMCA`: 16건

두 게시판은 각각 목적이 명확한 전용 분양공고판이므로, 현재 정책은 키워드 강제 필터보다 게시판 범위 전체 수집이다. 그 전까지는 `--include-pilots`가 `--dry-run` 없이 실행되지 않는다.

2026-07-14 최신 production regression `29302647947`에서도 enabled set `LH`, `i-SH`, `GH`, `BMC`, `UMCA`가 정상 실행됐고, Sheets/Telegram sync 예외가 없었다.

## 첫 source family dry-run 결과

2026-07-14 기준 실제 목록에서 다음 adapter가 동작했다.

- `BMC`: 22건
- `UMCA`: 5건
- `DUDC`: 38건
- `DCCO`: 6건
- `SCTC`: 4건
- `JNDC`: 6건

이 소스들은 adapter·current-page dry-run 단계까지 완료했지만, detail/schema/Telegram production gate 전이므로 `enabled: false`, `production_approved: false`를 유지한다. 2026-07-14 04:56 KST post-production dry-run에서 6개 source 합계 80건을 재현했다.

이 registry는 신규 소스를 production에 자동 연결하지 않는다. 활성화는 parser와 운영 검증이 끝난 뒤 별도 변경으로 수행한다.

## 2026-07-14 adapter coverage

registry에 남아 있던 소스도 모두 adapter dispatch 경로에 등록했다.

- `IH`, `GDCO`, `CBDC`, `GMCC`: legacy/server-board adapter
- `CNDC`, `JBDC`: onclick/JavaScript detail identifier adapter
- `GBDC`, `GNDC`: JSON board API adapter
- `GH_SALE_RENTAL_CANDIDATE`: `articleNo` adapter; active GH와 제목 중복 정책을 별도 gate로 유지

현재 live smoke 증거는 CNDC 4건, JBDC 9건, GBDC 14건, GNDC 29건, GH 후보 39건이며, 이 수치는 production 승인이나 Sheets tab 생성을 의미하지 않는다.
