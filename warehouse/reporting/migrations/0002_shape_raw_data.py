# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shape',
            name='raw_data',
            field=jsonfield.fields.JSONField(default=dict),
            preserve_default=True,
        ),
    ]
