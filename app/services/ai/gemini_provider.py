"""Google Gemini provider implementation using the generativeai SDK with function calling."""

import json

import google.generativeai as genai
from google.generativeai.types import content_types

from .base import AIProvider


class GeminiProvider(AIProvider):
    """Wraps the Google Generative AI client for multi-turn function-calling conversations."""

    async def run_thread(self, messages, model, tools, tool_executor, on_message):
        """Run the conversation loop, executing function calls until a final text response."""
        genai.configure(api_key=self.api_key)

        system_instruction, gemini_history, latest_user = self._to_gemini_messages(
            messages
        )

        gemini_tools = self._convert_tools(tools) if tools else None

        model_kwargs = {}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        gen_model = genai.GenerativeModel(model, **model_kwargs)

        chat = gen_model.start_chat(history=gemini_history)

        send_kwargs = {}
        if gemini_tools:
            send_kwargs["tools"] = gemini_tools

        while True:
            response = await chat.send_message_async(latest_user, **send_kwargs)

            # Check for function calls in the response
            function_calls = []
            for part in response.parts:
                if part.function_call and part.function_call.name:
                    function_calls.append(part.function_call)

            if function_calls:
                function_responses = []
                for fc in function_calls:
                    args = dict(fc.args) if fc.args else {}
                    args_str = json.dumps(args)

                    await on_message(
                        {
                            "role": "tool_call",
                            "tool_name": fc.name,
                            "tool_call_id": fc.name,
                            "content": args_str,
                        }
                    )

                    result = await tool_executor(fc.name, args)

                    await on_message(
                        {
                            "role": "tool_result",
                            "tool_call_id": fc.name,
                            "tool_name": fc.name,
                            "content": result,
                        }
                    )

                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fc.name,
                                response={"result": result},
                            )
                        )
                    )

                # Send tool results back as the next user turn
                latest_user = function_responses
            else:
                final_text = response.text or ""
                await on_message({"role": "assistant", "content": final_text})
                return {"content": final_text}

    def _to_gemini_messages(self, messages):
        """Convert provider-neutral messages to Gemini chat history + latest user message.

        Returns (system_instruction, history, latest_user_content).
        Gemini expects alternating user/model turns in history and the latest
        user message is passed to send_message separately.
        """
        system_instruction = None
        history = []
        latest_user = ""

        converted = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg.get("content", "")
            elif msg["role"] == "user":
                converted.append(
                    {"role": "user", "parts": [msg.get("content", "")]}
                )
            elif msg["role"] == "assistant":
                converted.append(
                    {"role": "model", "parts": [msg.get("content", "")]}
                )
            elif msg["role"] == "tool_call":
                try:
                    args = json.loads(msg.get("content", "{}"))
                except json.JSONDecodeError:
                    args = {}
                converted.append(
                    {
                        "role": "model",
                        "parts": [
                            genai.protos.Part(
                                function_call=genai.protos.FunctionCall(
                                    name=msg.get("tool_name", ""),
                                    args=args,
                                )
                            )
                        ],
                    }
                )
            elif msg["role"] == "tool_result":
                converted.append(
                    {
                        "role": "user",
                        "parts": [
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=msg.get("tool_name", ""),
                                    response={"result": msg.get("content", "")},
                                )
                            )
                        ],
                    }
                )

        # Merge consecutive same-role messages (Gemini requires alternation)
        merged = []
        for entry in converted:
            if merged and merged[-1]["role"] == entry["role"]:
                merged[-1]["parts"].extend(entry["parts"])
            else:
                merged.append(entry)

        if merged and merged[-1]["role"] == "user":
            latest_user = merged[-1]["parts"]
            history = [
                content_types.to_content(m) for m in merged[:-1]
            ]
        elif merged:
            latest_user = ["Continue."]
            history = [content_types.to_content(m) for m in merged]
        else:
            latest_user = ["Hello."]

        return system_instruction, history, latest_user

    def _convert_tools(self, openai_tools):
        """Convert OpenAI tool definitions to Gemini FunctionDeclaration list."""
        if not openai_tools:
            return None

        declarations = []
        for t in openai_tools:
            if t.get("type") != "function":
                continue
            func = t["function"]
            declarations.append(
                genai.protos.FunctionDeclaration(
                    name=func["name"],
                    description=func.get("description", ""),
                    parameters=self._convert_schema(func.get("parameters", {})),
                )
            )
        return declarations

    def _convert_schema(self, schema):
        """Convert a JSON Schema object to Gemini's Schema proto."""
        if not schema:
            return None

        type_map = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }

        schema_type = type_map.get(schema.get("type", "object"), genai.protos.Type.OBJECT)

        properties = {}
        for name, prop in schema.get("properties", {}).items():
            properties[name] = self._convert_schema(prop)

        kwargs = {"type": schema_type}
        if schema.get("description"):
            kwargs["description"] = schema["description"]
        if properties:
            kwargs["properties"] = properties
        if schema.get("required"):
            kwargs["required"] = schema["required"]
        if schema.get("items"):
            kwargs["items"] = self._convert_schema(schema["items"])

        return genai.protos.Schema(**kwargs)

    async def list_models(self):
        """Return model IDs that support content generation from the Gemini API."""
        genai.configure(api_key=self.api_key)
        return sorted(
            m.name.removeprefix("models/")
            for m in genai.list_models()
            if "generateContent" in (m.supported_generation_methods or [])
        )
