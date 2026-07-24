# 원본 기능 → KH_Aw 매핑

| 원본 영역 | 판단 | KH_Aw 대체/보존 |
|---|---|---|
| `backend/pipeline.mjs` | 로컬 CLI에 과결합된 대형 오케스트레이터 | `kh_aw_cli.py`, stage state, executable gates |
| `backend/auto-repair.mjs` | 풍부하지만 복잡한 stale/session 상태 | `repair.py` failure signature, deterministic repair, strategy generation |
| `backend/web-research.mjs` | fetch/excerpt 장점, 원문 물리 증거 부족 | `evidence.py` raw body + extracted text + hash + registry |
| `backend/production-validator.mjs` | 핵심 강점 | 페이지·본문·이미지·모션·해시 검증으로 재구현 |
| `backend/artifact-guard.mjs` | quarantine/resume 장점 | run-root containment + immutable analysis backup/restore |
| `backend/state-recovery.mjs` | 로컬 장기 세션에 최적화 | Git-tracked JSON state and nonterminal repair tickets |
| `backend/tasklist-protocol.mjs` | Antigravity live actor 이벤트 의존 | Codex skill stage loop + JSON repair ticket |
| `backend/runtime-resource-loader.mjs` | 로컬 skill/learning 탐색 | plugin bundled skills/references |
| `frontend/*` | 독립 로컬 서버 UI | Codex 웹 플러그인 대상에서 제거 |
| concept/color picker | 사용자 요구와 직접 충돌 | 삭제 및 forbidden-key gate |
| legacy taste skills | 고정 디자인 처방 | 동적 body-backed design skill로 교체 |
| config stage prompts | AI가 무시할 수 있는 문구 중심 | artifact templates + validators |
| legacy tests | 61/62 통과, 1 local-cache failure | 10 plugin-specific cross-platform tests 통과 |
| browser profile/data/output/logs | 공개 배포 위험 | 원장에는 기록, 패키지/GitHub에서는 제외 |
| 단일 단계 AI 작업 | 대규모 프로젝트에서 누락·편향·병목 위험 | 각 단계 대장 AI + 동적 2~60 독립 하위 AI |
| 프롬프트 기반 역할 분담 | 실제 호출·독립성·산출물 확인 불가 | immutable agent plan + session ID + 물리 결과 + SHA-256 |
| 고정 병렬 수 | 작은 프로젝트 낭비·대규모 프로젝트 부족 | 프로젝트 신호 기반 canonical scaling, 최소 2·최대 60 |
| 자기검토 한 번 | 동일 관점 오류 반복 | 독립 worker 교차검토 + 대장 AI 충돌 해결 집계 |
| `/agents` 사용 주장 | UI 호출 여부 검증 불가 | native invocation 또는 independent Codex task 기록; fallback은 완료 불인정 |
