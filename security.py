"""Cloud-only transport controls. Model math is unchanged."""
import base64
import binascii
import hmac
import os
import time
from collections import deque
from urllib.parse import urlsplit
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 10 * 1024 * 1024 + 64 * 1024

class ResearchSecurity:
    def __init__(self, app):
        self.app = app
        self.busy = False
        self.attempts = deque()
        self.predictions = deque()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        async def secured_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'cache-control', b'no-store'),
                    (b'x-content-type-options', b'nosniff'),
                    (b'x-frame-options', b'DENY'),
                    (b'referrer-policy', b'no-referrer'),
                    (b'content-security-policy', b"frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"),
                ]
            await send(message)
        async def reject(status, detail, extra=None):
            await JSONResponse({'detail': detail}, status_code=status, headers=extra)(scope, receive, secured_send)
        if scope['path'] == '/api/health' and scope['method'] == 'GET':
            return await self.app(scope, receive, secured_send)
        now = time.monotonic()
        while self.attempts and self.attempts[0] < now - 60:
            self.attempts.popleft()
        if len(self.attempts) >= 120:
            return await reject(429, 'Request limit reached.', {'Retry-After':'60'})
        self.attempts.append(now)
        expected_user = os.environ.get('ONCOLENS_USERNAME', '')
        expected_password = os.environ.get('ONCOLENS_PASSWORD', '')
        if not expected_user or len(expected_password) < 20:
            return await reject(503, 'Research access is not configured.')
        auth = headers.get(b'authorization', b'')
        try:
            scheme, token = auth.split(b' ', 1)
            if scheme.lower() != b'basic' or len(token) > 1024:
                raise ValueError()
            user, password = base64.b64decode(token, validate=True).split(b':', 1)
            valid = hmac.compare_digest(user, expected_user.encode()) & hmac.compare_digest(password, expected_password.encode())
        except (ValueError, binascii.Error):
            valid = False
        if not valid:
            return await reject(401, 'Research access requires sign-in.', {'WWW-Authenticate':'Basic realm="OncoLens research", charset="UTF-8"'})
        predicting = scope['path'] == '/api/predict' and scope['method'] == 'POST'
        if predicting:
            origin = headers.get(b'origin')
            if origin:
                try:
                    parsed = urlsplit(origin.decode('ascii'))
                    allowed = parsed.scheme in ('http','https') and parsed.netloc.lower() == headers.get(b'host',b'').decode('ascii').lower()
                except (ValueError, UnicodeError):
                    allowed = False
                if not allowed:
                    return await reject(403, 'Cross-origin requests are not permitted.')
            while self.predictions and self.predictions[0] < now - 60:
                self.predictions.popleft()
            if len(self.predictions) >= 12:
                return await reject(429, 'Prediction limit reached.', {'Retry-After':'60'})
            length = headers.get(b'content-length')
            if length:
                try:
                    if int(length) < 0 or int(length) > MAX_BODY_BYTES:
                        return await reject(413, 'Request exceeds upload limit.')
                except ValueError:
                    return await reject(400, 'Invalid request length.')
            if self.busy:
                return await reject(503, 'Research worker is busy. Retry shortly.', {'Retry-After':'5'})
            self.predictions.append(now)
            self.busy = True
        try:
            await self.app(scope, receive, secured_send)
        finally:
            if predicting:
                self.busy = False
