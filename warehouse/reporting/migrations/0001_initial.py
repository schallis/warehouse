# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('deleted', models.DateTimeField(null=True, blank=True)),
                ('vs_id', models.CharField(unique=True, max_length=10)),
                ('filename', models.CharField(max_length=255, null=True, blank=True)),
                ('username', models.CharField(max_length=255)),
                ('created', models.DateTimeField()),
                ('raw_data', jsonfield.fields.JSONField(default=dict)),
                ('sites', models.ManyToManyField(to='sites.Site')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Download',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('when', models.DateTimeField(auto_now_add=True)),
                ('username', models.CharField(max_length=255)),
                ('item', models.ForeignKey(to='reporting.Asset')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Shape',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('deleted', models.DateTimeField(null=True, blank=True)),
                ('vs_id', models.CharField(unique=True, max_length=10)),
                ('shapetag', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(null=True, blank=True)),
                ('size', models.BigIntegerField()),
                ('version', models.IntegerField()),
                ('item', models.ForeignKey(to='reporting.Asset')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StandardMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('item', models.ForeignKey(to='reporting.Asset')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='download',
            name='shape',
            field=models.ForeignKey(to='reporting.Shape'),
            preserve_default=True,
        ),
    ]
