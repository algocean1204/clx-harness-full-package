# Credits — 참조·벤더링한 오픈소스

이 하네스는 아래 프로젝트들을 참조하거나 일부를 벤더링했습니다. 링크만 가볍게 남깁니다 —
각 자산의 라이선스는 원 저장소를 따르며, 벤더링본에는 해당 고지를 함께 둡니다.

## 벤더링 (실물 포함)

- <https://github.com/anthropics/claude-plugins-official> — skill-creator · plugin-dev · LSP 3종 (`common/claude/plugins-vendored/`)
- <https://github.com/DietrichGebert/ponytail> — ponytail 플러그인 (같은 위치)
- <https://github.com/anthropics/skills> — document-skills(docx·pptx·xlsx·pdf) (같은 위치)

- <https://github.com/revfactory/harness-100> — 100종 팀 하네스 라이브러리 (`common/agents/harness-library/`, Apache-2.0, ko판 · [en판](https://github.com/revfactory/harness-100/tree/main/en))
- <https://github.com/revfactory/harness> — clx-harness-factory의 포크 원본 (v1.2.0, Apache-2.0)
- <https://github.com/emilkowalski/skills> — clx-apple-design 원본 (17 principles)
- <https://github.com/facebook/astryx> — clx-astryx가 스냅숏한 React 디자인 시스템
- Meodai `skill.color-expert` — clx-color-expert 원본 (CC BY 4.0)
- <https://github.com/MohamedAbdallah-14/unslop> — clx-unslop이 감싸는 CLI
- 업종별 웹사이트 컬러 가이드 (에이원 스튜디오, <https://aewonstudio.com/>) —
  `clx-color-expert/references/industry-palettes.md`의 무드 7·업종 30 매핑 출처
  (<https://cool-mint-391.notion.site/3b0cd7df65e08103bafdc3d0babc2389>, 2026-08-02 열람).
  hex·매핑은 데이터로 인용하고 주의사항 문구는 자체 표현으로 재작성했으며, 원문에 없는 **WCAG 실측과
  수리표**(역할 쌍 28건 중 8건 AA 미달)를 덧붙였습니다 — 방향 참조용이지 토큰 소스가 아닙니다.
- <https://github.com/artemnovitckii/content-skills> — 글쓰기 팩 `dumbify` · `storytelling` ·
  `viral-hooks` · `anti-ai-writing` · `voice-dna` (MIT, 업스트림 `1c6e909`). 벤더링본에는 코어
  rule 4/8과 충돌하지 않도록 **적용 범위 가드**(발행용 콘텐츠 전용 — 보고·커밋·코드 주석 제외)와
  한국어 애드덤을 추가했고, `voice-dna`는 업스트림에 SKILL.md가 없어 빌드 가이드를 스킬로 감쌌습니다.
  생성되는 문체 프로필은 개인 지문이라 공개판에는 **빈 템플릿만** 들어갑니다.
- p5.js (<https://p5js.org>) — clx-algorithmic-art 동봉 에셋
- Vercel Web Interface Guidelines — clx-vercel-web-design-guidelines 오프라인 스냅숏

## 참조 (실물 미포함, 연동/도구)

- <https://github.com/Graphify-Labs/graphify> — 코드베이스 지식 그래프 CLI (선택 확장)
- <https://github.com/headroomlabs-ai/headroom> — 컨텍스트 압축 프록시 (선택 확장, 옵트인 wrap)

- <https://github.com/arinspunk/claude-talk-to-figma-mcp> — Figma MCP 경로 (npx @latest)
- <https://lucide.dev> — docs/ 시각화 사이트 아이콘 (인라인 SVG)
- Playwright (<https://playwright.dev>) — clx-playwright가 구동하는 브라우저 자동화
- <https://github.com/anthropics/skills> · Anthropic 공식 마켓플레이스 — 첫 실행 시 자동 설치되는 공개 플러그인·스킬들
- <https://github.com/openai/codex> — Codex CLI (연동 대상)
