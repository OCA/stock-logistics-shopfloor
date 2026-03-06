# TODO: Find a module to put this in

from odoo import api, fields, models


class PackageType(models.Model):
    _inherit = 'stock.package.type'

    package_carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Dedicated carrier",
    )
