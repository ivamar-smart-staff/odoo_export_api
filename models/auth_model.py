from odoo import models, fields, api, exceptions
import secrets
import string
import jwt
import datetime
import pytz
from odoo.tools import lazy_property
import logging

_logger = logging.getLogger(__name__)

def generate_random_secret_key():
    alphabet = string.ascii_letters + string.digits + "-_."
    return ''.join(secrets.choice(alphabet) for _ in range(24))

class AuthModel(models.Model):
    _name = 'auth.model'
    _description = 'JWT Token Configuration'

    # Campos existentes
    name = fields.Char(string='Configuration Name', required=True)
    secret_key = fields.Char(
        string="Secret Key",
        default=lambda self: generate_random_secret_key(),
        required=True
    )
    algorithm = fields.Char(string="Algorithm", default="HS256", required=True)
    expiration_hours = fields.Integer(string="Expiration (Hours)", default=24)

    # Novos campos
    key_rotation_days = fields.Integer(string="Key Rotation (Days)", default=30)
    last_rotation_date = fields.Datetime(string="Last Rotation")
    allow_refresh_tokens = fields.Boolean(string="Allow Refresh Tokens", default=True)
    refresh_token_expiry = fields.Integer(string="Refresh Token Expiry (Days)", default=30)

    @lazy_property
    def _token_cache(self):
        return {}  # Em produção, use um cache distribuído

    def invalidate_user_tokens(self, user_id):
        # Reinicializa o cache sobrescrevendo a propriedade lazy
        self.__dict__['_token_cache'] = {}
        self.env['auth.refresh.token'].search([('user_id', '=', user_id)]).unlink()


    def rotate_secret_key(self):
        self.ensure_one()
        self.write({
            'secret_key': generate_random_secret_key(),
            'last_rotation_date': fields.Datetime.now()
        })
        _logger.info("Chave JWT rotacionada")

    def generate_token(self, user_id):
        exp_utc = datetime.datetime.utcnow() + datetime.timedelta(hours=self.expiration_hours)
        payload = {
            'user_id': user_id,
            'exp': exp_utc,
            'iat': datetime.datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
        exp_local = exp_utc.replace(tzinfo=pytz.utc).astimezone(sao_paulo_tz)
        return token, exp_local

    def verify_token(self, token):
        try:
            config = self.search([], limit=1)
            if not config:
                raise exceptions.ValidationError('JWT configuration not found')
            return jwt.decode(token, config.secret_key, algorithms=[config.algorithm])
        except jwt.ExpiredSignatureError:
            raise exceptions.ValidationError('Token expirado')
        except jwt.InvalidTokenError:
            raise exceptions.ValidationError('Token inválido')

    def generate_refresh_token(self, user_id):
        exp_utc = datetime.datetime.utcnow() + datetime.timedelta(days=self.refresh_token_expiry)
        payload = {
            'user_id': user_id,
            'exp': exp_utc,
            'type': 'refresh'
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        self.env['auth.refresh.token'].create({
            'token': token,
            'user_id': user_id,
            'expiry_date': exp_utc
        })
        return token

    def verify_refresh_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            valid_count = self.env['auth.refresh.token'].search_count([
                ('token', '=', token),
                ('user_id', '=', payload['user_id']),
                ('expiry_date', '>', fields.Datetime.now())
            ])
            if not valid_count:
                raise jwt.InvalidTokenError("Refresh token revogado")
            return payload
        except jwt.ExpiredSignatureError:
            raise exceptions.ValidationError('Refresh token expirado')
        except jwt.InvalidTokenError:
            raise exceptions.ValidationError('Refresh token inválido')

class AuthRefreshToken(models.Model):
    """Modelo para gerenciamento de refresh tokens"""
    _name = 'auth.refresh.token'
    _description = 'Refresh Tokens'

    token = fields.Char(string="Token", required=True, index=True)
    user_id = fields.Many2one('res.users', string="User", required=True)
    expiry_date = fields.Datetime(string="Expiry Date", required=True)
    created_at = fields.Datetime(string="Created At", default=fields.Datetime.now)

class AuthSecurityLog(models.Model):
    """Modelo para logs de segurança"""
    _name = 'auth.security.log'
    _description = 'Security Logs'
    _order = 'create_date desc'

    name = fields.Char(string="Event Type", required=True)
    user_id = fields.Many2one('res.users', string="User")
    ip_address = fields.Char(string="IP Address")
    details = fields.Text(string="Details")
    create_date = fields.Datetime(string="Date", default=fields.Datetime.now)
