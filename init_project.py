import platform
import subprocess
import sys
import shutil

def is_tool(name):
    """Check whether `name` is on PATH."""
    return shutil.which(name) is not None

def setup_ollama():
    print("=== Checking System Requirements ===")
    
    if is_tool("ollama"):
        print("[OK] Ollama is already installed!")
    else:
        print("[WARN] Ollama not found on system PATH.")
        os_name = platform.system()
        if os_name == "Windows":
            print(">>> Attempting to install Ollama via winget...")
            try:
                subprocess.run(
                    ["winget", "install", "Ollama.Ollama", "--silent", "--accept-source-agreements", "--accept-package-agreements"], 
                    check=True
                )
                print("[OK] Ollama installed successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to install Ollama automatically: {e}")
                print("Please download and install it manually from https://ollama.com/download")
                sys.exit(1)
        else:
            print("Please install Ollama manually for your OS at: https://ollama.com/download")
            sys.exit(1)
            
    print("\n=== Pulling Local Base Model (mistral:7b) ===")
    print("This may take a few minutes if downloading for the first time (~4GB)...")
    try:
        # Run the pull command
        subprocess.run(["ollama", "pull", "mistral:7b"], check=True)
        print("[OK] Mistral model pulled successfully and is ready to serve!")
    except Exception as e:
        print(f"[ERROR] Failed to pull mistral: {e}")
        print("Please run 'ollama pull mistral' manually in your terminal.")
        sys.exit(1)

if __name__ == "__main__":
    setup_ollama()
    print("\n=== Setup Complete! You can now run the Router CLI ===")
