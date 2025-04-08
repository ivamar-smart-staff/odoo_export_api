from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

class AuthController(http.Controller):

    @http.route('/api/auth/', type='http', auth='none', methods=['POST'], csrf=False)
    def generate_token(self, **kwargs):
        try:
            post = request.httprequest.get_json(force=True)

            login = post.get('login')
            password = post.get('password')

            if not login or not password:
                return self._error_response('Login and password required', 400)

            uid = request.session.authenticate(request.db, login, password)

            if not uid:
                return self._error_response('Invalid credentials', 401)

            jwt_model = request.env['auth.model'].sudo().search([], limit=1)
            if not jwt_model:
                return self._error_response('JWT configuration missing', 500)

            token = jwt_model.generate_token(uid)
            return self._success_response({'token': token})

        except Exception as e:
            return self._error_response(str(e), 500)

    def _error_response(self, message, status):
        return Response(
            json.dumps({'error': message}),
            status=status,
            mimetype='application/json'
        )

    def _success_response(self, data):
        return Response(
            json.dumps(data),
            status=200,
            mimetype='application/json'
        )
    
    @http.route('/api/ping', type='http', auth='none', methods=['GET'], csrf=False)
    def ping(self, **kw):
        return "pong"
