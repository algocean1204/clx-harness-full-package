---
name: clx-modular-architecture-design
description: >
  Analysis-driven module architecture design with library-style boundaries: evidence-gated
  decomposition, one public surface per module, single composition root, field-level IN/OUT
  specs, and a single DESIGN.md deliverable (never HTML). Use when designing the structure
  of a NEW system/project, a large-scale refactor design, or on explicit requests —
  'architecture', 'system design', '설계도', '아키텍처', '모듈 설계', '파이프라인 설계'.
  Do NOT use for simple structure questions or small edits.
---

# Analysis-Driven Module Architecture Design (Library-Style)

> **"Modularization is the RESULT of analysis, not the default. Every split/commonization
> decision carries a one-line justification — and every surviving module is shaped like a
> small library: one public surface, wired in one place, deletable in one move."**

Identity: OUT=1, straight-line pipeline, field-level specs, gates before structure.
Deliverable: a **single DESIGN.md** — HTML generation forbidden. If the user asked for
HTML or any other format, state the refusal explicitly in one line — never silently
substitute. Gate refusals always surface in the same-turn report, even under goal/loop.

## Workflow

### Phase 0: Mode selection

- **Greenfield**: new system → Phases 1–5 as written.
- **Refactor**: existing code → inventory current modules first (`rg`/tree scan: real call
  sites, sizes, change hot-spots from git log), THEN run Phases 2–5 on the target design,
  and add a **migration order** to DESIGN.md (strangler pattern: which module moves first,
  what stays temporarily duplicated, cutover checks). Gates apply identically — refactors
  over-split even more easily than greenfield.

### Phase 1: Tech-stack agreement — the ONLY approval gate

Establish purpose, deployment target, performance needs, stack preference (skip questions
the user already answered) → propose as a table → **one user approval**. Every later phase
proceeds without approval and reports results. Under goal/loop, replace even this gate with
"propose + state the chosen default + proceed".

### Phase 2: Scale Gate — decide decomposition depth first

| Scale | Rough size (files) | Allowed depth |
|-------|--------------------|---------------|
| Small | ~10 | Feature level (F1..FN) only. Start with NO C0 |
| Medium | ~40 | Feature + Level-2 modules. C0 only via admission review |
| Large | beyond | Full hierarchy + C0. Write feature-by-feature |

Decomposing past the allowed depth is forbidden unless the Phase-3 split gate provides evidence.
The gate reads the **current** codebase size (refactor: the as-is inventory) — never the
user's target estimate. Scale is an analysis output, not a user input.

### Phase 3: Decomposition — analysis gates (WHETHER a boundary exists)

**Read `references/module-design-rules.md` first**, then in order:

1. Feature decomposition (F1..FN)
2. **Split gate** on every split candidate: 2+ reasons to change **AND** (2+ real reuse sites
   ∥ independent test value ∥ different change cadence/owner). Fails the gate → **keep it together**
3. **C0 admission review** on every commonization candidate (rule of three + interface stability
   + domain independence). Fails → keep it feature-local — **duplication at this stage is allowed**
4. **Merge signals** sweep: pass-through modules, always-called-together, effectively identical
   IN/OUT → merge them
5. Derive the straight-line main pipeline

### Phase 4: Boundary shaping — library discipline (HOW each boundary looks)

**Read `references/library-module-rules.md` first**, then for every surviving module:

1. **Public surface**: exactly one exported entry point + its IN/OUT types; internals private
2. **Composition root**: all cross-module wiring at one root (per level); modules never
   wire or import siblings
3. **Extension gate**: 2+ REAL variants of one contract today → shared contract + variant
   modules + selection map at the root; otherwise no interface, no registry
4. **Hidden-input ban**: modules consume only declared INs — env/config touching happens
   at the composition root (or a C0 config module) only
5. **Delete test**: removal = delete folder + unwire at root; anything more means the
   boundary is wrong — fix it now

### Phase 5: Detailed IN/OUT specs + DESIGN.md

For every module: IN (main/aux — type, source, description), exactly one OUT (field-level),
**failure semantics** (what the OUT looks like on failure — Result-style object or declared
exception; never an unspecified crash), **PUBLIC surface** (exported names), internal logic,
C0 usage, constraints, a one-line **removal note**, and a **parallel mark**
(`parallel-safe: yes/no` + resource note) whenever the user stated quantified resources —
the design must show how stated RAM/cores get saturated. Then generate a **single
`DESIGN.md`** following `references/ai-behavior-guide.md`: header → tech-stack table →
folder tree → main pipeline (optional mermaid) → C0 (if any) → extension points (if any) →
feature cards → dependency table → implementation checklist → **design decision log**
(justification for every split/commonization/merge/variant).

## Core rules (quick reference)

| Rule | Meaning |
|------|---------|
| **Justification duty** | Every split/commonization gets one written reason — no reason, keep together |
| **Split gate** | 2+ change reasons AND (2+ reuse ∥ test value ∥ different cadence) |
| **C0 admission** | 3rd real use site + stable interface + domain-independent — all three or stay local |
| **Module floor** | A single function is NOT a module — modules are cohesive responsibility units |
| **OUT = 1** | One OUT per module (a multi-field result object counts as one) |
| **Public surface = 1** | One exported entry + types; consumers import the module root only |
| **Composition root** | All wiring in one place — add/swap/remove touches one file + one folder |
| **Extension gate** | Contract + registry only with 2+ real variants today — never speculative |
| **Hidden-input ban** | Nothing consumed that the IN spec doesn't declare; env stays at the root |
| **Delete test** | Removal = folder + unwire; more than that = wrong boundary |
| **Straight pipeline** | One branch-free line; conditionals live inside modules |
| **Spec = code level** | Types, sources, and fields written out in IN/OUT |
| **Deliverable** | Single `DESIGN.md` — HTML generation forbidden |

## Living design (drift prevention)

DESIGN.md is not a one-shot artifact. Any deviation during implementation — a module merged,
a boundary moved, a public surface or contract changed — updates the decision log **in the
same turn** as the code change. Breaking contract changes additionally re-run the OUT→IN
type-chain check over consumers. A design that disagrees with the code is worse than no design.

## Mandatory verification before declaring the design done

- [ ] Decision log covers every split / commonization / merge / variant with a reason?
- [ ] Every C0 module has 3+ real use sites AND passes the standalone test?
- [ ] No module left matching a merge signal?
- [ ] OUT=1 everywhere, IN sources named, pipeline straight, zero circular deps?
- [ ] Every module's failure semantics specified (no unspecified crash paths)?
- [ ] PUBLIC surface listed for every module (one entry + types, nothing else)?
- [ ] All wiring at composition roots — no module constructs or imports a sibling?
- [ ] Every extension point backed by 2+ real variants logged in the decision log?
- [ ] No hidden inputs — env/config touched only at the root or C0 config module?
- [ ] Removal note present per feature card (delete test passes on paper)?
- [ ] Parallel marks + resource math present when the user stated quantities?
- [ ] Each module boundary has one contract-test stub in the implementation checklist?
- [ ] Module count within the Scale Gate bound? (exceeding requires logged evidence)
- [ ] Refactor mode: migration order + cutover checks included?
