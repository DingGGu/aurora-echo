PYTHON_MAIN=aurora_echo/__init__.py
FINAL_EXECUTABLE=aurora-echo
BUILD_DIR=build
PYTHON_INTERPRETER=python3

.PHONY: all clean build lint

all: clean build

clean:
	@rm -rf *.pyc
	@echo "Project .pyc's removed."
	@rm -rf $(BUILD_DIR)
	@echo "Build directory removed."

build:
	#rm -f $(BUILD_DIR)/$(FINAL_EXECUTABLE)
	pipenv install --deploy
	python eggsecute.py $(PYTHON_MAIN) $(BUILD_DIR)/$(FINAL_EXECUTABLE)
	chmod a+x $(BUILD_DIR)/$(FINAL_EXECUTABLE)
	echo "Package created."

lint:
	python setup.py flake8
