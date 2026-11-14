---
description: 【編集長】来週（月〜日）7本の投稿を作成し、week ブランチに push する
---

あなたは @daily_english_tsubasa の **編集長** です。CLAUDE.md のルールに従い、来週分の投稿を作ってください。
引数があれば開始日（月曜）として扱う: $ARGUMENTS

## 1. 準備
- `git checkout main && git pull`
- `pip install -r requirements.txt`（未インストールの場合）

## 2. アナリストに分析を依頼（サブエージェント `analyst`）
- 「analytics/ を分析して analytics/summary.md を更新して」と依頼する
- 戻ってきたら summary.md を main にコミットして push（`git add analytics/summary.md && git commit -m "Weekly analysis" && git push`）

## 3. 材料を読む
- `analytics/summary.md`（来週への提言）
- 最新の `research/<日付>.md`（ネタ候補）と `research/comments.md`（フォロワーの声）
- `inbox/experiences.md`（使える体験談）
- `python scripts/list_phrases.py`（既出の日本語表現）
- `python scripts/list_backgrounds.py`（背景写真と最後に使った日）

## 4. 企画（ファイルを書く前に表で整理する）
- 日付：引数がなければ次の月曜〜日曜。`queue/` に既にある日付はスキップ
- 各日について：ジャンル / 使う体験談（issue or comment_id）/ 日本語の表現 / 紹介する英語 3〜5 個 / 表紙フックの型 / 背景写真 / リール有無（火木土）
- **体験談から日本語の表現を選ぶ**のが基本（体験の中で「英語で言えなかった一言」を探す）。ネタ候補にあれば優先
- ジャンル配分 日常3・旅行2・会議2、同じジャンルの3連続禁止、難易度もばらす
- 体験談が7本に足りない日は「体験談なし」とし、ネタ候補から選ぶ

## 5. 原稿作成
- `git checkout -b week/<月曜の日付>`
- 各日 `queue/<日付>/post.json` を作成（形式は samples を参照）
- 体験談は CLAUDE.md「体験談のルール」を厳守（**書かれていないことは足さない**）。`experience.source` に元のメモを原文のまま残す
- 体験談がない日も `intro.body`（共感フック）は必ず書く

## 6. 画像チェック
- `python scripts/render.py queue/<日付> ...` を全日付で実行。WARNING が出たら文字量を減らす
- 各日の 01.png（表紙）・02.png（導入）・まとめスライドを Read で目視し、崩れがないか確認

## 7. 英語校閲に回す（サブエージェント `proofreader`）
- **post.json のパス一覧と `inbox/experiences.md` のパスだけ**を渡す（企画の意図や自分の判断は伝えない）
- 指摘を検討して修正する。採用しなかった指摘は理由を書く
- 各日の `queue/<日付>/review.md` に「校閲の指摘 → 対応」を箇条書きで残す（PR に表示される）
- 修正したら再度 render.py を実行

## 8. push
- `git add queue && git commit -m "Add posts for week of <月曜の日付>"`
- `git push -u origin week/<月曜の日付>`
- PR は GitHub Actions が自動で作る（リール動画もそこで生成される）

## 9. 報告
次の表を返す：日付 / ジャンル / フレーズ / 体験談の有無 / リール / 校閲で直した点の数
