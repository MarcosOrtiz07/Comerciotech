from pymongo import MongoClient

client = MongoClient(
    "mongodb://Admin:Admin2005@32.198.32.165:27017/admin?authSource=admin"
)

print(client.admin.command("ping"))
