"""Boot the deployed settings in a fresh process, independent of local .env files."""
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class VercelHostingTests(SimpleTestCase):
    def run_deployed(self, code, secret=True):
        env = os.environ.copy()
        for key in ('DEBUG', 'ALLOWED_HOSTS', 'CORS_ALLOW_ALL_ORIGINS', 'TRUST_PROXY_HEADERS',
                    'SECURE_COOKIES', 'SECRET_KEY', 'FRONTEND_DIST', 'DATABASE_PATH'):
            env.pop(key, None)
        env.update(VERCEL='1', VERCEL_URL='spotter-preview.vercel.app',
                   VERCEL_PROJECT_PRODUCTION_URL='spotter.vercel.app', VERCEL_BRANCH_URL='spotter-git-main.vercel.app')
        if secret:
            env['SECRET_KEY'] = 'test-only-serverless-key'
        return subprocess.run([sys.executable, '-c', code], cwd=settings.BASE_DIR,
                              env=env, capture_output=True, text=True, timeout=30)

    def test_deployment_defaults_and_planning_never_access_database(self):
        result = self.run_deployed('''
import gzip
import json
import django
django.setup()
from django.conf import settings
from django.db import connection
from rest_framework.test import APIClient
from routing.tests.test_api import RoutePlanningIntegrationTests
assert settings.SERVERLESS and not settings.DEBUG
assert not settings.CORS_ALLOW_ALL_ORIGINS
assert settings.DATABASES['default']['NAME'] == ':memory:'
assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
assert '*' not in settings.ALLOWED_HOSTS
assert 'spotter-preview.vercel.app' in settings.ALLOWED_HOSTS
assert 'spotter.vercel.app' in settings.ALLOWED_HOSTS
assert 'https://spotter-git-main.vercel.app' in settings.CSRF_TRUSTED_ORIGINS

def reject_database(*args, **kwargs):
    raise AssertionError('The serverless planner must not access a database')

client = APIClient(HTTP_HOST='spotter-preview.vercel.app')
with connection.execute_wrapper(reject_database):
    assert client.get('/api/health/').status_code == 200
    assert client.get('/admin/').status_code == 404
    assert client.post('/api/routes/plan/', {}, format='json').status_code == 400
    case = RoutePlanningIntegrationTests()
    case.client = client
    case.client.credentials(HTTP_ACCEPT_ENCODING='gzip')
    response = case.plan()
    assert response.status_code == 200
    assert response['Content-Encoding'] == 'gzip'
    data = json.loads(gzip.decompress(response.content))
    assert len(data['routes']) == 3
    assert data['recommended_route_id'] is not None
    assert 'hourly_forecast' not in data['routes'][0]['checkpoints'][0]
    assert len(data['corridor']['points'][0]['hourly_forecast']) == 49
print('PASS')
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_deployment_requires_its_own_secret(self):
        result = self.run_deployed('import core.settings', secret=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Set SECRET_KEY in the Vercel project environment.', result.stderr)
