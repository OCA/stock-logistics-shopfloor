/**
 * Copyright 2022 Camptocamp SA (http://www.camptocamp.com)
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
 */

import {demotools} from "/shopfloor_mobile_base/static/src/demo/demo.core.esm.js";

const receipt_pickings = [];
for (let i = 0; i < 10; i++) {
    receipt_pickings.push(
        demotools.makePicking(
            {},
            {lines_count: 5, line_random_pack: true, line_random_dest: true}
        )
    );
}

const data_for_start = {
    next_state: "select_document",
    data: {
        start: {
            pickings: receipt_pickings,
        },
    },
};
const data_for_select_document = {
    next_state: "select_document",
    data: {
        select_document: {
            pickings: receipt_pickings,
        },
    },
};

/* eslint-disable no-unused-vars */
const DEMO_RECEPTION = {
    start: data_for_start,
    list_stock_pickings: {
        next_state: "manual_selection",
        message: null,
        data: {
            manual_selection: {
                pickings: _.sampleSize(receipt_pickings, _.random(8)),
            },
        },
    },
    select_line: function (data) {
        const res = data_for_select_document;
        return res;
    },
    scan_document: function (data) {
        return {
            next_state: "select_move",
            data: {
                select_move: {
                    picking: receipt_pickings.find((p) => p.name === data.barcode),
                },
            },
        };
    },
    done_action: function (data) {
        return {
            next_state: "select_document",
            message: "Transfer done",
            data: {
                select_document: {
                    pickings: _.sampleSize(receipt_pickings, _.random(8)),
                },
            },
        };
    },
};

const menuitem_id = demotools.addAppMenu(
    {
        name: "Reception",
        scenario: "reception",
        picking_types: [{id: 27, name: "Random type"}],
    },
    "re_1"
);
demotools.add_case("reception", menuitem_id, DEMO_RECEPTION);
