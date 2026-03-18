from django.db import migrations


def mark_existing_scenarios(apps, schema_editor):
    ScenarioComparison = apps.get_model("plans", "ScenarioComparison")
    ScenarioComparison.objects.update(is_system_generated=True)


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0002_scenariocomparison_is_system_generated"),
    ]

    operations = [
        migrations.RunPython(mark_existing_scenarios, migrations.RunPython.noop),
    ]
