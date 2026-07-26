# KH_Aw 초보자 사용 안내

## 처음 설치할 때

1. GitHub에서 KH_Aw 마켓플레이스를 Codex 플러그인으로 설치합니다.
2. 설치 뒤에는 반드시 새 Codex 작업을 엽니다.
3. 새 작업에서 `@kh-aw`를 선택해 요청 내용을 그대로 입력합니다.
4. KH_Aw가 보여 주는 doctor 결과에서 `ok: true`인지 확인합니다.

## 새 작업 시작

프로젝트 폴더에서 다음 형식으로 실행합니다.

```powershell
python <설치된-KH_Aw>\scripts\kh_aw_cli.py init `
  --project-root . `
  --instructions-file C:\경로\작업지시서.txt `
  --target-auto
```

`target-auto`는 파일과 지시문을 함께 보고 웹, 앱, 플러그인 같은 작업 종류를
고릅니다.

## 작업이 중단됐을 때

프로젝트 폴더에서:

```powershell
python <설치된-KH_Aw>\scripts\kh_aw_cli.py resume --project-root .
```

새로 시작하지 않고 저장된 단계와 수리 기록에서 이어집니다.

## 문제가 생겼을 때

먼저 플러그인 자체를 검사합니다.

```powershell
python <설치된-KH_Aw>\scripts\kh_aw_cli.py doctor --plugin-root <플러그인-폴더>
```

그다음 진행 중인 프로젝트를 검사합니다.

```powershell
python <설치된-KH_Aw>\scripts\kh_aw_cli.py project-doctor --project-root .
```

결과의 `actual`은 실제 문제, `repair`는 고칠 위치, `reverify`는 다시 확인할
명령입니다. 캐시 폴더를 직접 수정하지 마세요.
