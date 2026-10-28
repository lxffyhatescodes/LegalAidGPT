# Legal Aid AI Assistant

Local RAG assistant: legal documents -> ingestion -> local retrieval -> local LLM -> Streamlit UI.
No external APIs. See the Architecture Guide for the full design and role ownership (P1 to P10).

## 0. Open in VS Code
- File > Open Folder... and choose the `legal-aid-assistant` folder (open the folder, not a single file).
- Accept the prompt to install the recommended extensions (Python, Pylance, Jupyter).
- Open the integrated terminal with Ctrl+` and follow the steps below.
- After creating `.venv` (step 2), press Ctrl+Shift+P, run **Python: Select Interpreter**, and pick `.venv`.
  On Windows, change `python.defaultInterpreterPath` in `.vscode/settings.json` to `${workspaceFolder}/.venv/Scripts/python.exe`.

## 1. Prerequisites
- Python 3.11 or 3.12 (3.10 to 3.12 supported). Check with `python --version`.
- Git.
- About 8 GB RAM minimum for a 3B model; 16 GB is more comfortable. A GPU is optional.

## 2. Create the virtual environment
Windows (PowerShell):
    python -m venv .venv
    .venv\Scripts\Activate.ps1
macOS / Linux:
    python3 -m venv .venv
    source .venv/bin/activate

## 3. Install dependencies
    python -m pip install --upgrade pip
    pip install -r requirements.txt

## 4. Set up the local LLM (choose one route)
Route A, in-process (no server, simplest to explain as "fully local"):
    pip install llama-cpp-python
  Download a small instruct model in GGUF format (3B to 8B, Q4 quantization) and save it as
  `models/model.gguf`. Set `LLM_BACKEND = "llama_cpp"` in `assistant/config.py`.
  On Windows, if the install tries to compile and fails, install the "Build Tools for Visual Studio"
  or look for a prebuilt wheel for your Python version.

Route B, local server:
  Install Ollama (ollama.com), then:
    ollama pull llama3.2:3b
    pip install ollama
  Set `LLM_BACKEND = "ollama"` in `assistant/config.py`.
  Note: Ollama serves on localhost. Confirm with your instructor that a same-machine server counts as "local".

## 5. Download the embedding model once
The first run of `scripts/check_env.py` downloads the embedding model (needs internet one time).
After that the project works offline. To enforce offline mode afterwards:
    Windows:  setx HF_HUB_OFFLINE 1
    macOS/Linux:  export HF_HUB_OFFLINE=1

## 6. Verify everything
    python scripts/check_env.py

## 7. Run the app
    streamlit run ui/app.py
  It opens in your browser at http://localhost:8501 and runs entirely on your machine.
  In VS Code you can also press F5 and pick **Run Streamlit app**.
  `ui/app.py` is a working chat skeleton that calls `assistant/pipeline.py: ask()`, which is still a stub
  until P8 connects the real pipeline.

## 8. Team workflow
- One Git branch per role (for example `p4-extraction`), merge through P8.
- Do not commit `models/` or `data/index/` (they are in `.gitignore`); share model files another way.
- Folder ownership is in the Architecture Guide, section 8.
