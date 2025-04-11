from odoo import http
from odoo.http import request, Response, Controller
from werkzeug.exceptions import BadRequest
import json
import re
import logging

_logger = logging.getLogger(__name__)

class VisitsController(Controller):
    @http.route('/api/visits/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_visits(self):
        # Validação do token via header "Authorization"
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return request.make_response(
                json.dumps({"error": "Token não fornecido no header de autorização"}),
                status=401,
                headers=[("Content-Type", "application/json")]
            )
        token = auth_header.split(" ")[1].strip()
        try:
            request.env["auth.model"].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[("Content-Type", "application/json")]
            )

        page = int(request.params.get('page'))
        page_size = int(request.params.get('page_size'))

        if not page or not page_size:
            raise BadRequest("Os parâmetros 'page' e 'page_size' são obrigatórios na URL.")

        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            raise BadRequest("Os parâmetros 'page' e 'page_size' devem ser números inteiros.")

        offset = (page - 1) * page_size

        leads = request.env['crm.lead'].sudo().search([],offset=offset,limit=page_size)

        json_return = []
        for lead in leads:
            team_member = request.env['crm.team.member'].sudo().search([('email', '=', lead.user_id.login)],limit=1)
            match lead.company_id.selection_base.id: # todo: adicionar os tipos no futuro
                case 1:
                    _logger.info("case 1")
                    for integra in lead.company_id.vendas_ids:
                        if not lead.chanel_1:
                            main_media_id = None
                            break

                        if lead.team_id == integra.team_id:
                            _logger.info("achou o team_id")
                            media_column = integra.stand_id.media_column


                            midia_nome = re.sub(r'\s*\d+$', '', lead.chanel_1.name.strip())
                            columns_map = {
                                'one': 'cod_midia1',
                                'two': 'cod_midia2',
                                'three': 'cod_midia3',
                                'four': 'cod_midia4',
                                'five': 'cod_midia5',
                                'six': 'cod_midia6',
                            }

                            # Identifica qual coluna deve ser usada com base no 'media_column'
                            column_name = columns_map.get(media_column)
                            if not column_name:
                                main_media_id = None
                                break

                            # Percorre as mídias para encontrar a que bate com 'midia_nome'
                            for midia in lead.company_id.midia_ids:
                                if midia.nome_midia == midia_nome:
                                    # Retorna o valor da coluna correta, usando getattr
                                    main_media_id = getattr(midia, column_name, None)
                                else:
                                    main_media_id = None

                                break
                            break

            data = {
                "id": lead.id,
                "third_party_id": None,
                "broker_name": " - ".join(filter(None, [lead.user_id.name, team_member.sales_name])),
                "manager_name": team_member.crm_team_id.user_id.name,
                "superintendent_name": None,
                "indication_broker_name": None,
                "sales_company_id": lead.team_id.id,
                # "another": None,
                "product_id": lead.company_id.id,
                "customer_id": lead.partner_id.id,
                "type_of": lead.type_of_visit, # FIRSTCONTACT, RECURRENCE, PHONECONTACT - puxar de dentro do lead
                "out_of_service": None,  # todo: data de cadastro de lead de uma data diferente do dia de hoje
                "created": lead.create_date.isoformat() if lead.create_date else None,
                "justify_id": None, # todo: não sabemos
                "owner": None, # todo: é pra indicar se já comprou ou n
                # "indication": False,
                "created_by": lead.creator_user_id.id, # todo: id do usuário da recep que criou o lead
                "changed_by": lead.last_editor_id.id, # todo id da ultima pessoa que atualizou o lead
                "changed_when": lead.write_date.isoformat() if lead.write_date else None, # todo: data da mudança
                "main_media_id": main_media_id, #todo: id do first channel
                "deleted": lead.active, # todo: se o lead tá arquivado ou n
                "corretor_account_id_crm": None, #todo: campo pra adicionar nos corretores da equipe de vendas com o usuário deles (ou adicionar no usuário interno deles)
                "recebido_crm": False, #todo: talvez uma integração com a tabela de log
                # "regra3": False,
                "broker_email": lead.user_id.login,
                "product_type_id": None #todo: se é residencial,
            }


            json_return.append(data)

        total_count = request.env['crm.lead'].sudo().search_count([])
        has_next = offset + page_size < total_count

        return request.make_response(
            json.dumps({
                'data': json_return,
                'page': page,
                'page_size': page_size,
                'has_next': has_next,
                'total_count': total_count,
            }),
            headers=[('Content-Type', 'application/json')]
        )

    # _logger.info("Data recebido1: %s", lead.user_id.name)
    # _logger.info("Data recebido2: %s", team_member.sales_name)
    # _logger.info("Data recebido3: %s", team_member)
