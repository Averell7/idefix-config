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

    def update_group(self, group_id, verified=None, name=None, domains=None, category_id=None):
        """Update the group with the given details"""

        cur = self.db.cursor()
        parameters = []
        query = 'UPDATE proxy_groups SET'
        if verified is not None:
            query += ' unverified=%s,'
            parameters.append(not verified)
        if name:
            query += ' name=%s,'
            parameters.append(name)
        if domains:
            query += ' domains=%s,'
            parameters.append(json.dumps(domains))
        if category_id:
            query += ' category_id=%s,'
            parameters.append(category_id)

        if ',' in query:
            query = query[:-1]

        query += ' WHERE id=%s LIMIT 1'
        parameters.append(group_id)

        cur.execute(query, parameters)
        cur.close()

    def update_category(self, category_id, name=None, parent_id=None):
        """Update the category with the given details. Use parent_id='' to unset"""
        cur = self.db.cursor()
        parameters = []
        query = 'UPDATE proxy_category SET'
        if name is not None:
            query += ' name=%s,'
            parameters.append(name)
        if parent_id is not None:
            if parent_id == '':
                query += ' parent_id=NULL,'
            else:
                query += ' parent_id=%s,'
                parameters.append(parent_id)
        if ',' in query:
            query = query[:-1]
        query += ' WHERE id=%s LIMIT 1'
        parameters.append(category_id)
        cur.execute(query, parameters)
        cur.close()

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
        cur = self.db.cursor()
        cur.execute("INSERT INTO proxy_groups (unverified, name, domains, category_id) VALUES(%s, %s, %s, %s)", (
            not verified,
            name,
            json.dumps(domains),
            category_id
        ))
        cur.close()

    def create_category(self, name, parent_id):
        """Create a new category and return its id"""
        cur = self.db.cursor()
        try:
            cur.execute("INSERT INTO proxy_category (name, parent_id) VALUES (%s, %s)", (
                name,
                int(parent_id) if parent_id is not None else None
            ))
        except mysql.connector.errors.IntegrityError as e:
            return False, 'Category already exists. Please use a different name'
        cur.close()
        return True, ''
