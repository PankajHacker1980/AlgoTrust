import { algodClient } from '../algorand.js';

export const SplitModule = {
    calculateSplits(totalAmount, participantsString) {
        const participants = participantsString.split('\n')
            .map(p => p.trim())
            .filter(p => p.length > 0);
        
        if (participants.length === 0) return [];

        const share = (totalAmount / participants.length).toFixed(6);
        return participants.map(address => ({
            address,
            share
        }));
    },

    
    async settleExpenses(sender, totalAmount, participants, peraManager) {
        const params = await algodClient.getTransactionParams().do();
        const shareMicroAlgos = Math.round((totalAmount / participants.length) * 1_000_000);

        const txns = participants.map(addr => {
            return algosdk.makePaymentTxnWithSuggestedParamsFromObject({
                from: sender,
                to: addr,
                amount: shareMicroAlgos,
                suggestedParams: params
            });
        });

        
        if (txns.length > 16) throw new Error("Too many participants for a single atomic group.");

        algosdk.assignGroupID(txns);
        const formatted = txns.map(txn => ({ txn, signers: [sender] }));

        try {
            const signed = await peraManager.signTransaction([formatted]);
            const { txId } = await algodClient.sendRawTransaction(signed).do();
            return await algosdk.waitForConfirmation(algodClient, txId, 4);
        } catch (err) {
            console.error("Settlement failed:", err);
            throw err;
        }
    }
};