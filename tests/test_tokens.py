from app.tokens import calculate_reduction, count_tokens, estimate_cost, is_token_warning

def test_count_tokens():
    text = "Xin chào Việt Nam! Đây là phần mềm LilbowMdConvert."
    cnt = count_tokens(text)
    assert cnt > 0
    assert count_tokens("") == 0

def test_calculate_reduction():
    assert calculate_reduction(1000, 700) == 30.0
    assert calculate_reduction(0, 0) == 0.0
    assert calculate_reduction(500, 600) == 0.0

def test_estimate_cost():
    usd, vnd = estimate_cost(1_000_000, "GPT-4o")
    assert usd == 2.5
    assert vnd == 2.5 * 25400

    usd_mini, vnd_mini = estimate_cost(1_000_000, "GPT-4o-mini")
    assert usd_mini == 0.15

def test_token_warning():
    assert is_token_warning(150_000) is True
    assert is_token_warning(50_000) is False
