"""
Streaming utilities for faster perceived performance
"""

import sys
from utils.logger import setup_logger

logger = setup_logger(__name__)

class StreamingOutput:
    """
    Stream output to user for better UX
    """
    
    @staticmethod
    def stream_text(text, delay=0.01):
        """
        Stream text character by character
        
        Args:
            text: Text to stream
            delay: Delay between characters (seconds)
        """
        import time
        
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        
        print()  # Newline at end
    
    @staticmethod
    def stream_thinking(message="Thinking"):
        """
        Show animated thinking indicator
        
        Args:
            message: Base message to show
        """
        import time
        
        for i in range(3):
            sys.stdout.write(f"\r{message}{'.' * (i + 1)}   ")
            sys.stdout.flush()
            time.sleep(0.3)
        
        sys.stdout.write("\r" + " " * 50 + "\r")  # Clear line
        sys.stdout.flush()
    
    @staticmethod
    def show_progress(current, total, message="Processing"):
        """
        Show progress bar
        
        Args:
            current: Current progress
            total: Total items
            message: Progress message
        """
        percent = int((current / total) * 100)
        bar_length = 30
        filled = int((bar_length * current) / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        sys.stdout.write(f"\r{message}: [{bar}] {percent}%")
        sys.stdout.flush()
        
        if current == total:
            print()  # Newline when complete