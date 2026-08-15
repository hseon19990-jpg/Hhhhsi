user_states = {}
user_temp_data = {}

STATE_NONE = 0
STATE_WAITING_ACCOUNT = 1
STATE_WAITING_CLIP = 2
STATE_WAITING_GROUP = 3
STATE_WAITING_DELETE_ACCOUNT = 4
STATE_WAITING_DELETE_GROUP = 5
STATE_WAITING_DELETE_CLIP = 6
STATE_WAITING_TIMER = 7
STATE_WAITING_CONFIRM = 8
STATE_WAITING_SESSION = 9
STATE_WAITING_SESSION_PHONE = 10
STATE_WAITING_ROTATE = 11
STATE_WAITING_CHATS = 12

def set_state(user_id, state):
    user_states[user_id] = state

def get_state(user_id):
    return user_states.get(user_id, STATE_NONE)

def clear_state(user_id):
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_temp_data:
        del user_temp_data[user_id]

def set_temp_data(user_id, key, value):
    if user_id not in user_temp_data:
        user_temp_data[user_id] = {}
    user_temp_data[user_id][key] = value

def get_temp_data(user_id, key):
    return user_temp_data.get(user_id, {}).get(key)

def clear_temp_data(user_id):
    if user_id in user_temp_data:
        del user_temp_data[user_id]
