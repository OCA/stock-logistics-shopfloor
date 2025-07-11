# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    qty_picked = fields.Float()

    def _pick_qty(self, qty):
        values = {
            "qty_picked": qty,
            "picked": True,
        }
        if qty > self.quantity:
            values["quantity"] = qty
        self.write(values)
        return True

    def _action_done(self):
        for ml in self:
            if ml.qty_picked and ml.picked and ml.qty_picked != ml.quantity:
                ml.quantity = ml.qty_picked
        return super()._action_done()
