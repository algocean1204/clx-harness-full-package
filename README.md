# clx-harness-full-package

> **구조 시각화 사이트**: <https://algocean1204.github.io/clx-harness-full-package/> —
> 레포 구성·스킬 카탈로그·설치 흐름을 한눈에 (한국어/English/中文).

**한 줄 요약: Claude Code + Codex 에이전트 하네스의 "클린 배포판"입니다.** 에이전트의 행동을
규정하는 설정(라우터·규칙·가이드·스킬·안전 훅·settings)만 담았고, **개인정보는 전혀 없습니다.**
개인용 전체 백업에서 시크릿·메모리·세션·오너 전용 도구를 걷어낸 판본이라, **새 맥·윈도우 머신이나
친구 머신**에 그대로 복제해 같은 하네스를 재현하는 용도입니다. **git 원격은 설정돼 있지 않고, 절대
자동 푸시하지 않습니다.** 푸시가 필요하면 직접 붙이세요.

## OS별 활성화

클론은 **공통**입니다(모든 폴더가 항상 들어있음). 활성화는 **OS별로 자동 분기**됩니다:
`install.sh`(macOS/Linux)는 `common/` + `macos-harness/`만, `install.ps1`(Windows)는
`common/` + `windows-harness/`만 적용하고 나머지는 명시적으로 건너뜁니다. 두 설치기 모두
무엇을 건너뛰었는지 요약에 출력합니다. **윈도우도 1급 지원**입니다 — bash 훅은 설치 시
크로스플랫폼 Python 포트로 교체되어 실제로 동작합니다(아래 Windows 참고).

## 구성

```
common/            플랫폼 공통 페이로드 (홈 경로는 __CLX_HOME__ 토큰으로 치환됨)
  claude/          -> ~/.claude   (CLAUDE.md, rules, guides, skills, agents, hooks, settings.json,
                                   plugins-vendored/ = 로컬 마켓플레이스 — 플러그인 11종 실물)
  codex/           -> ~/.codex    (AGENTS.md, rules, guides, skills, prompts, hooks, config.toml 안전 부분집합)
  agents/          -> ~/.agents   (AGENTS.md 코어 + models.toml + harness-library/ = 팀 하네스 100종)
  grok/            -> ~/.grok     (config.toml의 sandbox 기본값; 기존 다른 설정은 보존)
  local-bin/       -> ~/.local/bin (Codex·Claude Code 위임 실행기)
macos-harness/     macOS 전용 (launchd 잡, disk-guard.sh) + personal-examples/ (오너 푸시 예시)
windows-harness/   install.ps1 + hooks/ (bash 훅의 크로스플랫폼 Python 포트) + README
setup-ui/          설치 상태를 보고 모델을 전환하는 로컬 페이지 (stdlib만, 온디맨드, 한/영·라이트/다크)
install.sh         macOS/Linux 설치기 (--check / --apply)
update-vendored.sh 벤더 자산(플러그인·하네스 100종) 주기 갱신 (diff 리뷰 → 수동 커밋)
PRINCIPLES.md      설계 원칙 공개 요약 · credits/ 참조 오픈소스 링크
```

## 내 설정 보고 모델 바꾸기 (setup-ui)

```bash
python3 setup-ui/server.py     # 브라우저가 알아서 열립니다 (--no-open 이면 URL만 출력)
```

설치 상태·플러그인·스킬·훅·하네스 개수·`user/` 파일 목록(+오너 머신이라면 `config-doctor` 결과)을 한 페이지로
보여주고, **모델 전환**을 한 번의 클릭으로 처리합니다. 한국어가 기본이고 영어로 전환 가능, 테마는
시스템·라이트·다크 중 선택(선택은 브라우저에 기억됩니다).

**모델 전환** — 역할마다 지금 설치된 백엔드가 실제로 제공하는 모델만 칩으로 뜹니다(`grok models`,
Codex 모델 카탈로그). 카탈로그에 없는 모델이나 그 모델이 지원하지 않는 강도는 서버가 400으로 거부하고,
자기 위임 단계(`ultra`)는 애초에 목록에 없습니다. CLI가 없는 역할은 "쓰이지 않음"으로 표시됩니다.

**쓰기 범위** — 이 서버가 쓰는 파일은 `~/.agents/models.toml` **하나뿐**이고, 그 안에서도 `model`/`effort`
줄만 바꿉니다. 주석·다른 역할·`owner_pinned`는 그대로 남고, 변경 직전 파일은 `models.toml.bak`으로 보관됩니다.
`~/.codex/config.toml`은 **건드리지 않습니다** — 그건 대화형 Codex 기본값이고 레지스트리는 위임 핀이라
서로 독립입니다. 그 외 모든 접근은 읽기이고, 실행하는 것은 있으면 `config-doctor.py` 1회(타임아웃 있음)뿐입니다.

파이썬 표준 라이브러리만 사용, 127.0.0.1 바인딩 + Host/Origin 검증(다르면 403), 30분 유휴 시 자동 종료.
실행하면 브라우저가 바로 열리므로 토큰을 옮겨 적을 일이 없고, 페이지 껍데기(정적 HTML)는 토큰 없이도 열려서 **새로고침이 그냥 됩니다** — 이 머신에 대한 데이터는 한 바이트도
들어있지 않고, 실제 상태 조회와 모델 전환 엔드포인트는 전부 **실행마다 새로 생기는 토큰**(상수시간 비교)을
요구합니다. 토큰은 주소창에서 지워지고 그 탭의 sessionStorage에만 남습니다(탭 닫으면 소멸). 기본 포트 23456은 `CLX_SETUP_UI_PORT` 또는 `--port`로 변경.
`user/` 파일은 **이름만** 표시하고 내용은 읽지 않습니다.

## 다른 AI에 작업 맡기기

사용자가 실행기를 직접 지정한 요청은 작업 1단위에 한해 위임할 수 있습니다. Claude Code에서는
`/grok`, `/gpt`, Codex에서는 `/grok`, `/claude`를 사용합니다. 자연어로 같은 대상을 명시해도 동일하게
처리하며, 현재 실행기 자신을 지정하면 재호출하지 않고 그대로 작업합니다.

- `clx-grok-delegate`와 `clx-ai-delegate`가 Git 저장소 하나만 작업 대상으로 받습니다.
- Codex는 임시 세션과 `workspace-write` 샌드박스, Claude Code는 비영구 세션·빈 MCP 설정·제한된 도구로 실행됩니다.
- 외부 실행기가 다시 다른 외부 실행기를 부르는 체인, 같은 저장소의 동시 위임, 무제한 자동 재시도는 차단됩니다.
- CLI가 없으면 해당 위임만 건너뛰고 현재 실행기가 작업합니다. 모델과 effort는 `~/.agents/models.toml`이 정합니다.
- Windows의 Claude Code 위임은 OS 수준 Bash 샌드박스가 없으므로 파일 편집 도구만 허용합니다.

## 설치 (macOS / Linux)

```bash
./install.sh --check     # 드라이런: 환경 자동감지 결과 + 무엇을 어디에 쓸지 출력만
./install.sh --apply     # ~/.claude, ~/.codex, ~/.agents 에 설치
```

**환경 자동감지** — 두 모드 모두 시작할 때 이 머신 상태를 먼저 읽고 출력합니다: OS·python·git,
`claude`/`codex`/`grok`/`hermes-call` 설치 여부(없으면 그 기능은 꺼진 채로 둠), 기존 `~/.claude`·
`~/.codex`·`~/.agents`·`~/.grok` 유무와 파일 수, 인증 파일 존재(**손대지 않음**), 기존 `settings.json`,
채워둔 `~/.agents/user/`. 조용히 바뀌는 것이 없도록 하기 위한 것입니다.

**기존 환경은 흡수됩니다.** 이미 Claude Code를 쓰고 있었다면 `settings.json`을 덮어쓰지 않고
**병합**합니다 — 사용자의 `model`·`permissions`·`env`·본인 훅은 그대로 남고 하네스 훅만 추가되며,
직전 파일은 `settings.json.pre-clx-<시각>`으로 남습니다. 재설치해도 훅이 중복 등록되지 않습니다.
기존 Grok `config.toml`도 `config.toml.pre-clx-<시각>`으로 보관한 뒤 다른 키는 유지하고
`[sandbox] profile`만 배포값으로 갱신합니다.

- `~/.claude`가 **이미 비어있지 않으면** `--force` 없이는 거부합니다. `--force`는 삭제가 아니라
  **병합**(같은 파일만 덮어씀, 기존 데이터는 안 지움)입니다.
- `--with-launchd`(macOS 전용, 선택): 로컬 미러 launchd 잡을 배치만 합니다. 자동 로드/푸시 안 함.
- 설치 시 `__CLX_HOME__` 토큰을 실제 `$HOME`으로 치환합니다. 원격/인증/Keychain은 건드리지 않습니다.

## 설치 (Windows) — 1급 지원

자세한 내용은 `windows-harness/README.md`.

```powershell
powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Check
powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Apply   # [-Force]
```

- **요구사항: PowerShell 5.1+ 또는 7+, 그리고 PATH의 Python 3**(`py -3`/`python`/`python3`).
- `%USERPROFILE%\.claude, .codex, .agents, .grok` 생성 + `common/` 복사 + 토큰 치환(정방향 슬래시).
- **훅 전체 활성화**: 설치기가 bash 훅을 크로스플랫폼 Python 포트로 바꾸고, 모든 훅 명령을
  감지된 Python 런처로 실행되게 재작성합니다. **Python이 없으면** 세션이 깨지지 않도록 훅을
  아예 등록하지 않고(그리고 statusLine 제거) 요약에 비활성으로 표시합니다 — Python 설치 후 재실행.
- macOS 전용(`disk-guard`/launchd)은 Windows에서 등록하지 않습니다. 맥과 100% 동일한 경험이
  필요하면 WSL에서 `install.sh` 사용을 권장.

## 업데이트 (한 줄)

새 버전이 나오면 클론 폴더에서:

```bash
git pull --ff-only origin main && ./install.sh --apply --force
```

Claude Code 안에서는 **`/clx-update`** 한 번이면 같은 절차(pull → 드라이런 → 적용 → 검증)를
수행합니다. 적용이 끝나면 모델 레지스트리를 다시 검사해, 백엔드에 더 나은 모델이 생겼는데 핀이
뒤처져 있으면 그 자리에서 알려줍니다(고치는 건 `/clx-model`). `--force`는 **삭제가 아니라 병합**입니다 — 직접 추가한 스킬, 채워 넣은
`~/.agents/user/*`, `settings.json`의 본인 설정은 그대로 남습니다. 훅·스킬·플러그인이 바뀌었으면
Claude Code를 재시작하세요.

## 다른 머신에서의 동작 보증

이 하네스가 호스트에 대해 무엇을 가정하는지는 **한 곳에만** 있습니다 — `~/.claude/hooks/clx_host.py`.
훅은 임시 디렉터리·파일 크기·도구 존재 여부를 직접 캐지 않고 여기에 물어봅니다. 같은 질문에 두 답이
생기던 게 "여기선 되는데 저기선 죽는" 버그의 원인이었기 때문입니다(BSD `stat -f%z` vs GNU `stat -c%s`,
셸은 `/tmp` 파이썬은 다른 경로, 3.11 전용 `tomllib`, Windows에 없는 `fcntl`).

```bash
python3 ~/.claude/hooks/clx_host.py          # 이 머신이 무엇을 할 수 있는지 표로
```

- **아무것도 설치하지 않습니다.** 설치기는 세 디렉터리 밖을 안 건드린다고 보증하므로, 없는 도구는
  깔지 않고 **꺼졌다고 보고**합니다. 이 표는 설치 끝, `/clx-update` 끝, 그리고 위 `clx_host.py`가
  보여줍니다 (`config-doctor`는 원 소유자 레포 구조에 하드와이어돼 동봉되지 않습니다).
- **파이썬 하한은 3.9**(맥 기본). 배포되는 모든 `.py`가 매 검증마다 3.9로 컴파일·임포트됩니다.
- **선택 도구가 없어도 설치와 훅은 전부 정상 종료**합니다: `ruff`/`node`가 없으면 자동 포맷만,
  `grok`/`codex`가 없으면 그 위임만, TOML 파서가 없으면 레지스트리가 줄 단위 리더로 내려갑니다.
- POSIX 전용 기능(`fcntl` 기반 잠금, Grok 런타임)은 Windows에서 **한 줄로 이유를 말하고 빠집니다** —
  세 프레임 아래 `ImportError`가 아니라.

## 승인받는 작업의 두 단계 명세

승인이 필요한 작업은 채팅에서 `작업명세서 승인`을 먼저 받고, 그 범위 안에서
`개발명세서 승인`을 받은 뒤에만 구현합니다. 두 명세서는 별도 파일로 만들지 않습니다.
명세 이름에 번호나 버전 표기를 붙이지 않습니다.

- 작업명세서: 현재 상태, 기존 동작, 목표, 범위, 결과물, 완료 기준, 위험, 롤백
- 개발명세서: 파일별 변경, 실행 흐름, 명령·권한, 테스트, 배포·백업

목표·범위·권한·위험이 달라지면 작업명세서부터 다시 승인받고, 구현 방법만 달라지면
개발명세서만 다시 승인받습니다. 개발명세서 승인 전에는 읽기 전용 분석 외의 변경을 하지 않습니다.

### 채팅 완료 보고

승인받은 작업은 구현이 끝났다는 말만 남기지 않고 `작업명세 N/N`, `개발명세 N/N`, DoD,
실제 검증, 적용·배포·백업 상태를 채팅에서 함께 보고합니다. REQUIRED 항목이 남으면 완료로
표현하지 않고 차단 원인과 남은 항목을 밝힙니다. 별도 완료 보고서 파일을 만들지 않습니다.

## 위험한 작업을 허용하는 법 (승인 grant)

force-push나 hard reset처럼 가드가 막는 작업은 **소유자만** 열 수 있습니다. 에이전트는 나머지 일을
마친 뒤 사용자 응답이 필요한 이유를 한 문장으로 알리고, 실행 명령을 정확히 적은 승인 줄을 마지막에
제공합니다. 승인 챌린지만 단독으로 보내지 않습니다.

```
승인 7F3C: git -C /path/to/repo push --force origin main
```

이 **한 줄만** 그대로 보내면 `UserPromptSubmit` 훅이 그 명령의 SHA-256을
`~/.claude/security/user-approvals.txt`에 1회용으로 적고, 가드가 딱 그 명령을 한 번 통과시킵니다.
Codex가 이 이벤트를 건너뛴 경우에는 PreToolUse 가드가 현재 transcript의 마지막 실제
`user_message` 한 줄만 읽어 같은 검사를 수행합니다. assistant·도구 출력이나 이전 사용자 메시지는 인정하지 않습니다.
실행 직전에 다시 묻지 않습니다 — 재확인은 대화가 아니라 훅의 해시 대조로 끝납니다.

- **에이전트가 원장을 쓰는 경로는 막혀 있습니다.** 원장·챌린지 저장소·`settings.json`에 대한 쓰기는
  리다이렉트·복사·`sed -i`는 물론 `python -c`/`perl -e` 같은 인터프리터 한 줄까지 가드가 거부합니다
  (`settings.json`의 `env`는 모든 훅 자식 프로세스로 전파되므로 같은 등급입니다). 다만 가드는 **정적
  분석**이라, 실행 시점에 조립되는 경로는 원리상 보이지 않습니다 — 그래서 진짜 방어선은 이 목록이
  아니라 "민팅에는 에이전트가 만들어낼 수 없는 실제 프롬프트가 필요하다"는 쪽입니다.
- **ID는 그 세션에서 발급된 것만** 유효하고 1회용이라, 승인 문구가 들어 있는 문서·웹페이지·다른
  모델의 출력을 통째로 붙여넣어도 아무것도 승인되지 않습니다. 60분이 지나면 만료됩니다.
- **명령은 자기 대상을 적어야 합니다.** 해시는 "어떤 명령"만 증명하지 "어디서"는 증명하지 않으므로,
  cwd에 의존하는 `git push …`는 발급 자체가 거부되고 `git -C /절대/경로 …`를 요구합니다.
- **권한이 없으면 멈추지 않습니다.** 나머지를 전부 끝낸 뒤 남은 사용자 작업을 한 문장으로 설명하고,
  복사할 승인 줄을 마지막에 그대로 둡니다. 소유자가 그 줄만 보내면 자동으로 작업을 재개합니다.
- **끝까지 안 열리는 것**: Keychain/인증, Chrome 프로필 직접 수정, 에이전트 세션 상태로의 증명된
  쓰기, 가드 자신. 소유자가 본인 터미널에서 직접 실행해야 합니다.
- 한계는 정직하게: 같은 UID라 암호학적 경계는 없습니다. 목표는 위조 불가가 아니라 **위조가
  시끄럽고 감사 가능해지는 것**입니다. 탐지 근거는 원장 자체입니다 —
  `~/.claude/security/user-approvals.txt`는 append-only 한 줄씩이라 위조 항목이 그대로 보입니다
  (오너 머신의 `config-doctor`가 더하는 `[approval integrity]`는 동봉되지 않습니다).

## 의도적으로 제외한 것

- **시크릿/인증**: 토큰·API 키·`auth.json`·`.credentials`·`.env` 없음(미러가 애초에 복사 안 함).
- **개인 메모리**: `memory/`, `MEMORY.md`, 세션 인텐트, `mistakes/`, `plans/`, `reports/` 없음.
  인텐트 실패 원장(`guides/work/intent-patterns.md`)은 **빈 템플릿**으로 배포됩니다.
- **런타임 상태**: 히스토리·캐시·sqlite·브라우저 상태·감사 원장·다운로드 없음.
- **오너 전용 인프라**: git 원격, 백업/푸시 자동화(→ `macos-harness/personal-examples/`),
  `config-doctor.py`·`hooks-selftest.sh`(오너의 레포·플러그인 레이아웃에 하드와이어된 검증기 —
  다른 머신에선 의미 없고 오너의 비공개 레포 이름이 들어감), Hermes/xAI 프록시, launchagents.
  **브라우저 감사 훅은 동봉됩니다** — 이전 판본에서 제외 목록에 잘못 적혀 있었습니다.
  `browser-audit.py`는 이식 가능한 판으로 다시 쓰였고(osascript·Keychain 미사용) 세션 시작·
  도구 호출 전후에 등록돼 실제로 동작합니다. 브라우저 관련 페이로드에만 반응하고, 남기는 것은
  메타데이터뿐입니다.
- **오너 컨텍스트**: `common/agents/user/`는 **빈 템플릿**만 들어갑니다. 모든 파일에
  `TEMPLATE-UNFILLED` 표시가 있고, 그 줄을 지우기 전까지 어떤 내용도 컨텍스트에 주입되지 않으며,
  재설치해도 채워 넣은 파일은 덮어쓰지 않습니다.
- **플러그인은 전부 실물 동봉**: 공개 플러그인(ponytail, skill-creator, plugin-dev, LSP 3종,
  document-skills)과 **커스텀 cluxion 플러그인 4종**(clx-supercoder, clx-preprocessing,
  clx-ultracode, clx-hermes-call — MIT로 공개)이 `common/claude/plugins-vendored/`
  **로컬 마켓플레이스**에 담겨 네트워크 없이 바로 동작합니다. 제외 원칙은 도구가 아니라
  **개인 상태**(위의 메모리·세션·크리덴셜)입니다. clx-grok-call·clx-autoclearmemory는
  중복 정리로 은퇴(각각 `/grok` CLI 직행·네이티브 메모리로 대체).
  주의: clx-hermes-call은 별도 `hermes-call` CLI가 있어야 실동작합니다(없으면 스킬이 그렇다고 보고).
  공개 플러그인 주기 업데이트는 레포 루트 `./update-vendored.sh` → diff 리뷰 → 수동 커밋.

## 개인화 포인트

- **백업+푸시**: `macos-harness/personal-examples/backup-to-git.sh`를 복사해 `OWNER`와
  `EXPECTED_REMOTE`를 **본인 비공개 레포**로 바꾸세요. 시크릿 스캔은 유지. 폴더 단위 백업은
  `clx-repo-backup` 스킬(`.backup-repo` 마커 = `OWNER/repo` 한 줄) — 마커 없이는 아무것도 푸시 안 함.
- **모델 변경**: 모델 id의 **단일 소스**는 `~/.agents/models.toml`(설치 후 `common/agents/models.toml`)
  입니다. 여기서 바꾸면 되고, `/clx-model`로 레지스트리 검증→각 설정 반영이 자동으로 이뤄집니다.
- **모델 지정 우선**: 대화에서 모델 이름을 직접 말하면 **그 호출에만** 그 모델이 쓰입니다(레지스트리는
  안 바뀝니다). 이름을 안 대면 역할의 핀이 그대로 쓰이고, 더 좋아 보인다고 임의로 올려 쓰지 않습니다.
  역할에 `owner_pinned = true`가 붙어 있으면 "더 상위 모델이 있다"는 경고를 끄되, 존재하지 않는 모델이나
  지원하지 않는 강도는 여전히 FAIL로 잡습니다.
- **모델 자동감지**: 핀은 손으로 적는 값이라 백엔드가 새 모델을 내놓아도 조용히 뒤처집니다.
  `python3 ~/.claude/hooks/model-registry-check.py`가 **설치된** 백엔드에 직접 물어
  (`grok models`, Codex 모델 카탈로그) 존재하지 않는 id·지원하지 않는 effort는 FAIL,
  같은 세대에 더 상위 모델이 있거나 새 세대가 나왔으면 WARN으로 알려줍니다. CLI가 없는 역할은
  건너뜁니다. 설치·업데이트 끝에 자동으로 한 번 돌고, `/clx-model`도 이 결과를 근거로 씁니다.
  **자동으로 바꾸지는 않습니다** — 위임 모델이 말없이 바뀌는 쪽이 더 위험하기 때문입니다.
  개별 핀은 Claude `common/claude/settings.json`의 `"model"`, Codex `common/codex/config.toml`의
  `model` / `model_provider` / `model_reasoning_effort`에도 있습니다.
- **Grok 샌드박스 기본값**: 제한된 데스크톱 실행 환경에서도 한 번 호출로 동작하도록
  `common/grok/config.toml`은 `profile = "off"`를 사용합니다. 이는 Grok CLI 자체의 파일·네트워크
  샌드박스를 끄는 설정입니다. 격리가 필요한 머신에서는 설치 후 `workspace`로 바꾸세요.
- **Claude·Codex 안전 기본값 되돌리기**: 두 실행기는 **보수적** 기본값입니다. 오너처럼 느슨하게 쓰려면(위험 감수 시)
  `config.toml`에 `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`,
  `settings.json`에 `"skipDangerousModePermissionPrompt": true`를 추가하세요.

## 주의

- **Astryx(`clx-astryx`)는 베타** 성격의 신규 디자인-시스템 스킬입니다. design-workflow 규칙이
  발동할 때(기존 시스템 없는 새 React)나 명시적 요청에만 쓰세요.
- Windows에서는 bash 훅이 동작하지 않습니다(위 참고). 그 외 설정은 정상 동작합니다.

## 하네스 라이브러리 (100종)

`common/agents/harness-library/`에 [revfactory/harness-100](https://github.com/revfactory/harness-100)의
팀 하네스 100종(ko, Apache-2.0)이 통째로 들어있습니다. 설치 후 `/harness list [키워드]`로 찾고
`/harness use <번호>`로 **현재 프로젝트에만** 설치됩니다(전역 상시 로드 없음, 원본 무수정).

## 선택 확장 (미동봉 — 외부 CLI, 원하면 설치)

- **Graphify** (`uv tool install graphifyy`): 코드베이스를 지식 그래프로 — `graphify . --code-only`는
  API 키 없이 로컬 AST만으로 동작(문서 의미 추출은 키 필요). Windows 지원(PowerShell에선 `graphify .`).
- **Headroom** (`uv tool install --python 3.13 "headroom-ai[all]"`): 컨텍스트 압축 프록시.
  **기본 wrap은 권장하지 않음** — 필요할 때만 `headroom wrap claude`로 옵트인 기동. Windows 휠 지원.

설계 기준은 [PRINCIPLES.md](PRINCIPLES.md) 참고.

## 라이선스 · 기여

- **MIT** ([LICENSE](LICENSE), © 2026 algocean1204). 단, 벤더링된 외부 자산(예: 일부 스킬의
  `assets/p5.js`)은 **원 라이선스**를 그대로 따릅니다.
- PR·Issue 환영 — 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md) 참고. 핵심: 작게, 개인정보 0,
  설치기 드라이런(`--check`/`-Check`) 통과.

## 새니타이즈 보증

오너의 홈 경로·사용자명·이메일·GitHub 계정·각종 토큰/개인키가 파일 내용에 **0건**입니다. 신원 토큰은
언제든 재확인 가능하고, 크리덴셜은 본인 스캐너(예: `gitleaks detect`)를 돌리세요:

```bash
grep -rIE '/Users/[A-Za-z]+|@gmail\.com' common --exclude-dir=plugins-vendored | grep -v p5.js   # 매치 없어야 정상 (벤더 원문·p5.js 표기는 검사 대상 아님)
```

---

일부 구성은 오픈소스 프로젝트를 참조·벤더링했습니다 — 링크 목록: [credits/](credits/README.md)
