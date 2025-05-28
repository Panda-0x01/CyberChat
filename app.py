from flask import Flask, render_template, request  # type: ignore
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms  # type: ignore
import json
import uuid
from datetime import datetime
import base64
from encrypted_chat_app.encrypted_database import EncryptedDatabase

# In-memory user session storage for legacy code (should be removed if using only EncryptedDatabase)
user_sessions = {}
public_messages = []
group_rooms = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize encrypted database
db = EncryptedDatabase("chat_data.db", "your-super-secure-database-password-2024")

# Clean up old sessions on startup
db.cleanup_old_sessions(24)  # Remove sessions older than 24 hours

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/stats')
def admin_stats():
    """Admin endpoint to view database statistics"""
    stats = db.get_stats()
    db_info = db.get_database_info()
    return {
        'stats': stats,
        'database_info': db_info,
        'groups': db.get_all_groups()
    }

@socketio.on('connect')
def handle_connect():
    print(f'User connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'User disconnected: {request.sid}')
    # Remove user from all rooms and clean up
    session_data = db.get_session(request.sid)
    if session_data:
        username = session_data['username']
        # Leave all rooms
        for room in rooms(request.sid):
            if room != request.sid:  # Don't leave own room
                leave_room(room)
                emit('user_left', {'username': username}, room=room)
        db.remove_session(request.sid)

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data['username']
    user_id = str(uuid.uuid4())
    
    # Store user in database
    user_data = db.add_user(user_id, username, data.get('public_key', ''))
    
    # Store user session
    session_data = {
        'username': username,
        'user_id': user_id,
        'public_key': data.get('public_key', '')
    }
    db.add_session(request.sid, session_data)
    
    # Join public room by default
    join_room('public')
    
    # Get recent messages and groups
    public_messages = db.get_public_messages(50)
    available_groups = list(db.get_all_groups().keys())
    
    emit('chat_joined', {
        'user_id': user_id,
        'username': username,
        'public_messages': public_messages,
        'available_groups': available_groups
    })
    
    # Notify others in public room
    emit('user_joined', {
        'username': username,
        'room': 'public'
    }, room='public', include_self=False)

@socketio.on('send_public_message')
def handle_public_message(data):
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    message_data = {
        'id': str(uuid.uuid4()),
        'user_id': session_data['user_id'],
        'username': session_data['username'],
        'message': data['message'],
        'encrypted_content': data.get('encrypted_content', ''),
        'timestamp': datetime.now().isoformat(),
        'room': 'public'
    }
    
    # Store message in encrypted database
    stored_message = db.add_public_message(message_data)
    
    # Update user activity
    db.update_user_activity(session_data['user_id'])
    
    # Emit to all users in public room
    emit('new_message', message_data, room='public')

@socketio.on('create_group')
def handle_create_group(data):
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    group_name = data['group_name']
    password = data.get('password', '')
    
    # Check if group already exists
    if db.get_group(group_name):
        emit('error', {'message': 'Group already exists'})
        return
    
    # Create group in database
    group_data = db.create_group(group_name, session_data['username'], password)
    if not group_data:
        emit('error', {'message': 'Failed to create group'})
        return
    
    join_room(group_name)
    
    emit('group_created', {
        'group_name': group_name,
        'group_id': group_data['id']
    })
    
    # Notify all users about new group
    emit('group_list_updated', {
        'available_groups': list(db.get_all_groups().keys())
    }, broadcast=True)

@socketio.on('join_group')
def handle_join_group(data):
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    group_name = data['group_name']
    password = data.get('password', '')
    
    # Try to join group in database
    if not db.join_group(group_name, session_data['username'], password):
        emit('error', {'message': 'Failed to join group. Check password.'})
        return
    
    join_room(group_name)
    
    # Get group messages
    group_messages = db.get_group_messages(group_name, 50)
    group_data = db.get_group(group_name)
    
    emit('group_joined', {
        'group_name': group_name,
        'messages': group_messages,
        'members': group_data['members'] if group_data else []
    })
    
    # Notify others in the group
    emit('user_joined', {
        'username': session_data['username'],
        'room': group_name
    }, room=group_name, include_self=False)

@socketio.on('send_group_message')
def handle_group_message(data):
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    group_name = data['group_name']
    
    # Check if group exists
    if not db.get_group(group_name):
        emit('error', {'message': 'Group does not exist'})
        return
    
    message_data = {
        'id': str(uuid.uuid4()),
        'user_id': session_data['user_id'],
        'username': session_data['username'],
        'message': data['message'],
        'encrypted_content': data.get('encrypted_content', ''),
        'timestamp': datetime.now().isoformat(),
        'room': group_name
    }
    
    # Store message in encrypted database
    stored_message = db.add_group_message(group_name, message_data)
    
    # Update user activity
    db.update_user_activity(session_data['user_id'])
    
    # Emit to all users in the group
    emit('new_message', message_data, room=group_name)

@socketio.on('leave_group')
def handle_leave_group(data):
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    group_name = data['group_name']
    
    # Remove user from group in database
    if db.leave_group(group_name, session_data['username']):
        leave_room(group_name)
        
        emit('group_left', {'group_name': group_name})
        
        # Notify others in the group
        emit('user_left', {
            'username': session_data['username'],
            'room': group_name
        }, room=group_name)

@socketio.on('get_user_stats')
def handle_get_user_stats():
    """Get user statistics"""
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    user_data = db.get_user(session_data['user_id'])
    if user_data:
        emit('user_stats', {
            'message_count': user_data.get('message_count', 0),
            'groups_joined': len(user_data.get('groups_joined', [])),
            'created_at': user_data.get('created_at'),
            'last_active': user_data.get('last_active')
        })

@socketio.on('backup_database')
def handle_backup_database():
    """Create database backup (admin function)"""
    session_data = db.get_session(request.sid)
    if not session_data:
        return
    
    # Simple admin check (in production, implement proper admin authentication)
    if session_data['username'] == 'admin':
        backup_file = db.create_backup()
        if backup_file:
            emit('backup_created', {'backup_file': backup_file})
        else:
            emit('error', {'message': 'Failed to create backup'})

# Periodic cleanup task (run every hour)
import threading
import time

def periodic_cleanup():
    """Periodic cleanup of old sessions and maintenance"""
    while True:
        try:
            # Clean up old sessions every hour
            time.sleep(3600)  # 1 hour
            removed_sessions = db.cleanup_old_sessions(24)
            if removed_sessions > 0:
                print(f"Cleaned up {removed_sessions} old sessions")
        except Exception as e:
            print(f"Error in periodic cleanup: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    print("Starting Encrypted Chat Server...")
    print(f"Database initialized with {len(db.get_all_users())} users")
    print(f"Database file: {db.db_file}")
    
    # Print startup statistics
    stats = db.get_stats()
    print("\n=== Database Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    print("===========================\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data['username']
    user_id = str(uuid.uuid4())
    
    # Store user session
    user_sessions[request.sid] = {
        'username': username,
        'user_id': user_id,
        'public_key': data.get('public_key', '')
    }
    
    # Join public room by default
    join_room('public')
    
    emit('chat_joined', {
        'user_id': user_id,
        'username': username,
        'public_messages': public_messages[-50:],  # Last 50 messages
        'available_groups': list(group_rooms.keys())
    })
    
    # Notify others in public room
    emit('user_joined', {
        'username': username,
        'room': 'public'
    }, room='public', include_self=False)

@socketio.on('send_public_message')
def handle_public_message(data):
    if request.sid not in user_sessions:
        return
    
    user_info = user_sessions[request.sid]
    message = {
        'id': str(uuid.uuid4()),
        'username': user_info['username'],
        'message': data['message'],
        'encrypted_content': data.get('encrypted_content', ''),
        'timestamp': datetime.now().isoformat(),
        'room': 'public'
    }
    
    public_messages.append(message)
    
    # Keep only last 1000 messages
    if len(public_messages) > 1000:
        public_messages.pop(0)
    
    emit('new_message', message, room='public')

@socketio.on('create_group')
def handle_create_group(data):
    if request.sid not in user_sessions:
        return
    
    group_name = data['group_name']
    password = data.get('password', '')
    
    if group_name in group_rooms:
        emit('error', {'message': 'Group already exists'})
        return
    
    user_info = user_sessions[request.sid]
    group_id = str(uuid.uuid4())
    
    group_rooms[group_name] = {
        'id': group_id,
        'creator': user_info['username'],
        'password': password,
        'members': [user_info['username']],
        'messages': []
    }
    
    join_room(group_name)
    
    emit('group_created', {
        'group_name': group_name,
        'group_id': group_id
    })
    
    # Notify all users about new group
    emit('group_list_updated', {
        'available_groups': list(group_rooms.keys())
    }, broadcast=True)

@socketio.on('join_group')
def handle_join_group(data):
    if request.sid not in user_sessions:
        return
    
    group_name = data['group_name']
    password = data.get('password', '')
    
    if group_name not in group_rooms:
        emit('error', {'message': 'Group does not exist'})
        return
    
    group = group_rooms[group_name]
    
    # Check password if required
    if group['password'] and group['password'] != password:
        emit('error', {'message': 'Invalid password'})
        return
    
    user_info = user_sessions[request.sid]
    username = user_info['username']
    
    # Add user to group if not already a member
    if username not in group['members']:
        group['members'].append(username)
    
    join_room(group_name)
    
    emit('group_joined', {
        'group_name': group_name,
        'messages': group['messages'][-50:],  # Last 50 messages
        'members': group['members']
    })
    
    # Notify others in the group
    emit('user_joined', {
        'username': username,
        'room': group_name
    }, room=group_name, include_self=False)

@socketio.on('send_group_message')
def handle_group_message(data):
    if request.sid not in user_sessions:
        return
    
    group_name = data['group_name']
    
    if group_name not in group_rooms:
        emit('error', {'message': 'Group does not exist'})
        return
    
    user_info = user_sessions[request.sid]
    message = {
        'id': str(uuid.uuid4()),
        'username': user_info['username'],
        'message': data['message'],
        'encrypted_content': data.get('encrypted_content', ''),
        'timestamp': datetime.now().isoformat(),
        'room': group_name
    }
    
    group_rooms[group_name]['messages'].append(message)
    
    # Keep only last 1000 messages per group
    if len(group_rooms[group_name]['messages']) > 1000:
        group_rooms[group_name]['messages'].pop(0)
    
    emit('new_message', message, room=group_name)

@socketio.on('leave_group')
def handle_leave_group(data):
    if request.sid not in user_sessions:
        return
    
    group_name = data['group_name']
    user_info = user_sessions[request.sid]
    username = user_info['username']
    
    if group_name in group_rooms:
        if username in group_rooms[group_name]['members']:
            group_rooms[group_name]['members'].remove(username)
        
        leave_room(group_name)
        
        emit('group_left', {'group_name': group_name})
        
        # Notify others in the group
        emit('user_left', {
            'username': username,
            'room': group_name
        }, room=group_name)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)