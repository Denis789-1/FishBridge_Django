                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fishbridge', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pond',
            name='fish_species',
            field=models.ManyToManyField(blank=True, related_name='ponds', through='fishbridge.StockingBatch', to='fishbridge.fishspecies', verbose_name='Виды рыб'),
        ),
    ]
