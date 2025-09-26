# Discord Partybot Development Scripts
param([string]$Command)

switch ($Command) {
    "install" {
        Write-Host "Installing project dependencies..."
        uv sync
    }
    "dev" {
        Write-Host "Installing development dependencies..."
        uv sync --group dev
    }
    "run" {
        Write-Host "Starting Discord bot..."
        uv run python main.py
    }
    "format" {
        Write-Host "Formatting code..."
        uv run black .
    }
    "lint" {
        Write-Host "Running linter..."
        uv run flake8 .
    }
    "type-check" {
        Write-Host "Running type checker..."
        uv run mypy .
    }
    "test" {
        Write-Host "Running tests..."
        uv run pytest
    }
    "clean" {
        Write-Host "Cleaning cache files..."
        Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force .mypy_cache -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force *.egg-info -ErrorAction SilentlyContinue
        Remove-Item -Force *.log -ErrorAction SilentlyContinue
        Write-Host "Clean completed!"
    }
    "add" {
        Write-Host "To add new dependencies:"
        Write-Host "  uv add package-name"
    }
    "setup-env" {
        Write-Host "Setting up environment configuration..."
        if (Test-Path .env.example) {
            if (-not (Test-Path .env)) {
                Copy-Item .env.example .env
                Write-Host "Created .env file from template"
                Write-Host "Please edit .env file and add your API keys:"
                Write-Host "  - DISCORD_TOKEN (required)"
                Write-Host "  - YOUTUBE_API_KEY (required for music)"

                Write-Host "  - SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET (optional)"
            } else {
                Write-Host ".env file already exists"
            }
        } else {
            Write-Host "Error: .env.example template not found"
        }
    }
    "help" {
        Write-Host "Available commands:"
        Write-Host "  install     - Install project dependencies"
        Write-Host "  dev         - Install development dependencies"
        Write-Host "  run         - Start Discord bot"
        Write-Host "  setup-env   - Create .env file from template"
        Write-Host "  format      - Format code with black"
        Write-Host "  lint        - Run flake8 linter"
        Write-Host "  type-check  - Run mypy type checker"
        Write-Host "  test        - Run pytest tests"
        Write-Host "  clean       - Clean cache files"
        Write-Host "  add         - Show how to add dependencies"
        Write-Host "  help        - Show this help message"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\scripts.ps1 install"
        Write-Host "  .\scripts.ps1 run"
        Write-Host "  .\scripts.ps1 format"
    }
    default {
        Write-Host "Unknown command: $Command"
        Write-Host "Use '.\scripts.ps1 help' to see available commands"
    }
}