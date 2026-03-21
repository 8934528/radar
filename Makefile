# Makefile for Radar System Project
# Variables
PYTHON = python
PROJECT_ROOT = $(shell pwd)
BACKEND_DIR = $(PROJECT_ROOT)/backend
VENV_DIR = $(BACKEND_DIR)/venv
VENV_ACTIVATE = $(VENV_DIR)/bin/activate
PIP = $(VENV_DIR)/bin/pip
PYTHON_VENV = $(VENV_DIR)/bin/python
REQUIREMENTS = $(BACKEND_DIR)/requirements.txt

# Default target
.PHONY: help
help:
	@echo "Radar System Project Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make all          - Complete setup: check Python, create venv, install deps, run"
	@echo "  make setup        - Create virtual environment and install dependencies"
	@echo "  make install      - Install dependencies only (venv must exist)"
	@echo "  make run          - Run the main application"
	@echo "  make clean        - Remove virtual environment and cache files"
	@echo "  make check        - Check Python version and environment status"
	@echo "  make info         - Show virtual environment information"
	@echo "  make dev          - Setup development environment"
	@echo "  make help         - Show this help message"
	@echo ""

# All: Complete setup and run
.PHONY: all
all: check_python setup run
	@echo ""
	@echo "✓ Complete setup and execution finished"

# Check Python version on host system
.PHONY: check_python
check_python:
	@echo "Checking Python version on your system..."
	@command -v $(PYTHON) >/dev/null 2>&1 || (echo "Error: Python is not installed or not in PATH. Please install Python 3.8 or higher." && exit 1)
	@$(PYTHON) -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" || (echo "Error: Python 3.8 or higher is required. Your Python version:" && $(PYTHON) --version && exit 1)
	@echo "✓ Python version OK: $(shell $(PYTHON) --version)"

# Check if backend directory exists
.PHONY: check_backend
check_backend:
	@test -d "$(BACKEND_DIR)" || (echo "Error: Backend directory not found at $(BACKEND_DIR)" && echo "Please ensure you're running make from the project root directory" && exit 1)
	@test -f "$(REQUIREMENTS)" || (echo "Error: requirements.txt not found at $(REQUIREMENTS)" && exit 1)

# Check if virtual environment exists and is valid
.PHONY: check_venv
check_venv:
	@if [ -d "$(VENV_DIR)" ] && [ -f "$(PYTHON_VENV)" ]; then \
		echo "✓ Virtual environment found at $(VENV_DIR)"; \
	else \
		echo "Virtual environment not found or corrupted"; \
		exit 1; \
	fi

# Setup: Create virtual environment and install dependencies
.PHONY: setup
setup: check_backend
	@echo ""
	@echo "Setting up virtual environment..."
	@if [ -d "$(VENV_DIR)" ] && [ -f "$(PYTHON_VENV)" ]; then \
		echo "✓ Virtual environment already exists and is valid"; \
	else \
		if [ -d "$(VENV_DIR)" ]; then \
			echo "Virtual environment is corrupted, removing..."; \
			rm -rf "$(VENV_DIR)"; \
		fi; \
		echo "Creating new virtual environment in $(BACKEND_DIR)..."; \
		cd $(BACKEND_DIR) && $(PYTHON) -m venv venv; \
	fi
	@echo "✓ Virtual environment ready at $(VENV_DIR)"
	@echo ""
	@echo "Installing dependencies from $(REQUIREMENTS)..."
	@echo "This may take a few moments..."
	@cd $(BACKEND_DIR) && $(PIP) install --upgrade pip
	@cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt
	@if [ $$? -ne 0 ]; then \
		echo "Error: Failed to install dependencies"; \
		exit 1; \
	fi
	@echo "✓ All dependencies installed successfully"
	@echo ""
	@echo "To activate the virtual environment manually:"
	@echo "  cd $(BACKEND_DIR) && source venv/bin/activate"
	@echo "  or run: make run"
	@echo ""

# Create virtual environment only
.PHONY: create_venv
create_venv: check_backend
	@echo "Creating virtual environment..."
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment already exists. Use 'make clean' first if you want to recreate."; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && $(PYTHON) -m venv venv
	@echo "✓ Virtual environment created at $(VENV_DIR)"

# Install dependencies only (venv must exist)
.PHONY: install
install: check_backend check_venv
	@echo "Installing dependencies..."
	@cd $(BACKEND_DIR) && $(PIP) install --upgrade pip
	@cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt
	@if [ $$? -ne 0 ]; then \
		echo "Error: Failed to install dependencies"; \
		exit 1; \
	fi
	@echo "✓ Dependencies installed"

# Run the main application
.PHONY: run
run: check_backend check_venv
	@echo "Running Radar System..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@cd $(BACKEND_DIR) && $(PYTHON_VENV) main.py
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ Application finished"

# Clean up: remove virtual environment and cache files
.PHONY: clean
clean:
	@echo "Cleaning up..."
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Removing virtual environment..."; \
		rm -rf "$(VENV_DIR)"; \
		echo "  ✓ Removed virtual environment"; \
	else \
		echo "  Virtual environment not found"; \
	fi
	@echo "Removing Python cache files..."
	@find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type f -name "*.pyc" -delete 2>/dev/null || true
	@find $(BACKEND_DIR) -type f -name "*.pyo" -delete 2>/dev/null || true
	@find $(BACKEND_DIR) -type f -name "*.so" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Check environment status
.PHONY: check
check: check_python check_backend
	@echo ""
	@echo "Checking environment..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Project root: $(PROJECT_ROOT)"
	@echo "Backend directory: $(BACKEND_DIR)"
	@echo ""
	@echo "System Python version:"
	@$(PYTHON) --version
	@echo ""
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Virtual Environment:"; \
		echo "  ✓ Virtual environment exists at $(VENV_DIR)"; \
		if [ -f "$(PYTHON_VENV)" ]; then \
			echo "  ✓ Python interpreter found"; \
			echo "  Version:"; \
			$(PYTHON_VENV) --version; \
		else \
			echo "  ✗ Python interpreter not found - venv may be corrupted"; \
		fi \
	else \
		echo "  ✗ Virtual environment not found"; \
	fi
	@echo ""
	@if [ -f "$(REQUIREMENTS)" ]; then \
		echo "  ✓ $(REQUIREMENTS) exists"; \
	else \
		echo "  ✗ $(REQUIREMENTS) not found"; \
	fi
	@if [ -d "$(VENV_DIR)" ] && [ -f "$(PIP)" ]; then \
		echo ""; \
		echo "Installed packages:"; \
		cd $(BACKEND_DIR) && $(PIP) list; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ Environment check complete"

# Show virtual environment info
.PHONY: info
info: check_backend
	@echo "Virtual Environment Information:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Project root: $(PROJECT_ROOT)"
	@echo "  Backend:      $(BACKEND_DIR)"
	@echo "  Location:     $(VENV_DIR)"
	@echo "  Python:       $(PYTHON_VENV)"
	@echo "  Pip:          $(PIP)"
	@echo "  Requirements: $(REQUIREMENTS)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment exists and is ready to use."; \
	else \
		echo "Virtual environment does not exist. Run 'make setup' to create it."; \
	fi
	@echo ""
	@echo "To activate manually:"
	@echo "  cd $(BACKEND_DIR) && source venv/bin/activate"
	@echo ""
	@echo "To deactivate: deactivate"

# Development mode
.PHONY: dev
dev: check_backend check_venv
	@echo "Setting up development environment..."
	@cd $(BACKEND_DIR) && $(PIP) install --upgrade pip
	@cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt
	@echo "✓ Development environment ready"
	@echo ""
	@echo "You can now run: make run"

# Default target
.DEFAULT_GOAL := help
