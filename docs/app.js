/* clx-harness-full-package — static site. Vanilla JS, no build step. */
(() => {
'use strict';

/* ------------------------------------------------------------------ icons */
/* lucide (ISC) 24px stroke icons, inlined — the page makes no network requests. */
const ICONS = {
  languages: '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>',
  boxes: '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  library: '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/>',
  lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  package: '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  terminal: '<path d="m4 17 6-6-6-6"/><path d="M12 19h8"/>',
  archive: '<rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  laptop: '<path d="M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0 1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45L4 16"/>',
  monitor: '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
  github: '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>',
  'pull-request': '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M6 9v12"/>',
  scale: '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  ellipsis: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  palette: '<circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.506 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
  sliders: '<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>',
  branch: '<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
  plug: '<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>'
};

function icon(name) {
  const d = ICONS[name];
  if (!d) return '';
  return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + d + '</svg>';
}

/* --------------------------------------------------------------- i18n dict */
const I18N = {
  ko: {
    skip: '본문으로 건너뛰기',
    brandSub: 'full-package',
    heroEyebrow: '오픈소스 멀티 CLI 에이전트 하네스',
    heroTitle: 'AI 에이전트 셋, 규칙은 하나.',
    heroLede: 'Claude Code · Codex · Grok Build를 한 규칙으로 굴리려는 개발자를 위한 클린 배포판. 클론하고 설치하면 끝 — 개인정보 0, 외부 위임은 언제나 옵트인.',
    heroCta1: '생태계 살펴보기',
    heroCta2: '바로 설치하기',
    heroBadge1: 'MIT 라이선스',
    heroBadge2: 'PR · Issue 환영',
    heroBadge3: 'macOS · Windows 1급 지원',
    docTitle: 'clx 에이전트 하네스 — AI 에이전트 셋, 규칙은 하나',
    docDesc: 'Claude Code · Codex · Grok Build를 단일 코어 규칙으로 묶는 오픈소스 멀티 CLI 에이전트 하네스 클린 배포판. 개인정보 0, macOS·Windows 1급 지원.',
    navEco: '생태계', navTree: '구조', navCat: '카탈로그', navIns: '설치',
    navAria: '섹션', filterAria: '카테고리 필터',
    copyBtn: '복사', copyDone: '복사됨',
    catClear: '필터 초기화', whyLabel: '의도', benefitLabel: '장점',
    fact1: 'CLI 하네스',
    fact2: '코어 규칙',
    fact3: '스킬 28 · 플러그인 4',
    fact4: '시크릿 · 개인정보',

    ecoKicker: '01 — 생태계',
    ecoTitle: '저장소 3개 + 내 머신',
    ecoFlowSr: '흐름: 비공개 스킬 원본 저장소의 스킬이 clx-harness-full-package 배포판에 벤더링되고, 설치기가 이를 로컬 설정으로 펼친 뒤, 로컬 설정이 개인 백업 저장소로 미러링됩니다.',
    badgePublic: '공개',
    badgePrivate: '비공개',
    badgeLocal: '로컬',
    nodeSkillbookName: '비공개 스킬 원본 저장소',
    nodeSkillbook: '커스텀 스킬·플러그인 모노레포. 배포판에 실리는 스킬의 원본입니다.',
    nodeSkillbookMeta: '스킬 28 · 플러그인 4',
    nodeHermess: '이 저장소 — 개인정보를 걷어낸 클린 배포판. 새 머신에 복제하면 같은 하네스가 재현됩니다.',
    nodeHermessMeta: 'MIT · PR 환영',
    nodeLive: '설치기가 만드는 실사용 설정. 에이전트가 실제로 읽는 자리입니다.',
    nodeLiveMeta: 'install.sh · install.ps1',
    nodeBackupName: '비공개 설정 백업 저장소',
    nodeBackup: '개인 백업. 내부 구조는 공개하지 않습니다.',
    nodeBackupMeta: '구조 비공개',
    connVendor: '벤더링',
    connInstall: '설치',
    connMirror: '미러',
    ecoNote: '배포판에는 시크릿·개인 메모리·세션·런타임 상태가 들어있지 않습니다. git 원격도 설정하지 않고, 어디에도 자동으로 푸시하지 않습니다.',

    treeKicker: '02 — 구조',
    treeTitle: '저장소 구조 탐색기',
    treeLede: '공개 배포판의 실제 트리입니다. 폴더를 눌러 펼쳐 보세요. 스킬 내부 자산처럼 반복되는 잎은 한 줄로 묶었습니다.',
    treeExpand: '모두 펼치기',
    treeCollapse: '모두 접기',

    catKicker: '03 — 카탈로그',
    catTitle: '스킬 · 플러그인 카탈로그',
    catLede: '비공개 스킬 원본 저장소가 출처입니다. 스킬과 cluxion 플러그인 모두 배포판에 실물로 실려 있습니다.',
    catSearchLabel: '스킬 검색',
    catSearchPlaceholder: '이름이나 기능으로 검색…',
    catEmpty: '조건에 맞는 항목이 없습니다.',
    catAll: '전체',
    catDesign: '디자인',
    catMeta: '메타 · 설정',
    catProcess: '프로세스',
    catReport: '보고 · 문체',
    catPlugin: '플러그인',
    catCount: '{n}개 표시 중',

    insKicker: '04 — 설치',
    insTitle: '설치 흐름',
    insLede: '클론은 공통, 활성화는 OS별로 자동 분기됩니다. 두 설치기 모두 드라이런이 먼저입니다.',
    insNote: '두 설치기 모두 인증·크리덴셜·Keychain을 건드리지 않고, git 원격을 설정하지 않습니다.',

    ctaTitle: '같이 다듬어 주세요',
    ctaBody: 'MIT 라이선스입니다. 새 머신에 복제해 쓰고, 고칠 곳이 보이면 PR이나 이슈로 알려주세요.',
    ctaRepo: '저장소 열기',
    ctaIssues: '이슈 · PR',
    ctaLicense: 'MIT License',
    footerNote: '개인 백업 저장소의 내부 구조는 의도적으로 공개하지 않습니다.'
  },
  en: {
    skip: 'Skip to content',
    brandSub: 'full-package',
    heroEyebrow: 'Open-source multi-CLI agent harness',
    heroTitle: 'Three AI agents. One rulebook.',
    heroLede: 'A clean distro for developers who run Claude Code, Codex and Grok Build on one rulebook. Clone, install, done — zero personal data, outward delegation strictly opt-in.',
    heroCta1: 'See the ecosystem',
    heroCta2: 'Install now',
    heroBadge1: 'MIT licensed',
    heroBadge2: 'PRs & issues welcome',
    heroBadge3: 'First-class macOS · Windows',
    docTitle: 'clx agent harness — Three AI agents. One rulebook.',
    docDesc: 'Open-source clean distro of a multi-CLI agent harness for Claude Code, Codex and Grok Build. Zero personal data, first-class macOS & Windows.',
    navEco: 'Ecosystem', navTree: 'Structure', navCat: 'Catalog', navIns: 'Install',
    navAria: 'Sections', filterAria: 'Category filter',
    copyBtn: 'Copy', copyDone: 'Copied',
    catClear: 'Clear filters', whyLabel: 'Intent', benefitLabel: 'Benefit',
    fact1: 'CLI harnesses',
    fact2: 'core rules',
    fact3: '28 skills · 4 plugins',
    fact4: 'secrets · personal data',

    ecoKicker: '01 — Ecosystem',
    ecoTitle: 'Three repos + your machine',
    ecoFlowSr: 'Flow: skills from a private source repo are vendored into the clx-harness-full-package distro, the installer unfolds that into the local config, and the local config is mirrored to a personal backup repo.',
    badgePublic: 'Public',
    badgePrivate: 'Private',
    badgeLocal: 'Local',
    nodeSkillbookName: 'Private skills source repo',
    nodeSkillbook: 'Monorepo of custom skills and plugins — the source the distro vendors its skills from.',
    nodeSkillbookMeta: '28 skills · 4 plugins',
    nodeHermess: 'This repo — the clean distro, personal traces stripped. Clone it on a new machine and the same harness comes back.',
    nodeHermessMeta: 'MIT · PRs welcome',
    nodeLive: 'The live config the installer writes. This is what the agents actually read.',
    nodeLiveMeta: 'install.sh · install.ps1',
    nodeBackupName: 'Private config backup repo',
    nodeBackup: 'Personal backup. Its internals stay private.',
    nodeBackupMeta: 'structure withheld',
    connVendor: 'vendored',
    connInstall: 'install',
    connMirror: 'mirror',
    ecoNote: 'The distro ships no secrets, no personal memory, no sessions, no runtime state. It configures no git remote and never pushes anywhere on its own.',

    treeKicker: '02 — Structure',
    treeTitle: 'Repo structure explorer',
    treeLede: 'The real tree of the public distro. Click a folder to open it. Repetitive leaves, such as a skill’s internal assets, are folded into one line.',
    treeExpand: 'Expand all',
    treeCollapse: 'Collapse all',

    catKicker: '03 — Catalog',
    catTitle: 'Skill & plugin catalog',
    catLede: 'Sourced from a private skills repo. Both the skills and the cluxion plugins ship in the public distro.',
    catSearchLabel: 'Search skills',
    catSearchPlaceholder: 'Search by name or what it does…',
    catEmpty: 'Nothing matches those filters.',
    catAll: 'All',
    catDesign: 'Design',
    catMeta: 'Meta · config',
    catProcess: 'Process',
    catReport: 'Reporting',
    catPlugin: 'Plugins',
    catCount: 'Showing {n}',

    insKicker: '04 — Install',
    insTitle: 'Install flow',
    insLede: 'The clone is shared; activation branches per OS. Both installers start with a dry run.',
    insNote: 'Neither installer touches auth, credentials or the Keychain, and neither configures a git remote.',

    ctaTitle: 'Help shape it',
    ctaBody: 'MIT licensed. Clone it onto your own machine, and if you spot something to fix, open a PR or an issue.',
    ctaRepo: 'Open the repo',
    ctaIssues: 'Issues · PRs',
    ctaLicense: 'MIT License',
    footerNote: 'The internals of the personal backup repo are deliberately left unpublished.'
  },
  zh: {
    skip: '跳到正文',
    brandSub: 'full-package',
    heroEyebrow: '开源多 CLI 智能体框架',
    heroTitle: '三个 AI 智能体，一套规则。',
    heroLede: 'Claude Code、Codex 与 Grok Build 由同一份核心配置驱动。克隆、安装即可 —— 零个人数据，向外委派始终显式选择。',
    heroCta1: '查看生态',
    heroCta2: '立即安装',
    heroBadge1: 'MIT 许可证',
    heroBadge2: '欢迎 PR 与 Issue',
    heroBadge3: 'macOS · Windows 一级支持',
    docTitle: 'clx 智能体框架 —— 三个 AI 智能体，一套规则',
    docDesc: '面向 Claude Code、Codex 与 Grok Build 的开源多 CLI 智能体框架干净发行版。零个人数据，macOS 与 Windows 一级支持。',
    navEco: '生态', navTree: '结构', navCat: '目录', navIns: '安装',
    navAria: '章节', filterAria: '类别筛选',
    copyBtn: '复制', copyDone: '已复制',
    catClear: '清除筛选', whyLabel: '意图', benefitLabel: '优势',
    fact1: 'CLI 框架',
    fact2: '核心规则',
    fact3: '技能 28 · 插件 4',
    fact4: '密钥 · 个人数据',

    ecoKicker: '01 — 生态',
    ecoTitle: '三个仓库 + 本地机器',
    ecoFlowSr: '流向：私有技能源仓库中的技能被引入 clx-harness-full-package 发行版，安装器把它展开为本地配置，本地配置再镜像到个人备份仓库。',
    badgePublic: '公开',
    badgePrivate: '私有',
    badgeLocal: '本地',
    nodeSkillbookName: '私有技能源仓库',
    nodeSkillbook: '自定义技能与插件的单体仓库，是发行版所用技能的源头。',
    nodeSkillbookMeta: '技能 28 · 插件 4',
    nodeHermess: '就是本仓库 —— 剔除个人信息的干净发行版。在新机器上克隆即可复现同一套框架。',
    nodeHermessMeta: 'MIT · 欢迎 PR',
    nodeLive: '安装器写出的实际配置，智能体真正读取的就是这里。',
    nodeLiveMeta: 'install.sh · install.ps1',
    nodeBackupName: '私有配置备份仓库',
    nodeBackup: '个人备份，内部结构不对外公开。',
    nodeBackupMeta: '结构不公开',
    connVendor: '内置',
    connInstall: '安装',
    connMirror: '镜像',
    ecoNote: '发行版不含任何密钥、个人记忆、会话或运行时状态；它不配置 git 远程，也绝不自行推送。',

    treeKicker: '02 — 结构',
    treeTitle: '仓库结构浏览器',
    treeLede: '这是公开发行版的真实目录树，点击文件夹即可展开。技能内部资源等重复末端已折叠为一行。',
    treeExpand: '全部展开',
    treeCollapse: '全部折叠',

    catKicker: '03 — 目录',
    catTitle: '技能与插件目录',
    catLede: '内容来自私有技能源仓库。技能与 cluxion 插件均已随公开发行版一同提供。',
    catSearchLabel: '搜索技能',
    catSearchPlaceholder: '按名称或功能搜索…',
    catEmpty: '没有符合条件的条目。',
    catAll: '全部',
    catDesign: '设计',
    catMeta: '元配置',
    catProcess: '流程',
    catReport: '汇报文风',
    catPlugin: '插件',
    catCount: '显示 {n} 项',

    insKicker: '04 — 安装',
    insTitle: '安装流程',
    insLede: '克隆是共用的，激活按操作系统自动分流。两个安装器都先跑一次空跑检查。',
    insNote: '两个安装器都不触碰认证信息、凭据和钥匙串，也不配置任何 git 远程。',

    ctaTitle: '欢迎一起打磨',
    ctaBody: '采用 MIT 许可。欢迎克隆到自己的机器上使用；发现可以改进的地方，提个 PR 或 issue 就好。',
    ctaRepo: '打开仓库',
    ctaIssues: 'Issue · PR',
    ctaLicense: 'MIT License',
    footerNote: '个人备份仓库的内部结构有意不予公开。'
  }
};

/* ---------------------------------------------------------------- tree data
   Derived from `git ls-files` (2,876 tracked files) plus README.md,
   windows-harness/README.md, install.sh and macos-harness/manifest.md.        */
const t = (ko, en, zh) => ({ ko, en, zh });

const TREE = [{
  name: 'clx-harness-full-package', kind: 'dir', count: '2,904', open: true,
  note: t('공개 클린 배포판의 저장소 루트',
          'Repository root of the public clean distro',
          '公开干净发行版的仓库根目录'),
  children: [
    { name: 'README.md', kind: 'file',
      note: t('배포판 개요, OS별 활성화, 의도적으로 제외한 것, 개인화 포인트',
              'Overview, per-OS activation, what was deliberately excluded, personalization points',
              '总览、按系统激活、刻意排除的内容与个性化要点') },
    { name: 'install.sh', kind: 'file',
      note: t('macOS/Linux 설치기 — --check / --apply / --force / --with-launchd',
              'macOS/Linux installer — --check / --apply / --force / --with-launchd',
              'macOS/Linux 安装器 —— --check / --apply / --force / --with-launchd') },
    { name: '.gitignore', kind: 'file',
      note: t('로컬 산출물 제외 규칙', 'Keeps local build noise out of the tree', '排除本地产物的规则') },
    { name: 'LICENSE · CONTRIBUTING.md · PRINCIPLES.md', kind: 'group',
      note: t('MIT 라이선스, 기여 규칙, 설계 원칙 공개 요약본',
              'MIT license, contribution rules, and the public design-principles summary',
              'MIT 许可证、贡献规则与设计原则公开摘要') },
    { name: 'update-vendored.sh', kind: 'file',
      note: t('벤더 자산(플러그인·하네스 100종) 주기 갱신 스크립트 — diff 리뷰 후 수동 커밋',
              'Periodic refresh for vendored assets (plugins + 100 harnesses) — review the diff, commit manually',
              '内置资产（插件与 100 套哈尼斯）的定期更新脚本 —— 审阅 diff 后手动提交') },
    { name: 'credits/', kind: 'dir', count: '1',
      note: t('참조·벤더링한 오픈소스 링크 모음', 'Links to every referenced or vendored upstream', '所引用与内置的开源项目链接') },
    { name: 'setup-ui/', kind: 'dir', count: '2',
      note: t('설치 상태를 보고 모델을 클릭 한 번으로 바꾸는 로컬 페이지 — 한/영·라이트/다크, 표준 라이브러리만, 토큰·Host 검증, models.toml 외에는 쓰지 않음',
              'Local page that shows your install state and switches models in one click — ko/en, light/dark, stdlib only, token + Host checks, writes nothing but models.toml',
              '查看安装状态并一键切换模型的本地页面 —— 中/英界面、明暗主题、仅标准库、令牌与 Host 校验，除 models.toml 外不写入任何文件') },
    {
      name: 'common/', kind: 'dir', count: '2,880',
      note: t('플랫폼 공통 페이로드. 설치 시 __CLX_HOME__ 토큰이 실제 $HOME으로 치환됩니다.',
              'Cross-platform payload. At install time the __CLX_HOME__ token is materialized to your real $HOME.',
              '跨平台配置载荷。安装时会把 __CLX_HOME__ 占位符替换成真实的 $HOME。'),
      children: [
        {
          name: 'agents/', kind: 'dir', count: '920',
          note: t('~/.agents 로 설치 — 두 플랫폼이 공유하는 단일 코어 + 하네스 라이브러리',
                  'Installs to ~/.agents — the single core both platforms share, plus the harness library',
                  '安装到 ~/.agents —— 两个平台共用的唯一核心与哈尼斯库'),
          children: [
            { name: 'AGENTS.md', kind: 'file',
              note: t('12개 상시 규칙의 단일 정본. Claude는 import, Codex는 임베드합니다.',
                      'The single source of truth for the 12 always-on rules. Claude imports it; Codex embeds it.',
                      '12 条常驻规则的唯一正本：Claude 通过 import 引用，Codex 直接内嵌。') },
            { name: 'models.toml', kind: 'file',
              note: t('모델 id·추론 강도의 단일 소스. 다른 곳에 모델명을 하드코딩하지 않습니다.',
                      'Single source for model ids and reasoning effort — no model name is hardcoded anywhere else.',
                      '模型 id 与推理强度的唯一来源，其他任何地方都不硬编码模型名。') },
            { name: 'harness-library/', kind: 'dir', count: '909',
              note: t('revfactory/harness-100 ko 100종 실물(프리스틴, 커밋 핀). /harness list·use로 프로젝트에 온디맨드 설치',
                      'All 100 upstream team harnesses, pristine and commit-pinned. Installed per-project on demand via /harness list·use',
                      '上游 100 套团队哈尼斯完整内置（原样、锁定提交）。经 /harness list·use 按需装入项目') },
            { name: 'user/', kind: 'dir', count: '9',
              note: t('당신의 컨텍스트가 들어갈 빈 템플릿 — 모든 파일에 TEMPLATE-UNFILLED 표시. 채우기 전엔 아무것도 주입되지 않고, 재설치해도 덮어쓰지 않습니다',
                      'Empty skeleton for YOUR context — every file marked TEMPLATE-UNFILLED. Nothing is injected until you fill it in, and a re-install never overwrites it',
                      '留给你自己上下文的空骨架 —— 每个文件都标有 TEMPLATE-UNFILLED。填写之前不会注入任何内容，重装也不会覆盖') }
          ]
        },
        {
          name: 'claude/', kind: 'dir', count: '1,453',
          note: t('~/.claude 로 설치되는 Claude Code 페이로드',
                  'The Claude Code payload, installed to ~/.claude',
                  '安装到 ~/.claude 的 Claude Code 载荷'),
          children: [
            { name: 'CLAUDE.md', kind: 'file',
              note: t('코어를 @import하고 Claude 전용 델타와 라우터 표만 추가',
                      'Imports the shared core, then adds only Claude-specific deltas and router tables',
                      '@import 共享核心，再补充 Claude 专属差异与路由表') },
            { name: 'settings.json', kind: 'file',
              note: t('훅 등록, statusLine, 권한, 모델 핀',
                      'Hook registration, statusLine, permissions, model pin',
                      '钩子注册、statusLine、权限与模型固定') },
            { name: 'figma-mcp.json', kind: 'file',
              note: t('ClaudeTalkToFigma MCP 서버 정의 (stdio)',
                      'ClaudeTalkToFigma MCP server definition (stdio)',
                      'ClaudeTalkToFigma MCP 服务器定义（stdio）') },
            {
              name: 'agents/', kind: 'dir', count: '3',
              note: t('읽기 전용 리뷰 서브에이전트 — 파일을 수정하지 않고 결과만 돌려줍니다.',
                      'Read-only review subagents — they report findings and never edit files.',
                      '只读评审子智能体：只返回结论，从不改动文件。'),
              children: [
                { name: 'a11y-motion-auditor.md', kind: 'file',
                  note: t('WCAG AA 대비, 포커스, 키보드, 축소 모션 감사',
                          'WCAG AA contrast, focus, keyboard and reduced-motion audit',
                          '审计 WCAG AA 对比度、焦点、键盘与减弱动效') },
                { name: 'ui-visual-inspector.md', kind: 'file',
                  note: t('겹침·잘림·가로 넘침·브레이크포인트 결함 점검',
                          'Overlap, clipping, horizontal overflow and breakpoint defects',
                          '检查重叠、裁切、横向溢出与断点问题') },
                { name: 'ux-friction-reviewer.md', kind: 'file',
                  note: t('흐름의 마찰 — 불필요한 단계, 모호한 상태, 인지 부하',
                          'Friction in flows — extra steps, unclear states, cognitive load',
                          '流程摩擦：多余步骤、状态不清与认知负担') }
              ]
            },
            {
              name: 'commands/', kind: 'dir', count: '8',
              note: t('슬래시 커맨드', 'Slash commands', '斜杠命令'),
              children: [
                { name: 'grok.md', kind: 'file',
                  note: t('/grok — 등급 게이트를 통과한 한 건의 Grok Build 위임',
                          '/grok — one bounded delegation to Grok Build, after the grade gate',
                          '/grok —— 通过等级判定后向 Grok Build 委派一次') },
                { name: 'gpt.md', kind: 'file',
                  note: t('/gpt — 같은 게이트를 거친 Codex 위임',
                          '/gpt — the same gate, delegating to Codex',
                          '/gpt —— 同样的判定，委派给 Codex') },
                { name: 'clx-model.md', kind: 'file',
                  note: t('/clx-model — models.toml 검증 → 반영 → 재검증',
                          '/clx-model — validate models.toml, propagate, verify again',
                          '/clx-model —— 校验 models.toml、下发、再次验证') },
                { name: 'backup.md', kind: 'file',
                  note: t('/backup — .backup-repo 마커 기반 폴더 백업',
                          '/backup — folder backup driven by the .backup-repo marker',
                          '/backup —— 基于 .backup-repo 标记的文件夹备份') },
                { name: 'harness.md', kind: 'file',
                  note: t('/harness — 프로젝트용 에이전트 팀 구성',
                          '/harness — build an agent team for a project',
                          '/harness —— 为项目组建智能体团队') },
                { name: 'clx-help.md', kind: 'file',
                  note: t('/clx-help — 전체 슬래시 커맨드 한 줄 요약',
                          '/clx-help — one-line summary of every slash command',
                          '/clx-help —— 所有斜杠命令的一行摘要') }
              ]
            },
            {
              name: 'guides/', kind: 'dir', count: '14',
              note: t('라우터 트리거가 걸릴 때만 읽는 온디맨드 가이드',
                      'On-demand guides, read only when a router trigger fires',
                      '按需加载的指南，只有触发路由时才读取'),
              children: [
                { name: 'README.md', kind: 'file',
                  note: t('가이드 인덱스', 'Guide index', '指南索引') },
                { name: 'meta/', kind: 'dir', count: '3',
                  note: t('claude-layout · meta-governance · backup — 설정 자체를 다룰 때',
                          'claude-layout · meta-governance · backup — for working on the config itself',
                          'claude-layout · meta-governance · backup —— 处理配置本身时使用') },
                { name: 'work/', kind: 'dir', count: '10',
                  note: t('intent · work-modes · subagents · models · git · goals · browser-state · cluxion · ensemble-consensus · intent-patterns',
                          'intent · work-modes · subagents · models · git · goals · browser-state · cluxion · ensemble-consensus · intent-patterns',
                          'intent · work-modes · subagents · models · git · goals · browser-state · cluxion · ensemble-consensus · intent-patterns') }
              ]
            },
            {
              name: 'hooks/', kind: 'dir', count: '28',
              note: t('세션 수명주기 훅. 설치기가 실행 권한을 붙여줍니다.',
                      'Session lifecycle hooks; the installer sets the executable bit for you.',
                      '会话生命周期钩子，安装器会自动加上可执行权限。'),
              children: [
                { name: 'intent-lock.py', kind: 'file',
                  note: t('UserPromptSubmit — 세션 의도와 완료 조건을 주입',
                          'UserPromptSubmit — injects the session intent and its definition of done',
                          'UserPromptSubmit —— 注入会话意图与完成条件') },
                { name: 'guard-destructive.py', kind: 'file',
                  note: t('PreToolUse — 파괴적 명령을 승인 원장 없이는 막습니다.',
                          'PreToolUse — blocks destructive commands without an approval-ledger entry',
                          'PreToolUse —— 没有审批记录就拦截破坏性命令') },
                { name: 'block-goal-tools.py', kind: 'file',
                  note: t('PreToolUse — 계획만 하고 끝나는 턴을 차단',
                          'PreToolUse — blocks plan-only turns',
                          'PreToolUse —— 拦截只做计划、不动手的回合') },
                { name: 'auto-format.sh', kind: 'file',
                  note: t('PostToolUse — 편집 직후 포매터 실행',
                          'PostToolUse — runs the formatter right after an edit',
                          'PostToolUse —— 编辑后立即执行格式化') },
                { name: 'statusline.sh', kind: 'file',
                  note: t('statusLine — 상태 표시줄 렌더링',
                          'statusLine — renders the status bar',
                          'statusLine —— 渲染状态栏') },
                { name: 'precompact-guard.sh', kind: 'file',
                  note: t('PreCompact — 압축 전 보존 규칙',
                          'PreCompact — what must survive a compaction',
                          'PreCompact —— 压缩前的保留规则') },
                { name: 'session-intent-archive.sh', kind: 'file',
                  note: t('SessionEnd — 세션 의도 아카이브',
                          'SessionEnd — archives the session intent',
                          'SessionEnd —— 归档会话意图') },
                { kind: 'group', name: '…', count: '20 more',
                  note: t('backup-config · browser-audit(3) · cache-slim · clx-bounded-run · clx-first-run · clx-grok-runtime · clx-resource-lock · clx_grant · clx_host · disk-guard · forgetforge-sync · home-tokenize · model-registry-check · report-prune · restore-*(2) · selfcheck-stop · session-restore · session_intent_paths · standing_blocks',
                          'backup-config · browser-audit(3) · cache-slim · clx-bounded-run · clx-first-run · clx-grok-runtime · clx-resource-lock · clx_grant · clx_host · disk-guard · forgetforge-sync · home-tokenize · model-registry-check · report-prune · restore-*(2) · selfcheck-stop · session-restore · session_intent_paths · standing_blocks',
                          'backup-config · browser-audit(3) · cache-slim · clx-bounded-run · clx-first-run · clx-grok-runtime · clx-resource-lock · clx_grant · clx_host · disk-guard · forgetforge-sync · home-tokenize · model-registry-check · report-prune · restore-*(2) · selfcheck-stop · session-restore · session_intent_paths · standing_blocks') }
              ]
            },
            {
              name: 'rules/', kind: 'dir', count: '3',
              note: t('경로 스코프 자동 로드 규칙 — 라우터 없이 항상 적용',
                      'Path-scoped rules that auto-load, no router trigger needed',
                      '按路径自动加载的规则，无需路由触发'),
              children: [
                { name: 'engineering.md', kind: 'file',
                  note: t('근본 원인 우선, 최소 diff, 검증 후 단언, 컨텍스트 예산',
                          'Root cause first, minimal diff, verify before asserting, context budget',
                          '先找根因、最小改动、先验证后断言、控制上下文预算') },
                { name: 'design/', kind: 'dir', count: '2',
                  note: t('design-core · design-workflow — 디자인 스킬 라우팅 격자',
                          'design-core · design-workflow — the design skill routing lattice',
                          'design-core · design-workflow —— 设计技能的路由网格') }
              ]
            },
            {
              name: 'skills/', kind: 'dir', count: '42',
              note: t('커스텀 clx-* 스킬 27개 + 벤더링·업스트림 스킬 15개',
                      '27 custom clx-* skills plus 15 vendored and upstream skills',
                      '27 个自定义 clx-* 技能，外加 15 个引入与上游技能'),
              children: [
                { name: 'clx-apple-design/', kind: 'dir',
                  note: t('SKILL.md + references (principles.md) + agents',
                          'SKILL.md + references (principles.md) + agents',
                          'SKILL.md + references（principles.md）+ agents') },
                { name: 'clx-algorithmic-art/', kind: 'dir',
                  note: t('SKILL.md + references + agents + assets (p5.js 번들)',
                          'SKILL.md + references + agents + assets (bundled p5.js)',
                          'SKILL.md + references + agents + assets（内置 p5.js）') },
                { name: 'clx-frontend-design/', kind: 'dir',
                  note: t('SKILL.md + references/ui-ux-pro-max (data, scripts)',
                          'SKILL.md + references/ui-ux-pro-max (data, scripts)',
                          'SKILL.md + references/ui-ux-pro-max（data、scripts）') },
                { name: 'impeccable/', kind: 'dir',
                  note: t('SKILL.md + reference + scripts/detector (engines, rules, browser)',
                          'SKILL.md + reference + scripts/detector (engines, rules, browser)',
                          'SKILL.md + reference + scripts/detector（engines、rules、browser）') },
                { name: 'docx · pptx · xlsx · pdf', kind: 'group',
                  note: t('오피스·PDF 저작 스킬. scripts/office/schemas가 파일 수의 대부분입니다.',
                          'Office and PDF authoring skills — scripts/office/schemas accounts for most of the file count.',
                          '办公与 PDF 编写技能，scripts/office/schemas 占了文件数的大头。') },
                { kind: 'group', name: '…', count: '31 more',
                  note: t('나머지 스킬은 아래 카탈로그에서 검색·필터로 확인하세요.',
                          'Browse the rest in the searchable catalog below.',
                          '其余技能可在下方目录中搜索筛选。') }
              ]
            },
            { name: 'plugins-vendored/', kind: 'dir', count: '938',
              note: t('로컬 마켓플레이스 clx-vendored — 플러그인 11종 실물(ponytail·skill-creator·plugin-dev·LSP 3종·오피스 4종·cluxion 4종). 네트워크 없이 동작',
                      'Local marketplace clx-vendored — all 11 plugins shipped verbatim (ponytail, skill-creator, plugin-dev, 3 LSPs, 4 office, 4 cluxion). Works offline',
                      '本地市场 clx-vendored —— 11 个插件完整内置（ponytail、skill-creator、plugin-dev、3 个 LSP、4 个办公、4 个 cluxion），离线可用') }
          ]
        },
        {
          name: 'codex/', kind: 'dir', count: '506',
          note: t('~/.codex 로 설치되는 Codex 페이로드',
                  'The Codex payload, installed to ~/.codex',
                  '安装到 ~/.codex 的 Codex 载荷'),
          children: [
            { name: 'AGENTS.md', kind: 'file',
              note: t('동일한 코어 섹션을 임베드한 Codex 라우터. 드리프트는 config-doctor가 잡습니다.',
                      'Codex router embedding the identical core section; drift is caught by config-doctor.',
                      '内嵌同一核心章节的 Codex 路由文件，偏移由 config-doctor 检查。') },
            { name: 'config.toml', kind: 'file',
              note: t('모델·프로바이더·승인 정책·샌드박스의 안전 부분집합',
                      'A conservative subset: model, provider, approval policy, sandbox',
                      '模型、提供方、审批策略与沙箱的保守子集') },
            { name: 'hooks.json', kind: 'file',
              note: t('Codex 훅 레지스트리', 'Codex hook registry', 'Codex 钩子注册表') },
            { name: 'guides/', kind: 'dir', count: '13',
              note: t('meta 3개 + work 9개 — Claude 쪽과 같은 축, codex-layout으로 교체',
                      '3 meta + 9 work — the same axes as the Claude side, with codex-layout swapped in',
                      'meta 3 个 + work 9 个：与 Claude 侧同构，仅换成 codex-layout') },
            { name: 'hooks/', kind: 'dir', count: '3',
              note: t('backup-config.sh · session-intent.py · sync-grok-model-config.py',
                      'backup-config.sh · session-intent.py · sync-grok-model-config.py',
                      'backup-config.sh · session-intent.py · sync-grok-model-config.py') },
            { name: 'prompts/', kind: 'dir', count: '4',
              note: t('gpt · grok · supercoder · ultracode 커스텀 프롬프트',
                      'Custom prompts: gpt · grok · supercoder · ultracode',
                      '自定义提示词：gpt · grok · supercoder · ultracode') },
            { name: 'rules/', kind: 'dir', count: '3',
              note: t('engineering + design/{core,workflow} — Claude와 같은 규칙',
                      'engineering + design/{core,workflow} — the same rules Claude gets',
                      'engineering + design/{core,workflow}，与 Claude 侧一致') },
            { name: 'skills/', kind: 'dir', count: '14 + .system 5',
              note: t('Codex는 실행 표면이라 코딩·프로세스 스킬만 활성화합니다. .system/에는 imagegen, openai-docs, plugin-creator, skill-creator, skill-installer.',
                      'Codex is the execution surface, so only coding and process skills stay active. .system/ holds imagegen, openai-docs, plugin-creator, skill-creator, skill-installer.',
                      'Codex 是执行面，只保留编码与流程类技能。.system/ 内含 imagegen、openai-docs、plugin-creator、skill-creator、skill-installer。') },
            { name: 'skills-disabled/', kind: 'dir', count: '18',
              note: t('디스크에는 남기되 Codex가 스캔하지 않는 자리. 스킬 설명이 컨텍스트 예산을 먹는 것을 막습니다.',
                      'Kept on disk but never scanned by Codex — this is what keeps skill descriptions from eating the context budget.',
                      '保留在磁盘上但 Codex 不扫描，避免技能描述占用上下文预算。') }
          ]
        },
        {
          name: 'grok/', kind: 'dir', count: '1',
          note: t('~/.grok 로 설치되는 Grok CLI 실행 기본값. 기존 설정의 다른 키는 보존합니다.',
                  'The Grok CLI runtime baseline installed to ~/.grok; other existing settings are preserved.',
                  '安装到 ~/.grok 的 Grok CLI 运行基线；保留其他既有设置。'),
          children: [
            { name: 'config.toml', kind: 'file',
              note: t('제한된 데스크톱 실행 환경 호환을 위해 sandbox profile을 off로 설정',
                      'Sets the sandbox profile to off for compatibility with restricted desktop runners',
                      '为兼容受限桌面运行环境，将 sandbox profile 设为 off') }
          ]
        }
      ]
    },
    {
      name: 'macos-harness/', kind: 'dir', count: '6',
      note: t('macOS 전용 조각. 기본 설치 대상이 아니며 옵트인해야 동작합니다.',
              'macOS-only pieces. Not installed by default — each one is opt-in.',
              '仅限 macOS 的部分，默认不安装，需显式启用。'),
      children: [
        { name: 'disk-guard.sh', kind: 'file',
          note: t('SessionStart 가드 — 여유 디스크가 30G 미만이면 경고 (jetsam kill 예방)',
                  'SessionStart guard — warns when free disk drops under 30G (jetsam kill protection)',
                  'SessionStart 守卫：空闲磁盘低于 30G 时告警（防止 jetsam 杀进程）') },
        { name: 'com.OWNER.agents-backup.plist', kind: 'file',
          note: t('09:30 로컬 미러 launchd 잡. --with-launchd로 배치만 하고 자동 로드는 하지 않습니다.',
                  'A 09:30 local-mirror launchd job. --with-launchd only stages it; it is never auto-loaded.',
                  '09:30 的本地镜像 launchd 任务。--with-launchd 只做部署，绝不自动加载。') },
        { name: 'manifest.md', kind: 'file',
          note: t('무엇이 왜 macOS 전용인지, 어떻게 되살리는지',
                  'What is macOS-only, why, and how to re-enable it',
                  '说明哪些内容仅限 macOS、原因，以及如何重新启用') },
        { name: 'personal-examples/', kind: 'dir', count: '3',
          note: t('오너의 백업·푸시 흐름 예시. 설치기가 절대 실행하지 않습니다.',
                  'The owner’s backup and push flow, as examples. The installer never runs them.',
                  '所有者备份与推送流程的示例，安装器绝不会执行。') }
      ]
    },
    {
      name: 'windows-harness/', kind: 'dir', count: '6',
      note: t('윈도우도 1급 지원. 훅은 설치 시 크로스플랫폼 Python 포트로 교체됩니다.',
              'Windows is first-class — hooks are swapped for cross-platform Python ports at install time.',
              'Windows 同为一等公民：安装时把钩子替换为跨平台的 Python 版本。'),
      children: [
        { name: 'install.ps1', kind: 'file',
          note: t('-Check / -Apply / -Force. Python 런처를 탐지해 모든 훅 명령을 다시 씁니다.',
                  '-Check / -Apply / -Force. Detects the Python launcher and rewrites every hook command through it.',
                  '-Check / -Apply / -Force：探测 Python 启动器并据此重写所有钩子命令。') },
        { name: 'hooks/', kind: 'dir', count: '4',
          note: t('auto-format · precompact-guard · session-intent-archive · statusline의 Python 포트',
                  'Python ports of auto-format, precompact-guard, session-intent-archive and statusline',
                  'auto-format、precompact-guard、session-intent-archive、statusline 的 Python 移植版') },
        { name: 'README.md', kind: 'file',
          note: t('요구사항과 훅 매핑 표 — 어떤 훅이 윈도우에서 어떤 형태로 도는지',
                  'Requirements plus the hook mapping table: what each hook becomes on Windows',
                  '环境要求与钩子映射表：每个钩子在 Windows 上的形态') }
      ]
    }
  ]
}];

/* -------------------------------------------------------------- catalog data
   Skills: skills/<name>/SKILL.md frontmatter `description:` in the private source repo.
   Plugins: plugins/<name>/.claude-plugin/plugin.json `description`.            */
const CATALOG = [
  { n: 'clx-algorithmic-art', c: 'design', d: t(
    '시드 랜덤·파티클·플로우 필드·p5.js로 코드 자체가 작품이 되는 제너러티브 아트를 만듭니다.',
    'Generative art as code — seeded randomness, particles, flow fields, p5.js.',
    '用种子随机、粒子、流场与 p5.js 创作以代码为作品的生成艺术。') },
  { n: 'clx-apple-design', c: 'design', d: t(
    'UI 동작·모션·머티리얼·타이포의 애플식 기본기. 지정되지 않은 상호작용을 이 렌즈로 채웁니다.',
    'An Apple-first foundation for UI behavior, motion, materials and type — it fills in whatever the spec leaves unsaid.',
    'UI 行为、动效、材质与字体的 Apple 式基础，用来补齐规格未定义的交互。') },
  { n: 'clx-astryx', c: 'design', d: t(
    '기존 디자인 시스템이 없는 새 React 작업에만 붙는 컴포넌트·접근성 기반.',
    'A component and accessibility base for new React work that has no design system yet.',
    '仅用于尚无设计系统的新 React 项目的组件与无障碍基础。') },
  { n: 'clx-canvas-design', c: 'design', d: t(
    '포스터·표지 같은 정적 비주얼 아트를 PNG/PDF로 만듭니다.',
    'Static visual art — posters, covers, one-pagers — as PNG or PDF.',
    '制作海报、封面等静态视觉作品，输出 PNG 或 PDF。') },
  { n: 'clx-color-expert', c: 'design', d: t(
    'OKLCH/OKLab 변환, 개멋 처리, WCAG/APCA 대비, 색각 검증 같은 색 과학 작업.',
    'Color science: OKLCH/OKLab conversion, gamut handling, WCAG/APCA contrast, color-vision checks.',
    '色彩科学：OKLCH/OKLab 转换、色域处理、WCAG/APCA 对比与色觉校验。') },
  { n: 'clx-figma-workflow', c: 'design', d: t(
    'ClaudeTalkToFigma MCP 절차 — 채널 접속, 원본 충실 재현, export 검증 루프.',
    'The ClaudeTalkToFigma MCP procedure — channel join, faithful reproduction, export-and-verify loop.',
    'ClaudeTalkToFigma MCP 流程：加入频道、忠实还原、导出校验循环。') },
  { n: 'clx-frontend-design', c: 'design', d: t(
    '새 UI의 초기 미학 방향 — 개성, 타이포, 토큰 선택이 템플릿처럼 보이지 않게.',
    'The initial aesthetic direction for new UI — personality, type and tokens that do not read as a template.',
    '为新 UI 定初始美学方向：个性、字体与令牌，避免模板感。') },
  { n: 'clx-hand-drawn-diagrams', c: 'design', d: t(
    '손그림 느낌의 Excalidraw 다이어그램·스케치 흐름·와이어프레임.',
    'Hand-drawn Excalidraw diagrams, sketch flows and wireframes.',
    '手绘风格的 Excalidraw 图示、流程草图与线框图。') },
  { n: 'clx-immersive-web', c: 'design', d: t(
    'Three.js·R3F·GSAP·셰이더처럼 명시적으로 몰입형인 웹 경험의 설계와 리뷰.',
    'Design and review of explicitly immersive web work — Three.js, R3F, GSAP, shaders.',
    '面向 Three.js、R3F、GSAP、着色器等沉浸式网页体验的设计与评审。') },
  { n: 'clx-theme-factory', c: 'design', d: t(
    '프리셋 10종 또는 즉석 생성 테마로 슬라이드·문서·랜딩을 스타일링합니다.',
    'Styles slides, docs and landing pages with ten preset themes or one generated on the spot.',
    '用 10 套预设主题或即时生成的主题为幻灯片、文档与落地页配色。') },
  { n: 'clx-vercel-web-design-guidelines', c: 'design', d: t(
    'Vercel Web Interface Guidelines 오프라인 스냅샷 기준으로 UI 코드를 감사합니다.',
    'Audits UI code against an offline snapshot of Vercel’s Web Interface Guidelines.',
    '依据 Vercel Web Interface Guidelines 的离线快照审计 UI 代码。') },

  { n: 'clx-claude-config', c: 'meta', d: t(
    'Claude Code 전역 설정 유지보수 — CLAUDE.md 라우터, rules, guides, 스킬, 훅, settings.',
    'Maintains the Claude Code global setup — CLAUDE.md router, rules, guides, skills, hooks, settings.',
    '维护 Claude Code 全局配置：CLAUDE.md 路由、rules、guides、技能、钩子与 settings。') },
  { n: 'clx-codex-config', c: 'meta', d: t(
    'Codex 전역 설정 유지보수 — AGENTS.md 라우터, rules, guides, 스킬, 훅, config.toml.',
    'Maintains the Codex global setup — AGENTS.md router, rules, guides, skills, hooks, config.toml.',
    '维护 Codex 全局配置：AGENTS.md 路由、rules、guides、技能、钩子与 config.toml。') },
  { n: 'clx-model', c: 'meta', d: t(
    'models.toml 하나만 고치면 각 기계 설정까지 검증·반영·재확인되는 모델 레지스트리.',
    'The model registry — edit models.toml alone, and it validates, propagates and re-verifies every machine config.',
    '模型注册表：只改 models.toml，其余机器配置自动校验、下发并复核。') },
  { n: 'clx-session-intent', c: 'meta', d: t(
    '세션 단위 의도와 완료 조건(DoD) 관리 — 재개, 충돌, 완료 판정을 다룹니다.',
    'Session-scoped intent and definition of done — resumes, conflicts and completion calls.',
    '会话级意图与完成条件（DoD）管理：续接、冲突与完成判定。') },
  { n: 'clx-bracket-payload', c: 'meta', d: t(
    '["…"]로 감싼 내용이 실제 작업 지시라는 표기 규약.',
    'The convention that whatever sits inside ["…"] is the actual instruction to act on.',
    '约定：被 ["…"] 包裹的内容才是真正要执行的指令。') },
  { n: 'clx-repo-backup', c: 'meta', d: t(
    '.backup-repo 마커 한 줄로 폴더를 비공개 깃허브에 백업합니다. 마커가 없으면 아무것도 푸시하지 않습니다.',
    'Backs a folder up to a private GitHub repo, driven by a one-line .backup-repo marker. No marker, no push.',
    '依据一行 .backup-repo 标记把文件夹备份到私有 GitHub；没有标记就不推送。') },
  { n: 'clx-harness-factory', c: 'meta', d: t(
    '프로젝트 설명을 에이전트 정의와 스킬로 바꾸는 팀 아키텍처 팩토리.',
    'A team-architecture factory that turns a project description into agent definitions and skills.',
    '把项目描述转成智能体定义与技能的团队架构工厂。') },

  { n: 'clx-anti-hallucination', c: 'process', d: t(
    '긴 세션의 환각을 줄이는 컨텍스트 무결성 원칙 — 단언 전 검증, 압축 후 재확인.',
    'Context-integrity doctrine for long sessions — verify before asserting, re-check after compaction.',
    '面向长会话的上下文完整性准则：先验证再断言，压缩后重新核对。') },
  { n: 'clx-anti-overengineering', c: 'process', d: t(
    'ponytail 규율의 이식 가능한 미러. 다른 표면에서도 최소 해법을 고르게 합니다.',
    'A portable mirror of the ponytail discipline, so other surfaces still pick the smallest solution.',
    'ponytail 规约的可移植镜像，让其他环境同样选择最小解法。') },
  { n: 'clx-dataset-work', c: 'process', d: t(
    '데이터셋·Hugging Face 파이프라인 — 디스크 가드, 스트리밍 처리, JSONL 검증, 업로드 점검.',
    'Dataset and Hugging Face pipelines — disk guard, streaming processing, JSONL validation, upload checks.',
    '数据集与 Hugging Face 流水线：磁盘守卫、流式处理、JSONL 校验与上传检查。') },
  { n: 'clx-grill-me', c: 'process', d: t(
    '집요한 인터뷰로 의도·제약·숨은 가정을 끄집어냅니다. 작업보다 결정이 먼저일 때.',
    'Interviews you relentlessly to surface intent, constraints and hidden assumptions — for when the ask is a decision, not a task.',
    '用连续追问挖出意图、约束与隐含假设，适用于「先决策后动手」的情形。') },
  { n: 'clx-modular-architecture-design', c: 'process', d: t(
    '근거 기반 모듈 분해와 라이브러리식 경계. 산출물은 DESIGN.md 하나뿐입니다.',
    'Evidence-gated module decomposition with library-style boundaries; the deliverable is a single DESIGN.md.',
    '基于证据的模块拆分与库式边界，交付物只有一份 DESIGN.md。') },
  { n: 'clx-playwright', c: 'process', d: t(
    '터미널에서 실제 브라우저를 몰아 탐색·폼 입력·스냅샷·UI 디버깅을 수행합니다.',
    'Drives a real browser from the terminal — navigation, forms, snapshots, UI-flow debugging.',
    '在终端驱动真实浏览器：导航、填表、快照与 UI 流程调试。') },
  { n: 'ensemble-consensus', c: 'process', d: t(
    '경계 지어진 읽기 전용 적대 토론 → 합의 → 같은 턴 구현과 검증.',
    'Bounded read-only adversarial debate, then consensus, then same-turn implementation and verification.',
    '有界只读的对抗式辩论 → 达成共识 → 同一回合内实现并验证。') },

  { n: 'clx-concise-report', c: 'report', d: t(
    '두괄식 판정문, 근거만 남기기, 길이 상한 — 토큰 효율 보고 규율.',
    'Outcome first, evidence only, hard length ceilings — the token-efficient reporting discipline.',
    '结论先行、只留证据、限定长度的高效汇报规约。') },
  { n: 'clx-report-policy', c: 'report', d: t(
    '보고서를 파일로 남길지 채팅으로 끝낼지 정하는 규칙. 기본은 채팅, 잡동사니는 롤링 로그.',
    'Decides when a report becomes a file at all — chat-first by default, one rolling log for the ephemera.',
    '决定汇报是否要落成文件：默认留在聊天里，零碎内容进滚动日志。') },
  { n: 'clx-unslop', c: 'report', d: t(
    '발행 전에 unslop CLI로 AI 문체 흔적을 걷어냅니다.',
    'Runs finished prose through the unslop CLI to strip AI writing tells before publishing.',
    '发布前用 unslop CLI 去掉文本中的 AI 腔。') },

  { n: 'clx-supercoder', c: 'plugin', d: t(
    '해시 검증 패치, 라인 예산, 테스트 게이트를 갖춘 결정적 코딩 하네스.',
    'A deterministic coding harness: hash-checked patches, line budgets, test gates.',
    '确定性的编码框架：哈希校验补丁、行数预算与测试闸门。') },
  { n: 'clx-preprocessing', c: 'plugin', d: t(
    '명확화, 지속 작업 큐, loop_auto, doctor 점검을 담당하는 전처리기.',
    'Preprocessing: clarification, a durable work queue, loop_auto, and doctor checks.',
    '预处理器：澄清需求、持久任务队列、loop_auto 与 doctor 自检。') },
  { n: 'clx-ultracode', c: 'plugin', d: t(
    '에이전트·라운드 상한이 박힌 3에이전트 적대 합의 토론.',
    'Three-agent adversarial consensus debate with hard agent and round caps.',
    '带有智能体数与轮次硬上限的三方对抗式共识辩论。') },
  { n: 'clx-hermes-call', c: 'plugin', d: t(
    'hermes-call CLI로 원샷 또는 완료까지 경계가 정해진 작업을 위임합니다.',
    'Delegates one-shot or bounded until-done work through the hermes-call CLI.',
    '通过 hermes-call CLI 委派一次性或有界的「做到完成」任务。') }
];

/* Per-asset design intent (w) and payoff (b) — rendered as two labeled rows on each card. */
const WHY = {
  'clx-algorithmic-art': { w: t('차트가 아닌 "코드 생성예술" 요청만 정확히 받는 전용 통로.', 'A dedicated lane for code-as-art requests — never charts or UI.', '只承接"代码生成艺术"请求的专用通道，绝不接图表。'),
    b: t('시드 고정 재현성 + p5.js 오프라인 동봉으로 네트워크 없이 작품 생성.', 'Seeded reproducibility with p5.js bundled offline.', '种子可复现，离线内置 p5.js，无网络也能出作品。') },
  'clx-apple-design': { w: t('모든 실질 UI 작업 밑에 애플 상호작용 원칙 17개를 기본으로 깐다.', "Lays Apple's 17 interaction principles under every substantial UI task.", '为所有实质性 UI 工作垫上苹果 17 条交互原则。'),
    b: t('어떤 화면이든 반응성·공간 일관성·모션 품질이 기본값이 된다.', 'Responsiveness, spatial coherence and motion quality become defaults.', '响应性、空间连贯与动效品质成为默认值。') },
  'clx-astryx': { w: t('기존 시스템 없는 새 React 작업에만 Meta 디자인 시스템을 연결.', "Wires Meta's design system only into new React work with no established system.", '仅在没有既有体系的新 React 项目中接入 Meta 设计系统。'),
    b: t('접근성 검증된 컴포넌트 기반을 얻고, 남용은 라우팅 규칙이 차단.', 'An accessibility-proven component base, with routing rules preventing overuse.', '白得无障碍验证的组件底座，路由规则防止滥用。') },
  'clx-canvas-design': { w: t('포스터·표지 같은 정적 시각물만 맡는 아트디렉션 전용 스킬.', 'An art-direction lane reserved for static visuals like posters and covers.', '只负责海报、封面等静态视觉的艺术指导通道。'),
    b: t('제품 UI와 분리돼 있어 화면 작업이 포스터풍으로 오염되지 않는다.', 'Keeps product UI from drifting into poster aesthetics.', '与产品 UI 隔离，界面不被海报风格污染。') },
  'clx-color-expert': { w: t('색을 취향이 아니라 과학(OKLCH·대비 계산)으로 다루는 협소 도구.', 'Treats color as science (OKLCH, contrast math), not taste.', '把颜色当科学（OKLCH、对比度计算）而非品味。'),
    b: t('WCAG/APCA 수치가 붙은 팔레트 — 감이 아니라 측정으로 판정.', 'Palettes ship with WCAG/APCA numbers — judged by measurement.', '调色板自带 WCAG/APCA 数据，靠测量下结论。') },
  'clx-figma-workflow': { w: t('Figma MCP의 채널 접속·claude_page 규약·검증 루프를 표준화.', 'Standardizes Figma MCP channel joins, page conventions and verify loops.', '规范 Figma MCP 的频道接入、页面约定与校验循环。'),
    b: t('레퍼런스 재현 시 글자 세로찢김·요소 겹침 사고를 절차로 방지.', 'Procedure-level prevention of broken wraps and overlapping elements.', '用流程杜绝文字断裂、元素重叠等还原事故。') },
  'clx-frontend-design': { w: t('새 UI의 첫 미감 방향만 담당 — 템플릿 냄새 나는 기본값 거부.', 'Owns only the initial aesthetic direction of new UI — anti-template.', '只负责新 UI 的初始审美方向——拒绝模板味。'),
    b: t('신규 화면이 밋밋한 AI 랜딩 클리셰로 시작하지 않는다.', 'New screens never start as generic AI landing clichés.', '新界面不会从平庸的 AI 落地页套路起步。') },
  'clx-hand-drawn-diagrams': { w: t('손그림(Excalidraw) 언어를 명시 요청 시에만 여는 좁은 문.', 'A narrow gate for the hand-drawn (Excalidraw) language, explicit-only.', '仅在明确要求时开启的手绘（Excalidraw）窄门。'),
    b: t('결과물이 편집 가능한 다이어그램이라 리뷰에서 바로 수정된다.', 'Output stays an editable diagram, tweakable in reviews.', '产出是可编辑图表，评审中可直接修改。') },
  'clx-immersive-web': { w: t('Three.js·셰이더 등 진짜 3D 기술이 명시된 때만 등판.', 'Steps in only when real 3D/advanced-motion tech is explicitly named.', '仅当明确点名 Three.js、着色器等真 3D 技术时出场。'),
    b: t('일반 페이지 모션에 무거운 3D 스택이 끼는 과설계를 차단.', 'Blocks heavy 3D stacks from creeping into ordinary motion.', '阻止沉重 3D 栈混入普通页面动效。') },
  'clx-theme-factory': { w: t('산출물 스타일링을 검증 테마 10종+즉석 생성으로 규격화.', 'Standardizes artifact styling via 10 curated themes plus generation.', '用 10 套精选主题加即时生成规范产物样式。'),
    b: t('슬라이드·문서·랜딩이 몇 분 만에 일관된 색·폰트 체계를 입는다.', 'Slides and docs get a coherent color-font system in minutes.', '幻灯片与文档几分钟穿上一致的色彩字体体系。') },
  'clx-vercel-web-design-guidelines': { w: t('Vercel 공식 체크리스트 감사를 오프라인 스냅숏으로 고정 실행.', 'Runs the named Vercel checklist audit from a pinned offline snapshot.', '用固定离线快照执行 Vercel 官方清单审计。'),
    b: t('네트워크·버전 변동 없이 같은 기준으로 반복 감사 가능.', 'Repeatable audits against the same bar — no network drift.', '无网络无版本漂移，可重复同一标准审计。') },
  'clx-claude-config': { w: t('~/.claude 전역 설정(라우터·룰·훅) 유지보수를 한 절차로 캡슐화.', 'Encapsulates ~/.claude global-config maintenance into one procedure.', '将 ~/.claude 全局配置维护封装为单一流程。'),
    b: t('설정 변경이 체크리스트·doctor/selftest 검증과 함께 움직인다.', 'Config edits travel with checklists and doctor/selftest verification.', '配置变更伴随清单与 doctor/selftest 校验。') },
  'clx-codex-config': { w: t('Codex 쪽 설정·코어 동기화를 Claude와 같은 규율로 관리.', 'Manages Codex-side config and core sync under the same discipline.', '以同样纪律管理 Codex 侧配置与核心同步。'),
    b: t('두 CLI 사이 코어 드리프트를 doctor가 잡는 구조가 유지된다.', 'Core drift between the two CLIs stays doctor-caught.', '两个 CLI 的核心漂移始终被 doctor 捕获。') },
  'clx-model': { w: t('모델 id·effort의 단일 소스(models.toml)만 고치면 전체가 따라온다.', 'One source of truth (models.toml) that everything else follows.', '模型 id 与推理力度只有一个真源（models.toml）。'),
    b: t('하드코딩 0 — 모델 교체가 검증→전파→재검증 원패스로 끝난다.', 'Zero hardcoding — swaps are validate→propagate→re-verify in one pass.', '零硬编码——换模型即"验证→传播→复验"一趟完成。') },
  'clx-session-intent': { w: t('세션의 요구사항·완료정의(DoD)를 UUID 코어 파일로 이어붙인다.', 'Persists session requirements and DoD in a UUID-keyed core file.', '用 UUID 核心文件延续会话需求与完成定义。'),
    b: t('컨텍스트 압축·재개 후에도 "뭘 하기로 했는지"가 유실되지 않는다.', 'Nothing about "what we agreed" is lost across compaction or resume.', '压缩或恢复后"约定了什么"绝不丢失。') },
  'clx-bracket-payload': { w: t('["…"] 래핑을 행동 대상 페이로드로 못 박는 문법 계약.', 'A syntax contract: ["…"] wrapping marks the actionable payload.', '语法契约：["…"] 包裹即为待执行载荷。'),
    b: t('인용·지시가 잡담과 안 섞여 오해석이 사라진다.', 'Quotes and instructions never blur into chatter.', '引用与指令绝不混入闲聊，误解释归零。') },
  'clx-repo-backup': { w: t('폴더 백업을 .backup-repo 마커 한 줄로 선언하는 옵트인 파이프라인.', 'Opt-in backup declared by a one-line .backup-repo marker.', '用一行 .backup-repo 标记声明的可选备份管道。'),
    b: t('마커 없는 폴더는 절대 푸시 안 됨 — 실수 업로드가 구조적으로 불가.', 'No marker, no push — accidental uploads are structurally impossible.', '无标记绝不推送——误上传在结构上不可能。') },
  'clx-harness-factory': { w: t('도메인 설명→팀 설계 6패턴 공장 + 100종 라이브러리 설치기.', 'Turns domain briefs into teams (6 patterns) plus the 100-harness installer.', '把领域描述铸成团队（6 模式）+ 100 套哈尼斯安装器。'),
    b: t('팀이 코어 상한(≤10·≤2계층)을 자동 준수한 채 몇 분 만에 나온다.', 'Teams arrive in minutes, pre-bound to the core caps.', '团队数分钟成型，天然遵守核心上限。') },
  'clx-anti-hallucination': { w: t('긴 세션·압축 후의 기억 오염을 재검증·체크포인트 절차로 방어.', 'Procedural defense against memory rot in long or compacted sessions.', '用复验与检查点流程防御长会话的记忆污染。'),
    b: t('"예전에 그랬던 것 같다" 대신 다시 읽고 말하게 만든다.', 'Forces re-reading over "I think it was like that".', '逼着重读，而不是"我记得好像是"。') },
  'clx-anti-overengineering': { w: t('ponytail 없는 표면(Codex·Grok)에 YAGNI 규율을 이식하는 미러.', 'Ports the YAGNI discipline to surfaces without ponytail (Codex, Grok).', '把 YAGNI 纪律移植到没有 ponytail 的界面。'),
    b: t('어느 CLI에서 작업해도 최소 diff·표준 라이브러리 우선이 유지된다.', 'Minimal diffs and stdlib-first hold on every CLI.', '无论哪个 CLI，最小 diff 与标准库优先不变。') },
  'clx-dataset-work': { w: t('데이터셋 작업 전 디스크 가드·스트리밍 처리·업로드 체크를 의무화.', 'Mandates disk guards, streaming and upload checks for dataset jobs.', '数据集作业强制磁盘守卫、流式处理与上传检查。'),
    b: t('디스크 고갈로 프로세스가 죽는 사고의 재발 경로를 봉쇄.', 'Seals the disk-exhaustion crash path for good.', '封死磁盘耗尽杀进程的旧事故路径。') },
  'clx-grill-me': { w: t('결정형 요청은 실행 전에 의도·제약·대안을 집요하게 인터뷰.', 'Relentless interviewing before decision-shaped work begins.', '决策型请求先接受意图、约束、替代方案的连环追问。'),
    b: t('잘못된 문제를 훌륭하게 푸는 낭비가 시작 전에 걸러진다.', 'Filters out brilliantly solving the wrong problem.', '开工前滤掉"漂亮地解错题"。') },
  'clx-modular-architecture-design': { w: t('새 시스템 설계를 증거 게이트·단일 공개면·DESIGN.md 한 장으로 강제.', 'Forces new-system design through evidence gates into one DESIGN.md.', '新系统设计必须过证据门，产出单份 DESIGN.md。'),
    b: t('모듈 경계가 추측이 아닌 분석에서 나와 리팩터 비용이 급감.', 'Module boundaries come from analysis, not vibes.', '模块边界源于分析而非感觉，重构成本骤降。') },
  'clx-playwright': { w: t('터미널에서 실브라우저 증거(스냅숏·스크린숏)를 뽑는 표준 통로.', 'The standard lane for real-browser evidence from the terminal.', '从终端获取真实浏览器证据的标准通道。'),
    b: t('"된다"는 주장이 항상 렌더된 화면 증거와 함께 온다.', '"It works" always arrives with rendered proof.', '"能用"永远附带渲染截图证据。') },
  'ensemble-consensus': { w: t('고위험 모호성만 3모델 적대 토론→오케스트레이터 합의로 처리.', 'Reserves 3-model adversarial debate for high-stakes ambiguity only.', '仅高风险歧义才启动三模型对抗辩论与共识。'),
    b: t('값비싼 합의 절차가 필요한 순간에만 발동해 토큰 낭비가 없다.', 'The expensive ritual fires only when it earns its cost.', '昂贵仪式只在值回成本时触发。') },
  'clx-concise-report': { w: t('보고를 두괄식+길이 상한으로 규격화 — 결론 먼저, 과정 서술 금지.', 'Standardizes reports: verdict first, hard length caps, no narration.', '报告规范化：结论先行、硬性长度上限、禁流水账。'),
    b: t('어떤 작업이든 첫 문장만 읽으면 결과를 안다.', 'The first sentence always carries the answer.', '任何任务读第一句即知结果。') },
  'clx-report-policy': { w: t('보고서가 파일이 되는 조건을 게이트로 통제(채팅 우선).', 'Gates when a report may become a file (chat-first default).', '用闸门控制报告何时可以成为文件（聊天优先）。'),
    b: t('리포트 파일 더미가 쌓이는 고질병이 원천 차단된다.', 'The report-pile disease never starts.', '报告文件堆积的老毛病无从发生。') },
  'clx-unslop': { w: t('발행 전 AI 문체 흔적을 전용 CLI로 걷어내는 마감 공정.', 'A finishing pass that strips AI-tone via a dedicated CLI.', '发布前用专用 CLI 去除 AI 文风的收尾工序。'),
    b: t('공개 글이 사람 손을 탄 것처럼 읽힌다.', 'Published prose reads human.', '公开文字读起来像人写的。') },
  'clx-supercoder': { w: t('해시 검증 패치·라인 예산·테스트 게이트로 코딩을 결정적 절차화.', 'Makes coding deterministic: hash-verified patches, line budgets, test gates.', '让编码确定化：哈希校验补丁、行数预算、测试闸门。'),
    b: t('대충 고친 척이 불가능 — 모든 수정이 게이트를 통과해야 끝난다.', 'No fake fixes — every change must clear the gates.', '无法假装修好——一切改动必须过闸。') },
  'clx-preprocessing': { w: t('모호한 인입을 명확화·큐잉·닥터 점검으로 정돈하는 전처리기.', 'A preprocessor that clarifies, queues and doctor-checks fuzzy intake.', '把模糊输入整理为澄清、排队、体检的预处理器。'),
    b: t('요청이 실행 가능한 작업 단위가 된 뒤에만 일이 시작된다.', 'Work starts only after requests become executable units.', '请求变成可执行单元后才开工。') },
  'clx-ultracode': { w: t('에이전트 수·라운드에 하드캡을 박은 3자 적대 합의 토론.', 'Three-agent adversarial consensus with hard agent/round caps.', '智能体数与轮次带硬上限的三方对抗共识。'),
    b: t('무한 토론 없이 정해진 예산 안에서 최선의 합의가 나온다.', 'Best consensus inside a fixed budget — never endless debate.', '固定预算内得出最优共识，绝无无限辩论。') },
  'clx-hermes-call': { w: t('외부 Hermes 위임을 "경계 있는 호출" 계약으로만 허용.', 'External Hermes delegation only through a bounded-call contract.', '外部 Hermes 委派只走"有界调用"契约。'),
    b: t('위임이 폭주하지 않고 원샷/완료까지 범위가 항상 명시된다.', 'Delegation never sprawls; scope is always explicit.', '委派不会失控，范围始终明确。') }
};

const CATEGORIES = ['all', 'design', 'meta', 'process', 'report', 'plugin'];
const CAT_KEY = { all: 'catAll', design: 'catDesign', meta: 'catMeta', process: 'catProcess', report: 'catReport', plugin: 'catPlugin' };
const CAT_ICON = { all: 'boxes', design: 'palette', meta: 'sliders', process: 'branch', report: 'file', plugin: 'plug' };

/* --------------------------------------------------------------- install data */
const STEPS = {
  mac: [
    { title: t('저장소 클론', 'Clone the repo', '克隆仓库'),
      body: t('원격은 이 저장소 하나뿐입니다.', 'One remote, this repo.', '只有这一个远程仓库。'),
      code: 'git clone https://github.com/algocean1204/clx-harness-full-package.git\ncd clx-harness-full-package' },
    { title: t('드라이런 + 환경 자동감지', 'Dry run + environment detection', '空跑检查 + 环境自动识别'),
      body: t('OS·python·git, claude/codex/grok CLI 설치 여부, 기존 ~/.claude·~/.codex·~/.agents·~/.grok와 인증 파일까지 먼저 감지해 출력합니다. 무엇을 어디에 쓸지 보여줄 뿐 아무것도 바꾸지 않습니다.',
              'First detects and prints your machine: OS, python, git, which of the claude/codex/grok CLIs exist, any existing ~/.claude · ~/.codex · ~/.agents · ~/.grok, and auth files. Then it shows the exact write scope — and changes nothing.',
              '先检测并打印本机环境：OS、python、git、是否装有 claude/codex/grok CLI、已存在的 ~/.claude · ~/.codex · ~/.agents · ~/.grok 与认证文件；随后只显示将要写入的范围，不做任何改动。'),
      code: './install.sh --check' },
    { title: t('설치 — 병합, 삭제 없음', 'Install — merge, never delete', '安装 —— 合并，不删除'),
      body: t('common/{claude,codex,agents,grok}를 ~/.claude · ~/.codex · ~/.agents · ~/.grok로 복사합니다. Grok의 다른 설정은 보존하고 sandbox profile만 갱신합니다. ~/.claude가 비어있지 않으면 --force 없이는 거부합니다.',
              'Copies common/{claude,codex,agents,grok} into ~/.claude, ~/.codex, ~/.agents and ~/.grok. Other Grok settings are preserved while only its sandbox profile is updated. A non-empty ~/.claude is refused without --force.',
              '把 common/{claude,codex,agents,grok} 复制到 ~/.claude、~/.codex、~/.agents 与 ~/.grok；保留其他 Grok 设置，仅更新 sandbox profile。~/.claude 非空时必须加 --force。'),
      code: './install.sh --apply\n./install.sh --apply --force   # merge into an existing setup' },
    { title: t('토큰 치환과 실행 권한', 'Token materialization and +x', '占位符替换与执行权限'),
      body: t('설치된 모든 텍스트 파일의 __CLX_HOME__이 실제 $HOME으로 바뀌고(json·toml·plist는 각 형식에 맞게 이스케이프), 훅 스크립트에 실행 권한이 붙습니다.',
              'Every installed text file gets __CLX_HOME__ replaced with your real $HOME (escaped per format for json, toml and plist), and hook scripts get the executable bit.',
              '所有已安装文本文件中的 __CLX_HOME__ 会替换为真实 $HOME（json、toml、plist 按各自格式转义），并给钩子脚本加上可执行权限。'),
      code: 'materialized __CLX_HOME__ -> /Users/you', noCopy: true },
    { title: t('인증은 직접', 'Bring your own auth', '认证需自行处理'),
      body: t('설치기는 크리덴셜과 Keychain을 건드리지 않습니다. Claude Code와 Codex에 각자 로그인하면 되고, 활성화된 플러그인은 첫 실행 때 마켓플레이스에서 설치됩니다. launchd 잡은 --with-launchd로만 배치되고 자동 로드는 하지 않습니다.',
              'The installer never touches credentials or the Keychain. Sign in to Claude Code and Codex yourself; enabled plugins install from their marketplaces on first launch. The launchd job is staged only with --with-launchd, and never auto-loaded.',
              '安装器不碰凭据与钥匙串。请自行登录 Claude Code 与 Codex；已启用插件会在首次启动时从市场安装。launchd 任务仅在 --with-launchd 时部署，且不会自动加载。'),
      code: './install.sh --apply --with-launchd   # optional, macOS only' },
    { title: t('모델 레지스트리 자동감지', 'Model registry auto-detection', '模型注册表自动检测'),
      body: t('설치 끝에 설치된 백엔드에 직접 물어봅니다 — grok models와 Codex 모델 카탈로그. 없는 모델 id나 지원하지 않는 effort는 FAIL, 같은 세대에 더 상위 모델이 있거나 새 세대가 나왔으면 WARN. CLI가 없는 역할은 건너뜁니다. 바꾸지는 않습니다 — 고치는 건 /clx-model 하나뿐입니다.',
              'At the end of an install it asks the installed backends directly — grok models and the Codex model catalog. An unknown id or an unsupported effort is a FAIL; a higher-ranked model in the same generation, or a newer generation, is a WARN. Roles whose CLI is absent are skipped. It never rewrites the pin — /clx-model is the only way to change one.',
              '安装结束时直接询问已安装的后端 —— grok models 与 Codex 模型目录。未知的模型 id 或不支持的 effort 判为 FAIL；同代中存在更高排名的模型、或出现新一代，则给出 WARN。缺少 CLI 的角色会被跳过。它不会自动改写，唯一的修改途径是 /clx-model。'),
      code: 'python3 ~/.claude/hooks/model-registry-check.py' },
    { title: t('나중에 업데이트', 'Updating later', '之后的更新'),
      body: t('한 프로젝트라 한 명령으로 끝납니다. 기존 settings.json은 덮어쓰지 않고 병합되고(내 model·permissions·본인 훅 유지, 직전 파일은 .pre-clx-* 로 보관), 채워 넣은 ~/.agents/user/*와 직접 만든 스킬은 그대로 남습니다. Claude Code 안에서는 /clx-update 한 번.',
              'One project, one command. An existing settings.json is merged rather than replaced (your model, permissions and own hooks stay; the previous file is kept as .pre-clx-*), and your filled ~/.agents/user/* and hand-made skills survive. Inside Claude Code: just /clx-update.',
              '一个项目，一条命令。已有的 settings.json 会被合并而非覆盖（保留你的 model、permissions 与自有钩子，旧文件存为 .pre-clx-*），你填写的 ~/.agents/user/* 和自建技能都会保留。在 Claude Code 中直接用 /clx-update。'),
      code: 'git pull --ff-only origin main && ./install.sh --apply --force' }
  ],
  win: [
    { title: t('저장소 클론', 'Clone the repo', '克隆仓库'),
      body: t('PowerShell 5.1+ 또는 7+, 그리고 PATH의 Python 3가 필요합니다.',
              'Needs PowerShell 5.1+ or 7+, plus Python 3 on PATH.',
              '需要 PowerShell 5.1+ 或 7+，以及 PATH 中的 Python 3。'),
      code: 'git clone https://github.com/algocean1204/clx-harness-full-package.git\ncd clx-harness-full-package' },
    { title: t('드라이런', 'Dry run', '空跑检查'),
      body: t('쓰기 범위와 함께 탐지된 Python 런처를 보고합니다. Python이 없으면 그 사실도 여기서 알려줍니다.',
              'Reports the write scope and which Python launcher it found — or tells you right here that it found none.',
              '报告写入范围与探测到的 Python 启动器；若没有 Python，这一步就会告诉你。'),
      code: 'powershell -ExecutionPolicy Bypass -File windows-harness\\install.ps1 -Check' },
    { title: t('적용', 'Apply', '执行安装'),
      body: t('%USERPROFILE%\\.claude, .codex, .agents, .grok를 만들고 common/을 병합 복사합니다. Grok의 다른 설정은 보존하고 sandbox profile만 갱신합니다. 비어있지 않은 ~\\.claude는 -Force 없이는 거부합니다.',
              'Creates %USERPROFILE%\\.claude, .codex, .agents and .grok and merge-copies common/. Other Grok settings are preserved while only its sandbox profile is updated. A non-empty ~\\.claude is refused without -Force.',
              '创建 %USERPROFILE%\\.claude、.codex、.agents 与 .grok 并合并复制 common/；保留其他 Grok 设置，仅更新 sandbox profile。~\\.claude 非空时须加 -Force。'),
      code: 'powershell -ExecutionPolicy Bypass -File windows-harness\\install.ps1 -Apply\n#  -Force  merges into an existing setup' },
    { title: t('Python 훅 포트', 'Python hook ports', 'Python 钩子移植'),
      body: t('windows-harness\\hooks\\*.py를 ~\\.claude\\hooks로 복사하고, 모든 훅 명령을 탐지된 런처(py -3 / python)로 실행되도록 다시 씁니다. bash 훅은 각자의 .py 포트로 바뀝니다.',
              'Copies windows-harness\\hooks\\*.py into ~\\.claude\\hooks and rewrites every hook command to run through the detected launcher (py -3 / python). Bash hooks are swapped for their .py ports.',
              '把 windows-harness\\hooks\\*.py 复制到 ~\\.claude\\hooks，并把所有钩子命令改为经由探测到的启动器（py -3 / python）执行；bash 钩子替换为对应的 .py 版本。'),
      code: 'auto-format.py · precompact-guard.py\nsession-intent-archive.py · statusline.py', noCopy: true },
    { title: t('모델 레지스트리 자동감지', 'Model registry auto-detection', '模型注册表自动检测'),
      body: t('맥과 동일하게, 설치 끝에 설치된 백엔드에 물어 모델 핀이 뒤처졌는지 알려줍니다. Python이 없으면 이 단계도 건너뜁니다.',
              'Same as macOS: at the end of an install it asks the installed backends whether a model pin has fallen behind. With no Python this step is skipped too.',
              '与 macOS 相同：安装结束时询问已安装的后端，判断模型固定值是否已经落后。若没有 Python，此步骤同样跳过。'),
      code: 'py -3 %USERPROFILE%\\.claude\\hooks\\model-registry-check.py' },
    { title: t('OS별 활성화', 'Per-OS activation', '按系统激活'),
      body: t('Python이 없으면 세션이 깨지지 않도록 훅을 아예 등록하지 않고 statusLine도 제거한 뒤 비활성으로 표시합니다. macOS 전용(disk-guard, launchd)은 윈도우에서 등록되지 않습니다. 맥과 완전히 같은 경험이 필요하면 WSL에서 install.sh를 쓰세요.',
              'With no Python it registers no hooks at all and strips statusLine, so sessions still start cleanly — the summary lists them as inactive. macOS-only pieces (disk-guard, launchd) are never registered here. For a truly identical experience, run install.sh inside WSL.',
              '若缺少 Python，则完全不注册钩子并移除 statusLine，保证会话正常启动，并在摘要中标为未启用。macOS 专属部分（disk-guard、launchd）不会在此注册。若想获得完全一致的体验，请在 WSL 中运行 install.sh。'),
      code: '# macOS-only: disk-guard.sh, launchd  ->  skipped', noCopy: true }
  ]
};

/* ------------------------------------------------------------------ runtime */
let lang = 'ko';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dict = () => I18N[lang];

function paintIcons(root = document) {
  $$('[data-icon]', root).forEach((el) => {
    if (el.firstElementChild) return;
    el.innerHTML = icon(el.dataset.icon);
  });
}

function applyStatic() {
  const d = dict();
  $$('[data-i18n]').forEach((el) => {
    const val = d[el.dataset.i18n];
    if (val === undefined) return;
    if (el.dataset.i18nAttr) el.setAttribute(el.dataset.i18nAttr, val);
    else el.textContent = val;
  });
  document.documentElement.lang = lang === 'zh' ? 'zh-Hans' : lang;
}

/* ---- ecosystem connectors: curves drawn from the live card geometry ---- */
function drawEcoLinks() {
  const canvas = $('#ecoCanvas');
  const svg = $('#ecoLinks');
  if (!canvas || !svg) return;
  const box = canvas.getBoundingClientRect();
  if (!box.width) return;
  svg.setAttribute('viewBox', '0 0 ' + box.width + ' ' + box.height);

  const labels = [dict().connVendor, dict().connInstall, dict().connMirror];
  const rel = (el) => {
    const r = el.getBoundingClientRect();
    return { l: r.left - box.left, r: r.right - box.left, t: r.top - box.top, b: r.bottom - box.top };
  };
  const out = [];

  for (let i = 1; i <= 3; i++) {
    const a = $('#eco-' + i), b = $('#eco-' + (i + 1));
    if (!a || !b) continue;
    const A = rel(a), B = rel(b);
    const side = B.l >= A.r - 2;   // laid out in a row vs. stacked
    let x1, y1, x2, y2, c1x, c1y, c2x, c2y, head;

    if (side) {
      x1 = A.r + 2; y1 = (A.t + A.b) / 2;
      x2 = B.l - 10; y2 = (B.t + B.b) / 2;
      const dx = (x2 - x1) * 0.45;
      c1x = x1 + dx; c1y = y1; c2x = x2 - dx; c2y = y2;
      head = 'M' + x2 + ' ' + y2 + ' l-8 -5 v10 z';
    } else {
      x1 = (A.l + A.r) / 2; y1 = A.b + 2;
      x2 = (B.l + B.r) / 2; y2 = B.t - 10;
      const dy = (y2 - y1) * 0.45;
      c1x = x1; c1y = y1 + dy; c2x = x2; c2y = y2 - dy;
      head = 'M' + x2 + ' ' + y2 + ' l-5 -8 h10 z';
    }

    const d = 'M' + x1 + ' ' + y1 + ' C' + c1x + ' ' + c1y + ' ' + c2x + ' ' + c2y + ' ' + x2 + ' ' + y2;
    out.push('<path class="eco-flow-path" d="' + d + '"/>');
    out.push('<path class="eco-flow-dash" d="' + d + '"/>');
    out.push('<path class="eco-flow-cap" d="' + head + '"/>');
    out.push('<circle class="eco-flow-cap" cx="' + x1 + '" cy="' + y1 + '" r="3"/>');
    out.push('<text class="eco-flow-label" x="' + ((x1 + x2) / 2) + '" y="' +
      (side ? Math.min(y1, y2) - 14 : (y1 + y2) / 2 + 4) + '">' + esc(labels[i - 1]) + '</text>');
  }
  svg.innerHTML = out.join('');
}

/* ---- tree ---- */
function treeRow(node, level, gid) {
  const kids = node.children && node.children.length;
  const kindIcon = node.kind === 'dir' ? 'folder' : node.kind === 'group' ? 'ellipsis' : 'file';
  const kindCls = node.kind === 'dir' ? 'kind-dir' : node.kind === 'group' ? 'kind-group' : 'kind-file';
  return '' +
    '<div class="row' + (kids ? ' has-children' : '') + '" role="treeitem" tabindex="-1"' +
      ' aria-level="' + level + '"' + (kids ? ' aria-expanded="' + (node.open ? 'true' : 'false') + '"' : '') +
      (gid ? ' aria-owns="' + gid + '"' : '') + '>' +
      (kids ? '<span class="twisty" aria-hidden="true">' + icon('chevron-right') + '</span>'
            : '<span class="twisty-spacer" aria-hidden="true"></span>') +
      '<span class="kind ' + kindCls + '" aria-hidden="true">' + icon(kindIcon) + '</span>' +
      '<span class="row-body">' +
        '<span class="row-name">' + esc(node.name) +
          (node.count ? '<span class="row-count">' + esc(node.count) + '</span>' : '') +
        '</span>' +
        (node.note ? '<span class="row-note">' + esc(node.note[lang]) + '</span>' : '') +
      '</span>' +
    '</div>';
}

let grpSeq = 0;

function treeList(nodes, level) {
  return nodes.map((node) => {
    const kids = node.children && node.children.length;
    const gid = kids ? 'tgrp-' + (++grpSeq) : null;
    return '<li role="none">' + treeRow(node, level, gid) +
      (kids ? '<ul role="group" id="' + gid + '"' + (node.open ? '' : ' hidden') + '>' + treeList(node.children, level + 1) + '</ul>' : '') +
      '</li>';
  }).join('');
}

function renderTree() {
  const root = $('#tree');
  // Language re-renders keep the visitor's expansion state (node order is locale-invariant).
  const prev = $$('.row[aria-expanded]', root).map((r) => r.getAttribute('aria-expanded') === 'true');
  grpSeq = 0;
  root.innerHTML = treeList(TREE, 1);
  $$('.row[aria-expanded]', root).forEach((r, i) => { if (i < prev.length) setExpanded(r, prev[i]); });
  $$('.row', root).forEach((r, i) => { r.tabIndex = i === 0 ? 0 : -1; });
}

const rowsVisible = () => $$('#tree .row').filter((r) => r.offsetParent !== null);

function setExpanded(row, open) {
  if (!row.hasAttribute('aria-expanded')) return;
  row.setAttribute('aria-expanded', String(open));
  const group = row.parentElement.querySelector(':scope > ul');
  if (group) group.hidden = !open;
}

function focusRow(row) {
  if (!row) return;
  $$('#tree .row').forEach((r) => { r.tabIndex = -1; });
  row.tabIndex = 0;
  row.focus();
}

function initTree() {
  const tree = $('#tree');

  tree.addEventListener('click', (e) => {
    const row = e.target.closest('.row');
    if (!row || !row.hasAttribute('aria-expanded')) return;
    setExpanded(row, row.getAttribute('aria-expanded') !== 'true');
    focusRow(row);
  });

  tree.addEventListener('keydown', (e) => {
    const row = e.target.closest('.row');
    if (!row) return;
    const list = rowsVisible();
    const i = list.indexOf(row);
    const expandable = row.hasAttribute('aria-expanded');
    const open = row.getAttribute('aria-expanded') === 'true';
    let handled = true;

    switch (e.key) {
      case 'ArrowDown': focusRow(list[Math.min(i + 1, list.length - 1)]); break;
      case 'ArrowUp': focusRow(list[Math.max(i - 1, 0)]); break;
      case 'Home': focusRow(list[0]); break;
      case 'End': focusRow(list[list.length - 1]); break;
      case 'ArrowRight':
        if (expandable && !open) setExpanded(row, true);
        else if (expandable && open) focusRow(list[i + 1]);
        break;
      case 'ArrowLeft':
        if (expandable && open) setExpanded(row, false);
        else {
          const parent = row.parentElement.parentElement.closest('li');
          if (parent) focusRow(parent.querySelector(':scope > .row'));
        }
        break;
      case 'Enter': case ' ':
        if (expandable) setExpanded(row, !open);
        break;
      default: handled = false;
    }
    if (handled) e.preventDefault();
  });

  $('#treeExpand').addEventListener('click', () => {
    $$('#tree .row[aria-expanded]').forEach((r) => setExpanded(r, true));
  });
  $('#treeCollapse').addEventListener('click', () => {
    $$('#tree .row[aria-expanded]').forEach((r) => setExpanded(r, false));
    // Roving tabindex must not be left on a row inside a now-hidden group.
    const current = $('#tree .row[tabindex="0"]');
    if (!current || current.offsetParent === null) {
      $$('#tree .row').forEach((r) => { r.tabIndex = -1; });
      const first = rowsVisible()[0];
      if (first) first.tabIndex = 0;
    }
  });
}

/* ---- catalog ---- */
let activeCat = 'all';

function renderChips() {
  const d = dict();
  $('#catChips').innerHTML = CATEGORIES.map((c) => {
    const n = c === 'all' ? CATALOG.length : CATALOG.filter((x) => x.c === c).length;
    return '<button type="button" class="chip" data-cat="' + c + '" aria-pressed="' + (c === activeCat) + '">' +
      icon(CAT_ICON[c]) + '<span>' + esc(d[CAT_KEY[c]]) + '</span><span class="chip-n">' + n + '</span></button>';
  }).join('');
}

function renderCards() {
  const q = $('#catSearch').value.trim().toLowerCase();
  const items = CATALOG.filter((x) =>
    (activeCat === 'all' || x.c === activeCat) &&
    (!q || x.n.toLowerCase().includes(q) || x.d[lang].toLowerCase().includes(q)));

  const d = dict();
  $('#catGrid').innerHTML = items.map((x) =>
    '<li class="card cat-' + x.c + '">' +
      '<div class="card-top">' +
        '<span class="card-icon" aria-hidden="true">' + icon(CAT_ICON[x.c]) + '</span>' +
        '<span class="card-name">' + esc(x.n) + '</span>' +
        '<span class="tag">' + esc(d[CAT_KEY[x.c]]) + '</span>' +
      '</div>' +
      '<p class="card-desc">' + esc(x.d[lang]) + '</p>' +
      (WHY[x.n] ? '<dl class="card-why">' +
        '<div><dt>' + esc(d.whyLabel) + '</dt><dd>' + esc(WHY[x.n].w[lang]) + '</dd></div>' +
        '<div><dt>' + esc(d.benefitLabel) + '</dt><dd>' + esc(WHY[x.n].b[lang]) + '</dd></div>' +
      '</dl>' : '') +
    '</li>').join('');

  $('#catCount').textContent = d.catCount.replace('{n}', items.length);
  $('#catEmpty').hidden = items.length > 0;
}

function initCatalog() {
  $('#catChips').addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    activeCat = chip.dataset.cat;
    $$('#catChips .chip').forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
    renderCards();
  });
  $('#catSearch').addEventListener('input', renderCards);
  $('#catClear').addEventListener('click', () => {
    $('#catSearch').value = '';
    activeCat = 'all';
    $$('#catChips .chip').forEach((c) => c.setAttribute('aria-pressed', String(c.dataset.cat === 'all')));
    renderCards();
  });
}

/* ---- install steps ---- */
function renderSteps() {
  const arrow = '<li class="step-link" role="presentation" aria-hidden="true">' + icon('chevron-right') + '</li>';
  ['mac', 'win'].forEach((os) => {
    $('#steps' + (os === 'mac' ? 'Mac' : 'Win')).innerHTML = STEPS[os].map((s, i) =>
      '<li class="step">' +
        '<span class="step-n">' + (i + 1) + '</span>' +
        '<h3>' + esc(s.title[lang]) + '</h3>' +
        '<p>' + esc(s.body[lang]) + '</p>' +
        (s.code ? (s.noCopy
          ? '<pre class="output"><code>' + esc(s.code) + '</code></pre>'
          : '<div class="codebox"><pre><code>' + esc(s.code) + '</code></pre>' +
            '<button type="button" class="copy-btn" aria-live="polite" aria-label="' +
            esc(I18N[lang].copyBtn + ': ' + s.title[lang]) + '">' + esc(I18N[lang].copyBtn) + '</button></div>') : '') +
      '</li>').join(arrow);
  });
}

function initTabs() {
  const tabs = [$('#tab-mac'), $('#tab-win')];
  const select = (tab) => {
    tabs.forEach((other) => {
      const on = other === tab;
      other.setAttribute('aria-selected', String(on));
      other.tabIndex = on ? 0 : -1;
      $('#' + other.getAttribute('aria-controls')).hidden = !on;
    });
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      select(next);
      next.focus();
    });
  });
  // Windows visitors land on their own instructions ("Win32"/"Win64"; Darwin stays on mac).
  if (/^win/i.test(navigator.platform || '')) select(tabs[1]);
}

/* ---- copy-to-clipboard ---- */
function initCopy() {
  // Clipboard denied/unavailable -> select the command so a manual copy still works.
  const selectCode = (code) => {
    const sel = window.getSelection();
    if (!sel) return;
    const range = document.createRange();
    range.selectNodeContents(code);
    sel.removeAllRanges();
    sel.addRange(range);
  };
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.copy-btn');
    if (!btn) return;
    const box = btn.closest('.codebox');
    const code = box && box.querySelector('code');
    if (!code) return;
    if (!navigator.clipboard) { selectCode(code); return; }
    navigator.clipboard.writeText(code.textContent).then(() => {
      btn.textContent = I18N[lang].copyDone;
      btn.classList.add('done');
      setTimeout(() => { btn.textContent = I18N[lang].copyBtn; btn.classList.remove('done'); }, 1600);
    }).catch(() => selectCode(code));
  });
}

/* ---- language ---- */
function moveThumb() {
  const seg = $('#langSeg');
  const thumb = $('.seg-thumb', seg);
  const btn = $('.seg-btn[aria-pressed="true"]', seg);
  if (!btn || !btn.offsetWidth) return;
  thumb.style.width = btn.offsetWidth + 'px';
  thumb.style.height = btn.offsetHeight + 'px';
  thumb.style.transform = 'translate(' + btn.offsetLeft + 'px, ' + btn.offsetTop + 'px)';
  thumb.classList.add('ready');
}

function setLang(next, persist) {
  lang = I18N[next] ? next : 'ko';
  $$('#langSeg .seg-btn').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
  applyStatic();
  document.title = I18N[lang].docTitle;
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.setAttribute('content', I18N[lang].docDesc);
  const ctaCopy = $('.cta-clone .copy-btn');
  if (ctaCopy) ctaCopy.setAttribute('aria-label', I18N[lang].copyBtn + ': git clone');
  renderTree();
  renderChips();
  renderCards();
  renderSteps();
  paintIcons();
  moveThumb();
  requestAnimationFrame(drawEcoLinks);
  if (persist) { try { localStorage.setItem('clx-lang', lang); } catch (_) { /* private mode */ } }
}

function initLang() {
  $('#langSeg').addEventListener('click', (e) => {
    const btn = e.target.closest('.seg-btn');
    if (btn) setLang(btn.dataset.lang, true);
  });
  let saved = null;
  try { saved = localStorage.getItem('clx-lang'); } catch (_) { /* private mode */ }
  setLang(saved || 'ko', false);
}

paintIcons();
initTree();
initCatalog();
initTabs();
initCopy();
initLang();

/* Connector geometry depends on the rendered card sizes, so redraw on reflow. */
if (window.ResizeObserver) {
  const ro = new ResizeObserver(() => drawEcoLinks());
  ro.observe($('#ecoCanvas'));
} else {
  window.addEventListener('resize', drawEcoLinks);
}
window.addEventListener('resize', moveThumb);
window.addEventListener('load', () => { drawEcoLinks(); moveThumb(); });
})();
