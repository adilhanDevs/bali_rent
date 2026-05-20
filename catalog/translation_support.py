from functools import lru_cache

from django.db import connection
from django.db.utils import DatabaseError


@lru_cache(maxsize=1)
def vehicle_type_translation_table_available():
    try:
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
    except DatabaseError:
        return False
    return 'catalog_vehicletypetranslation' in tables
