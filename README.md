# setup in linux
rm -rf venv-us
python3 -m venv venv-us
source venv-us/bin/activate
pip3 install jupyter ipykernel playwright
playwright install chromium

# extra setup
python3 -m ipykernel install --uspython --versioner --name=venv-us