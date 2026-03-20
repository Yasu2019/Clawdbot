# Root Cause

## Purpose
- 真因解析と再発防止を、現象、流出、管理要因まで分けて整理する。

## Procedure
1. 現象を再現可能な粒度で定義する。
2. 発生点と流出点を分ける。
3. 物理的原因と管理上の原因を分ける。
4. なぜなぜ分析を 5 段以内で行う。
5. 暫定対策と恒久対策を分ける。
6. 妥当性確認方法と横展開対象を決める。

## Required Fields
- 現象
- 発生点
- 流出点
- 物理的原因
- 管理上の原因
- なぜなぜ分析
- 再現性
- 暫定対策
- 恒久対策
- 妥当性確認
- 横展開
- エビデンス不足欄

## Output Template
```markdown
# Root Cause

## Symptom
- 

## Occurrence Point
- 

## Escape Point
- 

## Physical Cause
- 

## Management Cause
- 

## Why-Why
1. 
2. 
3. 
4. 
5. 

## Reproducibility
- 

## Containment
- 

## Permanent Action
- 

## Validation
- 

## Horizontal Deployment
- 

## Evidence Gaps
- 
```

## Rules
- 真因候補が複数ある場合は、候補ごとに証拠の強さを書く。
- 暫定対策を恒久対策と誤記しない。
- 再発防止は、工程・管理票・教育のどこを変えるかを明記する。
