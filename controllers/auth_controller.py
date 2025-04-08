from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo.addons.odoo_export_api.services.auth_service import AuthService

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

            token = AuthService(request.env).authenticate_and_generate_token(login, password)
            return self._success_response({'token': token})

        except Exception as e:
            _logger.exception("Error generating token")
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
        try:
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise Exception("Missing or invalid Authorization header")

            token = auth_header.split(' ')[1]
            payload = request.env['auth.model'].sudo().verify_token(token)

            return Response("pong", status=200, mimetype='text/plain')
        except Exception as e:
            return Response(f"Unauthorized: {str(e)}", status=401, mimetype='text/plain')
