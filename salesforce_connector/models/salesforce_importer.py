from odoo import models, fields, api
from simple_salesforce import Salesforce
from openerp import _
from openerp.osv import osv
from openerp.exceptions import Warning
from datetime import datetime
import os


class SalesForceImporter(models.Model):

    _name = 'salesforce.connector'

    sales_force = None
    field_name = fields.Char('salesforce_connector')
    history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Import Customers')
    sales_orders = fields.Boolean('Import Sale Orders')
    products = fields.Boolean('Export Products')
    opportunities = fields.Boolean('Import Opportinities')

    def sync_data(self):
        """
        this function checks the user selection for import data and  base  of this  selection it call import_data function

        :return:
        """
        if self.customers or self.products or self.sales_orders or self.opportunities:
            self.import_data()
        else:
            raise Warning(_("No Option Checked.",))

    def connect_to_salesforce(self):
        """
        test user connection

        """
        try:
            username = self.env.user.sf_username
            password = self.env.user.sf_password
            security_token = self.env.user.sf_security_token
            self.sales_force = Salesforce(username=username, password=password, security_token=security_token)
        except Exception as e:
            Warning(_(str(e)))

    def import_data(self):
        """.

        import customer data from SalesForce
        :return:
        """
        success_message = "Customers Added: {} and {} updated.\n" \
                          "SalesOrders Added: {} and {} updated.\n" \
                          "Opportunities Added: {} and {} updated.\n" \
                          "Products Exported: {} and {} updated.\n"
        data_dictionary = {}
        None if self.sales_force else self.connect_to_salesforce()
        if self.sales_force is None:
            raise Warning(_("Kindly provide SalesForce Credentails for odoo user",))
        if self.customers:
            data_dictionary["customers"] = self.add_customers_from_sales_force(accountid=0)[0]
        if self.sales_orders:
            data_dictionary["sales_orders"] = self.import_sale_orders()
        if self.products:
            data_dictionary["products"] = self.export_products()
        if self.opportunities:
            data_dictionary["opportinities"] = self.import_opportunities()
        no_of_customers = len(data_dictionary.get("customers", []))
        no_of_sales_orders = len(data_dictionary.get("sales_orders", []))
        no_of_products = len(data_dictionary.get('products', []))
        no_of_opportunities = len(data_dictionary.get('opportinities', []))
        if no_of_customers + no_of_products + no_of_sales_orders + no_of_opportunities:
            self.sync_history(no_of_customers, no_of_sales_orders, no_of_products, no_of_opportunities, data_dictionary)

        else:
            print("No new sync needed. Data already synced.")

    def sync_history(self, no_of_customers, no_of_sales_orders, no_of_products, no_of_opportunities, data_dictionary):
        """
        sync the history of customers , sale order product and opportunities

        :param no_of_customers:
        :param no_of_sales_orders:
        :param no_of_products:
        :param data:
        :return:
        """
        path = ''
        # path = self.create_html_file(data_dictionary)
        sync_history = self.env["sync.history"].search([])
        if sync_history:
            sync_history[0].write({"no_of_orders_sync": no_of_sales_orders,
                             "no_of_customers_sync": no_of_customers,
                             "no_of_products_sync": no_of_products,
                             "no_of_opportunities_sync": no_of_opportunities,
                             "sync_id": 1,
                             "document_link": path})
        else:
            sync_history.create({"no_of_orders_sync": no_of_sales_orders,
                                 "no_of_customers_sync": no_of_customers,
                                 "no_of_products_sync": no_of_products,
                                 "no_of_opportunities_sync": no_of_opportunities,
                                 "sync_id": 1,
                                 "document_link": path})
        self.env.cr.commit()

    def import_opportunities(self):
        """
        import all opportunities from SaleForce to Odoo

        :return:
        """
        try:
            return self.add_opportunities_from_sales_force()
        except Exception as e:
            raise Warning(_(str(e)))

    def import_customers(self):
        """
        import customers from SalesForce to odoo

        :return:
        """
        try:
            return self.add_customers_from_sales_force(accountid=0)
        except Exception as e:
            raise Warning(_(str(e)))

    def import_sale_orders(self):
        """
        Import order from SalesForce to Odoo

        :return:
        """
        try:
            orders = self.sales_force.query("select id , AccountId,"
                                            " EffectiveDate, orderNumber, status from Order")['records']
            order_model = self.env["sale.order"]
            order_name = [order.name for order in order_model.search([])]
            order_data = []
            for order in orders:
                if order["OrderNumber"] in order_name:
                    continue
                details = self.add_order_products_in_product_model(order["Id"])
                customer = self.add_customers_from_sales_force(order['AccountId'])[0]
                temp_order = {"name": order["OrderNumber"],
                              "partner_id": customer.id,
                              "state": "draft" if order['Status'] == 'Draft' else 'sale',
                              "invoice_status": "no",
                              # "confirmation_date": order['EffectiveDate'],
                              "date_order": order['EffectiveDate']}
                order_data.append(temp_order)
                sale_order = self.env["sale.order"].create(temp_order)
                self.env.cr.commit()
                for product_details, quantity in details:
                    self.env["sale.order.line"].create({'product_uom': 1,
                                                        'product_id': self.get_product_id(product_details.id),
                                                        'order_partner_id': customer.id, "order_id": sale_order.id,
                                                        "product_uom_qty": quantity})
            self.env.cr.commit()
            return order_data
        except Exception as e:
            raise Warning(_(str(e)))

    def add_order_products_in_product_model(self, order_id):
        """
        import order product from SalesForce to Odoo

        :param order_id:
        :return:
        """
        try:
            order_products_data = []
            order_lines = self.sales_force.query("select Pricebookentry.Product2Id , listprice, Quantity from "
                                                 "orderitem where orderid='%s'" % str(order_id))["records"]
            product_model = self.env["product.template"]
            old_products = product_model.search([])
            old_products_default_code = [product.default_code for product in old_products]
            for order_line in order_lines:
                product_id = order_line["PricebookEntry"]["Product2Id"]
                product_data = self.sales_force.query("select productCode, name, description from product2"
                                                      " where id='%s'" % str(product_id))["records"][0]
                if product_data["ProductCode"] in old_products_default_code:
                    order_products_data.append((product_model.search([('default_code', '=', product_data["ProductCode"])]),
                                                order_line["Quantity"]))
                    continue
                temp = dict()
                temp["name"] = product_data["Name"]
                temp["description"] = product_data["Description"]
                temp["default_code"] = product_data["ProductCode"]
                temp["list_price"] = order_line['ListPrice']
                temp["invoice_policy"] = "delivery"
                product_details = product_model.create(temp)
                order_products_data.append((product_details, order_line["Quantity"]))
            self.env.cr.commit()
            return order_products_data
        except Exception as e:
            raise Warning(_(str(e)))

    def get_product_id(self, tempalte_id):
        """
        this function searches the product and returns product id

        :param tempalte_id:
        :return product.id:
        """

        product = self.env["product.product"].search([("product_tmpl_id", '=', tempalte_id)])
        return product.id

    def add_customers_from_sales_force(self, accountid, customer_id=None):
        """
        This function import the customers from SalesForce into Odoo contact

        :param accountid:
        :param customer_id:
        :return customers_detail_list, customers_detail_list_2:
        """
        query = ''
        extend_query = ''
        contacts = []
        if accountid:
            query = "select id, name, shippingStreet,\
                    ShippingCity,Website, \
                    ShippingPostalCode, shippingCountry, \
                    fax, phone, Description from account %s"

            extend_query = "where id='%s'" % accountid
            contacts = self.sales_force.query(query % extend_query)["records"]

        else:
            query = "select id, name, shippingStreet, ShippingCity,Website,\
             ShippingPostalCode, shippingCountry, fax,\
              phone, Description from account %s"

            if customer_id:
                extend_query = "where id='%s'" % customer_id
            contacts = self.sales_force.query(query % extend_query)["records"]

        # customers_detail_list = []
        customers_detail_list_2 = []

        partner_model = self.env["res.partner"]
        for customer in contacts:
            old_customers = partner_model.search([('sf_customer_id','=',customer["Id"])])
            if old_customers:
                customers_detail_list_2.append(old_customers)
                continue
            customer_data = dict()
            customer_data["sf_customer_id"] = customer["Id"]
            customer_data["name"] = customer["Name"] if customer["Name"] else ""
            customer_data["street"] = customer["ShippingStreet"] if customer["ShippingStreet"] else ""
            customer_data["city"] = customer["ShippingCity"] if customer["ShippingCity"] else ""
            customer_data["phone"] = customer["Phone"] if customer["Phone"] else ""
            customer_data["comment"] = customer['Description'] if customer['Description'] else ""
            customer_data['website'] = customer["Website"] if customer["Website"] else ""
            # customer_data["fax"] = customer["Fax"] if customer["Fax"] else ""
            customer_data["zip"] = customer["ShippingPostalCode"] if customer["ShippingPostalCode"] else ""
            country = self.add_country(customer['ShippingCountry'])
            customer_data["country_id"] = country[0].id if country else ''
            customer_detail = partner_model.create(customer_data)
            self.env.cr.commit()
            if customer_detail:
                self.add_child_customers(customer['Id'], customer_detail.id)
                # customers_detail_list.append(customer_detail)
                customers_detail_list_2.append(customer_detail)
            else:
                print('can not create customer ')
        self.env.cr.commit()
        return  customers_detail_list_2

    def add_opportunities_from_sales_force(self, customer_id=None):
        """
        import opportunities  from salesforce to Odoo

        :param customer_id:
        :return:
        """
        self.connect_to_salesforce()
        query = "select id,name, AccountId, Amount, CloseDate, \
                Description, ExpectedRevenue, HasOpenActivity, IsDeleted, \
                IsWon,OwnerId, Probability, LastActivityDate, StageName from opportunity"

        extend_query = ''
        leads_detail_list = []
        leads_detail_list_2 = []
        leads = self.sales_force.query(query)["records"]
        lead_model = self.env["crm.lead"]
        old_leads = lead_model.search([])
        old_leads_sf_ids = [lead.sf_opportunity_id for lead in old_leads]
        for lead in leads:
            if lead["Id"] in old_leads_sf_ids:
                leads_detail_list_2.append(lead_model.search([("name", "=", lead["Name"])]))
                continue
            lead_data = dict()
            if lead["AccountId"]:
                self.add_customers_from_sales_force(lead["AccountId"])
            lead_data["sf_opportunity_id"] = lead["Id"]
            lead_data["name"] = lead["Name"] if lead["Name"] else ""
            lead_data["planned_revenue"] = lead["ExpectedRevenue"] if lead["ExpectedRevenue"] else ""
            dateclosed = datetime.strptime(lead["CloseDate"], "%Y-%m-%d")
            lead_data["date_deadline"] = dateclosed if dateclosed else datetime.now
            lead_data["description"] = lead["Description"] if lead["Description"] else ""
            lead_data["probability"] = lead['Probability'] if lead['Probability'] else ""
            lead_data["type"] = "opportunity"
            lead_data["active"] = True
            partner_ID = self.env["res.partner"].search([('sf_customer_id', '=',lead["AccountId"])])[0].id
            lead_data['partner_id'] = partner_ID
            odoo_stage = self.env['crm.stage'].search([("name", "=", lead['StageName'])])
            if not odoo_stage:
                odoo_stage = self.env["crm.stage"].create({
                    "name": lead['StageName']
                })
            lead_data['stage_id'] = odoo_stage.id
            lead_detail = lead_model.create(lead_data)
            self.env.cr.commit()

            leads_detail_list.append(lead_data)
            leads_detail_list_2.append(lead_data)
        self.env.cr.commit()
        return leads_detail_list_2


    def add_country(self, country_name):
        """
        Search Country and return it

        :param country_name:
        :return country :
        """
        country_model = self.env["res.country"]
        country = country_model.search([('name', 'ilike', country_name)], limit=1)
        return country

    def add_child_customers(self, customer_id, parent_id):
        """

        :param customer_id:
        :param parent_id:
        :return:
        """
        query = "select id, name, mailingaddress, mailingpostalcode,\
                    mailingcountry, phone,email,fax,mobilephone," \
                "description from Contact where accountid='%s'"
        customers_detail_list = []
        contacts = self.sales_force.query(query % customer_id)["records"]
        partner_model = self.env["res.partner"]
        for customer in contacts:
            old_customers = partner_model.search([('sf_customer_id', '=', customer["Id"])])
            if old_customers:
                continue
            customer_data = dict()
            customer_data["sf_customer_id"] = customer["Id"]
            customer_data["name"] = customer["Name"] if customer["Name"] else ""
            customer_data["street"] = customer["MailingAddress"]["street"] if customer["MailingAddress"] else ""
            customer_data["city"] = customer["MailingAddress"]["city"] if customer["MailingAddress"] else ""
            customer_data["phone"] = customer["Phone"] if customer["Phone"] else ""
            customer_data["email"] = customer["Email"] if customer["Email"] else ""
            # customer_data["fax"] = customer["Fax"] if customer["Fax"] else ""
            customer_data["mobile"] = customer["MobilePhone"] if customer["MobilePhone"] else ""
            customer_data["zip"] = customer["MailingPostalCode"] if customer["MailingPostalCode"] else ""
            customer_data["parent_id"] = parent_id
            customer_data["type"] = "invoice"
            customer_data["comment"] = customer['Description'] if customer['Description'] else ""
            country = self.add_country(customer['MailingCountry'])
            customer_data["country_id"] = country[0].id if country else ''
            customer_detail = partner_model.create(customer_data)
            customers_detail_list.append(customer_detail)
        self.env.cr.commit()

    def export_products(self):
        """
        export Products from odoo to salespoint

        """
        try:
            products = self.get_products_not_in_salesforce()
            product_data = [{"Name": product["name"],
                            "Description":product["description"] if product["description"] else '',
                             "ProductCode":product["default_code"] if product["default_code"] else '',
                             "IsActive": True} for product in products]
            product_price = [product["list_price"] for product in products]
            counter = 0
            while 1:
                buffer = product_data[counter*200: (counter+1)*200]
                price_buffer = product_price[counter*200: (counter+1)*200]
                price_book = []
                if len(buffer) == 0:
                    break
                product_buffer = self.sales_force.bulk.Product2.insert(buffer)
                for product, price in zip(product_buffer, price_buffer):
                    if product["success"]:
                        price_book.append({"Pricebook2Id": self.get_standard_pricebook_id(),
                                           "Product2Id": product["id"],
                                           "UnitPrice": price,
                                           "IsActive": True})
                self.sales_force.bulk.PriceBookEntry.insert(price_book)
                counter += 1
            return product_data
        except Exception as e:
            raise Warning(_(str(e)))

    def get_products_not_in_salesforce(self):
        """
        Filter the products which are not exported

        :return:
        """
        filtered_products = []
        products = self.env["product.product"].search([])
        old_products = self.sales_force.query("select name, productCode from product2")["records"]
        p_filter = {str(p["Name"]) + str(p["ProductCode"] if p["ProductCode"] else "") for p in old_products}
        for product in products:
            product_filter = str(product["name"]) + str(product["default_code"] if product["default_code"] else "")
            if product_filter not in p_filter:
                filtered_products.append(product)
        return filtered_products

    def get_standard_pricebook_id(self):
        """

        """
        pricebook_detail = self.sales_force.query("select id from pricebook2 where name = 'Standard Price Book'")["records"]
        if pricebook_detail:
            return pricebook_detail[0]["Id"]
        pricebook_detail = self.sales_force.PriceBook2.create({"name": 'Standard Price Book',
                                                               "IsActive": True})
        return pricebook_detail["id"]

    def create_html_file(self, data_dictionary):
        """
        :param data_dictionary:
        :return:
        """
        log_file = "log_file_%s.html" % str(datetime.now())
        message = """<html>
        <head></head>
        <body><p>Hello World1!</p><p>%s</p></body>
        </html>"""

        root_path = os.path.dirname(os.path.abspath(__file__)).replace('models', 'static')
        f = open(root_path + "/" + log_file, 'w')
        f.write(message % str(data_dictionary))
        f.close()
        path = "/salesforce_connector/static/" + log_file
        return path
        

class DropBoxLinks(models.Model):

    _name = 'sync.history'
    _order = 'sync_date desc'
    sync_id = fields.Many2one('salesforce.connector', string='Partner Reference', required=True, ondelete='cascade',
                              index=True, copy=False)
    sync_date = fields.Datetime('Sync Date', readonly=True, required=True, default=fields.Datetime.now)
    no_of_orders_sync = fields.Integer('Sync SalesOrders', readonly=True)
    no_of_products_sync = fields.Integer('Sync Products', readonly=True)
    no_of_customers_sync = fields.Integer('Sync Customers', readonly=True)
    no_of_opportunities_sync = fields.Integer('Sync Opportunities', readonly=True)
    document_link = fields.Char('Document Link', readonly=True)


    def sync_data(self):
        """

        :return:
        """
        client_action = {

            'type': 'ir.actions.act_url',
            'name': "log_file",
            'target': 'new',
            'url': self.document_link
        }
        return client_action



