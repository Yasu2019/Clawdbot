# Claude Code Prompt: Compile Multi Source

複数の raw 文書を横断して、共通点・相違点・矛盾点を整理し、
1つの統合ノートを作成してください。

要件:
1. 出典の異なる主張を混同しない
2. 共通する事実を先に整理する
3. 相違点と矛盾点を明示する
4. 未確認事項は未確認として残す
5. wiki/topic 用のMarkdownにする

必須見出し:
- Summary
- Shared Facts
- Differences
- Contradictions
- Working Hypotheses
- Open Questions
- Related Notes
- Sources
