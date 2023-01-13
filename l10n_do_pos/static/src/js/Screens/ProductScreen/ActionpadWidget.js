odoo.define('l10n_cu_pos.ActionpadWidget', function (require) {
"use strict";
    const { useState } = owl;

    const ActionpadWidget = require('point_of_sale.ActionpadWidget');
    const Registries = require("point_of_sale.Registries");

    const ActionpadWidgetInherit = (ActionpadWidget) =>
        class extends ActionpadWidget {
            constructor() {
                super(...arguments);
                console.log(this);
            }
        };

    Registries.Component.extend(ActionpadWidget, ActionpadWidgetInherit);

    return ActionpadWidget;
});