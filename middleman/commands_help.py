COMMAND_WRITE = """Sends a message to a room using the bot. Usage:

`!message <room ID or alias> <Text to write>`

For example:

`!message #foobar:domain.tld Hello people in the Foobar room.`
"""

COMMAND_CLAIM = """Claim the ticket with specified index. Usage:

`!claim <Ticket index>`

For example:

`!claim 5`
"""

COMMAND_RAISE = """Raise a ticket for a user with a specified name. Usage:

`!raise <user id> <ticket name>`

For example:

`!claim @test:server.com Important issue`
"""

COMMAND_ADD_STAFF = """Add staff with specified name. Usage:

`!addstaff <user id>`
"""

COMMAND_ACTIVE_TICKET = """Get active ticket of specified user (the ticket users messages are being sent to). Usage:

`!activeticket <user id>`
"""