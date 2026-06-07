import os
import sys
import tkinter as tk
from dotenv import load_dotenv

# Add the project root to sys.path so 'src' can be imported everywhere
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.config.settings import load_config, load_environment
from src.config.models import normalize_config_model
from src.licensing import run_license_gate
from src.ui.app import OverlayApp
from src.ui.cursor import apply_global_cursor_defaults, refresh_cursor_policy
from src.utils.error_handler import install_in_app_error_handlers

def main():
    load_environment()
    config = load_config()
    normalize_config_model(config)

    root = tk.Tk()
    if not run_license_gate(root, config):
        root.destroy()
        return

    # Initialize optional modules
    try:
        from modules.personal_context import PersonalContextManager
        personal_context_manager = PersonalContextManager()
    except Exception as e:
        print(f"Failed to load PersonalContextManager: {e}")
        personal_context_manager = None

    apply_global_cursor_defaults(root)
    root.configure(cursor="arrow")
    app = OverlayApp(root, config, personal_context_manager=personal_context_manager)
    refresh_cursor_policy(root)
    
    install_in_app_error_handlers(app)
    
    # Check dependencies warning
    try:
        import langchain_openai
    except ImportError:
        app.add_system_message("⚠ Warning: langchain is not fully installed. Run `pip install -r requirements.txt`")

    root.mainloop()

if __name__ == '__main__':
    main()
