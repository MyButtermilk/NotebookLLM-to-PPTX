# Contributing to SlideRefactor

Thank you for your interest in contributing to SlideRefactor! This document provides guidelines for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/NotebookLLM-to-PPTX.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit: `git commit -m 'Add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Open a Pull Request

## Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Or with Poetry
poetry install
poetry shell

# Run tests
pytest tests/

# Run linters
black sliderefactor/
ruff check sliderefactor/
mypy sliderefactor/
```

## Code Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use type hints for all functions
- Write docstrings for public APIs

## Testing

- Add tests for new features
- Ensure existing tests pass
- Maintain test coverage >80%

## Pull Request Process

1. Update README.md with details of changes if needed
2. Update the examples if you change the API
3. Ensure all tests pass
4. Request review from maintainers

## Areas for Contribution

- **Extractors**: Add support for new OCR engines
- **Renderers**: Implement PptxGenJS JavaScript renderer
- **Layout Detection**: Integrate LayoutParser or DocLayout-YOLO
- **Preprocessing**: Add more OpenCV filters
- **Documentation**: Improve docs and examples
- **Tests**: Add more test cases
- **Performance**: Optimize extraction and rendering

## Questions?

Open an issue or start a discussion!
