## Server Setup


### MacOS

Make sure that you are on python@3.10.X to ensure all dependencies are installed correctly.

1. Create a python virtual environment
    - `python3 -m venv .venv`
2. Activate the virtual environment
    - `source .venv/bin/activate`
3. Install external dependency "espeak-ng"
    - `brew install espeak-ng`
    - `export PHONEMIZER_ESPEAK_LIBRARY="/opt/homebrew/lib/libespeak-ng.dylib"`
4. Install requirements
    - `pip install -r requirements.txt`
5. Run the server as a module
    - `python3 -m src.llm.server`
6. To deactivate the virtual env
    - `deactivate`

### Windows
Windows instructions are incomplete, feel free to copy above and extend this
- `(PowerShell) $env:PHONEMIZER_ESPEAK_LIBRARY = "C:\Program Files\eSpeak NG\libespeak-ng.dll"`