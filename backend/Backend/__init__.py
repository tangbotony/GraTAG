import pymongo

from config import llm_log, config_manager

mongo_client = pymongo.MongoClient(host=config_manager.mongo_config['Host'], port=int(config_manager.mongo_config['Port']),
                                   username=config_manager.mongo_config['Username'], password=config_manager.mongo_config['Password'], authSource=config_manager.mongo_config['authDB'])
