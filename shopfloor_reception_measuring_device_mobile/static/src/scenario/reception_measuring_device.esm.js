/**
 * Copyright 2026 Camptocamp SA (http://www.camptocamp.com)
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {process_registry} from "/shopfloor_mobile_base/static/src/services/process_registry.esm.js";

const reception_scenario = process_registry.get("reception");
const _get_states = reception_scenario.component.methods._get_states;
// Get the original template of the reception scenario
const template = reception_scenario.component.template;

// Everything happens on the `set_packaging_dimension` screen:
//   - the "Use measuring device" button, next to Done/Skip
//   - above the form, either the devices to choose from
//     or the device in use with its actions
const new_template = template
    .replace(
        "<!-- set-packaging-dimension-actions -->",
        `
        <v-row align="center" v-if="!state.data.assigned_measuring_device && !state.data.measuring_device_choices">
            <v-col class="text-center" cols="12">
                <btn-action @click="state.on_use_measuring_device">{{ $t('reception.measuring_device.use') }}</btn-action>
            </v-col>
        </v-row>
        <!-- set-packaging-dimension-actions -->
    `
    )
    .replace(
        "<!-- set-packaging-dimension-before-form -->",
        `
    <v-card v-if="state.data.measuring_device_choices && !state.data.assigned_measuring_device" class="mt-3 mb-2" outlined>
        <v-card-title>{{ $t('reception.measuring_device.choose') }}</v-card-title>
        <v-card-text>
            <div class="button-list button-vertical-list full">
                <v-row align="center" v-for="device in state.data.measuring_device_choices" :key="device.id">
                    <v-col class="text-center" cols="12">
                        <btn-action :disabled="device.in_use" @click="state.on_use_measuring_device(device)">
                            {{ device.name }}<span v-if="device.in_use"> {{ $t('reception.measuring_device.in_use') }}</span>
                        </btn-action>
                    </v-col>
                </v-row>
                <v-row align="center">
                    <v-col class="text-center" cols="12">
                        <btn-action action="cancel" @click="state.on_refresh_measures">{{ $t('btn.cancel.title') }}</btn-action>
                    </v-col>
                </v-row>
            </div>
        </v-card-text>
    </v-card>
    <v-card v-if="state.data.assigned_measuring_device" class="mt-3 mb-2" outlined>
        <v-card-title>{{ $t('reception.measuring_device.measuring_on', {name: state.data.assigned_measuring_device.name}) }}</v-card-title>
        <v-card-text>
            <p>{{ $t('reception.measuring_device.instructions') }}</p>
            <div class="button-list button-vertical-list full">
                <v-row align="center">
                    <v-col class="text-center" cols="12">
                        <btn-action @click="state.on_refresh_measures">{{ $t('reception.measuring_device.refresh') }}</btn-action>
                    </v-col>
                </v-row>
                <v-row align="center">
                    <v-col class="text-center" cols="12">
                        <btn-action action="complete" @click="state.on_confirm_measures">{{ $t('btn.confirm.title') }}</btn-action>
                    </v-col>
                </v-row>
                <v-row align="center">
                    <v-col class="text-center" cols="12">
                        <btn-action action="cancel" @click="state.on_release_measuring_device">{{ $t('btn.cancel.title') }}</btn-action>
                    </v-col>
                </v-row>
            </div>
        </v-card-text>
    </v-card>
    <!-- set-packaging-dimension-before-form -->
    `
    );

// Extend the reception scenario with:
//   - the new patched template
//   - the handlers of the measuring device actions
const ReceptionMeasuringDevice = process_registry.extend("reception", {
    template: new_template,
    "methods._get_states": function () {
        const states = _get_states.bind(this)();
        const state = states.set_packaging_dimension;
        const get_ids = () => {
            return {
                picking_id: this.state.data.picking.id,
                selected_line_id: this.state.data.selected_move_line.id,
                packaging_id: this.state.data.packaging.id,
            };
        };
        // The values are filled by the device: no manual input meanwhile
        const _is_form_locked = state.is_form_locked;
        state.is_form_locked = () => {
            return (
                Boolean(this.state.data.assigned_measuring_device) || _is_form_locked()
            );
        };
        state.on_use_measuring_device = (device) => {
            const values = get_ids();
            if (device) {
                values.device_id = device.id;
            }
            this.wait_call(
                this.odoo.call(
                    "set_packaging_dimension__measuring_device_assign",
                    values
                )
            );
        };
        // The device sends its measures to Odoo by itself: reload them
        state.on_refresh_measures = () => {
            this.wait_call(
                this.odoo.call(
                    "set_packaging_dimension__measuring_device_refresh",
                    get_ids()
                )
            );
        };
        // Values are already saved by the device: process the packaging as is,
        // the device is released by the backend
        state.on_confirm_measures = () => {
            this.wait_call(this.odoo.call("set_packaging_dimension", get_ids()));
        };
        state.on_release_measuring_device = () => {
            this.wait_call(
                this.odoo.call(
                    "set_packaging_dimension__measuring_device_release",
                    get_ids()
                )
            );
        };
        // Do not keep the device locked when leaving the screen
        const _on_back = state.on_back;
        state.on_back = () => {
            if (this.state.data.assigned_measuring_device) {
                this.odoo.call(
                    "set_packaging_dimension__measuring_device_release",
                    get_ids()
                );
            }
            if (_on_back) {
                _on_back();
            }
        };
        return states;
    },
});

process_registry.replace("reception", ReceptionMeasuringDevice);
