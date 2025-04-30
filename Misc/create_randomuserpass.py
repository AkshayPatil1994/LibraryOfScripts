import random
import string
 
# Number of users
num_users = 10 
 
# Adjectives
adjectives = [
    'funky', 'squishy', 'wobbly', 'sassy', 'bouncy',
    'zesty', 'grumpy', 'fluffy', 'chunky', 'jazzy',
    'snarky', 'quirky', 'jolly', 'spicy', 'goofy'
]
# Nouns
nouns = [
    'cat', 'potato', 'pancake', 'taco', 'donut',
    'pickle', 'monkey', 'waffle', 'nugget', 'cupcake',
    'penguin', 'sloth', 'otter', 'hamster', 'banana'
]
# Some useful function definitions 
def generate_funny_username():
    """Generates a funny username with adjective + noun + random number."""
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    number = random.randint(10, 99)
    return f"{adj}-{noun}{number}"
 
def generate_random_password(length=10):
    """Generates a random password with letters, digits, and punctuation."""
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choices(chars, k=length))
    return password
 
def create_users(num_users):
    """Generates a list of user dictionaries with funny usernames and passwords."""
    users = []
    for _ in range(num_users):
        user = {
            'username': generate_funny_username(),
            'password': generate_random_password()
        }
        users.append(user)
    return users
 
# Create users
users_list = create_users(num_users)
 
# Print users
for user in users_list:
    print(f"{user['username']} {user['password']}")
