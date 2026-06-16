import sys
from pathlib import Path
from PIL import Image

# Paths
src_dir = Path(__file__).resolve().parents[1] / 'src' / 'ui'
png_path = src_dir / 'icon.png'
ico_path = src_dir / 'icon.ico'

if not png_path.is_file():
    print(f'PNG icon not found at {png_path}')
    sys.exit(1)

# Load PNG and convert to ICO (multiple sizes for Windows)
im = Image.open(png_path)
# Ensure it's RGBA
if im.mode != 'RGBA':
    im = im.convert('RGBA')
# Save as ICO with common sizes
im.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f'Icon saved to {ico_path}')
