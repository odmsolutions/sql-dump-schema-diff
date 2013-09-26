import sys
import re

# Reports all the differences between 2 DB schemas.
# Both schemas must only contain mysql DDL statements either generated by 'mysql_dump' or 'manage.py sql'.
# $Id$


class CompDB:
    """ open 2 files
        convert them into a canonical dictionary
        compare the dictionaries
        reports which table, fields, PK, unique or FK has changed
    """
    
    def __init__(self):
        self.format = 'sql'
        self.source_file_name = ''
        self.target_file_name = ''
        self.table_prefix = ''
        self.no_loss = ''
        self.no_foreign_key = True
    
    def set_no_foreign_key(self, no_foreign_key):
        self.no_foreign_key = no_foreign_key

    def set_no_removing(self, no_removing):
        self.no_loss = ''
        if no_removing:
            self.no_loss = '-- ' 
    
    def set_files(self, source_file_name, target_file_name):
        self.source_file_name = source_file_name
        self.target_file_name = target_file_name
    
    def set_table_prefix(self, table_prefix):
        self.table_prefix = table_prefix
        
    def set_format(self, data_format):
        if data_format not in ('default', 'sql'):
            data_format = 'sql'
        self.format = data_format
        
    def get_format(self):
        return self.format
    
    def compare(self):
        tables_source = self.analyse_file(False, self.table_prefix)
        tables_target = self.analyse_file(True, self.table_prefix)
        # 1. compare tables
        diff_count = 0
        for table_name in tables_source:
            if table_name in tables_target:
                diff_count += self.compare_tables(tables_source[table_name], tables_target[table_name])
            else:
                diff_count += 1
                if self.format == 'sql':
                    print '%sDROP TABLE `%s`;' % (self.no_loss, table_name)

        for table_name in tables_target:
            if table_name not in tables_source:
                diff_count += 1
                print 'CREATE TABLE `%s` (' % table_name
                self.compare_tables(None, tables_target[table_name], True)
                print ');'
                self.compare_tables(None, tables_target[table_name], False)

    def compare_tables(self, source, target, create_statement=False):
        """ source is None means that we need to create the table
            compare table works in two phases:
                * within a create statement (e.g. declare the fields and PK)
                * after the create statement (e.g. add a field or an index)

            create_statement = True always implies that source is None

            There are three cases to consider for each difference:
                1. source is not None
                source is None:
                    2. create_statement
                    3. not create_statement
            But only two of those cases should ever be treated
            (2 and 3 are mutually exclusive).
        """
        diff_count = 0
        after_create_statement = (source is None and not create_statement)
        outside_create_statement = (source is not None or after_create_statement)
        # 2.1. compare fields
        if source is not None:
            for field_name in source['fields']:
                if field_name in target['fields']:
                    if source['fields'][field_name] != target['fields'][field_name]:
                        diff_count += 1
                        print "ALTER TABLE `%s` MODIFY COLUMN %s;" % (source['name'], self.describe_field(target['fields'][field_name]))
                else:
                    diff_count += 1
                    print '%sALTER TABLE `%s` DROP COLUMN `%s`;' % (self.no_loss, source['name'], field_name)

        for field_name in target['fields']:
            if source is not None:
                if field_name not in source['fields']:
                    diff_count += 1
                    print 'ALTER TABLE `%s` ADD COLUMN %s;' % (source['name'], self.describe_field(target['fields'][field_name]))
            else:
                if create_statement:
                    print '\t%s,' % self.describe_field(target['fields'][field_name])
        
        # 2.2. compare fk
        if not self.no_foreign_key:
            if source is not None:
                for key_hash in source['fk']:
                    if key_hash not in target['fk']:
                        diff_count += 1
                        print '%sALTER TABLE `%s` DROP FOREIGN KEY `%s`;' % (self.no_loss, target['name'], target['fk'][key_hash]['name'])

            if outside_create_statement:
                for key_hash in target['fk']:
                    if source is None or key_hash not in source['fk']:
                        diff_count += 1
                        print 'ALTER TABLE `%s` ADD CONSTRAINT `%s` FOREIGN KEY (%s) REFERENCES `%s` (%s);' % (target['name'], target['fk'][key_hash]['name'], self.get_quoted_fields(target['fk'][key_hash]['k']), target['fk'][key_hash]['table'], self.get_quoted_fields(target['fk'][key_hash]['fk'])) 
                        
        # 2.3. compare uk
        for key_type in [{'name': 'UNIQUE INDEX', 'id': 'uk'}, {'name': 'FULLTEXT KEY', 'id': 'ft'}]:
            if source is not None:
                for key_name in source[key_type['id']]:
                    if key_name not in target[key_type['id']]:
                        diff_count += 1
                        print '-- %s (%s) ' % (key_type['name'], ', '.join(source[key_type['id']][key_name]['fields']))
                        index_name = source[key_type['id']][key_name]['name']
                        if index_name == '':
                            print '-- WARNING: UNKNONW INDEX NAME: ALTER TABLE %s DROP INDEX ???;' % source['name']
                        else:
                            print '%sALTER TABLE %s DROP INDEX `%s`;' % (self.no_loss, source['name'], source[key_type['id']][key_name]['name'])
            
            if outside_create_statement:
                for key_name in target[key_type['id']]:
                    if source is None or key_name not in source[key_type['id']]:
                        diff_count += 1
                        index_name = target[key_type['id']][key_name]['name']
                        if index_name == '': index_name = key_name
                        print 'ALTER TABLE %s ADD %s `%s` (%s);' % (target['name'], key_type['name'], index_name, ', '.join(target[key_type['id']][key_name]['fields']))
                        
        # 2.4. compare pk
        if source is not None:
            if source['pk'] != target['pk']: 
                diff_count += 1
                #print '-- PRIMARY KEY: %s \n\t%s \n\t=> \n\t%s' % (source['name'], ', '.join(source['pk']), ', '.join(target['pk']))
                print 'ALTER TABLE %s DROP PRIMARY KEY;' % source['name']
                print 'ALTER TABLE %s ADD PRIMARY KEY (%s);' % (source['name'], ', '.join(target['pk']))
        else:
            if create_statement:
                if len(target['pk']):
                    diff_count += 1
                    print '\tPRIMARY KEY (%s)' % self.get_quoted_fields(target['pk'])
        
        return diff_count
        
    def describe_field(self, field):
        ret = '`%s` %s' % (field['name'], field['type'])
        if field['inc']: ret += ' AUTO_INCREMENT'
        if field['nn']: ret += ' NOT NULL'
        if field['default']:
            ret += ' DEFAULT '
            if field['default'] == 'NULL':
                ret += 'NULL'
            else:
                ret += '`%s`' % field['default']
        return ret

    def describe_foreign_key(self, key):
        return '(%s) -> %s.(%s)' % (', '.join(key['k']), key['table'], ', '.join(key['fk']))
    
    def get_quoted_fields(self, fields):
        ret = ''
        for field in fields:
            if len(ret) > 0: ret = ret + ', '
            ret = ret + u'`%s`' % field
        return ret
            
    def analyse_file(self, target=False, table_prefix='plays_'):
        file_name = self.source_file_name
        if (target): file_name = self.target_file_name
        # read the file
        f = None
        try:
            f = open(file_name, 'r')
        except IOError:
            print 'Error reading %s' % file_name
            exit()
            
        tables = {}
        current_table = None
        
        line_number = 0
        for line in f:
            line_number += 1
            detected = False
            if re.match('--', line):
                continue
            if re.match('/\*.*\*/', line):
                continue
            if (current_table is None):
                # statements to ignore
                if re.match('(?i)\s*DROP TABLE', line):
                    detected = True
                # statements to ignore
                if re.match('(?i)\s*SET @|\w', line):
                    detected = True
                match = re.match('(?i)CREATE TABLE `([^`]*)`', line)
                if (match):
                    detected = True
                    current_table = {'name' : match.group(1), 'fields': {}, 'pk': [], 'fk': {}, 'uk': {}, 'ft': {}}
                # ALTER TABLE `plays_text_sample` ADD CONSTRAINT text_id_refs_id_4aaf935 FOREIGN KEY (`text_id`) REFERENCES `plays_text` (`id`);
                foreign_key = re.match('(?i)\s*ALTER TABLE\s+`([^`]+)`\s+ADD CONSTRAINT\s+(.+)\s+FOREIGN KEY\s+\(([^)]+)\)\s+REFERENCES\s+`([^`]+)`\s+\(([^)]+)\)', line)
                if (foreign_key):
                    detected = True
                    # split the fields
                    key_fields = re.split(',', foreign_key.group(3))
                    source_fields = []
                    for field in key_fields:
                        source_fields.append(field.strip(' ').strip('`'))
                    key_fields = re.split(',', foreign_key.group(5))
                    target_fields = []
                    for field in key_fields:
                        target_fields.append(field.strip(' ').strip('`'))

                    fk_table = self.clean_field_name(foreign_key.group(4))
                    fkid = ''.join(source_fields) + '->' + fk_table + '.' + ''.join(target_fields)
                    tables[foreign_key.group(1)]['fk'][fkid] = {'table': fk_table, 'k': source_fields, 'fk': target_fields, 'name': self.clean_field_name(foreign_key.group(2))}
                    #['fk'][foreign_key.group(2)] = {'table': foreign_key.group(4), 'k': source_fields, 'fk': target_fields}
                    
            else:
                # statements to ignore
                if re.match('\s*KEY `', line):
                    detected = True
                # remove , at the end
                line = re.sub(',$', '', line)
                # FIELD
                match = re.match('\s*`(.*)`\s+([^\s]*)\s+(.*)$', line)
                if (match):
                    detected = True
                    field = {'name': match.group(1), 'type': match.group(2), 'nn': False, 'default': False, 'inc': False}
                    
                    # equivalent data types
                    if field['type'] == 'integer': field['type'] = 'int(11)'
                    if field['type'] == 'smallint(6)': field['type'] = 'smallint'
                    if field['type'] == 'tinyint(1)': field['type'] = 'bool'
                    test_null = True

                    if (re.search('(?i)PRIMARY KEY', match.group(3))):
                        current_table['pk'].append(match.group(1))
                    if (re.search('(?i)NOT NULL', match.group(3))):
                        field['nn'] = True
                        test_null = False
                    if (re.search('(?i)auto_increment', match.group(3))):
                        field['inc'] = True
                    default_value = re.search("(?i)DEFAULT\s+(?:(\w+)|'([^']*)')", match.group(3))
                    if (default_value):
                        field['default'] = default_value.group(1) or default_value.group(2)
                        if field['default'] == 'NULL': test_null = False
                    # NULL on its own means 'DEFAULT NULL'
                    #if test_null and re.match('(?i)NULL', match.group(3)):
                    #    field['default'] = 'NULL'
                    if test_null:
                        field['default'] = 'NULL'
                    # todo: other properties to capture???
                    current_table['fields'][field['name']] = field
                # PRIMARY KEY (`id`),
                primary_key = re.match('(?i)\s*PRIMARY KEY\s+\(([^)]+)\)', line)
                if (primary_key):
                    detected = True
                    # split the fields
                    pk_fields = re.split(',', primary_key.group(1))
                    for field in pk_fields:
                        current_table['pk'].append(field.strip(' ').strip('`'))

                # UNIQUE (`location`, `text_id`) # anonymous
                unique_key = re.match('(?i)\s*UNIQUE\s+\(([^)]+)\)', line)
                if (unique_key):
                    detected = True
                    # split the fields
                    uk_fields = re.split(',', unique_key.group(1))
                    fields = []
                    for field in uk_fields:
                        fields.append(field.strip(' ').strip('`'))
                    #current_table['uk'][unique_key.group(1)] = fields
                    current_table['uk'][''.join(fields)] = {'name': '', 'fields': fields}
                
                # UNIQUE KEY `location` (`location`,`text_id`),
                unique_key = re.match('(?i)\s*(?:UNIQUE|FULLTEXT) KEY\s+`([^`]+)`\s+\(([^)]+)\)', line)
                if (unique_key):
                    detected = True
                    # split the fields
                    uk_fields = re.split(',', unique_key.group(2))
                    fields = []
                    for field in uk_fields:
                        fields.append(field.strip(' ').strip('`'))
                    key_type = 'uk'
                    if re.search('(?i)FULLTEXT KEY', line): key_type = 'ft'
                    #current_table[key_type][unique_key.group(1)] = fields
                    current_table[key_type][''.join(fields)] = {'name': unique_key.group(1), 'fields': fields}
                
                # CONSTRAINT `text_id_refs_id_4aaf935` FOREIGN KEY (`text_id`) REFERENCES `plays_text` (`id`)
                # TODO: structure the fields
                foreign_key = re.match('(?i)\s*CONSTRAINT\s+`([^`]+)`\s+FOREIGN KEY\s+\(([^)]+)\)\s+REFERENCES\s+`([^`]+)`\s+\(([^)]+)\)', line)
                if (foreign_key):
                    detected = True
                    # split the fields
                    key_fields = re.split(',', foreign_key.group(2))
                    source_fields = []
                    for field in key_fields:
                        source_fields.append(self.clean_field_name(field))
                    key_fields = re.split(',', foreign_key.group(4))
                    target_fields = []
                    for field in key_fields:
                        target_fields.append(self.clean_field_name(field))

                    #current_table['fk'][foreign_key.group(1)] = {'table': foreign_key.group(3), 'k': source_fields, 'fk': target_fields}
                    fk_table = self.clean_field_name(foreign_key.group(3))
                    fkid = ''.join(source_fields) + '->' + fk_table + '.' + ''.join(target_fields)
                    current_table['fk'][fkid] = {'table': fk_table, 'k': source_fields, 'fk': target_fields, 'name': self.clean_field_name(foreign_key.group(1))}
                
                # TODO: KEY `plays_text_sample_text_id` (`text_id`),
                
                # end of table
                match = re.match('\)', line)
                if (match):
                    detected = True
                    tables[current_table['name']] = current_table
                    current_table = None
            line = line.strip("\n ")
            if (not detected and len(line) > 1):
                print "WARNING: (%s:%d) not recognised: %s" % (file_name, line_number, line)
                
        f.close()
        # analyse the file
        
        # filter the result
        self.filter_table_dic(tables, table_prefix)
        
        return tables
    
    def clean_field_name(self, field_name):
        return field_name.strip(' ').strip('`')
    
    def filter_table_dic(self, tables={}, table_prefix=''):
        if tables is None or table_prefix == '': return
        for table_name in tables.keys():
            if (not re.match(table_prefix, table_name)): del tables[table_name]


def usage(stay=False):
        print "Usage: %s [OPTION]... [OLD_SCHEMA.sql NEW_SCHEMA.sql]" % sys.argv[0]
        print """Prints all the differences between 2 DB schemas on the standard output.

Options:

  -p TABLE_PREFIX  compare only the tables which name starts with TABLE_PREFIX
  -a               For Django users: if you execute this command from your 
                   project folder, the script will report the differences 
                   between your current database and your django model.
                   You don't need to provide OLD_SCHEMA.sql and NEW_SCHEMA.sql 
                   arguments.
                   -a makes -p mandatory. The -p argument must match the name 
                   of an application installed in your Django project.
                   e.g. python compdb.py -a -p MY_APP_NAME
  -k               Enables detection of differences in the foreign keys.
                   This feature is disabled by default as the constraint names 
                   may be different between the two databases. 
  -h               show this help screen

---

OLD_SCHEMA.sql and NEW_SCHEMA.sql schemas must only contain mysql DDL 
statements either generated with 'mysql_dump -d' or django's 
'manage.py sql'.

WARNING: this script cannot detect changes in the name of an object (e.g. a 
table or a field). For instance, if you have changed the name of a table from 
A to B, the script will tell you to drop A and create B because it doesn't 
know they are related. If you follow those instructions you will loose your 
data. Please be aware of this limitation."""
        if not stay:
            sys.exit(2)

def run_command(command):
    import os
    ret = os.system(command)
    return ret

def parseCmdLine():
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ahp:nkK", ["auto", "help", "prefix=", "no-removing", "foreign-key", "no-foreign-key"])           
    except getopt.GetoptError: usage()
    
    comp = CompDB()
         
    auto = False
    for opt, arg in opts:
        if opt in ("-h", "--help"): usage()
        elif opt in ('-p', "--prefix"):
            comp.set_table_prefix(arg)            
        elif opt in ("-a", "--auto"):
            auto = True
        elif opt in ("-n", "--no-removing"):
            comp.set_no_removing(True)
        elif opt in ("-K", "--no-foreign-key"):
            comp.set_no_foreign_key(True)
        elif opt in ("-k", "--foreign-key"):
            comp.set_no_foreign_key(False)
    
    if len(args) == 2 and not auto:
        comp.set_files(args[0], args[1])
    elif len(args) == 0 and auto and comp.table_prefix != '':
        try:
            import settings
        except ImportError, e:
            print e
            print "ERROR: settings.py not found in the current directory\n"
            usage();

        # mysqldump of the db schema
        host = settings.DATABASE_HOST
        if host != '':
            host = '-h %s' % host
        command = 'mysqldump -u %s --single-transaction --password="%s" -d %s %s > cmpdb.sql' % (settings.DATABASE_USER, settings.DATABASE_PASSWORD, host, settings.DATABASE_NAME);
        run_command(command)
        command = 'python manage.py sql %s > cmpdj.sql' % comp.table_prefix
        run_command(command)
        
        # django dump of the db schema
        comp.set_files('cmpdb.sql', 'cmpdj.sql')
    else: usage()
    
    comp.compare()

parseCmdLine()
