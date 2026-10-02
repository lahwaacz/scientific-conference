# Web application for the organization of scientific conferences

## Overview

This project is a full-stack web application designed for the organization and administration of scientific conferences. It was developed as a modern replacement for an internal system used by the Department of Software Engineering at the Faculty of Nuclear Sciences and Physical Engineering, Czech Technical University in Prague.

The original system reflected the practical needs of conference organization, but its limited flexibility and outdated user interface reduced usability and hindered further development. This project addresses these limitations by providing a modern, scalable, and user-centered solution that better supports the evolving requirements of academic conference management.

The application covers the core functionality needed for managing a scientific conference in an academic environment, including public conference information, participant management, submission handling, reviews, scheduling, and administrative content editing. The project also includes administrator documentation to support deployment, maintenance, and practical use of the system.

## Project Goals

The main goal of this project was to analyze the existing conference management system, identify its functional and non-functional limitations, redesign the user interface and user flows, and implement a new web application that improves usability, maintainability, and long-term extensibility.

The project focuses on:
- analyzing existing conference management solutions,
- identifying the requirements of scientific conference organization,
- redesigning the original user interface and interaction logic,
- implementing a new full-stack web application,
- preparing documentation for administrative use.

## Tech Stack

- Backend: Django
- API: Django REST Framework
- Frontend: React
- Database: SQLite

## Key Features

- Public conference website with structured conference information.
- Conference data management.
- Participant management.
- Submission handling.
- Review and publication workflows.
- Scheduling and program management.
- Administrator panel for managing conference content.
- Responsive user interface for desktop and mobile devices.
- Modular component-based frontend architecture.
- REST API backend with protected administrative operations.

## Demo

Demo URL: `https://mmg-webapps.fjfi.cvut.cz/conference-demo/`


## Local Setup

### Backend

The backend uses [uv](https://docs.astral.sh/uv/) for dependency management
(commands run from the `backend/` directory).

1. Install dependencies (creates `backend/.venv` from `uv.lock`):
   ```bash
   uv sync
   ```

2. Apply database migrations:
   ```bash
   uv run python manage.py migrate
   ```

3. Run the backend server:
   ```bash
   uv run python manage.py runserver
   ```

### Frontend

1. Install frontend dependencies:
   ```bash
   npm install
   ```

2. Start the frontend development server:
   ```bash
   npm run start
   ```

## Documentation

- `backend/README.md` — backend setup, dependencies, environment variables, and development notes.
- `frontend/README.md` — frontend setup, environment configuration, and development notes.
- `ADMINISTRATOR_GUIDE.md` — guide for using the admin panel and handling administrative actions.

## Notes

This project intentionally focuses on the core functionality required for managing a scientific conference in an academic setting. It is not intended to be a universal commercial conference platform with every advanced feature found in large-scale systems. Instead, the emphasis is placed on a practical, maintainable, and extensible solution tailored to departmental needs.
