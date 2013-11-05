"""Tests for the database dump analysis function.
Arguably one of the more complicated parts of the system."""
from compdb import analyse_file
from nose.tools import eq_

def test_it_should_store_column_order_in_field_dict():
    """Given an example table in mysql dump output format,
    the output data structure should represent the column
    order in the table fields"""

    sample_table_dump = """CREATE TABLE `test` (
        `first_column` int(11) NOT NULL PRIMARY KEY,
        `second_column` int(11) DEFAULT NULL,
        `third_column` varchar(20) DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1;
    """

    expect_field_order = ["first_column", "second_column", "third_column"]

    output = analyse_file(sample_table_dump.splitlines(False))

    for expect_field_name, actual_field_name in zip(expect_field_order, output['test']['fields'].keys()):
        eq_(expect_field_name, actual_field_name)
    #

