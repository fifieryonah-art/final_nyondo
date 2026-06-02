from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('nyondoapp', '0015_merge_20260602_0554'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='date_joined',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='profit_margin',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=10),
            preserve_default=False,
        ),
    ]
