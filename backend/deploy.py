import os
import logging
from dotenv import load_dotenv
from algokit_utils import (
    get_algod_client,
    get_indexer_client,
    get_account_from_mnemonic,
)
from beaker import client
from smart_contract.campuschain_app import app

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables (Create a .env file with DEPLOYER_MNEMONIC)
load_dotenv()

def deploy():
    # 1. Setup Network Clients (Testnet)
    # Using AlgoNode public endpoints - reliable for hackathons
    logger.info("Connecting to Algorand Testnet via AlgoNode...")
    algod_client = get_algod_client(
        config_route="https://testnet-api.algonode.cloud", 
        token=""
    )
    indexer_client = get_indexer_client(
        config_route="https://testnet-idx.algonode.cloud", 
        token=""
    )

    # 2. Setup Deployer Account
    # In .env, set DEPLOYER_MNEMONIC="word1 word2 ..."
    mnemonic = os.getenv("DEPLOYER_MNEMONIC")
    if not mnemonic:
        logger.error("DEPLOYER_MNEMONIC not found in .env")
        logger.info("Please generate a Testnet account and fund it via the Algorand Faucet.")
        return

    deployer = get_account_from_mnemonic(mnemonic)
    logger.info(f"Deployer Address: {deployer.address}")

    # 3. Initialize Application Client
    app_client = client.ApplicationClient(
        client=algod_client,
        app=app,
        signer=deployer,
    )

    # 4. Deploy the Smart Contract
    logger.info("Deploying AlgoTrust Smart Contract...")
    try:
        # This compiles the TEAL, creates the app, and stores the ID
        app_id, app_address, transaction_id = app_client.create()
        
        logger.info("--------------------------------------------------")
        logger.info("DEPLOYMENT SUCCESSFUL")
        logger.info("--------------------------------------------------")
        logger.info(f"App ID:      {app_id}")
        logger.info(f"App Address: {app_address}")
        logger.info(f"Tx ID:       {transaction_id}")
        logger.info("--------------------------------------------------")

        # 5. Initialize the App (Bootstrap for Demo)
        # We start a proposal and a campaign so the UI has data immediately.
        logger.info("Initializing demo data (Proposal & Campaign)...")
        
        # Start a Campus Proposal
        app_client.call(
            "start_proposal", 
            title="Should the Student Union fund a 24/7 AI Lab?"
        )
        
        # Start a Crowdfunding Campaign (Goal: 50 ALGO = 50,000,000 microAlgos)
        app_client.call(
            "start_campaign", 
            goal=50_000_000 
        )

        logger.info("Bootstrap complete. App is ready for interaction.")
        logger.info(f">>> ACTION REQUIRED: Update APP_ID in 'frontend/js/algorand.js' to: {app_id}")
        logger.info("--------------------------------------------------")

    except Exception as e:
        logger.error(f"Deployment failed: {e}")

if __name__ == "__main__":
    deploy()