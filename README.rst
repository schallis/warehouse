Warehouse
=========

:Info: A Django app to collect data from third party APIs into a reportable set of tables
:Authors: Steven Challis <steve@stevechallis.com>
:Requires: Django >= 1.7 (see requirements.pip)

Development
-----------

    mkvirtualenv warehouse
    workon warehouse
    source envs/local
    pip install -r requirements
    ./manage.py syncdb
    ./manage.py migrate
    ./manage.py sync_report_data
    ./manage.py runserver 0.0.0.0:8000

Then fire up `localhost:8000/admin`


Environment Variables
~~~~~~~~~~~~~~~~~~~~~

You'll need to set the following environment variables for this application to
run. It is suggested that you store these in a shell script under ``envs/local``::

    APPSETTING_BORK_TOKEN
    APPSETTING_BORK_USERNAME
    APPSETTING_DB_PASSWORD
    APPSETTING_DB_HOST
    APPSETTING_DB_USER


Usage
-----
The project primarily relies on the ``reporting`` app which is responsible for
gathering and cleaning data. The ``reporting`` app has a command which
syncs the entire 3rd party source to update the local tables.

The task can be also manually triggered from the webapp.

The data it collects can then be viewed and searched in the Django admin
interface exposed at ``/admin``.

NOTE: Data collection is done in parallel using multithreading (to maximise API
concurrency)

CSV Reports
-----------

NOTE: Since data collection happens iteratively, you should only report on data
from any one sync for highest accuracy. All reportable data is linked to the
sync it was found in so simply join and filter on that.

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

API to pull data to frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CSV Export
~~~~~~~~~~
* By site (or all)
* With metadata

Dashboard
~~~~~~~~~
* Size by site (linked to CSV report)
* Size by user (top users)
* Size by shapetag
* Size by mime
* Average transcodes per asset (per site)
* Version histogram
* Ingests over time, per site
* Ingests over time (by group)
* Size over time, per site
* Size over time (cumulative), per site
