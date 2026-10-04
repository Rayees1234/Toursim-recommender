import sys
import os

# Add workspace root to sys.path for test discovery
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
