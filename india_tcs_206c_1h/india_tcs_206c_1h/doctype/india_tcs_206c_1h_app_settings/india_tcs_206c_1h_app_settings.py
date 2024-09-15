# -*- coding: utf-8 -*-
# Copyright (c) 2020, aerele and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint

class IndiaTCS206C_1HAppSettings(Document):
    pass

def set_tcs(doc, action):
    if action == "validate" and not doc.is_return:
        from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
        settings = frappe.get_single("India TCS 206C_1H App Settings")
        if not cint(settings.enable_tcs):
            return
        if cint(settings.check_tcs_for_customer):
            if not frappe.db.get_value("Customer", doc.customer, "tax_withholding_category"):
                to_remove = []
                for d in doc.get("taxes"):
                    if d.account_head == settings.tcs_account:
                        to_remove.append(d)
                [doc.remove(d) for d in to_remove]
                calculate_taxes_and_totals(doc)
                return

        if doc.docstatus != 0:
            return
        if len(doc.taxes) < 1:
            return
        if doc.is_return == 1:
            return
        if doc.taxes[-1].account_head == settings.tcs_account:
            return
        from erpnext.accounts.party import get_dashboard_info
        info = get_dashboard_info("Customer", doc.customer)
        customer_turnover = 0
        for company_info in info:
            if company_info['company'] == doc.company:
                customer_turnover = company_info['billing_this_year']
        if settings.tcs_trigger_amount >= customer_turnover + flt(doc.rounded_total):
            return
        tcs_row = frappe.new_doc('Sales Taxes and Charges')
        tcs_row.update({
            "charge_type": "On Previous Row Total",
            "row_id": str(len(doc.taxes)),
            "account_head": settings.tcs_account,
            "rate": settings.tcs_percentage,
            "description": settings.tcs_invoice_description,
            "parenttype": "Sales Invoice",
            "parentfield": "taxes",
            "parent": doc.name,
            "idx": len(doc.taxes) + 1
        })
        # Add a debug log to check if the charge_type is being set correctly
        frappe.log_error("TCS Row Update: {}".format(tcs_row.as_dict()))
        doc.taxes.append(tcs_row)
        calculate_taxes_and_totals(doc)