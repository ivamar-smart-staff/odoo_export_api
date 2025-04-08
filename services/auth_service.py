from odoo.exceptions import ValidationError

class AuthService:

    def __init__(self, env):
        self.env = env

    def authenticate_and_generate_token(self, login, password):
        uid = self._authenticate_user(login, password)

        if not uid:
            raise ValidationError("Invalid credentials")

        jwt_config = self.env['auth.model'].sudo().search([], limit=1)
        if not jwt_config:
            raise ValidationError("JWT configuration missing")

        return jwt_config.generate_token(uid)

    def _authenticate_user(self, login, password):
        return self.env['res.users'].sudo().authenticate(
            self.env.cr.dbname, login, password, {}
        )
