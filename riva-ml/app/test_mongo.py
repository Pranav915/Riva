import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import certifi

load_dotenv()

async def test_connection():
    uri = os.getenv("MONGO_URI")
    print(f"Connecting to: {uri}")
    client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where())
    try:
        # The ping command is cheap and does not require auth.
        await client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print("Connection failed:")
        print(e)
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
