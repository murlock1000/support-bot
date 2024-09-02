# noinspection PyProtectedMember
def migrate(store):
    store._execute("""
        ALTER TABLE Chats ADD COLUMN created_at TIMESTAMP;
    """)
    store._execute("""
        ALTER TABLE Chats ADD COLUMN closed_at TIMESTAMP;
    """)
    store._execute("""
        ALTER TABLE Chats ADD COLUMN status VARCHAR(100) NULL DEFAULT 'open';
    """)
