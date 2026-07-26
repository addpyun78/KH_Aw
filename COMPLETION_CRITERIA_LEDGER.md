# Completion Criteria Ledger

Status meanings: `verified-local`, `implemented-needs-full-run`, `external-not-run`.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Compare at least 15 plugins | verified-local | `research/PUBLIC_PLUGIN_REPOSITORY_LIST.json` |
| 2 | Record URLs and commits | verified-local | repository list and citation ledger |
| 3 | Prove structural differences | verified-local | structural difference report |
| 4 | Reproduce actual doctor failure | verified-local | manual bypass reproduction and session path |
| 5 | Compare install and source | verified-local | installation snapshots |
| 6 | Cache/shadow/version/path inspection | verified-local | installation module and E2E |
| 7 | Single entrypoint | verified-local | skill visibility doctor |
| 8 | Platform capability detection | verified-local | capability matrix and target inference |
| 9 | Remove unsupported fixed command contract | verified-local | physical-capability policy |
| 10 | Separate plugin/project doctor | verified-local | `doctor`, `project-doctor` |
| 11 | Runtime bootstrap | verified-local | runtime module and init link |
| 12 | Resume | verified-local | resume module and regression test |
| 13 | Semantic requirement compilation | verified-local | compiler and tests |
| 14 | Source reachability | verified-local | reachability module and init output |
| 15 | Research evidence linking | implemented-needs-full-run | source registry and citation ledger |
| 16 | Task graph | verified-local | task graph module and tests |
| 17 | Subagent orchestration | verified-local | existing engine plus independent audit |
| 18 | Cause-specific repair | verified-local | issue classifier and strategy history |
| 19 | Independent verification | implemented-needs-full-run | verifier module and independent audit |
| 20 | Claim verifier | verified-local | claim verifier and session binding |
| 21 | Single version ledger | verified-local | `VERSION_LEDGER.json` |
| 22 | Distribution cleanup | verified-local | distribution doctor |
| 23 | Unit tests | verified-local | test evidence |
| 24 | Integration tests | verified-local | CLI doctor and E2E |
| 25 | Packaging tests | verified-local | deterministic ZIP case |
| 26 | Actual Codex install E2E | external-not-run | exact state not published/installed |
| 27 | Direct `@kh-aw` E2E | external-not-run | requires fresh installed session |
| 28 | Doctor | verified-local | source and distribution doctor |
| 29 | Run creation | verified-local | attached instruction created a plugin-target run |
| 30 | Full stage chain | implemented-needs-full-run | needs real eight-stage run |
| 31 | Return after repair | implemented-needs-full-run | controller retained; full run needed |
| 32 | Resume after session change | verified-local | temp run resumed active ticket without reset |
| 33 | Continue after manual bypass | implemented-needs-full-run | one-entry state design; real run needed |
| 34 | Missing fixture blocks release | verified-local | existing gate regressions |
| 35 | Repaired fixture passes release | implemented-needs-full-run | full release fixture needed |
| 36 | Final release receipt | implemented-needs-full-run | existing finalize controller; real run needed |
| 37 | Audit equals real E2E | external-not-run | requires criterion 26 |
| 38 | Reinstall ZIP and rerun | external-not-run | requires publication/install |
| 39 | Identify active version with old cache | implemented-needs-full-run | resolver tested; actual install needed |
| 40 | Beginner documents | verified-local | `docs/*.md` |
