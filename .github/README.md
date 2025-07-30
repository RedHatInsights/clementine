# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing and quality assurance.

## Workflows

### `test.yml` - Test Suite
- **Triggers**: Pull requests and pushes to `main`/`master`
- **Python versions**: 3.11  
- **Features**:
  - Runs full test suite with pytest
  - Generates test coverage report
  - Caches pipenv dependencies for faster builds

### `lint.yml` - Code Quality
- **Triggers**: Pull requests and pushes to `main`/`master`
- **Features**:
  - Basic syntax and error checking with flake8
  - Focuses on critical errors (syntax, undefined names, etc.)
  - Lightweight checks suitable for existing codebase

## Local Development

To run the same checks locally:

```bash
# Run tests
pipenv run python -m pytest tests/ -v

# Run test coverage  
pipenv run python -m pytest tests/ --cov=clementine --cov-report=term-missing

# Run linting
pipenv run flake8 clementine/ tests/ --max-line-length=120 --extend-ignore=E203,W503,E501 --select=E9,F63,F7,F82
```

## Status Checks

Both workflows provide status checks that can be required for PR merges:
- **Tests**: Must pass for code functionality
- **Lint**: Should pass for code quality (can be informational) 