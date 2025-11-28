# Server Setup

## MacOS

Make sure that you are on python@3.10.X to ensure all dependencies are installed correctly.
(Note: Windows currently runs with python@3.13.2)

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

## Windows

1. Create a python virtual environment
    - `python3 -m venv .venv`
2. Activate the virtual environment
    - `source .venv/bin/activate`
3. Go to the following link and follow the instructions to install espeak-ng:
    - `https://github.com/espeak-ng/espeak-ng/blob/master/docs/guide.md#windows`
4. Then add the install to your system environment variables:
    - In PowerShell: `$env:PHONEMIZER_ESPEAK_LIBRARY = "C:\Program Files\eSpeak NG\libespeak-ng.dll"`
5. Install requirements
    - `pip install -r requirements.txt`
6. Run the server as a module
    - `python3 -m src.llm.server`
7. To run a test:
    - In a first terminal: `python3 -m src.llm.server`
    - In another terminal: `python3 src/llm/test/simulate_connecting_client.py`
8. To deactivate the virtual env
    - `deactivate`
