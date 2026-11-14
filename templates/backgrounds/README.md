# 背景写真フォルダ

ここに入れた写真から、編集長（Claude）が投稿ごとに1枚選んで背景にします。

- 形式：JPG / PNG（横長でも縦長でもOK。自動で 4:5 に切り抜き）
- **ファイル名で中身がわかるように**：`city_newyork_bridge.jpg`、`travel_airport.jpg`、`office_meeting_room.jpg` など
  （英単語・アンダーバー区切り。編集長はファイル名を見て内容に合う写真を選ぶ）
- サブフォルダで分けてもOK：`travel/`、`city/`、`office/`、`nature/` など
- 同じ写真は直近7投稿以内で使い回さない（`python scripts/list_backgrounds.py` で確認）
- 自分で撮った写真、または商用利用OKの素材（Unsplash / Pexels など）を使う
- **有名人・他人が写った写真、ロゴやキャラクターが主役の写真は使わない**（肖像権・著作権のため）

`sample_city_evening.jpg` は動作確認用の仮画像です。写真を追加したら削除してOK。
