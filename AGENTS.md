# AGENTS.md - AI Coding Agent Instructions

This document provides guidelines for AI coding agents working on this codebase.

## Project Overview

**VideoAITranslateSub** - A video localization system with AI-powered subtitles, translation, and dubbing.

- **Backend**: Python 3.10+ with FastAPI
- **Frontend**: TypeScript 5.3+ with React 18, Vite 5, Ant Design 5.x, TailwindCSS
- **Core Pipeline**: Python modules for ASR, NLP, translation, TTS, video processing

## Build/Lint/Test Commands

### Backend (Python)

```bash
# Activate environment
conda activate videolingo

# Run development server
workdir="backend"
uvicorn main:app --reload --port 8000

# Run all tests
workdir="backend"
pytest

# Run single test file
workdir="backend"
pytest tests/test_config.py -v

# Run single test function
workdir="backend"
pytest tests/test_config.py::test_load_config -v
```

### Frontend (TypeScript/React)

```bash
# Install dependencies
workdir="frontend"
npm install

# Development server
workdir="frontend"
npm run dev

# Type check and build
workdir="frontend"
npm run build

# Lint (strict: 0 warnings allowed)
workdir="frontend"
npm run lint
```

## Project Structure

```
backend/
├── main.py                 # FastAPI entry point
├── api/routes/             # API route handlers
├── models/                 # Pydantic data models
└── services/               # Business logic layer

frontend/
├── src/
│   ├── components/         # React components
│   ├── pages/              # Page components
│   ├── services/           # API client (api.ts, polling.ts)
│   ├── hooks/              # Custom React hooks
│   ├── types/              # TypeScript types
│   └── i18n/               # Internationalization

core/                       # Video processing pipeline (DO NOT MODIFY)
├── _1_ytdlp.py            # YouTube download
├── _2_asr.py              # Speech recognition
├── _3_*.py                # NLP/semantic splitting
├── _4_*.py                # Summarization/translation
├── _5_*.py - _12_*.py     # Subtitle/dubbing stages
├── asr_backend/           # ASR implementations
├── tts_backend/           # TTS implementations
└── utils/                 # Shared utilities

config.yaml                # Application configuration
translations/              # i18n JSON files
```

## Code Style Guidelines

### Python

- Follow PEP 8
- Use type annotations for function parameters and returns
- Use Pydantic models for data validation
- Use block comments for section headers:
  ```python
  # ------------
  # Section Name
  # ------------
  ```
- Write comments in English
- Avoid complex inline comments and type hints in variable assignments
- Use descriptive variable names (no single letters except loop indices)

### TypeScript/React

- Strict mode enabled (`noUnusedLocals`, `noUnusedParameters`)
- Use `interface` for type definitions, not `type` aliases
- Function components with hooks only (no class components)
- Use path alias `@/*` for `src/*` imports
- Component files: PascalCase (e.g., `VideoUpload.tsx`)
- Hook files: camelCase with `use` prefix (e.g., `usePolling.ts`)

### Imports Order

**Python:**
1. Standard library
2. Third-party packages
3. Local modules

**TypeScript:**
1. React/framework imports
2. Third-party libraries
3. Local components/hooks
4. Types
5. Styles

### Naming Conventions

| Item | Python | TypeScript |
|------|--------|------------|
| Variables/functions | `snake_case` | `camelCase` |
| Classes/Components | `PascalCase` | `PascalCase` |
| Constants | `UPPER_SNAKE` | `UPPER_SNAKE` |
| Files | `snake_case.py` | `PascalCase.tsx` (components) |
| API routes | `/api/snake_case` | - |
| Pydantic/TS fields | `snake_case` + camelCase alias | `camelCase` |

### Error Handling

**Python:**
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

**TypeScript:**
```typescript
try {
  const result = await riskyOperation()
} catch (error) {
  message.error(error instanceof Error ? error.message : 'Unknown error')
}
```

## Key Conventions

1. **API Routes**: Prefix all routes with `/api/`
2. **Progress Polling**: 2-second interval for status updates
3. **File Upload**: No size limit enforced
4. **i18n**: Reuse `translations/*.json` for frontend localization
5. **Configuration**: Persist settings via `config.yaml`

## Constitution Principles

1. **Pipeline Integrity**: Call existing `core/` modules. DO NOT modify pipeline logic.
2. **Quality-First Translation**: Translation logic unchanged, only UI layer refactored.
3. **Modular Backend**: Keep ASR/TTS/LLM modules replaceable.
4. **Configuration Transparency**: Read/write config.yaml via API only.
5. **Internationalization**: Reuse `translations/*.json` files.

## Dependencies

### Backend (requirements.txt)
- FastAPI 0.109+, Uvicorn
- PyTorch, WhisperX, spaCy
- Pydantic, OpenAI SDK
- moviepy, opencv-python, pydub

### Frontend (package.json)
- React 18, Vite 5
- Ant Design 5.12, @ant-design/icons
- TailwindCSS 3.4
- react-i18next

## Files to Avoid Modifying

- `core/_*.py` files - Core pipeline logic
- `core/asr_backend/` - ASR implementations
- `core/tts_backend/` - TTS implementations
- Model files in cache directories

## Cursor Rules (.cursorrules)

1. Use block comments with dashes for section headers
2. Write all comments and print statements in English
3. Avoid complex inline comments
4. No type definitions in variable declarations

## Testing Patterns

```python
# Backend test example
def test_config_load():
    config = load_config()
    assert config is not None
    assert 'api' in config
```

```typescript
// Frontend: prefer integration tests with real API mocks
```

## Commit Message Format

- `feat:` new feature
- `fix:` bug fix
- `refactor:` code refactoring
- `docs:` documentation
- `test:` test changes
- `chore:` maintenance tasks
