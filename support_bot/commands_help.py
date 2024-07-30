COMMAND_WRITE = """Sends a message to a room using the bot. Usage:

`!message <room ID or alias> <Text to write>`

For example:

`!message #foobar:domain.tld Hello people in the Foobar room.`
"""

COMMAND_CLAIM = """Claim the ticket with specified index (be invited to the ticket room). Usage:

`!c claim <Ticket index>`

For example:

`!c claim 5`
"""

COMMAND_CLAIMFOR = """Claim the ticket with specified index (be invited to the ticket room) for a specific user. Usage:

`!c claimfor <user id> <Ticket index>`

For example:

`!c claimfor @test:matrix.org 5`
"""

COMMAND_RAISE = """Raise a ticket for a user with a specified name or for the replied to message sender. Usage:

Reply:
`!raise <ticket name>`

Standalone: 
`!c raise <user id> <ticket name>`
"""

COMMAND_ADD_STAFF = """Add staff with specified name. Usage:

`!c addstaff <user id>`
"""

COMMAND_ACTIVE_TICKET = """Get active ticket of specified user (the ticket user's messages are being sent to). Usage:

`!c activeticket <user id>`
"""

COMMAND_CLOSE = """Closes the ticket that belongs to the current room (no longer transmits communications to the ticket room). Usage:
(In a Ticket room)
`!c close`
"""

COMMAND_REOPEN = """Reopens the ticket that belongs to the current room (starts relaying user communications to the ticket room).
If Ticket ID provided - reopens the specified Ticket and invites the staff to the Ticket room (if not in it yet). Usage:
(In a Ticket room)
`!c reopen <Ticked Index>`
"""

COMMAND_OPEN_TICKETS = """Lists all currently open tickets, or open tickets that are assigned to a specified staff member. Usage:

`!c opentickets <user id>`
"""

COMMAND_SETUP_COMMUNICATIONS_ROOM = """Updates the user's communications room (DM between user and bot). 
Selects any DM room that only the bot and the user are in. Or creates a new DM and invites the user if not found. Usage:

`!c setupcommunicationsroom <user id>`
"""

COMMAND_PRINT_ROOM_STATE = """Prints the known room state of the provided room id. 
Usage:

`!c printroomstate <room id>`
"""

COMMAND_FETCH_ROOM_STATE = """Fetches the room state of the provided room id. 
Usage:

`!c fetchroomstate <filter json> <state> <since>`
"""

COMMAND_MESSAGE_ROOM = """Sends message to the room with provided room id. 
Usage:

`!c messageroom <room id> <message to send>`
"""

COMMAND_CHAT = """Create or join an existing chat for a user with a specified name or for the replied to message sender. Usage:

Reply:
`!chat

Standalone: 
`!c chat <user id>`
"""

COMMAND_FORCE_CLOSE_TICKET = """Closes the ticket that has the provided id. Usage:
`!c forcecloseticket <ticket id>`
"""

COMMAND_DELETE_ROOM_STATE = """Deletes local state of the provided room id. Usage:
`!c _deleteroomstate <room id>`
"""
