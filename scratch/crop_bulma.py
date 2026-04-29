from PIL import Image
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\character_sheet.png'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_front_only.png'

if os.path.exists(src_path):
    img = Image.open(src_path)
    width, height = img.size
    
    # 3面図（前・横・後）なので、左側 1/3 程度を切り出す
    # 余白を考慮して調整
    left = 0
    top = 0
    right = width // 3
    bottom = height
    
    front_img = img.crop((left, top, right, bottom))
    front_img.save(dest_path)
    print(f'Successfully cropped front view to {dest_path}')
else:
    print('Source image not found')
