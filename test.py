from pymongo import MongoClient

client = MongoClient(
    "mongodb://Admin:Admin2005@3.235.107.84:27017/admin?authSource=admin"
)

print(client.admin.command("ping"))