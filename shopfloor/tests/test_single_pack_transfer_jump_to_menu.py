# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests import Form

from odoo.addons.shopfloor.tests.test_single_pack_transfer_base import (
    SinglePackTransferCommonBase,
)

# pylint: disable=missing-return


class TestSinglePackTransferJumptoMenu(SinglePackTransferCommonBase):
    @classmethod
    def setUpClassBaseData(cls, *args, **kwargs):
        super().setUpClassBaseData(*args, **kwargs)
        cls.pack_a = cls.env["stock.quant.package"].create(
            {"location_id": cls.stock_location.id}
        )
        cls.quant_a = (
            cls.env["stock.quant"]
            .sudo()
            .create(
                {
                    "product_id": cls.product_a.id,
                    "location_id": cls.shelf1.id,
                    "quantity": 1,
                    "package_id": cls.pack_a.id,
                }
            )
        )
        cls.shelf1_2 = cls.shelf1.sudo().copy({"name": "Shelf 1_2"})
        cls.pack_b = cls.env["stock.quant.package"].create(
            {"location_id": cls.stock_location.id}
        )
        cls.quant_b = (
            cls.env["stock.quant"]
            .sudo()
            .create(
                {
                    "product_id": cls.product_b.id,
                    "location_id": cls.shelf1_2.id,
                    "quantity": 1,
                    "package_id": cls.pack_b.id,
                }
            )
        )
        cls.picking = cls._create_initial_move(
            lines=[(cls.product_a, 1), (cls.product_b, 1)]
        )
        cls.menu2 = cls.env.ref("shopfloor.shopfloor_menu_demo_zone_picking")

    @classmethod
    def _create_initial_move(cls, lines):
        """Create the move to satisfy the pre-condition before /start"""
        picking_form = Form(cls.env["stock.picking"])
        picking_form.picking_type_id = cls.picking_type
        picking_form.location_id = cls.stock_location
        picking_form.location_dest_id = cls.shelf2
        for line in lines:
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = line[0]
                move.product_uom_qty = line[1]
        picking = picking_form.save()
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _simulate_started(self, package):
        """Replicate what the /start endpoint would do on the given package.

        Used to test the next endpoints (/validate and /cancel)
        """
        package_level = self.picking.move_line_ids.package_level_id.filtered(
            lambda pl: pl.package_id == package
        )
        package_level.is_done = True
        return package_level

    def assert_response_jump_to_menu(self, response, data=None, message=None):
        self.assert_response(
            response,
            next_state="jump_to_menu",
            data=data,
            message=message,
        )

    def test_validate_jump_to_menu(self):
        self.menu.sudo().jump_to_single_pack_transfer_validate_menu_id = self.menu2
        package_level = self._simulate_started(self.pack_a)
        response = self.service.dispatch(
            "validate",
            params={
                "package_level_id": package_level.id,
                "location_barcode": self.shelf2.barcode,
            },
        )
        expected_data = {
            "menu_id": self.menu2.id,
            "next_state": "start",
            "states_data": '{"start": {"zones": []}}',
        }
        self.assert_response_jump_to_menu(response, expected_data)
