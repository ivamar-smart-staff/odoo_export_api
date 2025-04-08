from odoo import models, fields, api, exceptions
import secrets
import string
import jwt
import datetime

def generate_random_secret_key():
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + "-_."
    return ''.join(secrets.choice(alphabet) for _ in range(24))

class AuthModel(models.Model):
    _name = 'auth.model'
    _description = 'JWT Token Configuration'
    name = fields.Char(string='Configuration Name', required=True)
    secret_key = fields.Char(
        string="Secret Key",
        default=lambda self: generate_random_secret_key(),
        required=True,)
    algorithm = fields.Char(string="Algorithm", default="HS256", required=True)
    expiration_hours = fields.Integer(string="Expiration (Hours)", default=24)
    
    def generate_token(self, user_id):
        payload = {
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=self.expiration_hours),
            'iat': datetime.datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    @api.model
    def verify_token(self, token):
        try:
            config = self.search([], limit=1)
            if not config:
                raise exceptions.ValidationError('JWT configuration not found')
            
            return jwt.decode(token, config.secret_key, algorithms=[config.algorithm])
        except jwt.ExpiredSignatureError:
            raise exceptions.ValidationError('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.ValidationError('Invalid token')