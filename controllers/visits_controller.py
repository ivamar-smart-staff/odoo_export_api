from odoo import http
from odoo.http import request, Response, Controller
from werkzeug.exceptions import BadRequest
from datetime import datetime, time
import json
import re
import logging
import pytz

from ..utils.date_utils import parse_date

_logger = logging.getLogger(__name__)


class VisitsController(Controller):
    @http.route("/api/visits/", type="http", auth="none", methods=["GET"], csrf=False)
    def get_visits(self):
        # Validação do token via header "Authorization"
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return request.make_response(
                json.dumps({"error": "Token não fornecido no header de autorização"}),
                status=401,
                headers=[("Content-Type", "application/json")],
            )
        token = auth_header.split(" ")[1].strip()
        try:
            request.env["auth.model"].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[("Content-Type", "application/json")],
            )

        # Montagem do domain
        domain = []
        company_id_param = request.params.get("company_id")
        start_date_str = request.params.get("start_date")
        end_date_str = request.params.get("end_date")

        # Filtro por data
        if start_date_str and end_date_str:
            try:
                start_dt = parse_date(start_date_str)
                end_dt = parse_date(end_date_str)

                local_tz = pytz.timezone("America/Sao_Paulo")
                start_dt = local_tz.localize(datetime.combine(start_dt, time.min))
                end_dt = local_tz.localize(datetime.combine(end_dt, time.max))

                start_utc = start_dt.astimezone(pytz.utc)
                end_utc = end_dt.astimezone(pytz.utc)

                domain.append(("create_date", ">=", start_utc))
                domain.append(("create_date", "<=", end_utc))

                _logger.info("Domínio após filtro de datas: %s", domain)

            except Exception as e:
                _logger.exception("Erro ao converter datas: %s", e)
                return request.make_response(
                    json.dumps(
                        {
                            "error": "Erro ao converter as datas. Use um dos formatos: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS ou DD/MM/YYYY."
                        }
                    ),
                    status=400,
                    headers=[("Content-Type", "application/json")],
                )

        # Filtro por company_id
        if company_id_param:
            try:
                company_id = int(company_id_param)
                domain.append(("company_id", "=", company_id))
            except ValueError:
                return request.make_response(
                    json.dumps(
                        {
                            "error": "O parâmetro 'company_id' deve ser um número inteiro."
                        }
                    ),
                    status=400,
                    headers=[("Content-Type", "application/json")],
                )

        # Paginação
        page = request.params.get("page")
        page_size = request.params.get("page_size")
        if not page or not page_size:
            raise BadRequest(
                "Os parâmetros 'page' e 'page_size' são obrigatórios na URL."
            )
        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            raise BadRequest(
                "Os parâmetros 'page' e 'page_size' devem ser números inteiros."
            )

        offset = (page - 1) * page_size

        # Busca paginada usando o domain
        leads = (
            request.env["crm.lead"]
            .sudo()
            .search(domain, offset=offset, limit=page_size)
        )

        json_return = []
        for lead in leads:
            team_member = (
                request.env["crm.team.member"]
                .sudo()
                .search([("email", "=", lead.user_id.login)], limit=1)
            )

            # 1) filtra só as categorias “folha” (sem filhos)
            children_size = lead.product_category_ids.filtered(lambda c: not c.child_id)

            # 2) agrupa por parent → [filhos]
            sizes_by_parent = {}
            for cat in children_size:
                parent_name = cat.parent_id.name or "Sem categoria pai"
                sizes_by_parent.setdefault(parent_name, []).append(cat.name)

            # Lógica de main_media_id conforme seu case
            main_media_id = None
            if lead.company_id.selection_base.id == 1:
                for integra in lead.company_id.vendas_ids:
                    if not lead.chanel_1:
                        main_media_id = None
                        break
                    if lead.team_id == integra.team_id:
                        media_column = integra.stand_id.media_column
                        midia_nome = re.sub(r"\s*\d+$", "", lead.chanel_1.name.strip())
                        columns_map = {
                            "one": "cod_midia1",
                            "two": "cod_midia2",
                            "three": "cod_midia3",
                            "four": "cod_midia4",
                            "five": "cod_midia5",
                            "six": "cod_midia6",
                        }
                        column_name = columns_map.get(media_column)
                        if not column_name:
                            main_media_id = None
                            break
                        for midia in lead.company_id.midia_ids:
                            if midia.nome_midia == midia_nome:
                                main_media_id = getattr(midia, column_name, None)
                                break
                        break

            data = {
                "id": lead.id,
                "third_party_id": None,
                "broker_name": " - ".join(
                    filter(None, [lead.user_id.name, team_member.sales_name])
                ),
                "manager_name": team_member.crm_team_id.user_id.name,
                "superintendent_name": None,
                "indication_broker_name": None,
                "sales_company_id": lead.team_id.id,
                "product_id": lead.company_id.id,
                "customer_id": lead.partner_id.id,
                "type_of": {
                    "name": lead.type_of_visit,
                    "sub_type_of": lead.type_of_visit2 or None
                },
                "out_of_hours": lead.fora_do_expediente,
                "out_of_service": None,
                "created": lead.create_date.isoformat() if lead.create_date else None,
                "justify_id": None,
                "owner": None,
                "created_by": lead.creator_user_id.id,
                "changed_by": lead.last_editor_id.id,
                "changed_when": (
                    lead.write_date.isoformat() if lead.write_date else None
                ),
                "main_media_id": main_media_id,
                "deleted": not lead.active,
                "corretor_account_id_crm": None,
                "recebido_crm": False,
                "broker_email": lead.user_id.login,
                "product_type_id": None,
                "visit_size": sizes_by_parent,
            }
            json_return.append(data)

        # Total filtrado para paginação
        total_count = request.env["crm.lead"].sudo().search_count(domain)
        has_next = offset + page_size < total_count

        return request.make_response(
            json.dumps(
                {
                    "data": json_return,
                    "page": page,
                    "page_size": page_size,
                    "has_next": has_next,
                    "total_count": total_count,
                }
            ),
            headers=[("Content-Type", "application/json")],
        )
