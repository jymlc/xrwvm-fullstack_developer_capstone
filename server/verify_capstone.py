import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoproj.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from djangoapp.models import CarMake, CarModel

BASE = 'http://127.0.0.1:8000'
PASSWORD = 'capstone-demo-ci-only'
OUTPUT = Path('../evidence')
REVIEW = 'Fantastic services. The staff explained the options and made the visit easy.'


def seed():
    users = get_user_model().objects
    users.create_superuser('root', 'root@example.com', PASSWORD)
    users.create_user('demo_driver', password=PASSWORD)
    for make, model, kind, year in [
        ('Ford', 'Mustang', 'Coupe', 2024),
        ('Honda', 'Civic', 'Sedan', 2024),
        ('Toyota', 'Corolla', 'Sedan', 2025),
        ('Toyota', 'RAV4', 'SUV', 2025),
    ]:
        brand, _ = CarMake.objects.get_or_create(name=make)
        CarModel.objects.get_or_create(make=brand, name=model, year=year, defaults={'type': kind})


def evidence():
    OUTPUT.mkdir(exist_ok=True)
    cookie = OUTPUT / 'test-cookies.tmp'

    def request(name, path, expected=200, options=()):
        command = ['curl', '-sS', '--max-time', '15', '-w', '\\nHTTP %{http_code}\\n',
                   *options, BASE + '/djangoapp/' + path]
        result = subprocess.check_output(command, text=True)
        response, status = result.strip().rsplit('\nHTTP ', 1)
        assert int(status) == expected, result
        parsed = json.loads(response)
        if name:
            # Reusable cookie variable in the printed command, live token kept private.
            visible = [re.sub(r'X-CSRFToken: .*', 'X-CSRFToken: $CSRF_TOKEN', value) for value in command]
            (OUTPUT / (name + '.txt')).write_text(
                shlex.join(visible).replace("'X-CSRFToken: $CSRF_TOKEN'", '"X-CSRFToken: $CSRF_TOKEN"')
                + '\n\n' + json.dumps(parsed, indent=2, ensure_ascii=False) + '\nHTTP ' + status + '\n',
                encoding='utf-8')
        return parsed

    def csrf():
        return next(line.split('\t')[-1] for line in cookie.read_text().splitlines()
                    if '\tcsrftoken\t' in line)

    def post(name, path, payload, expected=200):
        return request(name, path, expected, ['-b', str(cookie), '-c', str(cookie), '-H',
                       'Content-Type: application/json', '-H', 'X-CSRFToken: ' + csrf(),
                       '-d', json.dumps(payload)])

    request(None, 'session', options=['-c', str(cookie)])
    assert post('loginuser', 'login', {'userName': 'demo_driver', 'password': PASSWORD})['status'] == 'Authenticated'
    assert request(None, 'session', options=['-b', str(cookie)])['userName'] == 'demo_driver'
    assert post('logoutuser', 'logout', {})['status'] == 'Logged out'
    assert request(None, 'session', options=['-b', str(cookie)])['userName'] == ''
    cookie.unlink()
    assert request('getdealerreviews', 'get_dealer_reviews/15')['reviews']
    assert len(request('getalldealers', 'get_dealers')['dealers']) > 10
    assert request('getdealerbyid', 'get_dealer_details/15')['dealer']['id'] == 15
    kansas = request('getdealersbyState', 'get_dealers/Kansas')['dealers']
    assert kansas and all(row['state'] == 'Kansas' for row in kansas)
    cars = request('getallcarmakes', 'get_cars')['CarMakes']
    assert len(cars) == 3 and sum(len(row['models']) for row in cars) == 4
    assert request('analyzereview', 'analyze/Fantastic%20services')['sentiment'] == 'positive'
    print('cURL checks passed: session login and logout, dealer routes, Kansas, car catalog, and sentiment.')


def screenshots():
    from playwright.sync_api import expect, sync_playwright

    def shot(page, name):
        page.bring_to_front()
        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        subprocess.run(['scrot', '-o', str(OUTPUT / f'{name}.png')], check=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, channel='chrome',
            args=['--window-position=0,0', '--window-size=1280,900', '--force-device-scale-factor=1'])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        page.goto(BASE + '/admin/')
        page.locator('#id_username').fill('root')
        page.locator('#id_password').fill(PASSWORD)
        page.get_by_role('button', name='Log in').click()
        expect(page.get_by_text('Welcome,', exact=False)).to_contain_text('root', ignore_case=True)
        shot(page, 'admin_login')
        page.get_by_role('button', name='Log out').click()
        expect(page.get_by_text('Logged out', exact=True).first).to_be_visible()
        shot(page, 'admin_logout')

        page.goto(BASE + '/')
        expect(page.get_by_role('link', name='Holdlamis Car Dealership')).to_be_visible()
        expect(page.get_by_role('link', name='Review Dealer')).to_have_count(0)
        shot(page, 'get_dealers')
        page.get_by_role('link', name='Log in').click()
        page.get_by_label('Username').fill('demo_driver')
        page.get_by_label('Password').fill(PASSWORD)
        page.get_by_role('button', name='Log in').click()
        expect(page.get_by_text('demo_driver', exact=True)).to_be_visible()
        expect(page.get_by_role('link', name='Review Dealer').first).to_be_visible()
        shot(page, 'get_dealers_loggedin')
        page.get_by_label('Filter by state').select_option('Kansas')
        expect(page.get_by_text('Topeka', exact=True).first).to_be_visible()
        expect(page.get_by_text('Texas', exact=True).filter(visible=True)).to_have_count(0)
        expect(page).to_have_url(re.compile(r'state=Kansas'))
        shot(page, 'dealersbystate')
        page.goto(BASE + '/dealer/15')
        expect(page.get_by_role('heading', name='Customer reviews')).to_be_visible()
        expect(page.get_by_text('Total grid-enabled service-desk')).to_be_visible()
        shot(page, 'dealer_id_reviews')
        page.get_by_role('link', name='Review Dealer').click()
        page.get_by_label('Review', exact=True).fill(REVIEW)
        page.get_by_label('Car make and model').select_option(label='Honda Civic (2024)')
        page.get_by_label('I bought a car here').check()
        page.get_by_label('Purchase date').fill('2025-03-12')
        shot(page, 'dealership_review_submission')
        page.get_by_role('button', name='Submit review').click()
        expect(page.get_by_text(REVIEW, exact=True)).to_be_visible()
        expect(page.get_by_text('2024 Honda Civic · positive')).to_be_visible()
        shot(page, 'added_review')
        page.get_by_role('button', name='Log out').click()
        page.get_by_role('link', name='Sign up').click()
        for label, value in [('Username', 'new_driver'), ('First Name', 'New'), ('Last Name', 'Driver'),
                             ('Email', 'new.driver@example.com'), ('Password', PASSWORD)]:
            page.get_by_label(label, exact=True).fill(value)
        page.get_by_role('button', name='Register').click()
        expect(page.get_by_text('new_driver', exact=True)).to_be_visible()
        browser.close()
    print('Browser checks passed: admin session, dealer pages, registration, and review persistence.')


if __name__ == '__main__':
    {'seed': seed, 'evidence': evidence, 'screenshots': screenshots}[sys.argv[1]]()
