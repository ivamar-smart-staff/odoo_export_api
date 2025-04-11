from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo import exceptions

# Importa o seu decorator
from odoo.addons.odoo_export_api.controllers.decorators import auto_authenticate

_logger = logging.getLogger(__name__)

class Home(http.Controller):
    @http.route('/web/login', type='http', auth='none', website=True, csrf=False)
    @auto_authenticate
    def login(self, redirect=None, **kw):
        # Removemos a chamada a ensure_db(), pois não existe na sua versão.
        # Se for GET e o usuário já estiver logado com redirect, redireciona.
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)
        
        # Se for POST, tenta autenticar
        if request.httprequest.method == 'POST':
            login = kw.get('login')
            password = kw.get('password')
            try:
                uid = request.session.authenticate(request.db, login, password)
                if uid:
                    # Atualiza o ambiente com o usuário autenticado
                    request.update_env(user=request.env['res.users'].browse(uid))
                    from odoo.addons.odoo_export_api.services.auth_service import AuthService
                    auth_service = AuthService(request.env)
                    token_data = auth_service.authenticate_and_generate_token(login, password)
                    token_data['expires_at'] = token_data['expires_at'].strftime('%d/%m/%Y %H:%M:%S')
                    _logger.info("Usuário autenticado: %s, token gerado", login)
                    # Retorna JSON e interrompe o fluxo (evitando a renderização do template de login)
                    return Response(json.dumps(token_data, ensure_ascii=False),
                                    status=200, mimetype='application/json')
            except exceptions.AccessDenied as e:
                _logger.warning("Falha na autenticação para %s: %s", login, e)
                kw['error'] = "Credenciais inválidas. Tente novamente."
                return request.render("web.login", kw)
            except Exception as e:
                _logger.exception("Erro inesperado durante o login")
                kw['error'] = "Ocorreu um erro interno, tente novamente."
                return request.render("web.login", kw)
        
        # Se a requisição não for POST, renderize a página de login
        return request.render("web.login", kw)
