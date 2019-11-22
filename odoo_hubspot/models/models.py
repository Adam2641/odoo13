# -*- coding: utf-8 -*-
import logging
import re
from openerp.exceptions import ValidationError
from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
import requests
import json
_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)


class CustomUser(models.Model):
    _inherit = 'res.users'

    key = fields.Char('Key')

    @api.model
    def auto_import_contacts(self):
        self.import_contacts()

    def import_contacts(self):
        if not self.env.user.key:
            raise ValidationError('Please! Enter Hubspot key...')
        else:
            try:
                response = requests.get(
                    'https://api.hubapi.com/contacts/v1/lists/all/contacts/all?hapikey=' + self.env.user.key,
                    headers={
                        'Accept': 'application/json',
                        'connection': 'keep-Alive'
                    })
                contacts = json.loads(response.content.decode('utf-8'))['contacts']
                for contact in contacts:
                    response = requests.get(
                        'https://api.hubapi.com/contacts/v1/contact/vid/' + str(
                            contact['vid']) + '/profile?hapikey=' + self.env.user.key,
                        headers={
                            'Accept': 'application/json',
                            'connection': 'keep-Alive'
                        })
                    profile = json.loads(response.content.decode('utf-8'))['properties']

                    first_name = profile['firstname']['value'] if 'firstname' in profile else ""
                    last_name = profile['lastname']['value'] if 'lastname' in profile else ""

                    name = first_name + ' ' + last_name
                    odoo_partner = self.env['res.partner'].search([('hubspot_id', '=', str(contact['vid']))])
                    odoo_company = None
                    if 'company' in profile.keys():
                        odoo_company = self.env['res.partner'].search([('name', '=', profile['company']['value'])])
                        if odoo_company:
                            odoo_company = odoo_company[0]

                    if not odoo_partner:
                        odoo_partner = self.env['res.partner'].create({
                            'name': name,
                            'email': profile['email']['value'] if 'email' in profile.keys() else '',
                            'website': profile['website']['value'] if 'website' in profile.keys() else '',
                            'function': profile['jobtitle']['value'] if 'jobtitle' in profile.keys() else '',
                            'city': profile['city']['value'] if 'city' in profile.keys() else '',
                            'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                            'parent_id': odoo_company.id if odoo_company else None,
                            'hubspot_id': str(contact['vid']),
                            'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                        })
                    else:
                        odoo_partner.write({
                            'name': name,
                            'email': profile['email']['value'] if 'email' in profile.keys() else '',
                            'website': profile['website']['value'] if 'website' in profile.keys() else '',
                            'function': profile['jobtitle']['value'] if 'jobtitle' in profile.keys() else '',
                            'city': profile['city']['value'] if 'city' in profile.keys() else '',
                            'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                            'parent_id': odoo_company.id if odoo_company else None,
                            'hubspot_id': str(contact['vid']),
                            'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                        })
                    if 'lifecyclestage' in profile.keys() and (profile['lifecyclestage']['value'] in ['lead', 'opportunity']
                                                               or 'qualified' in profile['lifecyclestage']['value']) and odoo_partner:
                        self.import_leads(profile, odoo_partner, contact)

                    self.env.cr.commit()

            except Exception as e:
                raise ValidationError(_(str(e)))

    def import_leads(self, profile, odoo_partner, contact):
        try:
            if 'vid' in contact:
                stage = None
                if 'hs_lead_status' in profile.keys():
                    stage = self.env['crm.stage'].search([('name', 'ilike', profile['hs_lead_status']['value'])])
                odoo_lead = self.env['crm.lead'].search([('hubspot_id', '=', str(contact['vid']))])
                if not odoo_lead:
                    self.env['crm.lead'].create({
                        'name': odoo_partner.name,
                        'partner_id': odoo_partner.id,
                        'hubspot_id': str(contact['vid']),
                        'email_from': odoo_partner.email if odoo_partner.email else '',
                        'city': odoo_partner.city if odoo_partner.city else '',
                        'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                        'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                        'website': profile['website']['value'] if 'website' in profile.keys() else '',
                        'function': profile['jobtitle']['value'] if 'jobtitle' in profile.keys() else '',
                        'type': profile['lifecyclestage']['value'] if not stage else 'opportunity',
                        'stage_id': stage.id if stage else ""
                    })
                else:
                    odoo_lead.write({
                                    'type': profile['lifecyclestage']['value'] if not stage else 'opportunity',
                                    'email_from': odoo_partner.email if odoo_partner.email else '',
                                    'city': odoo_partner.city if odoo_partner.city else '',
                                    'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                                    'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                                    'website': profile['website']['value'] if 'website' in profile.keys() else '',
                                    'function': profile['jobtitle']['value'] if 'jobtitle' in profile.keys() else '',
                                    'stage_id': stage.id if stage else ""
                                })
            else:
                stage = None
                if 'hs_lead_status' in profile.keys():
                    stage = self.env['crm.stage'].search([('name', 'ilike', profile['hs_lead_status']['value'])])
                odoo_lead = self.env['crm.lead'].search([('hubspot_id', 'ilike', str(contact['companyId']))])
                if not odoo_lead:
                    self.env['crm.lead'].create({
                        'name': odoo_partner.name,
                        'partner_id': odoo_partner.id,
                        'hubspot_id': str(contact['companyId']),
                        'email_from': odoo_partner.email if odoo_partner.email else '',
                        'city': odoo_partner.city if odoo_partner.city else '',
                        'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                        'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                        'website': profile['website']['value'] if 'website' in profile.keys() else '',
                        'function': profile['jobtitle']['value'] if 'jobtitle' in profile.keys() else '',
                        'type': profile['lifecyclestage']['value'] if not stage else 'opportunity',
                        'stage_id': stage.id if stage else ""
                    })
                else:
                    odoo_lead.write({
                        'type': profile['lifecyclestage']['value'] if not stage else 'opportunity',
                        'email_from': odoo_partner.email if odoo_partner.email else '',
                        'city': odoo_partner.city if odoo_partner.city else '',
                        'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                        'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                        'website': profile['website']['value'] if 'website' in profile.keys() else '',
                        'function': profile['jobtitle']['value'] if 'jobtitle' in profile.keys() else '',
                        'stage_id': stage.id if stage else ""
                    })

        except Exception as e:
            raise ValidationError(_(str(e)))

    @api.model
    def auto_export_contacts(self):
        self.export_contacts()

    def export_contacts(self):
        if not self.env.user.key:
            raise ValidationError('Please! Enter Hubspot key.')

        else:
            try:
                odoo_contacts = self.env['res.partner'].search([("is_company", "=", False)])
                for odoo_contact in odoo_contacts:
                    address = odoo_contact.street if odoo_contact.street else ""
                    address += odoo_contact.street2 if odoo_contact.street2 else ""
                    data = {
                        "properties": [
                            {
                                "property": "email",
                                "value": odoo_contact.email if odoo_contact.email else ""
                            },
                            {
                                "property": "firstname",
                                "value": odoo_contact.name
                            },
                            {
                                "property": "lastname",
                                "value": ""
                            },
                            {
                                "property": "website",
                                "value": odoo_contact.website if odoo_contact.website else ""
                            },
                            {
                                "property": "company",
                                "value": odoo_contact.parent_id.name if odoo_contact.parent_id else ""
                            },
                            {
                                "property": "phone",
                                "value": odoo_contact.phone if odoo_contact.phone else ""
                            },
                            {
                                "property": "address",
                                "value": address if address else ""
                            },
                            {
                                "property": "city",
                                "value": odoo_contact.city if odoo_contact.city else ""
                            },
                            {
                                "property": "state",
                                "value": odoo_contact.state_id.code if odoo_contact.state_id else ""
                            },
                            {
                                "property": "zip",
                                "value": odoo_contact.zip if odoo_contact.zip else ""
                            }
                        ]
                    }

                    if not odoo_contact.hubspot_id:
                        response = requests.post(
                            'https://api.hubapi.com/contacts/v1/contact/?hapikey='+ self.env.user.key, data=json.dumps(data),
                            headers={

                                'Accept': 'application/json',
                                'connection': 'keep-Alive',

                            })
                        contacts = json.loads(response.content.decode('utf-8'))
                        if response.status_code == 200:
                            odoo_contact.hubspot_id = contacts['vid']
                            self.env.cr.commit()
                    else:
                        response = requests.post(
                            'https://api.hubapi.com/contacts/v1/contact/vid/' + odoo_contact.hubspot_id + '/profile?hapikey='+ self.env.user.key,
                            data=json.dumps(data),
                            headers={
                                'Accept': 'application/json',
                                'connection': 'keep-Alive',
                            })
            except Exception as  e:
                raise ValueError(e)

    @api.model
    def auto_import_companies(self):
        self.import_companies()

    def import_companies(self):
        if not self.env.user.key:
            raise ValidationError('Please! Enter Hubspot key...')
        else:
            try:
                response = requests.get(
                    'https://api.hubapi.com/companies/v2/companies/paged?hapikey='+ self.env.user.key,
                    headers={
                        'Accept': 'application/json',
                        'connection': 'keep-Alive'
                    })
                companies = json.loads(response.content.decode('utf-8'))['companies']
                for company in companies:
                    response = requests.get(
                        'https://api.hubapi.com/companies/v2/companies/' + str(company['companyId']) + '?hapikey='+ self.env.user.key,
                        headers={
                            'Accept': 'application/json',
                            'connection': 'keep-Alive'
                        })
                    profile = json.loads(response.content.decode('utf-8'))['properties']
                    odoo_company = self.env['res.partner'].search([('hubspot_id', '=', str(company['companyId']))])
                    odoo_country = None
                    if 'country' in profile.keys():
                        odoo_country = self.env['res.country'].search([('name', '=', profile['country']['value'])])
                    if not odoo_company:
                        odoo_company = self.env['res.partner'].create({
                            'name': profile['name']['value'] if 'name' in profile.keys() else '',
                            'website': profile['website']['value'] if 'website' in profile.keys() else '',
                            'street': profile['address']['value'] if 'address' in profile.keys() else '',
                            'city': profile['city']['value'] if 'city' in profile.keys() else '',
                            'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                            'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                            'country_id': odoo_country.id if odoo_country else None,
                            'hubspot_id': str(company['companyId'])
                        })
                    else:
                        odoo_company.write({
                            'name': profile['name']['value'] if 'name' in profile.keys() else '',
                            'website': profile['website']['value'] if 'website' in profile.keys() else '',
                            'street': profile['address']['value'] if 'address' in profile.keys() else '',
                            'city': profile['city']['value'] if 'city' in profile.keys() else '',
                            'phone': profile['phone']['value'] if 'phone' in profile.keys() else '',
                            'zip': profile['zip']['value'] if 'zip' in profile.keys() else '',
                            'country_id': odoo_country.id if odoo_country else None,
                            'hubspot_id': str(company['companyId'])
                        })

                    if 'hs_lead_status' in profile.keys() and odoo_company:
                        self.import_leads(profile, odoo_company, company)

                    self.env.cr.commit()

            except Exception as e:
                raise ValidationError(_(str(e)))

    @api.model
    def auto_export_companies(self):
        self.export_companies()

    def export_companies(self):
        if not self.env.user.key:
            raise ValidationError('Please! Enter Hubspot key...')

        else:
            try:
                odoo_all = self.env['res.partner'].search([])
                odoo_companies = []
                for one_e in odoo_all:
                    if one_e.company_type == 'company':
                        odoo_companies.append(one_e)

                for odoo_company in odoo_companies:
                    address = odoo_company.street if odoo_company.street else ""
                    address += " " + odoo_company.street2 if odoo_company.street2 else ""
                    data = {
                        "properties": [
                            {
                                "name": "name",
                                "value": odoo_company.name
                            },
                            {
                                "name": "address",
                                "value": address
                            },
                            {
                                "name": "state",
                                "value": odoo_company.state_id.name if odoo_company.state_id else ' ',
                            },
                            {
                                "name": "city",
                                "value": odoo_company.city if odoo_company.city else '',
                            },
                            {
                                "name": "phone",
                                "value": odoo_company.phone if odoo_company.phone else '',
                            },
                            {
                                "name": "country",
                                "value": odoo_company.country_id.name if odoo_company.country_id else ''
                            },
                            {
                                "name": "zip",
                                "value": odoo_company.zip if odoo_company.zip else ''
                            }

                        ]
                    }
                    header = {
                        'Content-Type': 'application/json'
                    }
                    if not odoo_company.hubspot_id:
                        response = requests.post(
                            'https://api.hubapi.com/companies/v2/companies/?hapikey=' + self.env.user.key,
                            data=json.dumps(data),
                            headers=header)
                        if response.status_code == 200 and response.content:
                            contacts = json.loads(response.content.decode('utf-8'))
                            odoo_company.hubspot_id = contacts['companyId']
                            self.env.cr.commit()
                    else:
                        response = requests.put(
                            'https://api.hubapi.com/companies/v2/companies/' + odoo_company.hubspot_id + '?hapikey=' + self.env.user.key,
                            data=json.dumps(data),
                            headers=header)
            except Exception as e:
                raise ValidationError(e)


class CustomPartner(models.Model):
    _inherit = 'res.partner'

    hubspot_id = fields.Char('Hubspot Id')


class CustomLead(models.Model):
    _inherit = 'crm.lead'

    hubspot_id = fields.Char('Hubspot Id')
