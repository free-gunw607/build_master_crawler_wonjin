# Source Registry

신규 공고 소스는 먼저 `config/source_registry.json`에 등록하고, parser·회귀 smoke·Sheets dedup·Telegram 결과를 확인한 뒤 활성화한다.

## 운영 원칙

- `enabled: true`인 소스만 production 수집 대상으로 본다.
- 현재 V1 운영 소스는 `LH`, `i-SH`, `GH` 세 개다.
- 신규 소스는 기본적으로 `enabled: false`다.
- 서울 i-SH 후보와 경기 GH 후보는 기존 소스와 중복 여부를 먼저 판정한다.
- `source_id`는 Sheets dedup의 `source` 값이 되므로, 운영 투입 후 임의로 변경하지 않는다.
- 키워드는 필터 힌트이며, 실제 포함 조건은 소스별 parser smoke에서 확정한다.

## 추가 순서

1. 현재 V1 운영 기준선과 watchdog 검증
2. registry 전체 목록의 URL·게시판 범위 조사
3. 서로 다른 구조의 소스 2~3개를 파일럿 구현
4. 공통 `Notice` 계약과 parser family 정리
5. 지역 단위로 나머지 소스를 순차 활성화

## 현재 분류 상태

- `active_v1`: 기존 production adapter가 있는 소스
- `candidate`: 기존 소스와 게시판 범위 중복 확인이 필요한 소스
- `planned`: URL만 등록했고 parser 조사는 시작하지 않은 소스

이 registry는 신규 소스를 production에 자동 연결하지 않는다. 활성화는 parser와 운영 검증이 끝난 뒤 별도 변경으로 수행한다.
