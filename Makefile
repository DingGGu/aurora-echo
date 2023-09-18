.PHONY: build

all: build

clean:

build:
	pipenv install --deploy
	pipenv run pyinstaller --onefile aurora_echo.py

release:
	pipenv install --deploy
	pipenv run pyinstaller aurora_echo.spec
	shasum -a 256 dist/aurora_echo | cut -d ' ' -f 1 > dist/aurora_echo-shasum-256.txt