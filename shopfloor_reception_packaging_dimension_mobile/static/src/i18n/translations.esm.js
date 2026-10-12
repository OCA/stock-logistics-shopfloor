/**
 * Copyright 2026 Camptocamp SA (http://www.camptocamp.com)
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {translation_registry} from "/shopfloor_mobile_base/static/src/services/translation_registry.esm.js";

const i18n_path = "/shopfloor_reception_packaging_dimension_mobile/static/src/i18n";
translation_registry.load("en-US", `${i18n_path}/en.json`, true);
translation_registry.load("fr-FR", `${i18n_path}/fr.json`, true);
translation_registry.load("de-DE", `${i18n_path}/de.json`, true);
