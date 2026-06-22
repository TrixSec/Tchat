import sys
import os

# Add the client subdirectory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "client")))

from client import main

if __name__ == "__main__":
    main()