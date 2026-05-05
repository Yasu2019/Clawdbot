"""
台本をモーションタグ候補に変換する簡易ツール。
LLMに渡す前の下処理用。完全自動ではなく候補作成。
"""
import re
import sys

RULES = [
    (r"歩|入る|移動|近づ", "walk"),
    (r"走", "run"),
    (r"座", "sit"),
    (r"立", "stand"),
    (r"驚|びっくり", "surprised"),
    (r"怒", "angry"),
    (r"笑|嬉", "happy"),
    (r"指|示す", "pointing"),
    (r"拾|取|持", "pick_up"),
    (r"話|説明|会話", "talking_gesture"),
    (r"見る|視線", "look_at"),
]


def tag_line(line):
    tags = []
    for pattern, tag in RULES:
        if re.search(pattern, line):
            tags.append(tag)
    return sorted(set(tags))


def main():
    text = sys.stdin.read()
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        tags = tag_line(line)
        print(f"{i},{line},{'|'.join(tags)}")

if __name__ == "__main__":
    main()
