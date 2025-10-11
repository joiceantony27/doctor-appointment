from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeslot',
            name='status',
            field=models.CharField(
                choices=[('available', 'Available'), ('booked', 'Booked')],
                default='available',
                max_length=20
            ),
        ),
    ] 