import re

with open("test_audio.py", "r") as f:
    content = f.read()

content = content.replace("import Cocoa", "try:\n    import Cocoa\nexcept ImportError:\n    import pytest\n    pytest.skip('macOS only test', allow_module_level=True)\n    Cocoa = type('Dummy', (), {'NSObject': object})")

with open("test_audio.py", "w") as f:
    f.write(content)
