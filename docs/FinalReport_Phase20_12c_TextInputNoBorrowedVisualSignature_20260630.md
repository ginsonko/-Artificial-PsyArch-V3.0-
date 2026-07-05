# Phase20.12c 纯文本输入视觉签名借取泄漏修复

Date: 2026-06-30

## 1. Problem

After teaching apple/banana via image, a pure-text question "你是谁?" (no image,
never taught) answered "是香蕉". Any pure-text question echoed the most-recently-
taught visual item. Whitepaper §269 names this "最近答案覆盖": "如果系统总是说
最近教过的词,那不是 AP,是最近答案覆盖".

Clean repro (verified): empty DB → teach "image banana + 这是什么? -> 是香蕉" →
ask pure-text "你是谁?" → answered "是香蕉", B0 support 0.909, fired
`visual_imagination_recall`.

## 2. Root Cause (runtime.py:399-407)

Pure-text input "你是谁?" had no image this tick →
`visual_signature = _visual_signature_from_events() = None` →
`_select_backward_attribution` borrowed the historical banana window's
visual_signature → assigned to the current observation (line 407) →
`_record_text_observation` persisted the borrowed signature → three downstream
leaks:

1. `_find_exact_b0` saw `observation.visual_signature` non-None → took the
   `_find_visual_exact_b0` branch → matched the banana visual memory → output
   "是香蕉";
2. `_select_visual_imagination_recall` fired a `visual_imagination_recall` tick;
3. `_observation_is_visual_reference_family` returned True → relaxed the B0
   text-match threshold.

One borrow caused a triple leak. The root was the unconditional borrow at
runtime.py:406-407.

## 3. Whitepaper Basis

- §16.1: "视觉感受器把图像/画布/桌面区域转为视觉 SAOccurrence" — a visual signature
  comes only from THIS tick's visual receptor input. The whitepaper never
  authorises a pure-text observation borrowing a visual signature from a
  historical window as current perception.
- §269: "如果系统总是说最近教过的词,那不是 AP,是最近答案覆盖" — the whitepaper name
  for this failure mode.
- §1210: "看到苹果图却召回香蕉词,产生违和. C_backward 应……找历史上导致这种现状的前因
  ……如果该解释被教师纠正,这条归因关系被惩罚" — C_backward *attributing* "我可能受刚教
  香蕉影响" is legitimate, but that attribution must NOT become the answer output.
  The bug fed the borrowed signature straight to B0, turning "the last-taught
  banana" into "the current answer".

## 4. Adversarial Self-Review (the key step)

### 4.1 First plan (delete the borrow outright) was too broad

Adversarial self-review item 5 ("do any tests depend on the borrow?") was
answered wrong by grepping only `assert.*visual_signature`. Two stage5 tests
depend on the borrow *behaviourally*:

- `test_stage5_text_reference_can_trace_back_to_recent_visual`: pure-text
  "刚刚图片是啥" taught "绿色橙子"; a later turn with the SAME orange image recalled
  "绿色橙子". Pre-fix tick2 borrowed the orange signature → the alignment recorded
  a visual signature → tick3's image matched it. Deleting the borrow outright
  broke tick3's recall.
- `test_stage5_idle_visual_focus_follows_latest_visual_imagination_not_last_image`:
  pure-text "苹果" must fire `visual_imagination_recall` and steer idle to
  `idle_visual_focus`.

Deleting outright broke legitimate §1210 visual reference.

### 4.2 Distinguishing legitimate vs illegitimate borrow (measured)

| scenario | backward source_kind | query vs visual-memory output overlap | borrow? |
|---|---|---|---|
| "刚刚图片是啥" (legit, refers to just-seen image) | recent_visual_window | 0.0 (refers to image, not output text) | yes |
| "苹果" (legit, refers to taught apple) | recent_text_window | 0.435 (>=0.34) | yes |
| "你是谁?" (illegit, recent-answer-cover) | recent_text_window | 0.091 (<0.34) | no |

Two legitimate references:
1. `recent_visual_window` hit — the query landed on a visual window, e.g.
   "刚刚图片是啥" referring to the just-seen image;
2. the query has semantic overlap >= 0.34 (same threshold as
   `_select_visual_imagination_recall`) with the output of some visual-signatured
   alignment, e.g. "苹果" referring to the taught apple visual memory.

The illegitimate case satisfies neither.

### 4.3 Key finding: _select_visual_imagination_recall does not need the borrowed signature

Measured: with `observation.visual_signature=None`,
`_select_visual_imagination_recall` returns True for "苹果" (overlap 0.435 passes)
and False for "你是谁?" (overlap 0.091 fails). It works via
`_semantic_text_overlap_with_units`, independent of the borrowed signature. The
problem was solely `_find_visual_exact_b0` depending on the borrowed signature for
a direct hit.

## 5. Fix (no new entity, existing structures only)

**runtime.py:399-407**: replaced the unconditional borrow with a conditional one,
adding a `_text_query_refers_to_visual_memory` predicate that only reads existing
`experience_alignment` rows:

```python
if (
    backward_attribution is not None
    and backward_attribution.observation.visual_signature
    and _text_query_refers_to_visual_memory(
        conn, query_text=user_text.strip(), session_id=session_id,
        backward_source_kind=backward_attribution.source_kind,
    )
):
    visual_signature = backward_attribution.observation.visual_signature
```

`_text_query_refers_to_visual_memory`:
- returns True if `backward_source_kind == "recent_visual_window"` (§1210 visual-
  window reference);
- otherwise scans visual-signatured experience_alignments with the existing
  `_semantic_text_overlap_with_units` (same 0.34 threshold as
  `_select_visual_imagination_recall`) and returns True if any overlap passes;
- calls `_unified_experience_candidates_for_observation` with a temporary
  visual_signature=None observation to avoid a circular dependency (it must not
  assume the signature exists in order to decide whether to borrow it).

`backward_attribution` is still computed regardless of whether the borrow happens,
for the §1160 C_backward attribution rows (`c_backward_rows` uses the
backward_attribution's own recovered observation, decoupled from the current
observation's visual_signature) and the ssp_summary backward_reference.

## 6. Acceptance

Run from the `APV3.0test` root:

- `python -m py_compile apv3test/runtime/phase20_7/runtime.py` — BYTE_COMPILE_OK;
- `node --check apv3test/web/static/phase20_7_workbench.js` — NODE_CHECK_OK;
- `python scripts/red_line_check_v14.py` — zero hits;
- `python -m pytest -q tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py`
  — 5 passed;
- regression suite (16 files, 74 tests): stage1/2/3/5/6, 8e/8h/8i/8j, 9i, 10l/10m,
  11 (L1), 12 (L2 C_forward), 12b (L2 C_backward), 12c (this fix) —
  **74 passed in 45.99s** (including the two stage5 tests that the first too-broad
  plan had broken);
- three-scenario manual repro: "你是谁?"→"我还不太知道怎么说。" (illegit borrow
  blocked); "刚刚图片是啥"+image recall→"绿色橙子" (legit visual-window borrow
  kept); "苹果"→imagination fires (legit overlap borrow kept).

## 7. Boundaries

This step can prove:
- a pure-text input that does not semantically refer to a visual memory no longer
  borrows a historical visual signature (§16.1), so the §269 "最近答案覆盖" leak on
  that path is gone;
- an untaught pure-text question correctly requests the teacher;
- the two legitimate §1210 visual-reference paths (recent_visual_window hit;
  overlap >= 0.34 with a visual memory) still borrow and still work;
- image-input visual teaching does not regress;
- no completion claims are emitted.

This step cannot yet claim:
- that the borrowed signature always selects the *semantically intended* visual
  memory (the borrow still takes the backward_attribution's selected window
  signature; for "苹果" after teaching apple then banana, the selected window is
  the most-recent banana window, so the borrowed signature is banana's — this is
  a pre-existing limitation of the borrow's window selection, not introduced by
  this fix and not the reported bug);
- complete L1/L2/L3 online embedding;
- complete six-stage runtime; complete paradigm self-learning; object-centric
  visual imagination completion; Phase21 visual teaching generalisation closure.

## 8. Next Step

The runtime learning boundary returns to **L3 action-consequence online embedding**
(§173.2 "L3 行动后果与奖惩, 帮 action competition"; §173.7 "最后实现 L3, 接 action
competition"): fill the existing `vector_l3` column the same no-new-entity way —
triplet/annealed updates driven by action outcome (reward/punish) in the
experience flow, injected as a modulation on `action_competition` drive, with a
rebuildable `l3_vector_index/v1` and the same far-text no-leak / no-completion
guardrails.
