# KH_Aw 3.2 네이티브 기능·도구·대장/하위 AI 강제 보고서

## 1. 단계별 Codex 네이티브 기능

| 단계 | 우선 활용 기능 |
|---|---|
| intake | `/goal`, `/plan`, `/agents` |
| analyze | `/goal`, `/context`, `/agents`, `/artifact` |
| research | `/goal`, `/agents`, `/search`, `/artifact` |
| design | `/goal`, `/plan`, `/agents`, `/artifact` |
| implement | `/goal`, `/agents`, `/diff` |
| review | `/goal`, `/agents`, `/review`, `/diff` |
| test | `/goal`, `/agents`, `/test` |
| release | `/goal`, `/agents`, `/artifact`, `/diff` |

필수 네이티브 기능은 실제 session ID, invocation, 결과 파일, Codex rollout JSONL을 모두 등록한다. 필수 UI 기능을 실행할 수 없는 표면은 Git·파일·웹본문·브라우저 결과만으로 통과시키지 않고 차단한다.

`/agents` 배정표만으로는 실제 하위 AI 완료로 인정하지 않는다. 실제 독립 Codex 세션 JSONL, 호출 영수증, 결과 파일, 교차검토가 별도로 필요하다.

## 2. 모든 단계의 대장 AI와 동적 2~60개 하위 AI

다음 8개 단계 모두 동일한 강제 계약을 적용한다.

```text
intake → analyze → research → design → implement → review → test → release
```

- 단계마다 대장 AI 1개와 독립 하위 AI 최소 2개가 필요하다.
- 하위 AI 최대값은 60개다.
- 파일·디렉터리·요구사항·페이지·필드·로직·기능·위험·연구 요소·필수 도구·릴리스 산출물로 안전 최저치를 계산한다.
- 대장 AI는 계산된 최저치보다 적게 배정할 수 없다.
- 대장 AI는 실제 프로젝트 근거 파일을 제출하면 60개 범위 안에서 증원할 수 있다.
- 낮거나 중간 규모 프로젝트에 60개를 고정하는 행위는 실패한다.
- run-lock을 변경해 최소값·최대값·증원 규칙을 약화하면 자동복구한다.

## 3. 프롬프트가 아닌 물리 실행 강제

각 하위 AI에 대해 다음 파일과 해시가 모두 필요하다.

1. `agent-plan.json`의 불변 assignment
2. worker별 `dispatch/<worker-id>.json`
3. dispatch JSON의 SHA-256
4. 실제 Codex invocation receipt JSON
5. worker와 task가 표시된 물리 결과 파일
6. 독립 session ID
7. 결과 파일 SHA-256
8. 계획된 다른 worker의 교차검토 결과

호출 영수증은 stage, worker ID, task ID, session ID, delegation mode, 실제 invocation, dispatch SHA-256, issuedAt을 포함해야 한다. 호출 영수증이나 결과 파일을 복사하면 중복 해시로 실패한다.

## 4. 전체 결과 순환 교차검토

한 명의 최종 reviewer만 두지 않는다. 모든 worker가 다른 worker 한 명을 검토하는 ring 구조를 생성한다. 따라서 계획된 모든 worker 결과가 최소 한 번씩 다른 독립 하위 AI에게 검토돼야 한다.

검토 대상 누락, 자기 자신 검토, 계획과 다른 대상 검토, 전체 worker 검토 커버리지 부족은 단계 실패다.

## 5. 대장 AI 집계

대장 AI는 worker와 다른 독립 session을 사용하고 다음을 물리 집계 파일에 남긴다.

- plan fingerprint
- lead-contract SHA-256
- 모든 accepted worker ID
- 중복 제거 결과
- 충돌 해결 결과
- 미검토·미할당 범위 확인
- 실제 단계 산출물에 반영한 결과

모든 계획 worker를 수용하지 않으면 단계가 통과하지 않는다.

## 6. 웹 도구

- 실제 개발 서버 실행
- Playwright Chromium·Firefox·WebKit
- axe-core 접근성 검사
- 모바일·태블릿·데스크톱 viewport
- console·network·404·이미지 오류
- 시각 회귀
- Lighthouse
- 전체 페이지 화면 증거

## 7. Android 도구—APK 설치 제외

- Java·Gradle·Android SDK·ADB·Emulator 탐지
- Gradle build·unit test·lint
- 설치가 필요 없는 screenshot test
- AVD 목록·부팅·health·system screenshot
- Logcat 오류 검사

다음 명령은 실행 전후에 이중 차단한다.

```text
adb install
pm install
installDebug
connectedAndroidTest
bundletool install-apks
```

## 8. iOS 및 조건부 도구

- xcodebuild·simctl
- build·unit test
- Simulator 목록·부팅·UI 증거
- TypeScript typecheck
- dependency audit
- Firebase Emulator Suite
- Docker Compose 검증
- Flutter analyze·test·build
- OpenAPI 검증

## 9. 자동수리

게이트 실패는 종료가 아니다. 유효한 worker 결과는 보존하고 누락된 worker, 영수증, 교차검토, 대장 집계, 도구 증거만 다시 생성한다. 동일 원인이 반복되면 수리 전략 세대를 변경한다.
