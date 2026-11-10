# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


from odoo.addons.component.core import Component


class Reception(Component):
    _inherit = "shopfloor.reception"

    def _recompute_putaway_on_line(self, line, allow_unsafe=True):
        if allow_unsafe:
            line = line.with_context(allow_unsafe_putaway_recompute=True)
        line._recompute_putaways()
