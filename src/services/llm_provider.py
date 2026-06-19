import io
import base64
from PIL import Image
from src.prompts.registry import get_default_system_prompt
from src.config.settings import (
    get_config_value,
    api_key_env_name,
    get_api_key,
    load_environment,
    APP_NAME,
)
from src.config.models import OPENROUTER_BASE_URL, DEFAULT_OPENROUTER_MODEL
try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
except ImportError:
    ChatOpenAI = ChatAnthropic = HumanMessage = AIMessage = SystemMessage = None
try:
    import google.generativeai as genai
    genai_available = True
except ImportError:
    genai_available = False
# ============================================================================
# API PROVIDERS (USING LANGCHAIN)
# ============================================================================

class APIProvider:
    """Base class for AI API providers using LangChain."""
    
    def __init__(self, config, system_prompt=None):
        self.config = config
        self.conversation_history = []
        self.system_prompt = system_prompt or get_default_system_prompt()
        self.llm = None
        self._api_key_env = api_key_env_name(
            get_config_value(config, "API", "provider", "anthropic")
        )
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LangChain LLM. Implemented by subclasses."""
        raise NotImplementedError

    def is_ready(self):
        return self.llm is not None

    def _ensure_llm(self):
        """Try to initialize the client (e.g. after keys were added to the environment)."""
        if self.llm is not None:
            return True
        load_environment()
        self._initialize_llm()
        return self.llm is not None

    def _missing_key_message(self):
        return (
            f"{self._api_key_env} is not set. "
            f"Add it in Windows Environment Variables or a .env file, then try again."
        )
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to AI. Implemented by subclasses."""
        raise NotImplementedError
    
    def add_text_message(self, text):
        """Add a text message to history."""
        self.conversation_history.append(HumanMessage(content=text))
    
    def add_image_message(self, base64_image, text):
        """Add a screenshot message to history."""
        image_part = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        }
        if text:
            content = [{"type": "text", "text": text}, image_part]
        else:
            content = [image_part]
        self.conversation_history.append(HumanMessage(content=content))

    def add_multi_image_message(self, images_b64, text):
        """Add a multi-image message to history."""
        content = []
        if text:
            content.append({"type": "text", "text": text})
        for b64 in images_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        self.conversation_history.append(HumanMessage(content=content))
    
    def add_assistant_message(self, text):
        """Add AI response to history."""
        self.conversation_history.append(AIMessage(content=text))
    
    def trim_history(self):
        """Keep first 2 messages and last 28 messages if history exceeds 30."""
        if len(self.conversation_history) > 30:
            self.conversation_history = (
                self.conversation_history[:2] +
                self.conversation_history[-28:]
            )
    
    def clear_history(self):
        """Clear all conversation history."""
        self.conversation_history = []

    def apply_system_prompt(self, prompt_text):
        """Update the system prompt used for subsequent API calls."""
        self.system_prompt = prompt_text

    def supports_vision(self):
        """Return True if this provider can process image messages."""
        return True

    def _add_user_content(self, message_content):
        """Add user content to history based on format."""
        if isinstance(message_content, str):
            self.add_text_message(message_content)
        elif isinstance(message_content, dict):
            if "images" in message_content:
                self.add_multi_image_message(
                    message_content["images"], message_content["text"]
                )
            else:
                self.add_image_message(
                    message_content["image"], message_content["text"]
                )


class _LangChainChatProvider(APIProvider):
    """Shared LangChain chat invoke path (OpenAI-compatible APIs)."""

    def send_message(self, message_content, on_response, on_error):
        try:
            if not self._ensure_llm():
                on_error(self._missing_key_message())
                return

            self._add_user_content(message_content)
            self.trim_history()

            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            response = self.llm.invoke(messages)
            reply = getattr(response, "content", "")
            if reply is None:
                reply = ""
            elif isinstance(reply, list):
                reply = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in reply
                )
            else:
                reply = str(reply)
            
            metadata = getattr(response, "response_metadata", {}) or {}
            
            if not reply.strip():
                if metadata.get("finish_reason") == "length":
                    reply = "[The model ran out of output tokens during its reasoning/thinking phase. I have increased the default max_tokens in config.ini, please restart the application to apply the change.]"
                else:
                    reply = "[Empty response returned by the model. This can happen if the model is overloaded, rate-limited, or if there is a credit/quota issue on your provider account.]"
                
            self.add_assistant_message(reply)

            usage = metadata.get("usage", {}) or {}
            tokens = {
                "input": usage.get("input_tokens") or usage.get("prompt_tokens") or 0,
                "output": usage.get("output_tokens") or usage.get("completion_tokens") or 0,
            }
            on_response(reply, tokens)
        except Exception as e:
            if self.conversation_history and isinstance(
                self.conversation_history[-1], HumanMessage
            ):
                self.conversation_history.pop()
            on_error(str(e))


class AnthropicProvider(_LangChainChatProvider):
    """Anthropic Claude API provider using LangChain."""

    def _initialize_llm(self):
        api_key = get_api_key("ANTHROPIC_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(self.config, "API", "model", "claude-opus-4-5")

        self.llm = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            temperature=0.7,
        )


class OpenAIProvider(_LangChainChatProvider):
    """OpenAI GPT API provider using LangChain."""

    def _initialize_llm(self):
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(self.config, "API_OPENAI", "model", "gpt-4-turbo")

        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=0.7,
        )


class OpenRouterProvider(_LangChainChatProvider):
    """OpenRouter — one API key, many models (OpenAI-compatible + vision)."""

    def _initialize_llm(self):
        if ChatOpenAI is None:
            self.llm = None
            return

        api_key = get_api_key("OPENROUTER_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(
            self.config, "API_OPENROUTER", "model", DEFAULT_OPENROUTER_MODEL
        )

        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "https://github.com/openrouter",
                "X-Title": APP_NAME or "AI Overlay Agent",
            },
        )


class GeminiProvider(APIProvider):
    """Google Gemini API provider (native API)."""
    
    def _initialize_llm(self):
        """Initialize Gemini using native google.generativeai library."""
        if not genai_available:
            self.llm = None
            return

        api_key = get_api_key("GEMINI_API_KEY")
        if not api_key:
            self.llm = None
            return

        genai.configure(api_key=api_key)
        model_name = get_config_value(self.config, "API_GEMINI", "model", "gemini-2.5-pro")
        self.llm = genai.GenerativeModel(model_name, system_instruction=self.system_prompt)

    def apply_system_prompt(self, prompt_text):
        """Rebuild Gemini model so system_instruction takes effect."""
        self.system_prompt = prompt_text
        if not genai_available or self.llm is None:
            return
        model_name = get_config_value(self.config, "API_GEMINI", "model", "gemini-2.5-pro")
        self.llm = genai.GenerativeModel(model_name, system_instruction=self.system_prompt)
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to Gemini via native API."""
        try:
            if not self._ensure_llm():
                if not genai_available:
                    on_error("google-generativeai is not installed in this build.")
                else:
                    on_error(self._missing_key_message())
                return

            gen_config = genai.types.GenerationConfig()

            if isinstance(message_content, str):
                self.add_text_message(message_content)
                response = self.llm.generate_content(
                    message_content, generation_config=gen_config
                )
            elif isinstance(message_content, dict) and "images" in message_content:
                images_b64 = message_content["images"]
                text = message_content.get("text") or ""
                self.add_multi_image_message(images_b64, text)
                pil_images = []
                for b64 in images_b64:
                    pil_images.append(Image.open(io.BytesIO(base64.b64decode(b64))))
                payload = pil_images + ([text] if text else [])
                response = self.llm.generate_content(
                    payload, generation_config=gen_config
                )
            else:
                base64_image = message_content["image"]
                text = message_content.get("text") or ""
                self.add_image_message(base64_image, text)
                image = Image.open(io.BytesIO(base64.b64decode(base64_image)))
                payload = [image, text] if text else [image]
                response = self.llm.generate_content(
                    payload, generation_config=gen_config
                )
            
            # Safe text extraction handling safety block / candidacy issues
            try:
                reply = response.text
            except ValueError:
                # Typically occurs when response is blocked or contains no candidates
                try:
                    if hasattr(response, "prompt_feedback") and response.prompt_feedback.block_reason:
                        reply = f"[Blocked by Gemini Safety Filters. Reason: {response.prompt_feedback.block_reason}]"
                    else:
                        reply = "[No response text generated by the model. It might have been blocked or failed.]"
                except Exception:
                    reply = "[No response text generated by the model.]"
            
            if not reply.strip():
                reply = "[Empty response returned by the model.]"
            
            self.add_assistant_message(reply)
            
            tokens = {"input": 0, "output": 0}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens["input"] = getattr(response.usage_metadata, "prompt_token_count", 0)
                tokens["output"] = getattr(response.usage_metadata, "candidates_token_count", 0)
            
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


def get_provider(config, system_prompt=None):
    """Factory function to create the appropriate API provider using LangChain."""
    provider_name = get_config_value(config, "API", "provider", "openrouter").lower()
    prompt = system_prompt or get_default_system_prompt()

    if provider_name == "openrouter":
        return OpenRouterProvider(config, system_prompt=prompt)
    if provider_name == "openai":
        return OpenAIProvider(config, system_prompt=prompt)
    if provider_name == "gemini":
        return GeminiProvider(config, system_prompt=prompt)
    if provider_name == "anthropic":
        return AnthropicProvider(config, system_prompt=prompt)
    return OpenRouterProvider(config, system_prompt=prompt)


