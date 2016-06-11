# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-11 09:38
from __future__ import unicode_literals

from django.db import migrations
import tagulous.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tunga_comments', '0003_auto_20160611_0928'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='tags',
            field=tagulous.models.fields.TagField(_set_tag_meta=True, blank=True, help_text='Enter a comma-separated tag string', initial='Makerere, University', null=True, to='tunga_comments._Tagulous_Comment_tags'),
        ),
    ]
