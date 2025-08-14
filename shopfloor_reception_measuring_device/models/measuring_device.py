# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MeasuringDevice(models.Model):
    _inherit = "measuring.device"

    is_default = fields.Boolean(
        "Default",
        default=False,
        help=(
            "The device set as the default one will be "
            "the one used in the reception scenario."
        ),
    )

    @api.constrains("is_default")
    def _check_is_default(self):
        self.ensure_one()
        if self.search_count([("is_default", "=", True)]) > 1:
            raise ValidationError(
                self.env._("Only one measuring device can be the default one.")
            )
