# Computer Vision-Based Sales Loss Prevention System

This project is a Computer Vision-Based Retail Sales Opportunity Loss Prevention System. It includes:
- **FastAPI Backend**: For analytics and PostgreSQL integration.
- **Node.js Backend**: For MongoDB-based authentication.
- **React Frontend**: For the user interface.

## Prerequisites
- Node.js (v16 or higher)
- Python (v3.8 or higher)
- PostgreSQL
- MongoDB Atlas account
- Git

## Environment Variables

The `backend/` folder requires a `.env` file to configure the MongoDB connection. Create a `.env` file in the `backend/` folder with the following content:

```plaintext
# MongoDB Connection String
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
```

### Example:
```plaintext
MONGODB_URI=mongodb+srv://user123:password123@cluster0.mongodb.net/mydatabase?retryWrites=true&w=majority
```

### Instructions:
1. Replace `<username>` with your MongoDB username.
2. Replace `<password>` with your MongoDB password.
3. Replace `<cluster-url>` with your MongoDB cluster URL (e.g., `cluster0.mongodb.net`).
4. Replace `<database>` with the name of your database.

Ensure the `.env` file is not committed to version control by adding it to your `.gitignore` file.


## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Garv98/Computer-Vision-based-Sales-Loss-Prevention-System.git
   cd Computer-Vision-based-Sales-Loss-Prevention-System/DBMS5thEL
   ```

2. **Create a Virtual Environment**
   - At the root of the `DBMS5thEL` folder, create a Python virtual environment:
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

3. **Install Python Dependencies**
   - Navigate to the `src/` folder:
     ```bash
     cd src
     ```
   - Install the required Python packages:
     ```bash
     pip install -r requirements.txt
     ```

4. **Install Node.js Dependencies**
   - For the Node.js backend:
     ```bash
     cd ../backend
     npm install
     ```
   - For the React frontend:
     ```bash
     cd ../my-app
     npm install
     ```

---

## Running the Application

1. **Start the Node.js Backend**
   - Open a terminal, activate the virtual environment, and navigate to the `backend/` folder:
     ```bash
     cd backend
     node server.js
     ```

2. **Start the FastAPI Backend**
   - Open another terminal, activate the virtual environment, and navigate to the `src/` folder:
     ```bash
     cd src
     python api.py
     ```

3. **Start the React Frontend**
   - Open a third terminal, activate the virtual environment, and navigate to the `my-app/` folder:
     ```bash
     cd my-app
     npm run dev
     ```

---

## Accessing the Application
- **Frontend**: Open your browser and go to `http://localhost:5173`.
- **FastAPI Backend**: Runs at `http://127.0.0.1:8000`.
- **Node.js Backend**: Runs at `http://localhost:3000`.

---

## Notes
- Ensure your `.env` files are properly configured for both the Node.js backend and FastAPI backend.
- PostgreSQL and MongoDB Atlas must be running and accessible.

---

## License
This project is licensed under the MIT License.
