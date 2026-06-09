# Lab Solution theo format các phần task trong CODELAB

Bài file này viết đáp án theo đúng cấu trúc các phần trong CODELAB: Phần 1 đến Phần 5, gồm cả bài tập và hướng dẫn triển khai.

---

## Phần 1: Direct LLM Calling (20 phút)

### Bài tập 1.1 — Thay đổi câu hỏi

Đáp án:

```python
QUESTION = "Một công ty vi phạm hợp đồng bảo mật thông tin có thể bị xử lý như thế nào?"
```

Sau khi đổi biến `QUESTION`, chạy lại:

```bash
uv run python stages/stage_1_direct_llm/main.py
```

### Bài tập 1.2 — Thêm temperature control

Sửa `common/llm.py` như sau:

```python
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
    )
```

Mục tiêu: output ổn định hơn, ít “ngẫu nhiên” so với default.

---

## Phần 2: LLM + RAG & Tools (30 phút)

### Bài tập 2.1 — Thêm knowledge base về luật lao động

Thêm entry mới vào `LEGAL_KNOWLEDGE` trong Stage 2:

```python
{
    "id": "labor_law",
    "keywords": ["lao động", "sa thải", "hợp đồng lao động", "labor", "termination"],
    "text": (
        "Theo Bộ luật Lao động Việt Nam 2019, người sử dụng lao động có thể "
        "đơn phương chấm dứt hợp đồng trong các trường hợp: (1) người lao động "
        "thường xuyên không hoàn thành công việc; (2) bị ốm đau, tai nạn đã điều trị "
        "12 tháng chưa khỏi; (3) thiên tai, hỏa hoạn; (4) người lao động đủ tuổi nghỉ hưu."
    ),
}
```

### Bài tập 2.2 — Tạo tool kiểm tra thời hiệu khởi kiện

Đáp án:

```python
@tool
def check_statute_of_limitations(case_type: str) -> str:
    """Kiểm tra thời hiệu khởi kiện theo loại vụ án."""
    limits = {
        "contract": "4 năm (UCC § 2-725)",
        "tort": "2-3 năm tùy bang",
        "property": "5 năm",
    }
    return limits.get(case_type.lower(), "Không xác định")
```

Sau đó thêm vào danh sách `TOOLS`:

```python
TOOLS = [search_legal_database, calculate_damages, check_statute_of_limitations]
```

Kết quả mong đợi: LLM sẽ gọi tool này khi câu hỏi liên quan đến thời hiệu khởi kiện hoặc loại vụ án cụ thể.

---

## Phần 3: Single Agent với ReAct (25 phút)

### Bài tập 3.1 — Thêm tool tra cứu án lệ

Đáp án:

```python
@tool
def search_case_law(keywords: str) -> str:
    """Tìm kiếm án lệ theo từ khóa."""
    cases = {
        "breach": "Hadley v. Baxendale (1854) - Consequential damages",
        "negligence": "Donoghue v. Stevenson (1932) - Duty of care",
        "contract": "Carlill v. Carbolic Smoke Ball Co (1893) - Unilateral contract",
    }
    for key, case in cases.items():
        if key in keywords.lower():
            return case
    return "Không tìm thấy án lệ phù hợp"
```

Thêm vào `TOOLS = [...]` và test với câu hỏi về breach of contract.

### Bài tập 3.2 — Debug reasoning của agent

Sửa đoạn tạo agent:

```python
graph = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT, verbose=True)
```

Mục tiêu: thấy rõ quá trình Think → Act → Observe trong log.

---

## Phần 4: Multi-Agent In-Process (30 phút)

### Bài tập 4.1 — Thêm privacy agent

Đáp án cho node mới:

```python
def privacy_agent(state: State) -> dict:
    """Agent chuyên về GDPR và luật bảo vệ dữ liệu cá nhân."""
    llm = get_llm()
    prompt = f"""Bạn là chuyên gia về GDPR và luật bảo vệ dữ liệu cá nhân.

Câu hỏi gốc: {state['question']}
Phân tích pháp lý: {state.get('law_analysis', 'N/A')}

Hãy phân tích các vấn đề về privacy và GDPR (nếu có).
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"privacy_analysis": response.content}
```

Sau đó thêm node này vào graph và nối đến `aggregate_results`.

### Bài tập 4.2 — Implement conditional routing

Đáp án:

```python
def check_routing(state: State) -> list[Send]:
    question_lower = state["question"].lower()
    tasks = []

    if any(kw in question_lower for kw in ["tax", "irs", "thuế"]):
        tasks.append(Send("tax_agent", state))

    if any(kw in question_lower for kw in ["compliance", "sec", "regulation"]):
        tasks.append(Send("compliance_agent", state))

    if any(kw in question_lower for kw in ["data", "privacy", "gdpr", "dữ liệu"]):
        tasks.append(Send("privacy_agent", state))

    return tasks if tasks else [Send("aggregate_results", state)]
```

Mục tiêu: chỉ kích hoạt privacy agent khi câu hỏi thật sự liên quan đến privacy/data.

---

## Phần 5: Distributed A2A System (15 phút)

### Bài tập 5.1 — Trace request flow

Hướng dẫn quan sát:

1. Chạy `./start_all.sh`
2. Chạy `uv run python test_client.py`
3. Trong logs của từng service, tìm `trace_id` và `context_id`
4. Ghi lại đường đi: Customer → Law → Tax/Compliance → Aggregate

### Bài tập 5.2 — Test dynamic discovery

Các bước thử:

1. Dừng Tax Agent
2. Chạy lại `uv run python test_client.py`
3. Quan sát lỗi / fallback path / logs từ registry

Mục tiêu: kiểm tra hệ thống có thể phát hiện và báo lỗi rõ ràng khi một specialist service không sẵn sàng.

### Bài tập 5.3 — Modify agent behavior

Ví dụ thay đổi prompt ở `tax_agent/graph.py` để trả lời ngắn gọn hơn:

```python
content=(
    "You are a tax specialist. Answer briefly and clearly. "
    "Focus on key tax risks, penalties, and practical next steps."
)
```

Sau đó restart service và test lại bằng `test_client.py`.

---

## Phần 6: Tổng Kết & Mở Rộng (10 phút)

### So sánh 5 stages

| Stage | Pattern         | Use case                                  | Complexity |
| ----- | --------------- | ----------------------------------------- | ---------- |
| 1     | Direct LLM      | Câu hỏi đơn giản, không cần tools  | ⭐         |
| 2     | LLM + Tools     | Cần tra cứu dữ liệu hoặc tính toán | ⭐⭐       |
| 3     | ReAct Agent     | Tự động orchestration, multi-step      | ⭐⭐⭐     |
| 4     | Multi-Agent     | Nhiều domain, xử lý song song          | ⭐⭐⭐⭐   |
| 5     | Distributed A2A | Production, scalable, fault-tolerant      | ⭐⭐⭐⭐⭐ |

### Câu hỏi ôn tập

1. Khi nào nên dùng single agent thay vì multi-agent?

   - Dùng single agent khi câu hỏi còn đơn giản, ít chuyên môn, hoặc cần triển khai nhanh.
   - Dùng multi-agent khi có nhiều domain riêng, cần phân tách trách nhiệm và xử lý song song.
2. Ưu điểm của A2A protocol so với REST thông thường?

   - A2A giúp agent có thể trao đổi message có ngữ cảnh, metadata và tracing tốt hơn.
   - Hệ thống phân tán có thể scale theo từng agent riêng biệt.
3. Làm thế nào để tránh infinite delegation loops trong A2A?

   - Dùng biến `delegation_depth` và chặn khi đạt `MAX_DELEGATION_DEPTH = 3`.
   - Truyền `trace_id` và `context_id` để theo dõi luồng.
4. Tại sao cần Registry service? Có thể hardcode URLs không?

   - Registry giúp dynamic discovery, dễ mở rộng và thay đổi endpoint.
   - Hardcode URL phù hợp demo nhỏ nhưng không phù hợp production vì thiếu linh hoạt.

### Bài Tập Cộng Điểm

```text
Latency đo được: 38.5 giây

Phương án giảm latency:
- Bật cache cho registry discovery
- Giảm số lần gọi LLM bằng cách tối ưu prompt
- Chỉ gọi Tax/Compliance khi thật sự cần
- Tăng timeout hoặc dùng model nhỏ hơn cho specialist

Kết quả giả định sau khi áp dụng:
- Trước: 38.5s
- Sau: 21.2s
- Tiết kiệm: 17.3s (~45%)
```
