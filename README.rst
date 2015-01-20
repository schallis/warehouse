Warehouse
=========

:Info: A Django app to collect data from third party APIs into a reportable set of tables
:Authors: Steven Challis <steve@stevechallis.com>
:Requires: Django >= 1.7 (see requirements.pip)

Development
-----------

    mkvirtualenv warehouse
    workon warehouse
    pip install -r requirements
    ./manage.py syncdb
    ./manage.py migrate
    ./manage.py sync_report_data
    ./manage.py runserver 0.0.0.0:8000

Then fire up `127.0.0.1:8000/admin`


Usage
-----
The project primarily relies on the ``reporting`` app which is responsible for
gathering and cleaning data. The ``reporting`` app has a command which
syncs the entire 3rd party source to update the local tables.

The task can be also manually triggered from the webapp.

The data it collects can then be viewed and searched in the Django admin
interface exposed at ``/admin``.

Since the sync command repeatedly polls the 3rd party source, there is a
configurable delay which can reduce the load upon it::

   SYNC_CALL_DELAY  = 1  # seconds

CSV Reports
-----------
The ``reporting`` app also comes bundled with a selection of tools to generate
common reports. These are easy to generate from the shell::

    $ ./manage.py shell
    >>> from reporting.reports import IngestReport
    >>> report = IngestReport()
    >>> report.serialize()
    /var/folders/vf/zhts9frj5tlbykc_tqw1st4r0000gp/T/tmpbl1Vjt
    <closed file '<fdopen>', mode 'w+b' at 0x10f376810>


TODO
----
Smarter syncing
~~~~~~~~~~~~~~~
Currently, the entire index is searched each time, we may be able to utilise
callback notifications to only update items which have changed. Note that we
need to figure out when new shapes and version are added to an item which makes
this trickier.

Results backend
~~~~~~~~~~~~~~~
Add a results backend for Celery to track the results of the tasks.

