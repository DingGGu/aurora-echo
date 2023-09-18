.PHONY: build

all: build

clean:

build:
	pipenv run pyinstaller --onefile aurora_echo.py

release:
	pipenv install --deploy --dev
	pipenv run pyinstaller aurora_echo.spec
	shasum -a 256 dist/aurora_echo | cut -d ' ' -f 1 | tee dist/aurora_echo.sha256