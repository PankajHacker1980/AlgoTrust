import { PeraWalletConnect } from "https://cdn.skypack.dev/@perawallet/connect";

export class PeraWalletManager {
    constructor() {
        this.peraWallet = new PeraWalletConnect();
        // Bind disconnect to ensure 'this' context is maintained
        this.handleDisconnect = this.disconnect.bind(this);
    }

    async reconnect() {
        try {
            const accounts = await this.peraWallet.reconnectSession();
            if (this.peraWallet.connector) {
                this.peraWallet.connector.on("disconnect", this.handleDisconnect);
            }
            
            if (accounts.length > 0) {
                localStorage.setItem("walletAddress", accounts[0]);
                return accounts[0];
            }
        } catch (error) {
            console.warn("Pera Wallet: No existing session found.");
        }
        return null;
    }

    async connect() {
        try {
            const accounts = await this.peraWallet.connect();
            if (this.peraWallet.connector) {
                this.peraWallet.connector.on("disconnect", this.handleDisconnect);
            }
            
            if (accounts.length > 0) {
                localStorage.setItem("walletAddress", accounts[0]);
                return accounts;
            }
        } catch (error) {
            if (error?.data?.type !== "CONNECT_MODAL_CLOSED") {
                console.error("Pera Wallet: Connection Error", error);
            }
            throw error;
        }
    }

    async disconnect() {
        try {
            await this.peraWallet.disconnect();
            localStorage.removeItem("walletAddress");
            localStorage.removeItem("walletBalance"); // Optional cleanup
            window.location.reload();
        } catch (error) {
            console.error("Pera Wallet: Disconnect failed", error);
        }
    }

    async signTransaction(txnGroups) {
        try {
            return await this.peraWallet.signTransaction(txnGroups);
        } catch (error) {
            console.error("Pera Wallet: Signing failed", error);
            throw error;
        }
    }
}