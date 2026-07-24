# KH_Aw Codex 웹 실행 런북 3.2

## 1. 사용자 지시 원문 저장

사용자 요청을 요약·재작성하지 말고 UTF-8 텍스트 파일로 저장한다.

```bash
cat > /작업경로/user-instructions.txt <<'EOF'
사용자 원문 전체
EOF
```

## 2. 패키지 검사

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py doctor \
  --plugin-root <plugin-root> \
  --marketplace-root <marketplace-root>
```

## 3. 실행 초기화

### 분석폴더가 제공된 경우

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py init \
  --project-root <결과물 프로젝트 경로> \
  --analysis-folder <사용자 제공 분석폴더> \
  --output-root <분석폴더 밖 별도 출력 경로> \
  --instructions-file <user-instructions.txt> \
  --target <대상> \
  --name <프로젝트명>
```

분석폴더는 전수 목록·ZIP 백업·SHA-256 스냅샷으로 보호한다. 결과물과 `.kh_aw` 작업공간은 분석폴더 안에 생성하지 않는다.

### 분석폴더가 없는 경우

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py init \
  --project-root <프로젝트 경로> \
  --instructions-file <user-instructions.txt> \
  --target <대상> \
  --name <프로젝트명>
```

## 4. 모든 단계의 하위 AI 실행

고정 순서:

```text
intake → analyze → research → design → implement → review → test → release
```

각 단계에서 다음을 반복한다.

### 4-1. 대장 AI가 동적 배정표 생성

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py prepare-agents \
  --run-root <run-root> --stage <stage>
```

`agent-plan.json`의 수량은 최소 2, 최대 60이다. 60개를 고정하지 않는다.

### 4-2. 실제 독립 하위 AI 호출

`dispatch-manifest.json`의 모든 assignment를 Codex `/agents` 또는 독립 Codex task로 실행한다. 작업별 결과는 서로 다른 파일로 저장한다.

```text
<run-root>/orchestration/<stage>/outputs/<worker-id>.md
```

마지막 cross-reviewer는 적어도 하나의 다른 worker 결과를 읽고 검증한다.

### 4-3. 하위 AI 결과 등록

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py record-subagent \
  --run-root <run-root> \
  --stage <stage> \
  --worker-id <worker-id> \
  --task-id <task-id> \
  --session-id <독립 Codex 세션 ID> \
  --invocation "/agents <호출 내용>" \
  --delegation-mode native-agents \
  --evidence-file <물리 결과 파일> \
  [--review-of <다른 worker-id>]
```

### 4-4. 대장 AI 최종 집계

대장 AI는 모든 worker 결과를 읽어 중복·충돌·누락을 해결하고 실제 단계 장부와 프로젝트 파일을 수정한다. 집계 근거를 별도 파일로 저장한다.

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py aggregate-agents \
  --run-root <run-root> \
  --stage <stage> \
  --lead-agent-id <lead-id> \
  --lead-session-id <worker와 다른 세션 ID> \
  --evidence-file <lead-aggregation.md>
```

### 4-5. 오케스트레이션 검사

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py agent-status \
  --run-root <run-root> --stage <stage>
```

### 4-6. 단계 게이트

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py advance \
  --run-root <run-root> --stage <stage> --strict
```

실패 시 시스템은 종료 상태로 확정하지 않는다. `next-action.json`과 수리 티켓에 따라 실제 원인·파일·증거를 수리한 뒤 같은 단계를 다시 실행한다.

## 5. 웹 본문 연구

검색결과 목록은 증거가 아니다. 실제 페이지 본문을 저장한다.

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py fetch-source \
  --run-root <run-root> \
  --element-id <연구 요소 ID> \
  --source-type <web|github|official> \
  --url <실제 본문 URL> \
  --query <사용한 검색어> \
  --project-fit-reason <현재 프로젝트에 필요한 이유>
```

로그인·CAPTCHA·접근 거부·검색결과 페이지는 거절한다.

## 6. 도구 설정과 실행

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py bootstrap-tools --run-root <run-root>
python3 <plugin-root>/scripts/kh_aw_cli.py configure-tools --run-root <run-root> [프로젝트 설정]
python3 <plugin-root>/scripts/kh_aw_cli.py run-toolchain --run-root <run-root> --strict
```

APK 설치는 제외한다. `adb install`, `pm install`, `installDebug`, `connectedAndroidTest`, `bundletool install-apks`를 실행하지 않는다.

## 7. 최종 완료

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py finalize --run-root <run-root> --strict
```

모든 단계 게이트, 하위 AI 장부, 실제 도구 증거, 수리 티켓이 통과한 경우에만 `release/release-receipt.json`이 생성된다.
