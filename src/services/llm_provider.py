import io
import base64
from PIL import Image
from src.config.prompts import load_system_prompt
from src.config.settings import get_config_value, api_key_env_name, get_api_key, load_environment
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
    
    def __init__(self, config):
        self.config = config
        self.conversation_history = []
        self.system_prompt = load_system_prompt()
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
        self.conversation_history.append(
            HumanMessage(
                content=[
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ]
            )
        )

    def add_multi_image_message(self, images_b64, text):
        """Add a multi-image message to history."""
        content = [{"type": "text", "text": text}]
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


class AnthropicProvider(APIProvider):
    """Anthropic Claude API provider using LangChain."""
    
    def _initialize_llm(self):
        """Initialize Claude via LangChain."""
        api_key = get_api_key("ANTHROPIC_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(self.config, "API", "model", "claude-opus-4-5")
        self.max_tokens = int(get_config_value(self.config, "API", "max_tokens", "1500"))
        
        self.llm = ChatAnthropic(
            model=model_name,
            max_tokens=self.max_tokens,
            temperature=0.7
        )
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to Claude via LangChain."""
        try:
            if not self._ensure_llm():
                on_error(self._missing_key_message())
                return

            self._add_user_content(message_content)
            self.trim_history()
            
            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            response = self.llm.invoke(messages)
            reply = response.content
            self.add_assistant_message(reply)
            
            tokens = {
                "input": response.response_metadata.get("usage", {}).get("input_tokens", 0),
                "output": response.response_metadata.get("usage", {}).get("output_tokens", 0)
            }
            
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


class OpenAIProvider(APIProvider):
    """OpenAI GPT API provider using LangChain."""
    
    def _initialize_llm(self):
        """Initialize GPT via LangChain."""
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            self.llm = None
            return

        model_name = get_config_value(self.config, "API_OPENAI", "model", "gpt-4-turbo")
        self.max_tokens = int(get_config_value(self.config, "API", "max_tokens", "1500"))
        
        self.llm = ChatOpenAI(
            model=model_name,
            max_tokens=self.max_tokens,
            temperature=0.7
        )
    
    def send_message(self, message_content, on_response, on_error):
        """Send message to OpenAI via LangChain."""
        try:
            if not self._ensure_llm():
                on_error(self._missing_key_message())
                return

            self._add_user_content(message_content)
            self.trim_history()
            
            messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
            response = self.llm.invoke(messages)
            reply = response.content
            self.add_assistant_message(reply)
            
            tokens = {
                "input": response.response_metadata.get("usage", {}).get("prompt_tokens", 0),
                "output": response.response_metadata.get("usage", {}).get("completion_tokens", 0)
            }
            
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


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
        self.max_tokens = int(get_config_value(self.config, "API", "max_tokens", "1500"))
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

            gen_config = genai.types.GenerationConfig(max_output_tokens=self.max_tokens)

            if isinstance(message_content, str):
                self.add_text_message(message_content)
                response = self.llm.generate_content(
                    message_content, generation_config=gen_config
                )
            elif isinstance(message_content, dict) and "images" in message_content:
                images_b64 = message_content["images"]
                text = message_content["text"]
                self.add_multi_image_message(images_b64, text)
                pil_images = []
                for b64 in images_b64:
                    pil_images.append(Image.open(io.BytesIO(base64.b64decode(b64))))
                response = self.llm.generate_content(
                    pil_images + [text], generation_config=gen_config
                )
            else:
                base64_image = message_content["image"]
                text = message_content["text"]
                self.add_image_message(base64_image, text)
                image = Image.open(io.BytesIO(base64.b64decode(base64_image)))
                response = self.llm.generate_content(
                    [image, text], generation_config=gen_config
                )
            
            reply = response.text
            self.add_assistant_message(reply)
            
            tokens = {"input": 0, "output": 0}
            on_response(reply, tokens)
            
        except Exception as e:
            if self.conversation_history and isinstance(self.conversation_history[-1], HumanMessage):
                self.conversation_history.pop()
            on_error(str(e))


def get_provider(config):
    """Factory function to create the appropriate API provider using LangChain."""
    provider_name = get_config_value(config, "API", "provider", "anthropic").lower()
    
    if provider_name == "openai":
        return OpenAIProvider(config)
    elif provider_name == "gemini":
        return GeminiProvider(config)
    else:  # Default to Anthropic
        return AnthropicProvider(config)


