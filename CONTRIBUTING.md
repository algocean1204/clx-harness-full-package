# 기여 가이드 (Contributing)

PR과 Issue를 환영합니다. 이 레포는 Claude Code + Codex 에이전트 하네스의 **클린 배포판**이라,
"누가 클론해도 그대로 동작"이 최우선 가치입니다. 기여도 그 기준으로 리뷰됩니다.

## 환영하는 기여

- 설치기 개선/버그 수정 — `install.sh`, `windows-harness/install.ps1` (특히 Windows 경로·인코딩·Python 감지)
- `windows-harness/hooks/` Python 포트 버그 수정
- 스킬(`common/*/skills/`)·가이드 문서의 오류 수정과 명료화
- `docs/` 시각화 사이트 개선 및 번역(영어·중국어) 품질 향상
- 새 OS/셸 환경 호환성 리포트 (Issue로)

## PR 규칙

1. **작게, 한 주제로.** 여러 변경은 PR을 나누세요.
2. **개인정보·시크릿 절대 금지.** 홈 경로는 `__CLX_HOME__`, 계정은 `OWNER` 플레이스홀더 유지.
   제출 전 자가 점검:
   ```bash
   grep -rIE '/Users/[A-Za-z]+|@gmail\.com' common --exclude-dir=plugins-vendored | grep -v p5.js   # 매치 0건이어야 함 (벤더 원문·p5.js 표기는 검사 대상 아님)
   ```
3. **설치기 드라이런이 깨지면 안 됩니다.** `./install.sh --check`(macOS/Linux) 또는
   `install.ps1 -Check`(Windows)가 에러 없이 끝나는지 확인 후 제출.
4. 코드·식별자·커밋 메시지는 영어, 문서는 한국어 기본(영/중 병기 환영).
5. 커밋/PR에 AI 도구 표기(Co-Authored-By 봇 서명 등)를 넣지 마세요.

## English summary

PRs/issues welcome. Keep changes small and single-topic; never include personal data or
secrets (keep `__CLX_HOME__` / `OWNER` placeholders); make sure `./install.sh --check` or
`install.ps1 -Check` still passes; code/identifiers/commits in English; no AI attribution
in commits. Vendored third-party assets (e.g. p5.js) keep their original licenses.
