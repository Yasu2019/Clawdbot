import wave
import os
import json

audio_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\iatf_training\audio\tpm"
output_json = r"D:\Clawdbot_Docker_20260125\data\workspace\iatf_training\tpm_video\src\scenes.json"

script_info = [
    {"audio": "01_narrator_intro.wav", "image": "factory_audit_board.png", "text": "この監査の一部では、監査員がオペレーターとオペレーター主導のTPMシステムについて話し合っています。"},
    {"audio": "02_auditor_q1.wav", "image": "audit_interview.png", "text": "AJ、先ほど、ボードに記録されているTPMの問題について言及しましたが、もう少し詳しく調べてみたいと思います。"},
    {"audio": "03_aj_a1_part1.wav", "image": "audit_interview.png", "text": "私たちのTPMプロセスは、シフト開始時のチェックから始まります。これは、私たちが行う機械チェックの一例です。"},
    {"audio": "04_aj_a1_part2.wav", "image": "factory_audit_board.png", "text": "メンテナンステクニシャンも、その問題を私の注意を引くためにボードに記録します。"},
    {"audio": "05_auditor_q2.wav", "image": "audit_interview.png", "text": "もう少し詳しく見てみましょう。この機械を見に行ってもいいですか？"},
    {"audio": "06_aj_a2.wav", "image": "audit_interview.png", "text": "問題ありません、これを持って行きましょう。"},
    {"audio": "07_auditor_q3.wav", "image": "audit_interview.png", "text": "では、AJ、ここで実際に何をしているのか教えてください。"},
    {"audio": "08_aj_a3_part1.wav", "image": "machine_check_closeup.png", "text": "このステーションの活動リストを確認します。まず、非常停止ボタンが機能していることを確認します。"},
    {"audio": "09_aj_a3_part2.wav", "image": "machine_check_closeup.png", "text": "また、エアガンのテストも行い、エアが実際に除電されていることを確認します。"},
    {"audio": "10_aj_a3_part3.wav", "image": "machine_check_closeup.png", "text": "次に、ツールを接続して、ツールがここで認識されていることを確認します。"},
    {"audio": "11_auditor_q4.wav", "image": "audit_interview.png", "text": "もしこれらのチェックのいずれかが失敗した場合、どうしますか？"},
    {"audio": "12_aj_a4.wav", "image": "audit_interview.png", "text": "オペレーターはその問題をタブレットに記録し、技術者が確認しに来ます。"},
    {"audio": "13_auditor_finish.wav", "image": "audit_interview.png", "text": "完璧です。ありがとうございました、AJ。"},
    {"audio": "14_narrator_outro.wav", "image": "factory_audit_board.png", "text": "まとめです。組織は文書化された予防保全システムを開発し、実施し、維持する必要があります。"}
]

scenes = []
current_frame = 0
fps = 30

for item in script_info:
    path = os.path.join(audio_dir, item["audio"])
    if not os.path.exists(path):
        print(f"Waiting for {item['audio']}...")
        continue
    
    with wave.open(path, 'rb') as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)
        duration_frames = int(duration * fps) + 10 # Add a small buffer
        
        scenes.append({
            "audio": item["audio"],
            "image": item["image"],
            "text": item["text"],
            "startFrame": current_frame,
            "durationFrames": duration_frames
        })
        current_frame += duration_frames

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(scenes, f, ensure_ascii=False, indent=2)

print(f"Generated {output_json} with {len(scenes)} scenes.")
print(f"Total duration: {current_frame} frames ({current_frame/fps:.2f}s)")
