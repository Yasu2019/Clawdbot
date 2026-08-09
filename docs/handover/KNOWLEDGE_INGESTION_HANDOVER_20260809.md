# 資料の読み込み(知識取り込み) 引き継ぎ — 2026-08-09

作成: Claude Opus 5 / 引き継ぎ先: 別AIモデル
前提: すべての数値は 2026-08-09 時点の**実測値**。推定値・伝聞は含めない。

---

## 0. 最初に知っておくべき「罠」

**この領域の数字はほぼすべて額面どおりではない。** 実際に踏んだものを列挙する。

| 見かけ | 実体 | 原因 |
|---|---|---|
| 収集資料 302,845件 | **一意 5,591件** | `(source, external_id)` に一意制約が無く無条件INSERT |
| PDF 98,107件 / 310GB | **一意 971件 / 4.86GB** | 同上（同一PDFが最大1,596行） |
| DB 38GB | 中身の**35.15GBは1テーブル** | `dxf2step_trial_analyses.analysis_json` のFMEA累積バグ |
| `enrichment_status='summarized'` 179,795件 | **要約本文はどこにも無い** | 要約したという記録だけ。保存列が存在しない |
| ダッシュボード「30万件収集」 | 実態の約1/100 | 上記重複がそのまま表示されていた（修正済み） |

**教訓: 件数を報告する前に必ず `COUNT(DISTINCT ...)` を取ること。**

---

## 1. 現状（2026-08-09 実測）

### 1.1 SQLite: `data/workspace/universal_growth.db`

| テーブル | 件数 | 備考 |
|---|---|---|
| `growth_records` | 71,105 | **本物の資産。** 10本以上のスクリプトが実際に読んでいる |
| `web_material_index` | 5,938 | 重複排除後。正常収集中 |
| `public_api_acquisitions` | 5,938 | UNIQUE制約により重複0を維持 |
| うち実ファイル保有 | 2,077 | PDF/zip/json等 |

`growth_records.know_how` の長さ分布（重要）:

| 長さ | 件数 | 実質 |
|---|---|---|
| 50〜200字 | 61,849 | **88%がスタブ**。索引価値が低い |
| 200〜1000字 | 4,074 | 使える |
| **1000字以上** | **508** | **本物の解説**（最大10,805字のIATF 16949監査解説など） |

### 1.2 Qdrant（意味検索）: `http://localhost:6333`

| コレクション | 点数 | 中身 |
|---|---|---|
| `clawstack_docs` | 803 | **今回新設。** リポジトリMD 11ファイル分 |
| `universal_knowledge` | 1,236 | Paperless PDF 1,234 + RLスキル2。**リポジトリMDは0件** |
| `iatf_knowledge` | 99 | |
| `obsidian_knowledge` | 58 | |
| `lightrag_vdb_chunks_*` | **0** | ← 未稼働 |
| `lightrag_vdb_entities_*` | **0** | ← 未稼働 |

### 1.3 日本語FTS索引（今回新設）: `data/workspace/universal_growth_fts_ja.db`

| テーブル | 件数 | 内容 |
|---|---|---|
| `material_ja` | 302,946 | 収集資料のタイトル（重複排除前に構築したため件数が多い） |
| `knowhow_ja` | 4,582 | `growth_records.know_how` 200字以上 |
| `pdftext_ja` | 2,933 | PDF本文（J-STAGE中心） |

PDF抽出の内訳: `ok 73 / mojibake 3 / empty 2`（`done_pdf` テーブル。同一パスが多数の行に対応するため件数差あり）

---

## 2. 未解決の課題（引き継ぎの主題）

### 2.1 最優先: 埋め込みサーバ Infinity が存在しない

```
docker ps -a | grep infinity  -> 存在しない（停止ですらなく未作成）
curl http://127.0.0.1:4001/v1/embeddings -> HTTP 500
```

`docker-compose.yml` の 557行目に定義はあるが、イメージ `michaelf34/infinity:latest` が未取得。
**これが LightRAG が0件である直接原因**（LightRAG は `embedding_binding_host: http://infinity:7997` を見ている）。

暫定回避として、稼働中の Ollama に同一モデル `mxbai-embed-large`（1024次元）を導入済み。
既存コレクション（`universal_knowledge` / `iatf_knowledge` も1024次元）と次元が揃う。

**性能の実測値（重要な制約）**

| 条件 | 速度 |
|---|---|
| 450文字/チャンク、16件バッチ | **約2.0秒/件（30チャンク/分）** |
| 短い入力（数文字） | 0.5秒 |
| `keep_alive` 指定 | **効果なし**（モデル再ロードが原因ではない） |
| CPU/GPU | **どちらも同程度**（GPUにしても速くならない） |

→ リポジトリMD 8,235ファイル（推定数万チャンク）の全件取り込みは**現状の速度では非現実的**。
Infinity（バッチ最適化された専用サーバ）の復旧が本筋。

### 2.2 リポジトリMDの取り込みが11ファイルで止まっている

取り込み済み（`data/state/ingest_repo_docs_manifest.json`）:

```
CLAUDE.md
data/workspace/PROMISES.md
data/workspace/memory/trouble_history.md      (312チャンク・最重要)
data/workspace/memory/success_cases.md        (86チャンク)
data/workspace/memory/plan_postgres_wal_repair_20260702.md
data/workspace/memory/stale_legacy_task_confirmation_rule.md
data/workspace/knowledge/openradioss/lessons.md
data/workspace/knowledge/openradioss/fmea_log.md
data/workspace/knowledge/openradioss/qc_process_chart.md
docs/quality_analysis_protocol.md
docs/cae_north_star_and_meaning_gate_protocol.md
```

未取り込み: `docs/`(314) `protocols/`(137) `clawstack_v2/`(224) `projects/`(89)
`data/workspace/obsidian_vault/`(4,654) など計 8,000件超。

### 2.3 PDF本文の抽出が一部のみ

実PDF 971件（一意）のうち、索引化は J-STAGE 中心の一部。
`pdftotext -enc UTF-8` は **0.35〜0.67秒/PDF**、4並列で **116件/分** と高速なので、
残りの抽出はGPU不要・短時間で完了できる。**ここは費用対効果が高い。**

### 2.4 収集コーパスの質（方針判断が必要）

北極星（プレス/金型）関連の該当率を実測した:

| source | PDF数 | 関連 | 該当率 |
|---|---|---|---|
| **jstage** | 7,745行 | 5,099 | **65.8%** |
| unpaywall | 550 | 292 | 53.1% |
| semantic_scholar | 377 | 155 | 41.1% |
| europe_pmc | 23,267 | 6,128 | 26.3% |
| zenodo | 38,674 | 5,121 | 13.2% |
| arxiv | 27,494 | 2,082 | 7.6% |
| 全体 | 98,107 | 18,877 | **19.2%** |

※ これは重複排除**前**の行数ベース。一意ファイルでは母数が1/100になる。

- 日本語を含むタイトルは全体の **2.9%**、しかもサンプルは中国語が混じる
- `metadata_json` のキーは `query / publication_year / cited_by_count / open_access` のみで、
  **abstract すら保存していない**

→ 収集を続けるなら、(a) J-STAGE等の高該当率ソースに絞る (b) abstractを保存する
のどちらかを実装しないと、量が増えても検索価値は上がらない。

---

## 3. 使えるツール（すべて動作確認済み）

すべて `D:\Clawdbot_Docker_20260125\scripts\` 配下。

### 3.1 意味検索（推奨・最初に使う）

```bash
python scripts/search_docs.py "<症状や対象>"
python scripts/search_docs.py "GPU VRAM競合で学習が落ちた時の対処" --top 5
```

実績: 「VRAM競合」の質問で T077 の該当インシデントを score 0.72 で特定。
対処法（n-envs 6144→4096、残留プロセスtaskkill）まで到達した。

**CLAUDE.md のグローバルルールとして「着手前にこれを実行する」が制定済み。**

### 3.2 リポジトリMDの取り込み

```bash
python scripts/ingest_repo_docs.py --stats
python scripts/ingest_repo_docs.py --roots docs protocols
python scripts/ingest_repo_docs.py --dry-run
```

- 冪等（point ID は `uuid5(相対パス#チャンク番号)`）
- 差分更新（sha256をマニフェストに記録）
- 中断・再開可能（ファイル単位でflush後にマニフェスト保存）
- 埋め込みは既定でCPU実行（`EMBED_NUM_GPU=0`）。GPU学習中にVRAMを奪わないため

### 3.3 日本語FTS索引

```bash
python scripts/build_ja_fts_index.py          # 増分構築
python scripts/build_ja_fts_index.py --stats
```

**制約: trigramは3文字以上でないとマッチしない。**
実測: 「順送」(2文字)=0件 / 「順送金型」(4文字)=1件 / 「内部監査」=221件 / 「是正処置」=50件

索引は**別ファイル**に作る。本体38GBは収集デーモンが常時書き込み中のため
read-onlyでしか開かない。不要なら索引ファイルを消すだけで完全に元に戻る。

### 3.4 PDF本文の抽出・索引化

```bash
python scripts/extract_pdf_text_index.py --pattern jstage --workers 4
python scripts/extract_pdf_text_index.py --stats
python scripts/extract_pdf_text_index.py --verify
```

- `pdftotext -enc UTF-8` を使用（`/mingw64/bin/pdftotext` に実在）
- 化け率が閾値を超えた文書は索引に入れない（検索ノイズ防止）
- 中断・再開可能（`done_pdf` テーブル）

### 3.5 MD書き出し

```bash
python scripts/export_knowledge_md.py --what knowhow
python scripts/export_knowledge_md.py --what pdf --limit 500
```

出力先: `data/workspace/knowledge_export/`
書き込み後に読み戻して `U+FFFD` と化け記号の混入を検証し、
**検証に失敗したファイルは削除する**（壊れたMDを残さない）。

### 3.6 重複掃除

```bash
python scripts/dedupe_acquisitions.py            # dry-run（既定）
python scripts/dedupe_acquisitions.py --apply --vacuum
```

**既定はdry-run。** 収集デーモン稼働中は自動で中止する（走行中の削除は整合を壊すため）。

---

## 4. 厳守すべきルール（CLAUDE.md に制定済み）

### 4.1 文字化け防止（2026-08-08 グローバルルール）

- Python: `open(..., encoding="utf-8")` を**必ず指定**（既定はcp932）
- PowerShell: `Get-Content`/`Set-Content`/`Add-Content`/`Out-File` に `-Encoding utf8` 必須
- DB投入後は1件読み戻して往復検証
- 検証は `U+FFFD` と化け記号（`縺`/`繧`/`繝`）の混入数で判定
- **表示の化けと実体の破損を混同しない。**
  実証: `services/comfyui/Dockerfile` はコンソール上 `GPU縺ｪ縺礼腸蠅・` と化けるが、
  実体は `GPUなし環境向け` で正常なUTF-8。判定は
  `open(f,"rb").read().decode("utf-8")` の可否で行う

### 4.2 着手前に蓄積知識を検索する（2026-08-08 グローバルルール）

`python scripts/search_docs.py "<対象>"` を実行してから着手する。
「確認する」という努力目標では読まれないため、コマンド実行として固定した。

---

## 5. 推奨する進め方

| 優先 | 作業 | 所要 | 効果 |
|---|---|---|---|
| 1 | **PDF本文の残り抽出**（`extract_pdf_text_index.py --workers 4`） | 短時間・GPU不要 | 一意971件の中身が全文検索可能に |
| 2 | **Infinity コンテナ復旧**（`docker compose up -d infinity`） | イメージpull数GB | 埋め込みが2秒/件から改善。LightRAGも動き出す |
| 3 | Infinity復旧後に**リポジトリMDの全件取り込み** | 速度次第 | `docs`/`protocols`/`obsidian_vault` が意味検索可能に |
| 4 | **収集方針の見直し**（高該当率ソースへ絞る / abstract保存） | 設計判断 | 量ではなく質を上げる |

**1 を先にやるべき理由**: GPUを使わず、依存もなく、すぐ価値が出る。
2 は数GBのダウンロードを伴うので、ユーザー承認を得てから。

---

## 6. 注意: GPUの共有

単一 RTX 5060 Ti 16GB を RL学習・CAE・ComfyUI・埋め込みが共有する。
MIG非対応のため**時分割で調停**する。

```bash
python scripts/gpu_arbiter.py status
python scripts/gpu_arbiter.py acquire --owner <名前> --priority 0 --ttl 3600 --nonpreemptible
python scripts/gpu_arbiter.py release --owner <名前>
```

- 埋め込みは既定でCPU実行なので、通常は学習と競合しない
- リース保持者が死んでもTTLとPID死活で自動回収される
- 2026-08-09 現在、RL歩行のA/B実験が `rl_ab_experiment` でリースを保持中

---

## 7. 関連ファイル

| 種別 | パス |
|---|---|
| 本体DB | `data/workspace/universal_growth.db` |
| 日本語FTS索引 | `data/workspace/universal_growth_fts_ja.db` |
| 取り込みマニフェスト | `data/state/ingest_repo_docs_manifest.json` |
| MD書き出し先 | `data/workspace/knowledge_export/` |
| 実PDF | `data/public_api_downloads/{arxiv,europe_pmc,jstage,zenodo}/` |
| 収集スクリプト | `scripts/public_api_bulk_harvest.py` |
| 索引投入スクリプト | `scripts/index_web_materials_db.py` |
| ダッシュボード | `http://localhost:8088/apps/growth_dashboard/index.html` |

関連コミット: `9d6823d45e`（重複バグ修正）、`d8ee3a456e`（検証ツール）
