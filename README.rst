Warehouse
=========

:Info: A Django app to collect data from third party APIs into a reportable set of tables
:Authors: Steven Challis <steve@stevechallis.com>
:Requires: Django >= 1.7 (see requirements.pip)


.. image:: https://github.com/schallis/warehouse/raw/via_api/screenshot.png


Graphs
------
Graph drawing is done with React.js and D3.js as SVG

CSV Reports
-----------

Reports are generated directly from Postgres. Since it's storing metadata as
JSON, arbitrary fields can be configured in the report. It's also super fast :)


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

TODO
----

Dashboard
~~~~~~~~~

Add or remove columns in interface

* Asset Usage report, Size by site (linked to CSV report)
* User report, # by site (options to sort by last login, exclude disabled, exclude hogarth, test)
* Number of users, by site
* Expired assets (listing, with metadata)
* Size by user (top users)
* Size by shapetag
* Size by mime
* Average transcodes per asset (per site)
* Version histogram
* Ingests over time, per site (per day, month, year)
* Ingests over time (by group)
  Ingest report (filter ingest date)
* Size over time, per site
* Size over time (cumulative), per site
* history of an asset
* Who it is shared with
* Biggest assets per site

Smarter syncing
~~~~~~~~~~~~~~~
Currently, the entire index is searched each time, we may be able to utilise
callback notifications to only update items which have changed. Note that we
need to figure out when new shapes and version are added to an item which makes
this trickier.

API to pull data to frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
