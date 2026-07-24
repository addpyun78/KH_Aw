# KH_Aw 3.2.0 Release Notes

## 3.2 핵심 추가

- 모든 8단계에 대장 AI·독립 하위 AI 오케스트레이션 적용
- 배포본 완전성 validator 추가: 엔진·스킬·스키마·테스트·CI·감사자료 누락 시 doctor 실패
- 회귀 테스트 37개 전부 통과

- 대장 AI가 계산된 안전 최저치 이상에서 물리 근거 파일로 하위 AI 수를 증원 가능
- worker별 불변 dispatch JSON과 실제 디스크 SHA-256
- worker별 실제 호출 영수증 JSON과 중복 영수증 차단
- 모든 worker 결과가 최소 한 번 검토되는 ring 교차검토
- worker 역할 shard 고유성 검사
- lead-contract SHA-256과 plan fingerprint 기반 대장 AI 집계
- 8개 전체 단계에 대해 2~60 배정·dispatch·lead contract 회귀 테스트
- 프로젝트 규모에 따라 하위 AI 최소 2개·최대 60개 동적 계산
- 무조건 60개 호출 금지
- 파일·요구사항·페이지·필드·로직·기능·위험·도구 수 기반 단계별 scaling
- worker/task/role/scope immutable plan과 fingerprint
- 독립 Codex session ID와 물리 결과 파일·SHA-256 강제
- 동일 session·동일 결과 해시 차단
- 하위 AI 교차검토 필수
- 대장 AI의 전체 worker 집계·충돌 해결 증거 필수
- `/agents` fallback을 실제 하위 AI 완료로 오인하지 않도록 분리
- 하위 AI 정책·계획 변조 자동복구
- 집계만 누락된 경우 기존 유효 worker 결과 보존
- orchestration plan·ledger·aggregation을 단계 checkpoint와 release receipt에 포함

## 기존 3.0 기능 유지

- Codex 웹 마켓플레이스 구조
- 8단계 상태 머신·우회 차단
- 비종료 자동수리·전략 세대 변경
- 분석폴더 분기·자동복구
- 원문·run-lock 이중 해시 잠금
- 실제 본문 추출
- 모든 페이지 독립 목업·PNG
- 이미지·모션·reduced-motion
- 웹 3브라우저·axe·Lighthouse·시각회귀
- Android 무설치 에뮬레이터·스크린샷 테스트
- iOS Simulator
- 조건부 도구 자동 활성화
- APK 설치 명령 차단
