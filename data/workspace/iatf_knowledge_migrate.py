#!/usr/bin/env python3
"""
iatf_knowledge コレクション移行スクリプト
nomic-embed-text (768-dim) → mxbai-embed-large-v1 (1024-dim, Infinity)

実行場所: Docker gateway コンテナ内
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/iatf_knowledge_migrate.py
"""
import json, time, requests
from datetime import datetime, timezone

QDRANT_URL   = "http://qdrant:6333"
INFINITY_URL = "http://infinity:7997"
EMBED_MODEL  = "mxbai-embed-large-v1"
COLLECTION   = "iatf_knowledge"
BACKUP_COL   = "iatf_knowledge_768_backup"
BATCH_SIZE   = 10


def embed(texts: list[str]) -> list[list[float]]:
    """Infinityでバッチ埋め込み生成"""
    r = requests.post(
        f"{INFINITY_URL}/embeddings",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()["data"]
    return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]


def get_all_points(collection: str) -> list[dict]:
    """コレクション全ポイント取得"""
    points = []
    offset = None
    while True:
        payload = {"limit": 100, "with_payload": True, "with_vector": False}
        if offset:
            payload["offset"] = offset
        r = requests.post(
            f"{QDRANT_URL}/collections/{collection}/points/scroll",
            json=payload, timeout=30
        )
        r.raise_for_status()
        result = r.json()["result"]
        points.extend(result["points"])
        offset = result.get("next_page_offset")
        if not offset:
            break
    return points


def collection_exists(name: str) -> bool:
    r = requests.get(f"{QDRANT_URL}/collections/{name}", timeout=10)
    return r.status_code == 200


def create_collection_1024(name: str):
    """1024-dim コレクション作成"""
    r = requests.put(
        f"{QDRANT_URL}/collections/{name}",
        json={"vectors": {"size": 1024, "distance": "Cosine"}},
        timeout=30
    )
    r.raise_for_status()
    print(f"  コレクション作成: {name} (1024-dim, Cosine)")


def upsert_batch(collection: str, points: list[dict]):
    r = requests.put(
        f"{QDRANT_URL}/collections/{collection}/points",
        json={"points": points},
        timeout=60
    )
    r.raise_for_status()


def main():
    print("=" * 60)
    print("iatf_knowledge 移行: 768-dim → 1024-dim (mxbai-embed-large-v1)")
    print("=" * 60)

    # Step 1: 現コレクション確認
    print("\n【Step 1】現コレクション確認")
    if not collection_exists(COLLECTION):
        print(f"  エラー: {COLLECTION} が存在しません")
        return

    r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=10)
    info = r.json()["result"]
    current_dim = info["config"]["params"]["vectors"]["size"]
    point_count = info["points_count"]
    print(f"  現在: {current_dim}-dim, {point_count}件")

    if current_dim == 1024:
        print("  既に1024-dim。移行済みです。")
        return

    # Step 2: 全ポイント取得
    print(f"\n【Step 2】全ポイント取得 ({point_count}件)")
    old_points = get_all_points(COLLECTION)
    print(f"  取得完了: {len(old_points)}件")

    # Step 3: バックアップコレクション作成
    print(f"\n【Step 3】バックアップ作成: {BACKUP_COL}")
    if not collection_exists(BACKUP_COL):
        r = requests.put(
            f"{QDRANT_URL}/collections/{BACKUP_COL}",
            json={"vectors": {"size": current_dim, "distance": "Cosine"}},
            timeout=30
        )
        r.raise_for_status()
        print(f"  バックアップコレクション作成完了")
    else:
        print(f"  バックアップ既存 → スキップ")

    # Step 4: 旧コレクション削除 → 新コレクション作成
    print(f"\n【Step 4】{COLLECTION} 削除 → 1024-dim で再作成")
    requests.delete(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=30)
    time.sleep(1)
    create_collection_1024(COLLECTION)

    # Step 5: 再埋め込み + upsert
    print(f"\n【Step 5】再埋め込み + upsert ({len(old_points)}件, batch={BATCH_SIZE})")
    success = 0
    errors = 0

    for i in range(0, len(old_points), BATCH_SIZE):
        batch = old_points[i:i + BATCH_SIZE]
        texts = [p["payload"].get("text", "") or p["payload"].get("content", "") for p in batch]

        # 空テキストのフィルタ
        valid = [(p, t) for p, t in zip(batch, texts) if t.strip()]
        if not valid:
            continue

        batch_points, batch_texts = zip(*valid)

        try:
            vectors = embed(list(batch_texts))
            upsert_data = [
                {
                    "id": p["id"],
                    "vector": v,
                    "payload": {
                        **p["payload"],
                        "migrated_at": datetime.now(timezone.utc).isoformat(),
                        "embed_model": EMBED_MODEL,
                    }
                }
                for p, v in zip(batch_points, vectors)
            ]
            upsert_batch(COLLECTION, upsert_data)
            success += len(upsert_data)
            print(f"  [{i+len(batch)}/{len(old_points)}] {success}件完了", end="\r")
        except Exception as e:
            print(f"\n  バッチエラー [{i}]: {e}")
            errors += 1
            time.sleep(2)

    print(f"\n\n  完了: 成功={success}件 / エラーバッチ={errors}件")

    # Step 6: 確認
    print(f"\n【Step 6】移行後確認")
    r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=10)
    info = r.json()["result"]
    print(f"  {COLLECTION}: {info['config']['params']['vectors']['size']}-dim, {info['points_count']}件")
    print(f"  バックアップ: {BACKUP_COL} (768-dim, 削除は手動で: DELETE /collections/{BACKUP_COL})")

    print("\n" + "=" * 60)
    print("移行完了!")
    print("=" * 60)


if __name__ == "__main__":
    main()
