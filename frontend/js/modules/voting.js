import { APP_ID, algodClient, indexerClient } from '../algorand.js';

export const VotingModule = {
    
    async fetchProposalData() {
        try {
            const appInfo = await indexerClient.lookupApplications(APP_ID).do();
            const globalState = appInfo.application.params['global-state'] || [];
            
            const state = {};
            globalState.forEach(item => {
                const key = b64ToString(item.key);
                state[key] = item.value.uint !== undefined ? item.value.uint : b64ToString(item.value.bytes);
            });

            return {
                title: state['proposal_title'] || "No active proposal",
                yesVotes: state['votes_yes'] || 0,
                noVotes: state['votes_no'] || 0,
                isActive: state['voting_active'] === 1
            };
        } catch (err) {
            console.error("Error fetching proposal data:", err);
            return null;
        }
    },

    async castVote(sender, choice, peraManager) {
        const params = await algodClient.getTransactionParams().do();
        const txnsToSign = [];

        
        const accountInfo = await algodClient.accountInformation(sender).do();
        const isOptedIn = accountInfo['apps-local-state'] && accountInfo['apps-local-state'].some(a => a.id === APP_ID);

        if (!isOptedIn) {
            const optInTxn = algosdk.makeApplicationOptInTxnFromObject({
                from: sender,
                suggestedParams: params,
                appIndex: APP_ID
            });
            txnsToSign.push(optInTxn);
        }

        
        const methodSelector = new Uint8Array([0x59, 0x11, 0x93, 0x01]); 
        
        
        const choiceBuffer = algosdk.encodeUint64(choice);

        const appCallTxn = algosdk.makeApplicationNoOpTxnFromObject({
            from: sender,
            suggestedParams: params,
            appIndex: APP_ID,
            appArgs: [
                new TextEncoder().encode("cast_vote"), 
                choiceBuffer                          
            ]
        });
        txnsToSign.push(appCallTxn);

        
        if (txnsToSign.length > 1) {
            algosdk.assignGroupID(txnsToSign);
        }

        
        const formattedTxns = txnsToSign.map(txn => ({
            txn: txn,
            signers: [sender],
        }));

        try {
            const signedTxns = await peraManager.signTransaction([formattedTxns]);
            const { txId } = await algodClient.sendRawTransaction(signedTxns).do();
            
            console.log(`Vote submitted! Transaction ID: ${txId}`);
            return await algosdk.waitForConfirmation(algodClient, txId, 4);
        } catch (err) {
            console.error("Voting transaction failed:", err);
            throw err;
        }
    }
};


function b64ToString(b64) {
    try {
        return atob(b64);
    } catch (e) {
        return "";
    }
}