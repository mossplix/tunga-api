# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-06 12:39
from __future__ import unicode_literals

from django.db import migrations
import tagulous.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tunga_profiles', '0007_auto_20160606_1142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='skills',
            field=tagulous.models.fields.TagField(_set_tag_meta=True, blank=True, help_text='Enter a comma-separated tag string', initial='Kampala, Entebbe, Jinja, Nairobi, Mombosa, Dar es Salaam, Kigali, Amsterdam', to='tunga_profiles.Skill'),
        ),
    ]