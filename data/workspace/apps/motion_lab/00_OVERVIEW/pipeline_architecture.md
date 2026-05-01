# 全体アーキテクチャ

```text
YouTube動画/台本
  ↓
文字起こし・字幕抽出
  ↓
DeepSeek Pro: 秒単位の動作表
  ↓
短尺カット作成
  ↓
FreeMoCap / Rokoko Vision / Mixamo
  ↓
BVH/FBX
  ↓
Blender + Rigify + Retarget
  ↓
NLA Editorで動作合成
  ↓
手・指・視線・口・接地補正
  ↓
映画風レンダリング
  ↓
DaVinci Resolve Freeで編集
```

## 成功の原則
- AIに「自然に動かして」と丸投げしない
- 台本を「動作命令表」に変換する
- 1カットは3〜15秒に分割する
- 全身が見える参考動画を使う
- 足滑り、指、目線、顔向きだけは最後に人間が確認する
