<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: N/A → 1.0.0 (Initial Constitution)
Modified Principles: N/A (Initial creation)
Added Sections:
  - Core Principles (5 principles)
  - Quality Standards
  - Development Workflow
  - Governance
Removed Sections: N/A
Templates Status:
  ✅ plan-template.md - Constitution Check section compatible
  ✅ spec-template.md - Requirements align with principles
  ✅ tasks-template.md - Task phases compatible with workflow
Follow-up TODOs: None
================================================================================
-->

# VideoLingo Constitution

## Core Principles

### I. Pipeline Integrity
All video processing operations MUST follow the defined sequential pipeline (`_1_ytdlp` → `_2_asr` → ... → `_12_dub_to_vid`). Each stage:
- MUST produce well-defined intermediate outputs that can be inspected and resumed
- MUST validate inputs before processing to fail fast on invalid data
- MUST log progress for resumption capability
- MUST NOT skip stages or modify outputs of previous stages directly

**Rationale**: VideoLingo processes videos through a complex multi-stage pipeline. Maintaining clear stage boundaries ensures debuggability, enables progress resumption, and prevents data corruption from partial failures.

### II. Quality-First Translation
Translation output MUST meet Netflix-quality subtitle standards:
- Single-line subtitles ONLY - multi-line subtitles are prohibited
- NLP and AI-powered segmentation MUST be used to avoid awkward breaks
- The 3-step Translate-Reflect-Adaptation workflow MUST be followed for cinematic quality
- Custom terminology and context MUST be preserved across segments

**Rationale**: The project's core differentiator is superior translation quality. Compromising on quality standards would undermine the project's value proposition.

### III. Modular Backend Architecture
Each backend (ASR, TTS, LLM) MUST be independently swappable:
- ASR backends in `core/asr_backend/` MUST implement a common interface
- TTS backends in `core/tts_backend/` MUST implement a common interface
- LLM calls via `core/utils/ask_gpt.py` MUST use OpenAI-compatible API format
- Adding a new backend MUST NOT require changes to the core pipeline logic

**Rationale**: Users have different infrastructure constraints (API keys, local resources, cost considerations). Modular backends allow flexibility without fragmenting the codebase.

### IV. Configuration Transparency
All user-configurable options MUST be:
- Centralized in `config.yaml` with clear documentation
- Exposed through the Streamlit UI in `core/st_utils/sidebar_setting.py`
- Validated at startup with helpful error messages
- Defaulted to sensible values that work for most use cases

**Rationale**: VideoLingo targets users who may not be developers. Configuration must be discoverable and foolproof.

### V. Internationalization Compliance
All user-facing strings MUST be:
- Defined in `translations/*.json` files, never hardcoded
- Available in all supported UI languages (en, zh-CN, zh-HK, ja, es, ru, fr)
- Consistent in terminology across the application

**Rationale**: As a video localization tool, VideoLingo must lead by example in internationalization practices.

## Quality Standards

### Code Quality
- Python code MUST follow PEP 8 style guidelines
- All functions with complex logic MUST have docstrings explaining purpose and parameters
- Error handling MUST use structured logging via the decorator pattern in `core/utils/decorator.py`
- Dependencies MUST be pinned in `requirements.txt` with version constraints

### Testing Requirements
- Core pipeline stages SHOULD have integration tests validating input/output contracts
- Backend implementations SHOULD have unit tests for edge cases
- Manual testing with sample videos MUST be performed before releases

### Documentation
- README files MUST be maintained in sync across all language versions in `translations/`
- API configuration instructions MUST include both 302.ai and local deployment options
- Known limitations MUST be documented clearly to set user expectations

## Development Workflow

### Branch Strategy
- Feature development MUST occur on feature branches
- Main branch MUST always be in a deployable state
- Breaking changes MUST be documented in commit messages and release notes

### Pull Request Requirements
- PRs MUST include a description of changes and testing performed
- PRs affecting the pipeline MUST include sample video test results
- PRs adding new backends MUST include configuration documentation

### Release Process
- Releases MUST follow semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking changes to pipeline, config format, or API compatibility
- MINOR: New features, new backend support, new language support
- PATCH: Bug fixes, documentation updates, performance improvements

## Governance

This Constitution supersedes all other development practices for the VideoLingo project. All contributions MUST comply with these principles.

### Amendment Process
1. Propose amendment with rationale in a GitHub issue or PR
2. Document impact on existing functionality
3. Update version following semantic versioning rules
4. Update dependent documentation and templates as needed

### Compliance
- Code reviews MUST verify compliance with Constitution principles
- Complexity additions MUST be justified against Core Principles
- Refer to this Constitution when making architectural decisions

### Exceptions
Temporary exceptions may be granted for:
- Experimental features clearly marked as such
- Hotfixes with follow-up tickets for proper implementation
- Third-party integration constraints beyond project control

All exceptions MUST be documented with remediation plans.

**Version**: 1.0.0 | **Ratified**: 2026-01-17 | **Last Amended**: 2026-01-17
