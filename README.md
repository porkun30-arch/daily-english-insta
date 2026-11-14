# daily-english-insta

Instagram **@daily_english_tsubasa** を AI 社員チームで運用するリポジトリです。

- 毎朝 7:00：カルーセル（9〜10枚）を自動投稿
- 火・木・土 21:00：音声付きリールを自動投稿
- 水曜：リサーチャーがネタ候補と「体験談の呼び水」Issue を作成
- 土曜：アナリストが分析 → 編集長が7本作成 → 英語校閲 → PR
- つばさの仕事：**体験談をメモ／PR を確認してマージ**だけ

```
水 20:00  [Actions] 反応データ・コメント取得
水 21:00  [Claude] リサーチャー → research/*.md → 「ネタ候補」Issue 自動作成
水〜金    [つばさ] Issue に体験談を一言コメント（いつでも「体験談」Issue も作れる）
土 06:00  [Actions] 反応データ・体験談を inbox/ に取り込み
土 08:00  [Claude] アナリスト → 編集長 → 英語校閲 → week/* ブランチに push
          [Actions] 画像・リール動画を生成して PR 作成
〜月 07:00 [つばさ] スマホで確認、体験談なしの日は追記 → マージ
毎日      [Actions] 07:00 カルーセル / 火木土 21:00 リール
1日・15日 [Actions] Instagram トークン延長
```

---

## セットアップ（初回だけ・1〜2時間）

### 1. GitHub リポジトリ
1. GitHub で **公開** リポジトリ `daily-english-insta` を作成（README なしの空で）
2. この ZIP を展開したフォルダを VS Code で開き、ターミナルで：
   ```bash
   git init && git add -A && git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<ユーザー名>/daily-english-insta.git
   git push -u origin main
   ```
3. **Settings → Pages**：Source を「Deploy from a branch」、Branch を `main` / `(root)` に
   → 表示される URL（`https://<ユーザー名>.github.io/daily-english-insta`）を控える
4. **Settings → Actions → General → Workflow permissions**：
   「Read and write permissions」と「Allow GitHub Actions to create and approve pull requests」に✓
5. **Settings → Secrets and variables → Actions → Variables** に追加：
   - `PAGES_BASE_URL` = 手順3の URL（末尾スラッシュなし）

### 2. Instagram API（Meta for Developers）
1. https://developers.facebook.com/ で「アプリを作成」→ ユースケースで Instagram の
   **「Instagram API（Instagramログイン）」** を選ぶ
2. 「API設定」で @daily_english_tsubasa を追加し、**アクセストークンを生成**
   - 必要な権限：`instagram_business_basic` / `instagram_business_content_publish` /
     `instagram_business_manage_comments` / `instagram_business_manage_insights`
   - 自分のアカウントだけで使う場合は、通常アプリレビューは不要（開発モードのまま）
3. Secrets に追加：`IG_ACCESS_TOKEN` = 生成したトークン
4. **Actions → publish → Run workflow** で kind=`whoami` を実行 → ログに出る `user_id` を
   Secrets の `IG_USER_ID` に追加

### 3. 音声（Google Cloud Text-to-Speech）
1. https://console.cloud.google.com/ でプロジェクトを作成
2. 「Cloud Text-to-Speech API」を有効化
3. 「認証情報」→ API キーを作成 → **キーの制限で Text-to-Speech API のみに限定**
4. Secrets に追加：`GOOGLE_TTS_API_KEY`
   （声は `templates/style.json` の `voices` で変更可）

### 4. トークン自動延長用の GitHub トークン
1. GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate
2. Repository access：`daily-english-insta` のみ ／ Permissions：**Secrets: Read and write**
3. Secrets に追加：`GH_PAT`

### 5. 動作テスト
1. `samples/2026-11-17` を `queue/<今日の日付>` にコピーし、`post.json` の `date` を今日に変更して main に push
2. **Actions → publish → Run workflow**（kind=carousel, date=今日, **dry_run=✓**）→ 画像URLが表示されればOK
3. 問題なければ dry_run を外して実行 → Instagram に投稿される
   （テスト後、不要なら Instagram 側で削除）

### 6. AI 社員の定期実行（Claude のスケジュールタスク）
リポジトリ作成後、Claude に「スケジュールタスクを登録して」と頼めば設定します。内容は：
- **水曜 21:00**：`/research-week` を実行
- **土曜 08:00**：`/generate-week` を実行
手動で動かす場合は、VS Code の Claude Code で同じコマンドを実行してください。

### 7. Instagram プロフィール
企業案件の窓口として、プロフィールに **仕事用のメールアドレス**（連絡先ボタン）を設定。
`analytics/media_kit.md` の「お問い合わせ」にも同じものを記入。

---

## 毎週やること（つばさ）
| いつ | やること |
|---|---|
| 思いついたとき | GitHub アプリで **New issue →「体験談メモ」** に一言 |
| 水曜の夜〜金曜 | 「来週のネタ候補」Issue を見て、心当たりにコメント |
| 土曜〜月曜 7:00 | PR を確認。⚠️体験談なしの日は `post.json` の `experience.text` に追記 → **マージ** |
| 毎朝 7:00〜 | 通勤中にコメント返信（ここは手動の方が伸びる） |

- 1日だけ出したくない → PR でその日のフォルダを削除してからマージ
- マージしなかった日は投稿されない（未承認のものは絶対に出ない）

## ファイル
| パス | 中身 |
|---|---|
| `CLAUDE.md` | 方針・体験談ルール・品質ルール（AI 社員が毎回読む） |
| `.claude/commands/` | 編集長 `/generate-week`、`/research-week` |
| `.claude/agents/` | 英語校閲・アナリスト・リサーチャー |
| `scripts/render.py` | post.json → カルーセル画像 |
| `scripts/make_reel.py` | post.json → 音声付きリール（`--silent` で音声なし確認） |
| `scripts/publish.py` | Instagram へ投稿 |
| `scripts/insights.py` | 反応データ・メディアキット |
| `scripts/gh_tasks.py` | Issue / PR 処理 |
| `templates/style.json` | 色・フォント・投稿時刻・リール曜日・音声 |

## ローカルで画像を確認する
```bash
pip install -r requirements.txt
python scripts/render.py samples/2026-11-17
python scripts/make_reel.py --silent samples/2026-11-17   # ffmpeg が必要
```

## 困ったとき
- **投稿されない**：Actions → publish のログを確認。「queue にありません」なら PR 未マージ
- **画像URLにアクセスできません**：Pages の設定と `PAGES_BASE_URL` を確認
- **トークン期限切れ**：手順2で再発行して `IG_ACCESS_TOKEN` を上書き
- **ハッシュタグ関連のエラー**：6個以上入っていないか確認（上限5）
- 投稿時刻・リール曜日を変える：`publish.yml` の cron と `style.json` の `reel_weekdays`
