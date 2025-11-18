.PHONY: help install install-backend install-frontend run dev backend frontend clean test lint check-env setup

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Easy Ads - Creative Automation Pipeline$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup - install all dependencies and check environment
	@echo "$(BLUE)Setting up Easy Ads project...$(NC)"
	@$(MAKE) check-env
	@$(MAKE) install
	@echo "$(GREEN)✓ Setup complete!$(NC)"

check-env: ## Check if required environment variables are set
	@echo "$(BLUE)Checking environment variables...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)✗ .env file not found$(NC)"; \
		echo "$(YELLOW)Please create a .env file with REPLICATE_API_TOKEN$(NC)"; \
		exit 1; \
	fi
	@if ! grep -q "REPLICATE_API_TOKEN" .env; then \
		echo "$(RED)✗ REPLICATE_API_TOKEN not found in .env$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Environment variables configured$(NC)"

install: install-backend install-frontend ## Install all dependencies (backend + frontend)

install-backend: ## Install Python backend dependencies
	@echo "$(BLUE)Installing backend dependencies with uv...$(NC)"
	@uv sync
	@echo "$(GREEN)✓ Backend dependencies installed$(NC)"

install-frontend: ## Install Node.js frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

run: ## Run both backend and frontend in parallel (recommended)
	@echo "$(BLUE)Starting Easy Ads (backend + frontend)...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop both servers$(NC)"
	@trap 'kill 0' EXIT; \
	$(MAKE) backend & \
	$(MAKE) frontend & \
	wait

dev: run ## Alias for 'make run'

backend: check-env ## Run the FastAPI backend server only
	@echo "$(BLUE)Starting backend server...$(NC)"
	@echo "$(GREEN)Backend running at http://localhost:8000$(NC)"
	@echo "$(GREEN)API docs at http://localhost:8000/docs$(NC)"
	@cd backend && uv run python main.py

frontend: ## Run the React frontend dev server only
	@echo "$(BLUE)Starting frontend server...$(NC)"
	@echo "$(GREEN)Frontend running at http://localhost:5173$(NC)"
	@cd frontend && npm run dev

cli: check-env ## Run the CLI tool (main.py)
	@echo "$(BLUE)Running Easy Ads CLI...$(NC)"
	@uv run python main.py

build-frontend: ## Build the frontend for production
	@echo "$(BLUE)Building frontend for production...$(NC)"
	@cd frontend && npm run build
	@echo "$(GREEN)✓ Frontend built successfully$(NC)"

lint-frontend: ## Lint the frontend code
	@echo "$(BLUE)Linting frontend code...$(NC)"
	@cd frontend && npm run lint

lint: lint-frontend ## Run all linters

clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@rm -rf backend/__pycache__
	@rm -rf pipeline/__pycache__
	@rm -rf .pytest_cache
	@rm -rf frontend/dist
	@rm -rf frontend/node_modules/.vite
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned successfully$(NC)"

clean-all: clean ## Clean everything including dependencies
	@echo "$(BLUE)Cleaning all dependencies...$(NC)"
	@rm -rf .venv
	@rm -rf uv.lock
	@rm -rf frontend/node_modules
	@echo "$(GREEN)✓ All dependencies removed$(NC)"

test-backend: ## Run backend tests (if available)
	@echo "$(BLUE)Running backend tests...$(NC)"
	@uv run pytest tests/ 2>/dev/null || echo "$(YELLOW)No tests found$(NC)"

test: test-backend ## Run all tests

status: ## Show status of servers
	@echo "$(BLUE)Server Status:$(NC)"
	@echo ""
	@if lsof -ti:8000 > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Backend server running on port 8000$(NC)"; \
	else \
		echo "$(YELLOW)✗ Backend server not running$(NC)"; \
	fi
	@if lsof -ti:5173 > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Frontend server running on port 5173$(NC)"; \
	else \
		echo "$(YELLOW)✗ Frontend server not running$(NC)"; \
	fi

stop: ## Stop all running servers
	@echo "$(BLUE)Stopping servers...$(NC)"
	@-lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "$(GREEN)✓ Backend stopped$(NC)" || echo "$(YELLOW)Backend not running$(NC)"
	@-lsof -ti:5173 | xargs kill -9 2>/dev/null && echo "$(GREEN)✓ Frontend stopped$(NC)" || echo "$(YELLOW)Frontend not running$(NC)"

info: ## Show project information
	@echo "$(BLUE)Easy Ads - Project Information$(NC)"
	@echo ""
	@echo "$(GREEN)Project Structure:$(NC)"
	@echo "  backend/     - FastAPI backend server"
	@echo "  frontend/    - React frontend application"
	@echo "  pipeline/    - Image generation pipeline"
	@echo "  assets/      - Brand assets and style guides"
	@echo "  outputs/     - Generated images"
	@echo ""
	@echo "$(GREEN)Ports:$(NC)"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "$(GREEN)Package Management:$(NC)"
	@echo "  Using uv for fast Python dependency management"
	@echo "  uv sync      - Install/update dependencies"
	@echo "  uv add pkg   - Add a new package"
	@echo "  uv run cmd   - Run command in virtual environment"
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  1. make setup    - Initial setup"
	@echo "  2. make run      - Start both servers"
	@echo "  3. Visit http://localhost:5173"

add-pkg: ## Add a Python package (usage: make add-pkg PKG=package-name)
	@echo "$(BLUE)Adding package: $(PKG)$(NC)"
	@uv add $(PKG)
	@echo "$(GREEN)✓ Package $(PKG) added$(NC)"

uv-lock: ## Update uv.lock file
	@echo "$(BLUE)Updating uv.lock...$(NC)"
	@uv lock
	@echo "$(GREEN)✓ Lock file updated$(NC)"
