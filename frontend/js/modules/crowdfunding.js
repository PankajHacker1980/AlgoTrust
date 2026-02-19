import { APP_ID, algodClient, indexerClient } from '../algorand.js';

export const CrowdfundingModule = {
    
    async fetchCampaignInfo() {
        try {
            const appInfo = await indexerClient.lookupApplications(APP_ID).do();
            const globalState = appInfo.application.params['global-state'];
            
            
            const findVal = (key) => {
                const item = globalState.find(x => b64ToString(x.key) === key);
                return item ? item.value.uint : 0;
            };

            return {
                goal: findVal('campaign_goal') / 1_000_000,
                raised: findVal('total_raised') / 1_000_000,
                active: findVal('campaign_active') === 1
            };
        } catch (err) {
            console.error("Error fetching campaign:", err);
            return null;
        }
    },

    
    async contribute(sender, amountAlgo, peraManager) {
        const params = await algodClient.getTransactionParams().do();
        const amountMicroAlgos = Math.round(amountAlgo * 1_000_000);

        
        const appAddr = algosdk.getApplicationAddress(APP_ID);
        const payTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
            from: sender,
            to: appAddr,
            amount: amountMicroAlgos,
            suggestedParams: params
        });

        
        const appCallTxn = algosdk.makeApplicationNoOpTxnFromObject({
            from: sender,
            suggestedParams: params,
            appIndex: APP_ID,
            appArgs: [new TextEncoder().encode("contribute")],
        });

        
        const txnGroup = [payTxn, appCallTxn];
        algosdk.assignGroupID(txnGroup);

        const formattedGroup = txnGroup.map(txn => ({ txn, signers: [sender] }));

        try {
            const signedTxns = await peraManager.signTransaction([formattedGroup]);
            const { txId } = await algodClient.sendRawTransaction(signedTxns).do();
            return await algosdk.waitForConfirmation(algodClient, txId, 4);
        } catch (err) {
            console.error("Contribution failed:", err);
            throw err;
        }
    }
};

function b64ToString(b64) {
    return atob(b64);
}