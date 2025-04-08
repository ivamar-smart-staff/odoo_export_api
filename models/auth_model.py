from odoo import models, fields, api, exceptions
import jwt
import datetime

class AuthModel(models.Model):
    _name = 'auth.model'
    _description = 'JWT Token Configuration'

    name = fields.Char(string='Configuration Name', required=True)
    secret_key = fields.Char(string='JWT Secret Key', required=True, default='your-secret-key-here')
    algorithm = fields.Char(string='Algorithm', default='HS256')
    expiration_hours = fields.Integer(string='Token Expiration (hours)', default=24)

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