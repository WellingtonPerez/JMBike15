odoo.define('l10n_do_pos.ClientDetailsEdit', function (require) {
"use strict";
    const { useState } = owl;

    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');
    const Registries = require("point_of_sale.Registries");

    const ClientDetailsEditInherit = (ClientDetailsEdit) =>
        class extends ClientDetailsEdit {
            constructor() {
                super(...arguments);
                this.state = useState({
                    'l10n_do_dgii_tax_payer_type': this.props.partner.l10n_do_dgii_tax_payer_type,
                });
            }
            saveChanges() {
                this.changes.l10n_do_dgii_tax_payer_type = this.state.l10n_do_dgii_tax_payer_type;
                super.saveChanges();
            }
        };

    Registries.Component.extend(ClientDetailsEdit, ClientDetailsEditInherit);

    return ClientDetailsEdit;
});