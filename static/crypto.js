class SimpleCrypto {
    constructor() {
        this.keyPair = null;
        this.initialize();
    }

    async initialize() {
        // Generate key pair for encryption
        this.keyPair = await window.crypto.subtle.generateKey(
            {
                name: "RSA-OAEP",
                modulusLength: 2048,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash: "SHA-256",
            },
            true,
            ["encrypt", "decrypt"]
        );
    }

    // Simple XOR encryption for demo purposes (not secure for production)
    encrypt(text, key = 'default-key') {
        let result = '';
        for (let i = 0; i < text.length; i++) {
            result += String.fromCharCode(
                text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
            );
        }
        return btoa(result); // Base64 encode
    }

    decrypt(encryptedText, key = 'default-key') {
        try {
            const text = atob(encryptedText); // Base64 decode
            let result = '';
            for (let i = 0; i < text.length; i++) {
                result += String.fromCharCode(
                    text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
                );
            }
            return result;
        } catch (error) {
            return encryptedText; // Return original if decryption fails
        }
    }

    // Generate a simple hash for key derivation
    generateKey(seed) {
        let hash = 0;
        for (let i = 0; i < seed.length; i++) {
            const char = seed.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash).toString(16);
    }

    // Encrypt message with room-specific key
    encryptMessage(message, room) {
        const key = this.generateKey(room + 'encryption-seed');
        return this.encrypt(message, key);
    }

    // Decrypt message with room-specific key
    decryptMessage(encryptedMessage, room) {
        const key = this.generateKey(room + 'encryption-seed');
        return this.decrypt(encryptedMessage, key);
    }
}

// Initialize crypto instance
const crypto = new SimpleCrypto();