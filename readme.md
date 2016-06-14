# Tunga API and Backend [![Build Status](https://travis-ci.org/tunga-io/tunga-api.svg?branch=develop)](https://travis-ci.org/tunga-io/tunga-api)
API and Backend for tunga.io

# Installation
1. run the following commands from project root (preferably in a virtualenv)
```
pip install -r requirements.txt
python manage.py migrate
python manage.py initial_tags
python manage.py initial_tunga_settings
```

# Coding Guide
* Built with [Django](https://www.djangoproject.com/) and [Django REST framework](http://www.django-rest-framework.org/)

# Development
1. run this command from project root
```
python manage.py runserver
```
2. Access the API at http://127.0.0.1:8000/api/ and the backend at http://127.0.0.1:8000/admin/ in your browser

# Testing
1. run this command from project root
```
python manage.py test
```

# Documentation
API Documentation is generated automatically at http://127.0.0.1:8000/api/docs/ using [Django REST Swagger](https://github.com/marcgibbons/django-rest-swagger)

# Deployment
