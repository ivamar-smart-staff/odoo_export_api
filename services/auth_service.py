from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from functools import lru_cache
import time

class AuthService:
    def __init__(self, env):
        self.env = env

    @lru_cache(maxsize=1)
    def _get_jwt_config(self):
        return self.env['auth.model'].sudo().search([], limit=1)

    def authenticate_and_generate_token(self, login, password):
        uid = self._authenticate_user(login, password)
        if not uid:
            raise ValidationError("Credenciais inválidas")
        jwt_config = self._get_jwt_config()
        if not jwt_config:
            raise ValidationError("Configuração JWT ausente")
        token, exp_time = jwt_config.generate_token(uid)
        refresh_token = None
        if jwt_config.allow_refresh_tokens:
            refresh_token = jwt_config.generate_refresh_token(uid)
        return {
            'token': token,
            'expires_at': exp_time,
            'refresh_token': refresh_token
        }

    def refresh_token(self, refresh_token):
        jwt_config = self._get_jwt_config()
        if not jwt_config:
            raise ValidationError("Configuração JWT ausente")
        payload = jwt_config.verify_refresh_token(refresh_token)
        user_id = payload.get('user_id')
        token, exp_time = jwt_config.generate_token(user_id)
        new_refresh_token = None
        if jwt_config.allow_refresh_tokens:
            new_refresh_token = jwt_config.generate_refresh_token(user_id)
        return {
            'token': token,
            'expires_at': exp_time,
            'refresh_token': new_refresh_token
        }

    def _authenticate_user(self, login, password):
        try:
            start = datetime.now()
            uid = self.env['res.users'].sudo().authenticate(
                self.env.cr.dbname, login, password, {}
            )
            elapsed = (datetime.now() - start).total_seconds()
            time.sleep(max(0, 0.5 - elapsed))  # Prevenção contra timing attacks
            return uid
        except Exception:
            time.sleep(0.5)
            return None
