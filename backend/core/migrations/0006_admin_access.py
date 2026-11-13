from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_recommendation_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [
                    ('assign_roles', 'Can assign roles and manage staff accounts'),
                    ('view_system_report', 'Can view the system report'),
                    ('view_data_catalogue', 'Can view the careers and skills catalogue'),
                ],
                'managed': False,
                'default_permissions': (),
            },
        ),
    ]
