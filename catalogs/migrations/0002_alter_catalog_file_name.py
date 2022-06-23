# Generated by Django 4.0.4 on 2022-06-07 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalog',
            name='file_name',
            field=models.FileField(help_text='Location of static catalog data file', unique=True),
        ),
    ]
