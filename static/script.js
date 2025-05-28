class EncryptedChatApp {
    constructor() {
        this.socket = io();
        this.currentUser = null;
        this.currentRoom = 'public';
        this.isEncryptionEnabled = true;
        this.initializeElements();
        this.bindEvents();
        this.setupSocketListeners();
    }

    initializeElements() {
        // Screens
        this.loginScreen = document.getElementById('login-screen');
        this.chatScreen = document.getElementById('chat-screen');

        // Login elements
        this.usernameInput = document.getElementById('username');
        this.joinBtn = document.getElementById('join-btn');

        // Chat elements
        this.currentUsernameSpan = document.getElementById('current-username');
        this.currentRoomName = document.getElementById('current-room-name');
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.encryptToggle = document.getElementById('encrypt-toggle');
        this.groupList = document.getElementById('group-list');
        this.leaveGroupBtn = document.getElementById('leave-group-btn');

        // Group creation elements
        this.createGroupBtn = document.getElementById('create-group-btn');
        this.createGroupModal = document.getElementById('create-group-modal');
        this.groupNameInput = document.getElementById('group-name');
        this.groupPasswordInput = document.getElementById('group-password');
        this.createGroupConfirm = document.getElementById('create-group-confirm');
        this.createGroupCancel = document.getElementById('create-group-cancel');

        // Join group elements
        this.joinGroupModal = document.getElementById('join-group-modal');
        this.joinGroupName = document.getElementById('join-group-name');
        this.joinGroupPassword = document.getElementById('join-group-password');
        this.joinGroupConfirm = document.getElementById('join-group-confirm');
        this.joinGroupCancel = document.getElementById('join-group-cancel');
    }

    bindEvents() {
        // Login events
        this.joinBtn.addEventListener('click', () => this.joinChat());
        this.usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.joinChat();
        });

        // Message events
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Encryption toggle
        this.encryptToggle.addEventListener('change', (e) => {
            this.isEncryptionEnabled = e.target.checked;
        });

        // Group events
        this.createGroupBtn.addEventListener('click', () => this.showCreateGroupModal());
        this.createGroupConfirm.addEventListener('click', () => this.createGroup());
        this.createGroupCancel.addEventListener('click', () => this.hideCreateGroupModal());
        this.leaveGroupBtn.addEventListener('click', () => this.leaveCurrentGroup());

        // Join group events
        this.joinGroupConfirm.addEventListener('click', () => this.joinGroup());
        this.joinGroupCancel.addEventListener('click', () => this.hideJoinGroupModal());

        // Room selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.room-item')) {
                const roomItem = e.target.closest('.room-item');
                const room = roomItem.dataset.room;
                if (room) this.switchRoom(room);
            }
        });
    }

    setupSocketListeners() {
        this.socket.on('chat_joined', (data) => {
            this.currentUser = data.username;
            this.currentUsernameSpan.textContent = data.username;
            this.switchScreen('chat');
            
            // Load public messages
            data.public_messages.forEach(msg => this.displayMessage(msg));
            
            // Update group list
            this.updateGroupList(data.available_groups);
        });

        this.socket.on('new_message', (message) => {
            this.displayMessage(message);
        });

        this.socket.on('user_joined', (data) => {
            this.displaySystemMessage(`${data.username} joined ${data.room}`);
        });

        this.socket.on('user_left', (data) => {
            this.displaySystemMessage(`${data.username} left ${data.room}`);
        });

        this.socket.on('group_created', (data) => {
            this.hideCreateGroupModal();
            this.displaySystemMessage(`Group "${data.group_name}" created successfully`);
        });

        this.socket.on('group_joined', (data) => {
            this.hideJoinGroupModal();
            this.switchRoom(data.group_name);
            this.messagesContainer.innerHTML = '';
            data.messages.forEach(msg => this.displayMessage(msg));
        });

        this.socket.on('group_left', (data) => {
            if (this.currentRoom === data.group_name) {
                this.switchRoom('public');
            }
            this.displaySystemMessage(`Left group "${data.group_name}"`);
        });

        this.socket.on('group_list_updated', (data) => {
            this.updateGroupList(data.available_groups);
        });

        this.socket.on('error', (data) => {
            alert(data.message);
        });
    }

    switchScreen(screenName) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        
        if (screenName === 'login') {
            this.loginScreen.classList.add('active');
        } else if (screenName === 'chat') {
            this.chatScreen.classList.add('active');
        }
    }

    joinChat() {
        const username = this.usernameInput.value.trim();
        if (!username) {
            alert('Please enter a username');
            return;
        }

        this.socket.emit('join_chat', {
            username: username,
            public_key: 'demo-public-key'
        });
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        let encryptedContent = '';
        let displayMessage = message;

        if (this.isEncryptionEnabled) {
            encryptedContent = crypto.encryptMessage(message, this.currentRoom);
            displayMessage = message; // Keep original for display
        }

        if (this.currentRoom === 'public') {
            this.socket.emit('send_public_message', {
                message: displayMessage,
                encrypted_content: encryptedContent
            });
        } else {
            this.socket.emit('send_group_message', {
                group_name: this.currentRoom,
                message: displayMessage,
                encrypted_content: encryptedContent
            });
        }

        this.messageInput.value = '';
    }

    displayMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.username === this.currentUser ? 'own' : ''}`;

        let displayContent = message.message;
        let isEncrypted = false;

        // Try to decrypt if encrypted content exists
        if (message.encrypted_content && this.isEncryptionEnabled) {
            try {
                const decrypted = crypto.decryptMessage(message.encrypted_content, message.room);
                if (decrypted && decrypted !== message.encrypted_content) {
                    displayContent = decrypted;
                    isEncrypted = true;
                }
            } catch (error) {
                console.log('Decryption failed:', error);
            }
        }

        const timestamp = new Date(message.timestamp).toLocaleTimeString();
        
        messageElement.innerHTML = `
            <div class="message-bubble">
                ${message.username !== this.currentUser ? `<div class="message-header">${message.username}</div>` : ''}
                <div class="message-content">${this.escapeHtml(displayContent)}</div>
                <div class="message-footer">
                    <span>${timestamp}</span>
                    ${isEncrypted ? '<span class="encrypted-indicator">🔐</span>' : ''}
                </div>
            </div>
        `;

        this.messagesContainer.appendChild(messageElement);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    displaySystemMessage(text) {
        const messageElement = document.createElement('div');
        messageElement.className = 'system-message';
        messageElement.textContent = text;
        this.messagesContainer.appendChild(messageElement);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    switchRoom(room) {
        // Update active room indicator
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const roomItem = document.querySelector(`[data-room="${room}"]`);
        if (roomItem) {
            roomItem.classList.add('active');
        }

        this.currentRoom = room;
        this.currentRoomName.textContent = room === 'public' ? 'Public Chat' : room;
        
        // Show/hide leave group button
        if (room === 'public') {
            this.leaveGroupBtn.style.display = 'none';
        } else {
            this.leaveGroupBtn.style.display = 'inline-flex';
        }

        // Clear messages when switching rooms
        this.messagesContainer.innerHTML = '';
    }

    updateGroupList(groups) {
        this.groupList.innerHTML = '';
        
        groups.forEach(groupName => {
            const groupElement = document.createElement('div');
            groupElement.className = 'room-item';
            groupElement.dataset.room = groupName;
            groupElement.innerHTML = `
                <span>${groupName}</span>
                <button class="join-group-btn" data-group="${groupName}">Join</button>
            `;
            
            // Add click handler for join button
            const joinBtn = groupElement.querySelector('.join-group-btn');
            joinBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showJoinGroupModal(groupName);
            });
            
            this.groupList.appendChild(groupElement);
        });
    }

    showCreateGroupModal() {
        this.createGroupModal.classList.add('active');
        this.groupNameInput.focus();
    }

    hideCreateGroupModal() {
        this.createGroupModal.classList.remove('active');
        this.groupNameInput.value = '';
        this.groupPasswordInput.value = '';
    }

    createGroup() {
        const groupName = this.groupNameInput.value.trim();
        const password = this.groupPasswordInput.value.trim();

        if (!groupName) {
            alert('Please enter a group name');
            return;
        }

        this.socket.emit('create_group', {
            group_name: groupName,
            password: password
        });
    }

    showJoinGroupModal(groupName) {
        this.joinGroupName.textContent = `Join "${groupName}"`;
        this.joinGroupModal.classList.add('active');
        this.joinGroupModal.dataset.group = groupName;
        this.joinGroupPassword.focus();
    }

    hideJoinGroupModal() {
        this.joinGroupModal.classList.remove('active');
        this.joinGroupPassword.value = '';
        delete this.joinGroupModal.dataset.group;
    }

    joinGroup() {
        const groupName = this.joinGroupModal.dataset.group;
        const password = this.joinGroupPassword.value.trim();

        if (!groupName) return;

        this.socket.emit('join_group', {
            group_name: groupName,
            password: password
        });
    }

    leaveCurrentGroup() {
        if (this.currentRoom === 'public') return;

        this.socket.emit('leave_group', {
            group_name: this.currentRoom
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EncryptedChatApp();
});