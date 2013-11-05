"""Tests for the function that compares table definitions and output the alter table syntax"""
from collections import OrderedDict
from compdb import compare_tables


def test_that_middle_column_is_added_in_right_order():
    """Given table dictionaries for source and target that differ
    by the addition of one column to the target,
    in the middle of the definition,
    ensure that the ALTER table output has the order specified"""
    source_dict = {'name': 'test_table',
                   'fields': OrderedDict((
                       ('first_column',
                        {'name': 'first_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('second_column',
                        {'name': 'second_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('third_column',
                        {'name': 'third_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False})
                   )),
                   'pk': set(),
                   'fk': {},
                   'uk': {},
                   'ft': {}
    }
    target_dict = {'name': 'test_table',
                   'fields': OrderedDict((
                       ('first_column',
                        {'name': 'first_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('second_column',
                        {'name': 'second_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('new_column',
                        {'name': 'new_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('third_column',
                        {'name': 'third_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False})
                   )),
                   'pk': set(),
                   'fk': {},
                   'uk': {},
                   'ft': {}
    }

    expected_output = "ALTER TABLE `test_table` ADD COLUMN `new_column` int(11) NOT NULL AFTER `second_column`;"
    actual_output = compare_tables(source_dict, target_dict, '')
    assert expected_output in actual_output, "%s not found in:\n%s\n\n" %(expected_output, actual_output)


def test_that_first_column_is_added_in_right_order():
    """Given table dictionaries for source and target that differ
    by the addition of one column to the target,
    at the start of the definition,
    ensure that the ALTER table output has the order specified"""
    source_dict = {'name': 'test_table',
                   'fields': OrderedDict((
                       ('first_column',
                        {'name': 'first_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('second_column',
                        {'name': 'second_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('third_column',
                        {'name': 'third_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False})
                   )),
                   'pk': set(),
                   'fk': {},
                   'uk': {},
                   'ft': {}
    }
    target_dict = {'name': 'test_table',
                   'fields': OrderedDict((
                       ('new_column',
                        {'name': 'new_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('first_column',
                        {'name': 'first_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('second_column',
                        {'name': 'second_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False}),
                       ('third_column',
                        {'name': 'third_column', 'type': 'int(11)', 'nn': True,
                         'default': False, 'inc': False})
                   )),
                   'pk': set(),
                   'fk': {},
                   'uk': {},
                   'ft': {}
    }

    expected_output = "ALTER TABLE `test_table` ADD COLUMN `new_column` int(11) NOT NULL FIRST;"
    actual_output = compare_tables(source_dict, target_dict, '')
    assert expected_output in actual_output, "%s not found in:\n%s\n\n" %(expected_output, actual_output)


