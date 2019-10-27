"""
Connect to the remote database to do operations
"""
import json

import mysql.connector


class Database:
    def __init__(self, host, port, username, password, database):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.db = None

    def connect(self):
        """Connect to the db"""
        self.db = mysql.connector.connect(
            host=self.host,
            user=self.username,
            passwd=self.password,
            port=self.port,
            db=self.database,
            auth_plugin='mysql_native_password'
        )
        self.db.autocommit = True

    def disconnect(self):
        """Disconnect from the db"""
        self.db.close()
        self.db = None

    @property
    def connected(self):
        return self.db is not None

    def get_groups(self, verified=None, name=None, domains=None, category=None):
        """Return a list of groups"""
        rows = self.db.cursor()
        rows.execute("SELECT id, name, domains, unverified, category_id FROM proxy_groups")
        for id, name, domains, unverified, category_id in rows:

            # Convert domain list from json list to new-line separated string
            if domains:
                domains = '\n'.join([domain for domain in json.loads(domains)])
            else:
                domains = ''

            yield {
                'id': id,
                'name': name,
                'domains': domains,
                'unverified': unverified,
                'category_id': category_id
            }
        rows.close()

    def get_categories(self, category=None):
        """Return a list of categories"""
        rows = self.db.cursor()
        rows.execute("SELECT id, name, parent_id FROM proxy_category ORDER BY parent_id")
        for id, name, parent_id in rows:
            yield {
                'id': id,
                'name': name,
                'parent_id': parent_id,
            }
        rows.close()

    def update_group(self, group_id, verified, name, domains):
        """Update the group with the given details"""

        cur = self.db.cursor()
        cur.execute("UPDATE proxy_groups SET unverified=%s, name=%s, domains=%s WHERE id=%s LIMIT 1", (
            not verified,
            name,
            json.dumps(domains),
            group_id
        ))
        cur.close()

    def update_category(self, category, name, parent_id):
        """Update the category with the given details"""
        pass

    def delete_group(self, group_id):
        """Remove the group by its id"""
        cur = self.db.cursor()
        cur.execute("DELETE FROM proxy_groups WHERE id=%s LIMIT 1", (group_id,))
        cur.close()

    def delete_category(self, category_id):
        """Delete the category by its id"""
        pass

    def create_group(self, verified, name, domains, category_id):
        """Create a new group and return its id"""

    def create_category(self, name, parent_id):
        """Create a new category and return its id"""
