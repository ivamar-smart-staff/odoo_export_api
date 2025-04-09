from odoo import http
from odoo.http import request, Response
import json
import logging
import time
from functools import wraps
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class AuthController(http.Controller):
    # --- Configurações de rate limiting por endpoint ---
    _RATE_LIMIT = {
        'change_password': (5, 60),  # 5 tentativas por 60 segundos
        'auth': (10, 300)           # 10 tentativas por 5 minutos
    }

    # ---- Helpers ----
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

    def _success_response(self, data, status=200, headers=None):
        default_headers = self._get_security_headers()
        if headers:
            default_headers.update(headers)
        return Response(
            json.dumps(data, ensure_ascii=False),
            status=status,
            mimetype='application/json',
            headers=default_headers
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
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400',  # 1 dia
        }

    def _validate_json_input(self, data):
        if not isinstance(data, dict):
            raise ValidationError("Formato JSON inválido")
        login = data.get('login')
        password = data.get('password')
        if not login or not isinstance(login, str):
            raise ValidationError("É necessário fornecer um login válido")
        if not password or not isinstance(password, str):
            raise ValidationError("É necessário fornecer uma senha válida")
        return login, password

    def _log_auth_attempt(self, login, success, ip_address):
        log_message = "Auth %s para %s de %s" % (
            "sucesso" if success else "FALHOU",
            login,
            ip_address
        )
        _logger.info(log_message)

    def _log_security_event(self, user_id=None, event_type=None, ip_address=None, metadata=None):
        log_data = {
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        _logger.info("Security Event: %s", json.dumps(log_data))
        try:
            request.env['auth.security.log'].sudo().create({
                'name': event_type,
                'user_id': user_id,
                'ip_address': ip_address,
                'details': str(metadata)
            })
        except Exception as e:
            _logger.error("Falha ao salvar log de segurança: %s", str(e))

    # ---- Decorador para tratamento padronizado de erros ----
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

    def _check_rate_limit(self, endpoint_key, ip):
        cache_key = f"{endpoint_key}_{ip}"
        now = datetime.now()
        if not hasattr(request, '_rate_limit_cache'):
            request._rate_limit_cache = {}
        attempts, last_time = request._rate_limit_cache.get(cache_key, (0, now))
        max_attempts, time_window = self._RATE_LIMIT[endpoint_key]
        if now - last_time > timedelta(seconds=time_window):
            attempts = 0
        if attempts >= max_attempts:
            _logger.warning("Limite de requisições atingido para %s a partir do IP %s", endpoint_key, ip)
            raise ValidationError("Muitas requisições. Tente novamente mais tarde.")
        request._rate_limit_cache[cache_key] = (attempts + 1, now)
        return True

    # ---- Endpoints ----
    @http.route('/api/auth/', type='http', auth='none', methods=['POST'], csrf=False)
    @handle_api_errors
    def generate_token(self, **kwargs):
        post_data = request.httprequest.get_json(force=True, silent=True) or {}
        login, password = self._validate_json_input(post_data)
        from odoo.addons.odoo_export_api.services.auth_service import AuthService 
        auth_service = AuthService(request.env)
        result = auth_service.authenticate_and_generate_token(login, password)
        self._log_auth_attempt(login, True, request.httprequest.remote_addr)
        # Formata a data de expiração em ISO 8601
        result['expires_at'] = result['expires_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        return self._success_response(result, headers=self._get_cors_headers())

    @http.route('/api/auth/refresh-token', type='http', auth='none', methods=['POST'], csrf=False)
    @handle_api_errors
    def refresh_token(self, **kwargs):
        ip = request.httprequest.remote_addr
        self._check_rate_limit('auth', ip)
        post_data = request.httprequest.get_json(force=True, silent=True) or {}
        refresh_token_val = post_data.get('refresh_token')
        if not refresh_token_val:
            raise ValidationError("Refresh token obrigatório")
        from odoo.addons.odoo_export_api.services.auth_service import AuthService 
        auth_service = AuthService(request.env)
        result = auth_service.refresh_token(refresh_token_val)
        result['expires_at'] = result['expires_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        return self._success_response(result, headers=self._get_cors_headers())

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
