import base64
from pathlib import Path

# Path to your image
img_path = Path("paystream/static/elements/images/logo/logo_text.png")

# Read and encode the image
with img_path.open("rb") as img_file:
    base64_string = base64.b64encode(img_file.read()).decode("utf-8")

# Save the base64 string as a Python variable inside this file
output_path = Path("logo.py")
with output_path.open("w") as f:
    f.write(f'LOGO_BASE64 = "{base64_string}"\n')

print(f"Base64 string written to {output_path.resolve()}")
