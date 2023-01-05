# noinspection PyProtectedMember
def migrate(store):
    
    if store.db_type == "postgres":
        store._execute("""
            CREATE TABLE Staff (
                user_id text PRIMARY KEY
            )
        """)
        store._execute("""
            CREATE TABLE Users (
                user_id text PRIMARY KEY
            )
        """)
        store._execute("""
            CREATE TABLE Tickets (
                id INTEGER PRIMARY KEY,
                user_room_id text,
                staff_room_id text,
                user_id text REFERENCES Users(user_id),
                status text DEFAULT 'open',
                UNIQUE(user_room_id,user_id)
            )
        """)
        store._execute("""
            CREATE TABLE TicketsStaffRelation (
                ticket_id INTEGER,
                staff_id text,
                FOREIGN KEY (ticket_id) REFERENCES Tickets(id) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES Staff(user_id) ON DELETE CASCADE
            )
        """)
        store._execute("""
            CREATE TABLE TimelineEvents (
                id INTEGER PRIMARY KEY,
                ticket_id INTEGER REFERENCES Tickets(id) ON DELETE CASCADE,
                device_id text,
                event_id text,
                room_id text,
                session_id text,
                event text,
                user_id text default ''
            )
        """)
    else:
        store._execute("""
            CREATE TABLE Staff (
                user_id text PRIMARY KEY
            )
        """)
        store._execute("""
            CREATE TABLE Users (
                user_id text PRIMARY KEY
            )
        """)
        store._execute("""
            CREATE TABLE Tickets (
                id INTEGER PRIMARY KEY autoincrement,
                user_room_id text,
                staff_room_id text,
                user_id text REFERENCES Users(user_id),
                status text,
                UNIQUE(user_room_id,user_id)
            )
        """)
        store._execute("""
            CREATE TABLE TicketsStaffRelation (
                ticket_id INTEGER,
                staff_id text,
                FOREIGN KEY (ticket_id) REFERENCES Tickets(id) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES Staff(user_id) ON DELETE CASCADE
            )
        """)
        store._execute("""
            CREATE TABLE TimelineEvents (
                id INTEGER PRIMARY KEY autoincrement,
                ticket_id INTEGER REFERENCES Tickets(id) ON DELETE CASCADE,
                device_id text,
                event_id text,
                room_id text,
                session_id text,
                event text,
                user_id text default ''
            )
        """)
