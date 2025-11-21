from sqlalchemy.inspection import inspect

def sa_obj_to_dict(obj):
    mapper = inspect(obj)
    return {c.key: getattr(obj, c.key) for c in mapper.mapper.column_attrs}
