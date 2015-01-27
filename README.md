Dump MySQL Schema differences as executable SQL code.

This can be used to automate schema only synchronisation between sites, 
where there is not a culture of creating migrations to make changes. 
While the latter is probably a technically better solution (and highly recommended before using this), this offers an alternative. It is currently far from perfect, and will need work to be completely trusted.

The code has only been tested with Python 2.7.

At a regular basis, this script can be run to produce incremental migrations between a stored DB dump and a new one, perhaps as part of a release basis for a large infrastructure project.

It comes with absolutely no warranties and is used at your own risk. It has been used - but is not considered beautified or well maintained code. This fork was for bug fixing purposes!

Fork from original project at https://code.google.com/p/sql-dump-schema-diff/

Fork for bug fixes

