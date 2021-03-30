class User:
    def __init__(self, name, id):
        self.name = name
        self.id = id

    def get_user(self):
        return {"name": self.name, "id": self.id}

    def set_name_in_mongo(self):
        return {"$set": {"name": self.name}}