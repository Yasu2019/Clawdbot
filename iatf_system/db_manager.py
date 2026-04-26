import os
import csv
import shutil
from datetime import datetime

# Paths
BASE_DIR = r"D:\Clawdbot_Docker_20260125\iatf_system\db"
INGEST_DIR = os.path.join(BASE_DIR, "ingest")
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
CATEGORY_CSV = os.path.join(BASE_DIR, "category.csv")
ATTACHED_CSV = os.path.join(BASE_DIR, "record", "attachedfile.csv")

def load_categories():
    categories = []
    if not os.path.exists(CATEGORY_CSV):
        return categories
    with open(CATEGORY_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                categories.append({'id': row[0], 'name': row[1]})
    return categories

def scan_ingest():
    if not os.path.exists(INGEST_DIR):
        os.makedirs(INGEST_DIR)
    return [f for f in os.listdir(INGEST_DIR) if os.path.isfile(os.path.join(INGEST_DIR, f))]

def guess_category(filename, categories):
    # Keyword matching with confidence
    best_match = None
    for cat in categories:
        if cat['name'] in filename:
            # If we find a very specific match, return it
            if len(cat['name']) > 5:
                return cat['id'], "high"
            best_match = cat['id']
    
    if best_match:
        return best_match, "medium"
        
    # Fallback to category 3 (教材) if it looks like a manual
    if "監査" in filename or "教材" in filename:
        return "3", "low"
    
    return "unknown", "none"

def create_category(name, parent_id="2"):
    # Load existing to find next ID
    cats = load_categories()
    if not cats:
        next_id = 1
    else:
        # Get max ID and add 1
        try:
            next_id = max(int(c['id']) for c in cats) + 1
        except:
            next_id = len(cats) + 1
            
    new_row = [str(next_id), name, parent_id, ""]
    
    try:
        with open(CATEGORY_CSV, mode='a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(new_row)
        return True, str(next_id)
    except Exception as e:
        return False, str(e)

def ingest_file(filename, category_id):
    src_path = os.path.join(INGEST_DIR, filename)
    dst_path = os.path.join(DOCUMENTS_DIR, filename)
    
    if not os.path.exists(src_path):
        return False, "File not found"
    
    # Check if category exists
    categories = load_categories()
    cat_name = next((c['name'] for c in categories if c['id'] == category_id), "Unknown")
    
    # Prepare row for attachedfile.csv
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_row = [
        filename,           # filename
        category_id,        # category
        "",                 # partnumber
        "",                 # materialcode
        "",                 # phase
        "",                 # stage
        "",                 # description
        "完了",             # status
        "",                 # documenttype
        filename.split('.')[0], # documentname
        "",                 # documentrev
        "",                 # documentcategory
        "",                 # documentnumber
        now_str,            # start_time
        now_str,            # deadline_at
        now_str,            # end_at
        "100",              # goal_attainment_level
        "100",              # tasseido
        "object1"           # object
    ]
    
    try:
        with open(ATTACHED_CSV, mode='a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(new_row)
        
        if not os.path.exists(DOCUMENTS_DIR):
            os.makedirs(DOCUMENTS_DIR)
        shutil.move(src_path, dst_path)
        
        return True, f"Successfully ingested {filename} to {cat_name}"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python db_manager.py [scan|ingest|create_cat] ...")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "scan":
        files = scan_ingest()
        cats = load_categories()
        results = []
        for f in files:
            guess_id, confidence = guess_category(f, cats)
            results.append(f"{f}|{guess_id}|{confidence}")
        print("\n".join(results))
    elif cmd == "ingest":
        if len(sys.argv) < 4:
            print("Missing arguments for ingest")
            sys.exit(1)
        success, msg = ingest_file(sys.argv[2], sys.argv[3])
        print(msg)
    elif cmd == "create_cat":
        if len(sys.argv) < 3:
            print("Missing name for category")
            sys.exit(1)
        success, res = create_category(sys.argv[2])
        print(f"{success}|{res}")
