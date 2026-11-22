from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('fishbridge', '0002_pond_fish_species'),
    ]

    operations = [
        migrations.AddField(
            model_name='sector',
            name='is_closed',
            field=models.BooleanField(default=False, verbose_name='Временно закрыт'),
        ),
        migrations.AddField(
            model_name='sector',
            name='closure_reason',
            field=models.CharField(blank=True, max_length=255, verbose_name='Причина закрытия'),
        ),
        migrations.AddField(
            model_name='sector',
            name='closed_until',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Закрыт до'),
        ),
    ]
