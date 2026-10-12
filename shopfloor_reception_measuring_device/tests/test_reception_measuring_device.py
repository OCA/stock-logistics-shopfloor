# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo_test_helper import FakeModelLoader

from odoo.tools import mute_logger

from odoo.addons.shopfloor_reception.tests.common import CommonCase


class TestSetPackDimension(CommonCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.menu.sudo().set_packaging_dimension = True
        cls.wh = cls.env.ref("stock.warehouse0")
        cls.setUpClassPackaging()
        cls.setUpComponentRegistry()

    def setUp(self):
        super().setUp()
        self.loader = FakeModelLoader(self.env, self.__module__)
        self.loader.backup_registry()

        from .device_model import MeasuringModel

        self.loader.update_registry((MeasuringModel,))
        self.device_model = self.env["measuring.device"].sudo()
        self.device = self.device_model.create(
            {
                "name": "Test Device",
                "device_type": "testdevice",
                "state": "ready",
                "warehouse_id": self.wh.id,
            }
        )

    def tearDown(self):
        self.loader.restore_registry()
        return super().tearDown()

    @classmethod
    def setup_picking(cls):
        return cls._create_picking(lines=[(cls.product_c, 10)])

    @classmethod
    def setUpComponentRegistry(cls):
        from .device_component import MeasuringComponent

        MeasuringComponent._build_component(cls._components_registry)

    @classmethod
    def setUpClassPackaging(cls):
        cls.packaging1 = cls.product_c.packaging_ids
        cls.packaging2 = (
            cls.env["product.packaging"]
            .sudo()
            .create(
                {
                    "name": "Big Box",
                    "product_id": cls.product_c.id,
                    "barcode": "ProductCBigBox",
                    "qty": 6,
                }
            )
        )

    def _assert_response_set_dimension(
        self, response, picking, line, packaging, message=None, devices=None
    ):
        data = {
            "picking": self.data.picking(picking),
            "selected_move_line": self.data.move_line(line),
            "packaging": self.data_detail.packaging_detail(packaging),
        }
        if packaging.measuring_device_id:
            data["assigned_measuring_device"] = self.data.measuring_device(
                packaging.measuring_device_id
            )
        if devices is not None:
            data["measuring_device_choices"] = devices
        self.assert_response(
            response,
            next_state="set_packaging_dimension",
            data=data,
            message=message,
        )

    def _create_device(self, name, **kw):
        vals = {
            "name": name,
            "device_type": "testdevice",
            "state": "ready",
            "warehouse_id": self.wh.id,
        }
        vals.update(kw)
        return self.device_model.create(vals)

    def _dispatch(self, endpoint, picking, line, packaging, **params):
        params.update(
            {
                "picking_id": picking.id,
                "selected_line_id": line.id,
                "packaging_id": packaging.id,
            }
        )
        return self.service.dispatch(
            f"set_packaging_dimension__measuring_device_{endpoint}", params=params
        )

    def _dispatch_assign(self, picking, line, packaging, **params):
        return self._dispatch("assign", picking, line, packaging, **params)

    def _device_choice(self, device, in_use=False):
        return dict(self.data.measuring_device(device), in_use=in_use)

    def test_select_device__no_device(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        # Unlink device so none is found
        self.device.unlink()
        response = self._dispatch_assign(picking, line, self.packaging1)
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            message=self.msg_store.no_measuring_device_found(),
        )

    def test_select_device__device_already_assigned(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        # assign measuring device to packaging2, so it cannot be selected again
        self.packaging2._measuring_device_assign(self.device)
        response = self._dispatch_assign(picking, line, self.packaging1)
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            message=self.msg_store.measuring_device_already_in_use(self.device),
        )

    @mute_logger("odoo.addons.stock_measuring_device.models.measuring_device")
    def test_select_device__ok(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        response = self._dispatch_assign(picking, line, self.packaging1)
        self.assertEqual(self.packaging1.measuring_device_id, self.device)
        # Same screen, w/ the assigned device
        self._assert_response_set_dimension(response, picking, line, self.packaging1)
        self.assertEqual(
            response["data"]["set_packaging_dimension"]["assigned_measuring_device"][
                "id"
            ],
            self.device.id,
        )
        measurements = {
            "weight": 42,
            "height": 43,
            "packaging_length": 44,
            "width": 45,
        }
        measured_packaging = self.device._update_packaging_measures(measurements)
        self.assertEqual(measured_packaging, self.packaging1)
        self.assertEqual(measured_packaging.weight, 42)
        self.assertEqual(measured_packaging.height, 43)
        self.assertEqual(measured_packaging.packaging_length, 44)
        self.assertEqual(measured_packaging.width, 45)

    def test_select_device__domain(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        other_wh = (
            self.env["stock.warehouse"]
            .sudo()
            .create({"name": "Other WH", "code": "OWH"})
        )
        self.device.unlink()
        # Neither a device not ready nor a device from another warehouse
        # can be used.
        self._create_device("Not Ready Device", state="not_ready")
        self._create_device("Other WH Device", warehouse_id=other_wh.id)
        response = self._dispatch_assign(picking, line, self.packaging1)
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            message=self.msg_store.no_measuring_device_found(),
        )

    def test_select_device__other_device_free(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        device2 = self._create_device("Test Device 2")
        # The first device is busy, the second one is the only choice
        self.packaging2._measuring_device_assign(self.device)
        response = self._dispatch_assign(picking, line, self.packaging1)
        self.assertEqual(self.packaging1.measuring_device_id, device2)
        self._assert_response_set_dimension(response, picking, line, self.packaging1)

    def test_select_device__choose(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        device2 = self._create_device("Test Device 2")
        device3 = self._create_device("Test Device 3")
        self.packaging2._measuring_device_assign(device3)
        # Several devices available: the user has to choose
        response = self._dispatch_assign(picking, line, self.packaging1)
        self.assertFalse(self.packaging1.measuring_device_id)
        devices = self.device_model.search(
            [("id", "in", (self.device | device2 | device3).ids)]
        )
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            devices=[self._device_choice(d, in_use=d == device3) for d in devices],
        )
        # Choose one
        response = self._dispatch_assign(
            picking, line, self.packaging1, device_id=device2.id
        )
        self.assertEqual(self.packaging1.measuring_device_id, device2)
        self._assert_response_set_dimension(response, picking, line, self.packaging1)

    def test_select_device__choose_device_in_use(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        device2 = self._create_device("Test Device 2")
        device3 = self._create_device("Test Device 3")
        # Taken in the meantime by another user
        self.packaging2._measuring_device_assign(device3)
        response = self._dispatch_assign(
            picking, line, self.packaging1, device_id=device3.id
        )
        self.assertFalse(self.packaging1.measuring_device_id)
        devices = self.device_model.search(
            [("id", "in", (self.device | device2 | device3).ids)]
        )
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            message=self.msg_store.measuring_device_already_in_use(device3),
            devices=[self._device_choice(d, in_use=d == device3) for d in devices],
        )

    def test_select_device__already_assigned_to_packaging(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        # Eg: the user left the screen and comes back
        self.packaging1._measuring_device_assign(self.device)
        response = self._dispatch_assign(picking, line, self.packaging1)
        self._assert_response_set_dimension(response, picking, line, self.packaging1)
        self.assertEqual(self.packaging1.measuring_device_id, self.device)

    @mute_logger("odoo.addons.stock_measuring_device.models.measuring_device")
    def test_refresh(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        self.packaging1._measuring_device_assign(self.device)
        self.device._update_packaging_measures(
            {"weight": 42, "height": 43, "packaging_length": 44, "width": 45}
        )
        response = self._dispatch("refresh", picking, line, self.packaging1)
        # The device is kept, the measured values are returned
        self.assertEqual(self.packaging1.measuring_device_id, self.device)
        self._assert_response_set_dimension(response, picking, line, self.packaging1)
        packaging_data = response["data"]["set_packaging_dimension"]["packaging"]
        self.assertEqual(packaging_data["height"], 43)
        self.assertEqual(packaging_data["length"], 44)

    def test_set_packaging_dimension_releases_device(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        self.packaging1._measuring_device_assign(self.device)
        # Confirm (or Done/Skip): the packaging is processed
        self.service.dispatch(
            "set_packaging_dimension",
            params={
                "picking_id": picking.id,
                "selected_line_id": line.id,
                "packaging_id": self.packaging1.id,
            },
        )
        self.assertFalse(self.packaging1.measuring_device_id)

    def test_release_device__no_device_assigned(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        response = self._dispatch("release", picking, line, self.packaging1)
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            message=self.msg_store.no_measuring_device_to_release(self.packaging1),
        )

    def test_release_device__ok(self):
        picking = self.setup_picking()
        line = picking.move_line_ids[0]
        # Assign device to the packaging so it can be released
        self.packaging1._measuring_device_assign(self.device)
        response = self._dispatch("release", picking, line, self.packaging1)
        self.assertFalse(self.packaging1.measuring_device_id)
        self._assert_response_set_dimension(
            response,
            picking,
            line,
            self.packaging1,
            message=self.msg_store.measuring_device_released(
                self.packaging1, self.device
            ),
        )
