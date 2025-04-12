from odoo import http
from odoo.http import request, Response
import json
import logging
from functools import wraps
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class AuthController(http.Controller):

    _RATE_LIMIT = {
        'auth' : (10, 300)
    }

    def _error_response(self, message, status, error_code=None, extra_headers=None):
        response_data = {
            'error': message,
            'code': error_code or str(status)
        }
        headers = self._get_security_headers()
        if extra_headers:
            headers.update(extra_headers)
        return Response(
            json.dumps(response_data, ensure_ascii=False),
            status=status,
            mimetype='application/json',
            headers=headers
        )

    def _success_response(self, data, status=200, extra_headers=None):
        headers = self._get_security_headers()
        if extra_headers:
            headers.update(extra_headers)
        return Response(
            json.dumps(data, ensure_ascii=False),
            status=status,
            mimetype='application/json',
            headers=headers
        )

    def _get_security_headers(self):
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
        }

    def _get_cors_headers(self):
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '86400'
        }

    def _validate_json_input(self, data):
        if not isinstance(data, dict):
            raise ValidationError('Formato JSON inválido')
        login = data.get('login')
        password = data.get('password')
        if not login or not isinstance(login, str):
            raise ValidationError("É necessário informar o login")
        if not password or not isinstance(password, str):
            raise ValidationError("É necessário informar a senha")
        return login, password

    def handle_api_errors(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except ValidationError as ve:
                _logger.warning("Erro de validação: %s", str(ve))
                return self._error_response(
                    str(ve), 401, 'validation_error',
                    extra_headers=self._get_cors_headers()
                )
            except Exception as e:
                _logger.exception("Erro no endpoint %s", f.__name__)
                return self._error_response(
                    "Erro interno no servidor", 500, 'server_error',
                    extra_headers=self._get_cors_headers()
                )

        return wrapper

    def _check_rate_limit(self, endpoint, ip):
        cache_key = f'rate_limit:{endpoint}:{ip}'
        now = datetime.now()
        if not hasattr(request, '_rate_limit_cache'):
            request._rate_limit_cache = {}
        attempts, last_time = request._rate_limit_cache.get(cache_key, (0, now))
        max_attempts, max_time = self._RATE_LIMIT.get(endpoint, (1, 300))
        if now - last_time > timedelta(seconds=max_time):
            attempts = 0
        if attempts >= max_attempts:
            raise ValidationError("Muitas requisições. Tente novamente mais tarde.")
        request._rate_limit_cache[cache_key] = (attempts + 1, now)
        return True

    @http.route('/api/auth/', type='http', auth='none', methods=['POST'], csrf=False)
    @handle_api_errors
    def generate_token(self, **kwargs):
        ip = request.httprequest.remote_addr
        self._check_rate_limit('auth', ip)

        post_data = request.httprequest.get_json(force=True, silent=True) or {}
        login, password = self._validate_json_input(post_data)
        from odoo.addons.odoo_export_api.services.auth_service import AuthService
        auth_service = AuthService(request.env)
        result = auth_service.authenticate_and_generate_token(login, password)
        # Formata a data de expiração em ISO 8601
        result['expires_at'] = result['expires_at'].strftime('%d/%m/%Y %H:%M:%S')
        return self._success_response(result, extra_headers=self._get_cors_headers())

    @http.route('/api/ping', type='http', auth='none', methods=['GET'], csrf=False)
    @handle_api_errors
    def ping(self, **kw):
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise ValidationError("Cabeçalho Authorization ausente ou inválido")
        token = auth_header.split(' ')[1].strip()
        if not token:
            raise ValidationError("Token vazio")
        request.env['auth.model'].sudo().verify_token(token)
        return self._success_response({"status": "pong"}, headers={'Cache-Control': 'no-store'})
