import sys
import os

# Add the server subdirectory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "server")))

from server import main

if __name__ == "__main__":
    main()
