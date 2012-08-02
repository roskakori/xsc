xsc
===

Xsc is a command line tool and Python module to convert column based files
such as CSV and PRN to hierarchical XML files.

It uses a template, which is a valid XML document itself with XML
processing instructions to express loops and conditionals. Loops iterate
over data files row by row. XML attributes and text can use inline Python
code to embed data.


Installation
------------

Xsc is available from `PyPI <http://pypi.python.org/>`_ and can be
installed using::

  $ pip install xsc

or::

  $ easy_install xsc

Provided you are connected to the internet, this also installs a few
required Python modules:

  * coverage, a developer module for testing
  * cutplace, a tool to describe and validate data
  * loxun, a module to write XML files
  * nose, a developer module for testing
  * xlrd, a module to read Excel files

All of them are available from PyPI and can be downloaded and installed
separately.


Tutorial
--------

This section provides a tutorial on using xsc to convert a simple CSV file
containing customer data in an XML file.

Here is the source CSV file::

  id,surname,firstname,dateOfBirth
  1,Doe,John,1957-03-08
  2,Miller,Jane,1946-10-04
  3,Webster,Mike,1974-12-23

As you can see, the first row contains headings for the various columns
where the other rows contain the actual data. This is the kind of CSV file
xsc can process out of the box. If your CSV file has header rows or columns
that cannot be mapped to a header, you either have to remove them manually
or provide a specific interface control document using `cutplace
<http://cutplace.sourceforge.net>`_.

Our goal is to get an XML document that looks like::

  <?xml version="1.0" encoding="utf-8"?>
  <customers>
    <person>
      <surname>Doe</surname>
      <firstname>John</firstname>
      <dateOfBirth>1957-03-08</dateOfBirth>
    </person>
    <person>
      <surname>Miller</surname>
      <firstname>Jane</firstname>
      <dateOfBirth>1946-10-04</dateOfBirth>
    </person>
    <person>
      <surname>Webster</surname>
      <firstname>Mike</firstname>
      <dateOfBirth>1974-12-23</dateOfBirth>
    </person>
  </customers>

First, we have to provide a xsc template. This is a XML document by itself
and can contain processing instructions to read data from data sources such
as CSV files and use inline Python expressions to generate text and XML
attribute values.

To get the desired output, we need the following template::

  <?xml version="1.0" encoding="utf-8"?>
  <customers>
    <?xsc for customers?>
    <person>
      <surname>${customers.surname}</surname>
      <firstname>${customers.surname}</firstname>
      <dateOfBirth>${customers.dateOfBirth}</dateOfBirth>
    </person>
    <?xsc end for?>
  </customers>

The line::

  <?xsc for customers?>

tells xsc to read the data source  ``customers`` row by row and generate
XML code until::

  <?xsc end for?>

for each row. As you probably guessed, we are going to point the data
source ``customers`` to our CSV file.

In the line::

  <surname>${customers.surname}</surname>

the ``${customers.surname}`` tells xsc to insert the value of the row
``surname`` in current row read from the data source ``customers``.  In the
CSV file provided, the first data row has a ``surname`` column with the
value ``Doe``. For the next row, the value is ``Miller`` and so on.

You could use the same syntax to assign a value to an attribute, for
example::

  <person surname="${customers.surname}" .../>

If needed, you can use namespaces just like you are used to:

  <some:person surname="${customers.surname}" .../>

Furthermore you are can use any Python function you like to compute
expressions within ``${...}``, for example::

  <person surname="${customers.surname.upper()}" id="n${'%05d' % (long(id)+100)" .../>

Note that all values read are unicode strings, so you have to convert them
to Python ``long``, ``Decimal``, ``datetime`` and so on if you want to use
them for computations on any of these types.

Now that we have a template (``customers.xsc``) and a data source
(``customers.csv``), we can finally generate our XML document. Open a new
console and change the current folder to the location where the CSV and XSC
file are stored. Then run::

  $ xsc customers.xsc customers:customers.csv

This tells xsc to generate an XML file based on the template
``customers.xsc`` with a data source named ``customers`` read from the file
``customers.csv``.

By default, the output is stored in the same folder as the template under
the same name but with the suffix ``.xml``. You can set a specific output
file using the command line option ``--output``, for example::

  $ xsc --output /tmp/northern_customers.xml customers.xsc customers:customers.csv

If ``customers.csv`` has a more complex format than "CSV with a header
row", you can describe it in a cutplace interface definition in, say,
``cid_customers.xls`` and add it to the data source description after an at
sign (@)::

  $ xsc customers.xsc customers:customers.csv@cid_customers.xls

To learn more about cutplace and how you can use it to describe a data
source, visit <http://cutplace.sourceforge.net>.

Computing text and attribute values
-----------------------------------

Apart from processing instructions, you can use inline python code to
compute text and attribute values in the document. Simply embed the code in
a ``${...}``, for example::

    <img src="${name.lower()}.png" alt="image of ${name}"/>
    This is ${name}.

Assuming the Python variable ``name`` holds the value ``"Bob"``, the
resulting XML code is::

    <img src="bob.png" alt="image of Bob"/>
    This is Bob.

To set variables to values retrieved from a data source, use ``<?xsc
for?>`` (see `Traversing data`_). To set variables to specific values using
possibly complex computations, use ``<?xsc python?>`` (see `Executing
Python code`_).


Importing Python modules
------------------------

To import a Python module for usage by XSC expressions, use::

  <?xsc import some_module?>

For example::

  <?xsc import errno?>

This imports the Python standard module `errno` so it can be used
by XSC expressions, for example::

  <text>access error code = ${errno.EACCES}</text>


Executing Python code
---------------------

To execute arbitrary Python code, use::

  <?xsc python
  code
  ?>

For example::

  <?xsc python
  import errno
  accessErrorCode
  accessErrorCode = errno.EACCES
  ?>

Variables, functions, imports and so are are added to the global scope and
can be used by later ``<?xsc python?>`` instructions and inline code.


Traversing data
---------------

To traverse all rows in a data source specified on the command line, use::

  <?xsc for dataSource?>
  ...
  <?xsc end for?>

For example, consider a data source defined using::

  $ xsc ... customer:customers.csv@icd_customers.xls

The name under which the data source is available for xsc is `customer`.
The data to process are stored in a CSV file in `customers.csv`. A
description of the file as a cutplace interface definition is stored in
`icd_customers.xls`.

To add a tag `<customer>` for each customer in `customers.csv`, use::

  <?xsc for customer?>
  <customer id="${customder.id}" surname="${customer.lastName}" .../>
  <?xsc end for?>


Conditionals and joins
----------------------

Sometimes XML fragments are optional and should show up in the output
only if certain conditions are met. For such a case, xsc provides a
processing instruction of the form::

  <?xsc if condition?>
  ...
  <?xsc end if?>

where *condition* is a boolean Python expression typically resolving to
``True`` or ``False``. Of course, the expression can resolve to any other
value too, in which case the usual Python rules apply whether it should be
interpreted as ``True`` or ``False``.

Apart from adding optional XML fragments, this can be used to simulate
functionality similar to data base joins. As an example consider an XML
document that contain a ``<customer>`` tag for each customer in a data
source and embed a ``<loan>`` in it for each loan the current customer
has::

  <customer id="${customer.id}" ...>
  <?xsc if customer.id == loan.customer_id?>
    <loan id="${loan.id}" ... />
  <?xsc end if?>
  </customer>


Comments
--------

As xsc templates are XML documents, they can contain XML comments, for example::

    <!-- Some comment. -->

Such comments are passed through and show up in the generated XML output.

For comments on implementation details, todo notes and similar things, there
is no point including them in the output especially if the output just acts
as input to be automatically processed by another application.

For these cases xsc supports a processing instruction for comments that do
not show up in the output::

    <?xsc # Some comment. ?>

It can also spawn multiple lines::

    <?xsc #
    Some comment
    spawning multiple
    lines.
    ?>


Security considerations
-----------------------

Xsc templates can contain arbitrary Python code that can do pretty much
everything any Python script can do. To achieve the concise and powerful
possibilities available to templates, on a technical level xsc liberally
uses ``eval()`` and ``exec()``. Both of them imply that you think about who
can modify xsc templates and how.

Just like any Python code, xsc templates can remove files, connect to
databases, send emails and so on. This enables anybody how can modify a xsc
template to remove or modify important system files or publish sensitive
data processed by xsc to unintended places.

Keep this in mind when deploying xsc based applications within your
organization.

The easiest solution to ensure that your xsc based application does not do
anything worse that other applications is to integrate xsc templates in the
same organizational processes as Python code. Typically this means that xsc
templates are modified only by developers, are put under the same version
control as Python source code and use the same test and release management
process as the rest of your Python application.


Support
-------

For support requests please use the issue tracker at
<https://github.com/roskakori/xsc/issues>.


Sourc code
----------

The source code is available from <https://github.com/roskakori/xsc>.


License
-------

Copyright (C) 2011-2012 Thomas Aglassinger

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
