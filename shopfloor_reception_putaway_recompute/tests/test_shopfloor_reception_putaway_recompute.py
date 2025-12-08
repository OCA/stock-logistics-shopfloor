# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
# pylint: disable=missing-return

from odoo.addons.shopfloor_reception.tests.common import CommonCase


class TestShopfloorReceptionPutawayRecompute(CommonCase):
    @classmethod
    def setUpClassBaseData(cls):
        super().setUpClassBaseData()
        cls.picking_type.sudo().allow_to_recompute_putaways = True
        cls.default_destination = cls.menu.picking_type_ids.default_location_dest_id
        cls.sub_location_1 = (
            cls.env["stock.location"]
            .sudo()
            .create(
                {
                    "name": "Sub location 1",
                    "location_id": cls.default_destination.id,
                    "usage": "internal",
                }
            )
        )
        cls.sub_location_2 = (
            cls.env["stock.location"]
            .sudo()
            .create(
                {
                    "name": "Sub location 2",
                    "location_id": cls.default_destination.id,
                    "usage": "internal",
                }
            )
        )
        cls.rule = (
            cls.env["stock.putaway.rule"]
            .sudo()
            .create(
                {
                    "product_id": cls.product_a.id,
                    "location_in_id": cls.default_destination.id,
                    "location_out_id": cls.sub_location_1.id,
                }
            )
        )
        cls.picking = cls._create_picking(lines=[(cls.product_a, 10)])
        cls.picking.action_confirm()
        cls.move_line = cls.picking.move_line_ids

    def test_recompute_putaway(self):
        """Check the hook function is working as expected."""
        self.assertEqual(self.sub_location_1, self.move_line.location_dest_id)
        self.rule.location_out_id = self.sub_location_2
        self.service._recompute_putaway_on_line(self.picking.move_line_ids)
        self.assertEqual(self.sub_location_2, self.move_line.location_dest_id)

    def test_change_package_type_on_package(self):
        """Check hook is called on set_package_type endpoint."""
        self.rule.unlink()
        self.package_type = self.env.ref("stock.package_type_01")
        self.package_type.sudo().barcode = "CAGE"
        self.storage_category = (
            self.env["stock.storage.category"]
            .sudo()
            .create(
                {
                    "name": "Cage category",
                    "capacity_ids": [
                        (
                            0,
                            0,
                            {
                                "package_type_id": self.package_type.id,
                                "quantity": 1,
                            },
                        )
                    ],
                }
            )
        )
        self.sub_location_1.storage_category_id = self.storage_category
        self.sub_location_2.storage_category_id = self.storage_category
        self.env["stock.storage.location.sequence"].sudo().create(
            {
                "package_type_id": self.package_type.id,
                "location_id": self.sub_location_2.id,
                "sequence": 1,
            }
        )
        self.service.dispatch("scan_document", params={"barcode": self.picking.name})
        self.move_line.qty_picked = self.move_line.quantity_product_uom
        response = self.service.dispatch(
            "select_dest_package",
            params={
                "picking_id": self.picking.id,
                "selected_line_id": self.move_line.id,
                "barcode": "CAGE-0001",
                "confirmation": True,
            },
        )
        response = self.service.dispatch(
            "set_package_type",
            params={
                "picking_id": self.picking.id,
                "selected_line_id": self.move_line.id,
                "barcode": "CAGE",
            },
        )
        self.assertEqual(response["next_state"], "set_destination")
        self.assertEqual(
            self.move_line.result_package_id.package_type_id, self.package_type
        )
        self.assertEqual(self.sub_location_2, self.move_line.location_dest_id)
