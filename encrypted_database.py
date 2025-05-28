import json
import os
from datetime import datetime
from cryptography.fernet import Fernet  # type: ignore
from cryptography.hazmat.primitives import hashes  # type: ignore
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # type: ignore
import base64
import hashlib

class EncryptedDatabase:
    def __init__(self, db_file="encrypted_chat.db", password="default-db-password"):
        self.db_file = db_file
        self.password = password
        self.key = self._generate_key(password)
        self.fernet = Fernet(self.key)
        self.data = self._load_data()
        
        # Initialize empty structure if new database
        if not self.data:
            self.data = {
                'users': {},
                'public_messages': [],
                'groups': {},
                'user_sessions': {},
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            self.save()
    
    def _generate_key(self, password):
        """Generate encryption key from password"""
        # Use a fixed salt for consistency (in production, use random salt per user)
        salt = b'encrypted_chat_app_salt_2024'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _load_data(self):
        """Load and decrypt data from file"""
        if not os.path.exists(self.db_file):
            return None
        
        try:
            with open(self.db_file, 'rb') as file:
                encrypted_data = file.read()
                
            if not encrypted_data:
                return None
                
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        
        except Exception as e:
            print(f"Error loading database: {e}")
            return None
    
    def save(self):
        """Encrypt and save data to file"""
        try:
            # Update metadata
            self.data['metadata']['last_updated'] = datetime.now().isoformat()
            
            # Convert data to JSON and encrypt
            json_data = json.dumps(self.data, indent=2, default=str)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Write to file
            with open(self.db_file, 'wb') as file:
                file.write(encrypted_data)
            
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    # User Management
    def add_user(self, user_id, username, public_key="", metadata=None):
        """Add a new user to the database"""
        user_data = {
            'user_id': user_id,
            'username': username,
            'public_key': public_key,
            'created_at': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat(),
            'message_count': 0,
            'groups_joined': [],
            'metadata': metadata or {}
        }
        
        self.data['users'][user_id] = user_data
        self.save()
        return user_data
    
    def update_user_activity(self, user_id):
        """Update user's last activity time"""
        if user_id in self.data['users']:
            self.data['users'][user_id]['last_active'] = datetime.now().isoformat()
            self.save()
    
    def get_user(self, user_id):
        """Get user data by ID"""
        return self.data['users'].get(user_id)
    
    def get_all_users(self):
        """Get all users"""
        return self.data['users']
    
    # Message Management
    def add_public_message(self, message_data):
        """Add a message to public chat"""
        # Encrypt message content
        encrypted_message = self._encrypt_message_content(message_data)
        encrypted_message['room'] = 'public'
        encrypted_message['stored_at'] = datetime.now().isoformat()
        
        self.data['public_messages'].append(encrypted_message)
        
        # Keep only last 1000 messages
        if len(self.data['public_messages']) > 1000:
            self.data['public_messages'] = self.data['public_messages'][-1000:]
        
        # Update user message count
        if 'user_id' in message_data and message_data['user_id'] in self.data['users']:
            self.data['users'][message_data['user_id']]['message_count'] += 1
        
        self.save()
        return encrypted_message
    
    def get_public_messages(self, limit=50):
        """Get recent public messages"""
        messages = self.data['public_messages'][-limit:]
        return [self._decrypt_message_content(msg) for msg in messages]
    
    def add_group_message(self, group_name, message_data):
        """Add a message to a group"""
        if group_name not in self.data['groups']:
            return None
        
        # Encrypt message content
        encrypted_message = self._encrypt_message_content(message_data)
        encrypted_message['room'] = group_name
        encrypted_message['stored_at'] = datetime.now().isoformat()
        
        if 'messages' not in self.data['groups'][group_name]:
            self.data['groups'][group_name]['messages'] = []
        
        self.data['groups'][group_name]['messages'].append(encrypted_message)
        
        # Keep only last 1000 messages per group
        if len(self.data['groups'][group_name]['messages']) > 1000:
            self.data['groups'][group_name]['messages'] = self.data['groups'][group_name]['messages'][-1000:]
        
        # Update user message count
        if 'user_id' in message_data and message_data['user_id'] in self.data['users']:
            self.data['users'][message_data['user_id']]['message_count'] += 1
        
        self.save()
        return encrypted_message
    
    def get_group_messages(self, group_name, limit=50):
        """Get recent group messages"""
        if group_name not in self.data['groups']:
            return []
        
        messages = self.data['groups'][group_name].get('messages', [])[-limit:]
        return [self._decrypt_message_content(msg) for msg in messages]
    
    def _encrypt_message_content(self, message_data):
        """Encrypt sensitive message content"""
        encrypted_data = message_data.copy()
        
        # Encrypt the actual message content
        if 'message' in encrypted_data:
            encrypted_data['encrypted_message'] = self.fernet.encrypt(
                encrypted_data['message'].encode()
            ).decode()
            # Keep original for backward compatibility, but in production remove this
            
        if 'encrypted_content' in encrypted_data and encrypted_data['encrypted_content']:
            encrypted_data['double_encrypted_content'] = self.fernet.encrypt(
                encrypted_data['encrypted_content'].encode()
            ).decode()
        
        return encrypted_data
    
    def _decrypt_message_content(self, encrypted_data):
        """Decrypt message content"""
        decrypted_data = encrypted_data.copy()
        
        # Decrypt the message content
        if 'encrypted_message' in encrypted_data:
            try:
                decrypted_data['message'] = self.fernet.decrypt(
                    encrypted_data['encrypted_message'].encode()
                ).decode()
            except Exception as e:
                print(f"Error decrypting message: {e}")
        
        if 'double_encrypted_content' in encrypted_data:
            try:
                decrypted_data['encrypted_content'] = self.fernet.decrypt(
                    encrypted_data['double_encrypted_content'].encode()
                ).decode()
            except Exception as e:
                print(f"Error decrypting content: {e}")
        
        return decrypted_data
    
    # Group Management
    def create_group(self, group_name, creator_username, password="", metadata=None):
        """Create a new group"""
        if group_name in self.data['groups']:
            return None
        
        # Encrypt group password
        encrypted_password = ""
        if password:
            encrypted_password = self.fernet.encrypt(password.encode()).decode()
        
        group_data = {
            'id': hashlib.sha256(group_name.encode()).hexdigest()[:16],
            'name': group_name,
            'creator': creator_username,
            'encrypted_password': encrypted_password,
            'created_at': datetime.now().isoformat(),
            'members': [creator_username],
            'messages': [],
            'metadata': metadata or {}
        }
        
        self.data['groups'][group_name] = group_data
        self.save()
        return group_data
    
    def join_group(self, group_name, username, password=""):
        """Add user to group"""
        if group_name not in self.data['groups']:
            return False
        
        group = self.data['groups'][group_name]
        
        # Check password if required
        if group['encrypted_password']:
            try:
                stored_password = self.fernet.decrypt(
                    group['encrypted_password'].encode()
                ).decode()
                if password != stored_password:
                    return False
            except Exception as e:
                print(f"Error checking group password: {e}")
                return False
        
        # Add user to group if not already a member
        if username not in group['members']:
            group['members'].append(username)
            self.save()
        
        return True
    
    def leave_group(self, group_name, username):
        """Remove user from group"""
        if group_name not in self.data['groups']:
            return False
        
        group = self.data['groups'][group_name]
        if username in group['members']:
            group['members'].remove(username)
            self.save()
            return True
        
        return False
    
    def get_group(self, group_name):
        """Get group data"""
        group = self.data['groups'].get(group_name)
        if group:
            # Decrypt password for internal use (don't expose in API)
            decrypted_group = group.copy()
            if group['encrypted_password']:
                try:
                    decrypted_group['password'] = self.fernet.decrypt(
                        group['encrypted_password'].encode()
                    ).decode()
                except:
                    decrypted_group['password'] = ""
            else:
                decrypted_group['password'] = ""
            return decrypted_group
        return None
    
    def get_all_groups(self):
        """Get all groups (without passwords)"""
        groups = {}
        for name, group in self.data['groups'].items():
            groups[name] = {
                'id': group['id'],
                'name': group['name'],
                'creator': group['creator'],
                'created_at': group['created_at'],
                'member_count': len(group['members']),
                'message_count': len(group.get('messages', [])),
                'has_password': bool(group['encrypted_password'])
            }
        return groups
    
    # Session Management
    def add_session(self, session_id, user_data):
        """Add user session"""
        self.data['user_sessions'][session_id] = {
            **user_data,
            'session_start': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        self.save()
    
    def update_session(self, session_id, data):
        """Update session data"""
        if session_id in self.data['user_sessions']:
            self.data['user_sessions'][session_id].update(data)
            self.data['user_sessions'][session_id]['last_activity'] = datetime.now().isoformat()
            self.save()
    
    def remove_session(self, session_id):
        """Remove user session"""
        if session_id in self.data['user_sessions']:
            del self.data['user_sessions'][session_id]
            self.save()
    
    def get_session(self, session_id):
        """Get session data"""
        return self.data['user_sessions'].get(session_id)
    
    def get_all_sessions(self):
        """Get all active sessions"""
        return self.data['user_sessions']
    
    # Analytics and Statistics
    def get_stats(self):
        """Get database statistics"""
        total_messages = len(self.data['public_messages'])
        for group in self.data['groups'].values():
            total_messages += len(group.get('messages', []))
        
        return {
            'total_users': len(self.data['users']),
            'total_groups': len(self.data['groups']),
            'total_messages': total_messages,
            'public_messages': len(self.data['public_messages']),
            'active_sessions': len(self.data['user_sessions']),
            'database_size': os.path.getsize(self.db_file) if os.path.exists(self.db_file) else 0,
            'created_at': self.data['metadata']['created_at'],
            'last_updated': self.data['metadata']['last_updated']
        }
    
    # Backup and Recovery
    def create_backup(self, backup_file=None):
        """Create encrypted backup of database"""
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_encrypted_chat_{timestamp}.db"
        
        try:
            # Create backup with current data
            backup_data = self.data.copy()
            backup_data['metadata']['backup_created'] = datetime.now().isoformat()
            backup_data['metadata']['original_file'] = self.db_file
            
            json_data = json.dumps(backup_data, indent=2, default=str)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            with open(backup_file, 'wb') as file:
                file.write(encrypted_data)
            
            return backup_file
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None
    
    def restore_from_backup(self, backup_file):
        """Restore database from backup"""
        try:
            with open(backup_file, 'rb') as file:
                encrypted_data = file.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            backup_data = json.loads(decrypted_data.decode())
            
            # Restore data
            self.data = backup_data
            self.data['metadata']['restored_at'] = datetime.now().isoformat()
            self.data['metadata']['restored_from'] = backup_file
            
            self.save()
            return True
            
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False
    
    # Cleanup and Maintenance
    def cleanup_old_sessions(self, hours=24):
        """Remove sessions older than specified hours"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        sessions_to_remove = []
        
        for session_id, session_data in self.data['user_sessions'].items():
            try:
                last_activity = datetime.fromisoformat(session_data['last_activity'])
                if last_activity < cutoff_time:
                    sessions_to_remove.append(session_id)
            except Exception as e:
                print(f"Error parsing session time: {e}")
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.data['user_sessions'][session_id]
        
        if sessions_to_remove:
            self.save()
        
        return len(sessions_to_remove)
    
    def get_database_info(self):
        """Get detailed database information"""
        return {
            'file_path': os.path.abspath(self.db_file),
            'file_exists': os.path.exists(self.db_file),
            'file_size_bytes': os.path.getsize(self.db_file) if os.path.exists(self.db_file) else 0,
            'encryption_key_length': len(self.key),
            'data_structure': {
                'users': len(self.data.get('users', {})),
                'public_messages': len(self.data.get('public_messages', [])),
                'groups': len(self.data.get('groups', {})),
                'sessions': len(self.data.get('user_sessions', {}))
            },
            'metadata': self.data.get('metadata', {})
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db = EncryptedDatabase("test_chat.db", "secure-password-123")
    
    # Test user operations
    user_id = "user123"
    db.add_user(user_id, "TestUser", "public-key-data")
    
    # Test message operations
    message_data = {
        'id': 'msg123',
        'user_id': user_id,
        'username': 'TestUser',
        'message': 'Hello, this is a test message!',
        'encrypted_content': 'encrypted-content-here',
        'timestamp': datetime.now().isoformat()
    }
    
    db.add_public_message(message_data)
    
    # Test group operations
    db.create_group("TestGroup", "TestUser", "group-password")
    db.join_group("TestGroup", "TestUser", "group-password")
    db.add_group_message("TestGroup", message_data)
    
    # Print statistics
    print("Database Statistics:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Create backup
    backup_file = db.create_backup()
    print(f"\nBackup created: {backup_file}")
    
    print("\nDatabase setup and testing completed!")