# 문제 진단 안내

## doctor가 폴더 이름 오류를 표시할 때

새 doctor는 `kh-aw` 소스 폴더와 `kh-aw/4.0.0` 형식 캐시를 모두 이해합니다.
계속 오류가 나면 `actual`에 표시된 manifest 이름과 버전을 확인합니다.

## 해시 오류가 많이 나올 때

Windows 줄바꿈 차이는 normalized-LF 검사로 구분됩니다. 한두 파일만 계속
실패하면 실제 내용 변경일 수 있으므로 해당 파일을 다시 설치합니다.

## 예전 스킬이 여러 개 보일 때

오래된 캐시 또는 오래된 세션입니다. 플러그인 관리 기능으로 업데이트하고 새
Codex 작업을 엽니다. 캐시 폴더를 손으로 덮어쓰지 않습니다.

## 작업이 처음부터 다시 시작될 때

`init` 대신 `resume --project-root <프로젝트>`를 실행합니다.
`project-doctor`가 state, runtime, task graph 중 어느 파일이 빠졌는지 보여 줍니다.

## 같은 수리가 반복될 때

`repairs/<stage>/attempt-*/repair-ticket.json`의 `classification`과
`strategyHistory`를 확인합니다. 같은 서명은 전략 세대를 바꿔야 하며 단순
재시도만으로 통과하지 않습니다.

## 완료라고 했지만 증거가 없을 때

`verify-run`을 실행합니다. 단계 gate, 요구사항 증거, release receipt 중 하나라도
없으면 실패합니다.
