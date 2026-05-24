"""OpenAI provider implementation using the Chat Completions API with tool calling."""

import json

from openai import AsyncOpenAI

from .base import AIProvider


class OpenAIProvider(AIProvider):
    """Wraps the OpenAI async client for multi-turn tool-calling conversations."""

    async def run_thread(self, messages, model, tools, tool_executor, on_message):
        """Run the conversation loop, executing tool calls until a final text response."""
        client = AsyncOpenAI(api_key=self.api_key)
        openai_messages = self._to_openai_messages(messages)

        while True:
            response = await client.chat.completions.create(
                model=model,
                messages=openai_messages,
                tools=tools if tools else None,
            )
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" or (
                choice.message.tool_calls and len(choice.message.tool_calls) > 0
            ):
                assistant_msg = {
                    "role": "assistant",
                    "content": choice.message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.message.tool_calls
                    ],
                }
                openai_messages.append(assistant_msg)

                for tc in choice.message.tool_calls:
                    await on_message(
                        {
                            "role": "tool_call",
                            "tool_name": tc.function.name,
                            "tool_call_id": tc.id,
                            "content": tc.function.arguments,
                        }
                    )

                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = await tool_executor(tc.function.name, args)

                    await on_message(
                        {
                            "role": "tool_result",
                            "tool_call_id": tc.id,
                            "tool_name": tc.function.name,
                            "content": result,
                        }
                    )

                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        }
                    )
            else:
                final_text = choice.message.content or ""
                await on_message({"role": "assistant", "content": final_text})
                return {"content": final_text}

    def _to_openai_messages(self, messages):
        """Convert provider-neutral messages to OpenAI format."""
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            if msg["role"] in ("system", "user", "assistant"):
                if (
                    msg["role"] == "assistant"
                    and i + 1 < len(messages)
                    and messages[i + 1]["role"] == "tool_call"
                ):
                    tool_calls = []
                    j = i + 1
                    while j < len(messages) and messages[j]["role"] == "tool_call":
                        tool_calls.append(
                            {
                                "id": messages[j].get("tool_call_id", ""),
                                "type": "function",
                                "function": {
                                    "name": messages[j].get("tool_name", ""),
                                    "arguments": messages[j].get("content", "{}"),
                                },
                            }
                        )
                        j += 1
                    result.append(
                        {
                            "role": "assistant",
                            "content": msg.get("content"),
                            "tool_calls": tool_calls,
                        }
                    )
                    i = j
                    continue
                else:
                    result.append(
                        {"role": msg["role"], "content": msg.get("content", "")}
                    )
            elif msg["role"] == "tool_call":
                tool_calls = [
                    {
                        "id": msg.get("tool_call_id", ""),
                        "type": "function",
                        "function": {
                            "name": msg.get("tool_name", ""),
                            "arguments": msg.get("content", "{}"),
                        },
                    }
                ]
                while (
                    i + 1 < len(messages)
                    and messages[i + 1]["role"] == "tool_call"
                ):
                    i += 1
                    tool_calls.append(
                        {
                            "id": messages[i].get("tool_call_id", ""),
                            "type": "function",
                            "function": {
                                "name": messages[i].get("tool_name", ""),
                                "arguments": messages[i].get("content", "{}"),
                            },
                        }
                    )
                result.append(
                    {"role": "assistant", "content": None, "tool_calls": tool_calls}
                )
            elif msg["role"] == "tool_result":
                result.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.get("tool_call_id", ""),
                        "content": msg.get("content", ""),
                    }
                )
            i += 1
        return result

    async def list_models(self):
        """Return available GPT/o-series model IDs from the OpenAI API."""
        client = AsyncOpenAI(api_key=self.api_key)
        models = await client.models.list()
        return sorted(
            m.id
            for m in models.data
            if "gpt" in m.id or "o1" in m.id or "o3" in m.id
        )
