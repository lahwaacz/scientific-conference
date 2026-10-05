# Web application for the organization of scientific conferences

## Overview

This project is a full-stack web application designed for the organization and administration of scientific conferences. It was developed as a modern replacement for an internal system used by the Department of Software Engineering at the Faculty of Nuclear Sciences and Physical Engineering, Czech Technical University in Prague.

The original system reflected the practical needs of conference organization, but its limited flexibility and outdated user interface reduced usability and hindered further development. This project addresses these limitations by providing a modern, scalable, and user-centered solution that better supports the evolving requirements of academic conference management.

The application covers the core functionality needed for managing scientific conferences in an academic environment, including public conference information, participant management, submission handling, reviews, scheduling, and administrative content editing. It hosts multiple conferences side by side: a public landing page lists all conferences, and each conference has its own website and its own data. The project also includes administrator documentation to support deployment, maintenance, and practical use of the system.

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

- Multi-conference hosting: a public landing page lists all conferences, grouped as Running, Upcoming, or Past.
- A separate public website per conference with structured conference information.
- Conference creation (slug) in the Django administration; conference logistics (title, dates, location, photo, badge title) edited in the conference's own admin panel (Edit Web Info).
- Conference data management, isolated per conference.
- Participant management.
- Submission handling.
- Review and publication workflows.
- Scheduling and program management.
- Administrator panel for managing conference content.
- Per-conference badge and program PDF generation.
- Responsive user interface for desktop and mobile devices.
- Modular component-based frontend architecture.
- REST API backend with per-conference URL scoping and protected administrative operations.

## URL Structure

The application hosts multiple conferences. Each conference is identified by a slug and lives at its own address:

- `/` — the landing page listing all conferences as cards.
- `/<slug>/` — the website of one conference (for example `/wsc2026/`). All pages and the admin panel of that conference live under this prefix. A slug that matches no conference shows the landing page.

The REST API follows the same split:

- `/api/conferences/` — public list of all conferences, ordered running first, then upcoming, then past.
- `/api/auth/login/` and `/api/auth/refresh/` — global JWT authentication (one staff account administers every conference).
- `/api/<slug>/...` — everything else, scoped to one conference. An unknown slug returns 404.

In the demo deployment, all of these sit under the `/conference-demo/` prefix (for example `/conference-demo/wsc2026/`).

## Demo

Demo URL: `https://mmg-webapps.fjfi.cvut.cz/conference-demo/`

The demo root shows the landing page. Each conference is available at its own address under the root, for example `https://mmg-webapps.fjfi.cvut.cz/conference-demo/wsc2026/`.

The frontend production image is built with two build arguments: `VITE_BACKEND_API_BASE_URL` (the backend base URL) and `VITE_BASE_PATH` (the absolute base path, defaulting to `/conference-demo/`, which makes the built asset URLs depth-independent). The reverse proxy in front of the deployment must serve the frontend entry page for every path under the root that is not a real file and not routed to the backend (`api/`, `admin/`, `media/`), so that direct links like `/conference-demo/<slug>/` work. See `ADMINISTRATOR_GUIDE.md` for details.


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

3. Optionally, load the demo fixture. It seeds five demo conferences
   (one running, two upcoming, two past) with participants and a sample
   program:
   ```bash
   uv run python manage.py loaddata conferences.json participants.json program.json
   ```

4. Run the backend server:
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

With the fixture loaded, `http://localhost:3000/` shows the landing page and
`http://localhost:3000/wsc2026/` opens the seeded conference. Without any
conference in the database, the landing page shows "No conferences yet." and
conferences can be created in the Django administration at
`http://localhost:8000/admin/`.

## Documentation

- `backend/README.md` — backend setup, dependencies, environment variables, and development notes.
- `frontend/README.md` — frontend setup, environment configuration, and development notes.
- `ADMINISTRATOR_GUIDE.md` — guide for using the admin panel and handling administrative actions.

## Notes

This project intentionally focuses on the core functionality required for managing a scientific conference in an academic setting. It is not intended to be a universal commercial conference platform with every advanced feature found in large-scale systems. Instead, the emphasis is placed on a practical, maintainable, and extensible solution tailored to departmental needs.
