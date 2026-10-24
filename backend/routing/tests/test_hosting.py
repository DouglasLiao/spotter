from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import Client, SimpleTestCase, override_settings


class HostingTests(SimpleTestCase):
    def test_backend_only_environment_has_no_frontend_shell(self):
        with override_settings(FRONTEND_DIST=None):
            self.assertEqual(self.client.get('/').status_code, 404)

    def test_single_image_serves_shell_assets_and_api_without_fallback_collisions(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text('<html><div id="root"></div></html>')
            (root / 'assets').mkdir()
            (root / 'static').mkdir()
            (root / 'assets' / 'index-12345678.js').write_text('console.log("frontend");')
            with override_settings(FRONTEND_DIST=directory, WHITENOISE_ROOT=directory, STATIC_ROOT=root / 'static'):
                client = Client()
                for path in ('/', '/client-side-route'):
                    result = client.get(path)
                    self.assertEqual(result.status_code, 200)
                    self.assertIn(b'id="root"', b''.join(result.streaming_content))
                    self.assertEqual(result['Cache-Control'], 'no-cache')
                asset = client.get('/assets/index-12345678.js')
                self.assertEqual(asset.status_code, 200)
                self.assertIn('immutable', asset['Cache-Control'])
                asset.close()
                self.assertEqual(client.get('/api/health/').json(), {'status': 'ok'})
                for path in ('/api/missing/', '/api', '/assets/missing.js', '/static/missing.css'):
                    self.assertEqual(client.get(path).status_code, 404)
