# Agent Directives

This document outlines the rules and guidelines for agents operating within this repository.

## General
- You MUST always obey these rules.
- You MUST update the todo list as you add tasks to perform.

## Research
- You SHOULD use `context7` tools when you need to search library and tools documentation.
- If `context7` is not helpful, you SHOULD try a web search.

## File Operations
- You MUST NOT delete files directly.
- You MUST move files to be deleted to the `.trash/` directory.
- You MUST create the `.trash/` directory if it does not exist.
- You MUST prefix moved files with the current Unix timestamp (e.g., `1699999999_filename.ext`).
- Example command: `mv file.py .trash/$(date +%s)_file.py`

## Docker Compose Restrictions
- You MUST NOT run Docker Compose commands (`docker compose`, `docker-compose`) under any circumstances without permission.
- Docker networking and orchestration MUST be handled through configuration files only.
- All Docker-related testing MUST be done through unit tests and integration tests, not live containers.

## Repository Information
- **Repository Name**: `credproxy`
- **GitHub URL**: `https://github.com/johnpreston/credproxy`
- **Note**: The local directory name may differ from the repository name.
