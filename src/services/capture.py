import io
import base64
from PIL import ImageGrab, Image
# ============================================================================
# SCREENSHOT CAPTURE AND COMPRESSION
# ============================================================================

def capture_and_compress_screenshot(max_width=1280, jpeg_quality=82):
    """Capture screen, compress to JPEG, encode as base64."""
    try:
        # Capture screenshot
        screenshot = ImageGrab.grab()
        
        # Resize if needed
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            new_height = int(screenshot.height * ratio)
            screenshot = screenshot.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to JPEG and compress
        jpeg_buffer = io.BytesIO()
        screenshot.convert("RGB").save(jpeg_buffer, format="JPEG", quality=jpeg_quality)
        jpeg_buffer.seek(0)
        
        # Encode to base64
        base64_image = base64.b64encode(jpeg_buffer.read()).decode("utf-8")
        return base64_image
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None


