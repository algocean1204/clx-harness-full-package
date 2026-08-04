---
description: Show a Korean+English one-line summary of every slash command in this setup
---

Print the table below EXACTLY as-is (두괄식, no preamble). Then glob `~/.claude/commands/*.md` — if any command exists that is not in the table, append it using its frontmatter `description` (KR line first, then EN line). Do nothing else.

| 커맨드 | 요약 |
|---|---|
| `/grok` | 명시적으로 지정한 작업 1단위를 Grok에 위임. Delegate one explicitly assigned unit to Grok. |
| `/gpt` | 명시적으로 지정한 Git 작업 1단위를 Codex에 위임. Delegate one explicitly assigned Git unit to Codex. |
| `/harness` | 프로젝트 설명 → 에이전트 팀+스킬 생성(clx-harness-factory, 상한 준수). Generate a project agent team + skills via clx-harness-factory, caps enforced. |
| `/backup` | 폴더의 `.backup-repo` 마커를 읽어 프라이빗 깃허브로 백업; 첫 실행은 질문→설정→푸시 원패스. Marker-driven private GitHub backup; first run asks, configures, pushes in one pipeline. |
| `/supercoder` | 해시 검증 패치 규율로 코딩(명시 호출 전용). Hash-verified patch discipline for coding — explicit invocation only. |
| `/preprocess` | 모호·다항목 요청을 기계검증 가능한 계약으로 전처리(필요시 자동 로드도 됨). Preprocess fuzzy/multi-item intake into a checkable contract; may also self-load. |
| `/clx-grill-me` | 요구·제약·숨은 가정을 집요하게 인터뷰로 발굴. Relentless interview to surface intent, constraints, hidden assumptions. |
| `/ponytail` | 게으른(최소) 해법 강제 모드 레벨 전환(lite/full/ultra). Switch the lazy-minimal coding discipline level. |
| `/clx-update` | 하네스 전체를 최신판으로 갱신(클론 pull → 드라이런 → 병합 적용 → 검증). 채운 `user/`는 보존. Update the whole harness from its clone; filled `user/` files are preserved. |
| `/clx-help` | 이 도움말 — 내 세팅의 슬래시 커맨드 요약. This help — slash commands in this setup. |
