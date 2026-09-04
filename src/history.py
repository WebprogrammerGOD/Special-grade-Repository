import json
from datetime import datetime
from pathlib import Path

def save_chat_to_local(conversation_log):
    """Tự động lưu lịch sử chat vào thư mục 'history' dưới dạng file JSON"""
    # Tạo thư mục history nếu chưa có
    history_dir = Path("history")
    history_dir.mkdir(exist_ok=True)
    
    # Tạo tên file theo mốc thời gian để không bị trùng (Ví dụ: chat_20260920_153022.json)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = history_dir / f"chat_{timestamp}.json"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(conversation_log, f, ensure_ascii=False, indent=4)