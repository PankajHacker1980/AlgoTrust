



export const APP_ID = 123456789; 


const ALGOD_TOKEN = "";
const ALGOD_SERVER = "https://testnet-api.algonode.cloud";
const ALGOD_PORT = "";

const INDEXER_TOKEN = "";
const INDEXER_SERVER = "https://testnet-idx.algonode.cloud";
const INDEXER_PORT = "";


export const algodClient = new algosdk.Algodv2(ALGOD_TOKEN, ALGOD_SERVER, ALGOD_PORT);
export const indexerClient = new algosdk.Indexer(INDEXER_TOKEN, INDEXER_SERVER, INDEXER_PORT);


export function b64ToString(b64) {
    return atob(b64);
}


export function truncateAddress(addr) {
    if (!addr) return "";
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
}