# Blenderリターゲット手順

1. 人型モデルを読み込む
2. Rigifyでメタリグ作成
3. 骨格位置をモデルに合わせる
4. Generate Rig
5. モデルをArmatureへParent with Automatic Weights
6. Mocap BVH/FBXを読み込む
7. ソース骨格とターゲット骨格を対応付け
8. Root位置、足接地、腕回転を確認
9. NLA Editorへカット別に配置
10. 手・指・視線・顔・足滑りを補正

## 補正優先順位
1. 足が滑らない
2. 重心が破綻しない
3. 手が体を貫通しない
4. 視線が合う
5. セリフとジェスチャーが同期する
