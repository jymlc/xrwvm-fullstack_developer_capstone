import json
import os
from urllib.parse import quote

import requests
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import CarMake, CarModel

DEALERS = os.environ.get('DEALERS_API_URL', 'http://127.0.0.1:3030')
SENTIMENT = os.environ.get('SENTIMENT_API_URL', 'http://127.0.0.1:5050')


@ensure_csrf_cookie
@require_GET
def frontend(request, **kwargs):
    return FileResponse((settings.FRONTEND / 'build' / 'index.html').open('rb'), content_type='text/html')


@require_GET
def info_page(request, filename):
    return FileResponse((settings.FRONTEND / 'static' / filename).open('rb'), content_type='text/html')


def json_body(request):
    try:
        data = json.loads(request.body)
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeError):
        return {}


def upstream(base, route, body=None):
    try:
        response = requests.get(base + route, timeout=5) if body is None else requests.post(
            base + route, json=body, timeout=5)
        return response.json(), response.status_code
    except (requests.RequestException, ValueError):
        return {'error': 'The upstream service is unavailable.'}, 502


@ensure_csrf_cookie
@require_GET
def session_user(request):
    return JsonResponse({'userName': request.user.username if request.user.is_authenticated else ''})


@require_POST
def login_user(request):
    data = json_body(request)
    user = authenticate(request, username=data.get('userName'), password=data.get('password'))
    if user is None:
        return JsonResponse({'error': 'Invalid username or password.'}, status=401)
    login(request, user)
    return JsonResponse({'userName': user.username, 'status': 'Authenticated'})


@require_POST
def logout_user(request):
    logout(request)
    return JsonResponse({'status': 'Logged out'})


@require_POST
def register_user(request):
    data = json_body(request)
    keys = ('userName', 'firstName', 'lastName', 'email', 'password')
    if not all(isinstance(data.get(key), str) and data[key].strip() for key in keys):
        return JsonResponse({'error': 'All five fields are required.'}, status=400)
    user = get_user_model()(username=data['userName'], first_name=data['firstName'],
                            last_name=data['lastName'], email=data['email'])
    try:
        validate_email(user.email)
        user.full_clean(validate_unique=False)
        validate_password(data['password'], user)
    except ValidationError as error:
        return JsonResponse({'error': ' '.join(error.messages)}, status=400)
    try:
        user.set_password(data['password'])
        user.save()
    except IntegrityError:
        return JsonResponse({'error': 'Username is already registered.'}, status=409)
    login(request, user)
    return JsonResponse({'userName': user.username, 'status': 'Registered'}, status=201)


@require_GET
def dealers(request, state=None):
    path = '/fetchDealers' + ('/' + quote(state, safe='') if state else '')
    data, status = upstream(DEALERS, path)
    return JsonResponse({'dealers': data} if status == 200 else data, status=status)


@require_GET
def dealer_details(request, dealer_id):
    data, status = upstream(DEALERS, f'/fetchDealer/{dealer_id}')
    return JsonResponse({'dealer': data} if status == 200 else data, status=status)


@require_GET
def dealer_reviews(request, dealer_id):
    data, status = upstream(DEALERS, f'/fetchReviews/dealer/{dealer_id}')
    return JsonResponse({'reviews': data} if status == 200 else data, status=status)


@require_GET
def cars(request):
    rows = CarMake.objects.prefetch_related('models').order_by('name')
    return JsonResponse({'CarMakes': [{
        'id': make.pk, 'name': make.name, 'description': make.description,
        'models': [{'id': model.pk, 'name': model.name, 'type': model.type, 'year': model.year}
                   for model in make.models.all()],
    } for make in rows]})


@require_GET
def analyze(request, text):
    data, status = upstream(SENTIMENT, '/analyze/' + quote(text, safe=''))
    return JsonResponse(data, status=status)


@require_POST
def add_review(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Log in to post a review.'}, status=401)
    data = json_body(request)
    review = data.get('review')
    dealer_id = data.get('dealership')
    if type(dealer_id) is not int or not isinstance(review, str) or not 1 <= len(review.strip()) <= 2000:
        return JsonResponse({'error': 'A dealer and review of 1–2000 characters are required.'}, status=400)
    model = CarModel.objects.select_related('make').filter(pk=data.get('modelId')).first() if type(data.get('modelId')) is int else None
    if not model:
        return JsonResponse({'error': 'Select a car model.'}, status=400)
    rating, status = upstream(SENTIMENT, '/analyze/' + quote(review.strip(), safe=''))
    if status != 200:
        return JsonResponse(rating, status=status)
    result, status = upstream(DEALERS, '/insert_review', {
        'name': request.user.username, 'dealership': dealer_id, 'review': review.strip(),
        'purchase': data.get('purchase') is True, 'purchase_date': data.get('purchaseDate', ''),
        'car_make': model.make.name, 'car_model': model.name, 'car_year': model.year,
        'sentiment': rating['sentiment'],
    })
    return JsonResponse(result, status=status)
