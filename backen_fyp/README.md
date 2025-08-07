## Requirements
- Python 3.8 or higher
- Django 3.2 or higher
- Django REST Framework
- PostgreSQL or SQLite (for development)

## Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   ```
2. Navigate to the project directory:
   ```bash
   cd FYP/backen_fyp
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
    ```
    NOTE: Don't forget to create a virtual environment before installing the requirements.
4. Make migrations and migrate the database:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Create a superuser account:
   ```bash
   python manage.py createsuperuser
    ```
6. Run the development server:
    ```bash
   python manage.py runserver
   ```
7. Access the application at `http://127.0.0.1:8000/`
8. Access the admin panel at `http://127.0.0.1:8000/admin/`
## Usage
- Use the admin panel to manage users, roles, and other data.
- The API endpoints can be accessed via the URLs defined in the `urls.py` file. 
- Use tools like Postman or cURL to interact with the API endpoints.
- For user authentication, use the provided endpoints to register and log in users.
## Recent Edits
- Added UUID field for user model to ensure unique identification.
- Updated role field to allow blank values for better flexibility in user management.
- Improved user model with additional fields for better user management.
