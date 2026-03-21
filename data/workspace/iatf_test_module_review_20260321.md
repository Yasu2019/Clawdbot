# IATF Test Module Review

Date: 2026-03-21
Target: `iatf_system` test-question / answer feature

## Scope

- `app/controllers/touans_controller.rb`
- `app/controllers/touan_collection.rb`
- `app/models/testmondai.rb`
- `app/models/touan.rb`
- `app/views/touans/*.erb`
- `db/schema.rb`
- `db/seeds.rb`
- `test.txt`

## Primary Findings

### 1. `TouanCollection.new` is called with reversed arguments in `TouansController#new`

Relevant files:
- `iatf_system/app/controllers/touans_controller.rb`
- `iatf_system/app/controllers/touan_collection.rb`

Current constructor:

```rb
def initialize(params, selected_testmondais, user)
```

Current call site in `new`:

```rb
@touans = TouanCollection.new(selected_testmondais, @testmondais, @user)
```

Problem:
- `selected_testmondais` is passed as `params`
- `params.present?` becomes true
- initializer tries to read model instances like hashes:
  - `value['kaito']`
  - `value['kajyou']`
- this is structurally inconsistent and can break question generation

Impact:
- quiz generation can silently produce broken `Touan` objects
- later answer submission and scoring become unreliable

Severity: Critical

### 2. Correct-answer counting logic is inconsistent and incorrect in at least one path

Relevant file:
- `iatf_system/app/controllers/touans_controller.rb`

Problematic code:

```rb
correct_answers = Touan.where(mondai_no: testmondai.mondai_no, user_id: @user.id, seikai: true).count
```

Problem:
- `seikai` is stored as `"a"`, `"b"`, `"c"`
- this query assumes boolean `true`
- other parts of the app compare correctly with:

```rb
touan.kaito == touan.seikai
```

Impact:
- low-score question selection in `new`
- review history
- remediation targeting

Severity: Critical

### 3. `seikairitsu` unit is inconsistent between `new`, `create`, and `kekka`

Relevant file:
- `iatf_system/app/controllers/touans_controller.rb`

Observed behavior:
- `new` computes `seikairitsu` as a ratio in `[0,1]`
- `kekka` computes it as percent in `[0,100]`
- views display with `%`

Impact:
- question sampling thresholds are wrong or misleading
- displayed history is inconsistent
- any future analytics will be unreliable

Severity: High

### 4. `mondai` and `kaisetsu` are `string`, not `text`

Relevant file:
- `iatf_system/db/schema.rb`

Current schema:
- `testmondais.mondai`: `string`
- `testmondais.kaisetsu`: `string`
- `touans.mondai`: `string`
- `touans.kaisetsu`: `string`

Impact:
- long question text or explanations can truncate
- CSV imports can silently lose content
- explanation quality is constrained by schema

Severity: High

### 5. CSV import is too weak for production data

Relevant files:
- `iatf_system/app/models/testmondai.rb`
- `iatf_system/app/models/touan.rb`

Problems:
- no header normalization
- no required-column validation
- no row-level error report
- `id`-based upsert only
- no business-key upsert by `(kajyou, mondai_no, rev)` or similar

Impact:
- malformed CSV can import partial garbage
- updates from external files are fragile
- duplicates and accidental overwrite risks are high

Severity: High

### 6. The main quiz controller owns too many responsibilities

Relevant file:
- `iatf_system/app/controllers/touans_controller.rb`

Current responsibilities mixed together:
- quiz generation
- answer submission
- score aggregation
- CSV import/export
- Excel generation
- cache coordination
- IATF/CSR/Mitsui comparison pages

Impact:
- difficult to test
- difficult to refactor safely
- logic defects hide inside unrelated features

Severity: High

### 7. Tests are effectively absent

Relevant files:
- `iatf_system/test/controllers/touans_controller_test.rb`
- `iatf_system/test/models/testmondai_test.rb`
- `iatf_system/test/models/touan_test.rb`

Current state:
- placeholder only
- no import tests
- no scoring tests
- no result-page tests
- no regression coverage for CSV structure

Impact:
- current defects can persist unnoticed
- refactoring risk is high

Severity: High

### 8. Seed import of question bank has no validation or deduplication

Relevant file:
- `iatf_system/db/seeds.rb`

Current logic:
- imports every `db/record/bing/kajyou*.csv`
- creates `Testmondai` rows directly
- no header checks
- no deduplication
- no length validation

Impact:
- low-quality or duplicate questions can enter the bank
- explanation quality and answer correctness can drift

Severity: Medium

### 9. View layer contains mojibake and malformed ERB text

Relevant files:
- `iatf_system/app/views/touans/new.html.erb`
- `iatf_system/app/views/touans/kekka.html.erb`
- `iatf_system/app/views/touans/testmondai.html.erb`
- more broadly across `touans/*`

Impact:
- difficult maintenance
- user-facing text quality is poor
- hidden syntax mistakes become harder to spot

Severity: Medium

## Data Quality Concerns

Based on `test.txt`, external review concerns are aligned with code reality:

- question text quality is likely inconsistent
- explanation quality is likely inconsistent
- CSVs may have:
  - missing columns
  - mixed column order
  - duplicated IDs
  - long text beyond schema limits
- answer key integrity is not strongly validated

## Recommended Review Slices

Do not review the whole Rails app at once. Review in this order.

### Slice 1. Quiz core

- `TouansController`
- `TouanCollection`
- `Touan`
- `Testmondai`
- views:
  - `new`
  - `kekka`
  - `testmondai`

Goal:
- make quiz generation, submission, scoring, and explanation rendering consistent

### Slice 2. CSV import/export

- `Testmondai.import_test`
- `Touan.import_kaitou`
- related upload views
- Excel export paths

Goal:
- robust import contract
- row validation
- dedupe and error reporting

### Slice 3. Schema hardening

- migrate long text columns to `text`
- add indexes and uniqueness constraints where appropriate

Goal:
- prevent truncation and duplicate quiz rows

### Slice 4. Test coverage

- model tests for import and scoring
- controller tests for quiz flow
- fixtures or small seed CSVs for regression coverage

Goal:
- make future refactoring safe

## Suggested First Fixes

1. Fix `TouanCollection.new` call order
2. Unify correct-answer logic to `kaito == seikai`
3. Unify `seikairitsu` representation to percent or ratio, not both
4. Add import validation and row error reporting
5. Change `mondai` / `kaisetsu` to `text`
6. Add minimal regression tests before deeper refactor

## Suggested Deliverables For Refactor Phase

- `app/services/testmondai_import_service.rb`
- `app/services/touan_scoring_service.rb`
- `app/services/touan_selection_service.rb`
- schema migration for `text` columns
- controller slimming
- Minitest coverage for import/scoring/result rendering

## Applied Minimal Fixes

Applied in this round:

- `iatf_system/app/controllers/touans_controller.rb`
  - fixed question selection scoring to use actual answer matching
  - changed `some_threshold_seikairitsu` from `0.5` to `50.0`
  - fixed `TouanCollection.new` call order in `new`
  - unified score storage in `create` to percent (`0..100`)
  - reused shared correct-answer counting in `kekka`

- `iatf_system/app/controllers/touan_collection.rb`
  - rebuilt collection initialization to safely support:
    - submitted param hashes
    - selected `Testmondai` objects
  - changed `save` to return boolean via `all?(&:save)`

- `iatf_system/app/models/touan.rb`
  - added `correct_answer?`
  - added `self.correct_answers_for(...)`

- tests added:
  - `iatf_system/test/models/touan_test.rb`
  - `iatf_system/test/models/testmondai_test.rb`
  - `iatf_system/test/models/touan_collection_test.rb`

## Validation Status

- `ruby -c` syntax check:
  - `app/models/touan.rb` OK
  - `app/controllers/touan_collection.rb` OK
  - `app/controllers/touans_controller.rb` OK
- Rails test execution:
  - not completed
  - blocked by PostgreSQL startup conflict on host port `5433`

## Applied Follow-up Fixes

Applied in the next round:

- added CSV import services:
  - `iatf_system/app/services/csv_import_result.rb`
  - `iatf_system/app/services/testmondai_import_service.rb`
  - `iatf_system/app/services/touan_import_service.rb`
- delegated model import entrypoints to those services:
  - `Testmondai.import_test`
  - `Touan.import_kaitou`
- updated `TouansController#import_test` and `#import_kaitou` to surface import summaries and row errors via flash
- added migration:
  - `iatf_system/db/migrate/20260321094500_change_quiz_text_columns_to_text.rb`
  - changes quiz/explanation and option fields from `string` to `text`
- added import service test:
  - `iatf_system/test/models/testmondai_import_service_test.rb`
