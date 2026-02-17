
import urllib.request
import urllib.error
import sys

def check_ollama():
    url = "http://localhost:11434"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                print("Ollama is reachable.")
                return 0
            else:
                print(f"Ollama returned status: {response.status}")
                return 1
    except urllib.error.URLError as e:
        print(f"Ollama check failed: {e}")
        return 1
    except Exception as e:
        print(f"Ollama check error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_ollama())
