---
description: 【マーケティング部】リサーチャーに来週のネタ候補を調べさせ、research/ に保存して push する
---

1. `git checkout main && git pull`
2. サブエージェント `researcher` に依頼する：
   「次の月曜（JST）から始まる週のネタ候補を調べ、research/<次の月曜の日付>.md に書いて」
3. 戻ってきたファイルを確認し、形式（特に `## 体験談の呼び水` セクション）が守られているか見る
4. `git add research && git commit -m "Research for week of <日付>" && git push`
   （main への push をきっかけに、Actions が「ネタ候補」Issue を自動で作る）
5. ネタ候補の上位5つと、呼び水の質問を一覧で報告する
