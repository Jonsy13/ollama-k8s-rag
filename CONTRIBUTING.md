# Contributing to K8s RAG Agent

Thank you for your interest in contributing to the K8s RAG Agent project! 🎉

## 📋 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and encourage diverse contributions
- Focus on constructive feedback
- Help each other learn and grow

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/k8s-rag-agent.git
cd k8s-rag-agent
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional)
pre-commit install
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## 🔨 Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_main.py -v
```

### Code Quality

```bash
# Format code
black src/ examples/ tests/
isort src/ examples/ tests/

# Lint code
flake8 src/ examples/ tests/

# Type checking
mypy src/
```

### Running Locally

```bash
# Start required services
docker run -d -p 6333:6333 qdrant/qdrant
ollama serve  # In separate terminal

# Pull models
ollama pull tinyllama
ollama pull all-minilm

# Run the agent
uvicorn src.main:app --reload --port 8000
```

## 📝 Commit Guidelines

### Commit Message Format

```
type(scope): subject

body (optional)

footer (optional)
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```bash
feat(k8s): add node affinity support
fix(rag): resolve embedding dimension mismatch
docs(readme): update installation instructions
test(api): add integration tests for cluster endpoints
```

## 🧪 Testing Guidelines

### Writing Tests

- Place tests in `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test names
- Include docstrings explaining what is tested
- Mock external dependencies (K8s API, Ollama, etc.)

Example:
```python
def test_cluster_cpu_metrics():
    """Test that cluster CPU metrics are correctly calculated."""
    # Arrange
    mock_metrics = {...}
    
    # Act
    result = calculate_cpu_utilization(mock_metrics)
    
    # Assert
    assert result["utilization_percent"] == 50.0
```

## 📚 Documentation

### Updating Documentation

- Update `README.md` for user-facing changes
- Update `docs/DEPLOYMENT_STEPS.md` for deployment changes
- Add docstrings to all public functions and classes
- Include type hints in function signatures

### Docstring Format

```python
def function_name(param1: str, param2: int) -> dict:
    """
    Brief description of function.
    
    Longer description if needed, explaining the purpose
    and behavior of the function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
    """
    pass
```

## 🔍 Pull Request Process

### Before Submitting

- [ ] Run all tests and ensure they pass
- [ ] Run linters and formatters
- [ ] Update documentation if needed
- [ ] Add/update tests for new features
- [ ] Ensure commit messages follow guidelines
- [ ] Rebase on latest main branch

### Submitting PR

1. Push your branch to your fork
2. Create a Pull Request on GitHub
3. Fill out the PR template completely
4. Link any related issues
5. Request review from maintainers

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Existing tests pass
- [ ] Added new tests
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
```

## 🎯 Areas for Contribution

### Good First Issues

- Documentation improvements
- Adding more examples
- Writing tests
- Fixing typos

### Feature Requests

- Support for additional LLM providers
- Enhanced K8s resource monitoring
- Authentication/authorization
- Prometheus metrics integration
- Helm chart

### Bug Reports

When reporting bugs, include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, K8s version, etc.)
- Relevant logs or error messages

## 💬 Communication

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, general discussion
- **Pull Requests**: Code contributions

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions help make this project better for everyone. We appreciate your time and effort! ⭐
