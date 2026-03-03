import os
from datetime import datetime
from src.output.base import OutputDestination

class ObsidianExporter(OutputDestination):
    def __init__(self, export_path="obsidian_export.md"):
        self.export_path = export_path

    def output(self, text: str, is_final: bool = False):
        # We only want to export the final recognized text to avoid writing partial sentences repeatedly.
        if is_final and text:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(self.export_path, 'a') as f:
                    f.write(f"## {timestamp}\n{text}\n\n")
            except Exception as e:
                import logging
                logging.getLogger('Voice2Text').error(f"Failed to export to Obsidian: {e}")
