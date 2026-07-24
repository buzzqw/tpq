import json
import requests
from typing import Optional, Generator


class AIClient:
    PROVIDERS = {
        "openai": {
            "name": "OpenAI",
            "url": "https://api.openai.com/v1/chat/completions",
            "default_model": "gpt-4o",
            "key_env": "OPENAI_API_KEY",
            "protocol": "openai",
        },
        "claude": {
            "name": "Claude (Anthropic)",
            "url": "https://api.anthropic.com/v1/messages",
            "default_model": "claude-sonnet-4-20250514",
            "key_env": "ANTHROPIC_API_KEY",
            "protocol": "claude",
        },
        "gemini": {
            "name": "Google Gemini",
            "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            "default_model": "gemini-2.5-flash",
            "key_env": "GEMINI_API_KEY",
            "protocol": "gemini",
        },
        "deepseek": {
            "name": "DeepSeek",
            "url": "https://api.deepseek.com/chat/completions",
            "default_model": "deepseek-chat",
            "key_env": "DEEPSEEK_API_KEY",
            "protocol": "openai",
        },
        "ollama": {
            "name": "Ollama (Local)",
            "url": "http://localhost:11434/v1/chat/completions",
            "default_model": "llama3",
            "key_env": "",
            "protocol": "ollama",
        },
        "custom": {
            "name": "Custom OpenAI API",
            "url": "http://localhost:8080/v1/chat/completions",
            "default_model": "llama3",
            "key_env": "",
            "protocol": "openai",
        },
    }

    def __init__(self, provider: str, api_key: str = "", model: Optional[str] = None,
                 base_url: str = ""):
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' non supportato. "
                f"Usa: {', '.join(self.PROVIDERS.keys())}"
            )
        self.provider = provider
        self.api_key = api_key
        info = self.PROVIDERS[provider]
        self.model = model or info["default_model"]
        self.base_url = base_url or info["url"]
        self._protocol = info.get("protocol", "openai")
        self._messages = []

    def chat(self, message: str) -> str:
        self._messages.append({"role": "user", "content": message})
        if self._protocol == "claude":
            return self._call_claude()
        elif self._protocol == "gemini":
            return self._call_gemini(message)
        else:
            return self._call_openai_compatible()

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        self._messages.append({"role": "user", "content": message})
        if self._protocol == "claude":
            yield from self._call_claude_stream()
        elif self._protocol == "gemini":
            yield self._call_gemini(message)
        else:
            yield from self._call_openai_stream()

    def reset(self):
        self._messages = []

    def _call_openai_compatible(self) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key and self._protocol != "ollama":
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": self._messages,
        }
        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        self._messages.append({"role": "assistant", "content": content})
        return content

    def _call_openai_stream(self) -> Generator[str, None, None]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key and self._protocol != "ollama":
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": self._messages,
            "stream": True,
        }
        resp = requests.post(self.base_url, headers=headers, json=payload,
                             stream=True, timeout=120)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        full = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or line.startswith(":") or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full += content
                    yield content
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
        self._messages.append({"role": "assistant", "content": full})

    def _call_claude(self) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        system = ""
        msgs = []
        for m in self._messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                msgs.append(m)

        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": msgs,
        }
        if system:
            payload["system"] = system

        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        self._messages.append({"role": "assistant", "content": content})
        return content

    def _call_claude_stream(self) -> Generator[str, None, None]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        system = ""
        msgs = []
        for m in self._messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                msgs.append(m)

        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": msgs,
            "stream": True,
        }
        if system:
            payload["system"] = system

        resp = requests.post(self.base_url, headers=headers, json=payload,
                             stream=True, timeout=120)
        resp.raise_for_status()
        full = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            try:
                event = json.loads(data_str)
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        full += text
                        yield text
                elif event.get("type") == "message_stop":
                    break
            except (json.JSONDecodeError, KeyError):
                continue
        self._messages.append({"role": "assistant", "content": full})

    def _call_gemini(self, message: str) -> str:
        url = self.base_url.replace("{model}", self.model)
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        contents = []
        for m in self._messages:
            contents.append({
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}],
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            },
        }

        resp = requests.post(url, headers=headers, params=params, json=payload,
                             timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        self._messages.append({"role": "assistant", "content": content})
        return content
