# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0003_auto_20150204_0512'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='sync_uuid',
            field=models.CharField(max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='download',
            name='sync_uuid',
            field=models.CharField(max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='shape',
            name='sync_uuid',
            field=models.CharField(max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='standardmetadata',
            name='sync_uuid',
            field=models.CharField(max_length=32),
            preserve_default=True,
        ),
    ]
