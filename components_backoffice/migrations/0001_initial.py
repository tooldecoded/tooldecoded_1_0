from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ComponentAudit',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('component_id', models.UUIDField()),
                ('field', models.CharField(max_length=100)),
                ('old_value', models.TextField(blank=True, null=True)),
                ('new_value', models.TextField(blank=True, null=True)),
                ('source', models.CharField(default='inline', max_length=50)),
                ('created_at', models.DateTimeField()),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='componentaudit',
            index=models.Index(fields=['component_id', '-created_at'], name='comp_compid_created_idx'),
        ),
        migrations.AddIndex(
            model_name='componentaudit',
            index=models.Index(fields=['field'], name='comp_field_idx'),
        ),
    ]


