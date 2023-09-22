# noinspection PyProtectedMember
def migrate(store):
    store._execute("""
        ALTER TABLE Tickets ADD COLUMN raised_at TIMESTAMP;
    """)
    store._execute("""
        ALTER TABLE Tickets ADD COLUMN closed_at TIMESTAMP;
    """)
