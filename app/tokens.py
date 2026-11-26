from typing import Dict, Tuple
import tiktoken

# Bảng giá ước tính theo 1M token đầu vào (USD)
# Lưu ý: Đây là số ước tính tham khảo, giá thực tế có thể thay đổi theo từng nhà cung cấp.
MODEL_PRICING: Dict[str, float] = {
    "GPT-4o": 2.50,          # $2.50 / 1M input tokens
    "GPT-4o-mini": 0.15,     # $0.15 / 1M input tokens
    "Claude 3.5 Sonnet": 3.00,  # $3.00 / 1M input tokens
    "Claude 3.5 Haiku": 0.80,   # $0.80 / 1M input tokens
    "Gemini 1.5 Flash": 0.075,  # $0.075 / 1M input tokens
    "Gemini 1.5 Pro": 1.25,    # $1.25 / 1M input tokens
}

USD_TO_VND_RATE = 25400  # Tỉ giá ước tính

_cached_encoding = None

def get_encoding():
    """Lấy bộ mã hóa tiktoken (cl100k_base), cache để tăng tốc."""
    global _cached_encoding
    if _cached_encoding is None:
        try:
            _cached_encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            try:
                _cached_encoding = tiktoken.encoding_for_model("gpt-4o")
            except Exception:
                _cached_encoding = None
    return _cached_encoding

def count_tokens(text: str) -> int:
    """
    Đếm số token của văn bản bằng tiktoken (cl100k_base).
    Nếu gặp lỗi mạng hoặc môi trường không tải được, ước tính xấp xỉ bằng số ký tự / 3.5.
    """
    if not text:
        return 0
    enc = get_encoding()
    if enc is not None:
        try:
            return len(enc.encode(text, disallowed_special=()))
        except Exception:
            pass
    # Ước lượng xấp xỉ cho tiếng Việt/tiếng Anh nếu tiktoken chưa nạp được
    return max(1, int(len(text) / 3.5))

def estimate_cost(token_count: int, model: str = "GPT-4o") -> Tuple[float, float]:
    """
    Ước tính chi phí đầu vào (USD và VND) cho lượng token nhất định.
    Trả về: (usd_cost, vnd_cost)
    """
    price_per_million = MODEL_PRICING.get(model, MODEL_PRICING["GPT-4o"])
    usd = (token_count / 1_000_000.0) * price_per_million
    vnd = usd * USD_TO_VND_RATE
    return round(usd, 4), round(vnd, 0)

def calculate_reduction(before_tokens: int, after_tokens: int) -> float:
    """Tính % token đã giảm được sau khi làm sạch."""
    if before_tokens <= 0:
        return 0.0
    reduction = ((before_tokens - after_tokens) / before_tokens) * 100.0
    return max(0.0, round(reduction, 1))

def is_token_warning(token_count: int, threshold: int = 100_000) -> bool:
    """Cảnh báo nếu số token vượt ngưỡng (mặc định 100k token)."""
    return token_count > threshold
