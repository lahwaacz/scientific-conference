# Frontend

## Overview

This directory contains the frontend part of the scientific conference management system. The application is implemented in React and provides the user interface for both public visitors and administrative users.

The frontend presents conference information, program details, participant-related content, accommodation and hiking information, and the registration form. It also includes the administrative interface used for managing conference data through authenticated operations.

The application communicates with the Django backend through a REST API and is structured as a modular component-based interface. The design emphasizes clarity, usability, and responsive behavior across different screen sizes.

## Tech Stack

- React
- React Router
- Create React App

## Testing

- Jest and React Testing Library

## Project Structure

- `src/` — application source code.
- `src/components/` — reusable UI and page components.
- `src/components/ui/` — shared interface components.
- `src/components/hooks/` — custom hooks.
- `src/utils/` — API utilities and helper functions.
- `public/` — static public assets.
- `.env.development` — local development environment variables.
- `.env.production` — production environment variables.

## Requirements

- Node.js
- npm

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure the environment variables if needed.

3. Start the development server:
   ```bash
   npm run start
   ```

The application will run on `http://localhost:3000/` by default.

## Environment Variables

The frontend reads the backend base URL from the `REACT_APP_BACKEND_API_BASE_URL` environment variable defined in the corresponding `.env` file.

Create React App automatically loads different environment files depending on the command used:

- `npm start` uses `.env.development`
- `npm run build` uses `.env.production`

For local development, the backend is configured in `.env.development`:

```env
REACT_APP_BACKEND_API_BASE_URL=http://localhost:8000
```

For production builds, `.env.production` should contain the URL of the deployed backend server.  
After changing environment variables, restart the development server or rebuild the frontend to apply the updates.

API requests are constructed centrally in `src/utils/api.js`.


If the project is deployed on another server, this value should be updated accordingly.

## Production Build

To create a production build, run:

```bash
npm run build
```

## Testing

To run the frontend test suite, use:

```bash
npm test
```

## Main Features

- Public conference website.
- Conference program overview.
- Registration form for participants.
- Participant and abstract-related pages.
- Accommodation information.
- Hiking information.
- Administrative login and protected admin routes.
- Component-based editing interface for conference content.
- Modal-based interaction for important user actions.

## Notes

The frontend is designed to work together with the Django backend and depends on the REST API for data loading and data submission.  
For local development, the backend server should be running before the frontend is used.
