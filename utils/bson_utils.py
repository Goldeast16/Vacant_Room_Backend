from bson import ObjectId

def str_objectid(oid) -> str:
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)