from pymongo import MongoClient

from ioc.anotations.beans.component import Component
from ioc.mongo.mongo import Mongo

client = MongoClient('mongodb://files_reader:password@localhost:27017/file_link_hub')

db = client['file_link_hub']
collection = db['photos']


@Component()
class MongoImpl(Mongo):

    def find_by_id(self, id: str):
        return collection.find_one({"_id": id})
