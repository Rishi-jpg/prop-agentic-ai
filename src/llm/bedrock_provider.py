import asyncio
import boto3
from typing import Any, Optional
from src.llm.base import LLMProvider, LLMResponse, Message, ToolCall


class BedrockConverseProvider(LLMProvider):
    """Production LLM provider using Amazon Bedrock Converse API."""

    def __init__(
        self,
        model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0",
        region_name: str = "us-east-1",
    ):
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region_name)

    def _to_bedrock_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        bedrock_msgs = []
        for msg in messages:
            if msg.role == "tool":
                bedrock_msgs.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": msg.tool_call_id,
                            "content": [{"text": msg.content}],
                        }
                    }]
                })
            elif msg.role == "assistant" and msg.tool_calls:
                blocks = []
                if msg.content:
                    blocks.append({"text": msg.content})
                for tc in msg.tool_calls:
                    blocks.append({
                        "toolUse": {
                            "toolUseId": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    })
                bedrock_msgs.append({"role": "assistant", "content": blocks})
            else:
                bedrock_msgs.append({
                    "role": msg.role,
                    "content": [{"text": msg.content}]
                })
        return bedrock_msgs

    async def generate(
        self,
        messages: list[Message],
        system_prompt: str,
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "modelId": self.model_id,
            "system": [{"text": system_prompt}],
            "messages": self._to_bedrock_messages(messages),
            "inferenceConfig": {"temperature": temperature, "maxTokens": 2048},
        }
        if tools:
            kwargs["toolConfig"] = {"tools": tools}

        # boto3 is synchronous; run in threadpool to keep our async agent loop non-blocking
        response = await asyncio.to_thread(self.client.converse, **kwargs)

        output_msg = response["output"]["message"]
        text_parts, tool_calls = [], []

        for block in output_msg.get("content", []):
            if "text" in block:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(
                    ToolCall(id=tu["toolUseId"], name=tu["name"], arguments=tu["input"])
                )

        usage = response.get("usage", {})
        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            stop_reason=response.get("stopReason", "end_turn"),
        )