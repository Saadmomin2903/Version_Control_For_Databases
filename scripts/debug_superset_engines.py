from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.db_engine_specs import get_available_engine_specs
    engines = get_available_engine_specs()
    for spec, drivers in engines.items():
        if "trino" in spec.__name__.lower() or "trino" in str(drivers).lower():
            print(f"Spec: {spec.__name__}, Engine: {spec.engine}, Drivers: {drivers}")
