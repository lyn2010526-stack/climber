# Contributing to Climber

## Development Setup

```bash
git clone https://github.com/lyn2010526-stack/climber.git
cd climber/agent-engine
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if exists
```

## Code Style

- Python: PEP 8, type hints, max line length 100
- TypeScript: ESLint + Prettier config
- Commit messages: Conventional Commits

## Pull Request Process

1. Create feature branch from main
2. Implement changes with tests
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description

## Testing

```bash
python3 -m pytest tests/ -v --tb=short
```

## Code Review Checklist

- [ ] Tests pass
- [ ] Type hints present
- [ ] No hardcoded secrets
- [ ] Error handling included
- [ ] Documentation updated
