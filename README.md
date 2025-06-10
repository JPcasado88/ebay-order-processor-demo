# eBay Order Processor & File Generator

A professional, production-ready Flask web application designed to automate the processing of eBay orders. This application fetches order data from multiple eBay store accounts via the Trading API, matches items against internal reference data using a sophisticated SKU and title-matching engine, and generates formatted Excel files (RUN, COURIER_MASTER, Tracking, etc.) for warehouse and shipping logistics.

This project has been fully refactored to showcase best practices in modern web application development, including the Application Factory pattern, blueprint-based routing, service layer separation, and configuration management for seamless deployment on cloud platforms like Railway.

## Key Features

*   **Secure User Authentication:** Login/logout system to protect access.
*   **Asynchronous Background Processing:** Long-running tasks (API fetching, file generation) are executed in the background using a threaded model, preventing web request timeouts and providing a responsive user experience.
*   **Real-time Progress Updates:** The frontend polls the server to display live progress of background jobs.
*   **Robust eBay API Integration:**
    *   Handles fetching orders from multiple store accounts.
    *   Features automated OAuth2 token management with a persistent token refresh mechanism.
*   **Advanced SKU Matching Engine:**
    *   Utilizes a multi-stage matching process, including a data-driven `ForcedMatchSKU` override system.
    *   Employs a complex, 19-case pattern-matching function (`extract_sku_identifier`) to handle a wide variety of SKU formats.
    *   Performs title-based analysis to determine product attributes like vehicle make/model, year, and colors.
*   **Dynamic File Generation:** Creates multiple, complex Excel and ZIP files based on user-selected criteria and business rules (e.g., batching for multi-item orders).
*   **Production-Ready Architecture:**
    *   Uses a persistent file-based store for tracking process state, suitable for stateless cloud environments.
    *   Includes a health check endpoint for platform monitoring.
    *   Features scheduled background jobs (using APScheduler) for automatic cleanup of old session and process files.

## Tech Stack

*   **Backend:** Python, Flask, Gunicorn
*   **Frontend:** HTML, CSS, JavaScript (for polling)
*   **Data Handling:** Pandas, OpenPyXEL
*   **API Interaction:** `ebay-sdk-python`, `requests`
*   **Deployment:** Configured for Railway (or other platform-as-a-service providers)

## Project Structure

This project follows the Flask Application Factory pattern to ensure a clean separation of concerns and scalability.

```
ebay_order_processor/
├── .env.example          # Template for environment variables
├── .gitignore           # Specifies files to be ignored by Git
├── Procfile             # Command for the production server (Gunicorn)
├── README.md            # This file
├── requirements.txt     # Project dependencies
├── run.py              # Entry point for local development server
└── ebay_processor/     # The main Flask application package
    ├── __init__.py     # Application factory (create_app)
    ├── config.py       # Configuration class (loads from .env)
    ├── services/       # Core business logic (no web code)
    │   ├── ebay_api.py           # All eBay API interaction & token logic
    │   ├── file_service.py       # All file generation logic
    │   └── sku_matching_service.py # Core SKU matching & order processing
    ├── web/            # Flask-related code (routes, utils)
    │   ├── __init__.py
    │   ├── routes.py   # All @app.route definitions (Blueprint)
    │   └── utils.py    # Helper functions & utility classes
    ├── static/         # CSS, JavaScript, images
    └── templates/      # HTML templates
```

## Local Setup and Running the Application

Follow these steps to run the project on your local machine.

### 1. Prerequisites

*   Python 3.8+
*   `pip` and `venv`

### 2. Clone the Repository

```bash
git clone <your-github-repository-url>
cd ebay_order_processor
```

### 3. Set Up a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 4. Install Dependencies

Install all the required packages from the requirements.txt file.

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

The application requires several secret keys and configuration variables.

1. Copy the template:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your credentials:
   * A strong `SECRET_KEY`
   * Your `ADMIN_USERNAME` and generated `ADMIN_PASSWORD_HASH`
   * Your eBay API `APP_ID`, `CERT_ID`, and `DEV_ID`
   * The refresh tokens for each of your eBay stores (`EBAY_STORE_1_REFRESH_TOKEN`, etc.)

3. To generate a secure password hash, open a Python shell and run:
   ```python
   from werkzeug.security import generate_password_hash
   print(generate_password_hash('your-super-strong-password-here'))
   ```
   Copy the entire output (including the `scrypt:...` part) into the `ADMIN_PASSWORD_HASH` variable in your `.env` file.

### 6. Run the Application

Once your dependencies are installed and your `.env` file is configured, you can start the local development server.

```bash
python run.py
```

The application will be running and available at http://127.0.0.1:5001.

## Deployment

This application is configured for easy deployment on platforms like Railway. The `Procfile` specifies the gunicorn command to run the production server. To deploy:

1. Push the code to a GitHub repository
2. Link the repository to a new Railway project
3. Add a Persistent Volume on Railway and mount it (e.g., at `/data`)
4. Set all the variables from your local `.env` file as Environment Variables in the Railway service settings
5. Update the path variables (`OUTPUT_DIR`, `FLASK_SESSION_DIR`, `LOG_DIR`) to use the persistent volume (e.g., `OUTPUT_DIR=/data/output`)