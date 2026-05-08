# Changelog

All notable changes to this project will be documented in this file.

## [0.1.4] - 2026-05-08

### Added
- **`structure_mode` Parameter**: New initialization parameter (defaults to `True`) that enables building nested namespaces from directory structures (e.g., `prompts.folder.file`).
- **`auto_export` Visibility**: Improved documentation for the `auto_export` feature which mirrors the prompt tree to `pyprompts.toml`.
- **Enhanced Metadata**: Expanded PyPI keywords and Trove classifiers for better discoverability.
- **Project URLs**: Added links for Documentation, Issue Tracker, and Changelog to the PyPI profile.

### Changed
- **`auto_render` Default**: Now defaults to `True`. Variables within templates will be automatically rendered during the initialization phase for better consistency.
- **Modernized Test Suite**: Refactored legacy test scripts into a clean `pytest` suite using `tmp_path` fixtures for isolation.
- **Root Directory Cleanup**: Removed all temporary and manual test files from the project root.

### Fixed
- **CI Workflow**: Fixed an "Invalid action input" error in the GitHub Actions workflow by updating the Codecov action to version 5 and using the correct `files` parameter.

### Documentation
- **API Reference**: Added a comprehensive `docs/api_reference.md`.
- **User Guide**: Updated `docs/dynaprompt.md` with detailed architecture and feature explanations.
- **README**: Redesigned with better formatting, icons, and `uv` installation instructions.

## [0.1.3] - 2026-05-04
- Initial release with lazy-loading, environment support, and Pydantic schema integration.
