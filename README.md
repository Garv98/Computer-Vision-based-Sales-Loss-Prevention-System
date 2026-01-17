# Computer Vision-Based Sales Loss Prevention System

This project is a Computer Vision-Based Retail Sales Opportunity Loss Prevention System. It includes a FastAPI backend for analytics, a Node.js backend for authentication, and a React frontend for the user interface.

## Prerequisites
- Node.js (v16 or higher)
- Python (v3.8 or higher)
- PostgreSQL
- MongoDB Atlas account
- Git

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Garv98/Computer-Vision-based-Sales-Loss-Prevention-System.git
   cd Computer-Vision-based-Sales-Loss-Prevention-System/DBMS5thEL
   ```

2. **Set Up the Backend**
   - Navigate to the `backend/` folder:
     ```bash
     cd backend
     ```
   - Install dependencies:
     ```bash
     npm install
     ```
   - Create a `.env` file and configure the required environment variables (e.g., MongoDB URI).
   - Start the backend server:
     ```bash
     node server.js
     ```

3. **Set Up the FastAPI Backend**
   - Navigate to the `src/` folder:
     ```bash
     cd ../src
     ```
   - Create a virtual environment:
     ```bash
     python -m venv .venv
     ```
   - Activate the virtual environment:
     - On Windows:
       ```bash
       .venv\Scripts\activate
       ```
     - On macOS/Linux:
       ```bash
       source .venv/bin/activate
       ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Start the FastAPI server:
     ```bash
     uvicorn main:app --reload
     ```

4. **Set Up the Frontend**
   - Navigate to the `my-app/` folder:
     ```bash
     cd ../my-app
     ```
   - Install dependencies:
     ```bash
     npm install
     ```
   - Start the development server:
     ```bash
     npm run dev
     ```

## Usage
- Access the frontend at `http://localhost:5173`.
- The FastAPI backend runs at `http://127.0.0.1:8000`.
- The Node.js backend runs at `http://localhost:3000`.

## License
This project is licensed under the MIT License.
