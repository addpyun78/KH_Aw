# KH_Aw 산출물 계약

모든 경로는 `kh-aw-state.json`의 `workspaceRoot` 기준이다.

## requirements/raw-instruction-ledger.json

```json
[
  {
    "lineId": "LINE-*",
    "lineNumber": 1,
    "sourceText": "사용자 원문 한 줄",
    "requirementIds": ["REQ-*"],
    "status": "analyzed",
    "evidence": ["analysis/analysis.json#..."]
  }
]
```

## requirements/requirements.json

각 항목은 `id`, `requirement`, `source`, `priority`, `acceptanceChecks`를 가진다.

## analysis/analysis.json

필수 항목:

- requirements
- requirementCoverage
- pageInventory
- fieldInventory
- logicInventory
- researchPlan.elements
- risks
- omissions
- analysisFolderEvidence
- summary

`pageInventory`는 실제 기존 화면과 사용자 요구 화면의 합집합이다.

## research/evidence.json

`sources[]`의 accepted=true 조건:

- httpStatus=200
- bodyTextLength>=500
- bodySha256 64자리
- bodyExcerpt 160자 이상
- extractionMode이 허용값
- 차단 페이지가 아님

각 source는 sourceId, sourceType, URL, query, elementIds, 본문 근거, 디자인 신호를 가진다.

## design/design.json

필수 항목:

- pageInventory
- screenBlueprints
- visualStructureBoard
- designApplicationLedger
- designTokenProvenance
- imagePlacementPlan
- motionStoryboard
- designImplementationMap
- manualSelection=false

모든 pageId는 고유한 실제 HTML/SVG 목업과 연결한다.

## implementation/implementation.json

필수 원장:

- visualDesignConformance
- featureImplementationLedger
- fieldImplementationLedger
- logicImplementationLedger
- imageAssetLedger
- motionImplementationLedger
- changedFiles

모든 파일 경로는 implementationRoot 기준 상대 경로다.

## review/review.json

`visualDesignReview[]`는 모든 pageId를 포함하고 다음 boolean을 모두 true로 만든다.

- structureMatched
- fieldsMatched
- logicMatched
- featuresMatched
- imagesMatched
- motionMatched
- overlapFree
- passed

각 페이지는 actualScreenshotPath PNG를 가진다.

## test/test-report.json

- commands: command, exitCode=0, outputSha256, logPath
- visualRegression: 모든 pageId, passed=true
- accessibility: 실제 검사 결과
- status: complete

## tickets/REPAIR-*.json

티켓은 삭제하지 않는다. 수리 후 status=closed와 closureEvidence를 기록한다.

## release/release-receipt.json

최종 게이트가 직접 생성하며 사람이 미리 만들지 않는다.
