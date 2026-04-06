# Running the M&A Prospecting Platform Locally

This document provides instructions for running the backend and frontend independently for local development.

## Prerequisites

- **Python**: Version 3.11 or higher
- **Node.js**: Version 18 or higher (with npm)
- **Make**: (Optional, but recommended for using the provided Makefile commands)

## Running the Backend

The backend is built with FastAPI and runs on port 8000.

1. **Navigate to the root directory**:
   ```bash
   cd ma-prospecting-platform
   pip install -e
   pip install -e ".[playwright]"
   playwright install chromium
   ```

2. **Set up the backend environment**:
   Create a virtual environment (optional but recommended) and install dependencies.
   ```bash
   # Optional: Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate

   cd backend
   cp .env.example .env
   pip install -e ".[dev]"
   ```
   *(Make sure to update the `.env` file with any required API keys)*

3. **Start the backend server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *The API will be available at `http://localhost:8000`*

## Running the Frontend

The frontend is a Next.js application and typically runs on port 3000.

1. **Navigate to the project root**:
   ```bash
   cd ma-prospecting-platform
   ```

2. **Set up the frontend environment**:
   ```bash
   cd frontend
   cp .env.local.example .env.local
   npm install
   ```

3. **Start the frontend development server**:
   ```bash
   npm run dev
   ```
   *The application will be available at `http://localhost:3000`*

## Using the Makefile (Shortcut)

If you have `make` installed, you can use the commands specified in the `/ma-prospecting-platform/Makefile` from the `ma-prospecting-platform` directory:

- **Full Setup**: `make setup` (sets up env variables and installs dependencies for both)
- **Run Backend**: `make run-backend`
- **Run Frontend**: `make run-frontend`
