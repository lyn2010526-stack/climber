# Contributing to Climber

For security vulnerabilities, follow the private reporting process in [docs/SECURITY.md](docs/SECURITY.md).

## Development Setup

```bash
git clone https://github.com/lyn2010526-stack/climber.git
cd climber
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Frontend checks run from `frontend-react`:

```bash
cd frontend-react
npm install
npm run typecheck
npm run lint
npm test
npm run build
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
- [ ] `.env.example` updated when configuration changes
- [ ] No secrets, user data, local databases or build artifacts included
