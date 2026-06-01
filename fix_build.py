import os

for filename in os.listdir('build'):
    filepath = os.path.join('build', filename)
    if os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'ai_overlay.py' in content:
            new_content = content.replace('ai_overlay.py', 'main.py')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {filename}")
