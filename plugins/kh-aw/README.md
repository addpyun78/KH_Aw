# KH_Aw Codex Plugin 3.2.0

- 표시 이름: **KH_Aw**
- 플러그인 ID: **kh-aw**
- 대상: Codex 웹 Git 마켓플레이스/플러그인
- 단계별 하위 AI: **동적 최소 2개·최대 60개**
- APK 설치: **금지**

## 포함 스킬

1. `kh-aw-full-cycle`: 전체 8단계 실행과 자동수리
2. `kh-aw-multi-agent-orchestration`: 단계별 대장 AI·2~60개 독립 하위 AI
3. `kh-aw-audit-upgrade`: 전체 파일·요구사항·로직 전수조사
4. `kh-aw-research-design`: 실제 본문 추출과 전체 페이지 목업
5. `kh-aw-implementation-repair`: 실제 구현·추적·비종료 자동수리
6. `kh-aw-release-company`: 실제 도구 검증과 회사용 릴리스

## 실행 진입점

```bash
python3 scripts/kh_aw_cli.py doctor --plugin-root . --marketplace-root ../..
python3 scripts/kh_aw_cli.py init --project-root <project> --instructions-file <exact.txt> --target <target>
python3 scripts/kh_aw_cli.py prepare-agents --run-root <run> --stage <stage>
python3 scripts/kh_aw_cli.py record-subagent ...
python3 scripts/kh_aw_cli.py aggregate-agents ...
python3 scripts/kh_aw_cli.py agent-status --run-root <run> --stage <stage>
python3 scripts/kh_aw_cli.py advance --run-root <run> --stage <stage> --strict
python3 scripts/kh_aw_cli.py run-toolchain --run-root <run> --strict
python3 scripts/kh_aw_cli.py finalize --run-root <run> --strict
```

## 하위 AI 물리 게이트

각 단계의 `agent-plan.json`은 프로젝트 복잡도를 다시 계산하여 2~60개를 배정합니다. 계획 파일의 수량이나 역할을 임의로 낮춰도 게이트가 원래 계산값과 fingerprint를 비교하므로 통과하지 않습니다.

각 하위 AI는 다음이 필요합니다.

- 계획에 존재하는 worker/task/role
- 독립 Codex 세션 ID
- `/agents` 실제 호출 또는 독립 Codex task
- run root 내부 물리 결과 파일
- 고유 SHA-256
- 최소 한 건의 교차검토
- 모든 worker를 수용한 대장 AI 집계 파일

`exercise-native`로 생성한 `/agents` fallback 배정표는 하위 AI 완료 증거가 아닙니다.

## 도구 검증

웹은 Chromium·Firefox·WebKit·axe·Lighthouse·시각회귀를, Android는 Gradle·스크린샷 테스트·AVD/ADB 상태·Logcat을, iOS는 xcodebuild·Simulator를 대상으로 합니다. 도구 실행 로그·종료코드·버전·산출물·SHA-256이 없으면 통과하지 않습니다.

Android APK 설치 명령은 실행 전에 거부되며 실행 기록에서도 다시 탐지됩니다.
