"""Bài Tập Nâng Cao: Financial Agent + Memory + Retry Logic.

Demo các tính năng mở rộng:
1. Financial Agent phân tích thiệt hại tài chính.
2. Conversation memory giữ lịch sử câu hỏi/trả lời.
3. Retry logic khi gọi LLM hoặc tool thất bại.
4. Custom tool estimate_financial_loss.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common.llm import get_llm


@tool
def estimate_financial_loss(contract_value: float, breach_type: str) -> str:
    """Ước tính thiệt hại tài chính dựa trên giá trị hợp đồng và loại vi phạm."""
    multiplier = 1.5
    if "willful" in breach_type.lower() or "intentional" in breach_type.lower():
        multiplier = 2.0
    elif "negligent" in breach_type.lower():
        multiplier = 1.0

    estimated = contract_value * multiplier
    fees = contract_value * 0.15
    total = estimated + fees

    return (
        f"Estimated financial exposure:\n"
        f"- breach_type: {breach_type}\n"
        f"- contract_value: {contract_value:,.0f}\n"
        f"- multiplier: {multiplier:.1f}x\n"
        f"- estimated damages: {estimated:,.0f}\n"
        f"- legal fees (~15%): {fees:,.0f}\n"
        f"- total exposure: {total:,.0f}"
    )


async def invoke_with_retry(llm_with_tools, messages: list, retries: int = 3, delay: int = 1):
    """Gọi LLM với retry logic đơn giản khi gặp lỗi tạm thời."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return await llm_with_tools.ainvoke(messages)
        except Exception as exc:  # broad catch for the demo; production should narrow this.
            last_error = exc
            if attempt == retries:
                raise
            wait_time = delay * attempt
            print(f"[retry] attempt {attempt} failed: {exc!r}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    raise last_error


async def financial_agent(question: str, history: list[str]) -> str:
    """Demo agent có memory + tool + retry logic."""
    llm = get_llm()
    tools = [estimate_financial_loss]
    llm_with_tools = llm.bind_tools(tools)

    history_text = "\n".join(history[-3:]) if history else "(chưa có câu hỏi trước đó)"
    prompt = (
        "Bạn là chuyên gia tài chính pháp lý. Dựa trên câu hỏi và lịch sử hội thoại, "
        "hãy phân tích thiệt hại tài chính, ưu tiên dùng tool estimate_financial_loss "
        "khi có số tiền hợp đồng.\n\n"
        f"Lịch sử hội thoại:\n{history_text}\n\n"
        f"Câu hỏi hiện tại:\n{question}"
    )

    messages = [
        SystemMessage(content="Bạn là chuyên gia pháp lý tài chính. Trả lời ngắn gọn, rõ ràng, có thể dùng tool."),
        HumanMessage(content=prompt),
    ]

    response = await invoke_with_retry(llm_with_tools, messages)
    messages.append(response)

    if response.tool_calls:
        tool_result = None
        for tool_call in response.tool_calls:
            if tool_call["name"] == "estimate_financial_loss":
                tool_result = estimate_financial_loss.invoke(tool_call["args"])
        if tool_result:
            messages.append(ToolMessage(content=tool_result, tool_call_id=response.tool_calls[0]["id"]))
            final_response = await invoke_with_retry(llm_with_tools, messages)
            return final_response.content

    return response.content


async def main():
    load_dotenv()

    history = [
        "Câu 1: Tôi cần biết thiệt hại tài chính nếu vi phạm hợp đồng trị giá 2 tỷ đồng.",
    ]

    question = "Hãy ước tính thiệt hại tài chính cho vụ vi phạm hợp đồng trị giá 2.000.000.000 đồng, loại vi phạm là willful breach."

    print("=" * 72)
    print("ADVANCED CHALLENGE: Financial Agent + Memory + Retry")
    print("=" * 72)
    print("\nLịch sử hội thoại trước:\n")
    for item in history:
        print("-", item)

    print("\nCâu hỏi hiện tại:")
    print(question)
    print("\nĐang xử lý bằng financial_agent...")

    answer = await financial_agent(question, history)
    history.append(f"Câu 2: {question}")
    history.append(f"Trả lời: {answer}")

    print("\n✅ Kết quả cuối cùng:")
    print(answer)
    print("\n✅ Memory đã được cập nhật:")
    for item in history[-3:]:
        print("-", item)


if __name__ == "__main__":
    asyncio.run(main())
