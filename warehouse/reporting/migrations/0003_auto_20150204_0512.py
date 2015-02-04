# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0002_shape_raw_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='sync_uuid',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='download',
            name='sync_uuid',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='shape',
            name='sync_uuid',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='standardmetadata',
            name='sync_uuid',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
    ]
