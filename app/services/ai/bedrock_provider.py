"""AWS Bedrock provider implementation using the Converse API with tool use."""

import json
from functools import partial

import boto3
from botocore.config import Config

from app.config import settings

from .base import AIProvider


class BedrockProvider(AIProvider):
    """Wraps the boto3 Bedrock runtime client for multi-turn tool-calling conversations."""

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key, **kwargs)
        self.aws_profile = kwargs.get("aws_profile", "")
        self.region = kwargs.get("aws_region", "us-east-1")

    def _get_session(self):
        session_kwargs = {"region_name": self.region}
        if self.aws_profile:
            session_kwargs["profile_name"] = self.aws_profile
        return boto3.Session(**session_kwargs)

    def _get_client(self):
        cfg = Config(
            connect_timeout=settings.bedrock_connect_timeout_seconds,
            read_timeout=settings.bedrock_read_timeout_seconds,
            retries={"max_attempts": 5, "mode": "adaptive"},
        )
        return self._get_session().client("bedrock-runtime", config=cfg)

    @staticmethod
    def _resolve_model_id(model: str, region: str) -> str:
        """Map a raw foundation model ID to a cross-region inference profile ID.

        Newer Bedrock models (e.g. Claude Opus) don't support on-demand
        invocation with bare model IDs — they require an inference profile.
        If the model ID already has a geo prefix (e.g. ``us.anthropic.…``)
        it is returned as-is.
        """
        GEO_PREFIXES = ("us.", "eu.", "ap.")
        if any(model.startswith(p) for p in GEO_PREFIXES):
            return model

        region_to_geo = {
            "us": "us", "eu": "eu", "ap": "ap", "me": "eu", "af": "eu",
            "ca": "us", "sa": "us",
        }
        geo = region_to_geo.get(region.split("-")[0], "us")
        return f"{geo}.{model}"

    async def run_thread(self, messages, model, tools, tool_executor, on_message):
        """Run the conversation loop via Bedrock Converse, offloading sync calls to an executor."""
        import asyncio

        client = self._get_client()
        model_id = self._resolve_model_id(model, self.region)
        system_prompt, bedrock_messages = self._to_bedrock_messages(messages)
        bedrock_tools = self._convert_tools(tools)

        while True:
            kwargs = {
                "modelId": model_id,
                "messages": bedrock_messages,
            }
            if system_prompt:
                kwargs["system"] = [{"text": system_prompt}]
            if bedrock_tools:
                kwargs["toolConfig"] = {"tools": bedrock_tools}

            # boto3 is synchronous — run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, partial(client.converse, **kwargs)
            )

            output = response.get("output", {})
            message = output.get("message", {})
            stop_reason = response.get("stopReason", "")

            content_blocks = message.get("content", [])
            tool_use_blocks = [b for b in content_blocks if "toolUse" in b]
            text_blocks = [b for b in content_blocks if "text" in b]

            if stop_reason == "tool_use" or tool_use_blocks:
                # Append assistant message with tool use to history
                bedrock_messages.append({"role": "assistant", "content": content_blocks})

                tool_result_blocks = []
                for block in tool_use_blocks:
                    tu = block["toolUse"]
                    tool_name = tu["name"]
                    tool_use_id = tu["toolUseId"]
                    tool_input = tu.get("input", {})

                    args_str = json.dumps(tool_input)
                    await on_message(
                        {
                            "role": "tool_call",
                            "tool_name": tool_name,
                            "tool_call_id": tool_use_id,
                            "content": args_str,
                        }
                    )

                    result = await tool_executor(tool_name, tool_input)

                    await on_message(
                        {
                            "role": "tool_result",
                            "tool_call_id": tool_use_id,
                            "tool_name": tool_name,
                            "content": result,
                        }
                    )

                    tool_result_blocks.append(
                        {
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"text": result}],
                            }
                        }
                    )

                bedrock_messages.append(
                    {"role": "user", "content": tool_result_blocks}
                )
            else:
                final_text = " ".join(b["text"] for b in text_blocks)
                await on_message({"role": "assistant", "content": final_text})
                return {"content": final_text}

    def _to_bedrock_messages(self, messages):
        """Convert provider-neutral messages to Bedrock converse format.

        Returns (system_prompt, bedrock_messages).
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
                    {"role": "user", "content": [{"text": msg.get("content", "")}]}
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
                        content_blocks.append({"text": msg["content"]})
                    j = i + 1
                    while j < len(messages) and messages[j]["role"] == "tool_call":
                        tc = messages[j]
                        try:
                            inp = json.loads(tc.get("content", "{}"))
                        except json.JSONDecodeError:
                            inp = {}
                        content_blocks.append(
                            {
                                "toolUse": {
                                    "toolUseId": tc.get("tool_call_id", ""),
                                    "name": tc.get("tool_name", ""),
                                    "input": inp,
                                }
                            }
                        )
                        j += 1
                    result.append({"role": "assistant", "content": content_blocks})
                    i = j
                    continue
                else:
                    result.append(
                        {
                            "role": "assistant",
                            "content": [{"text": msg.get("content", "")}],
                        }
                    )
                    i += 1
                    continue

            if msg["role"] == "tool_call":
                # Standalone tool_call without preceding assistant
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
                            "toolUse": {
                                "toolUseId": tc.get("tool_call_id", ""),
                                "name": tc.get("tool_name", ""),
                                "input": inp,
                            }
                        }
                    )
                    j += 1
                result.append({"role": "assistant", "content": content_blocks})
                i = j
                continue

            if msg["role"] == "tool_result":
                tool_result_blocks = []
                j = i
                while j < len(messages) and messages[j]["role"] == "tool_result":
                    tr = messages[j]
                    tool_result_blocks.append(
                        {
                            "toolResult": {
                                "toolUseId": tr.get("tool_call_id", ""),
                                "content": [{"text": tr.get("content", "")}],
                            }
                        }
                    )
                    j += 1
                result.append({"role": "user", "content": tool_result_blocks})
                i = j
                continue

            i += 1

        return system_prompt, result

    def _convert_tools(self, openai_tools):
        """Convert OpenAI tool format to Bedrock converse toolConfig format."""
        if not openai_tools:
            return []
        return [
            {
                "toolSpec": {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "inputSchema": {
                        "json": t["function"]["parameters"],
                    },
                }
            }
            for t in openai_tools
            if t.get("type") == "function"
        ]

    async def list_models(self):
        """Return Bedrock foundation model IDs that support the Converse API."""
        import asyncio
        from functools import partial as _partial

        session = self._get_session()
        bedrock = session.client("bedrock")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            _partial(
                bedrock.list_foundation_models,
                byOutputModality="TEXT",
            ),
        )
        return sorted(
            m["modelId"]
            for m in response.get("modelSummaries", [])
            if "CONVERSE" in m.get("inferenceTypesSupported", [])
            or "ON_DEMAND" in m.get("inferenceTypesSupported", [])
        )
