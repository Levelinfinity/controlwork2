python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
Открыть Swagger: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)