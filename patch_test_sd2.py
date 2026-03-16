with open("test_sounddevice.py", "r") as f:
    content = f.read()

content = content.replace("import sounddevice as sd\nimport numpy as np", "try:\n    import sounddevice as sd\n    import numpy as np\nexcept ImportError:\n    import pytest\n    pytest.skip('macOS only test', allow_module_level=True)")

with open("test_sounddevice.py", "w") as f:
    f.write(content)
