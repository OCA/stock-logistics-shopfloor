# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.addons.base_rest.components.service import to_int
from odoo.addons.component.core import Component


class Reception(Component):
    _inherit = "shopfloor.reception"

    def _get_measuring_device_domain(self):
        warehouse = self.work.menu.picking_type_ids.warehouse_id
        return [
            ("warehouse_id", "in", warehouse.ids),
            ("state", "=", "ready"),
        ]

    def _get_measuring_devices_in_use(self, devices):
        return (
            self.env["product.packaging"]
            .sudo()
            .search([("measuring_device_id", "in", devices.ids)])
            .measuring_device_id
        )

    def _data_for_set_packaging_dimension(self, picking, line, packaging):
        data = super()._data_for_set_packaging_dimension(picking, line, packaging)
        device = packaging.sudo().measuring_device_id
        if device:
            data["assigned_measuring_device"] = self.data.measuring_device(device)
        return data

    def _response_for_set_packaging_dimension_choose_device(
        self, picking, line, packaging, devices, message=None
    ):
        data = self._data_for_set_packaging_dimension(picking, line, packaging)
        in_use = self._get_measuring_devices_in_use(devices)
        data["measuring_device_choices"] = [
            dict(self.data.measuring_device(device), in_use=device in in_use)
            for device in devices
        ]
        return self._response(
            next_state="set_packaging_dimension", data=data, message=message
        )

    def set_packaging_dimension__measuring_device_assign(
        self, picking_id, selected_line_id, packaging_id, device_id=None
    ):
        """Assign a measuring device to the packaging.

        If exactly one device is available it's assigned right away,
        if several are available the user has to choose one
        (`measuring_device_choices` in the response, then call again with `device_id`).

        Transitions:
            - set_packaging_dimension: always
        """
        picking = self.env["stock.picking"].sudo().browse(picking_id)
        selected_line = self.env["stock.move.line"].sudo().browse(selected_line_id)
        packaging = self.env["product.packaging"].sudo().browse(packaging_id)
        if not packaging:
            return self._response_for_set_packaging_dimension(
                picking,
                selected_line,
                packaging,
                message=self.msg_store.record_not_found(),
            )
        if packaging.measuring_device_id:
            # Already assigned (eg: the user came back to the screen),
            # keep using the same device.
            return self._response_for_set_packaging_dimension(
                picking, selected_line, packaging
            )
        devices = self.env["measuring.device"].search(
            self._get_measuring_device_domain()
        )
        free_devices = devices - self._get_measuring_devices_in_use(devices)
        msg = None
        if not devices:
            msg = self.msg_store.no_measuring_device_found()
        elif not free_devices:
            msg = self.msg_store.measuring_device_already_in_use(devices)
        if msg:
            return self._response_for_set_packaging_dimension(
                picking, selected_line, packaging, message=msg
            )
        if device_id:
            device = free_devices.filtered(lambda d: d.id == device_id)
            if not device:
                # Taken in the meantime (or not a valid choice): choose again
                chosen = devices.filtered(lambda d: d.id == device_id)
                msg = (
                    self.msg_store.measuring_device_already_in_use(chosen)
                    if chosen
                    else self.msg_store.record_not_found()
                )
                return self._response_for_set_packaging_dimension_choose_device(
                    picking, selected_line, packaging, devices, message=msg
                )
        elif len(free_devices) > 1:
            return self._response_for_set_packaging_dimension_choose_device(
                picking, selected_line, packaging, devices
            )
        else:
            device = free_devices
        packaging._measuring_device_assign(device)
        return self._response_for_set_packaging_dimension(
            picking, selected_line, packaging
        )

    def set_packaging_dimension__measuring_device_refresh(
        self, picking_id, selected_line_id, packaging_id
    ):
        """Reload the packaging, eg: to get the values sent by the device.

        The device sends its measures to Odoo by itself, this only reloads
        the screen and keeps the device assigned.

        Transitions:
            - set_packaging_dimension: always
        """
        picking = self.env["stock.picking"].sudo().browse(picking_id)
        selected_line = self.env["stock.move.line"].sudo().browse(selected_line_id)
        packaging = self.env["product.packaging"].sudo().browse(packaging_id)
        message = None
        if not packaging:
            message = self.msg_store.record_not_found()
        return self._response_for_set_packaging_dimension(
            picking, selected_line, packaging, message=message
        )

    def set_packaging_dimension__measuring_device_release(
        self, picking_id, selected_line_id, packaging_id
    ):
        picking = self.env["stock.picking"].sudo().browse(picking_id)
        selected_line = self.env["stock.move.line"].sudo().browse(selected_line_id)
        packaging = self.env["product.packaging"].sudo().browse(packaging_id)
        device = packaging.measuring_device_id
        if not packaging:
            msg = self.msg_store.record_not_found()
        elif not device:
            msg = self.msg_store.no_measuring_device_to_release(packaging)
        else:
            packaging._measuring_device_release()
            msg = self.msg_store.measuring_device_released(packaging, device)
        return self._response_for_set_packaging_dimension(
            picking, selected_line, packaging, message=msg
        )

    def set_packaging_dimension(
        self, picking_id, selected_line_id, packaging_id, cancel=False, **kwargs
    ):
        # Done/Skip/Confirm: the packaging is processed, free the device.
        packaging = self.env["product.packaging"].sudo().browse(packaging_id)
        if packaging.measuring_device_id:
            packaging._measuring_device_release()
        return super().set_packaging_dimension(
            picking_id, selected_line_id, packaging_id, cancel=cancel, **kwargs
        )


class ShopfloorReceptionValidator(Component):
    _inherit = "shopfloor.reception.validator"

    def _set_packaging_dimension__measuring_device_params(self):
        return {
            "picking_id": {"coerce": to_int, "required": True, "type": "integer"},
            "selected_line_id": {
                "coerce": to_int,
                "required": True,
                "type": "integer",
            },
            "packaging_id": {"coerce": to_int, "required": True, "type": "integer"},
        }

    def set_packaging_dimension__measuring_device_assign(self):
        return dict(
            self._set_packaging_dimension__measuring_device_params(),
            device_id={
                "coerce": to_int,
                "required": False,
                "nullable": True,
                "type": "integer",
            },
        )

    def set_packaging_dimension__measuring_device_refresh(self):
        return self._set_packaging_dimension__measuring_device_params()

    def set_packaging_dimension__measuring_device_release(self):
        return self._set_packaging_dimension__measuring_device_params()


class ShopfloorReceptionValidatorResponse(Component):
    _inherit = "shopfloor.reception.validator.response"

    @property
    def _schema_set_packaging_dimension(self):
        schema = super()._schema_set_packaging_dimension
        schema.update(
            {
                # The device assigned to the packaging, if any
                "assigned_measuring_device": {
                    "type": "dict",
                    "schema": self.schemas.measuring_device(),
                    "required": False,
                    "nullable": True,
                },
                # The devices to choose from, if several are available
                "measuring_device_choices": {
                    "type": "list",
                    "required": False,
                    "schema": {
                        "type": "dict",
                        "schema": dict(
                            self.schemas.measuring_device(),
                            in_use={"type": "boolean", "required": True},
                        ),
                    },
                },
            }
        )
        return schema

    def _set_packaging_dimension__measuring_device_next_states(self):
        # The measuring device actions always get back on the same screen
        return {"set_packaging_dimension"}

    def set_packaging_dimension__measuring_device_assign(self):
        return self._response_schema(
            next_states=self._set_packaging_dimension__measuring_device_next_states()
        )

    def set_packaging_dimension__measuring_device_refresh(self):
        return self._response_schema(
            next_states=self._set_packaging_dimension__measuring_device_next_states()
        )

    def set_packaging_dimension__measuring_device_release(self):
        return self._response_schema(
            next_states=self._set_packaging_dimension__measuring_device_next_states()
        )
