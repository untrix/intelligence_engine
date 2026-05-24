"""Anthropic Claude provider implementation using the Messages API with tool use."""

import json

from anthropic import AsyncAnthropic

from .base import AIProvider


class AnthropicProvider(AIProvider):
    """Wraps the Anthropic async client for multi-turn tool-calling conversations."""

    async def run_thread(self, messages, model, tools, tool_executor, on_message):
        """Run the conversation loop, executing tool calls until a final text response."""
        client = AsyncAnthropic(api_key=self.api_key)
        system_prompt, anthropic_messages = self._to_anthropic_messages(messages)
        anthropic_tools = self._convert_tools(tools)

        while True:
            kwargs = {
                "model": model,
                "max_tokens": 4096,
                "messages": anthropic_messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools

            response = await client.messages.create(**kwargs)

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            if tool_use_blocks:
                # Build the assistant content blocks for the conversation history
                assistant_content = []
                for b in response.content:
                    if b.type == "text":
                        assistant_content.append({"type": "text", "text": b.text})
                    elif b.type == "tool_use":
                        assistant_content.append(
                            {
                                "type": "tool_use",
                                "id": b.id,
                                "name": b.name,
                                "input": b.input,
                            }
                        )
                anthropic_messages.append(
                    {"role": "assistant", "content": assistant_content}
                )

                tool_result_blocks = []
                for block in tool_use_blocks:
                    args_str = json.dumps(block.input) if block.input else "{}"
                    await on_message(
                        {
                            "role": "tool_call",
                            "tool_name": block.name,
                            "tool_call_id": block.id,
                            "content": args_str,
                        }
                    )

                    result = await tool_executor(block.name, block.input or {})

                    await on_message(
                        {
                            "role": "tool_result",
                            "tool_call_id": block.id,
                            "tool_name": block.name,
                            "content": result,
                        }
                    )

                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

                anthropic_messages.append(
                    {"role": "user", "content": tool_result_blocks}
                )
            else:
                final_text = " ".join(b.text for b in text_blocks)
                await on_message({"role": "assistant", "content": final_text})
                return {"content": final_text}

    def _to_anthropic_messages(self, messages):
        """Convert provider-neutral messages to Anthropic format.

        Returns (system_prompt, anthropic_messages).
        Anthropic requires alternating user/assistant turns.  Tool results
        are sent as user messages with tool_result content blocks.
        """
        system_prompt = ""
        result = []

        i = 0
        while i < len(messages):
            msg = messages[i]

            if msg["role"] == "system":
                system_prompt = msg.get("content", "")
                i += 1
                continue

            if msg["role"] == "user":
                result.append(
                    {"role": "user", "content": msg.get("content", "")}
                )
                i += 1
                continue

            if msg["role"] == "assistant":
                # Check if followed by tool_call messages
                if (
                    i + 1 < len(messages)
                    and messages[i + 1]["role"] == "tool_call"
                ):
                    content_blocks = []
                    if msg.get("content"):
                        content_blocks.append(
                            {"type": "text", "text": msg["content"]}
                        )
                    j = i + 1
                    while j < len(messages) and messages[j]["role"] == "tool_call":
                        tc = messages[j]
                        try:
                            inp = json.loads(tc.get("content", "{}"))
                        except json.JSONDecodeError:
                            inp = {}
                        content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc.get("tool_call_id", ""),
                                "name": tc.get("tool_name", ""),
                                "input": inp,
                            }
                        )
                        j += 1
                    result.append({"role": "assistant", "content": content_blocks})
                    i = j
                    continue
                else:
                    result.append(
                        {"role": "assistant", "content": msg.get("content", "")}
                    )
                    i += 1
                    continue

            if msg["role"] == "tool_call":
                # Standalone tool_call without preceding assistant message
                content_blocks = []
                j = i
                while j < len(messages) and messages[j]["role"] == "tool_call":
                    tc = messages[j]
                    try:
                        inp = json.loads(tc.get("content", "{}"))
                    except json.JSONDecodeError:
                        inp = {}
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.get("tool_call_id", ""),
                            "name": tc.get("tool_name", ""),
                            "input": inp,
                        }
                    )
                    j += 1
                result.append({"role": "assistant", "content": content_blocks})
                i = j
                continue

            if msg["role"] == "tool_result":
                # Collect consecutive tool_result messages into one user turn
                tool_result_blocks = []
                j = i
                while j < len(messages) and messages[j]["role"] == "tool_result":
                    tr = messages[j]
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tr.get("tool_call_id", ""),
                            "content": tr.get("content", ""),
                        }
                    )
                    j += 1
                result.append({"role": "user", "content": tool_result_blocks})
                i = j
                continue

            i += 1

        return system_prompt, result

    def _convert_tools(self, openai_tools):
        """Convert OpenAI tool format to Anthropic format."""
        if not openai_tools:
            return []
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"]["parameters"],
            }
            for t in openai_tools
            if t.get("type") == "function"
        ]

    async def list_models(self):
        """Return a hardcoded list of supported Claude model IDs."""
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]
