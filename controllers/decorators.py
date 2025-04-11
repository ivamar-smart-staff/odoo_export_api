import logging
from odoo.http import request

_logger = logging.getLogger(__name__)

def auto_authenticate(func):
    def wrapper(*args, **kwargs):
        # Executa a função original
        response = func(*args, **kwargs)

        # Verifica se a resposta possui um atributo 'status_code' e se ele é 404
        if getattr(response, 'status_code', None) == 404:
            _logger.info("Resposta 404 detectada, tentando auto autenticação...")

            try:
                auth_result = request.env['auth.model'].sudo().auto_authenticate_user() # todo: chamae esse metodo dentro do module de autenticação usando o metodo de autenticação do Odoo
                if auth_result.get('success'):
                    _logger.info("Autenticação automática realizada com sucesso, reexecutando a requisição.")
                    # Reexecuta a função após a autenticação
                    response = func(*args, **kwargs)
                else:
                    _logger.warning("Falha na autenticação automática.")
            except Exception as e:
                _logger.exception("Exceção durante a tentativa de autenticação automática: %s", e)
        return response
    return wrapper
