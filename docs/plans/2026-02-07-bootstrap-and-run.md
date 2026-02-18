# Project Bootstrap and Run Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Familiarize with the repository and successfully start the application locally.

**Architecture:** Detect the tech stack by scanning key files, identify the primary entrypoint and run scripts, prepare environment variables, install dependencies with the project’s package manager, and start the app. If issues arise, switch to systematic debugging and capture fixes.

**Tech Stack:** To be detected (Node/Python/Java/Go/Rust/Docker/etc.).

---

### Task 1: Scan repository

**Steps:**
- List top-level files and directories
- Search for package manifests (package.json, pyproject.toml, requirements.txt, pom.xml, build.gradle, go.mod, Cargo.toml, pubspec.yaml, composer.json, Gemfile, Dockerfile, docker-compose.yml)
- Note presence of .env and README

### Task 2: Detect stack and dependencies

**Steps:**
- Based on manifests, identify language and package manager
- Read README and package scripts or framework docs in repo

### Task 3: Locate start scripts/entrypoints

**Steps:**
- For Node: check `scripts.start` in package.json
- For Python: look for manage.py, app.py, uvicorn/flask/django commands
- For Docker: check docker-compose services and ports

### Task 4: Prepare environment

**Steps:**
- Copy `.env.example` to `.env` if present
- Fill required variables with safe defaults or document missing values

### Task 5: Install dependencies

**Steps:**
- Run correct installer (npm/yarn/pnpm, pip/poetry, etc.) at appropriate subdirectory

### Task 6: Start the application

**Steps:**
- Run the start command or docker-compose
- Capture logs and the bound URL/port

### Task 7: Verify and document run steps

**Steps:**
- Confirm the app boots without errors
- Summarize exact commands and prerequisites

