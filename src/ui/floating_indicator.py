import os
import Cocoa
import objc
from PIL import Image
from src.utils.logger import logger

class FloatingIndicator:
    def __init__(self, root):
        self.root = root
        self.is_visible = False
        
        # Load image asset path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.image_path = os.path.join(base_path, "assets", "floating_mic.png")
        
        # Setup pure native macOS NSPanel for the indicator
        # This guarantees it NEVER steals focus (NSWindowStyleMaskNonactivatingPanel)
        width, height = 180, 70
        screen_rect = Cocoa.NSScreen.mainScreen().frame()
        
        # Position 50px from bottom right
        x = screen_rect.size.width - width - 50
        y = 50 
        
        rect = Cocoa.NSMakeRect(x, y, width, height)
        style = Cocoa.NSWindowStyleMaskNonactivatingPanel | Cocoa.NSWindowStyleMaskBorderless
        
        self.panel = Cocoa.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, Cocoa.NSBackingStoreBuffered, False
        )
        self.panel.setLevel_(Cocoa.NSStatusWindowLevel) # Always on top
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(Cocoa.NSColor.clearColor())
        self.panel.setHasShadow_(True)
        self.panel.setIgnoresMouseEvents_(True) # Don't block clicks
        
        # Create a container view for background and styling
        self.container = Cocoa.NSView.alloc().initWithFrame_(Cocoa.NSMakeRect(0, 0, width, height))
        self.container.setWantsLayer_(True)
        self.container.layer().setBackgroundColor_(Cocoa.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.1, 0.1, 0.85).CGColor())
        self.container.layer().setCornerRadius_(12.0)
        
        # Add Icon (sloth) if exists
        self.icon_view = None
        if os.path.exists(self.image_path):
            ns_img = Cocoa.NSImage.alloc().initWithContentsOfFile_(self.image_path)
            if ns_img:
                ns_img.setSize_(Cocoa.NSMakeSize(50, 50))
                # x=10, y=10, width=50, height=50
                self.icon_view = Cocoa.NSImageView.alloc().initWithFrame_(Cocoa.NSMakeRect(10, 10, 50, 50))
                self.icon_view.setImage_(ns_img)
                self.container.addSubview_(self.icon_view)
        
        # Add Text Label
        text_x = 70 if self.icon_view else 15
        text_width = width - text_x - 10
        self.label = Cocoa.NSTextField.alloc().initWithFrame_(Cocoa.NSMakeRect(text_x, 22, text_width, 25))
        self.label.setStringValue_("Recording...")
        self.label.setBezeled_(False)
        self.label.setDrawsBackground_(False)
        self.label.setEditable_(False)
        self.label.setSelectable_(False)
        self.label.setTextColor_(Cocoa.NSColor.whiteColor())
        self.label.setFont_(Cocoa.NSFont.boldSystemFontOfSize_(15))
        
        self.container.addSubview_(self.label)
        self.panel.contentView().addSubview_(self.container)

    def show(self):
        if self.is_visible:
            return
            
        # Bring the panel to screen without stealing focus
        self.panel.orderFront_(None)
        self.is_visible = True

    def hide(self):
        if not self.is_visible:
            return
            
        self.panel.orderOut_(None)
        self.is_visible = False
