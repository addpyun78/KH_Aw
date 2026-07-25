# 사용자 요구사항 완전 추적표

| ID | 원문 의도 | KH_Aw 구현 위치 | 기계 검증 |
|---|---|---|---|
| U-01 | 이름은 KH_Aw | plugin displayName `KH_Aw`, 내부 규격 ID `kh-aw` | plugin validator가 폴더명과 manifest name 일치 확인 |
| U-02 | 누락·요약·축소·생략 금지 | exact instruction contract, 2,519개 전수 원장 | analyze gate가 원문 줄 순서/수/텍스트 1:1 비교 |
| U-03 | 느려도 정밀·세밀 | 전체 SHA-256 원장, full folder backup, every-page evidence | 파일 수·해시·페이지 수 검증 |
| U-04 | 로직 문제 연구·업그레이드 | `LOGIC_DEEP_RESEARCH_REPORT.md`, 새 Python state machine | unit tests와 CI |
| U-05 | 각 항목 점수 보고서 | `SCORE_REPORT.md` | 산출물/테스트 기반 점수 |
| U-06 | 앱·웹 회사 운영 | full cycle/release/company skills | verify/release gates |
| U-07 | GitHub→마켓플레이스→Codex 설치 | repo-root marketplace structure, branch publication docs | marketplace validator |
| U-08 | 수동 컨셉·색상 선택 삭제 | manual UI 제외, forbidden keys, dynamic design origin | analyze/research/design/implement gates + deterministic repair |
| U-09 | 검색만 하지 말고 본문 직접 추출 | source body/text/hash registry | research gate가 body file, SHA-256, 300자, HTTP, URL을 검사 |
| U-10 | 설계에서 목업용 시각 디자인 선행 | design stage before implement | state order와 design gate |
| U-11 | 샘플 몇 개가 아니라 전체 페이지 목업 | one mockup HTML + one PNG per page, unique paths | exact ID/count/path uniqueness 검사 |
| U-12 | 목업 기반 실제 디자인·로직·이미지 | implementation ledger with target hashes and asset IDs | implement gate |
| U-13 | 소기업도 주목받을 고품질 | per-page attention/conversion/image/motion decisions | design gate 최소 적용 범위 |
| U-14 | 모션과 이미지 필요 | image slots/assets, motion storyboards/code markers | design and implement gates |
| U-15 | 게이트 실패 시 시스템 정지 금지 | nonterminal exit and repairing state | test `test_cli_advance_returns_zero_on_repair` |
| U-16 | 모든 전체에 자동수리 후 계속 | deterministic repair + root-cause ticket + strategy generation | repair tests |
| U-17 | 프롬프트만으로 무시되지 않게 로직 강제 | executable gates and physical evidence | prose cannot advance state |
| U-18 | 분석폴더 있음/없음 구분 | two explicit analysisMode values | analyze gate |
| U-19 | 제공 분석폴더 원본 보호 | full ZIP backup, snapshot, output boundary, restore | protection tests |
| U-20 | Codex 웹 마켓플레이스 플러그인 | official plugin/marketplace structure, no local model cache dependency | doctor validation |
| U-21 | 디자인을 KH_Aw에 하드코딩하지 않음 | dynamic research mode, placeholders must be replaced per project | research/design gates |
| U-22 | 각 단계 순수/슬러시 기능 적극 활용 | 단계별 `/goal`·`/agents`와 `/plan`·`/context`·`/artifact`·`/search`·`/diff`·`/review`·`/test` capability | 실제 native session JSONL 없으면 단계 차단 |
| U-23 | 시뮬레이터·에뮬레이터 등 도구 적극 활용 | web 3브라우저, Android AVD/ADB, iOS Simulator, 조건부 도구 정책 | target toolchain coverage와 실제 로그·해시 |
| U-24 | APK 설치 제외 | forbidden command patterns 및 android policy | 실행 전 차단·test gate 재탐지 |
| U-25 | 프롬프트가 아니라 로직으로 강제 | physical evidence, canonical policy, immutable fingerprint | 문장형 완료·임의 JSON 약화 거부 |
| U-26 | 각 단계 대장 AI가 하위 AI 사용 | stage lead contract·plan fingerprint·독립 lead session·전체 집계 | 모든 worker ID·lead-contract SHA-256·집계 파일 검사 |
| U-27 | 하위 AI 최소 2개·최대 60개 | 안전 최저치 계산 + 대장 AI 근거 기반 증원 | 2~60 범위·최저치 감소 차단·120바이트 이상 근거/해시 검사 |
| U-28 | 무조건 60개가 아니라 필요한 만큼 | file/requirement/page/field/logic/feature/risk/tool 신호 + 물리 증원근거 | plan fingerprint·scale justification SHA-256·run-lock 검사 |
| U-29 | 대규모 프로젝트 누락·실패 방지 | worker별 불변 dispatch·실제 호출 영수증·고유 결과·전체 ring 검토 | session/output/receipt 중복 차단·모든 worker 검토 커버리지·대장 집계 |
| U-30 | 최종 패키지 자체 누락 방지 | distribution completeness validator | 필수 6개 스킬·엔진·스키마·테스트·CI·감사자료 중 하나라도 없으면 doctor 실패 |
